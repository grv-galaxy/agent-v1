import functools
import time
import asyncio

class CircuitBreakerOpenException(Exception):
    pass

def circuit_breaker(failure_threshold: int = 3, recovery_timeout: int = 300):
    """
    A decorator that acts as a circuit breaker for unreliable API wrappers.
    If the decorated function fails `failure_threshold` times consecutively, 
    the circuit opens and all subsequent calls instantly fail for `recovery_timeout` seconds.
    """
    def decorator(func):
        # We store state per-function
        func._failures = 0
        func._last_failure_time = 0
        func._state = "CLOSED" # CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            now = time.time()
            
            # Check if circuit is open
            if func._state == "OPEN":
                if now - func._last_failure_time >= recovery_timeout:
                    func._state = "HALF_OPEN"
                else:
                    print(f"[CircuitBreaker] {func.__name__} is OPEN. Bypassing request.")
                    # Return empty list for sources to gracefully degrade
                    return []
                    
            try:
                # Execute the actual function
                result = await func(*args, **kwargs)
                
                # If we get here, it succeeded! Reset circuit.
                func._failures = 0
                func._state = "CLOSED"
                return result
                
            except Exception as e:
                # It failed.
                func._failures += 1
                func._last_failure_time = now
                print(f"[CircuitBreaker] {func.__name__} failed ({func._failures}/{failure_threshold}): {e}")
                
                if func._state == "HALF_OPEN" or func._failures >= failure_threshold:
                    func._state = "OPEN"
                    print(f"[CircuitBreaker] {func.__name__} circuit OPENED!")
                    
                # Graceful degradation for our search sources: return empty instead of raising
                return []
                
        # Handle synchronous functions by wrapping them in async thread automatically if needed,
        # but since we'll apply this to our async wrappers, we just return the async_wrapper.
        return async_wrapper
    return decorator
