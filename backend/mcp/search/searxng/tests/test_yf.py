import requests

def search_ticker(query):
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers).json()
    if "quotes" in res and len(res["quotes"]) > 0:
        return res["quotes"][0]["symbol"]
    return query

print(search_ticker("APPLE"))
print(search_ticker("NVIDIA"))
print(search_ticker("RELIANCE INDUSTRY"))
