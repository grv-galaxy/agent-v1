import json
import time
import os
from pathlib import Path
from datetime import datetime
from openai import AsyncOpenAI
from .schemas import ClassifierOutput
from .config import settings

# Load system prompt
PROMPT_PATH = Path(__file__).parent / "prompts" / "classify.txt"
with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# Initialize AsyncOpenAI client for Groq
client = AsyncOpenAI(
    api_key=settings.groq_api_key or "dummy_api_key_for_testing",
    base_url="https://api.groq.com/openai/v1"
)

async def classify_query(query: str) -> ClassifierOutput:
    """
    Classifies the user query using the Groq LLM API.
    Returns a strict JSON parsed into a ClassifierOutput Pydantic model.
    """
    start_time = time.perf_counter()
    
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_prompt = SYSTEM_PROMPT.replace("{current_date}", current_date)
    
    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": formatted_prompt},
            {"role": "user", "content": query}
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    print(f"[telemetry] classify stage took {elapsed_ms:.2f} ms")
    
    content = response.choices[0].message.content
    
    # Parse the returned JSON string into our Pydantic model
    # Groq should return valid JSON because of response_format json_object
    parsed_dict = json.loads(content)
    return ClassifierOutput(**parsed_dict)

if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Only run if API key is set
        if not settings.groq_api_key:
            print("Set GROQ_API_KEY in .env to run manual tests.")
            return
            
        test_queries = [
            "latest advances in solid state batteries",
            "AAPL stock price today",
            "best indian restaurants in new york"
        ]
        
        for q in test_queries:
            print(f"\nQuery: {q}")
            try:
                res = await classify_query(q)
                print(res.model_dump_json(indent=2))
            except Exception as e:
                print(f"Error: {e}")
                
    asyncio.run(main())
