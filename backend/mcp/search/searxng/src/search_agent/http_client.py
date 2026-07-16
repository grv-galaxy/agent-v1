import httpx

# A global httpx client to enable connection pooling and Keep-Alive across the application.
# This prevents tearing down and recreating TCP/TLS connections on every tool call.

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
)
