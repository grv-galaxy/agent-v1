# Active Prompts (from compression_service.py)

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

Return ONLY a single valid JSON object. Ensure all newlines within string values (like the "summary" string) are properly escaped as "\n" to maintain strict JSON compliance. Do NOT output unescaped literal newlines inside string properties.

Do NOT output markdown outside the JSON.

Do NOT wrap JSON inside code fences.

Do NOT output any explanations.

===============================================================================
OBJECTIVE 1 — SUMMARY (SHORT-TERM MEMORY)
===============================================================================

The "summary" is NOT a transcript.

The "summary" is NOT a chronological retelling of every message, nor is it a single flat paragraph.

Instead, it is a highly structured, dense, and clean markdown block that preserves the CURRENT STATE of the conversation.

Assume the future assistant will receive ONLY:
• this summary
• future raw conversation messages

You MUST format the "summary" string inside the JSON using the exact markdown structure below. Only fill in the sub-bullets with actual content from the conversation. Do NOT write generic placeholder sentences for categories that have no information (simply omit empty bullet items, but keep the headers).

CRITICAL RULES FOR THE SUMMARY STRING:
- You MUST output exactly ONE block of the summary.
- NEVER repeat the headers. Do NOT append multiple blocks.
- The summary block MUST be the value of the `summary` string inside the JSON output. Do NOT output raw markdown outside the JSON.

REQUIRED SUMMARY FORMAT:
### 👤 USER PROFILE
- **Name**: [Actual name or nickname if stated, otherwise "Unknown"]
- **Preferences**: [List stable/long-term preferences relevant to the conversation]
- **Key Attributes**: [List location, occupation, or identity facts]

### 🎯 SESSION STATE
- **Active Goal**: [Primary objective of the current conversation]
- **Current Topic**: [Specific subject being discussed right now]
- **Completed Work**: [Key deliverables, code written, or decisions finalized]
- **Progress**: [Summary of the conversation flow so far]

### 📋 NEXT STEPS
- **Pending Tasks**: [Unfinished actions or commitments by the user/assistant]
- **Open Questions**: [Unresolved questions or topics to follow up on]

CONCISENESS & FORMULATING RULES:
- Use short, punchy fragments (NOT full conversational sentences).
- Do NOT repeat the same topic name or keywords in multiple fields.
- Deduplicate items; never repeat information.
- Format lists cleanly: do NOT leave trailing commas or incomplete punctuation.
- Keep sub-bullet lists concise, using simple words.

GOOD SUMMARY EXAMPLE (Note how the markdown is inside the JSON "summary" string, with newlines escaped as \\n):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav (Nickname: Jarvis)\\n- **Preferences**: Blue, dark mode\\n- **Key Attributes**: Lives in New York; loves swimming and travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Test available programming/search tools\\n- **Current Topic**: Tool capabilities overview\\n- **Completed Work**: Explained Python and Browser capabilities\\n- **Progress**: Introduced self and aligned on tool list\\n\\n### 📋 NEXT STEPS\\n- **Pending Tasks**: Execute user's first tool request\\n- **Open Questions**: Which tool does the user want to try first?",
  "facts_json": {{
    "episodic_events": [],
    "factual_traits": [],
    "semantic_concepts": [],
    "entities": {{}}
  }}
}}

BAD SUMMARY EXAMPLE (Avoid this structure):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav\\n- **Preferences**: Gaurav prefers the color blue, and Gaurav prefers dark mode, \\n- **Key Attributes**: Lives in New York, loves to swim, loves travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Assist Gaurav with using the Jarvis tools\\n- **Current Topic**: Discussing the Jarvis tools\\n- **Completed Work**: Gave the Jarvis tools to Gaurav and discussed Jarvis tools\\n- **Progress**: Gaurav has introduced himself and wants to use Jarvis tools"
}}

CRITICAL — IDENTITY AND PERSONAL FACTS:
If the user reveals their name, nickname, location, occupation, age, relationships,
or any stable personal attribute, this information MUST ALWAYS be explicitly preserved 
in the "USER PROFILE" section of the summary — even if it was shared during a greeting or introduction.
These facts are essential for conversational continuity.
Extracting such facts into `facts_json` does NOT mean removing them from the summary.
Identity facts must appear in BOTH the summary AND `facts_json`.

Do NOT include:
- Greetings or pleasantries that contain NO factual information.
- Pure acknowledgements or conversational filler (e.g., "okay", "got it", "thanks").
- Repeated information already present in the summary.
- Unnecessary chronological narration.
- Information that has no future conversational value.
- Empty template fields or placeholder strings like "[no information]". Just omit bullet items if they are empty.

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

Do NOT extract arbitrary, trivial, or useless facts. Only extract meaningful information that has a clear, actionable use-case for future reference.

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

CRITICAL RULE — CANONICAL SUBJECT:
Always use the exact string "User" as the subject for the person you are speaking with, and "Assistant" for yourself.
(e.g. {{"subject": "User", "relation": "name", "object": "Gaurav"}}).
Do NOT use the user's actual name (e.g. do NOT use "Gaurav", "Jarvis", "Jay", or any other name) as the subject of factual_traits or episodic_events. 
The subject must strictly be the literal string "User" or "Assistant". No names allowed in the subject field whatsoever.

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

Return ONLY a single valid JSON object. Ensure all newlines within string values (like the "summary" string) are properly escaped as "\n" to maintain strict JSON compliance. Do NOT output unescaped literal newlines inside string properties.

Do NOT output markdown outside the JSON.

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

Treat the EXISTING SUMMARY as the authoritative conversational state. It is formatted in structured markdown.

Do NOT rewrite the summary structure. Maintain the exact same headers:
- `### 👤 USER PROFILE`
- `### 🎯 SESSION STATE`
- `### 📋 NEXT STEPS`

Intelligently merge the NEW CONVERSATION CHUNK into the existing summary. Update sub-bullets under these headers, preserving important context while replacing outdated or contradicted information with fresher context from the new chunk.

CRITICAL RULES FOR THE SUMMARY STRING:
- You MUST output exactly ONE block of the summary.
- NEVER repeat the headers. Do NOT append a new summary below the old one.
- You MUST MERGE the EXISTING SUMMARY and the NEW CONVERSATION CHUNK into a SINGLE, unified markdown string.
- This unified markdown string MUST be the value of the `summary` field in your JSON output.

REQUIRED SUMMARY FORMAT:
### 👤 USER PROFILE
- **Name**: [Keep or update user's name/nickname]
- **Preferences**: [Keep or update stable user preferences]
- **Key Attributes**: [Keep or update location, occupation, or key identity facts]

### 🎯 SESSION STATE
- **Active Goal**: [Current conversation goal, updated if it changed]
- **Current Topic**: [Topic under discussion in the new chunk]
- **Completed Work**: [Accumulate any new completed deliverables or decisions]
- **Progress**: [Merge new events and progress with historical progress]

### 📋 NEXT STEPS
- **Pending Tasks**: [Unfinished actions or commitments by the user/assistant]
- **Open Questions**: [Unresolved questions or topics to follow up on]

CONCISENESS & FORMULATING RULES:
- Use short, punchy fragments (NOT full conversational sentences).
- Do NOT repeat the same topic name or keywords in multiple fields.
- Deduplicate items; never repeat information.
- Format lists cleanly: do NOT leave trailing commas or incomplete punctuation.
- Keep sub-bullet lists concise, using simple words.

GOOD SUMMARY EXAMPLE (Note how the markdown is inside the JSON "summary" string, with newlines escaped as \\n):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav (Nickname: Jarvis)\\n- **Preferences**: Blue, dark mode\\n- **Key Attributes**: Lives in New York; loves swimming and travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Test available programming/search tools\\n- **Current Topic**: Tool capabilities overview\\n- **Completed Work**: Explained Python and Browser capabilities\\n- **Progress**: Introduced self and aligned on tool list\\n\\n### 📋 NEXT STEPS\\n- **Pending Tasks**: Execute user's first tool request\\n- **Open Questions**: Which tool does the user want to try first?",
  "facts_json": {{
    "episodic_events": [],
    "factual_traits": [],
    "semantic_concepts": [],
    "entities": {{}}
  }}
}}

BAD SUMMARY EXAMPLE (Avoid this structure):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav\\n- **Preferences**: Gaurav prefers the color blue, and Gaurav prefers dark mode, \\n- **Key Attributes**: Lives in New York, loves to swim, loves travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Assist Gaurav with using the Jarvis tools\\n- **Current Topic**: Discussing the Jarvis tools\\n- **Completed Work**: Gave the Jarvis tools to Gaurav and discussed Jarvis tools\\n- **Progress**: Gaurav has introduced himself and wants to use Jarvis tools"
}}

CRITICAL — IDENTITY AND PERSONAL FACTS:
User identity facts (name, nickname, location, occupation, age, relationships,
stable preferences) from the EXISTING SUMMARY must ALWAYS be carried forward
into the updated summary. Never drop identity facts during merging.
If the NEW CONVERSATION CHUNK reveals new identity facts, add them to the "USER PROFILE" section.
Extracting facts into `facts_json` does NOT mean removing them from the summary.
The summary is the primary context carrier — identity facts must appear in BOTH.

Do NOT include:
- Greetings or pleasantries that contain NO factual information.
- Pure acknowledgements or conversational filler (e.g., "okay", "got it", "thanks").
- Repeated information already present in the summary.
- Unnecessary chronological narration.
- Information that has no future conversational value.
- Empty template fields or placeholder strings like "[no information]". Just omit bullet items if they are empty.

===============================================================================
OBJECTIVE 2 — LONG-TERM MEMORY EXTRACTION
===============================================================================

You must use BOTH the EXISTING SUMMARY and the NEW CONVERSATION CHUNK to extract Long-Term Memories.

The EXISTING SUMMARY provides the necessary historical context to fully understand the events, decisions, and facts being discussed in the NEW CONVERSATION CHUNK.

Extract only meaningful, high-value long-term memory candidates that are established or updated in the NEW CONVERSATION CHUNK, using the summary to resolve references and context.

Do NOT extract arbitrary, trivial, or useless facts. Only extract information that has a clear, actionable use-case for future reference. If a fact does not provide significant value to a future AI assistant, DO NOT extract it.

Any duplicate detection, semantic similarity checking, memory merging,
memory updating, or conflict resolution with previously stored memories
will be handled by downstream memory management systems.

Before extracting a memory, ask yourself:

"Will this information still be useful if the conversation resumes weeks or
months later?"

If YES:
Store it inside facts_json.
If it is a user identity fact or stable personal attribute (name, location,
occupation, preferences), ALSO ensure it remains in the summary.

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

Only extract information explicitly supported by the NEW CONVERSATION CHUNK, using the EXISTING SUMMARY for context resolution.

Do NOT extract arbitrary, trivial, or useless facts. Only extract meaningful information that has a clear, actionable use-case for future reference.

Never hallucinate.

Never guess.

Never infer unstated preferences, intentions, or traits.

If uncertain, omit it.

Prefer precision over quantity.

Normalize memories into concise wording whenever possible.

For factual_traits and episodic_events, always output triples in the form
{{"subject": "...", "relation": "...", "object": "...", "importance": <1-100>, "confidence": <0-1>}}.

CRITICAL RULE — CANONICAL SUBJECT:
Always use the exact string "User" as the subject for the person you are speaking with, and "Assistant" for yourself.
(e.g. {{"subject": "User", "relation": "name", "object": "Gaurav"}}).
Do NOT use the user's actual name (e.g. do NOT use "Gaurav", "Jarvis", "Jay", or any other name) as the subject of factual_traits or episodic_events. 
The subject must strictly be the literal string "User" or "Assistant". No names allowed in the subject field whatsoever.

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

DISCONNECTED_BATCH_COMPRESSION_PROMPT = """
You are an advanced Long-Term Memory Extraction Engine.

Your task is to process a BATCH of DISCONNECTED raw conversation fragments and extract valuable Long-Term Memory (LTM) candidates.

You are given:
A NEW CONVERSATION CHUNK
- This contains a batch of raw messages gathered over time (e.g., from a raw ledger).
- CRITICAL: These messages are DISJOINTED. They do NOT necessarily form a continuous, chronological narrative. Topic A might jump instantly to Topic B (e.g., coding Python on Monday, then suddenly booking a flight on Wednesday).

Your responsibilities:
1. Extract valuable Long-Term Memory (LTM) candidates independently from the fragments.
2. Provide a brief overview of the topics covered in the `summary` field.

Return ONLY a single valid JSON object. Ensure all newlines within string values (like the "summary" string) are properly escaped as "\\n" to maintain strict JSON compliance. Do NOT output unescaped literal newlines inside string properties.

Do NOT output markdown outside the JSON.

Do NOT wrap JSON inside code fences.

Do NOT include explanations.

===============================================================================
OBJECTIVE 1 — SUMMARY
===============================================================================

Because the chunk contains disconnected fragments, do NOT attempt to write a continuous narrative.
Instead, briefly list or summarize the distinct topics discussed in this batch.
(e.g., "The user worked on a Python memory script, then asked about flights to Japan, and finally discussed vegetarian recipes.")

===============================================================================
OBJECTIVE 2 — LONG-TERM MEMORY EXTRACTION
===============================================================================

You must evaluate each message or fragment INDEPENDENTLY.

Do NOT hallucinate connections between different topics in the chunk. If the user talks about Python and then suddenly talks about a recipe, they are NOT related.

Extract only meaningful, high-value long-term memory candidates.

Do NOT extract arbitrary, trivial, or useless facts. Only extract information that has a clear, actionable use-case for future reference. If a fact does not provide significant value to a future AI assistant, DO NOT extract it.

Any duplicate detection, semantic similarity checking, memory merging,
memory updating, or conflict resolution with previously stored memories
will be handled by downstream memory management systems.

Before extracting a memory, ask yourself:

"Will this information still be useful if the conversation resumes weeks or
months later?"

If YES:
Store it inside facts_json.

If NO:
Omit it entirely.

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

Do NOT extract arbitrary, trivial, or useless facts. Only extract meaningful information that has a clear, actionable use-case for future reference.

Never hallucinate.

Never guess.

Never infer unstated preferences, intentions, or traits.

If uncertain, omit it.

Prefer precision over quantity.

Normalize memories into concise canonical wording whenever possible.

For factual_traits and episodic_events, always output triples in the form
{{"subject": "...", "relation": "...", "object": "...", "importance": <1-100>, "confidence": <0-1>}}.

CRITICAL RULE — CANONICAL SUBJECT:
Always use the exact string "User" as the subject for the person you are speaking with, and "Assistant" for yourself.
(e.g. {{"subject": "User", "relation": "name", "object": "Gaurav"}}).
Do NOT use the user's actual name (e.g. do NOT use "Gaurav", "Jarvis", "Jay", or any other name) as the subject of factual_traits or episodic_events. 
The subject must strictly be the literal string "User" or "Assistant". No names allowed in the subject field whatsoever.

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

Return ONLY a single valid JSON object. Ensure all newlines within string values (like the "summary" string) are properly escaped as "\n" to maintain strict JSON compliance. Do NOT output unescaped literal newlines inside string properties.

Do NOT output markdown outside the JSON.

Do NOT wrap JSON inside code fences.

Do NOT include explanations.

===============================================================================
OBJECTIVE
===============================================================================

The input summary represents the assistant's accumulated Short-Term Memory (STM). It is formatted in structured markdown.

Reconcile, clean, and deduplicate the content under each header. Preserve the exact structure:
- `### 👤 USER PROFILE`
- `### 🎯 SESSION STATE`
- `### 📋 NEXT STEPS`

Improve the quality of the summary, resolving any contradictions, removing redundancies, and optimizing readability. Do NOT rewrite the structure, convert it into bulletless narrative paragraphs, or flatten it. Maintain the structured markdown layout.

REQUIRED SUMMARY FORMAT:
### 👤 USER PROFILE
- **Name**: [Preserve name/nickname]
- **Preferences**: [Clean/deduplicate stable preferences]
- **Key Attributes**: [Clean/deduplicate location, occupation, or identity facts]

### 🎯 SESSION STATE
- **Active Goal**: [Primary objective, consolidated]
- **Current Topic**: [Most recent active topic]
- **Completed Work**: [Consolidated list of completed tasks/decisions]
- **Progress**: [Coherent, consolidated progress flow]

### 📋 NEXT STEPS
- **Pending Tasks**: [Consolidated outstanding actions/commitments]
- **Open Questions**: [Consolidated open questions]

CONCISENESS & FORMULATING RULES:
- Use short, punchy fragments (NOT full conversational sentences).
- Do NOT repeat the same topic name or keywords in multiple fields.
- Deduplicate items; never repeat information.
- Format lists cleanly: do NOT leave trailing commas or incomplete punctuation.
- Keep sub-bullet lists concise, using simple words.

GOOD SUMMARY EXAMPLE (Note how the markdown is inside the JSON "summary" string, with newlines escaped as \\n):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav (Nickname: Jarvis)\\n- **Preferences**: Blue, dark mode\\n- **Key Attributes**: Lives in New York; loves swimming and travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Test available programming/search tools\\n- **Current Topic**: Tool capabilities overview\\n- **Completed Work**: Explained Python and Browser capabilities\\n- **Progress**: Introduced self and aligned on tool list\\n\\n### 📋 NEXT STEPS\\n- **Pending Tasks**: Execute user's first tool request\\n- **Open Questions**: Which tool does the user want to try first?",
  "facts_json": {{
    "episodic_events": [],
    "factual_traits": [],
    "semantic_concepts": [],
    "entities": {{}}
  }}
}}

BAD SUMMARY EXAMPLE (Avoid this structure):
{{
  "summary": "### 👤 USER PROFILE\\n- **Name**: Gaurav\\n- **Preferences**: Gaurav prefers the color blue, and Gaurav prefers dark mode, \\n- **Key Attributes**: Lives in New York, loves to swim, loves travel\\n\\n### 🎯 SESSION STATE\\n- **Active Goal**: Assist Gaurav with using the Jarvis tools\\n- **Current Topic**: Discussing the Jarvis tools\\n- **Completed Work**: Gave the Jarvis tools to Gaurav and discussed Jarvis tools\\n- **Progress**: Gaurav has introduced himself and wants to use Jarvis tools"
}}

CRITICAL — IDENTITY AND PERSONAL FACTS:
User identity facts (name, nickname, location, occupation, age, relationships,
stable preferences) must ALWAYS be preserved. Never drop or summarize away the actual
values of identity facts (e.g. do not turn "Name is Gaurav" into "User's name was discussed").
The actual values must remain explicitly written in the summary.

Do NOT include:
- Greetings or pleasantries that contain NO factual information.
- Pure acknowledgements or conversational filler (e.g., "okay", "got it", "thanks").
- Repeated information already present in the summary.
- Unnecessary chronological narration.
- Information that has no future conversational value.
- Empty template fields or placeholder strings like "[no information]". Just omit bullet items if they are empty.

===============================================================================
CURRENT SUMMARY
===============================================================================

{existing_summary}
"""

# Legacy / Unused Prompts (from prompt.py, preserved for reference/compatibility)

LEGACY_FIRST_EPOCH_PROMPT = """
    You are a conversation analyzer. Given the **first raw conversation chunk**, produce:

    1. A **detailed, coherent summary** of what happened (length should match the complexity of the conversation).
    2. A **JSON object** extracting ALL facts, decisions, preferences, and entities.

    ### Rules:
    - The summary must **capture all critical information** from the chunk. Do NOT artificially limit its length.
    - The JSON must include:
    - `facts`: Array of objects with `fact` (string), `source` ("user" or "assistant"), `type` ("explicit", "question", or "request").
    - `decisions`: Array of strings (e.g., ["User decided to explore London"]).
    - `preferences`: Array of strings (e.g., ["User prefers concise answers"]).
    - `entities`: Object with `Files/Paths`, `Variables/Functions`, `Errors/Bugs` (all arrays or ["NONE"]).

    ### Output Format:
    SUMMARY:
    [Your detailed summary here]

    ---
    FACTS_JSON:
    {{
    "facts": [
        {{"fact": "User asked about London", "source": "user", "type": "question"}},
        {{"fact": "Assistant listed capabilities", "source": "assistant", "type": "explicit"}}
    ],
    "decisions": ["User decided to explore London"],
    "preferences": ["User prefers concise answers"],
    "entities": {{
        "Files/Paths": ["NONE"],
        "Variables/Functions": ["NONE"],
        "Errors/Bugs": ["NONE"]
    }}
    }}
    ---
    CONVERSATION CHUNK:
    {chunk_text}
"""

LEGACY_ANCHORED_COMPRESSION_PROMPT = """
    You are a memory manager. Your job is to **rewrite and improve** the existing summary by merging it with new information from the conversation chunk.
    **Do NOT simply append the new chunk to the old summary.** Instead, create a **new, coherent summary** that:
    - Retains ALL critical information from the old summary.
    - Incorporates ALL new information from the chunk.
    - **Resolves any contradictions** between the old summary and new chunk (prioritize the new chunk if there is a conflict).
    - **Removes redundancies** (do not repeat the same fact twice).

    ### Rules:
    - If a fact in the new chunk **contradicts** the old summary, **resolve it in the new summary** and mark it in the JSON as `"type": "contradiction_resolved"`.
    - If a fact is **updated**, mark it in the JSON as `"type": "updated"`.
    - The JSON must only include **new or updated facts** from this chunk.

    ### Output Format:
    SUMMARY:
    [Your new, rewritten, and improved summary here]

    ---
    FACTS_JSON:
    {{
    "new_facts": [
        {{"fact": "New or updated fact text", "source": "user" | "assistant", "type": "explicit" | "contradiction_resolved" | "updated"}}
    ],
    "new_decisions": ["New decision"],
    "new_preferences": ["New preference"],
    "new_entities": {{
        "Files/Paths": ["new_path"],
        "Variables/Functions": ["new_var"],
        "Errors/Bugs": ["new_error"]
    }}
    }}
    ---
    EXISTING SUMMARY:
    {existing_summary}

    NEW CONVERSATION CHUNK:
    {chunk_text}
"""

LEGACY_GROUNDING_PROMPT = """
    You are a grounding expert. Given **ALL previous compression summaries**, produce:

    1. A **holistic, narrative summary** of the entire conversation so far (describe the flow, key events, and current state).
    2. A **canonical JSON** that:
    - Merges ALL facts from all epochs.
    - **Resolves ALL contradictions** (keep the most recent version of any fact).
    - Tracks **repetitions** (count + epochs where each fact appears).
    - Includes **source** and **resolution** for contradictions.

    ### Rules:
    - The holistic summary should **tell the story** of the conversation (e.g., "The user started by asking about X, then explored Y, and finally decided Z").
    - The canonical JSON should be the **single source of truth** for all facts.

    ### Output Format:
    HOLISTIC_SUMMARY:
    [Your narrative summary of the entire conversation here]

    ---
    CANONICAL_FACTS_JSON:
    {{
    "facts": [
        {{
        "fact": "Fact text",
        "source": "user" | "assistant",
        "type": "explicit" | "contradiction_resolved" | "updated",
        "count": 2,
        "epochs": [1, 3],
        "resolution": "Final resolved value" | null
        }}
    ],
    "decisions": ["Decision 1", "Decision 2"],
    "preferences": ["Preference 1"],
    "entities": {{
        "Files/Paths": ["path1", "path2"],
        "Variables/Functions": ["var1"],
        "Errors/Bugs": ["error1"]
    }},
    "metadata": {{
        "total_facts": 10,
        "contradictions_resolved": 2,
        "epochs_merged": [1, 2, 3]
    }}
    }}
    ---
    ALL PREVIOUS SUMMARIES (oldest to newest):
    {all_summaries}
"""
