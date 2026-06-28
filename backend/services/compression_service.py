import asyncio
import json
import re
from utils.memory_utils import count_tokens, cap_summary_by_tokens
from utils.fact_storage import trigger_on_demand_save

def extract_json_from_output(output: str, marker: str = None) -> dict:
    """
    Robustly extracts a JSON object from the LLM output string.
    If a marker is provided, it attempts to find JSON within or after that marker block.
    Handles strict structural raw JSON objects as well as markdown code wrapping.
    """
    if not output or not isinstance(output, str):
        return None

    content = output
    if marker and marker in output:
        marker_pos = output.find(marker)
        content = output[marker_pos + len(marker):]

    # Find the outer bounds of the JSON object
    first_brace = content.find("{")
    last_brace = content.rfind("}")

    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        print(f"[Warning] Failed to find valid JSON brace limits. Marker used: {marker}")
        return None

    json_str = content[first_brace:last_brace + 1].strip()

    # Remove markdown code fences if present
    json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
    json_str = re.sub(r'\s*```$', '', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Warning] JSON parsing failed: {e}. Raw content: {json_str[:200]}...")
        return None


# --- Prompts (unchanged) ---
FIRST_EPOCH_PROMPT = """
You are an advanced Conversation Analyzer and Memory Extraction Engine.

Your task is to analyze the FIRST raw conversation chunk and return a single, valid JSON object matching the exact schema below.

The JSON you produce will become the foundation of an AI memory system.

It has TWO purposes:

1. `summary`
   - A detailed rolling Short-Term Memory (STM) summary.
   - This summary will be injected into future prompts together with new raw conversation messages.

2. `facts_json`
   - A structured Long-Term Memory (LTM) extraction.
   - Only information with lasting value should be stored here.

Return ONLY valid JSON.

Do NOT output markdown.

Do NOT wrap JSON inside code fences.

Do NOT output any explanations.

===============================================================================
OBJECTIVE 1 — SUMMARY (SHORT-TERM MEMORY)
===============================================================================

The "summary" is NOT a transcript.

The "summary" is NOT a chronological retelling of every message.

Instead, it is a detailed state-preserving narrative whose purpose is to allow
another assistant to continue the conversation naturally even if the original
conversation history is no longer available.

Assume the future assistant will receive ONLY:
• this summary
• future raw conversation messages

The summary should preserve the CURRENT STATE of the conversation.

Include, whenever applicable:
• The user's primary goal(s)
• Current discussion topic(s)
• Overall context
• Important decisions already made
• Conclusions reached
• Work already completed
• Current progress
• Active tasks
• Open questions
• Outstanding problems
• Important assumptions
• Constraints or requirements
• Assistant commitments or promises
• User preferences that are relevant to THIS conversation
• Important relationships between different discussion topics
• Any other information necessary for seamless continuation

The summary should be sufficiently detailed to reconstruct the conversation
state without needing previous messages.

Do NOT include:
- Greetings.
- Conversational introductions that contain no meaningful information.
- Pleasantries or social niceties.
- Acknowledgements or conversational filler.
- Repeated information.
- Unnecessary chronological narration.
- Information that has no future conversational value.

Exception:
If an introduction establishes important conversational context, persistent user information, or information necessary for continuing the conversation, preserve that information appropriately in the summary and, if it has lasting value, extract it into `facts_json`.

Write naturally as one coherent narrative.

Do NOT artificially shorten the summary.

===============================================================================
OBJECTIVE 2 — LONG-TERM MEMORY EXTRACTION
===============================================================================

Extract ONLY information that has value beyond the current conversation.

Long-term memory should contain information that is likely to remain useful
across future conversations.

Avoid storing temporary discussion context.

Avoid storing short-lived conversational details.

The categories are:

------------------------------------------------------------------------------
episodic_events
------------------------------------------------------------------------------

Store meaningful events or milestones as a (subject, relation, object) triple.

Examples:
- {{"subject": "User", "relation": "started", "object": "building an AI memory system"}}
- {{"subject": "User", "relation": "planned", "object": "a trip to Japan"}}
- {{"subject": "User", "relation": "completed", "object": "a research project"}}
- {{"subject": "User", "relation": "began", "object": "learning Spanish"}}

Use "User" as the canonical subject unless a different named person is explicitly the subject.
Use a short past-tense relation describing the action (started, planned, completed, began, finished, decided, etc.)

Ignore trivial events.

------------------------------------------------------------------------------
factual_traits
------------------------------------------------------------------------------

Store stable or semi-stable information about the user as a (subject, relation, object) triple.

Examples:
- {{"subject": "User", "relation": "name", "object": "Gaurav"}}
- {{"subject": "User", "relation": "lives_in", "object": "Delhi"}}
- {{"subject": "User", "relation": "prefers", "object": "dark mode"}}
- {{"subject": "User", "relation": "is", "object": "vegetarian"}}
- {{"subject": "User", "relation": "develops", "object": "AI applications"}}

Use "User" as the canonical subject unless a different named person is explicitly the subject.
Use a short, lowercase, snake_case relation (e.g. lives_in, prefers, name, is, owns, works_at).
Do not invent a fixed list of relations — use whatever relation best fits the fact.

Only extract facts explicitly stated or directly established.
Never infer personal information.

------------------------------------------------------------------------------
semantic_concepts
------------------------------------------------------------------------------

Store important concepts central to the discussion as plain strings (no triple needed here).

Examples:
- "Machine Learning"
- "Budget Planning"
- "Memory Compression"

Do NOT extract every noun.
Only include concepts that would improve future retrieval.

------------------------------------------------------------------------------
entities
------------------------------------------------------------------------------

Extract important named entities mentioned during the conversation.

Populate the following categories whenever applicable:
• Files/Paths
• Variables/Functions
• Classes
• Libraries
• Frameworks
• Models
• Packages
• Repositories
• Commands
• Errors/Bugs
• URLs
• Applications
• Products
• Projects
• Organizations
• People
• Places
• Books
• Movies

If a category has no entities, return ["NONE"].

===============================================================================
EXTRACTION RULES
===============================================================================

Only extract information directly supported by the conversation.

Never hallucinate.

Never guess.

Never infer unstated user preferences, traits or intentions.

If uncertain, omit it.

Prefer precision over quantity.

Avoid duplicate memories.

Normalize memories into concise canonical wording whenever possible.

Bad:
"The user seems interested in Python."

Good:
"Preferred programming language: Python"

For factual_traits and episodic_events, always output triples in the form
{{"subject": "...", "relation": "...", "object": "...", "importance": <1-100>, "confidence": <0-1>}}.

Set importance high (80-100) for identity/stable attributes (name, location, relationships, firm preferences).
Set importance low (1-20) for one-off events, trivia, or minor occurrences.
Set confidence based on how explicitly/clearly the fact was stated (0.9+ for direct statements, lower for implied ones).

Only store information that is likely to improve future conversations.

===============================================================================
EXPECTED JSON OUTPUT
===============================================================================

{{
  "summary": "...",

  "facts_json": {{

    "episodic_events": [{{"subject": "", "relation": "", "object": "", "importance": 0, "confidence": 0}}
    ],

    "factual_traits": [{{"subject": "", "relation": "", "object": "", "importance": 0, "confidence": 0}}
    ],

    "semantic_concepts": [],

    "entities": {{
      "Files/Paths": [],
      "Variables/Functions": [],
      "Classes": [],
      "Libraries": [],
      "Frameworks": [],
      "Models": [],
      "Packages": [],
      "Repositories": [],
      "Commands": [],
      "Errors/Bugs": [],
      "URLs": [],
      "Applications": [],
      "Products": [],
      "Projects": [],
      "Organizations": [],
      "People": [],
      "Places": [],
      "Books": [],
      "Movies": []
    }}
  }}
}}
===============================================================================
CONVERSATION CHUNK
===============================================================================
{chunk_text}
"""

ANCHORED_COMPRESSION_PROMPT = """
You are an advanced Memory Consolidation, Conversation State Update, and Long-Term Memory Extraction Engine.

Your task is to process a continuing conversation after the first epoch.

You are given:

1. An EXISTING SUMMARY
   - This is the rolling Short-Term Memory (STM) representing the accumulated conversational state from all previous epochs.

2. A NEW CONVERSATION CHUNK
   - This contains only the latest raw conversation messages.

Your responsibilities are equally important:

1. Update the rolling Short-Term Memory (STM) summary by intelligently merging the new conversation into the existing conversational state.

2. Extract valuable Long-Term Memory (LTM) candidates ONLY from the NEW CONVERSATION CHUNK.

Return ONLY a single valid JSON object.

Do NOT output markdown.

Do NOT wrap JSON inside code fences.

Do NOT include explanations.

===============================================================================
UNDERSTANDING THE TWO MEMORY SYSTEMS
===============================================================================

This task maintains TWO completely different memory systems.

SHORT-TERM MEMORY (summary)
The summary represents the assistant's current conversational working memory.

Its purpose is to preserve everything necessary for another assistant to
continue the conversation naturally.

The summary may contain temporary information such as:
• current discussion topics
• active tasks
• ongoing plans
• unresolved questions
• temporary constraints
• project state
• current decisions

LONG-TERM MEMORY (facts_json)
The facts_json represents persistent knowledge.

Only information that is expected to remain useful beyond the current
conversation belongs here.

Do NOT store temporary discussion context.

Do NOT store temporary plans.

Do NOT store short-lived questions.

Do NOT store information that is only useful inside the current conversation.

===============================================================================
OBJECTIVE 1 — UPDATE THE ROLLING SUMMARY
===============================================================================

Treat the EXISTING SUMMARY as the authoritative conversational state.

Do NOT rewrite it from scratch.

Instead, intelligently merge the NEW CONVERSATION CHUNK into the existing
summary while preserving important context.

The updated summary should represent the CURRENT STATE of the conversation after
processing the new messages.

Preserve information unless:
• it is explicitly contradicted,
• it has become obsolete because newer information replaces it,
• or it is no longer useful for continuing the conversation.

When updating the summary, preserve and update whenever applicable:
• user goals
• current discussion topics
• overall context
• important decisions
• conclusions reached
• completed work
• current progress
• active tasks
• unresolved questions
• ongoing problems
• constraints
• assumptions
• assistant commitments
• conversation-relevant user preferences
• important relationships between discussion topics
• any information required for seamless continuation

Merge new information naturally into the existing narrative.

Do NOT simply append new paragraphs.

Do NOT remove useful context merely to shorten the summary.

Do NOT include:
- Greetings.
- Conversational introductions that contain no meaningful information.
- Pleasantries or social niceties.
- Acknowledgements or conversational filler.
- Repeated information.
- Unnecessary chronological narration.
- Information that has no future conversational value.

Exception:
If an introduction establishes important conversational context, persistent user information, or information necessary for continuing the conversation, preserve that information appropriately in the summary and, if it has lasting value, extract it into `facts_json`.

The goal is to preserve conversational continuity with minimal information loss.

===============================================================================
OBJECTIVE 2 — LONG-TERM MEMORY EXTRACTION
===============================================================================

The ONLY source of truth for long-term memory extraction is the
NEW CONVERSATION CHUNK.

The EXISTING SUMMARY exists ONLY to update the rolling conversational state.

Never use the EXISTING SUMMARY as evidence when extracting long-term memories.

Extract only long-term memory candidates explicitly supported by the
NEW CONVERSATION CHUNK.

Any duplicate detection, semantic similarity checking, memory merging,
memory updating, or conflict resolution with previously stored memories
will be handled by downstream memory management systems.

Before extracting a memory, ask yourself:

"Will this information still be useful if the conversation resumes weeks or
months later?"

If YES:
Store it inside facts_json.

If NO:
Keep it only inside the summary.

------------------------------------------------------------------------------
episodic_events
------------------------------------------------------------------------------

Store meaningful events or milestones as a (subject, relation, object) triple.

Examples:
- {{"subject": "User", "relation": "started", "object": "building an AI memory system"}}
- {{"subject": "User", "relation": "planned", "object": "a trip to Japan"}}
- {{"subject": "User", "relation": "completed", "object": "a research project"}}
- {{"subject": "User", "relation": "began", "object": "learning Spanish"}}

Use "User" as the canonical subject unless a different named person is explicitly the subject.
Use a short past-tense relation describing the action (started, planned, completed, began, finished, decided, etc.)

Ignore trivial events.

------------------------------------------------------------------------------
factual_traits
------------------------------------------------------------------------------

Store stable or semi-stable information about the user as a (subject, relation, object) triple.

Examples:
- {{"subject": "User", "relation": "name", "object": "Gaurav"}}
- {{"subject": "User", "relation": "lives_in", "object": "Delhi"}}
- {{"subject": "User", "relation": "prefers", "object": "dark mode"}}
- {{"subject": "User", "relation": "is", "object": "vegetarian"}}
- {{"subject": "User", "relation": "develops", "object": "AI applications"}}

Use "User" as the canonical subject unless a different named person is explicitly the subject.
Use a short, lowercase, snake_case relation (e.g. lives_in, prefers, name, is, owns, works_at).
Do not invent a fixed list of relations — use whatever relation best fits the fact.

Only extract facts explicitly stated or directly established.
Never infer personal information.

------------------------------------------------------------------------------
semantic_concepts
------------------------------------------------------------------------------

Store important concepts central to the discussion as plain strings (no triple needed here).

Examples:
- "Machine Learning"
- "Budget Planning"
- "Memory Compression"

Do NOT extract every noun.
Only include concepts that would improve future retrieval.

------------------------------------------------------------------------------
entities
------------------------------------------------------------------------------

Extract important named entities introduced in the NEW CONVERSATION CHUNK.

Populate whenever applicable:
• Files/Paths
• Variables/Functions
• Classes
• Libraries
• Frameworks
• Models
• Packages
• Repositories
• Commands
• Errors/Bugs
• URLs
• Applications
• Products
• Projects
• Organizations
• People
• Places
• Books
• Movies

If a category contains no entities, return ["NONE"].

===============================================================================
EXTRACTION RULES
===============================================================================

Only extract information explicitly supported by the NEW CONVERSATION CHUNK.

Never hallucinate.

Never guess.

Never infer unstated preferences, intentions, or traits.

If uncertain, omit it.

Prefer precision over quantity.

Normalize memories into concise canonical wording whenever possible.

For factual_traits and episodic_events, always output triples in the form
{{"subject": "...", "relation": "...", "object": "...", "importance": <1-100>, "confidence": <0-1>}}.

Set importance high (80-100) for identity/stable attributes (name, location, relationships, firm preferences).
Set importance low (1-20) for one-off events, trivia, or minor occurrences.
Set confidence based on how explicitly/clearly the fact was stated (0.9+ for direct statements, lower for implied ones).

Avoid extracting temporary conversational details into long-term memory.

===============================================================================
EXPECTED JSON OUTPUT
===============================================================================

{{
  "summary": "...",

  "facts_json": {{

    "episodic_events": [{{"subject": "", "relation": "", "object": "", "importance": 0, "confidence": 0}}
    ],

    "factual_traits": [{{"subject": "", "relation": "", "object": "", "importance": 0, "confidence": 0}}
    ],

    "semantic_concepts": [],

    "entities": {{
      "Files/Paths": [],
      "Variables/Functions": [],
      "Classes": [],
      "Libraries": [],
      "Frameworks": [],
      "Models": [],
      "Packages": [],
      "Repositories": [],
      "Commands": [],
      "Errors/Bugs": [],
      "URLs": [],
      "Applications": [],
      "Products": [],
      "Projects": [],
      "Organizations": [],
      "People": [],
      "Places": [],
      "Books": [],
      "Movies": []
    }}
  }}
}}
===============================================================================
EXISTING SUMMARY
===============================================================================

{existing_summary}

===============================================================================
NEW CONVERSATION CHUNK
===============================================================================

{chunk_text}
"""

GROUNDING_PROMPT = """
You are an advanced Summary Maintenance and Conversation State Reconciliation Engine.

Your task is NOT to summarize a conversation from scratch.

Your task is to improve the quality of an existing rolling conversation summary
after many update cycles.

The summary has been updated across multiple conversation epochs and may now
contain:
• duplicated information
• repetitive wording
• outdated context
• obsolete assumptions
• conflicting statements
• inconsistent organization
• unnecessary verbosity

Your responsibility is to transform it into a cleaner, more coherent,
well-structured conversation state while preserving all important information.

Return ONLY a valid JSON object.

Do NOT output markdown.

Do NOT wrap JSON inside code fences.

Do NOT include explanations.

===============================================================================
OBJECTIVE
===============================================================================

The input summary represents the assistant's accumulated Short-Term Memory (STM).

Treat it as the authoritative representation of the conversation.

Improve its quality WITHOUT losing important context.

The output should still represent exactly the same conversation state,
only better organized, more coherent, and easier for another assistant
to understand.

===============================================================================
WHAT TO PRESERVE
===============================================================================

Preserve whenever applicable:
• user goals
• current discussion topics
• overall context
• important decisions
• conclusions
• completed work
• current progress
• active tasks
• unresolved questions
• ongoing problems
• constraints
• assumptions
• assistant commitments
• conversation-relevant user preferences
• important contextual relationships
• any information required for seamless continuation

===============================================================================
WHAT TO IMPROVE
===============================================================================

Improve the summary by:
• removing duplicate information
• merging repeated ideas
• removing obsolete information that is no longer relevant
• resolving contradictions using the most recent information
• improving logical flow
• improving readability
• improving clarity
• reducing unnecessary verbosity
• preserving all meaningful context

Do NOT aggressively shorten the summary.

Optimize for information quality rather than minimum length.

===============================================================================
WHAT NOT TO DO
===============================================================================

Do NOT:
• invent information
• hallucinate facts
• remove useful context
• remove active tasks
• remove unresolved questions
• remove important decisions
• convert the summary into bullet points
• rewrite it as a chronological transcript

Maintain it as a natural, coherent state-preserving narrative.

===============================================================================
OUTPUT FORMAT
===============================================================================

{{
  "summary": "Improved rolling conversation summary."
}}

===============================================================================
CURRENT SUMMARY
===============================================================================

{existing_summary}
"""

async def compress_chunk(
    chunk_messages: list[dict],
    existing_summary: str,
    provider_instance,
    model_name: str,
    session_id: str,
    compression_epoch: int,
    max_summary_tokens: int = None,
) -> str:
    try:


        # --- Step 1: Prepare chunk_text ---
        chunk_text = "\n".join(
            f"[{m.get('role', 'unknown').upper()}]: {m.get('content', '')}"
            for m in chunk_messages
        )


        # --- Step 2: Select prompt ---
        if compression_epoch == 1:
            prompt = FIRST_EPOCH_PROMPT.format(chunk_text=chunk_text)
        else:
            prompt = ANCHORED_COMPRESSION_PROMPT.format(
                existing_summary=existing_summary or "",
                chunk_text=chunk_text
            )


        # --- Step 3: Stream LLM response ---
        result_tokens = []
        async for chunk in provider_instance.generate_stream(model_name, [{"role": "user", "content": prompt}]):
            if isinstance(chunk, dict):
                result_tokens.append(chunk.get("text", ""))
        raw_response = "".join(result_tokens).strip()


        # --- Step 4: Parse JSON ---

        parsed_payload = extract_json_from_output(raw_response)
        if parsed_payload and isinstance(parsed_payload, dict):

            new_summary = parsed_payload.get("summary", "").strip()
            facts = parsed_payload.get("facts_json", {})
        else:

            # Emergency fallback
            new_summary = raw_response
            facts = None
            if "SUMMARY:" in new_summary:
                new_summary = new_summary.split("SUMMARY:")[-1]
            if "FACTS_JSON:" in new_summary:
                parts = new_summary.split("FACTS_JSON:")
                new_summary = parts[0].strip()
                facts = extract_json_from_output(parts[1])


        # --- Step 5: Save and return ---
        trigger_on_demand_save(
            session_id=session_id,
            epoch=compression_epoch,
            event_type="compression_pass",
            rolling_summary=new_summary,
            facts=facts,
        )
        return cap_summary_by_tokens(new_summary, max_summary_tokens)

    except Exception as e:
        print(f"[ERROR] Compression failed at step: {e}")  # This is where '\n  "summary"' appears!
        import traceback
        traceback.print_exc()  # Print full stack trace to see the exact line
        return cap_summary_by_tokens(existing_summary or "", max_summary_tokens)

async def grounding_pass(
    summary_history: list[str],
    current_summary: str,
    provider_instance,
    model_name: str,
    session_id: str,
    compression_epoch: int,
    max_summary_tokens: int = None,
) -> str:
    """
    - Takes ALL prior compression summaries.
    - Outputs holistic summary + canonical JSON (resolves all contradictions).
    - Parses and stores JSON facts separately.
    """
    try:
        all_versions = [s for s in summary_history if s] + [current_summary]
        if len(all_versions) < 2:
            return cap_summary_by_tokens(current_summary, max_summary_tokens)

        versions_text = "\n\n---\n\n".join(
            f"Epoch {i+1}:\n{s}" for i, s in enumerate(all_versions)
        )

        prompt = GROUNDING_PROMPT.format(existing_summary=versions_text)
        messages = [{"role": "user", "content": prompt}]

        # --- Stream LLM response ---
        result_tokens = []
        try:
            async for chunk in provider_instance.generate_stream(model_name, messages):
                if isinstance(chunk, dict):
                    result_tokens.append(chunk.get("text", ""))
        except Exception as e:
            print(f"[Error] Streaming failed: {e}")
            return cap_summary_by_tokens(current_summary, max_summary_tokens)

        raw_response = "".join(result_tokens).strip()

        # --- Parse Master grounding payload ---
        parsed_payload = extract_json_from_output(raw_response)

        if parsed_payload and isinstance(parsed_payload, dict):
            grounded_summary = parsed_payload.get("summary", "").strip()
            facts = parsed_payload.get("facts_json", {})
        else:
            # Flat text partition emergency fallback
            print("[grounding_service] Grounding fallback processing triggered.")
            grounded_summary = raw_response
            facts = None

            if "SUPER_COMPRESSION:" in grounded_summary:
                grounded_summary = grounded_summary.split("SUPER_COMPRESSION:")[-1].strip()
            if "RECONCILED_FACTS_JSON:" in grounded_summary:
                parts = grounded_summary.split("RECONCILED_FACTS_JSON:")
                grounded_summary = parts[0].strip()
                facts = extract_json_from_output(parts[1])

        # --- Save grounding pass ---
        try:
            trigger_on_demand_save(
                session_id=session_id,
                epoch=compression_epoch,
                event_type="grounding_pass",
                rolling_summary=grounded_summary,
                facts=facts,
            )
        except Exception as e:
            print(f"[Error] Failed to save grounding pass: {e}")

        return cap_summary_by_tokens(grounded_summary, max_summary_tokens)

    except Exception as e:
        print(f"[Error] Grounding failed: {e}")
        return cap_summary_by_tokens(current_summary, max_summary_tokens)