import asyncio
import random

async def search(query: str) -> dict:
    await asyncio.sleep(random.uniform(0.2, 0.4))
    if random.random() < 0.2:
        raise Exception(f"Rate limit hit in job_board for query: {query}")
    return {
        "source": "job_board",
        "query": query,
        "results": [
            {"company": "Stripe", "job_title": "AI Fraud Analyst", "url": "https://stripe.com/jobs/ai-fraud-analyst"},
            {"company": "Square", "job_title": "Machine Learning Engineer - Fraud", "url": "https://squareup.com/careers/ml-fraud"}
        ]
    }
