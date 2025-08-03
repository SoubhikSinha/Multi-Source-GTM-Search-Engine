# smoke_test.py

import asyncio
from aiohttp import ClientSession
from search_pipeline import SearchPipeline

async def main():
    sp = SearchPipeline()

    async with ClientSession() as session:
        # Run a batch search against two domains:
        results = await sp.batch_search(
            domains=["techcrunch.com", "stripe.com"],
            queries=["AI startup funding", "Go-To-Market strategy"],
            session=session,
            max_parallel=5
        )
        for res in results:
            print(res)

if __name__ == "__main__":
    asyncio.run(main())