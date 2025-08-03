import logging                                # For logging events and errors
from aiohttp import ClientSession             # Async HTTP client for making external requests
from dataclasses import asdict, is_dataclass  # Helpers for converting dataclasses (unused here)
from fastapi import FastAPI, HTTPException    # FastAPI classes for API and error responses
from models import ResearchRequest            # Input schema for the API
from query_generator import QueryGenerator    # Module to generate intelligent search queries
from search_pipeline import SearchPipeline    # Module to run searches in parallel
from fastapi.responses import StreamingResponse  # Used for Server-Sent Events (SSE) streaming
import json                                   # For JSON serialization
import uuid                                   # To generate unique research IDs
import time                                   # To measure execution time
import asyncio                                # To manage async concurrency

# Set up basic logging level
logging.basicConfig(level=logging.INFO)

# Initialize FastAPI app
app = FastAPI()

# Initialize generator and pipeline objects
generator = QueryGenerator()
pipeline = SearchPipeline()

# ---------------------------
# /research/batch endpoint
# ---------------------------
@app.post("/research/batch")
async def research_batch(request: ResearchRequest):
    start = time.time()                                 # Record start time
    research_id = str(uuid.uuid4())                     # Generate a unique research ID
    logging.info(f"[START] Research ID: {research_id}, Goal: {request.research_goal}")

    strategies = generator.generate_queries(request.research_goal)   # Generate initial search strategies
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)   # Sort by relevance score (high to low)
    queries = [s.query_text for s in strategies]                     # Extract just the query texts

    if not queries:                               # If no queries were generated, abort
        logging.error("Query generation failed.")
        raise HTTPException(status_code=400, detail="Query generation failed.")

    depth = request.search_depth                  # Get search depth: quick, standard, or comprehensive
    max_parallel = request.max_parallel_searches  # Initial parallel limit

    # Adjust depth and concurrency behavior
    if depth == "quick":
        queries = queries[:5]
        max_parallel = max(1, max_parallel // 2)
    elif depth == "standard":
        queries = queries[:10]
    elif depth == "comprehensive":
        max_parallel = max_parallel * 2
    else:
        raise HTTPException(status_code=400, detail=f"Invalid search_depth value: {depth}")

    # Perform async pipeline search using the generated queries
    async with ClientSession() as session:
        try:
            results = await pipeline.batch_search(
                domains=request.company_domains,
                queries=queries,
                session=session,
                research_goal=request.research_goal,
                max_parallel=max_parallel
            )

            # Retry low-confidence results with expanded queries
            for result in results:
                if result["confidence_score"] < request.confidence_threshold:
                    expanded = generator.expand_queries(
                        request.research_goal,
                        result["domain"],
                        weak_signals=[result["findings"].get("summary", "")[:100]]
                    )
                    expanded_queries = [q.query_text for q in expanded]
                    retry_results = await pipeline.batch_search(
                        domains=[result["domain"]],
                        queries=expanded_queries,
                        session=session,
                        research_goal=request.research_goal,
                        max_parallel=max_parallel
                    )
                    result.update(retry_results[0])  # Replace with expanded results

            # Final structured response
            return {
                "research_id": research_id,
                "total_companies": len(request.company_domains),
                "search_strategies_generated": len(queries),
                "total_searches_executed": len(queries) * len(request.company_domains),
                "processing_time_ms": int((time.time() - start) * 1000),
                "results": results
            }

        except Exception as e:
            # Handle internal errors gracefully
            logging.error(f"Pipeline error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


# ---------------------------
# /research/stream endpoint (SSE)
# ---------------------------
@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    research_id = str(uuid.uuid4())                       # Unique ID for the streaming session
    strategies = generator.generate_queries(request.research_goal)   # Generate queries
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)   # Sort by relevance
    queries = [s.query_text for s in strategies]                     # Extract just the text queries

    # Limit the number of queries based on search depth
    if request.search_depth == "quick":
        queries = queries[:5]
    elif request.search_depth == "standard":
        queries = queries[:10]

    max_parallel = request.max_parallel_searches  # Set max concurrency

    # Async generator for streaming results as SSE events
    async def event_stream():
        # Send initial message to client
        yield f"event: start\ndata: Research ID {research_id} initiated\n\n"

        # Open HTTP session for search
        async with ClientSession() as session:
            for domain in request.company_domains:
                try:
                    # Run batch search for a single domain
                    results = await pipeline.batch_search(
                        domains=[domain],
                        queries=queries,
                        session=session,
                        research_goal=request.research_goal,
                        max_parallel=max_parallel
                    )
                    result = results[0]

                    # Re-query low confidence domains
                    if result["confidence_score"] < request.confidence_threshold:
                        expanded = generator.expand_queries(
                            request.research_goal,
                            domain,
                            weak_signals=[result["findings"].get("summary", "")[:100]]
                        )
                        expanded_queries = [q.query_text for q in expanded]
                        retry_results = await pipeline.batch_search(
                            domains=[domain],
                            queries=expanded_queries,
                            session=session,
                            research_goal=request.research_goal,
                            max_parallel=max_parallel
                        )
                        result = retry_results[0]

                    # Stream result as JSON
                    yield f"data: {json.dumps(result)}\n\n"

                except Exception as e:
                    # Stream error if something breaks
                    yield f"event: error\ndata: {{\"domain\": \"{domain}\", \"error\": \"{str(e)}\"}}\n\n"

        # Final SSE close event
        yield f"event: end\ndata: Research Complete\n\n"

    # Return response as SSE stream
    return StreamingResponse(event_stream(), media_type="text/event-stream")