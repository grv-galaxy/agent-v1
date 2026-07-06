from backend.mcp.search.wikipedia.search_tool import wikipedia_search
import json

if __name__ == "__main__":
    res = wikipedia_search("smallest country by size", 3)
    print(json.dumps(res, indent=2))
