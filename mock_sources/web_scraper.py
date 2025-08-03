import asyncio                     # Provides async support for simulated delays and concurrency.
import aiohttp                      # Enables making asynchronous HTTP requests.
from bs4 import BeautifulSoup       # HTML parser to extract text from pages.
import re                           # Regular expressions for matching query in text.

from dotenv import load_dotenv     # Loads environment variables from a .env file.
load_dotenv()                       # Reads key/value pairs from .env into os.environ.

PAGES_TO_TRY = ["/about", "/blog", ""]  # List of URL paths to attempt scraping (homepage if empty path).

async def fetch_page(session, url):
    """Fetches a page and returns its HTML text, or None on failure."""
    try:
        async with session.get(url, timeout=5) as resp:  # Send GET with a 5-second timeout.
            if resp.status == 200:                        # Only proceed if HTTP status is OK.
                return await resp.text()                  # Return the raw HTML content.
    except Exception:
        return None                                      # On any exception, return None.
    return None                                          # If status not 200, return None.

async def scrape_website(domain: str, query: str) -> dict:
    """Scrapes specified paths for the query and scores by hit count."""
    base_url = f"https://{domain}"                    # Construct the base URL from the domain.
    async with aiohttp.ClientSession() as session:    # Open an HTTP session for requests.
        for path in PAGES_TO_TRY:                     # Loop through each page path to try.
            url = f"{base_url}{path}"                 # Build the full URL (e.g., https://example.com/about).
            html = await fetch_page(session, url)    # Fetch HTML content of the page.
            if html:                                 # Proceed only if fetch_page returned HTML.
                soup = BeautifulSoup(html, "html.parser")  # Parse HTML into a BeautifulSoup object.
                # Extract all text, join with spaces, strip extra whitespace, convert to lowercase.
                text = soup.get_text(separator=' ', strip=True).lower()
                query_lc = query.lower()             # Lowercase the query for case-insensitive search.
                # Count occurrences of the exact query string in the page text.
                hits = len(re.findall(re.escape(query_lc), text))
                if hits > 0:                          # If at least one hit is found...
                    # Naive confidence: base 0.6 + 0.1 per hit, but no more than 0.9.
                    confidence = min(0.6 + 0.1 * hits, 0.9)
                    return {
                        "source": "company_website",   # Labels the data source.
                        "domain": domain,             # Echoes the input domain.
                        "query": query,               # Echoes the input query.
                        "content": f"Found '{query}' {hits} times in {url}",  # Summarizes where hits occurred.
                        "confidence": round(confidence, 2)  # Rounded confidence score.
                    }
        # If loop completes with no hits found on any page:
        return {
            "source": "company_website",               # Labels the data source.
            "domain": domain,                         # Echoes the input domain.
            "query": query,                           # Echoes the input query.
            "content": f"No relevant content found for '{query}' on {domain}",  # Indicates no matches.
            "confidence": 0.4                         # Lower confidence when nothing is found.
        }
