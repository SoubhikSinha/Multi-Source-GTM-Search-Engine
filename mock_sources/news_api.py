'''
Mock implementation of a news API search.  # Describes that this block fakes the real API for testing.
It simulates network delay and random failures like a real-world call.
'''

# import asyncio  # Imports asyncio to simulate asynchronous network latency.
# import random   # Imports random to simulate occasional API failures and random confidence scores.

# async def search_news(domain: str, query: str) -> dict:  # Defines an async mock function taking company domain and search query.
#     await asyncio.sleep(random.uniform(0.05, 0.15))        # Pauses 50–150 ms to mimic network delay.
#     if random.random() < 0.05:                             # 5% chance to simulate an API failure.
#         raise Exception("News API failure")                # Raises an exception to mimic a failed API call.
#     return {                                               # Returns a fake successful response dictionary.
#         "source": "news",                                  # Labels the data source.
#         "domain": domain,                                  # Echoes the input domain.
#         "query": query,                                    # Echoes the input query.
#         "content": f"News mention of '{query}' on {domain}",  # Mock content snippet.
#         "confidence": round(random.uniform(0.7, 0.95), 2)  # Random confidence between 0.7 and 0.95.
#     }

'''
Below is the implementation of the real news API search using NewsAPI.org.
'''
import os               # Provides functions to interact with the operating system.
import aiohttp          # Enables making asynchronous HTTP requests.
import asyncio          # Provides async functionality (used if mocking or elsewhere).
from dotenv import load_dotenv  # Loads environment variables from a .env file.

load_dotenv()  # Reads key/value pairs from a .env file and adds them to os.environ.
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Retrieves the NewsAPI API key from environment variables.

NEWS_API_URL = "https://newsapi.org/v2/everything"  # Endpoint for searching news articles.

async def search_news(domain: str, query: str) -> dict:
    params = {
        "q": query,          # only your keywords
        "domains": domain,   # restrict to stripe.com
        "sortBy": "relevancy",
        "language": "en",
        "apiKey": NEWS_API_KEY,
        "pageSize": 3
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(NEWS_API_URL, params=params, timeout=8) as resp:
                data = await resp.json()
                # DEBUG: print raw JSON once to inspect
                # print("NewsAPI response:", json.dumps(data, indent=2))

                # if resp.status != 200:
                #     return {
                #         "source": "news",
                #         "domain": domain,
                #         "query": query,
                #         "content": f"News API error: {resp.status}",
                #         "confidence": 0.0
                #     }
                if resp.status != 200:
                    # Let safe_call retry on rate‐limit or other failures
                    raise Exception(f"News API HTTP {resp.status}")

                articles = data.get("articles", [])
                if articles:
                    headlines = [a["title"] for a in articles]
                    confidence = min(0.7 + 0.1 * len(headlines), 0.95)
                    return {
                        "source": "news",
                        "domain": domain,
                        "query": query,
                        "content": "; ".join(headlines),
                        "confidence": round(confidence, 2)
                    }
                else:
                    return {
                        "source": "news",
                        "domain": domain,
                        "query": query,
                        "content": "No news results found.",
                        "confidence": 0.5
                    }
    except Exception as e:
        return {
            "source": "news",
            "domain": domain,
            "query": query,
            "content": f"Exception: {e}",
            "confidence": 0.0
        }

