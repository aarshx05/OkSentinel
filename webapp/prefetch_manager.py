"""
OkSentinel - Prefetch Manager

Intelligent chunk prefetching with:
- Velocity-based seek pattern detection
- Three-phase prefetch (immediate, short-range, long-range)
- Security enforcement (expiry checks, abort mechanism)
- Thread-safe background workers
"""

import threading
import time
import queue
from enum import Enum
from typing import Optional
from pathlib import Path


class SeekPattern(Enum):
    """Detected seek patterns based on velocity."""
    SEQUENTIAL = "sequential"          # Normal playback (~1-5MB/s)
    FORWARD_SCRUB = "forward_scrub"    # Rapid scrubbing (>10MB/s)
    SLOW_FORWARD = "slow_forward"      # Slow seeking
    BACKWARD_JUMP = "backward"         # Backward seek


class VelocityDetector:
    """
    Detects seek patterns using byte-range velocity.
    
    Tracks recent access history and calculates velocity
    to adapt prefetch strategy.
    """
    
    def __init__(self, window_size: int = 5):
        self.access_history = []  # [(timestamp, byte_start, byte_end), ...]
        self.window_size = window_size
        self.lock = threading.Lock()
    
    def on_range_request(self, byte_start: int, byte_end: int) -> SeekPattern:
        """
        Record range request and detect pattern.
        
        Args:
            byte_start: Start byte of request
            byte_end: End byte of request
        
        Returns:
            Detected seek pattern
        """
        with self.lock:
            timestamp = time.time()
            self.access_history.append((timestamp, byte_start, byte_end))
            
            # Keep window size
            if len(self.access_history) > self.window_size:
                self.access_history.pop(0)
            
            return self._detect_pattern()
    
    def _detect_pattern(self) -> SeekPattern:
        """Analyze history to detect pattern."""
        if len(self.access_history) < 2:
            return SeekPattern.SEQUENTIAL
        
        # Compare last two requests
        recent = self.access_history[-2:]
        
        time_0, start_0, end_0 = recent[0]
        time_1, start_1, end_1 = recent[1]
        
        # Calculate deltas
        byte_delta = end_1 - end_0
        time_delta = time_1 - time_0
        
        # Avoid division by zero
        if time_delta < 0.001:
            time_delta = 0.001
        
        # Velocity in bytes/second
        velocity = byte_delta / time_delta
        
        # Pattern detection
        if byte_delta < 0:
            # Backward seek
            return SeekPattern.BACKWARD_JUMP
        elif velocity > 10_000_000:  # >10MB/s
            # Rapid forward scrubbing
            return SeekPattern.FORWARD_SCRUB
        elif velocity > 1_000_000:   # >1MB/s
            # Normal sequential playback
            return SeekPattern.SEQUENTIAL
        else:
            # Slow forward seek
            return SeekPattern.SLOW_FORWARD


class PrefetchManager:
    """
    Manages background chunk prefetching with adaptive strategy.
    
    Phases:
    1. Immediate serve (blocking) - decrypt and serve current chunk
    2. Short-range prefetch (background) - decrypt N+2 to N+window
    3. Long-range lookahead (background) - fetch encrypted only
    """
    
    def __init__(self, sdk, decrypted_cache, encrypted_cache,
                 short_range_window: int = 3,
                 long_range_window: int = 10,
                 worker_threads: int = 2):
        self.sdk = sdk
        self.decrypted_cache = decrypted_cache
        self.encrypted_cache = encrypted_cache
        
        self.short_range_window = short_range_window
        self.long_range_window = long_range_window
        
        # Velocity detector per asset
        self.velocity_detectors = {}  #asset_id -> VelocityDetector
        self.detector_lock = threading.Lock()
        
        # Work queue for prefetch tasks
        self.prefetch_queue = queue.Queue()
        
        # Abort flags per asset
        self.abort_flags = {}  # asset_id -> threading.Event
        self.abort_lock = threading.Lock()
        
        # Worker threads
        self.workers = []
        self.shutdown_event = threading.Event()
        
        for _ in range(worker_threads):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def on_chunk_access(self, asset_id: str, asset_path: str, chunk_idx: int,
                       byte_start: int, byte_end: int, user_id: str, pin: str,
                       total_chunks: int, chunk_size: int, expiry_time: float):
        """
        Called when a chunk is accessed/served.
        
        Triggers background prefetch based on detected pattern.
        """
        # Get or create velocity detector
        with self.detector_lock:
            if asset_id not in self.velocity_detectors:
                self.velocity_detectors[asset_id] = VelocityDetector()
            detector = self.velocity_detectors[asset_id]
        
        # Detect pattern
        pattern = detector.on_range_request(byte_start, byte_end)
        
        print(f"[PREFETCH] Pattern: {pattern.value}, Chunk: {chunk_idx}/{total_chunks}")
        
        # Ensure abort flag exists
        with self.abort_lock:
            if asset_id not in self.abort_flags:
                self.abort_flags[asset_id] = threading.Event()
        
        # Schedule prefetch tasks
        self._schedule_prefetch(asset_id, asset_path, chunk_idx, pattern,
                               user_id, pin, total_chunks, chunk_size, expiry_time)
    
    def _schedule_prefetch(self, asset_id: str, asset_path: str, chunk_idx: int,
                          pattern: SeekPattern, user_id: str, pin: str,
                          total_chunks: int, chunk_size: int, expiry_time: float):
        """Schedule short-range and long-range prefetch tasks."""
        
        # Short-range: decrypt chunks N+2 to N+window
        short_start = chunk_idx + 2
        short_end = min(chunk_idx + self.short_range_window + 2, total_chunks)
        
        for i in range(short_start, short_end):
            task = {
                'type': 'short_range',
                'asset_id': asset_id,
                'asset_path': asset_path,
                'chunk_idx': i,
                'user_id': user_id,
                'pin': pin,
                'chunk_size': chunk_size,
                'expiry_time': expiry_time
            }
            self.prefetch_queue.put(task)
        
        # Long-range: fetch encrypted only (adaptive based on pattern)
        if pattern == SeekPattern.SEQUENTIAL:
            long_start = chunk_idx + 5
            long_end = min(chunk_idx + 15, total_chunks)
        elif pattern == SeekPattern.FORWARD_SCRUB:
            long_start = chunk_idx + 15
            long_end = min(chunk_idx + 30, total_chunks)
        elif pattern == SeekPattern.SLOW_FORWARD:
            long_start = chunk_idx + 10
            long_end = min(chunk_idx + 20, total_chunks)
        elif pattern == SeekPattern.BACKWARD_JUMP:
            # Discard forward cache and prefetch backward
            self._discard_forward_cache(asset_id, chunk_idx)
            long_start = max(chunk_idx - 15, 0)
            long_end = chunk_idx
        
        for i in range(long_start, long_end):
            task = {
                'type': 'long_range',
                'asset_id': asset_id,
                'asset_path': asset_path,
                'chunk_idx': i,
                'expiry_time': expiry_time
            }
            self.prefetch_queue.put(task)
    
    def _discard_forward_cache(self, asset_id: str, current_chunk: int):
        """Discard cached chunks ahead of current position (backward seek)."""
        # This would require tracking which chunks are cached
        # For now, just invalidate the entire decrypted cache for this asset
        self.decrypted_cache.invalidate(asset_id)
        print(f"[PREFETCH] Discarded forward cache for {asset_id}")
    
    def _worker_loop(self):
        """Background worker thread that processes prefetch tasks."""
        while not self.shutdown_event.is_set():
            try:
                # Get task with timeout
                task = self.prefetch_queue.get(timeout=1)
            except queue.Empty:
                continue
            
            asset_id = task['asset_id']
            
            # Check abort flag
            with self.abort_lock:
                abort_flag = self.abort_flags.get(asset_id)
            
            if abort_flag and abort_flag.is_set():
                print(f"[PREFETCH] Aborting task for {asset_id}")
                continue
            
            # Check expiry
            if time.time() > task['expiry_time']:
                print(f"[PREFETCH] Asset {asset_id} expired, aborting")
                self.abort_asset(asset_id)
                continue
            
            # Process based on task type
            if task['type'] == 'short_range':
                self._prefetch_short_range(task, abort_flag)
            elif task['type'] == 'long_range':
                self._prefetch_long_range(task, abort_flag)
    
    def _prefetch_short_range(self, task: dict, abort_flag: Optional[threading.Event]):
        """
        Short-range prefetch: Fetch encrypted chunk and DECRYPT.
        
        This is for chunks N+2 to N+window that are likely to be accessed soon.
        """
        asset_id = task['asset_id']
        asset_path = task['asset_path']
        chunk_idx = task['chunk_idx']
        
        # Check if already in decrypted cache
        if self.decrypted_cache.get(asset_id, chunk_idx) is not None:
            return  # Already cached
        
        try:
            # Check encrypted cache first
            encrypted_data = self.encrypted_cache.get(asset_path, chunk_idx)
            
            if encrypted_data is None:
                # Fetch from disk
                encrypted_data = self._fetch_encrypted_chunk(asset_path, chunk_idx)
                if encrypted_data:
                    enc_chunk, enc_key, nonce = encrypted_data
                    self.encrypted_cache.put(asset_path, chunk_idx, enc_chunk, enc_key, nonce)
            
            if encrypted_data and not (abort_flag and abort_flag.is_set()):
                # Decrypt
                enc_chunk, enc_key, nonce = encrypted_data
                decrypted = self.sdk.decrypt_chunk(asset_path, chunk_idx,
                                                   task['user_id'], task['pin'])
                
                # Cache decrypted
                self.decrypted_cache.put(asset_id, chunk_idx, decrypted, task['expiry_time'])
                print(f"[PREFETCH] Short-range cached chunk {chunk_idx}")
                
        except Exception as e:
            print(f"[PREFETCH ERROR] Short-range {chunk_idx}: {e}")
            # On error, abort future prefetch for this asset
            self.abort_asset(asset_id)
    
    def _prefetch_long_range(self, task: dict, abort_flag: Optional[threading.Event]):
        """
        Long-range prefetch: Fetch and cache ENCRYPTED chunks only.
        
        These will be decrypted only when they enter short-range window.
        """
        asset_path = task['asset_path']
        chunk_idx = task['chunk_idx']
        
        # Check if already in encrypted cache
        if self.encrypted_cache.get(asset_path, chunk_idx) is not None:
            return  # Already cached
        
        try:
            if abort_flag and abort_flag.is_set():
                return
            
            # Fetch encrypted chunk from disk
            encrypted_data = self._fetch_encrypted_chunk(asset_path, chunk_idx)
            
            if encrypted_data:
                enc_chunk, enc_key, nonce = encrypted_data
                self.encrypted_cache.put(asset_path, chunk_idx, enc_chunk, enc_key, nonce)
                print(f"[PREFETCH] Long-range cached encrypted chunk {chunk_idx}")
                
        except Exception as e:
            print(f"[PREFETCH ERROR] Long-range {chunk_idx}: {e}")
    
    def _fetch_encrypted_chunk(self, asset_path: str, chunk_idx: int):
        """
        Fetch encrypted chunk files from disk.
        
        Returns:
            (encrypted_chunk, encrypted_key, nonce) or None
        """
        try:
            asset_dir = Path(asset_path)
            
            chunk_file = asset_dir / "chunks" / f"chunk_{chunk_idx}.enc"
            key_file = asset_dir / "chunks" / f"chunk_{chunk_idx}.key"
            nonce_file = asset_dir / "chunks" / f"chunk_{chunk_idx}.nonce"
            
            if not chunk_file.exists():
                return None
            
            with open(chunk_file, 'rb') as f:
                encrypted_chunk = f.read()
            with open(key_file, 'rb') as f:
                encrypted_key = f.read()
            with open(nonce_file, 'rb') as f:
                nonce = f.read()
            
            return (encrypted_chunk, encrypted_key, nonce)
            
        except Exception as e:
            print(f"[PREFETCH] Failed to fetch encrypted chunk {chunk_idx}: {e}")
            return None
    
    def abort_asset(self, asset_id: str):
        """
        Abort all prefetch operations for an asset.
        
        Called on expiry or access failure.
        """
        with self.abort_lock:
            if asset_id not in self.abort_flags:
                self.abort_flags[asset_id] = threading.Event()
            self.abort_flags[asset_id].set()
        
        # Invalidate caches
        self.decrypted_cache.invalidate(asset_id)
        print(f"[PREFETCH] Aborted and invalidated {asset_id}")
    
    def shutdown(self):
        """Shutdown prefetch manager and wait for workers."""
        self.shutdown_event.set()
        for worker in self.workers:
            worker.join(timeout=2)
