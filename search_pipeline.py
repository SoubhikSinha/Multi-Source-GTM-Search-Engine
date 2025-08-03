import asyncio  # Provides asynchronous capabilities to handle concurrent tasks
import json  # Used to parse and manipulate JSON data
from openai import OpenAI, AsyncOpenAI  # OpenAI SDK clients (synchronous and asynchronous)
import os  # Used to access environment variables
from typing import List, Dict  # Type hints for function signatures and variables

# Import mock search functions from their respective source files
from mock_sources.news_api import search_news  # Function to perform news search
from mock_sources.web_scraper import scrape_website  # Function to scrape content from websites
from mock_sources.linkedin_api import search_linkedin  # Function to search LinkedIn content

# HTTP session handling and timeout settings
from aiohttp import ClientSession, ClientTimeout  # Async HTTP client and timeout control

# Utility functions and in-memory cache from utils module
from utils import CACHE, hash_key, deduplicate_evidence  # Simple cache system, hashing utility, deduplicator

# Constant for setting a maximum timeout for all external requests
MAX_TIMEOUT = 10  # Maximum time in seconds before timing out HTTP requests

# Instantiate OpenAI async client using environment variable
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Async function to fetch search snippets using Google Custom Search Engine
async def fetch_html(domain: str, query: str, session: ClientSession):
    api_url = "https://www.googleapis.com/customsearch/v1"  # Endpoint for Google Custom Search
    params = {
        "key": os.getenv("GOOGLE_API_KEY"),  # API key for Google Search
        "cx":  os.getenv("GOOGLE_CX"),  # Custom search engine ID
        "q":   f"site:{domain} {query}",  # Compose query to restrict search to domain
        "num": 3  # Return top 3 results
    }
    try:
        # Send GET request with specified timeout
        async with session.get(api_url, params=params, timeout=ClientTimeout(total=MAX_TIMEOUT)) as resp:
            if resp.status != 200:  # If response is not OK, raise an exception
                raise Exception(f"Web search HTTP {resp.status}")
            data = await resp.json()  # Parse response JSON
            items = data.get("items", [])  # Extract items or default to empty list
            if items:  # If there are search results
                snippets = [item.get("snippet","") for item in items]  # Extract snippets from results
                confidence = min(0.7 + 0.1*len(snippets), 0.95)  # Calculate confidence score
                return {
                    "source": "web_search",
                    "domain": domain,
                    "query": query,
                    "content": "; ".join(snippets),  # Join snippets into one string
                    "confidence": round(confidence,2)  # Round confidence
                }
            else:  # If no items found
                return {
                    "source": "web_search",
                    "domain": domain,
                    "query": query,
                    "content": "No web search results found.",
                    "confidence": 0.5
                }
    except Exception as e:  # On any exception during the fetch
        return {
            "source": "web_search",
            "domain": domain,
            "query": query,
            "content": f"Exception: {e}",
            "confidence": 0.0
        }

# Async function to synthesize a summary of the evidence collected from various sources
async def synthesize_findings(evidence_list, research_goal):
    # Build prompt with research goal and raw evidence
    prompt = (
       f"Our research goal: {research_goal}\n\n"
       "Here is the collected raw evidence:\n" +
       "\n".join(f"- {e['content']}" for e in evidence_list) +
       "\n\nSummarize in JSON with keys: "
       '"summary","signals_found","evidence_count"'
    )
    # Call OpenAI chat completion API with system and user messages
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[
          {"role": "system", "content": "You are a researcher assistant."},
          {"role": "user", "content": prompt}
        ],
        temperature=0.0  # Low randomness for consistent results
    )
    return json.loads(response.choices[0].message.content)  # Return parsed JSON result

# Class that encapsulates the entire search and aggregation pipeline
class SearchPipeline:
    def __init__(self):
        self.failed_requests = 0  # Tracks number of failed external requests
        self.total_requests = 0  # Tracks number of total requests
        self.cache_hits = 0  # Number of responses served from cache
        self.semaphore = None  # Used to limit concurrent access during batch search

    # Wrapper to safely call any async search function with retry and timeout
    async def safe_call(self, func, domain, query, retries=2):
        key = hash_key(domain, query)  # Generate cache key from domain and query
        if CACHE.get(key):  # If result exists in cache
            self.cache_hits += 1
            return CACHE.get(key)

        self.total_requests += 1
        for attempt in range(retries + 1):  # Retry loop
            try:
                async with self.semaphore:  # Limit concurrency
                    result = await asyncio.wait_for(func(domain, query), timeout=MAX_TIMEOUT)
                CACHE.set(key, result)  # Store result in cache
                return result

            except asyncio.TimeoutError:  # Handle timeout error
                self.failed_requests += 1
                if attempt == retries:  # On final retry, return timeout structure
                    return {
                        "source": func.__name__,
                        "domain": domain,
                        "query": query,
                        "content": "timeout",
                        "confidence": 0.0
                    }

            except Exception as e:  # Handle other exceptions
                self.failed_requests += 1
                if attempt == retries:  # Return exception structure
                    return {
                        "source": func.__name__,
                        "domain": domain,
                        "query": query,
                        "content": f"Exception: {e}",
                        "confidence": 0.0
                    }
            await asyncio.sleep(0.2 * (2 ** attempt))  # Exponential backoff

    # Search across multiple data sources for one company
    async def search_company(self, domain: str, queries: List[str], session, research_goal: str) -> Dict:
        results = []  # Store results from all sources

        for query in queries:  # Loop over each query
            query = query.strip().strip('"')  # Clean query string
            news_task = self.safe_call(search_news, domain, query)  # News API task
            scrape_task = self.safe_call(scrape_website, domain, query)  # Scraper task
            linkedin_task = self.safe_call(search_linkedin, domain, query)  # LinkedIn API task
            html_task = self.safe_call(lambda d, q: fetch_html(d, q, session), domain, query)  # Google search task

            r = await asyncio.gather(news_task, scrape_task, html_task, linkedin_task)  # Run all in parallel
            results.extend(r)  # Collect results

        clean_results = [  # Remove failed results
             r for r in results
             if not r.get("content", "").startswith("Exception:")
        ]

        clean_results = deduplicate_evidence(clean_results)  # Deduplicate overlapping content

        confidence = (
            sum(r["confidence"] for r in clean_results) / len(clean_results)
        ) if clean_results else 0  # Compute average confidence

        return {
            "domain": domain,  # Input domain
            "confidence_score": round(confidence, 2),  # Averaged confidence
            "evidence_sources": len(clean_results),  # Number of evidence sources
            "findings": await synthesize_findings(clean_results, research_goal)  # Summary
        }

    # Run search pipeline for multiple companies
    async def batch_search(self, domains: List[str], queries: List[str], research_goal: str, session, max_parallel: int = 20) -> List[Dict]:
        self.semaphore = asyncio.Semaphore(max_parallel)  # Limit concurrent executions
        tasks = [self.search_company(domain, queries, session, research_goal) for domain in domains]  # Prepare tasks
        return await asyncio.gather(*tasks)  # Run all tasks in parallel

    # Report pipeline metrics
    def get_metrics(self):
        return {
            "failed_requests": self.failed_requests,  # Number of failures
            "cache_hit_rate": (round(self.cache_hits / self.total_requests, 2)
                                if self.total_requests else 0)  # Ratio of cache hits
        }