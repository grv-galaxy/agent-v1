from pydantic import BaseModel, Field
from typing import List, Optional

class ClassifierOutput(BaseModel):
    categories: List[str] = Field(
        description="Array of category labels matching the query intent (e.g., 'general', 'news', 'science', 'it', 'finance', 'patents', 'packages', 'academic', 'economic', 'india_news', 'india_public', 'india_finance', 'legal'). A query can span multiple categories."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0 for the classification."
    )
    entities: List[str] = Field(
        description="List of extracted key entities, terms, or concepts from the query."
    )
    date_range: Optional[str] = Field(
        default=None,
        description="Extracted date range if specified (e.g., 'past month', 'last 24 hours', '2023'). Null if none."
    )
    language_hint: Optional[str] = Field(
        default=None,
        description="Region or language hint if the query specifies one (e.g., 'en-IN' for India, 'de' for Germany). Null if none."
    )
    requires_deep_research: bool = Field(
        default=False,
        description="True if the query requires multi-hop deep research (e.g. comparative analysis, multi-entity questions, synthesis across distinct fact types). False for simple lookups or single-entity facts."
    )
    deep_research_reasoning: str = Field(
        default="",
        description="A brief sentence explaining why the query requires deep research, if applicable. Leave empty if requires_deep_research is false."
    )

class PlannerOutput(BaseModel):
    sub_queries: List[str] = Field(
        description="List of 3 to 4 distinct, non-overlapping sub-queries to execute in parallel."
    )
    reasoning: str = Field(
        description="Brief reasoning behind the decomposition strategy."
    )
