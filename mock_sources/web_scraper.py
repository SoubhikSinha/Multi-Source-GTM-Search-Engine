import asyncio # For network delay (simulating real-world API calls)
import random # For random failures (simulating real-world API call variability)

async def scrape_website(domain: str, query: str) -> dict:
    await asyncio.sleep(random.uniform(0.1, 0.3))  # simulate latency

    if random.random() < 0.05: # 5% chance of failure to simulate real-world API variability
        raise Exception("Web scraping failed")

    return {
        "source": "company_website", # Source of the data
        "domain": domain, # Domain of the company
        "query": query, # Query used for the search
        "content": f"Scraped content mentioning '{query}' on {domain}/about or /blog", # Content of the scraped page
        "confidence": round(random.uniform(0.65, 0.9), 2) # Confidence score for the scraped content (randomly generated between 0.65 and 0.9)
    }
