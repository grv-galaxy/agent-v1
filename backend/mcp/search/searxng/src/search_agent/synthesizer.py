import os
import asyncio
from datetime import datetime
from typing import AsyncGenerator, List, Tuple, Dict
from openai import AsyncOpenAI
from src.search_agent.config import settings

# Initialize AsyncOpenAI with Groq base URL and API key
client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key
)

def load_prompt(filename: str = "synthesize.txt") -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def format_context(results: list[dict], start_idx: int = 1) -> str:
    """Format search results into a numbered list for the prompt."""
    context_parts = []
    for i, res in enumerate(results, start=start_idx):
        title = res.get("title", "No Title")
        content = res.get("content", "No Content")
        url = res.get("url", "No URL")
        context_parts.append(f"Source [{i}]\nTitle: {title}\nURL: {url}\nContent: {content}\n")
    return "\n".join(context_parts)

async def synthesize(query: str, top_results: list[dict]) -> AsyncGenerator[str, None]:
    """
    Streams a synthesized response from the LLM based on the query and top search results.
    Yields chunks of text as they arrive.
    """
    system_prompt_template = load_prompt("synthesize.txt")
    context = format_context(top_results)
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_message = system_prompt_template.replace("{context}", context).replace("{current_date}", current_date)
    
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ],
        stream=True,
        temperature=0.2, # Low temperature for factual synthesis
    )
    
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


async def _generate_mini_report(sub_query: str, sub_query_results: list[dict], global_start_idx: int) -> str:
    """Generates a mini report for a single sub-query (Map step)."""
    system_prompt_template = load_prompt("synthesize_mini.txt")
    context = format_context(sub_query_results, start_idx=global_start_idx)
    
    system_message = system_prompt_template.replace("{context}", context).replace("{sub_query}", sub_query)
    
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Write a mini-report for this sub-query: {sub_query}"}
        ],
        stream=False,
        temperature=0.2,
    )
    return response.choices[0].message.content


async def synthesize_deep_research(original_query: str, sub_queries: List[str], parallel_results_top_3: List[List[dict]]) -> AsyncGenerator[str, None]:
    """
    Map-Reduce synthesis for Deep Research mode.
    1. Map: Generates a mini-report for each sub-query.
    2. Reduce: Streams a final synthesis combining the mini-reports.
    """
    # 1. Map Step
    map_tasks = []
    global_start_idx = 1
    
    for sq, sq_results in zip(sub_queries, parallel_results_top_3):
        task = _generate_mini_report(sq, sq_results, global_start_idx)
        map_tasks.append(task)
        global_start_idx += len(sq_results)
        
    # Execute Map step concurrently
    mini_reports = await asyncio.gather(*map_tasks, return_exceptions=True)
    
    # Format mini-reports
    reports_text_parts = []
    for sq, report in zip(sub_queries, mini_reports):
        if isinstance(report, Exception):
            report_text = f"Error generating report: {report}"
        else:
            report_text = report
        reports_text_parts.append(f"### Sub-Query: {sq}\n{report_text}\n")
        
    combined_reports = "\n".join(reports_text_parts)
    
    # 2. Reduce Step
    system_prompt_template = load_prompt("synthesize_final.txt")
    system_message = system_prompt_template.replace("{original_query}", original_query).replace("{mini_reports}", combined_reports)
    
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Synthesize a final response for the query: {original_query}"}
        ],
        stream=True,
        temperature=0.2,
    )
    
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

# For manual testing
if __name__ == "__main__":
    import asyncio
    
    async def run_manual_test():
        query = "Who won the 2024 Super Bowl and what was the score?"
        mock_results = [
            {
                "title": "Super Bowl LVIII",
                "content": "The Kansas City Chiefs defeated the San Francisco 49ers 25-22 in overtime to win Super Bowl LVIII.",
                "url": "https://example.com/sb58"
            }
        ]
        
        print("Streaming response:")
        async for chunk in synthesize(query, mock_results):
            print(chunk, end="", flush=True)
        print("\n\nDone.")
        
    asyncio.run(run_manual_test())
