"""
OkSentinel SDK - Asset Management Module

Handles creation, loading, and validation of .ok assets (directory-based format).
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, Optional
from ..crypto.manifest import (
    serialize_manifest,
    deserialize_manifest,
    hash_manifest,
    verify_manifest_hash
)
from ..crypto.metadata import decrypt_metadata
from ..crypto.chunking import hash_chunk


class OkAsset:
    """
    Represents a loaded and validated .ok asset.
    
    Attributes:
        asset_path: Path to asset directory
        manifest: Parsed manifest dictionary
        metadata: Decrypted metadata dictionary
        is_validated: Whether metadata has been validated
        is_expired: Whether asset has expired
    """
    
    def __init__(self, asset_path: str):
        """Initialize OkAsset (does not load or validate)."""
        self.asset_path = Path(asset_path)
        self.manifest: Optional[Dict] = None
        self.metadata: Optional[Dict] = None
        self.is_validated = False
        self.is_expired = False
    
    def get_chunk_path(self, chunk_index: int) -> str:
        """Get path to encrypted chunk file."""
        return str(self.asset_path / "chunks" / f"chunk_{chunk_index}.enc")
    
    def get_chunk_key_path(self, chunk_index: int) -> str:
        """Get path to encrypted AES key file."""
        return str(self.asset_path / "chunks" / f"chunk_{chunk_index}.key")
    
    def get_chunk_nonce_path(self, chunk_index: int) -> str:
        """Get path to nonce file."""
        return str(self.asset_path / "chunks" / f"chunk_{chunk_index}.nonce")
    
    def get_metadata_path(self) -> str:
        """Get path to encrypted metadata file."""
        return str(self.asset_path / "metadata.enc")
    
    def get_metadata_key_path(self) -> str:
        """Get path to encrypted metadata key file."""
        return str(self.asset_path / "metadata.key")
    
    def get_metadata_nonce_path(self) -> str:
        """Get path to metadata nonce file."""
        return str(self.asset_path / "metadata.nonce")
    
    def get_manifest_path(self) -> str:
        """Get path to manifest file."""
        return str(self.asset_path / "manifest.json")


def create_asset(
    output_dir: str,
    asset_id: str,
    manifest: Dict,
    encrypted_metadata: bytes,
    encrypted_metadata_key: bytes,
    metadata_nonce: bytes,
    chunk_data: list  # List of (encrypted_chunk, encrypted_key, nonce) tuples
) -> str:
    """
    Create a new .ok asset directory structure.
    
    Args:
        output_dir: Parent directory for asset
        asset_id: Unique asset identifier
        manifest: Manifest dictionary
        encrypted_metadata: Encrypted metadata bytes
        encrypted_metadata_key: RSA-wrapped metadata AES key
        metadata_nonce: AES-CTR nonce for metadata
        chunk_data: List of tuples (encrypted_chunk, encrypted_key, nonce)
    
    Returns:
        Path to created asset directory
    """
    # Create asset directory
    asset_path = Path(output_dir) / asset_id
    asset_path.mkdir(parents=True, exist_ok=True)
    
    # Create chunks subdirectory
    chunks_dir = asset_path / "chunks"
    chunks_dir.mkdir(exist_ok=True)
    
    # Write manifest
    manifest_path = asset_path / "manifest.json"
    with open(manifest_path, 'w') as f:
        f.write(serialize_manifest(manifest))
    
    # Write encrypted metadata
    with open(asset_path / "metadata.enc", 'wb') as f:
        f.write(encrypted_metadata)
    with open(asset_path / "metadata.key", 'wb') as f:
        f.write(encrypted_metadata_key)
    with open(asset_path / "metadata.nonce", 'wb') as f:
        f.write(metadata_nonce)
    
    # Write encrypted chunks
    for i, (enc_chunk, enc_key, nonce) in enumerate(chunk_data):
        with open(chunks_dir / f"chunk_{i}.enc", 'wb') as f:
            f.write(enc_chunk)
        with open(chunks_dir / f"chunk_{i}.key", 'wb') as f:
            f.write(enc_key)
        with open(chunks_dir / f"chunk_{i}.nonce", 'wb') as f:
            f.write(nonce)
    
    return str(asset_path)


def load_asset(asset_path: str) -> OkAsset:
    """
    Load an .ok asset and read manifest.
    
    Args:
        asset_path: Path to asset directory
    
    Returns:
        OkAsset instance with loaded manifest
    
    Note:
        This does NOT decrypt or validate metadata.
        Use validate_asset_metadata() for validation.
    """
    asset = OkAsset(asset_path)
    
    # Load manifest
    manifest_path = asset.get_manifest_path()
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    
    with open(manifest_path, 'r') as f:
        asset.manifest = deserialize_manifest(f.read())
    
    return asset


def validate_asset_metadata(
    asset: OkAsset,
    private_key,
    check_expiry: bool = True
) -> Dict:
    """
    Decrypt and validate asset metadata including manifest integrity.
    
    Args:
        asset: OkAsset instance
        private_key: RSA private key for decryption
        check_expiry: Whether to check expiry timestamp
    
    Returns:
        Decrypted metadata dictionary
    
    Raises:
        ValueError: If manifest hash doesn't match or asset is expired
    
    Security:
        - Decrypts metadata with user's private key
        - Verifies manifest hash against metadata.manifest_hash
        - Checks expiry timestamp if enabled
        - MUST be called before any chunk decryption
    """
    # Read encrypted metadata
    with open(asset.get_metadata_path(), 'rb') as f:
        encrypted_metadata = f.read()
    with open(asset.get_metadata_key_path(), 'rb') as f:
        encrypted_key = f.read()
    with open(asset.get_metadata_nonce_path(), 'rb') as f:
        nonce = f.read()
    
    # Decrypt metadata
    metadata = decrypt_metadata(encrypted_metadata, encrypted_key, nonce, private_key)
    
    # Verify manifest integrity
    expected_hash = metadata.get('manifest_hash')
    if not expected_hash:
        raise ValueError("Metadata missing manifest_hash field")
    
    if not verify_manifest_hash(asset.manifest, expected_hash):
        raise ValueError("Manifest integrity check failed - possible tampering detected")
    
    # Check expiry
    if check_expiry:
        expiry_at = metadata.get('expiry_at')
        if expiry_at and time.time() > expiry_at:
            asset.is_expired = True
            raise ValueError(f"Asset expired at {time.ctime(expiry_at)}")
    
    # Cache validated metadata
    asset.metadata = metadata
    asset.is_validated = True
    
    return metadata


def verify_chunk_integrity(chunk_data: bytes, expected_hash: str) -> bool:
    """
    Verify chunk integrity against expected SHA-256 hash.
    
    Args:
        chunk_data: Decrypted chunk bytes
        expected_hash: Expected SHA-256 hash from manifest
    
    Returns:
        True if hash matches, False otherwise
    
    Security:
        MUST be called after decrypting each chunk.
        Rejects corrupted or tampered chunks.
    """
    actual_hash = hash_chunk(chunk_data)
    return actual_hash == expected_hash
