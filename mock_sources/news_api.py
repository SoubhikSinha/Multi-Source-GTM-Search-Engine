import os               # Provides functions to interact with the operating system.
import aiohttp          # Enables making asynchronous HTTP requests.
import asyncio          # Provides async functionality (used if mocking or elsewhere).
from dotenv import load_dotenv  # Loads environment variables from a .env file.

# Load environment variables from .env into the OS environment
load_dotenv()

# Retrieve NewsAPI key from environment variables
NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Used to authenticate requests to NewsAPI

# NewsAPI endpoint to fetch articles related to specific topics/domains
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Asynchronous function to search news content for a domain and a query
async def search_news(domain: str, query: str) -> dict:
    # Parameters for the GET request to NewsAPI
    params = {
        "q": query,            # Main keywords to search (e.g. "kubernetes security")
        "domains": domain,     # Restrict the news search to the given domain (e.g. stripe.com)
        "sortBy": "relevancy", # Sort articles by how relevant they are to the query
        "language": "en",      # Limit results to English
        "apiKey": NEWS_API_KEY, # Authentication key for NewsAPI
        "pageSize": 3          # Fetch up to 3 top articles
    }

    try:
        # Create an asynchronous session for making the API call
        async with aiohttp.ClientSession() as session:
            # Make the actual GET request to the NewsAPI with a timeout
            async with session.get(NEWS_API_URL, params=params, timeout=8) as resp:
                # Parse the response as JSON
                data = await resp.json()

                # If the response status is not 200 (OK), raise an exception
                if resp.status != 200:
                    raise Exception(f"News API HTTP {resp.status}")

                # Extract the list of articles (if any)
                articles = data.get("articles", [])

                # If articles were found
                if articles:
                    # Collect the titles (headlines) of the articles
                    headlines = [a["title"] for a in articles]

                    # Calculate a confidence score based on number of results, capped at 0.95
                    confidence = min(0.7 + 0.1 * len(headlines), 0.95)

                    # Return the structured result
                    return {
                        "source": "news",                        # Source label for tracking
                        "domain": domain,                        # The company domain queried
                        "query": query,                          # The specific search string used
                        "content": "; ".join(headlines),         # Concatenated list of titles
                        "confidence": round(confidence, 2)       # Final confidence score
                    }

                else:
                    # No articles found — return fallback result
                    return {
                        "source": "news",                         # Source label
                        "domain": domain,                         # The company domain queried
                        "query": query,                           # The search term used
                        "content": "No news results found.",      # Message for no results
                        "confidence": 0.5                         # Neutral fallback confidence
                    }

    except Exception as e:
        # Catch and report any exception (timeout, network failure, etc.)
        return {
            "source": "news",                      # Source label
            "domain": domain,                      # The company domain queried
            "query": query,                        # The query that failed
            "content": f"Exception: {e}",          # Include exception message in output
            "confidence": 0.0                      # Zero confidence on failure
        }