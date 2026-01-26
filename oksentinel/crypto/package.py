"""
OkShare SDK - Encrypted Package Format

This module defines the encrypted package format for file sharing.
Each package contains the encrypted file, wrapped AES key, and metadata.
"""

import json
import base64
from typing import Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class EncryptedPackage:
    """
    Encrypted package containing all data needed for secure file sharing.
    
    Attributes:
        package_id: Unique identifier for this package
        version: Package format version
        sender_id: ID of the user who sent the file
        recipient_id: ID of the intended recipient
        filename: Original filename
        encrypted_file: Base64-encoded encrypted file data
        encrypted_aes_key: Base64-encoded wrapped AES key
        algorithm: Encryption algorithm metadata
    """
    package_id: str
    version: str
    sender_id: str
    recipient_id: str
    filename: str
    encrypted_file: str  # Base64 encoded
    encrypted_aes_key: str  # Base64 encoded
    algorithm: Dict[str, str]


def create_package(
    package_id: str,
    sender_id: str,
    recipient_id: str,
    filename: str,
    encrypted_file_bytes: bytes,
    encrypted_aes_key_bytes: bytes
) -> EncryptedPackage:
    """
    Create an encrypted package from components.
    
    Args:
        package_id: Unique identifier for the package
        sender_id: ID of the sender
        recipient_id: ID of the recipient
        filename: Original filename
        encrypted_file_bytes: Encrypted file data
        encrypted_aes_key_bytes: Wrapped AES key
        
    Returns:
        EncryptedPackage object
    """
    return EncryptedPackage(
        package_id=package_id,
        version="1.0",
        sender_id=sender_id,
        recipient_id=recipient_id,
        filename=filename,
        encrypted_file=base64.b64encode(encrypted_file_bytes).decode('utf-8'),
        encrypted_aes_key=base64.b64encode(encrypted_aes_key_bytes).decode('utf-8'),
        algorithm={
            "file_encryption": "AES-256-CTR",
            "key_wrapping": "RSA-OAEP-SHA256"
        }
    )


def serialize_package(package: EncryptedPackage) -> str:
    """
    Serialize package to JSON string.
    
    Args:
        package: EncryptedPackage object
        
    Returns:
        JSON string representation
    """
    return json.dumps(asdict(package), indent=2)


def deserialize_package(json_data: str) -> EncryptedPackage:
    """
    Deserialize package from JSON string.
    
    Args:
        json_data: JSON string
        
    Returns:
        EncryptedPackage object
        
    Raises:
        ValueError: If JSON is invalid or missing required fields
    """
    try:
        data = json.loads(json_data)
        return EncryptedPackage(**data)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(f"Invalid package data: {e}")


def extract_encrypted_file(package: EncryptedPackage) -> bytes:
    """Extract encrypted file bytes from package."""
    return base64.b64decode(package.encrypted_file)


def extract_encrypted_key(package: EncryptedPackage) -> bytes:
    """Extract encrypted AES key bytes from package."""
    return base64.b64decode(package.encrypted_aes_key)

