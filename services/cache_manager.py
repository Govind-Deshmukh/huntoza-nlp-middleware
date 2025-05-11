"""
services/cache_manager.py - Simple in-memory cache with TTL support

Provides caching capabilities to reduce processing load and improve response times.
"""
import time
import threading
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheManager:
    """
    Thread-safe in-memory cache with TTL (time-to-live) support.
    Uses LRU (Least Recently Used) eviction policy when cache size exceeds max_size.
    """
    
    def __init__(self, max_size=1000, ttl=3600):
        """
        Initialize cache.
        
        Args:
            max_size (int): Maximum number of items in cache
            ttl (int): Time to live in seconds for cached items
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()  # {key: (value, timestamp)}
        self.lock = threading.RLock()
        
        # Start background cleaner thread if TTL is set
        if ttl > 0:
            self.cleaner = threading.Thread(target=self._clean_expired, daemon=True)
            self.cleaner.start()
    
    def get(self, key):
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Value or None if not found or expired
        """
        with self.lock:
            if key not in self.cache:
                return None
                
            value, timestamp = self.cache[key]
            
            # Check if item has expired
            if self.ttl > 0 and time.time() - timestamp > self.ttl:
                del self.cache[key]
                return None
                
            # Move item to end (most recently used)
            self.cache.move_to_end(key)
            
            return value
    
    def set(self, key, value):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            
        Returns:
            True if set successfully
        """
        with self.lock:
            # Check if key exists already
            if key in self.cache:
                # Update existing entry
                self.cache[key] = (value, time.time())
                self.cache.move_to_end(key)
                return True
                
            # If cache is full, remove least recently used item
            if len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
                
            # Add new item
            self.cache[key] = (value, time.time())
            
            return True
    
    def delete(self, key):
        """
        Delete item from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False if not found
        """
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False
    
    def clear(self):
        """Clear all items from cache."""
        with self.lock:
            self.cache.clear()
    
    def _clean_expired(self):
        """Background thread to clean expired items."""
        while True:
            try:
                time.sleep(min(self.ttl / 2, 300))  # Clean at half TTL or max 5 minutes
                
                with self.lock:
                    now = time.time()
                    expired_keys = [k for k, (_, ts) in self.cache.items() if now - ts > self.ttl]
                    
                    for key in expired_keys:
                        del self.cache[key]
                        
                    if expired_keys:
                        logger.debug(f"Removed {len(expired_keys)} expired items from cache")
            
            except Exception as e:
                logger.error(f"Error in cache cleaner: {str(e)}")
                
    def get_stats(self):
        """
        Get cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        with self.lock:
            now = time.time()
            return {
                'size': len(self.cache),
                'max_size': self.max_size,
                'ttl': self.ttl,
                'utilization': len(self.cache) / self.max_size if self.max_size > 0 else 0,
                'oldest_item_age': max([now - ts for _, ts in self.cache.values()]) if self.cache else 0,
                'newest_item_age': min([now - ts for _, ts in self.cache.values()]) if self.cache else 0,
            }