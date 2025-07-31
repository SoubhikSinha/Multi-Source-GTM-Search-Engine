import asyncio
import random

async def search(query: str) -> dict:
    """
    Simulating an async search on a job board with a fake delay and dummy results.
    """
    await asyncio.sleep(random.uniform(0.2, 0.5))  # Simulating network delay

    return {
        "source": "job_board",
        "query": query,
        "results": [
            {
                "company": "Stripe",
                "job_title": "AI Fraud Analyst",
                "url": "https://stripe.com/jobs/ai-fraud-analyst"
            },
            {
                "company": "Square",
                "job_title": "Machine Learning Engineer - Fraud",
                "url": "https://squareup.com/careers/ml-fraud"
            }
        ]
    }
