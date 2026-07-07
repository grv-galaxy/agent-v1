# Skill: Long-Term Memory (LTM) & Backend Development Agent

## Objective
You are tasked with analyzing the existing Long-Term Memory (LTM) documentation and the backend folder structure to autonomously guide and implement the development of the `backend/mcp/memory/` module. You must analyze what has been built, propose the next logical file to create, and wait for explicit user approval before generating it.

---

## 1. Context & Reference Files
You are operating inside the root directory of the **`agent-v1`** project. Before taking any actions or writing code, you must read, parse, and deeply understand the contents of the following two reference documents:

* **LTM Core Logic Documentation:**
    * Path: `C:\Users\kumar\Documents\agent-v1\docs\ltm_doc.md`
    * *Purpose:* Understand the architectural design, memory mechanics, and rules for the long-term memory system.
* **Backend Architecture & Folder Structure:**
    * Path: `C:\Users\kumar\Documents\agent-v1\docs\backend_folder.md`
    * *Purpose:* Understand how the backend components are organized, how imports are structured, and how new modules fit into the existing system.

---

## 2. Target Workspace
Your primary development focus is restricted to the following subdirectory:
* `backend/mcp/memory/`

---

## 3. Step-by-Step Execution Workflow

### Step 1: Analyze Existing Implementation
1. Read the reference files listed in Section 1.
2. Inspect the current files inside the `backend/mcp/memory/` directory to see what has already been created.
3. Cross-reference the existing code against the architecture outlined in `ltm_doc.md`.

### Step 2: Propose Next Step
Based on your analysis, determine the absolute next file that needs to be created to advance the memory module securely and efficiently. 

Present your findings to the user in the following format:
> **Analysis:** [Brief summary of what is currently built]
> **Proposed Next File:** `backend/mcp/memory/[filename].ext`
> **Purpose:** [Why this file is necessary right now and what it will handle]
>
> *Waiting for your confirmation. Please reply with "okay" to proceed with creating this file.*

### Step 3: Interactive Confirmation (Strict Guardrail)
* **DO NOT** create the file automatically.
* You must pause execution and wait for the user to reply.
* **Only when the user explicitly replies with "okay" or gives confirmation**, proceed to Step 4.

### Step 4: File Generation
1. Generate the complete, production-ready code for the approved file.
2. Ensure it perfectly aligns with the guidelines in `ltm_doc.md` and uses the correct path structure found in `backend_folder.md`.
3. Save the file to its designated path inside `backend/mcp/memory/`.