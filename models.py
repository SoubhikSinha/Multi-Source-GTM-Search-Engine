from pydantic import BaseModel  # Base class for data validation and settings management
from typing import List, Dict, Optional, Literal  # Generic types for static type hints

class ResearchRequest(BaseModel):  # Defines the expected shape of research request payloads
    research_goal: str  # Brief description of what the research aims to achieve
    company_domains: List[str]  # List of company website domains to include in the research
    search_depth: Literal["quick", "standard", "comprehensive"]  # Level of thoroughness for searches
    max_parallel_searches: int = 10  # Max number of simultaneous API calls allowed (default 10)
    confidence_threshold: float = 0.8  # Minimum confidence score required to accept a result (default 0.8)

class SearchResult(BaseModel):  # Defines the structure of an individual company search output
    domain: str  # The company domain that this result pertains to
    confidence_score: float  # Numeric score representing how reliable the result is
    evidence_sources: int  # Count of distinct sources backing up the findings
    findings: Dict  # Raw data or summarized insights returned by the various search modules
