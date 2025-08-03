import logging
from aiohttp import ClientSession
from dataclasses import asdict, is_dataclass
from fastapi import FastAPI, HTTPException
from models import ResearchRequest
from query_generator import QueryGenerator
from search_pipeline import SearchPipeline
from fastapi.responses import StreamingResponse
import json
import uuid
import time
import asyncio

logging.basicConfig(level=logging.INFO)

app = FastAPI()
generator = QueryGenerator()
pipeline = SearchPipeline()

@app.post("/research/batch")
async def research_batch(request: ResearchRequest):
    start = time.time()
    research_id = str(uuid.uuid4())
    logging.info(f"[START] Research ID: {research_id}, Goal: {request.research_goal}")

    strategies = generator.generate_queries(request.research_goal)
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)
    queries = [s.query_text for s in strategies]

    if not queries:
        logging.error("Query generation failed.")
        raise HTTPException(status_code=400, detail="Query generation failed.")

    depth = request.search_depth
    max_parallel = request.max_parallel_searches

    if depth == "quick":
        queries = queries[:5]
        max_parallel = max(1, max_parallel // 2)
    elif depth == "standard":
        queries = queries[:10]
    elif depth == "comprehensive":
        max_parallel = max_parallel * 2
    else:
        raise HTTPException(status_code=400, detail=f"Invalid search_depth value: {depth}")

    async with ClientSession() as session:
        try:
            results = await pipeline.batch_search(
                domains=request.company_domains,
                queries=queries,
                session=session,
                research_goal=request.research_goal,
                max_parallel=max_parallel
            )

            # Attempt dynamic query expansion for low-confidence results
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
                    result.update(retry_results[0])

            return {
                "research_id": research_id,
                "total_companies": len(request.company_domains),
                "search_strategies_generated": len(queries),
                "total_searches_executed": len(queries) * len(request.company_domains),
                "processing_time_ms": int((time.time() - start) * 1000),
                "results": results
            }
        except Exception as e:
            logging.error(f"Pipeline error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/research/stream")
async def research_stream(request: ResearchRequest):
    research_id = str(uuid.uuid4())
    strategies = generator.generate_queries(request.research_goal)
    strategies.sort(key=lambda s: s.relevance_score, reverse=True)
    queries = [s.query_text for s in strategies]

    if request.search_depth == "quick":
        queries = queries[:5]
    elif request.search_depth == "standard":
        queries = queries[:10]

    max_parallel = request.max_parallel_searches

    async def event_stream():
        yield f"event: start\ndata: Research ID {research_id} initiated\n\n"
        async with ClientSession() as session:
            for domain in request.company_domains:
                try:
                    results = await pipeline.batch_search(
                        domains=[domain],
                        queries=queries,
                        session=session,
                        research_goal=request.research_goal,
                        max_parallel=max_parallel
                    )
                    result = results[0]
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

                    yield f"data: {json.dumps(result)}\n\n"
                except Exception as e:
                    yield f"event: error\ndata: {{\"domain\": \"{domain}\", \"error\": \"{str(e)}\"}}\n\n"

        yield f"event: end\ndata: Research Complete\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")