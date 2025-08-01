from functools import lru_cache
import hashlib

def hash_key(domain: str, query: str) -> str:
    return hashlib.md5(f"{domain}:{query}".encode()).hexdigest() # Generate a unique hash key for caching

class SimpleCache:
    def __init__(self):
        self._cache = {}

    def get(self, key: str): # Retrieve an item from the cache
        return self._cache.get(key)

    def set(self, key: str, value: dict): # Set an item in the cache
        self._cache[key] = value

    def hit_rate(self, total: int) -> float: # Calculate the cache hit rate
        if total == 0:
            return 0.0
        return round((len(self._cache) / total), 2)

def deduplicate_evidence(evidence_list): # Deduplicate evidence based on content
    seen = set() # Set to track unique content
    deduped = [] # List to store deduplicated evidence
    for item in evidence_list:
        content_hash = hash(item["content"]) # Hashing the content to check for uniqueness
        if content_hash not in seen: # Checking if the content is unique
            seen.add(content_hash) # Adding the content hash to the seen set
            deduped.append(item) # Adding the item to the deduplicated list
    return deduped

CACHE = SimpleCache() # Global cache instance

# --- Async cached_search wrapper ---
async def cached_search(domain, query, semaphore, session, search_fn):
    """
    Generic wrapper to perform cached async search.
    Args:
        domain (str)
        query (str)
        semaphore (asyncio.Semaphore)
        session (aiohttp.ClientSession)
        search_fn (callable): Function(domain, query, semaphore, session) -> dict

    Returns:
        dict: Search result (possibly from cache)
    """
    key = hash_key(domain, query)
    cached = CACHE.get(key)
    if cached:
        return cached

    async with semaphore:
        result = await search_fn(domain, query, semaphore, session)
        CACHE.set(key, result)
        return result