from functools import lru_cache  # Import lru_cache decorator for potential function memoization
import hashlib  # Import hashlib for hashing utilities

# -----------------------------------------------
# Utility: Generate a unique hash key for caching
# -----------------------------------------------
def hash_key(domain: str, query: str) -> str:
    # Combine domain and query into a single string and encode it
    # Use MD5 hashing to produce a fixed-length unique hex string
    return hashlib.md5(f"{domain}:{query}".encode()).hexdigest()

# ----------------------------------------------------
# In-memory cache class for storing query results
# ----------------------------------------------------
class SimpleCache:
    def __init__(self):
        self._cache = {}  # Dictionary to store cached values

    def get(self, key: str):
        # Retrieve the value from cache, or None if key is not found
        return self._cache.get(key)

    def set(self, key: str, value: dict):
        # Store or overwrite a value in the cache for the given key
        self._cache[key] = value

    def hit_rate(self, total: int) -> float:
        # Return the cache hit rate: (hits / total requests)
        if total == 0:
            return 0.0  # Avoid division by zero
        return round((len(self._cache) / total), 2)  # Rounded to 2 decimal places

# ----------------------------------------------------
# Deduplicate evidence based on hash of content field
# ----------------------------------------------------
def deduplicate_evidence(evidence_list):
    seen = set()  # Track seen content hashes
    deduped = []  # List to store unique items
    for item in evidence_list:
        content_hash = hash(item["content"])  # Create hash from content string
        if content_hash not in seen:  # If this content is new
            seen.add(content_hash)  # Mark it as seen
            deduped.append(item)  # Add to result list
    return deduped  # Return the deduplicated list

# Global instance of the SimpleCache used across modules
CACHE = SimpleCache()

# ------------------------------------------------------------------------
# Async helper to perform a cached search with concurrency control
# ------------------------------------------------------------------------
async def cached_search(domain, query, semaphore, session, search_fn):
    """
    Generic wrapper to perform a search with caching, concurrency control, and storage.

    Args:
        domain (str): The company domain to search.
        query (str): The search query string.
        semaphore (asyncio.Semaphore): Limits concurrent calls.
        session (aiohttp.ClientSession): HTTP session for requests.
        search_fn (callable): Function to call for performing the actual search.

    Returns:
        dict: The search result, either from cache or freshly fetched.
    """
    key = hash_key(domain, query)  # Generate unique key for the query
    cached = CACHE.get(key)  # Check if the result is already cached
    if cached:
        return cached  # Return cached result if available

    async with semaphore:  # Limit number of concurrent requests
        result = await search_fn(domain, query, semaphore, session)  # Perform actual search
        CACHE.set(key, result)  # Cache the result for future reuse
        return result  # Return the fresh result
