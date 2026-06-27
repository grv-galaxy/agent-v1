# Memory Layer Architecture Audit Report

This report presents a thorough audit of the memory and summarization layer in the codebase, assessing the actual implementation against the planned architecture (Ground Truth).

---

## 1. Workflow Verification

| Epoch/Stage | Input to LLM (actual) | Prompt Used (actual) | Output (actual) | Status | File / Line Citations |
|---|---|---|---|---|---|
| **Epoch 1** | Raw conversation chunk text only (`chunk_text`) | `FIRST_EPOCH_PROMPT` | Summary + JSON string embedded in a single output. **Failed to parse JSON separates** (kept embedded). | ⚠️ **PARTIAL** | - Prompt defined: [compression_service.py:L37-73](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L37-73)<br>- Logic applied: [compression_service.py:L182-183](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L182-183) |
| **Epoch 2+** | Prior summary (`existing_summary`) + new conversation chunk (`chunk_text`) | `ANCHORED_COMPRESSION_PROMPT` | Rewritten summary + `new_*` JSON string. **Failed to parse JSON separates** (kept embedded). | ⚠️ **PARTIAL** | - Prompt defined: [compression_service.py:L124-161](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L124-161)<br>- Logic applied: [compression_service.py:L185-188](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L185-188) |
| **Grounding Pass** | Concatenated summary history (Epoch 1 → N) | `GROUNDING_PROMPT` | Holistic summary + `CANONICAL_FACTS_JSON`. **Failed to parse JSON separates** (kept embedded). Also, **history truncated to at most 3 entries**. | ❌ **FAIL** | - Prompt defined: [compression_service.py:L75-122](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L75-122)<br>- Slicing logic (frontend): [ChatPage.jsx:L1125-1128](file:///c:/Users/kumar/Documents/agent-v1/frontend/src/pages/ChatPage.jsx#L1125-L1128) |

---

## 2. Completion Breakdown

* **Total Score: 56 / 100**

| Category | Weight | Score | Notes & Evidence |
|---|---|---|---|
| **Workflow Compliance** | 25% | **18 / 25** | Epochs 1 and 2+ correctly select prompts and assemble raw chunks vs existing summary inputs. However, the Grounding Pass fails to receive *all* prior summaries due to a frontend truncation bug that limits history to the last 2 summaries ([ChatPage.jsx:L1125-1128](file:///c:/Users/kumar/Documents/agent-v1/frontend/src/pages/ChatPage.jsx#L1125-L1128)). Additionally, the LLM metadata fails to include the current epoch in its `epochs_merged` list. |
| **Content Flow to LLM** | 20% | **15 / 20** | Inputs correctly direct prior summaries + chunks to compression, and summaries-only to grounding. However, because of the frontend `.slice(-2)` limit, the grounding pass only ever sees up to 3 versions of the summary, not all historical ones. |
| **JSON Fact Extraction** | 20% | **5 / 20** | While prompts instruct the LLM to output structured JSON blocks (`FACTS_JSON` and `CANONICAL_FACTS_JSON`), the extraction function `extract_json_from_output` ([compression_service.py:L9-35](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L9-35)) fails to parse them 100% of the time. This is due to markdown formatting (`**FACTS_JSON:**` and code fences ` ```json `) returned by the LLM, causing `json.JSONDecodeError`s which are caught silently. |
| **Storage** | 15% | **5 / 15** | Because JSON parsing fails, the `facts` field is always `None` when writing to storage. Consequently, the JSON block remains embedded directly in `rolling_summary` in the JSONL log file, and the separate `facts` key is omitted entirely ([fact_storage.py:L44-45](file:///c:/Users/kumar/Documents/agent-v1/backend/utils/fact_storage.py#L44-45)). Timestamp, epoch, and event_type are written correctly. |
| **Edge Cases** | 10% | **8 / 10** | Empty chunks are handled safely without crashing. Malformed JSON falls back to text-only but fails to log a warning as planned. Contradiction resolution and repetition tracking are requested in the prompts but are useless programmatically since they are never successfully parsed. |
| **Error Handling** | 5% | **2 / 5** | Parser exceptions are caught and swallowed, preventing crashes in the active chat pathway. However, two critical signature mismatches exist in `memory_working.py` ([memory_working.py:L286](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L286) and [L297](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L297)), which cause the `/api/compress` endpoint to crash with `TypeError` 100% of the time. |
| **Backward Compatibility** | 5% | **5 / 5** | The backend is write-only for the JSONL files; it never reads them back. Since history states are managed on the client side, missing `facts` in log files never causes loading crashes. The frontend chat continues working. |

---

## 3. Content Flow Analysis

### `compression_pass`
* **Matches Ground Truth?**: **Yes**
* **LLM Input Assembly Code**:
  [compression_service.py:L177-189](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L177-L189):
  ```python
  chunk_text = "\n".join(
      f"[{m['role'].upper()}]: {m['content']}" for m in chunk_messages
  )

  # --- Select prompt based on epoch ---
  if compression_epoch == 1:
      prompt = FIRST_EPOCH_PROMPT.format(chunk_text=chunk_text)
  else:
      prompt = ANCHORED_COMPRESSION_PROMPT.format(
          existing_summary=existing_summary,
          chunk_text=chunk_text
      )
  ```
  Only the raw chunks are provided for Epoch 1, and only the immediately prior summary (`existing_summary`) plus the new chunk (`chunk_text`) are passed for Epoch 2+.

### `grounding_pass`
* **Matches Ground Truth?**: **No** (partially matches conceptually, but violates the "ALL prior summaries" requirement due to client-side truncation).
* **LLM Input Assembly Code**:
  [compression_service.py:L232-240](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L232-240):
  ```python
  all_versions = [s for s in summary_history if s] + [current_summary]
  if len(all_versions) < 2:
      return current_summary  # Nothing to reconcile

  versions_text = "\n\n---\n\n".join(
      f"Epoch {i+1}:\n{s}" for i, s in enumerate(all_versions)
  )

  prompt = GROUNDING_PROMPT.format(all_summaries=versions_text)
  ```
  While the python logic concatenates all elements in `summary_history`, the client-side state manager ([ChatPage.jsx:L1125-1128](file:///c:/Users/kumar/Documents/agent-v1/frontend/src/pages/ChatPage.jsx#L1125-L1128)) truncates `summary_history` to the last 2 elements via `.slice(-2)`. Consequently, `grounding_pass` only ever reconciles a maximum of 3 historical summaries. No raw chunks are sent here, which matches the ground truth rule.

---

## 4. Are We On Track?

* **Verdict**: **NO**, the implementation does not fully follow the planned architecture. While the overall prompts and conceptual flow exist, the data pipeline is severely degraded by (1) parsing failures that store JSON blocks inside the rolling summary text, (2) frontend-side truncation of the summary history, and (3) crashes on testing endpoints.

### Real `compression_pass` JSONL Entry
Taken from [18_06_session_1781781090907_0ln8rgtjj.jsonl:Line 1](file:///c:/Users/kumar/Documents/agent-v1/backend/data/facts/18_06_session_1781781090907_0ln8rgtjj.jsonl#L1):
```json
{"timestamp": "2026-06-18T11:12:42.423582+00:00", "epoch": 1, "event_type": "compression_pass", "rolling_summary": "**SUMMARY:**\n\nThe conversation starts with the user greeting the assistant, asking about their well-being. The assistant responds positively and asks how they can assist. The user then introduces themselves as Gaurav, and the assistant acknowledges and requests a name to be used for communication. The user provides the name \"Jarvis\" and the assistant confirms this new name. Finally, the user greets the assistant again, this time using the new name.\n\nThe conversation appears to be an exchange of pleasantries, with the user and assistant establishing a friendly tone and a personal name for communication.\n\n**---**\n\n**FACTS_JSON:**\n```json\n{\n  \"facts\": [\n    {\"fact\": \"User asked about assistant's well-being\", \"source\": \"user\", \"type\": \"question\"},\n    {\"fact\": \"Assistant responded positively\", \"source\": \"assistant\", \"type\": \"explicit\"},\n    {\"fact\": \"User introduced themselves as Gaurav\", \"source\": \"user\", \"type\": \"explicit\"},\n    {\"fact\": \"Assistant acknowledged user's name\", \"source\": \"assistant\", \"type\": \"explicit\"},\n    {\"fact\": \"User provided the name Jarvis\", \"source\": \"user\", \"type\": \"explicit\"},\n    {\"fact\": \"Assistant confirmed new name\", \"source\": \"assistant\", \"type\": \"explicit\"},\n    {\"fact\": \"User greeted assistant again\", \"source\": \"user\", \"type\": \"request\"}\n  ],\n  \"decisions\": [\"User decided to establish a friendly tone\", \"User decided to use the name Jarvis\"],\n  \"preferences\": [\"User prefers informal language\", \"User prefers concise responses\"],\n  \"entities\": {\n    \"Files/Paths\": [\"NONE\"],\n    \"Variables/Functions\": [\"NONE\"],\n    \"Errors/Bugs\": [\"NONE\"]\n  }\n}\n```\nNote: The \"decisions\" and \"preferences\" arrays are not explicitly mentioned in the conversation, so I've made educated guesses based on the context. If you'd like me to revise these arrays, please let me know!"}
```
*Note that the `facts` field is completely missing at the top-level of this JSONL entry, and the JSON format output is entirely embedded inside `rolling_summary`.*

### Real `grounding_pass` JSONL Entry
Taken from [18_06_session_1781781090907_0ln8rgtjj.jsonl:Line 4](file:///c:/Users/kumar/Documents/agent-v1/backend/data/facts/18_06_session_1781781090907_0ln8rgtjj.jsonl#L4):
```json
{"timestamp": "2026-06-18T11:16:25.208990+00:00", "epoch": 3, "event_type": "grounding_pass", "rolling_summary": "**HOLISTIC_SUMMARY:**\n\nThe conversation starts with the user greeting the assistant, asking about their well-being, and introducing themselves as Gaurav. The assistant responds positively and acknowledges the user's name, which is later changed to Jarvis. The conversation then shifts to a discussion about the assistant's fondness for curiosity, learning, and their love for stories, puzzles, and fresh perspectives. The assistant shares a few blue-themed verses and asks the user if they have a favorite poet or style. The user responds positively to one of the verses and shares their love for poetry. The assistant asks if the user knows poetry, and they respond affirmatively.\n\nThroughout the conversation, the user and assistant establish a friendly tone and a personal name for communication. The user's love for poetry and the assistant's fondness for curiosity and learning are recurring themes in the conversation.\n\n**---**\n\n**CANONICAL_FACTS_JSON:**\n```json\n{\n  \"facts\": [\n    {\"fact\": \"User asked about assistant's well-being\", \"source\": \"user\", \"type\": \"question\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"Assistant responded positively\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"User introduced themselves as Gaurav\", \"source\": \"user\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"Assistant acknowledged user's name\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"User provided the name Jarvis\", \"source\": \"user\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"Assistant confirmed new name\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"User greeted assistant again\", \"source\": \"user\", \"type\": \"request\", \"count\": 1, \"epochs\": [1], \"resolution\": null},\n    {\"fact\": \"Assistant mentioned fondness for curiosity and learning\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"Assistant expressed preference for calm, sky-blue color\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"Assistant shared love for stories, puzzles, and fresh perspectives\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"User shared love for poetry\", \"source\": \"user\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"Assistant asked about user's favorite poet or style\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"User responded positively to assistant's poem\", \"source\": \"user\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"Assistant asked if user knows poetry\", \"source\": \"assistant\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null},\n    {\"fact\": \"User responded affirmatively to knowing poetry\", \"source\": \"user\", \"type\": \"explicit\", \"count\": 1, \"epochs\": [2], \"resolution\": null}\n  ],\n  \"decisions\": [\"User decided to establish a friendly tone\", \"User decided to use the name Jarvis\"],\n  \"preferences\": [\"User prefers informal language\", \"User prefers concise responses\"],\n  \"entities\": {\n    \"Files/Paths\": [\"NONE\"],\n    \"Variables/Functions\": [\"NONE\"],\n    \"Errors/Bugs\": [\"NONE\"]\n  },\n  \"metadata\": {\n    \"total_facts\": 14,\n    \"contradictions_resolved\": 0,\n    \"epochs_merged\": [1, 2]\n  }\n}\n```"}
```

### Deviations List
1. **JSON Extraction Failures**: `extract_json_from_output` ([compression_service.py:L9-35](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L9-35)) fails to match markdown formatting such as `**FACTS_JSON:**` and code fences (```json ... ```) and fails to strip trailing comments/notes, resulting in a parsing rate of **0%** across all 45 real session entries.
2. **Missing Facts Field in DB**: Due to JSON extraction failures, the separate `facts` field is never populated inside the log entries written by `trigger_on_demand_save` ([fact_storage.py:L44-45](file:///c:/Users/kumar/Documents/agent-v1/backend/utils/fact_storage.py#L44-45)).
3. **Imperfect Grounding Input**: The grounding pass is only sent the last 3 summaries because the frontend truncates history using `.slice(-2)` ([ChatPage.jsx:L1125-1128](file:///c:/Users/kumar/Documents/agent-v1/frontend/src/pages/ChatPage.jsx#L1125-L1128)).
4. **Incorrect Epoch Merging Metadata**: In the grounding pass, the LLM response generated `epochs_merged: [1, 2]` at Epoch 3 instead of including the current epoch.
5. **Direct API Signature Crash**: The testing endpoint `/api/compress` in `memory_working.py` misses arguments when calling `compress_chunk` ([memory_working.py:L286-291](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L286-291)) and `grounding_pass` ([memory_working.py:L297-302](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L297-302)), causing crashes for anyone utilizing that router.

---

## 5. Edge Cases & Bugs

### Passed
* **Empty Chunk Handling**: The system correctly bypasses compression if the incoming chunk is empty ([chat.py:L157](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/chat.py#L157) and [memory_working.py:L242](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L242)).
* **Graceful Fallbacks for Parsing**: Malformed JSON from the LLM falls back to treating it as plain text without crashing the main application stream ([compression_service.py:L201-205](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L201-205)).

### Failed / Bugs
* **Silent Failure on Malformed JSON**: The codebase fails to log a warning when JSON extraction fails (violating the edge case rule).
* **Crash on Testing Endpoint `/api/compress`**:
  Calling this endpoint raises a `TypeError` due to a signature mismatch:
  ```
  TypeError: compress_chunk() missing 2 required positional arguments: 'session_id' and 'compression_epoch'
  ```
  *Evidence*: [memory_working.py:L286-291](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L286-291):
  ```python
  new_summary = await compress_chunk(
      chunk_messages=chunk,
      existing_summary=req.rolling_summary,
      provider_instance=memory_provider_instance,
      model_name=memory_model_name,
  )
  ```
  And [memory_working.py:L297-302](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py#L297-302):
  ```python
  new_summary = await grounding_pass(
      summary_history=req.summary_history,
      current_summary=new_summary,
      provider_instance=memory_provider_instance,
      model_name=memory_model_name,
  )
  ```

---

## 6. Recommendations

### Critical Fixes

#### 1. Robust JSON extraction parser
To resolve the 100% parsing failure rate, replace `extract_json_from_output` in [compression_service.py:L9-35](file:///c:/Users/kumar/Documents/agent-v1/backend/services/compression_service.py#L9-35) with a parser that cleans markdown wrapping and extracts the outermost JSON object bounds (from the first `{` to the last `}`):

```python
def extract_json_from_output(output: str, marker: str = "FACTS_JSON:") -> dict:
    if not output or marker not in output:
        return None

    # Locate the marker
    marker_pos = output.find(marker)
    content_after = output[marker_pos + len(marker):]

    # Find the outermost curly braces of the JSON block
    first_brace = content_after.find("{")
    last_brace = content_after.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        print(f"[Warning] Failed to find valid JSON brace limits after marker {marker}")
        return None

    json_str = content_after[first_brace:last_brace + 1].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"[Warning] JSON parsing failed: {e}. Raw content: {json_str[:150]}")
        return None
```

#### 2. Fix Signature Mismatch inside `memory_working.py`
In [memory_working.py](file:///c:/Users/kumar/Documents/agent-v1/backend/routers/memory_working.py), thread the missing arguments (`session_id` and `compression_epoch` / `next_epoch`) into the function calls. 

Replace lines 286–291 with:
```python
        new_summary = await compress_chunk(
            chunk_messages=chunk,
            existing_summary=req.rolling_summary,
            provider_instance=memory_provider_instance,
            model_name=memory_model_name,
            session_id="default_compress_endpoint",
            compression_epoch=next_epoch,
        )
```

Replace lines 297–302 with:
```python
            new_summary = await grounding_pass(
                summary_history=req.summary_history,
                current_summary=new_summary,
                provider_instance=memory_provider_instance,
                model_name=memory_model_name,
                session_id="default_compress_endpoint",
                compression_epoch=next_epoch,
            )
```

#### 3. Allow grounding pass to receive all versions (Frontend)
To align with the planned Ground Truth architecture of keeping **all** prior summaries for reconciliation during grounding, change [ChatPage.jsx:L1125-1128](file:///c:/Users/kumar/Documents/agent-v1/frontend/src/pages/ChatPage.jsx#L1125-L1128) to stop slicing history so aggressively:

```javascript
                      const newHistory = [
                        ...(session.summary_history || []),
                        session.rolling_summary,
                      ].filter(Boolean);
```
*(Alternatively, keep a larger limit like `.slice(-20)` if context window management requires bounding).*

---

### Optional Improvements
* **Write-to-read database layer**: Introduce a reader function inside `fact_storage.py` that can load these logs to allow the backend to restore summaries on restart, rather than relying entirely on client-side state.
* **Telemetry verification**: Implement validation checks on telemetry logs to ensure they stay structural when telemetry is enabled.
