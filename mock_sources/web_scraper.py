import asyncio                     # Provides async support for simulated delays and concurrency.
import aiohttp                      # Enables making asynchronous HTTP requests.
from bs4 import BeautifulSoup       # HTML parser to extract text from pages.
import re                           # Regular expressions for matching query in text.

from dotenv import load_dotenv     # Loads environment variables from a .env file.
load_dotenv()                       # Reads key/value pairs from .env into os.environ.

# Define which pages to try scraping from each domain (homepage, /about, /blog)
PAGES_TO_TRY = ["/about", "/blog", ""]  # Attempt each of these paths (in order) for scraping content

# Async function to fetch a web page and return its HTML content
async def fetch_page(session, url):
    """Fetches a page and returns its HTML text, or None on failure."""
    try:
        # Attempt to make a GET request with a timeout of 5 seconds
        async with session.get(url, timeout=5) as resp:
            if resp.status == 200:               # If the response is successful (HTTP 200 OK)
                return await resp.text()         # Return the page HTML text
    except Exception:
        return None                              # If any exception occurs (network, timeout), return None
    return None                                  # If not successful (non-200 status), also return None

# Async function to scrape company site content for specific query terms
async def scrape_website(domain: str, query: str) -> dict:
    """Scrapes specified paths for the query and scores by hit count."""

    # Construct the full base URL using HTTPS scheme
    base_url = f"https://{domain}"

    # Start an HTTP session to reuse across requests
    async with aiohttp.ClientSession() as session:
        # Try each of the predefined paths (/about, /blog, homepage)
        for path in PAGES_TO_TRY:
            url = f"{base_url}{path}"                 # Construct full URL (e.g. https://stripe.com/about)
            html = await fetch_page(session, url)     # Fetch page HTML content

            if html:  # If page content was successfully fetched
                soup = BeautifulSoup(html, "html.parser")  # Parse HTML using BeautifulSoup

                # Extract all visible text, normalize whitespace, convert to lowercase for matching
                text = soup.get_text(separator=' ', strip=True).lower()
                query_lc = query.lower()               # Lowercase the query too for case-insensitive match

                # Count how many times the query string appears exactly in the page text
                hits = len(re.findall(re.escape(query_lc), text))

                if hits > 0:
                    # Confidence scoring: 0.6 base + 0.1 per hit, max capped at 0.9
                    confidence = min(0.6 + 0.1 * hits, 0.9)

                    # Return structured success response
                    return {
                        "source": "company_website",                             # Indicates this came from a scrape
                        "domain": domain,                                        # Echo original domain
                        "query": query,                                          # Echo original query
                        "content": f"Found '{query}' {hits} times in {url}",     # Describe how many matches and where
                        "confidence": round(confidence, 2)                       # Round and include confidence score
                    }

        # If no matches were found across any of the pages
        return {
            "source": "company_website",                                       # Source tag
            "domain": domain,                                                  # Domain being scanned
            "query": query,                                                    # Query term used
            "content": f"No relevant content found for '{query}' on {domain}", # Default fallback message
            "confidence": 0.4                                                  # Low confidence when no results
        }