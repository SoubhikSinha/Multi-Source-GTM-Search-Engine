import os                 # Provides functions for interacting with the operating system.
import aiohttp            # Enables making asynchronous HTTP requests.
from dotenv import load_dotenv  # Loads environment variables from a .env file.
import asyncio            # Provides the async framework (used if you need to simulate delays elsewhere).

# Load environment variables from a .env file into the OS environment
load_dotenv()

# Retrieve Google API credentials from environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Google API key for making authenticated requests
GOOGLE_CX = os.getenv("GOOGLE_CX")            # Google Custom Search Engine ID (CSE context)

# Define an async function to search for LinkedIn company page content using Google Custom Search
async def search_linkedin(domain: str, query: str) -> dict:
    # Google Custom Search endpoint (Root URL)
    api_url = "https://www.googleapis.com/customsearch/v1"

    # Extract a simplified version of the domain to form the LinkedIn company slug
    company_slug = domain.split(".")[0]  # Example: 'stripe.com' becomes 'stripe'

    # Parameters for the GET request to Google CSE
    params = {
        "key": GOOGLE_API_KEY,                          # Auth key
        "cx": GOOGLE_CX,                                # Custom search engine context
        "q": f"site:linkedin.com/company/{company_slug} {query}",  # Build search query targeting LinkedIn company pages
        "num": 3                                         # Limit results to top 3
    }

    try:
        # Create an aiohttp client session for async HTTP requests
        async with aiohttp.ClientSession() as session:
            # Send GET request to Google CSE (Custom Search Engine) API with a timeout of 8 seconds
            async with session.get(api_url, params=params, timeout=8) as resp:
                # If response status is not 200 (OK), raise exception
                if resp.status != 200:
                    raise Exception(f"LinkedIn CSE HTTP {resp.status}")

                # Parse JSON body of the HTTP response
                data = await resp.json()

                # Extract the 'items' field which holds the actual search results
                items = data.get("items", [])

                # If there are search result items returned
                if items:
                    # Extract snippets (short text previews) from each item
                    snippets = [item["snippet"] for item in items]

                    # Assign a confidence score based on number of snippets, capped at 0.95
                    confidence = min(0.7 + 0.1 * len(snippets), 0.95)

                    # Return structured result dictionary
                    return {
                        "source": "linkedin",               # Data source label
                        "domain": domain,                   # Domain being searched
                        "query": query,                     # Search query used
                        "content": "; ".join(snippets),     # Combine snippets into one string
                        "confidence": round(confidence, 2)  # Confidence score rounded to 2 decimal places
                    }

                else:
                    # No results found for this query
                    return {
                        "source": "linkedin",                     # Data source label
                        "domain": domain,                         # Domain being searched
                        "query": query,                           # Search query used
                        "content": "No LinkedIn results found.",  # Placeholder content for no results
                        "confidence": 0.5                         # Assign a default medium confidence
                    }

    except Exception as e:
        # If any error occurs during request/response handling, return a fallback result
        return {
            "source": "linkedin",                      # Data source label
            "domain": domain,                          # Domain being searched
            "query": query,                            # Search query used
            "content": f"Exception: {str(e)}",         # Include the exception message in the response
            "confidence": 0.0                          # Assign 0 confidence due to failure
        }