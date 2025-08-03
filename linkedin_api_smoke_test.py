import asyncio
from aiohttp import ClientSession
from mock_sources.linkedin_api import search_linkedin
from search_pipeline import SearchPipeline

async def main():
    # 1) Direct LinkedIn API smoke test
    print("=== Direct LinkedIn Test ===")
    direct = await search_linkedin("stripe.com", "Go-To-Market strategy")
    print(direct, "\n")

    # 2) Pipeline integration test for LinkedIn source
    print("=== Pipeline search_company Test (LinkedIn + other sources) ===")
    pipeline = SearchPipeline()
    # You need to set a semaphore for safe_call to use
    pipeline.semaphore = asyncio.Semaphore(5)
    async with ClientSession() as session:
        result = await pipeline.search_company(
            domain="stripe.com",
            queries=["Go-To-Market strategy"],
            session=session
        )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
