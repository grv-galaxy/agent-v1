import time
from functools import wraps

def async_ttl_cache(ttl: int = 300):
    """
    An asynchronous in-memory TTL cache decorator.
    Caches the results of the async function based on its arguments.
    """
    cache = {}

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key from args and kwargs
            # Dictionaries or non-hashable types in kwargs will cause issues,
            # so we serialize them simply to string for the key.
            key_args = tuple(str(arg) for arg in args)
            key_kwargs = tuple(sorted((k, str(v)) for k, v in kwargs.items()))
            cache_key = (func.__name__, key_args, key_kwargs)

            now = time.time()

            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if now - timestamp < ttl:
                    # Cache hit
                    return result
                else:
                    # Cache expired
                    del cache[cache_key]

            # Cache miss, call function
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, now)
            return result

        return wrapper
    return decorator
