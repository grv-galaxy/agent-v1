"""
extractor.py
------------
Parses, sanitizes, and canonicalizes raw triple lines from facts.jsonl (ltm_doc.md §3, §8).

Responsibilities:
  - Read string lines or pre-parsed dictionaries.
  - Parse JSON safely without crashing the batch on one corrupt line.
  - Extract triples nested within episodic_events and factual_traits.
  - Apply extraction filters: drop triples with pronouns or empty objects.
  - Canonicalize subjects (e.g., ensuring variations of the primary human map strictly to "User").
  - Sanitize relations into lowercase snake_case.
  - Clamp importance scores using the business rules defined in importance.py.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Iterable, Any

from .deduplicator import CandidateTriple, normalize_relation
from . import importance

logger = logging.getLogger("ltm.extractor")

# Set of common low-meaning pronouns to filter out from objects (ltm_doc.md §3)
PRONOUN_FILTERS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those"
}

# Common user references to canonicalize to "User"
USER_ALIASES = {"i", "me", "my", "myself", "gaurav", "gautam", "user"}


def sanitize_relation(relation_text: str) -> str:
    """Transforms a relation string into standardized lowercase snake_case format."""
    if not relation_text:
        return "related_to"
    # Replace non-alphanumeric blocks with underscores
    cleaned = re.sub(r"[^\w\s\-]", "", relation_text)
    cleaned = re.sub(r"[\s\-]+", "_", cleaned)
    return cleaned.lower().strip("_")


def parse_facts(lines: Iterable[str | dict]) -> list[CandidateTriple]:
    """
    Parses complex nested JSONL lines or dictionaries to extract CandidateTriple objects
    from 'episodic_events' and 'factual_traits', ignoring rolling summaries.
    """
    candidates = []
    
    for line in lines:
        if line is None:
            continue
            
        # 1. Parse string to dict if needed
        if isinstance(line, dict):
            data = line
        else:
            if not isinstance(line, str) or not line.strip():
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"Skipping malformed JSON log line: {line}")
                continue

        if not isinstance(data, dict):
            continue
            
        # 2. Extract top-level tracking context
        conversation_id = data.get("conversation_id", "unknown_session")
        message_ids = data.get("message_ids", [])
        event_type = data.get("event_type", "factual")
        
        # 3. Pull out the facts bundle
        facts_bundle = data.get("facts", {})
        if not isinstance(facts_bundle, dict):
            continue
            
        # 4. Gather list sources from episodic_events and factual_traits
        episodic_list = facts_bundle.get("episodic_events", [])
        factual_list = facts_bundle.get("factual_traits", [])
        
        # Merge both categories into a single processing stream
        raw_triples: list[dict[str, Any]] = []
        if isinstance(episodic_list, list):
            raw_triples.extend(episodic_list)
        if isinstance(factual_list, list):
            raw_triples.extend(factual_list)
            
        # 5. Process and construct individual CandidateTriple objects
        for triple_data in raw_triples:
            if not isinstance(triple_data, dict):
                continue
                
            subject = triple_data.get("subject")
            relation = triple_data.get("relation")
            obj = triple_data.get("object")
            
            # Filter Rule: Skip incomplete data packages
            if not subject or not relation or not obj:
                continue
                
            # Clean text components
            subject_str = str(subject).strip()
            relation_str = str(relation).strip()
            obj_str = str(obj).strip()

            # Filter Rule: Drop items where the object is a low-meaning pronoun
            if obj_str.lower() in PRONOUN_FILTERS:
                continue

            # Step 2: Canonicalize subjects matching user context to "User"
            if subject_str.lower() in USER_ALIASES:
                subject_str = "User"

            # Step 3: Sanitize relation vocabulary to lowercase snake_case,
            # then normalize to canonical form so structural dedup hash matches
            # across synonymous phrasings (e.g. "lives" → "lives_in").
            relation_str = sanitize_relation(relation_str)
            relation_str = normalize_relation(relation_str)

            # Step 4: Extract and clean metadata metrics with defaults
            try:
                raw_importance = int(triple_data.get("importance", 60))
            except (ValueError, TypeError):
                raw_importance = 60

            try:
                confidence = float(triple_data.get("confidence", 1.0))
            except (ValueError, TypeError):
                confidence = 1.0

            # Bound metrics using lifecycle rules
            importance_score = importance.clamp_importance(raw_importance)
            confidence_score = max(0.0, min(1.0, confidence))

            # Generate the unified CandidateTriple packaging layer
            candidate = CandidateTriple(
                subject=subject_str,
                relation=relation_str,
                object=obj_str,
                layer=event_type,
                importance=importance_score,
                confidence=confidence_score,
                conversation_id=conversation_id,
                message_id=message_ids
            )
            candidates.append(candidate)
            
    return candidates