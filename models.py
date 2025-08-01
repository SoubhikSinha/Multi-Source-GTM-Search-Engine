from pydantic import BaseModel # Importing BaseModel for data validation
from typing import List, Dict, Optional, Literal # Importing necessary types for type hints

class ResearchRequest(BaseModel):
    research_goal: str # The goal of the research
    company_domains: List[str] # List of company domains to search
    search_depth: Literal["quick", "standard", "comprehensive"] # Depth of the search
    max_parallel_searches: int = 10 # Maximum number of parallel searches
    confidence_threshold: float = 0.8 # Confidence threshold for results

class SearchResult(BaseModel):
    domain: str # Domain of the company
    confidence_score: float # Confidence score of the search result
    evidence_sources: int # Number of evidence sources supporting the result
    findings: Dict # Findings from the search
