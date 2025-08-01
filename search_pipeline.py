import asyncio
from typing import List, Dict
from mock_sources.news_api import search_news
from mock_sources.job_board_api import search_jobs
from mock_sources.web_scraper import scrape_website
from mock_sources.linkedin_api import search_linkedin
from aiohttp import ClientSession, ClientTimeout
from utils import CACHE, hash_key, deduplicate_evidence  # Single import line

MAX_TIMEOUT = 10

async def fetch_html(domain: str, query: str, session: ClientSession):
    url = f"https://dummysearchengine.com/search?q=site:{domain}+{query}"
    try:
        async with session.get(url, timeout=ClientTimeout(total=MAX_TIMEOUT)) as resp: # Fetching HTML content
            return {
                "source": "raw_html",
                "domain": domain,
                "query": query,
                "content": await resp.text(),
                "confidence": 0.5  # baseline confidence
            }
    except Exception as e:
        return {"error": str(e)}

def synthesize_findings(evidence_list):
    deduped_evidence = deduplicate_evidence(evidence_list) # Deduplicating evidence
    combined_text = " ".join([e["content"].lower() for e in deduped_evidence]) # Combining content from all evidence sources

    ai_fraud_keywords = ["fraud detection", "aml", "anti money laundering", "risk engine"] # Keywords to identify AI fraud detection
    ai_fraud_detection = any(kw in combined_text for kw in ai_fraud_keywords) # Checking for AI fraud detection keywords

    tech_keywords = {
        "tensorflow": "TensorFlow",
        "scikit-learn": "scikit-learn",
        "pytorch": "PyTorch",
        "xgboost": "XGBoost",
        "huggingface": "Hugging Face"
    }

    technologies = [tech for key, tech in tech_keywords.items() if key in combined_text] # Identifying technologies used in the evidence

    return {
        "ai_fraud_detection": ai_fraud_detection,
        "technologies": technologies or None,
        "evidence": deduped_evidence,
        "signals_found": len(deduped_evidence)
    }

class SearchPipeline:
    def __init__(self):
        self.failed_requests = 0
        self.total_requests = 0
        self.cache_hits = 0
        self.semaphore = None  # Will be set dynamically

    async def safe_call(self, func, domain, query):
        key = hash_key(domain, query) # Generating a cache key
        cached = CACHE.get(key) # Checking if the result is cached
        self.total_requests += 1 # Incrementing total requests count
        if cached:
            self.cache_hits += 1 # Incrementing cache hits count
            return cached

        try:
            async with self.semaphore:
                return await asyncio.wait_for(func(domain, query), timeout=5) # Calling the function with a timeout
        except asyncio.TimeoutError: # Handling timeout errors
            self.failed_requests += 1 # Incrementing failed requests count
            return {"error": "timeout"} # Returning a timeout error
        except Exception as e:
            self.failed_requests += 1 # Incrementing failed requests count
            return {"error": str(e)} # Returning the error message

    async def search_company(self, domain: str, queries: List[str], session) -> Dict:
        results = []
        for query in queries:
            job_task = self.safe_call(search_jobs, domain, query) # Calling the job search API
            news_task = self.safe_call(search_news, domain, query) # Calling the news search API
            scrape_task = self.safe_call(scrape_website, domain, query) # Calling the web scraper API
            linkedin_task = self.safe_call(search_linkedin, domain, query) # Calling the LinkedIn search API
            html_task = self.safe_call(lambda d, q: fetch_html(d, q, session), domain, query) # Fetching HTML content

            r = await asyncio.gather(job_task, news_task, scrape_task, html_task, linkedin_task) # Gathering results from all tasks
            results.extend(r)
        clean_results = [r for r in results if "error" not in r]
        confidence = sum(r["confidence"] for r in clean_results) / len(clean_results) if clean_results else 0
        return {
            "domain": domain,
            "confidence_score": round(confidence, 2),
            "evidence_sources": len(clean_results),
            "findings": synthesize_findings(clean_results)
        }

    async def batch_search(self, domains: List[str], queries: List[str], session, max_parallel: int = 20) -> List[Dict]:
        self.semaphore = asyncio.Semaphore(max_parallel) # Setting the semaphore for parallel searches
        tasks = [self.search_company(domain, queries, session) for domain in domains] # Creating search tasks for each domain
        return await asyncio.gather(*tasks)

    def get_metrics(self):
        return {
            "failed_requests": self.failed_requests,
            "cache_hit_rate": round(self.cache_hits / self.total_requests, 2) if self.total_requests > 0 else 0
        }