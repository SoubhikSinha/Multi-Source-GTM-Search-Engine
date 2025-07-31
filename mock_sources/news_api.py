import asyncio
import random

async def search(query: str) -> dict:
    """
    Simulating a news API search with delay and dummy news articles.
    """
    await asyncio.sleep(random.uniform(0.3, 0.6))

    return {
        "source": "news_api",
        "query": query,
        "results": [
            {
                "company": "Stripe",
                "headline": "Stripe uses AI to detect fraud in real time",
                "link": "https://fintechnews.com/stripe-ai-fraud"
            },
            {
                "company": "Plaid",
                "headline": "Plaid integrates fraud detection AI for fintech",
                "link": "https://techcrunch.com/plaid-ai"
            }
        ]
    }
