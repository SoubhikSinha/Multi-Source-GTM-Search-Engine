import os                              # For reading environment variables like API keys
import uuid                            # Used to generate unique IDs for each query strategy
from dataclasses import dataclass      # Simplifies creation of simple data classes
from typing import List, Optional      # Type hints for better code clarity
from openai import OpenAI              # OpenAI SDK client for calling chat completion APIs

from dotenv import load_dotenv         # Loads environment variables from a .env file
load_dotenv()                          # Makes variables like OPENAI_API_KEY available via os.getenv

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")           # Reads the OpenAI API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))   # Initializes the OpenAI API client with the key

# Default system prompt to instruct the LLM to generate diverse, high-quality queries
SYSTEM_PROMPT = (
    "You are a search strategy generator for a GTM research engine. "
    "Given a research goal, produce diverse, high-signal queries across sources "
    "(company sites, engineering blogs, job boards, LinkedIn, news/PR, docs, forums). "
    "Score each query 0-1 for expected relevance, and ensure coverage of different channels."
)

# A data class to represent one generated search query strategy
@dataclass
class QueryStrategy:
    id: str               # Unique identifier for the strategy
    query_text: str       # The actual search string to be used
    source: str           # The source/channel (e.g., LinkedIn, blog, news)
    relevance_score: float  # Score between 0.0 and 1.0 indicating query importance or accuracy

# Main class responsible for query generation and dynamic expansion
class QueryGenerator:
    def __init__(self, system_prompt: Optional[str] = None):
        # Allows overriding the default system prompt if needed
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    # Internal method to parse LLM output lines into QueryStrategy objects
    def _parse_lines(self, raw: str, min_required: int = 1) -> List[QueryStrategy]:
        """
        Parse model output lines of the form:
          query_text | source | relevance_score
        Returns a list of QueryStrategy.
        """
        strategies: List[QueryStrategy] = []

        # Split raw text into lines and parse each line into a QueryStrategy
        for line in raw.strip().splitlines():
            if "|" not in line:         # Skip lines that do not contain a pipe separator
                continue
            parts = [p.strip() for p in line.split("|")]  # Split and strip whitespace
            if len(parts) != 3:         # Expect exactly 3 parts
                continue
            q, src, score = parts
            try:
                score_f = float(score)  # Try converting score to float
            except Exception:
                continue
            # Append the parsed query strategy to the list
            strategies.append(QueryStrategy(
                id=str(uuid.uuid4()),
                query_text=q,
                source=src,
                relevance_score=max(0.0, min(1.0, score_f)),  # Clamp score to [0.0, 1.0]
            ))

        # If too few strategies are parsed, fallback with a default query
        if len(strategies) < min_required:
            strategies.append(QueryStrategy(
                id=str(uuid.uuid4()),
                query_text="site:company.com product launch press release",
                source="news_pr",
                relevance_score=0.5,
            ))
        return strategies

    # Public method to generate initial query strategies for a given research goal
    def generate_queries(self, research_goal: str, n_min: int = 8, n_max: int = 12) -> List[QueryStrategy]:
        """
        Generate 8-12 diverse queries with relevance scores.
        """
        # Prompt sent to the LLM
        prompt = f"""
Research Goal: "{research_goal}"

Generate {n_min}-{n_max} search queries across multiple channels.
Format each line like:
query_text | source | relevance_score

Make the set diverse (company websites, job boards, blogs, LinkedIn, news/PR, docs, forums).
"""
        # Call OpenAI's chat model with system and user messages
        resp = client.chat.completions.create(
            model="gpt-4o-mini",                   # Use GPT-4o Mini model for balance of speed and quality
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,                        # Low temperature for stable, consistent outputs
        )
        raw = resp.choices[0].message.content       # Extract the raw text from the first message
        return self._parse_lines(raw, min_required=n_min)  # Convert to structured strategies

    # Public method to expand queries dynamically when confidence is low
    def expand_queries(self, research_goal: str, domain: str, weak_signals: List[str]) -> List[QueryStrategy]:
        """
        Dynamic query expansion: given a domain whose evidence is weak,
        generate 3-5 follow-up queries focused on that domain and signals.
        """
        # Join all weak signals into a single string; fallback to "No clear signals"
        weak = "; ".join([w for w in weak_signals if w]) or "No clear signals"

        # Prompt crafted to refine the original goal with weak areas
        prompt = f"""
Research Goal: "{research_goal}"
Domain: "{domain}"
Weak evidence/signals: {weak}

Generate 3-5 follow-up queries to strengthen confidence or fill gaps.
Focus specifically on this domain. Use varied sources (site: filters encouraged).
Format per line:
query_text | source | relevance_score
"""
        # Call OpenAI API to generate expansion queries
        resp = client.chat.completions.create(
            model="gpt-4o-mini",                   # Use GPT-4o Mini model again
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content       # Extract output text
        return self._parse_lines(raw, min_required=3)  # Convert to list of strategies