import asyncio
from src.search_agent.utils.circuit_breaker import circuit_breaker
from src.search_agent.utils.cache import async_ttl_cache

def _sync_yfinance(query: str):
    import yfinance as yf
    import requests
    import urllib.parse
    
    # Resolve ticker via Yahoo Search API
    symbol = query.upper()
    try:
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(search_url, headers=headers, timeout=3.0).json()
        if "quotes" in res and len(res["quotes"]) > 0:
            symbol = res["quotes"][0]["symbol"]
    except Exception:
        pass
        
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    if "currentPrice" in info or "regularMarketPrice" in info:
        price = info.get("currentPrice") or info.get("regularMarketPrice", "Unknown")
        name = info.get("shortName", symbol)
        currency = info.get("currency", "")
        return [{
            "title": f"Yahoo Finance: {name} ({symbol})",
            "url": f"https://finance.yahoo.com/quote/{symbol}",
            "content": f"Current Price: {price} {currency}\nSector: {info.get('sector', 'Unknown')}"
        }]
    return []


@async_ttl_cache(ttl=300)
@circuit_breaker(failure_threshold=3, recovery_timeout=300)
async def search_yfinance(query: str, entities: list[str] = None) -> list[dict]:
    """Search Yahoo Finance live data."""
    symbol = query
    if entities and len(entities) > 0:
        symbol = entities[0]
        
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_yfinance, symbol), timeout=5.0)
    except asyncio.TimeoutError:
        raise Exception("YFinance fetch timed out")


@async_ttl_cache(ttl=300)
@circuit_breaker(failure_threshold=3, recovery_timeout=300)
async def search_indian_markets(query: str, entities: list[str] = None) -> list[dict]:
    """Search Indian Markets (NSE/BSE) using Yahoo Finance for speed and reliability."""
    symbol = query
    if entities and len(entities) > 0:
        symbol = entities[0]
        
    # Append .NS for NSE by default if no suffix provided
    if not symbol.endswith(".NS") and not symbol.endswith(".BO"):
        symbol = f"{symbol.upper()}.NS"
        
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_yfinance, symbol), timeout=5.0)
    except asyncio.TimeoutError:
        raise Exception("Indian Markets fetch timed out")
