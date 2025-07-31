import asyncio
from mock_sources import job_board, news_api, company_site

async def safe_call(source_fn, query: str, retries: int = 1) -> dict:
    for attempt in range(retries + 1):
        try:
            return await source_fn(query)
        except Exception as e:
            print(f"[WARNING] Failed on attempt {attempt + 1} for {source_fn.__name__}: {e}")
            await asyncio.sleep(0.1)
    return {
        "source": source_fn.__name__,
        "query": query,
        "results": [],
        "error": "Failed after retries"
    }

async def run_single_query(query: str) -> dict:
    results = await asyncio.gather(
        safe_call(job_board.search, query),
        safe_call(news_api.search, query),
        safe_call(company_site.search, query)
    )
    return {
        "query": query,
        "sources": results
    }

async def run_parallel_search(queries: list) -> list:
    return await asyncio.gather(*[run_single_query(q) for q in queries])
