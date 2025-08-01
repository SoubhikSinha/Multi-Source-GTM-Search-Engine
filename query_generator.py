import os
import uuid
from typing import List
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) # Initialize OpenAI client

@dataclass
class QueryStrategy: # Data class for query strategies
    id: str
    query_text: str
    source: str  # e.g., "news", "job_board", "company_site"
    relevance_score: float = 0.0

class QueryGenerator:
    def __init__(self):
        self.system_prompt = (
            "You are an expert GTM researcher. Break down the research goal into 8-12 "
            "highly targeted search queries across job boards, blogs, LinkedIn, news, etc. "
            "Assign a relevance score (0.0 - 1.0) to each query."
        )

    def generate_queries(self, goal: str) -> List[QueryStrategy]:
        prompt = f"""
        Research Goal: "{goal}"

        Generate 8-12 search queries and assign relevance scores like:
        - Query: "hiring Kubernetes engineers" (score: 0.9)
        - Query: "recent Kubernetes security incidents" (score: 0.85)

        Output as:
        1. Query text (score: X)
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            raw_text = response.choices[0].message.content
            strategies = []

            for line in raw_text.strip().split("\n"):
                if "score:" in line:
                    parts = line.split("score:") # Splitting the query text and score
                    query = parts[0].strip("1234567890. -\t") # Stripping leading numbers and dashes
                    try:
                        score = float(parts[1].strip(" )"))
                    except:
                        score = 0.5  # fallback
                    strategies.append(QueryStrategy( # Creating a QueryStrategy instance
                        id=str(uuid.uuid4()),
                        query_text=query,
                        source="mixed",
                        relevance_score=score
                    ))
            return strategies
        except Exception as e:
            print("LLM Error:", e)
            return []

    def expand_queries(self, goal: str, domain: str, weak_signals: List[str]) -> List[str]:
        weak_areas = ", ".join(weak_signals) # Joining weak signals into a string
        prompt = f"""
        The original goal is: "{goal}".
        The company domain "{domain}" has low-confidence results or sparse evidence.
        Generate 2-3 follow-up queries targeting gaps in: {weak_areas}.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You're an expert research query generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return [q.strip("1234567890. -") for q in response.choices[0].message.content.strip().split("\n") if q]
        except Exception as e:
            print("Expansion LLM Error:", e)
            return []
