import os
from datetime import datetime
from typing import AsyncGenerator
from openai import AsyncOpenAI
from src.search_agent.config import settings

# Initialize AsyncOpenAI with Groq base URL and API key
client = AsyncOpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=settings.groq_api_key
)

def load_prompt() -> str:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "synthesize.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def format_context(results: list[dict]) -> str:
    """Format search results into a numbered list for the prompt."""
    context_parts = []
    for i, res in enumerate(results, start=1):
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
    system_prompt_template = load_prompt()
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
