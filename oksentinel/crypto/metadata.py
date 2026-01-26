"""
OkSentinel SDK - Metadata Module

Handles encryption and decryption of asset metadata including expiry and manifest hash.
"""

import os
import json
from typing import Dict, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# RSA-OAEP padding with explicit SHA-256 (non-negotiable)
RSA_OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
)


def encrypt_metadata(
    metadata: Dict,
    recipient_public_key
) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt metadata with AES-256-CTR using unique nonce.
    
    Args:
        metadata: Metadata dictionary containing:
            - created_at: Unix timestamp
            - expiry_at: Unix timestamp
            - version: Asset version
            - sender_id: Sender user ID
            - recipient_id: Recipient user ID
            - manifest_hash: SHA-256 hash of manifest.json
        recipient_public_key: RSA public key for key wrapping
    
    Returns:
        Tuple of (encrypted_metadata, encrypted_aes_key, nonce)
    
    Security:
        - Generates unique random 16-byte nonce
        - Uses AES-256-CTR with generated nonce
        - Wraps AES key with RSA-2048-OAEP-SHA256
        - manifest_hash field protects manifest integrity
    """
    # Serialize metadata to JSON
    metadata_json = json.dumps(metadata, sort_keys=True).encode('utf-8')
    
    # Generate unique AES-256 key for metadata
    aes_key = os.urandom(32)  # 256 bits
    
    # Generate unique cryptographically random nonce
    nonce = os.urandom(16)  # 128 bits for AES-CTR
    
    # Encrypt metadata with AES-256-CTR
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_metadata = encryptor.update(metadata_json) + encryptor.finalize()
    
    # Wrap AES key with RSA-2048-OAEP-SHA256 (explicit parameters)
    encrypted_aes_key = recipient_public_key.encrypt(aes_key, RSA_OAEP_PADDING)
    
    return encrypted_metadata, encrypted_aes_key, nonce


def decrypt_metadata(
    encrypted_metadata: bytes,
    encrypted_aes_key: bytes,
    nonce: bytes,
    private_key
) -> Dict:
    """
    Decrypt metadata using provided nonce and wrapped key.
    
    Args:
        encrypted_metadata: Encrypted metadata bytes
        encrypted_aes_key: RSA-wrapped AES key
        nonce: AES-CTR nonce used during encryption
        private_key: RSA private key for unwrapping
    
    Returns:
        Metadata dictionary
    
    Security:
        - Unwraps AES key with RSA-2048-OAEP-SHA256
        - Decrypts with AES-256-CTR using original nonce
    """
    # Unwrap AES key with RSA-2048-OAEP-SHA256 (explicit parameters)
    aes_key = private_key.decrypt(encrypted_aes_key, RSA_OAEP_PADDING)
    
    # Decrypt metadata with AES-256-CTR
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    metadata_json = decryptor.update(encrypted_metadata) + decryptor.finalize()
    
    # Parse JSON
    metadata = json.loads(metadata_json.decode('utf-8'))
    
    return metadata
