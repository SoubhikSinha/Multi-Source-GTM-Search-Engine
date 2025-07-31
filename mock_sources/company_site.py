import asyncio
import random

async def search(query: str) -> dict:
    await asyncio.sleep(random.uniform(0.1, 0.3))
    if random.random() < 0.2:
        raise Exception(f"Rate limit hit in company_site for query: {query}")
    return {
        "source": "company_site",
        "query": query,
        "results": [
            {"company": "Square", "page": "https://square.com/fraud-ai", "content_snippet": "Our AI system identifies fraud patterns before they occur."}
        ]
    }
