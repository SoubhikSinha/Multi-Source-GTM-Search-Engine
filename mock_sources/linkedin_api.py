import random # For random failures (simulating real-world API call variability)
import asyncio # For network delay (simulating real-world API calls)

async def search_linkedin(domain: str, query: str) -> dict:
    await asyncio.sleep(random.uniform(0.05, 0.15)) # Simulating network latency (50-150 ms)
    if random.random() < 0.05: # 5% chance of failure to simulate real-world API variability
        raise Exception("LinkedIn API failure")
    return {
        "source": "linkedin", # Source of the data
        "domain": domain, # Domain of the company
        "query": query, # Query used for the search
        "content": f"{domain} mentioned '{query}' in LinkedIn job posts or profiles", # Content of the LinkedIn mention
        "confidence": round(random.uniform(0.6, 0.9), 2) # Confidence score for the LinkedIn mention (randomly generated between 0.6 and 0.9)
    }
