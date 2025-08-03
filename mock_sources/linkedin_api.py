import os                 # Provides functions for interacting with the operating system.
import aiohttp            # Enables making asynchronous HTTP requests.
from dotenv import load_dotenv  # Loads environment variables from a .env file.
import asyncio            # Provides the async framework (used if you need to simulate delays elsewhere).

load_dotenv()  # Reads key/value pairs from a .env file into environment variables.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Retrieves the Google API key for authentication.
GOOGLE_CX = os.getenv("GOOGLE_CX")            # Retrieves the Custom Search Engine ID.

async def search_linkedin(domain: str, query: str) -> dict:  # Defines the async function to fetch LinkedIn-related results.
    # Construct the Google Custom Search API URL.
    api_url = "https://www.googleapis.com/customsearch/v1"

    # Derive the LinkedIn company slug (strip off .com, etc.)
    company_slug = domain.split(".")[0]
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CX,
        "q": f"site:linkedin.com/company/{company_slug} {query}",
        "num": 3
    }
    try:
        # Create an asynchronous HTTP session for making requests.
        async with aiohttp.ClientSession() as session:
            # Send the GET request with a total timeout of 8 seconds.
            async with session.get(api_url, params=params, timeout=8) as resp:
                if resp.status != 200:
                      # Turn 429 into an exception for safe_call retry/backoff
                      raise Exception(f"LinkedIn CSE HTTP {resp.status}")
                # Parse the response body as JSON.
                data = await resp.json()
                # Extract the "items" list (search results), defaulting to an empty list if missing.
                items = data.get("items", [])
                if items:
                    # Collect the snippet from each search result.
                    snippets = [item["snippet"] for item in items]
                    # Compute a naive confidence score based on number of snippets, capped at 0.95.
                    confidence = min(0.7 + 0.1 * len(snippets), 0.95)
                    return {
                        "source": "linkedin",               # Labels the data source.
                        "domain": domain,                   # Echoes the input domain.
                        "query": query,                     # Echoes the input query.
                        "content": "; ".join(snippets),     # Join all snippets into one string.
                        "confidence": round(confidence, 2)  # Rounded confidence score.
                    }
                else:
                    # No items found in the search results.
                    return {
                        "source": "linkedin",               # Labels the data source.
                        "domain": domain,                   # Echoes the input domain.
                        "query": query,                     # Echoes the input query.
                        "content": "No LinkedIn results found.",  # Indicates no results.
                        "confidence": 0.5                   # Medium confidence in “no results” outcome.
                    }
    except Exception as e:
        # Catch any exception (network, parsing, etc.) and return a structured error response.
        return {
            "source": "linkedin",                       # Labels the data source.
            "domain": domain,                           # Echoes the input domain.
            "query": query,                             # Echoes the input query.
            "content": f"Exception: {str(e)}",          # Includes the exception message.
            "confidence": 0.0                           # Zero confidence due to the error.
        }