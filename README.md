# Multi-Source GTM (Go-To-Market) Search Engine

## Acknowledgements
This project was built as part of a technical challenge from **[OpenFunnel](https://www.ycombinator.com/companies/openfunnel)**, simulating a high-stakes engineering scenario. It draws deep inspiration from Anthropic’s [_Building Effective Agents_](https://www.anthropic.com/engineering/building-effective-agents), leveraging modular AI patterns like **Evaluator, Refiner**, and **Synthesizer agents.** Core tools such as **OpenAI APIs, NewsAPI**, and **FastAPI (with async orchestration, caching, and streaming)** powered the system’s intelligence and scalability. Sincere thanks to the challenge creators for a spec that encouraged real-world design thinking and thoughtful system architecture.

<br>

## Table of Contents

- [Overview](#overview)
- [Assumptions](#assumptions)
- [Architecture](#architecture)
- [Agent Design (Orchestration)](#agent-design-orchestration)
- [How it Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [API Endpoints](#api-endpoints)
- [Setup and Running Locally](#setup-and-running-locally)
- [Limitations and Future Work](#limitations-and-future-work)

<br>


## Overview
**The Multi-Source GTM Research Engine** is a fully asynchronous, LLM-powered research system designed to uncover nuanced, multi-channel intelligence about companies — including signs of technology usage, hiring intent, product expansion, and recent security events.

<br>

It accepts a single research goal and a list of company domains, then autonomously orchestrates:

-   **Query generation** across diverse surfaces (news, job boards, blogs, forums, LinkedIn, etc.),
    
-   **Parallel data collection** from real-time and cached sources,
    
-   **Result evaluation**, identifying weak signals and gaps,
    
-   **Query refinement**, and
    
-   **Final synthesis** into structured, confidence-scored insights.
    

  

The engine is modular, resilient, and inspired by agentic design principles such as those outlined in Anthropic’s _Building Effective Agents_. It simulates a team of virtual analysts working in harmony — each focused on a precise role: strategist, executor, evaluator, refiner, and summarizer.

<br>

This is not just a tool for retrieving information — it’s a **cognitive loop system** that mimics the judgment and feedback-driven refinement of a skilled human analyst, packaged into a scalable and inspectable backend service.

<br>


## Assumptions
### **🧱 System & Language**
-   **Python 3.10+** is used, enabling modern type hinting (Literal, dataclass, etc.).
-   **FastAPI** is the framework of choice for async HTTP serving.
-   **aiohttp** is used instead of requests to support non-blocking I/O for all outbound calls.
-   **Environment configuration** is handled via .env files and dotenv.

### **🔐 Authentication & API Keys**
-   API keys for **OpenAI**, **Google Custom Search**, and **NewsAPI** are securely accessed through os.getenv (dotenv).    
-   No access control/authentication layer is implemented at the FastAPI endpoint level (assumed to be behind internal auth or gateway in production).

### **🌐 Input & Domain Assumptions**
-   **Input company_domains** is assumed to be a list of valid, reachable domains (no verification or sanitization done).
-   It is assumed that:
    -   Each domain has a meaningful homepage or /about, /blog page.
    -   Each domain is indexed by Google CSE.    
    -   Each domain may appear in LinkedIn or News sources.

### **📡 External Sources**
-   **Real API integrations** include:  
    -   Google CSE (customsearch/v1)    
    -   NewsAPI (/v2/everything)     
    -   LinkedIn (queried via Google site search site:linkedin.com/company/...)
-   **No crawling** beyond the homepage and 2 subpages is attempted.    
-   **Mocked fallback queries** are used when OpenAI responses cannot be parsed.

### **🔁 Query Generation**
-   Queries are generated via **OpenAI Chat API**, guided by a system prompt with structured instructions.
-   A **fallback query** is inserted if LLM output is insufficient or unparsable.
-   Relevance scores from 0.0 to 1.0 are assumed to be meaningful and used for sorting/pruning.
-   The expand_queries method is only triggered when confidence falls below a threshold (e.g., 0.8).

### **🤖 Agent Pattern (Inferred / Optional)**
-   The architecture implicitly follows an **agentic orchestration pattern**:
    -   Strategy agent (Query Generator)
    -   Execution agent (SearchPipeline) 
    -   Evaluator agent (confidence scoring)
    -   Refiner agent (dynamic query re-invocation)
    -   Synthesizer agent (OpenAI summarizer)

### **⚙️ Performance & Scaling**
-   All outbound calls (LinkedIn, NewsAPI, Google, Website) are made **in parallel via asyncio.gather()**.
-   The system enforces **concurrency limits** using asyncio.Semaphore(max_parallel).
-   **Timeouts** are set for every external call (8–10 seconds).
-   No persistent database (e.g., PostgreSQL) is used — only an **in-memory cache** is implemented (SimpleCache).
-   No pagination or scroll-based APIs are used — all sources fetch a max of 3 results per query.

### **💡 Scoring & Confidence Logic**
-   Confidence scores are **naively computed** per module:
    -   Based on number of results/snippets.    
    -   Capped at 0.95.
    -   Floor values (e.g., 0.4–0.5) used when no signal is found.
-   Final confidence per company is **averaged** across successful modules only.    
-   Results with exceptions are excluded from synthesis unless expanded queries succeed.

### **🧪 Error Handling & Recovery**
-   All external calls are wrapped in safe_call() with:
    -   Retry mechanism (up to 2 retries).
    -   Timeout handling.
    -   Graceful degradation to zero-confidence fallback.
-   Failed modules (e.g., LinkedIn API fails) do **not break the pipeline**.

### **🔄 SSE/Streaming**
-   SSE is **implemented manually** via StreamingResponse (no WebSocket used).
-   Stream sends:
    -   start → per-domain result → end events.
-   Parallelism is per-domain in streaming; each company is handled serially within the stream.

### **📈 Observability & Metrics**
-   Logging is enabled via logging.info and logging.error.
-   get_metrics() provides stats on:
    -   Cache hit rate
    -   Failed requests
    -   Total API calls
-   No external logging, tracing, or metrics pipeline is integrated (assumed to be internalized in prod).

### **🛠️ Other**
-   No frontend included; assumed to be **headless API** backend.
-   Designed to be deployable in **lightweight environments** (e.g., Docker, single-node testing).
-   Not built for multi-tenant access, but easy to refactor for that.

<br>

## Architecture
The **Multi-Source GTM Research Engine** is architected as a modular, agent-inspired async pipeline that combines LLM reasoning, multi-channel evidence gathering, and real-time synthesis. The system balances **scalability**, **modularity**, and **fault tolerance** using the following layered architecture:

 - ### Key Agent Components
	 | Agent Role             | Responsibility                                                                |
	|------------------------|-------------------------------------------------------------------------------|
	| QueryStrategyAgent     | Generates 8–12 diverse, high-signal queries across multiple sources           |
	| ExecutionAgent         | Runs all queries concurrently across APIs, CSE, and scrapers with backoff logic |
	| EvaluatorAgent         | Scores confidence, checks evidence sufficiency                                |
	| RefinerAgent           | Iteratively refines queries for domains with poor coverage                    |
	| SynthesisAgent         | Merges, deduplicates, and synthesizes insights from all evidence             |
 
 - ### **Core Architectural Features**
	 -   **Async First** : Built entirely on Python’s asyncio + aiohttp, with streaming support, timeouts, and semaphores for controlled parallelism.
	-   **LLM-Driven Strategy** : GPT-4o generates queries, expands them intelligently, and synthesizes final summaries—mimicking a human research analyst.
	-   **Tool-Agnostic Search Modules** : Each data source (News, LinkedIn, Website, Web Search) is encapsulated as a plug-and-play async module—easy to extend or replace.
	-   **Smart Retry and Backoff** : Implements retry logic, confidence-based re-query, and exception-aware fault tolerance at every stage.
	-   **In-Memory Caching** : Lightweight SimpleCache system prevents duplicate API calls, supports quick prototyping, and logs hit-rates.
	-   **Streaming Support** : Built-in /research/stream endpoint provides real-time Server-Sent Events (SSE) for frontend integration or dashboards.
 
 - ### **Design Principles Followed**
	 - **Separation of Concerns**: Each module/agent has a single responsibility.
	 -   **Agentic Design**: Loosely coupled, feedback-loop driven agents as per Anthropic’s Effective Agents principles.   
	 -   **Fail-Soft Philosophy**: All errors gracefully degrade to structured fallback responses.   
	 -   **Scalability First**: Supports dozens of domains and 80+ searches in parallel with dynamic throttling.
 
 - ### **Example Flow (for: “Find companies using Kubernetes in production with recent security incidents”)**
	> **Step 1**: GPT-4o generates queries like:
	 - > site:linkedin.com kubernetes security engineer
	 - > site:company.com/blog kubernetes deployment
     - > devops job site:company.com
    > **Step 2**: All queries run in parallel across:
	 - > NewsAPI, LinkedIn, CSE, Web Scraping
	> **Step 3**: Evidence scored, weak results flagged
	> **Step 4**: Weak evidence → Refined queries → Retry
	> **Step 5**: Findings synthesized via LLM (JSON output)

<br>

This architecture enables fast, adaptive, and scalable GTM research—ideal for intelligence gathering, sales strategy, or product scouting at enterprise scale.

<br>

## Agent Design (Orchestration)
The system leverages an **agentic architecture** inspired by Anthropic’s “Effective Agents” framework to orchestrate complex research tasks. Instead of relying on monolithic logic, we structure the workflow into **modular AI agents**, each with a narrow, specialized responsibility. These agents collaborate through feedback loops, retries, and strategic delegation — enabling **dynamic, intelligent, and high-coverage research** across companies and data sources.

 - ### **Core Agent Roles**
	 | Agent Name                   | Purpose                                                                                                                                       | Key Tools / Logic                                 |
	|------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------|
	| **QueryStrategyAgent**       | Breaks down the user’s research goal into 8–12 diverse, high-signal search queries across sources like LinkedIn, job boards, blogs, and news. | `OpenAI GPT-4o`<br>`Prompt Templates`             |
	| **ExecutionAgent**           | Executes queries across multiple domains and sources in parallel, applying retry logic and honoring concurrency limits.                       | `Async I/O`<br>`Semaphores`<br>`Circuit Breakers` |
	| **EvaluatorAgent**           | Reviews raw search results, scoring confidence and detecting gaps in coverage (e.g., missing signals, weak evidence).                         | `Evidence Count`<br>`Scoring Logic`               |
	| **RefinerAgent**             | For low-confidence companies, generates targeted follow-up queries using weak-signal feedback to improve depth and precision.                  | `LLM Feedback Loop`<br>`Query Expansion`          |
	| **SynthesisAgent**           | Aggregates and deduplicates evidence across all sources, then generates a concise synthesis aligned with the research goal.                    | `GPT-4 LLM Summarization`                         |
	| **ReQueryAgent** *(Optional)* | Triggers a second search wave if critical signals are missing or confidence remains low after retries.                                        | `Query Budget`<br>`Loop Guard`                    |

<br>

 - ### **Agent Collaboration Workflow**
	 - **QueryStrategyAgent**
	   - Transforms the user goal into 8–12 cross-channel queries  
	   - Ensures diversity across sources (e.g., blogs, PR, LinkedIn, docs)
	- **ExecutionAgent**
	   - Executes all queries in parallel across company domains using async semaphores  
	   - Sources include NewsAPI, company website scraping, LinkedIn, and Google Custom Search
    - **EvaluatorAgent**
	   - Analyzes results per company  
	   - Flags domains with:  
		   - Low confidence score (e.g., < 0.7)  
		   - Sparse evidence (e.g., only 1 source)
    - **RefinerAgent**
	   - For flagged companies, generates follow-up queries using weak-signal cues (e.g., blog post titles, job listings)  
	   - Focuses explicitly on the domain with refined `site:`-style search prompts
	- **ExecutionAgent (Retry)**
	   - Re-executes the refined queries for flagged companies  
	   - Merges improved results with original evidence
	- **SynthesisAgent**
	   - Deduplicates and synthesizes multi-source evidence  
	   - Returns structured insights (`summary`, `signals_found`, `evidence_count`)
 
 - ### **Design Principles**
	 -   **Agent Modularity**: Each agent is logically decoupled and independently testable. Components can be swapped or extended without breaking the pipeline.
	-   **Feedback Loops**: Evaluator → Refiner → Execution forms a resilient loop for handling weak or incomplete data.
	-   **Asynchronous Parallelism**: High-throughput querying enabled via asyncio semaphores and streaming support (SSE).
	-   **Confidence-Driven Decision Making**: Agents make choices (e.g., whether to retry, refine) based on dynamic scoring thresholds.
	-   **LLM as Reasoning Core**: GPT-4 powers both initial strategy generation and final synthesis, using tailored prompts per agent.
	-   **Capped Iteration**: Each domain is bounded by a configurable query budget to prevent runaway retries or infinite loops.

- ### **Inspired by Anthropic’s Engineering Patterns**
	This design follows best practices outlined in Anthropic’s “Building Effective Agents” including:
	-   **Evaluator-Optimizer Loop**: Confidence-driven refinement cycles
	-   **Orchestrator-Workers**: Strategy → Execution → Evaluation → Retry → Synthesis
	-   **Augmented LLM**: Each LLM call is enriched with tools (news, web, LinkedIn) and memory (via caching)

<br>

## How it Works
This system transforms a high-level research goal into structured, evidence-backed insights by orchestrating a pipeline of intelligent agents and async operations across multiple data sources.

- ### **🧾 User Input**
	A user provides:
	-   **Research Goal** — Natural language intent (e.g., _“Find companies using Kubernetes with recent security incidents”_)
	-   **Company Domains** — A list of domains (e.g., stripe.com, datadog.com)
	-   **Search Depth** — Controls query volume *(quick, standard, comprehensive)*
	-   **Confidence Threshold** — Minimum acceptable evidence confidence
	-   **Max Parallelism** — Concurrency budget for async processing

- ### **🧠 Query Generation**
	The QueryStrategyAgent converts the research goal into **8–12 high-signal search queries** using OpenAI. Queries target various information channels:
	-   🔍 Company blogs
	-   📰 News articles
	-   👥 LinkedIn posts

	Each query is scored for **expected relevance**, ensuring diverse and targeted coverage.

- ### **🔄 Parallel Execution**
	The ExecutionAgent performs **parallelized searches** using asyncio semaphores. Each query runs across all domains with rate-limited, source-specific integrations:
		
	| Source       | Method                                        |
	|--------------|-----------------------------------------------|
	| News API     | NewsAPI search (sorted by relevance)          |
	| Company Site | BeautifulSoup scraping (`/`, `/blog`, `/about`) |
	| LinkedIn     | Simulated API call (mock or real)             |
	| Web Snippets | Google Custom Search API                      |

Search results are collected as **structured evidence objects**.

- ### **✅ Evaluation & Gaps**
	The EvaluatorAgent computes:
	-   **Confidence Score** — Averaged across all evidence sources per company
	-   **Evidence Sources** — Total distinct hits (minimizing source redundancy)
	
	Companies with **insufficient confidence** or **weak evidence** are flagged for further investigation.

- ### **🔁 Query Refinement (if needed)**
	The RefinerAgent uses **weak signals** (e.g., blog snippet, job description fragments) to craft **targeted follow-up queries**, like:
	> “site:stripe.com/careers kubernetes security engineer”

	These refined queries are re-executed and merged into the original evidence set.

- ### **🧾 Synthesis**
	The SynthesisAgent aggregates all collected evidence for a domain and produces:
	```bash
		{
			"summary": "Stripe appears to use Kubernetes in production...",
			"signals_found": ["job posting for k8s", "blog on container orchestration"],
			"evidence_count": 5
		}
	```

	This synthesis is powered by a **structured LLM prompt** tuned for concise, factual extraction.

- ### **📦 Final Output**
	The response includes:
	-   research_id: UUID trace
	-   total_companies: Domains processed
	-   search_strategies_generated: Query count
	-   total_searches_executed: Domain × Query total
	-   processing_time_ms: Wall time
	-   results: List of structured findings per company

- ### **🧵 Optional: Real-Time Streaming**
	Via the /research/stream endpoint, results are streamed using **Server-Sent Events (SSE)**. Each company’s insight is pushed as soon as it’s ready — ideal for dashboards or long-running investigations.

- ### **Under the Hood**
	-   **Concurrency:** Controlled using asyncio.Semaphore
	-   **Retries & Timeout Handling:** Built-in for flaky APIs
	-   **Caching:** In-memory SimpleCache with hash-based deduplication
	-   **Resilience:** Supports query re-planning and fallback logic
	-   **Observability:** Logs start/end times, error traces, cache hits, and agent decisions

<br>

## Tech Stack
<!-- Specify languages, frameworks, libraries, etc. -->

## API Endpoints
<!-- Document each REST/GraphQL endpoint -->

## Setup and Running Locally
<!-- Local install, env vars, run commands -->

## Limitations and Future Work
<!-- Caveats, known issues, and planned improvements -->
