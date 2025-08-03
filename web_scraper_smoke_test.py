# smoke_test_web_scraper.py

import asyncio
from aiohttp import ClientSession
from mock_sources.web_scraper import scrape_website
from search_pipeline import SearchPipeline

async def main():
    # 1) Directly test scrape_website on a known domain
    print("=== Direct scraper test ===")
    direct = await scrape_website("openai.com", "research")
    print(direct, "\n")

    # 2) Test it through your pipeline for one domain + one query
    print("=== Pipeline search_company test ===")
    pipeline = SearchPipeline()
    async with ClientSession() as session:
        result = await pipeline.search_company(
            domain="openai.com",
            queries=["research"],
            session=session
        )
    print(result, "\n")

    # 3) Test a batch search (multiple domains & queries)
    print("=== Pipeline batch_search test ===")
    pipeline = SearchPipeline()
    async with ClientSession() as session:
        batch = await pipeline.batch_search(
            domains=["openai.com", "example.com"],
            queries=["research", "blog"],
            session=session,
            max_parallel=2
        )
    for item in batch:
        print(item)

if __name__ == "__main__":
    asyncio.run(main())
