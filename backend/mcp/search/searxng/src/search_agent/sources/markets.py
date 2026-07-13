import asyncio
from src.search_agent.utils.circuit_breaker import circuit_breaker

# We will wrap the synchronous library calls in their own inner functions
def _sync_nse(query: str):
    from nsepython import nse_quote_ltp, nse_eq
    # nsepython takes specific symbols, so this is mostly useful if query is a symbol like "SBIN"
    # We will just try to fetch it as a symbol. If it fails, it throws an error.
    try:
        # Try getting complete quote info
        data = nse_eq(query.upper())
        if 'priceInfo' in data:
            price = data['priceInfo'].get('lastPrice', 'Unknown')
            pChange = data['priceInfo'].get('pChange', 'Unknown')
            company = data['info'].get('companyName', query.upper())
            
            return [{
                "title": f"NSE: {company} ({query.upper()})",
                "url": f"https://www.nseindia.com/get-quotes/equity?symbol={query.upper()}",
                "content": f"Last Price: {price}\nChange: {pChange}%"
            }]
    except Exception as e:
        # Fallback to just simple LTP
        ltp = nse_quote_ltp(query.upper())
        if ltp:
            return [{
                "title": f"NSE: {query.upper()}",
                "url": f"https://www.nseindia.com/get-quotes/equity?symbol={query.upper()}",
                "content": f"Last Price: {ltp}"
            }]
    return []

def _sync_bse(query: str):
    from bsedata.bse import BSE
    b = BSE(update_codes=True) # Ensure codes are loaded
    
    # query needs to be the scrip code, but let's try to resolve it from symbol
    # bsedata gives b.getScripCodes() -> dict of code: name
    # We just try to get the quote if we assume it's a code, or we search for the name
    codes = b.getScripCodes()
    scrip_code = None
    
    # Try direct code match
    if query in codes:
        scrip_code = query
    else:
        # Search by name/symbol
        query_upper = query.upper()
        for code, name in codes.items():
            if query_upper in name.upper() or query_upper == name.upper():
                scrip_code = code
                break
                
    if scrip_code:
        q = b.getQuote(scrip_code)
        return [{
            "title": f"BSE: {q.get('companyName')} ({scrip_code})",
            "url": f"https://www.bseindia.com/stock-share-price/{scrip_code}",
            "content": f"Current Price: {q.get('currentValue')}\nChange: {q.get('pChange')}%"
        }]
    return []

def _sync_yfinance(query: str):
    import yfinance as yf
    # YFinance expects tickers like "AAPL" or "RELIANCE.NS"
    ticker = yf.Ticker(query.upper())
    info = ticker.info
    
    if "currentPrice" in info or "regularMarketPrice" in info:
        price = info.get("currentPrice") or info.get("regularMarketPrice", "Unknown")
        name = info.get("shortName", query.upper())
        currency = info.get("currency", "")
        return [{
            "title": f"Yahoo Finance: {name} ({query.upper()})",
            "url": f"https://finance.yahoo.com/quote/{query.upper()}",
            "content": f"Current Price: {price} {currency}\nSector: {info.get('sector', 'Unknown')}"
        }]
    return []


@circuit_breaker(failure_threshold=3, recovery_timeout=300)
async def search_nse(query: str, entities: list[str] = None) -> list[dict]:
    """Search National Stock Exchange live data."""
    symbol = query
    if entities and len(entities) > 0:
        symbol = entities[0]
        
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_nse, symbol), timeout=5.0)
    except asyncio.TimeoutError:
        raise Exception("NSE fetch timed out")

@circuit_breaker(failure_threshold=3, recovery_timeout=300)
async def search_bse(query: str, entities: list[str] = None) -> list[dict]:
    """Search Bombay Stock Exchange live data."""
    symbol = query
    if entities and len(entities) > 0:
        symbol = entities[0]
        
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_bse, symbol), timeout=5.0)
    except asyncio.TimeoutError:
        raise Exception("BSE fetch timed out")

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
