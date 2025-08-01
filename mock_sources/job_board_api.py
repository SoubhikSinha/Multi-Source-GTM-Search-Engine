import asyncio # For network delay (simulating real-world API calls)
import random # For random failures (simulating real-world API call variability)

async def search_jobs(domain: str, query: str) -> dict: # Domain (Company Website) | Query (Search Phase)
    await asyncio.sleep(random.uniform(0.05, 0.15)) # Simulating network latency (50-150 ms)
    if random.random() < 0.05: # 5% chance of failure to simulate real-world API variability
        raise Exception("Job board API failure")
    return {
        "source": "job_board", # Source of the data
        "domain": domain, # Domain of the company
        "query": query, # Query used for the search
        "content": f"Job posting found for '{query}' on {domain}", # Content of the job posting
        "confidence": round(random.uniform(0.6, 0.9), 2) # Confidence score for the job posting (randomly generated between 0.6 and 0.9)
    }
