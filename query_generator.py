import os  # Provides functions for reading environment variables and interacting with the OS
import uuid  # Used to generate unique identifiers for each query strategy
from typing import List  # Import List for type annotations of lists
from dataclasses import dataclass  # Simplifies creation of classes used as data containers
from openai import OpenAI  # OpenAI SDK client for making requests to the API
from dotenv import load_dotenv  # Loads environment variables from a .env file into os.environ

# Load variables from .env so we can access OPENAI_API_KEY
load_dotenv()

# Initialize the OpenAI client with the API key from environment variables
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@dataclass  # Decorator to auto-generate init, repr, and other methods
class QueryStrategy:  # Defines a simple container for one search query and its metadata
    id: str  # Unique identifier for this strategy instance
    query_text: str  # The actual text of the search query
    source: str  # Label for where this query targets (e.g., "news", "job_board")
    relevance_score: float = 0.0  # Score (0.0–1.0) indicating how relevant the query is

class QueryGenerator:  # Encapsulates logic for creating and expanding search queries
    def __init__(self):  # Constructor runs once when QueryGenerator() is called
        # System prompt guiding the LLM to produce 8–12 targeted queries with scores
        self.system_prompt = (
            "You are an expert GTM researcher. Break down the research goal into 8-12 "
            "highly targeted search queries across job boards, blogs, LinkedIn, news, etc. "
            "Assign a relevance score (0.0 - 1.0) to each query."
        )

    def generate_queries(self, goal: str) -> List[QueryStrategy]:  # Creates initial queries
        # Build the user prompt including the research goal and examples of desired output
        prompt = f"""
        Research Goal: "{goal}"

        Generate 8-12 search queries and assign relevance scores like:
        - Query: "hiring Kubernetes engineers" (score: 0.9)
        - Query: "recent Kubernetes security incidents" (score: 0.85)

        Output as:
        1. Query text (score: X)
        """
        try:
            # Call the OpenAI chat completion endpoint with system and user messages
            response = client.chat.completions.create(
                model="gpt-4",  # LLM model to use for generating queries
                messages=[
                    {"role": "system", "content": self.system_prompt},  # System instructions
                    {"role": "user", "content": prompt}  # The specific research goal prompt
                ],
                temperature=0.7  # Controls randomness: 0.7 is moderately creative
            )
            # Extract the raw text output from the first (and only) choice
            raw_text = response.choices[0].message.content
            strategies: List[QueryStrategy] = []  # Prepare an empty list to hold results

            # Split the LLM output by lines and parse any line containing "score:"
            for line in raw_text.strip().split("\n"):
                if "score:" in line:
                    # Separate query text from the numeric score
                    parts = line.split("score:")
                    # Clean up the query text by removing list numbers/dashes/spaces
                    query = parts[0].strip("1234567890. -\t")
                    try:
                        # Convert the score part to a float
                        score = float(parts[1].strip(" )"))
                    except ValueError:
                        score = 0.5  # Default fallback if conversion fails
                    # Create a QueryStrategy object and add to the list
                    strategies.append(QueryStrategy(
                        id=str(uuid.uuid4()),  # Generate a unique ID
                        query_text=query,
                        source="mixed",  # Mark source as mixed for generic use
                        relevance_score=score
                    ))
            return strategies  # Return the list of structured query strategies
        except Exception as e:
            # Log any error from the LLM call and return an empty list
            print("LLM Error:", e)
            return []

    def expand_queries(self, goal: str, domain: str, weak_signals: List[str]) -> List[str]:  # Generates follow-up queries
        # Combine weak signal keywords into a comma-separated string
        weak_areas = ", ".join(weak_signals)
        # Prompt for follow-up queries based on low-confidence areas
        prompt = f"""
        The original goal is: "{goal}".
        The company domain "{domain}" has low-confidence results or sparse evidence.
        Generate 2-3 follow-up queries targeting gaps in: {weak_areas}.
        """
        try:
            # Call the OpenAI chat completion endpoint to expand queries
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You're an expert research query generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            # Split output lines, clean each line, and filter out empty entries
            return [q.strip("1234567890. -") for q in 
                    response.choices[0].message.content.strip().split("\n") if q]
        except Exception as e:
            # Log expansion errors and return an empty list
            print("Expansion LLM Error:", e)
            return []