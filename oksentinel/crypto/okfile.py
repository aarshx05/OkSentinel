"""
OkShare SDK - .ok File Format Handler

Implements the portable .ok file format with:
- Single file containing all encrypted data
- Embedded expiry enforcement
- Section-based structure with delimiters
- Base64 encoding with light obfuscation
"""

import base64
import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path

# Import specific functions to avoid conflicts
from . import encryption
from . import keys


# Delimiters for section boundaries (unique 32-byte sequences)
DELIMITER_A = b'OK_DELIM_A_' + os.urandom(20)  # Between encrypted file and wrapped K1
DELIMITER_B = b'OK_DELIM_B_' + os.urandom(20)  # Between K1 and encrypted metadata
DELIMITER_C = b'OK_DELIM_C_' + os.urandom(20)  # Between metadata and wrapped K2

# Version identifier
OK_FILE_VERSION = "1.0"


class OkFileMetadata:
    """Metadata for .ok file with expiry enforcement."""
    
    def __init__(self, 
                 filename: str,
                 creation_time: datetime,
                 expiry_time: datetime,
                 sender_id: str = "unknown",
                 version: str = OK_FILE_VERSION):
        self.filename = filename
        self.creation_time = creation_time
        self.expiry_time = expiry_time
        self.sender_id = sender_id
        self.version = version
    
    def to_json(self) -> str:
        """Serialize metadata to JSON."""
        return json.dumps({
            'filename': self.filename,
            'creation_time': self.creation_time.isoformat(),
            'expiry_time': self.expiry_time.isoformat(),
            'sender_id': self.sender_id,
            'version': self.version
        })
    
    @staticmethod
    def from_json(json_str: str) -> 'OkFileMetadata':
        """Deserialize metadata from JSON."""
        data = json.loads(json_str)
        return OkFileMetadata(
            filename=data['filename'],
            creation_time=datetime.fromisoformat(data['creation_time']),
            expiry_time=datetime.fromisoformat(data['expiry_time']),
            sender_id=data.get('sender_id', 'unknown'),
            version=data['version']
        )
    
    def is_expired(self) -> bool:
        """Check if file has expired."""
        return datetime.now() > self.expiry_time


def _obfuscate(data: bytes) -> bytes:
    """
    Light obfuscation (reversible).
    Simple XOR with repeating key pattern.
    """
    key = b'OkSentinel2026'
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _deobfuscate(data: bytes) -> bytes:
    """Reverse the obfuscation (XOR is symmetric)."""
    return _obfuscate(data)  # XOR is its own inverse


def create_ok_file(
    input_file_path: str,
    output_ok_path: str,
    recipient_public_key_pem: bytes,
    sender_id: str,
    expiry_hours: int = 24
) -> str:
    """
    Create a .ok file from an input file.
    """
    # Read original file
    with open(input_file_path, 'rb') as f:
        file_bytes = f.read()
    
    filename = Path(input_file_path).name
    
    # Generate two AES keys (one for file, one for metadata)
    k1_file = encryption.generate_aes_key()
    k2_metadata = encryption.generate_aes_key()
    
    # SECTION 1: Encrypt file payload with K1
    encrypted_file = encryption.encrypt_file(file_bytes, k1_file)
    
    # SECTION 2: Wrap K1 with recipient's RSA public key
    recipient_pubkey = keys.load_public_key(recipient_public_key_pem)
    wrapped_k1 = encryption.wrap_key(k1_file, recipient_pubkey)
    
    # SECTION 3: Create and encrypt metadata with K2
    metadata = OkFileMetadata(
        filename=filename,
        creation_time=datetime.now(),
        expiry_time=datetime.now() + timedelta(hours=expiry_hours),
        sender_id=sender_id
    )
    metadata_json = metadata.to_json()
    encrypted_metadata = encryption.encrypt_file(metadata_json.encode('utf-8'), k2_metadata)
    
    # SECTION 4: Wrap K2 with recipient's RSA public key
    wrapped_k2 = encryption.wrap_key(k2_metadata, recipient_pubkey)
    
    # Concatenate all sections with delimiters
    ok_payload = (
        encrypted_file +
        DELIMITER_A +
        wrapped_k1 +
        DELIMITER_B +
        encrypted_metadata +
        DELIMITER_C +
        wrapped_k2
    )
    
    # Base64 encode
    base64_payload = base64.b64encode(ok_payload)
    
    # Light obfuscation
    obfuscated_payload = _obfuscate(base64_payload)
    
    # Write to .ok file
    with open(output_ok_path, 'wb') as f:
        f.write(obfuscated_payload)
    
    return output_ok_path


def decrypt_ok_file(
    ok_file_path: str,
    recipient_private_key_pem: bytes,
    output_dir: Optional[str] = None,
    return_bytes: bool = False
) -> Tuple[str, OkFileMetadata, Optional[bytes]]:
    """
    Decrypt a .ok file and extract the original file.
    
    Args:
        return_bytes: If True, returns (None, metadata, bytes) and skips writing to disk.
    """
    # Read .ok file
    with open(ok_file_path, 'rb') as f:
        obfuscated_data = f.read()
    
    # Deobfuscate
    base64_payload = _deobfuscate(obfuscated_data)
    
    # Base64 decode
    try:
        ok_payload = base64.b64decode(base64_payload)
    except Exception as e:
        raise ValueError(f"Invalid .ok file format: {e}")
    
    # Parse sections using delimiters
    try:
        # Split by DELIMITER_A
        parts_a = ok_payload.split(DELIMITER_A, 1)
        if len(parts_a) != 2:
            raise ValueError("Missing DELIMITER_A")
        encrypted_file = parts_a[0]
        remainder_a = parts_a[1]
        
        # Split by DELIMITER_B
        parts_b = remainder_a.split(DELIMITER_B, 1)
        if len(parts_b) != 2:
            raise ValueError("Missing DELIMITER_B")
        wrapped_k1 = parts_b[0]
        remainder_b = parts_b[1]
        
        # Split by DELIMITER_C
        parts_c = remainder_b.split(DELIMITER_C, 1)
        if len(parts_c) != 2:
            raise ValueError("Missing DELIMITER_C")
        encrypted_metadata = parts_c[0]
        wrapped_k2 = parts_c[1]
        
    except Exception as e:
        raise ValueError(f"Failed to parse .ok file structure: {e}")
    
    # Load recipient's private key
    recipient_privkey = keys.load_private_key(recipient_private_key_pem)
    
    # Decrypt K2 (metadata key)
    try:
        k2_metadata = encryption.unwrap_key(wrapped_k2, recipient_privkey)
    except Exception as e:
        raise ValueError(f"Failed to decrypt metadata key (wrong recipient?): {e}")
    
    # Decrypt metadata
    try:
        metadata_json = encryption.decrypt_file(encrypted_metadata, k2_metadata)
        metadata = OkFileMetadata.from_json(metadata_json.decode('utf-8'))
    except Exception as e:
        raise ValueError(f"Failed to decrypt metadata: {e}")
    
    # EXPIRY CHECK - Critical enforcement point
    if metadata.is_expired():
        raise ValueError(
            f"File has expired! "
            f"Created: {metadata.creation_time.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"Expired: {metadata.expiry_time.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"Current: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    # If not expired, decrypt file payload
    try:
        k1_file = encryption.unwrap_key(wrapped_k1, recipient_privkey)
    except Exception as e:
        raise ValueError(f"Failed to decrypt file key: {e}")
    
    try:
        file_bytes = encryption.decrypt_file(encrypted_file, k1_file)
    except Exception as e:
        raise ValueError(f"Failed to decrypt file: {e}")
    
    if return_bytes:
        return None, metadata, file_bytes

    # Determine output path
    if output_dir is None:
        output_dir = Path(ok_file_path).parent
    
    output_path = Path(output_dir) / metadata.filename
    
    # Write decrypted file
    with open(output_path, 'wb') as f:
        f.write(file_bytes)
    
    return str(output_path), metadata, None


def get_ok_file_metadata(
    ok_file_path: str,
    recipient_private_key_pem: bytes
) -> OkFileMetadata:
    """
    Extract metadata from .ok file without decrypting the full file.
    Useful for previewing expiry and details.
    
    Args:
        ok_file_path: Path to .ok file
        recipient_private_key_pem: Recipient's decrypted RSA private key
        
    Returns:
        OkFileMetadata object
    """
    # Read and parse (same as decrypt, but stop after metadata)
    with open(ok_file_path, 'rb') as f:
        obfuscated_data = f.read()
    
    base64_payload = _deobfuscate(obfuscated_data)
    ok_payload = base64.b64decode(base64_payload)
    
    # Parse to get encrypted metadata and wrapped K2
    parts_a = ok_payload.split(DELIMITER_A, 1)[1]
    parts_b = parts_a.split(DELIMITER_B, 1)[1]
    parts_c = parts_b.split(DELIMITER_C, 1)
    encrypted_metadata = parts_c[0]
    wrapped_k2 = parts_c[1]
    
    # Decrypt metadata
    recipient_privkey = keys.load_private_key(recipient_private_key_pem)
    k2_metadata = encryption.unwrap_key(wrapped_k2, recipient_privkey)
    metadata_json = encryption.decrypt_file(encrypted_metadata, k2_metadata)
    
    return OkFileMetadata.from_json(metadata_json.decode('utf-8'))

