import asyncio
import random

async def search(query: str) -> dict:
    """
    Simulating scraping a company website for relevant content.
    """
    await asyncio.sleep(random.uniform(0.1, 0.4))

    return {
        "source": "company_site",
        "query": query,
        "results": [
            {
                "company": "Square",
                "page": "https://square.com/fraud-ai",
                "content_snippet": "Our AI-based system identifies fraud patterns before they occur."
            }
        ]
    }
