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
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")  # Retrieves the NewsAPI API key from environment variables.

NEWSAPI_URL = "https://newsapi.org/v2/everything"  # Endpoint for searching news articles.

async def search_news(domain: str, query: str) -> dict:  # Defines the async function to fetch news articles.
    # Build the query parameters for the NewsAPI request.
    params = {
        "q": f"{domain} {query}",    # Search string combining domain and query keywords.
        "sortBy": "relevancy",       # Sort results by relevance to the query.
        "language": "en",            # Only return articles in English.
        "apiKey": NEWSAPI_KEY,       # API key for authentication.
        "pageSize": 3                # Limit the number of articles returned to 3.
    }
    try:
        # Create an asynchronous HTTP session for making requests.
        async with aiohttp.ClientSession() as session:
            # Send the GET request with an 8-second timeout.
            async with session.get(NEWSAPI_URL, params=params, timeout=8) as resp:
                # If the HTTP status is not OK (200), treat as an error.
                if resp.status != 200:
                    return {
                        "source": "news",                     # Labels the data source.
                        "domain": domain,                     # Echoes the input domain.
                        "query": query,                       # Echoes the input query.
                        "content": f"News API error: {resp.status}",  # Error message including status code.
                        "confidence": 0.0                     # Zero confidence due to failure.
                    }
                # Parse the response body as JSON.
                data = await resp.json()
                # Extract the list of articles, defaulting to an empty list if none present.
                articles = data.get("articles", [])
                if articles:
                    # Collect the title from each returned article.
                    headlines = [article["title"] for article in articles]
                    # Compute a naive confidence score: base 0.7 + 0.1 per article, capped at 0.95.
                    confidence = min(0.7 + 0.1 * len(headlines), 0.95)
                    return {
                        "source": "news",                     # Labels the data source.
                        "domain": domain,                     # Echoes the input domain.
                        "query": query,                       # Echoes the input query.
                        "content": "; ".join(headlines),      # Join all headlines into a single string.
                        "confidence": round(confidence, 2)    # Rounded confidence score.
                    }
                else:
                    # No articles were found matching the query.
                    return {
                        "source": "news",                     # Labels the data source.
                        "domain": domain,                     # Echoes the input domain.
                        "query": query,                       # Echoes the input query.
                        "content": "No news results found.",  # Indicates absence of results.
                        "confidence": 0.5                     # Medium confidence in “no results” outcome.
                    }
    except Exception as e:
        # Catch any exception (network error, JSON parsing error, etc.) and return a structured error response.
        return {
            "source": "news",                         # Labels the data source.
            "domain": domain,                         # Echoes the input domain.
            "query": query,                           # Echoes the input query.
            "content": f"Exception: {str(e)}",        # Includes the exception message.
            "confidence": 0.0                         # Zero confidence due to the exception.
        }
