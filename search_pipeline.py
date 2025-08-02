import asyncio  # Provides async support for concurrent operations
from typing import List, Dict  # Generic types for annotations: List and Dict
from mock_sources.news_api import search_news  # Function to search news via API
from mock_sources.job_board_api import search_jobs  # Function to search job board via API
from mock_sources.web_scraper import scrape_website  # Function to scrape company website
from mock_sources.linkedin_api import search_linkedin  # Function to search LinkedIn via API
from aiohttp import ClientSession, ClientTimeout  # HTTP client session and timeout config
from utils import CACHE, hash_key, deduplicate_evidence  # Cache store, key hasher, and deduplication helper

MAX_TIMEOUT = 10  # Maximum total seconds to wait for an HTTP request

async def fetch_html(domain: str, query: str, session: ClientSession):  # Fetch raw HTML for a domain+query
    url = f"https://dummysearchengine.com/search?q=site:{domain}+{query}"  # Build search URL
    try:
        # Send GET request with a total timeout, using the shared session
        async with session.get(url, timeout=ClientTimeout(total=MAX_TIMEOUT)) as resp:
            # Return a standardized dict with the raw HTML text
            return {
                "source": "raw_html",  # Label indicating this is uncooked HTML
                "domain": domain,  # Echo the domain
                "query": query,  # Echo the search query
                "content": await resp.text(),  # Read the response body as text
                "confidence": 0.5  # Base confidence for raw HTML evidence
            }
    except Exception as e:
        # On error, return an error dict with the exception message
        return {"error": str(e)}


def synthesize_findings(evidence_list):  # Combine and analyze evidence items
    """
    Analyze deduplicated evidence for AI fraud detection and key technologies.
    Uses expanded keyword lists and regex-based matching.
    """
    import re  # Import regex module locally for matching
    # Remove duplicate evidence entries
    deduped = deduplicate_evidence(evidence_list)
    # Join all content strings, lowercase, and strip punctuation
    raw_text = " ".join(e.get("content", "") for e in deduped)
    text = re.sub(r"[^\w\s]", " ", raw_text.lower())

    # Keywords to detect AI fraud features
    ai_fraud_keywords = [
        "fraud detection", "fraud prevention", "transaction monitoring",
        "anomaly detection", "chargeback protection", "risk scoring",
        "behavioral analytics", "anti money laundering", "aml",
        "identity verification", "kyc", "risk engine"
    ]
    # Check if any fraud-related keyword appears as a whole word
    ai_fraud_detection = any(
        re.search(rf"\b{re.escape(kw)}\b", text) for kw in ai_fraud_keywords
    )

    # Map internal keys to human-readable technology names
    tech_keywords = {
        "tensorflow": "TensorFlow",
        "scikit-learn": "scikit-learn",
        "pytorch": "PyTorch",
        "xgboost": "XGBoost",
        "huggingface": "Hugging Face",
        "azureml": "Azure ML",
        "sagemaker": "AWS SageMaker",
        "vertex ai": "Google Vertex AI",
        "openai": "OpenAI",
    }
    # Collect technologies mentioned in the text
    technologies = [name for key, name in tech_keywords.items() if key in text]
    # If none found, set to None
    technologies = technologies or None

    # Return a summary dict with findings and evidence
    return {
        "ai_fraud_detection": ai_fraud_detection,  # True if fraud keywords detected
        "technologies": technologies,  # List of tech names or None
        "evidence": deduped,  # The cleaned, deduplicated evidence list
        "signals_found": len(deduped)  # How many evidence items survived dedupe
    }


class SearchPipeline:  # Orchestrates all search functions and aggregates results
    def __init__(self):
        self.failed_requests = 0  # Counter for total failed calls
        self.total_requests = 0  # Counter for all calls made
        self.cache_hits = 0  # Counter for cache retrievals
        self.semaphore = None  # Async limiter, set in batch search

    async def safe_call(self, func, domain, query, retries=2):  # Wraps calls with caching, retries, and backoff
        key = hash_key(domain, query)  # Create a unique cache key
        cached = CACHE.get(key)  # Try reading from cache
        self.total_requests += 1  # Increment total requests counter

        if cached:
            self.cache_hits += 1  # Increment cache hit counter
            return cached  # Return cached result immediately

        # Attempt the call with retries
        for attempt in range(retries + 1):
            try:
                # Use the semaphore to limit concurrency and wait with timeout
                async with self.semaphore:
                    return await asyncio.wait_for(func(domain, query), timeout=5)
            except asyncio.TimeoutError:
                # On timeout, count failure and retry if possible
                self.failed_requests += 1
                if attempt == retries:
                    return {"error": "timeout"}
            except Exception as e:
                # On any other exception, count failure and retry if possible
                self.failed_requests += 1
                if attempt == retries:
                    return {"error": str(e)}
            # Exponential backoff before next retry
            await asyncio.sleep(0.2 * (2 ** attempt))

    async def search_company(self, domain: str, queries: List[str], session) -> Dict:
        results = []  # Container for all raw search hits
        # Launch all source-specific calls per query
        for query in queries:
            job_task = self.safe_call(search_jobs, domain, query)
            news_task = self.safe_call(search_news, domain, query)
            scrape_task = self.safe_call(scrape_website, domain, query)
            linkedin_task = self.safe_call(search_linkedin, domain, query)
            html_task = self.safe_call(lambda d, q: fetch_html(d, q, session), domain, query)

            # Wait for all five tasks to complete in parallel
            r = await asyncio.gather(job_task, news_task, scrape_task, html_task, linkedin_task)
            results.extend(r)  # Add their outputs to the results list
        # Filter out any calls that returned errors
        clean_results = [r for r in results if "error" not in r]
        # Compute average confidence across successes
        confidence = (sum(r["confidence"] for r in clean_results) / len(clean_results)) if clean_results else 0
        # Return aggregated result for this company
        return {
            "domain": domain,
            "confidence_score": round(confidence, 2),
            "evidence_sources": len(clean_results),
            "findings": synthesize_findings(clean_results)
        }

    async def batch_search(self, domains: List[str], queries: List[str], session, max_parallel: int = 20) -> List[Dict]:
        # Set up semaphore to allow up to max_parallel concurrent calls
        self.semaphore = asyncio.Semaphore(max_parallel)
        # Create a gather of search_company tasks for each domain
        tasks = [self.search_company(domain, queries, session) for domain in domains]
        return await asyncio.gather(*tasks)  # Wait for all domain searches to finish

    def get_metrics(self):  # Retrieve pipeline performance stats
        return {
            "failed_requests": self.failed_requests,  # Total failures
            "cache_hit_rate": (round(self.cache_hits / self.total_requests, 2)
                                if self.total_requests else 0)  # Cache efficiency
        }

    async def stream_evidence(self, domains, queries):  # Yield evidence items as they arrive
        import itertools  # For creating product of domains and queries

        async with ClientSession() as session:  # Separate session for streaming
            coros = []  # List of individual safe_call coroutines
            # Build one coroutine per domain-query-source combination
            for domain, query in itertools.product(domains, queries):
                coros += [
                    self.safe_call(search_news, domain, query),
                    self.safe_call(search_jobs, domain, query),
                    self.safe_call(scrape_website, domain, query),
                    self.safe_call(search_linkedin, domain, query),
                ]
            # As each call completes, yield its result immediately
            for future in asyncio.as_completed(coros):
                try:
                    result = await future  # Wait for this particular coroutine
                    yield result  # Push the result out to the caller
                except Exception as e:
                    yield {"error": str(e)}  # On unexpected error, yield an error dict
