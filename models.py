from pydantic import BaseModel  # Base class for data validation and settings management
from typing import List, Dict, Optional, Literal  # Generic types for static type hints

# -------------------------------
# Input schema for POST requests
# -------------------------------
class ResearchRequest(BaseModel):  # Defines the expected shape of a /research request payload
    research_goal: str  # A natural language goal (e.g., "Find fintech companies using AI for fraud detection")
    company_domains: List[str]  # List of domains to research (e.g., ["stripe.com", "square.com"])
    search_depth: Literal["quick", "standard", "comprehensive"]  # How deep to search (affects query count & parallelism)
    max_parallel_searches: int = 10  # Controls concurrency of async pipeline (default = 10)
    confidence_threshold: float = 0.8  # Only include results with this minimum confidence (default = 0.8)

# -------------------------------
# Output schema for each domain
# -------------------------------
class SearchResult(BaseModel):  # Represents the final output structure for a single company/domain
    domain: str  # The specific company domain (e.g., "stripe.com")
    confidence_score: float  # How confident the system is in the findings (0.0 to 1.0)
    evidence_sources: int  # Number of independent signals or data sources backing the findings
    findings: Dict  # Core insights returned by the system (usually includes fields like "technologies", "signals_found", etc.)