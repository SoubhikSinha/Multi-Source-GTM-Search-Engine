import os
import uuid
from dataclasses import dataclass
from typing import List, Optional
from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = (
    "You are a search strategy generator for a GTM research engine. "
    "Given a research goal, produce diverse, high-signal queries across sources "
    "(company sites, engineering blogs, job boards, LinkedIn, news/PR, docs, forums). "
    "Score each query 0-1 for expected relevance, and ensure coverage of different channels."
)

@dataclass
class QueryStrategy:
    id: str
    query_text: str
    source: str
    relevance_score: float

class QueryGenerator:
    def __init__(self, system_prompt: Optional[str] = None):
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    def _parse_lines(self, raw: str, min_required: int = 1) -> List[QueryStrategy]:
        """
        Parse model output lines of the form:
          query_text | source | relevance_score
        Returns a list of QueryStrategy.
        """
        strategies: List[QueryStrategy] = []
        for line in raw.strip().splitlines():
            if "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue
            q, src, score = parts
            try:
                score_f = float(score)
            except Exception:
                continue
            strategies.append(QueryStrategy(
                id=str(uuid.uuid4()),
                query_text=q,
                source=src,
                relevance_score=max(0.0, min(1.0, score_f)),
            ))
        # Fallback if parsing failed
        if len(strategies) < min_required:
            # Provide a minimal safe default so the pipeline can proceed
            strategies.append(QueryStrategy(
                id=str(uuid.uuid4()),
                query_text="site:company.com product launch press release",
                source="news_pr",
                relevance_score=0.5,
            ))
        return strategies

    def generate_queries(self, research_goal: str, n_min: int = 8, n_max: int = 12) -> List[QueryStrategy]:
        """
        Generate 8-12 diverse queries with relevance scores.
        """
        prompt = f"""
Research Goal: "{research_goal}"

Generate {n_min}-{n_max} search queries across multiple channels.
Format each line like:
query_text | source | relevance_score

Make the set diverse (company websites, job boards, blogs, LinkedIn, news/PR, docs, forums).
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content
        return self._parse_lines(raw, min_required=n_min)

    def expand_queries(self, research_goal: str, domain: str, weak_signals: List[str]) -> List[QueryStrategy]:
        """
        Dynamic query expansion: given a domain whose evidence is weak,
        generate 3-5 follow-up queries focused on that domain and signals.
        """
        weak = "; ".join([w for w in weak_signals if w]) or "No clear signals"
        prompt = f"""
Research Goal: "{research_goal}"
Domain: "{domain}"
Weak evidence/signals: {weak}

Generate 3-5 follow-up queries to strengthen confidence or fill gaps.
Focus specifically on this domain. Use varied sources (site: filters encouraged).
Format per line:
query_text | source | relevance_score
"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        raw = resp.choices[0].message.content
        return self._parse_lines(raw, min_required=3)