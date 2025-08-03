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

