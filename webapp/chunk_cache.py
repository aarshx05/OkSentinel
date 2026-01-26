"""
OkSentinel - Chunk Cache Layer

Provides two-tier caching for encrypted and decrypted chunks with LRU eviction.

Security:
- Decrypted chunks are memory-only with expiry enforcement
- Encrypted chunks cached to reduce fetch latency
- Thread-safe operations
"""

import threading
import time
from collections import OrderedDict
from typing import Optional, Tuple


class DecryptedChunkCache:
    """
    LRU cache for decrypted chunks (memory-only).
    
    Each entry includes:
    - Decrypted chunk data
    - Expiry timestamp
    
    Eviction: LRU when max_size exceeded
    """
    
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.cache = OrderedDict()  # (asset_id, chunk_idx) -> (data, expiry_time)
        self.lock = threading.Lock()
    
    def get(self, asset_id: str, chunk_idx: int) -> Optional[bytes]:
        """Get decrypted chunk if exists and not expired."""
        with self.lock:
            key = (asset_id, chunk_idx)
            if key not in self.cache:
                return None
            
            data, expiry_time = self.cache[key]
            
            # Expiry enforcement
            if time.time() > expiry_time:
                del self.cache[key]
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return data
    
    def put(self, asset_id: str, chunk_idx: int, data: bytes, expiry_time: float):
        """Store decrypted chunk with expiry."""
        with self.lock:
            key = (asset_id, chunk_idx)
            
            # Remove if already exists (update)
            if key in self.cache:
                del self.cache[key]
            
            # Add to end
            self.cache[key] = (data, expiry_time)
            
            # LRU eviction if over capacity
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)  # Remove oldest
    
    def invalidate(self, asset_id: str):
        """Remove all chunks for an asset (e.g., on expiry or access failure)."""
        with self.lock:
            keys_to_remove = [k for k in self.cache.keys() if k[0] == asset_id]
            for key in keys_to_remove:
                del self.cache[key]
    
    def clear(self):
        """Clear entire cache."""
        with self.lock:
            self.cache.clear()


class EncryptedChunkCache:
    """
    LRU cache for encrypted chunks (reduces disk/network fetch latency).
    
    Larger capacity than decrypted cache.
    """
    
    def __init__(self, max_size: int = 30):
        self.max_size = max_size
        self.cache = OrderedDict()  # (asset_path, chunk_idx) -> encrypted_data
        self.lock = threading.Lock()
    
    def get(self, asset_path: str, chunk_idx: int) -> Optional[Tuple[bytes, bytes, bytes]]:
        """
        Get encrypted chunk data.
        
        Returns:
            (encrypted_chunk, encrypted_key, nonce) or None
        """
        with self.lock:
            key = (asset_path, chunk_idx)
            if key not in self.cache:
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, asset_path: str, chunk_idx: int, encrypted_chunk: bytes, 
            encrypted_key: bytes, nonce: bytes):
        """Store encrypted chunk data."""
        with self.lock:
            key = (asset_path, chunk_idx)
            
            # Remove if already exists
            if key in self.cache:
                del self.cache[key]
            
            # Add to end
            self.cache[key] = (encrypted_chunk, encrypted_key, nonce)
            
            # LRU eviction
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
    
    def invalidate(self, asset_path: str):
        """Remove all chunks for an asset."""
        with self.lock:
            keys_to_remove = [k for k in self.cache.keys() if k[0] == asset_path]
            for key in keys_to_remove:
                del self.cache[key]
    
    def clear(self):
        """Clear entire cache."""
        with self.lock:
            self.cache.clear()
