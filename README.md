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
<!-- List any assumptions -->

## Architecture
<!-- Describe overall architecture -->

## Agent Design (Orchestration)
<!-- Dive into agent‐level design and orchestration -->

## How it Works
<!-- Explain the workflow step by step -->

## Tech Stack
<!-- Specify languages, frameworks, libraries, etc. -->

## API Endpoints
<!-- Document each REST/GraphQL endpoint -->

## Setup and Running Locally
<!-- Local install, env vars, run commands -->

## Limitations and Future Work
<!-- Caveats, known issues, and planned improvements -->
