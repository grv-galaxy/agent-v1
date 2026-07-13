import asyncio
import json
import websockets

async def test_websocket():
    uri = "ws://localhost:8000/ws/query"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send a query that triggers parallel searches (e.g. finance)
            query_payload = {"query": "What is the current stock price of SBI on NSE and BSE?"}
            await websocket.send(json.dumps(query_payload))
            print(f"Sent: {query_payload}")
            
            while True:
                response = await websocket.recv()
                event = json.loads(response)
                print(f"Received Event: {event['type']} - {event.get('stage') or event.get('source_id') or event.get('text')}")
                print(json.dumps(event, indent=2))
                print("-" * 40)
                
                if event.get("type") == "done":
                    print("Query complete. Exiting.")
                    break
                    
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
