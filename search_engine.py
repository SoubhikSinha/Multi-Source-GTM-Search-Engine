import asyncio
from mock_sources import job_board, news_api, company_site

async def run_single_query(query: str) -> dict:
    """
    Runs one query against all sources in parallel and returns a merged result.
    """
    # Calling all 3 sources in parallel
    results = await asyncio.gather(
        job_board.search(query),
        news_api.search(query),
        company_site.search(query)
    )

    # Combining results from all sources for a single query
    combined = {
        "query": query,
        "sources": results
    }

    return combined


async def run_parallel_search(queries: list) -> list:
    """
    Accepts list of queries. Runs each query against all sources concurrently.
    Returns: List of combined results for each query.
    """
    all_results = await asyncio.gather(
        *[run_single_query(query) for query in queries]
    )
    return all_results
