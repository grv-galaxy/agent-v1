---
name: search_skill
description: Use when the user asks for factual information, current events, biographies, or needs data from external sources.
---

# Search Skill Instructions

You are equipped with search tools to look up factual information. 

## When to use which tool

### 1. Wikipedia Search Tool (`wikipedia_search`)
Wikipedia is highly reliable for stable, objective, and well-documented facts, particularly in fields that lack emotional or political bias.
Use this tool for:
- Historical facts and timelines
- Biographies of notable figures
- Geography (countries, cities, capitals)
- Basic science, mathematics, and established theories
- Any query seeking general, static, consensus-driven information.

**How to call:**
Output a raw JSON block wrapped in `@jsonstart` and `@jsonstop` tags. You must include a `query` parameter.
Example:
@jsonstart
{
  "tool": "wikipedia_search",
  "query": "current CM of Assam",
  "reason": "Looking up factual information on Wikipedia",
  "logo": "Searching"
}
@jsonstop

**Important:** The backend will intercept this JSON block and stream the resulting structured data directly to the user's interface. You do not need to wait for the data to come back into your context window or synthesize the answer yourself. Just output the tool block and you are done.
