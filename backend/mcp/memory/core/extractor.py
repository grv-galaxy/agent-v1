# """
# extractor.py
# ------------
# Parses, sanitizes, and canonicalizes raw triple lines from facts.jsonl (ltm_doc.md §3, §8).

# Responsibilities:
#   - Read string lines (ALREADY FETCHED by the caller — this module does NOT
#     fetch anything itself. engine.py is responsible for calling fetcher.py
#     and handing the resulting lines to parse_facts()).
#   - Parse JSON safely without crashing the batch on one corrupt line.
#   - Apply extraction filters: drop triples with pronouns or empty objects.
#   - Canonicalize subjects (e.g., ensuring variations of the primary human map strictly to "User").
#   - Sanitize relations into lowercase snake_case.
#   - Clamp importance scores using the business rules defined in importance.py.
# """

# from __future__ import annotations

# import json
# import logging
# import re
# from typing import Iterable

# from .deduplicator import CandidateTriple
# from . import importance

# logger = logging.getLogger("ltm.extractor")

# # Set of common low-meaning pronouns to filter out from objects (ltm_doc.md §3)
# PRONOUN_FILTERS = {
#     "he", "him", "his", "himself",
#     "she", "her", "hers", "herself",
#     "it", "its", "itself",
#     "they", "them", "their", "theirs", "themselves",
#     "this", "that", "these", "those"
# }

# # Common user references to canonicalize to "User" (ltm_doc.md §3)
# USER_ALIASES = {"user", "me", "myself", "i", "the user", "human", "the human"}

# def sanitize_relation(relation: str) -> str:
#     """Convert open-vocabulary relation strings into clean lowercase snake_case."""
#     if not relation:
#         return "related_to"
#     # Replace spaces, hyphens, and special characters with underscores
#     s = re.sub(r"[\s\-_]+", "_", relation.strip())
#     # Keep only alphanumeric and underscores, strip trailing/leading underscores
#     s = re.sub(r"[^\w]", "", s).lower()
#     s = s.strip("_")
#     return s if s else "related_to"

# def should_skip_triple(subject: str, relation: str, obj: str) -> bool:
#     """
#     Applies filtering rules defined in ltm_doc.md §3:
#     - Skip triples where the object is a bare pronoun or empty.
#     - Skip structurally corrupt tokens.
#     """
#     if not obj or not obj.strip():
#         return True
    
#     clean_obj = obj.strip().lower()
#     if clean_obj in PRONOUN_FILTERS:
#         return True
        
#     if not subject or not subject.strip() or not relation or not relation.strip():
#         return True
        
#     return False

# def parse_facts(lines: Iterable[str]) -> list[CandidateTriple]:
#     """
#     Parses the `facts` section from each JSON line in the file.
#     Extracts episodic_events and factual_traits, filters invalid triples,
#     canonicalizes subjects/relations, and returns CandidateTriple objects.

#     `lines` MUST be provided by the caller (engine.py fetches them via
#     fetcher.read_latest_facts() and passes them in here). This function
#     has no knowledge of files, folders, or fetching — pure parsing only.
#     """
#     candidates = []

#     for line_idx, line in enumerate(lines):
#         if not line or not line.strip():
#             continue

#         try:
#             data = json.loads(line)
#         except json.JSONDecodeError as e:
#             logger.warning(f"Skipping corrupt JSONL line {line_idx}: {e}")
#             continue

#         if not isinstance(data, dict):
#             logger.warning(f"Skipping line {line_idx}: expected dict JSON shape, got {type(data)}")
#             continue

#         # Extract the "facts" section from the JSON line
#         facts_data = data.get("facts", {})
#         if not facts_data:
#             continue  # Skip lines with no facts

#         # Extract episodic_events and factual_traits
#         episodic_events = facts_data.get("episodic_events", [])
#         factual_traits = facts_data.get("factual_traits", [])

#         # Combine all fact lists
#         all_facts = episodic_events + factual_traits

#         for fact in all_facts:
#             # Extract fields from the fact dictionary
#             raw_subject = fact.get("subject", "")
#             raw_relation = fact.get("relation", "")
#             raw_object = fact.get("object", "")

#             # Cast to standard string types safely
#             subject = str(raw_subject).strip() if raw_subject is not None else ""
#             relation = str(raw_relation).strip() if raw_relation is not None else ""
#             obj = str(raw_object).strip() if raw_object is not None else ""

#             # Step 1: Filter out pronouns and structural noise
#             if should_skip_triple(subject, relation, obj):
#                 continue

#             # Step 2: Canonicalize User references
#             if subject.lower() in USER_ALIASES:
#                 subject = "User"

#             # Step 3: Sanitize relation vocabulary to lowercase snake_case
#             relation = sanitize_relation(relation)

#             # Step 4: Extract and clean metadata metrics with defaults
#             try:
#                 raw_importance = int(fact.get("importance", 50))
#             except (ValueError, TypeError):
#                 raw_importance = 50

#             try:
#                 confidence = float(fact.get("confidence", 1.0))
#             except (ValueError, TypeError):
#                 confidence = 1.0

#             # Bound metrics using lifecycle rules
#             importance_score = importance.clamp_importance(raw_importance)
#             confidence_score = max(0.0, min(1.0, confidence))

#             # Collect context markers if present
#             conversation_id = data.get("conversation_id")
#             message_ids = data.get("message_ids")
#             layer = fact.get("layer", "factual")

#             # Generate the CandidateTriple
#             candidate = CandidateTriple(
#                 subject=subject,
#                 relation=relation,
#                 object=obj,
#                 # raw_text=raw_text_string, 
#                 layer=layer,
#                 importance=importance_score,
#                 confidence=confidence_score,
#                 conversation_id=conversation_id,
#                 message_id=message_ids
#             )
#             candidates.append(candidate)

#     return candidates



































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