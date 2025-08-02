from functools import lru_cache  # Import lru_cache decorator for potential function memoization
import hashlib  # Import hashlib for hashing utilities

def hash_key(domain: str, query: str) -> str:  # Generate a unique hash key for a domain-query pair
    # Encode "domain:query" and compute its MD5 hash, then return as hex string
    return hashlib.md5(f"{domain}:{query}".encode()).hexdigest()

class SimpleCache:  # Simple in-memory cache using a Python dict
    def __init__(self):  # Constructor initializes the internal cache store
        self._cache = {}  # Private dict to hold cached items

    def get(self, key: str):  # Retrieve a value from the cache by key
        return self._cache.get(key)  # Returns the value or None if not found

    def set(self, key: str, value: dict):  # Store a value in the cache under the given key
        self._cache[key] = value  # Overwrites any existing entry for the key

    def hit_rate(self, total: int) -> float:  # Calculate cache efficiency as hits/total requests
        if total == 0:  # Avoid division by zero when no requests have been made
            return 0.0  # No requests implies no hits
        # Number of cached entries divided by total requests, rounded to two decimals
        return round((len(self._cache) / total), 2)

def deduplicate_evidence(evidence_list):  # Remove duplicate evidence items based on content
    seen = set()  # Track hashes of content strings we've already encountered
    deduped = []  # List to accumulate unique evidence items
    for item in evidence_list:  # Iterate through each evidence dict in the input list
        # Compute a built-in hash of the content string for quick comparison
        content_hash = hash(item["content"])
        if content_hash not in seen:  # If we've not seen this content before
            seen.add(content_hash)  # Mark this content as seen
            deduped.append(item)  # Add the unique item to the deduplicated list
    return deduped  # Return the list without duplicates

CACHE = SimpleCache()  # Global cache instance for storing and retrieving search results

# --- Async cached_search wrapper ---
async def cached_search(domain, query, semaphore, session, search_fn):  # Cached async search helper
    """
    Generic wrapper to perform a search with caching, concurrency control, and storage.

    Args:
        domain (str): The company domain to search.
        query (str): The search query string.
        semaphore (asyncio.Semaphore): Limits concurrent calls.
        session (aiohttp.ClientSession): HTTP session for requests.
        search_fn (callable): Function to call for performing the actual search, signature fn(domain, query, semaphore, session).

    Returns:
        dict: The search result, either from cache or freshly fetched.
    """
    key = hash_key(domain, query)  # Create a cache key from domain and query
    cached = CACHE.get(key)  # Check if a cached result already exists
    if cached:  # If we have a cached result
        return cached  # Return it immediately without making a network call

    # Acquire semaphore slot to limit concurrency
    async with semaphore:
        # Perform the actual search function and await its result
        result = await search_fn(domain, query, semaphore, session)
        CACHE.set(key, result)  # Store the fresh result in the cache
        return result  # Return the newly fetched result
