import asyncio  # Provides async support for concurrent operations
import json
from openai import OpenAI, AsyncOpenAI
import os
from typing import List, Dict  # Generic types for annotations: List and Dict
from mock_sources.news_api import search_news  # Function to search news via API
from mock_sources.web_scraper import scrape_website  # Function to scrape company website
from mock_sources.linkedin_api import search_linkedin  # Function to search LinkedIn via API
from aiohttp import ClientSession, ClientTimeout  # HTTP client session and timeout config
from utils import CACHE, hash_key, deduplicate_evidence  # Cache store, key hasher, and deduplication helper

MAX_TIMEOUT = 10  # Maximum total seconds to wait for an HTTP request

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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


async def synthesize_findings(evidence_list, research_goal):
    # Build a prompt that says: "Given these snippets, summarize how they address: <research_goal>"
    prompt = (
       f"Our research goal: {research_goal}\n\n"
       "Here is the collected raw evidence:\n" +
       "\n".join(f"- {e['content']}" for e in evidence_list) +
       "\n\nSummarize in JSON with keys: "
       '"summary","signals_found","evidence_count"'
    )
    # call out to OpenAI asynchronously (or a threadpool)…
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "You are a researcher assistant."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    return json.loads(response.choices[0].message.content)



class SearchPipeline:  # Orchestrates all search functions and aggregates results
    def __init__(self):
        self.failed_requests = 0  # Counter for total failed calls
        self.total_requests = 0  # Counter for all calls made
        self.cache_hits = 0  # Counter for cache retrievals
        self.semaphore = None  # Async limiter, set in batch search

    async def safe_call(self, func, domain, query, retries=2):
        key = hash_key(domain, query)
        if CACHE.get(key):
            self.cache_hits += 1
            return CACHE.get(key)

        self.total_requests += 1
        for attempt in range(retries + 1):
            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(func(domain, query), timeout=MAX_TIMEOUT)
                CACHE.set(key, result)
                return result

            except asyncio.TimeoutError:
                self.failed_requests += 1
                if attempt == retries:
                    return {
                        "source": func.__name__,
                        "domain": domain,
                        "query": query,
                        "content": "timeout",
                        "confidence": 0.0
                    }

            except Exception as e:
                self.failed_requests += 1
                if attempt == retries:
                    return {
                        "source": func.__name__,
                        "domain": domain,
                        "query": query,
                        "content": f"Exception: {e}",
                        "confidence": 0.0
                    }
            await asyncio.sleep(0.2 * (2 ** attempt))


    async def search_company(self, domain: str, queries: List[str], session, research_goal: str) -> Dict:
        results = []  # Container for all raw search hits
        # Launch all source-specific calls per query
        for query in queries:
            query = query.strip().strip('"')  # remove any surrounding quotes
            news_task = self.safe_call(search_news, domain, query)
            scrape_task = self.safe_call(scrape_website, domain, query)
            linkedin_task = self.safe_call(search_linkedin, domain, query)
            html_task = self.safe_call(lambda d, q: fetch_html(d, q, session), domain, query)

            # Wait for all five tasks to complete in parallel
            r = await asyncio.gather(news_task, scrape_task, html_task, linkedin_task)
            results.extend(r)  # Add their outputs to the results list
        # Filter out any calls that returned errors
        # clean_results = [r for r in results if "error" not in r]
        clean_results = [r for r in results if r.get("confidence", 0) > 0]
        # Compute average confidence across successes
        confidence = (sum(r["confidence"] for r in clean_results) / len(clean_results)) if clean_results else 0
        # Return aggregated result for this company
        return {
            "domain": domain,
            "confidence_score": round(confidence, 2),
            "evidence_sources": len(clean_results),
            "findings": await synthesize_findings(clean_results, research_goal)
        }

    async def batch_search(self, domains: List[str], queries: List[str], research_goal: str,session, max_parallel: int = 20) -> List[Dict]:
        # Set up semaphore to allow up to max_parallel concurrent calls
        self.semaphore = asyncio.Semaphore(max_parallel)
        # Create a gather of search_company tasks for each domain
        tasks = [self.search_company(domain, queries, session, research_goal) for domain in domains]
        return await asyncio.gather(*tasks)  # Wait for all domain searches to finish

    def get_metrics(self):  # Retrieve pipeline performance stats
        return {
            "failed_requests": self.failed_requests,  # Total failures
            "cache_hit_rate": (round(self.cache_hits / self.total_requests, 2)
                                if self.total_requests else 0)  # Cache efficiency
        }

    # async def stream_evidence(self, domains, queries):  # Yield evidence items as they arrive
    #     import itertools  # For creating product of domains and queries

    #     async with ClientSession() as session:  # Separate session for streaming
    #         coros = []  # List of individual safe_call coroutines
    #         # Build one coroutine per domain-query-source combination
    #         for domain, query in itertools.product(domains, queries):
    #             coros += [
    #                 self.safe_call(search_news, domain, query),
    #                 self.safe_call(scrape_website, domain, query),
    #                 self.safe_call(search_linkedin, domain, query),
    #             ]
    #         # As each call completes, yield its result immediately
    #         for future in asyncio.as_completed(coros):
    #             try:
    #                 result = await future  # Wait for this particular coroutine
    #                 yield result  # Push the result out to the caller
    #             except Exception as e:
    #                 yield {"error": str(e)}  # On unexpected error, yield an error dict
