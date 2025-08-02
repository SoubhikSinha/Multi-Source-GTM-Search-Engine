from dataclasses import asdict, is_dataclass
import time
from fastapi import FastAPI  # import FastAPI to create the application
from mock_sources.job_board_api import search_jobs  # import the job board search function
from mock_sources.linkedin_api import search_linkedin  # import the LinkedIn search function
from mock_sources.news_api import search_news  # import the news search function
from mock_sources.web_scraper import scrape_website  # import the website scraping function
from models import ResearchRequest  # import the request model for validation
from query_generator import QueryGenerator  # import the query generator class
from search_pipeline import SearchPipeline, synthesize_findings, fetch_html  # import the search pipeline and helpers
import uuid  # import uuid for generating unique IDs\import time  # import time to measure execution duration
from fastapi.responses import StreamingResponse  # import StreamingResponse for SSE endpoints
import json  # import json to serialize data in event stream
import asyncio  # import asyncio for async operations
from aiohttp import ClientSession  # import ClientSession for HTTP requestsrom dataclasses import asdict, is_dataclass  # import helpers to safely serialize dataclasses

app = FastAPI()  # create a FastAPI application instance
generator = QueryGenerator()  # instantiate the query generator
pipeline = SearchPipeline()  # instantiate the search pipeline

@app.post("/research/batch")  # define POST /research/batch endpoint
async def research_batch(request: ResearchRequest):  # handler takes a validated ResearchRequest
    start = time.time()  # record start time in seconds
    # 1. generate & sort queries
    strategies = generator.generate_queries(request.research_goal)  # generate search strategies
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)  # sort by descending relevance
    queries = [s.query_text for s in strategies]  # extract the query text from strategies
    if not queries:  # if no queries generated
        return {"error": "Query generation failed."}  # return an error response

    async with ClientSession() as session:  # open an HTTP session for all requests
        # 2 do batch search
        results = await pipeline.batch_search(
            domains=request.company_domains,  # list of company domains to search
            queries=queries,  # list of generated queries
            session=session,  # pass the HTTP session
            max_parallel=request.max_parallel_searches  # limit on concurrent searches
        )

        # 3 expand & re-query for weak domains
        weak = [r["domain"] for r in results if r["confidence_score"] < request.confidence_threshold]  # domains with low confidence
        for i, r in enumerate(results):  # iterate over results
            if r["domain"] in weak:  # if this domain was weak
                exp = generator.expand_queries(request.research_goal, r["domain"], ["low confidence"])  # generate expansion queries
                if exp:  # if expansion queries exist
                    results[i] = await pipeline.search_company(r["domain"], exp, session)  # re-run search with expanded queries

    elapsed = int((time.time() - start)*1000) or 1  # calculate elapsed time in ms, fallback to 1
    qps = len(request.company_domains) * len(queries) / (elapsed / 1000)  # calculate queries per second
    m = pipeline.get_metrics()  # retrieve pipeline performance metrics
    return {
        "research_id": str(uuid.uuid4()),  # unique ID for this research run
        "total_companies": len(request.company_domains),  # count of companies processed
        "search_strategies_generated": len(queries),  # count of queries generated
        "total_searches_executed": len(request.company_domains) * len(queries) * 2,  # rough estimate of searches performed
        "processing_time_ms": elapsed,  # total time in milliseconds
        "results": results,  # the search results
        "search_performance": {
            "queries_per_second": round(qps, 2),  # formatted QPS
            "avg_latency_per_company_ms": round(elapsed / len(request.company_domains), 2),  # avg time per company
            "cache_hit_rate": m["cache_hit_rate"],  # cache performance
            "failed_requests": m["failed_requests"]  # number of failed requests
        }
    }

@app.post("/research/stream", response_class=StreamingResponse)  # define POST /research/stream endpoint
async def stream_search(request: ResearchRequest):  # handler for streaming search
    # same query-gen & sort
    strategies = generator.generate_queries(request.research_goal)  # regenerate queries
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)  # sort by relevance
    queries = [s.query_text for s in strategies]  # extract query text
    return StreamingResponse(
        event_stream(request.company_domains, queries, request.confidence_threshold),  # attach the event stream
        media_type="text/event-stream"  # set SSE media type
    )

@app.post("/research/stream-realtime", response_class=StreamingResponse)  # define POST /research/stream-realtime endpoint
async def stream_realtime(request: ResearchRequest):  # handler for real-time streaming search
    strategies = generator.generate_queries(request.research_goal)  # regenerate queries
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)  # sort by relevance
    queries = [s.query_text for s in strategies]  # extract query text
    return StreamingResponse(
        event_stream(request.company_domains, queries, request.confidence_threshold),  # attach the event stream
        media_type="text/event-stream"  # set SSE media type
    )

async def event_stream(domains, queries, threshold):  # helper generator for SSE
    async with ClientSession() as session:  # open HTTP session
        for domain in domains:  # iterate over each company domain
            # run first-pass
            result = await pipeline.search_company(domain, queries, session)  # initial search

            # if weak, expand & re-run
            if result["confidence_score"] < threshold:  # check confidence
                exp = generator.expand_queries(generator.system_prompt, domain, ["low confidence"])  # generate expansions
                if exp:  # if expansions exist
                    result = await pipeline.search_company(domain, exp, session)  # re-run search

            # serialize safely
            def safe(o):  # helper to convert dataclasses and nested structures
                if is_dataclass(o): return asdict(o)
                if isinstance(o, list): return [safe(i) for i in o]
                if isinstance(o, dict): return {k: safe(v) for k, v in o.items()}
                return o  # return primitives unchanged

            payload = safe(result)  # serialize the result
            yield f"data: {json.dumps(payload, indent=2)}\n\n"  # send SSE-formatted data
