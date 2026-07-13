import asyncio
import pytest
from src.search_agent.sources.markets import search_nse, search_bse, search_yfinance

@pytest.mark.asyncio
async def test_tier4():
    print("Testing NSE (State Bank of India - SBIN)...")
    try:
        res = await search_nse("SBIN", ["SBIN"])
        print(f"NSE: {len(res)} results")
        if res: print(res[0]['content'])
    except Exception as e:
        print(f"NSE failed: {e}")

    print("\nTesting BSE (State Bank of India - 500112)...")
    try:
        # 500112 is SBI's BSE scrip code. We'll search by name which is supported by our wrapper
        res = await search_bse("State Bank of India", ["State Bank of India"])
        print(f"BSE: {len(res)} results")
        if res: print(res[0]['content'])
    except Exception as e:
        print(f"BSE failed: {e}")

    print("\nTesting Yahoo Finance (Apple - AAPL)...")
    try:
        res = await search_yfinance("AAPL", ["AAPL"])
        print(f"YFinance: {len(res)} results")
        if res: print(res[0]['content'])
    except Exception as e:
        print(f"YFinance failed: {e}")

    # Circuit breaker test
    print("\nTesting Circuit Breaker...")
    try:
        print("Forcing failure on Yahoo Finance 3 times using an invalid ticker to open circuit...")
        await search_yfinance("INVALID_TICKER_THAT_CRASHES_YFINANCE_!!!", ["INVALID"])
        await search_yfinance("INVALID_TICKER_THAT_CRASHES_YFINANCE_!!!", ["INVALID"])
        await search_yfinance("INVALID_TICKER_THAT_CRASHES_YFINANCE_!!!", ["INVALID"])
        
        # 4th time should be bypassed
        res = await search_yfinance("AAPL", ["AAPL"])
        print(f"Circuit Breaker tripped properly if results = 0. Results: {len(res)}")
    except Exception as e:
        print(f"Circuit Breaker test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_tier4())
