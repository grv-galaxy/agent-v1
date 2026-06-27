FIRST_EPOCH_PROMPT = """
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












ANCHORED_COMPRESSION_PROMPT = """
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












GROUNDING_PROMPT = """
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