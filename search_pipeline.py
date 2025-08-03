import asyncio  # Provides async support for concurrent operations
import json     # Used for formatting LLM output into JSON
from openai import OpenAI, AsyncOpenAI  # OpenAI clients (Async version used here)
import os
from typing import List, Dict  # Generic types for annotations: List and Dict

# External search modules from local mock_sources package
from mock_sources.news_api import search_news
from mock_sources.web_scraper import scrape_website
from mock_sources.linkedin_api import search_linkedin

# HTTP session and timeout config
from aiohttp import ClientSession, ClientTimeout

# Utility functions: cache object, query hash function, evidence deduplicator
from utils import CACHE, hash_key, deduplicate_evidence

# Set max timeout for HTTP calls
MAX_TIMEOUT = 10

# OpenAI client instance (async version)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# -----------------------------------
# GOOGLE CSE-powered HTML fetcher
# -----------------------------------
async def fetch_html(domain: str, query: str, session: ClientSession):
    api_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.getenv("GOOGLE_API_KEY"),
        "cx":  os.getenv("GOOGLE_CX"),
        "q":   f"site:{domain} {query}",
        "num": 3
    }
    try:
        async with session.get(api_url, params=params, timeout=ClientTimeout(total=MAX_TIMEOUT)) as resp:
            if resp.status != 200:
                raise Exception(f"Web search HTTP {resp.status}")
            data = await resp.json()
            items = data.get("items", [])
            if items:
                snippets = [item.get("snippet","") for item in items]
                confidence = min(0.7 + 0.1*len(snippets), 0.95)
                return {
                    "source": "web_search",
                    "domain": domain,
                    "query": query,
                    "content": "; ".join(snippets),
                    "confidence": round(confidence,2)
                }
            else:
                return {
                    "source": "web_search",
                    "domain": domain,
                    "query": query,
                    "content": "No web search results found.",
                    "confidence": 0.5
                }
    except Exception as e:
        return {
            "source": "web_search",
            "domain": domain,
            "query": query,
            "content": f"Exception: {e}",
            "confidence": 0.0
        }


# -----------------------------------
# Summarize & synthesize findings
# -----------------------------------
async def synthesize_findings(evidence_list, research_goal):
    # Format the input evidence into a summarization prompt for LLM
    prompt = (
       f"Our research goal: {research_goal}\n\n"
       "Here is the collected raw evidence:\n" +
       "\n".join(f"- {e['content']}" for e in evidence_list) +
       "\n\nSummarize in JSON with keys: "
       '"summary","signals_found","evidence_count"'
    )
    # Call OpenAI to generate structured summary
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "You are a researcher assistant."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    return json.loads(response.choices[0].message.content)


# -----------------------------------
# Pipeline class: full orchestration
# -----------------------------------
class SearchPipeline:
    def __init__(self):
        self.failed_requests = 0      # Count of total failed search attempts
        self.total_requests = 0       # Count of total search calls
        self.cache_hits = 0           # How many times cache was used
        self.semaphore = None         # Concurrency limiter (set in batch)

    # -----------------------------------
    # Resilient wrapper for any search call
    # -----------------------------------
    async def safe_call(self, func, domain, query, retries=2):
        key = hash_key(domain, query)      # Create cache key from domain + query
        if CACHE.get(key):                 # Check if result is cached
            self.cache_hits += 1
            return CACHE.get(key)

        self.total_requests += 1
        for attempt in range(retries + 1):  # Allow retries on failure
            try:
                async with self.semaphore:
                    result = await asyncio.wait_for(func(domain, query), timeout=MAX_TIMEOUT)
                CACHE.set(key, result)     # Cache the result for reuse
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
            await asyncio.sleep(0.2 * (2 ** attempt))  # Exponential backoff


    # -----------------------------------
    # Search all sources for a single company
    # -----------------------------------
    async def search_company(self, domain: str, queries: List[str], session, research_goal: str) -> Dict:
        results = []  # Container for all raw search hits

        # Loop through each query and call all sources
        for query in queries:
            query = query.strip().strip('"')  # Clean query string
            news_task = self.safe_call(search_news, domain, query)
            scrape_task = self.safe_call(scrape_website, domain, query)
            linkedin_task = self.safe_call(search_linkedin, domain, query)
            html_task = self.safe_call(lambda d, q: fetch_html(d, q, session), domain, query)

            # Run all search calls concurrently
            r = await asyncio.gather(news_task, scrape_task, html_task, linkedin_task)
            results.extend(r)

        # Filter out failed/exception results
        clean_results = [
             r for r in results
             if not r.get("content", "").startswith("Exception:")
        ]

        # Deduplicate similar or overlapping pieces of evidence
        clean_results = deduplicate_evidence(clean_results)

        # Calculate average confidence from all successful evidence
        confidence = (
            sum(r["confidence"] for r in clean_results) / len(clean_results)
        ) if clean_results else 0

        # Generate summary from all sources + return structured output
        return {
            "domain": domain,
            "confidence_score": round(confidence, 2),
            "evidence_sources": len(clean_results),
            "findings": await synthesize_findings(clean_results, research_goal)
        }

    # -----------------------------------
    # Batch search for many companies
    # -----------------------------------
    async def batch_search(self, domains: List[str], queries: List[str], research_goal: str, session, max_parallel: int = 20) -> List[Dict]:
        self.semaphore = asyncio.Semaphore(max_parallel)  # Limit concurrency to avoid overload
        tasks = [self.search_company(domain, queries, session, research_goal) for domain in domains]
        return await asyncio.gather(*tasks)  # Run all tasks concurrently

    # -----------------------------------
    # Metrics for debugging/monitoring
    # -----------------------------------
    def get_metrics(self):
        return {
            "failed_requests": self.failed_requests,
            "cache_hit_rate": (round(self.cache_hits / self.total_requests, 2)
                                if self.total_requests else 0)
        }