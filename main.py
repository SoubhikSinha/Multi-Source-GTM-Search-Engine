from fastapi import FastAPI # Main application instance
from models import ResearchRequest # Data models for request and response
from query_generator import QueryGenerator # Query generation logic
from search_pipeline import SearchPipeline # Search pipeline for executing queries
import uuid # For generating unique research IDs
import time # For measuring processing time
from fastapi.responses import StreamingResponse # For streaming responses
import json # For JSON serialization
import asyncio # For asynchronous operations
from aiohttp import ClientSession # For making async HTTP requests

app = FastAPI() # FastAPI application instance
generator = QueryGenerator() # Initialize the query generator
pipeline = SearchPipeline() # Initialize the search pipeline

@app.post("/research/batch")
async def research_batch(request: ResearchRequest):
    start_time = time.time() # Start timer for processing time measurement

    strategies = generator.generate_queries(request.research_goal) # Generate search strategies based on the research goal
    queries = [s.query_text for s in strategies] # Extract query texts from the generated strategies

    if not queries:
        return {
            "error": "Query generation failed. Check OpenAI setup or retry with a simpler goal."
        }

    async with ClientSession() as session:
        # Initial batch search
        search_results = await pipeline.batch_search( # Perform batch search across all domains
            domains=request.company_domains, # List of company domains to search
            queries=queries, # List of queries to execute
            session=session, # Passing the aiohttp session for async HTTP requests
            max_parallel=request.max_parallel_searches # Maximum parallel searches allowed
        )

        # Identifying low-confidence domains
        weak_domains = [r["domain"] for r in search_results if r["confidence_score"] < request.confidence_threshold]

        # Expanding queries for weak domains
        expanded_queries_per_domain = []
        for domain in weak_domains:
            expanded = generator.expand_queries(request.research_goal, domain, ["low confidence"]) # Generating follow-up queries for weak domains
            expanded_queries_per_domain.append((domain, expanded)) # Storing the domain and its expanded queries

        # Run re-queries for domains that got expansions
        requery_tasks = []
        for domain, expanded_queries in expanded_queries_per_domain:
            if expanded_queries:
                requery_tasks.append(pipeline.search_company(domain, expanded_queries, session))  # Passing the aiohttp session for async HTTP requests

        requery_results = await asyncio.gather(*requery_tasks)

        # Merge results (replace old with new if found)
        final_results = []
        updated_domains = {r["domain"] for r in requery_results if r} # Setting of domains that were updated with new results
        for result in search_results:
            if result["domain"] in updated_domains:
                replacement = next((r for r in requery_results if r["domain"] == result["domain"]), None) # Finding the replacement result
                final_results.append(replacement or result)
            else:
                final_results.append(result)

        processing_time = int((time.time() - start_time) * 1000) or 1 # Processing time in milliseconds, ensuring it's at least 1 ms
        qps = (len(request.company_domains) * len(queries)) / (processing_time / 1000) # Queries per second calculation
        metrics = pipeline.get_metrics() # Fetching search pipeline metrics

        return {
            "research_id": str(uuid.uuid4()),
            "total_companies": len(request.company_domains),
            "search_strategies_generated": len(queries),
            "total_searches_executed": len(request.company_domains) * len(queries) * 2,
            "processing_time_ms": processing_time,
            "results": final_results,
            "search_performance": {
                "queries_per_second": round(qps, 2),
                "cache_hit_rate": metrics["cache_hit_rate"],
                "failed_requests": metrics["failed_requests"]
            }
        }


async def event_stream(domains, queries):
    for domain in domains:
        results = await pipeline.search_company(domain, queries) # Performing search for each domain
        yield f"data: {json.dumps(results)}\n\n" # Streaming each result as a JSON object

@app.post("/research/stream")
async def stream_search(request: ResearchRequest):
    queries = generator.generate_queries(request.research_goal) # Generate search strategies based on the research goal
    return StreamingResponse(
        event_stream(request.company_domains, queries), # Streaming the search results
        media_type="text/event-stream" # Setting the media type for server-sent events
    )
