"""
OkSentinel SDK - Manifest Module

Handles creation, validation, and integrity verification of asset manifests.
"""

import json
import hashlib
from typing import Dict, List


def create_manifest(
    asset_id: str,
    chunk_size: int,
    chunks: List[Dict],
    total_size: int
) -> Dict:
    """
    Create a manifest for an encrypted asset.
    
    Args:
        asset_id: Unique asset identifier
        chunk_size: Size of each chunk in bytes
        chunks: List of chunk metadata dicts with keys:
            - index: Chunk index
            - hash_sha256: SHA-256 hash of decrypted chunk
            - size: Chunk size in bytes
            - encrypted_key_file: Path to wrapped AES key
            - nonce_file: Path to AES-CTR nonce
        total_size: Total size of original data
    
    Returns:
        Manifest dictionary
    """
    manifest = {
        "version": "2.0",
        "asset_id": asset_id,
        "chunk_size": chunk_size,
        "total_chunks": len(chunks),
        "total_size": total_size,
        "chunks": chunks,
        "metadata_block": "metadata.enc"
    }
    return manifest


def validate_manifest(manifest: Dict) -> bool:
    """
    Validate manifest structure and required fields.
    
    Args:
        manifest: Manifest dictionary
    
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["version", "asset_id", "chunk_size", "total_chunks", 
                      "total_size", "chunks", "metadata_block"]
    
    # Check top-level fields
    for field in required_fields:
        if field not in manifest:
            return False
    
    # Validate chunk entries
    for chunk in manifest["chunks"]:
        chunk_required = ["index", "hash_sha256", "size", "encrypted_key_file", "nonce_file"]
        for field in chunk_required:
            if field not in chunk:
                return False
    
    return True


def serialize_manifest(manifest: Dict) -> str:
    """
    Serialize manifest to deterministic JSON string.
    
    Args:
        manifest: Manifest dictionary
    
    Returns:
        JSON string with sorted keys for deterministic hashing
    """
    return json.dumps(manifest, sort_keys=True, indent=2)


def deserialize_manifest(json_str: str) -> Dict:
    """
    Deserialize manifest from JSON string.
    
    Args:
        json_str: JSON string
    
    Returns:
        Manifest dictionary
    """
    return json.loads(json_str)


def hash_manifest(manifest: Dict) -> str:
    """
    Compute SHA-256 hash of manifest for integrity protection.
    
    Args:
        manifest: Manifest dictionary
    
    Returns:
        Hex-encoded SHA-256 hash
    
    Note:
        Uses deterministic serialization to ensure consistent hashing.
        This hash is stored in encrypted metadata to prevent tampering.
    """
    manifest_json = serialize_manifest(manifest)
    return hashlib.sha256(manifest_json.encode('utf-8')).hexdigest()


def verify_manifest_hash(manifest: Dict, expected_hash: str) -> bool:
    """
    Verify manifest integrity against expected hash.
    
    Args:
        manifest: Manifest dictionary to verify
        expected_hash: Expected SHA-256 hash (from metadata)
    
    Returns:
        True if hash matches, False otherwise
    
    Security:
        This verification MUST succeed before trusting chunk layout.
        Prevents chunk reordering, substitution, or expiry bypass.
    """
    actual_hash = hash_manifest(manifest)
    return actual_hash == expected_hash
