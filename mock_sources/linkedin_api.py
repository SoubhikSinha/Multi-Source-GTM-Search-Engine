'''
Mock implementation of a LinkedIn search.  # Describes that this block fakes the real API for testing.
It simulates network delay and random failures like a real-world call.
'''

# import random  # Imports random to simulate occasional API failures.
# import asyncio # Imports asyncio to simulate network latency.

# async def search_linkedin(domain: str, query: str) -> dict:  # Defines an async mock function taking the company domain and search query.
#     await asyncio.sleep(random.uniform(0.05, 0.15))           # Pauses 50–150 ms to mimic network delay.
#     if random.random() < 0.05:                                # 5% chance to simulate an API failure.
#         raise Exception("LinkedIn API failure")               # Raises an exception to mimic failure.
#     return {                                                  # Returns a fake successful response dictionary.
#         "source": "linkedin",                                 # Labels the data source.
#         "domain": domain,                                     # Echoes the input domain.
#         "query": query,                                       # Echoes the input query.
#         "content": f"{domain} mentioned '{query}' in LinkedIn job posts or profiles",  # Mock content.
#         "confidence": round(random.uniform(0.6, 0.9), 2)      # Random confidence between 0.6 and 0.9.
#     }

'''
Below is the implementation of the real LinkedIn API search using Google Custom Search.
'''
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
    # Build the query parameters for the HTTP request.
    params = {
        "key": GOOGLE_API_KEY,                           # API key parameter.
        "cx": GOOGLE_CX,                                  # Custom Search Engine ID.
        "q": f"site:linkedin.com/company {domain} {query}",  # Restricts search to LinkedIn company pages matching domain and query.
        "num": 3                                         # Limit the number of results returned to 3.
    }
    try:
        # Create an asynchronous HTTP session for making requests.
        async with aiohttp.ClientSession() as session:
            # Send the GET request with a total timeout of 8 seconds.
            async with session.get(api_url, params=params, timeout=8) as resp:
                # If the response status is anything other than 200 (OK), treat as an error.
                if resp.status != 200:
                    return {
                        "source": "linkedin",               # Labels the data source.
                        "domain": domain,                   # Echoes the input domain.
                        "query": query,                     # Echoes the input query.
                        "content": f"Google CSE error: {resp.status}",  # Error message with HTTP status code.
                        "confidence": 0.0                   # Zero confidence due to failure.
                    }
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