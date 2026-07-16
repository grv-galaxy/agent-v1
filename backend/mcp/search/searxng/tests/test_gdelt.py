import httpx
import urllib.parse
import traceback

def test_gdelt():
    query = "reliance industry"
    encoded_query = urllib.parse.quote(query)
    url = f"https://api.gdeltproject.org/api/v2/search/search?query={encoded_query}&format=json&mode=artlist"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = httpx.get(url, headers=headers, timeout=10.0)
        print("Status code:", resp.status_code)
        data = resp.json()
        print("Parsed JSON items:", len(data.get("articles", [])))
    except Exception as e:
        print("Exception:", type(e).__name__, e)

test_gdelt()
