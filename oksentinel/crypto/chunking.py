"""
OkSentinel SDK - Chunking Module

Provides chunk-based encryption and decryption with per-chunk AES keys and nonces.
Each chunk is encrypted independently for progressive access.
"""

import os
from typing import List, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import hashlib


# RSA-OAEP padding with explicit SHA-256 (non-negotiable)
RSA_OAEP_PADDING = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None
)


def chunk_bytes(data: bytes, chunk_size: int) -> List[bytes]:
    """
    Split byte array into fixed-size chunks.
    
    Args:
        data: ByteArray to chunk
        chunk_size: Size of each chunk in bytes (e.g., 4MB)
    
    Returns:
        List of byte chunks
    """
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunks.append(data[i:i + chunk_size])
    return chunks


def encrypt_chunk(chunk: bytes, recipient_public_key) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt a single chunk with AES-256-CTR using unique nonce.
    
    Args:
        chunk: ByteArray chunk to encrypt
        recipient_public_key: RSA public key for key wrapping
    
    Returns:
        Tuple of (encrypted_chunk, encrypted_aes_key, nonce)
    
    Security:
        - Generates unique random 16-byte nonce per chunk (CRITICAL)
        - Uses AES-256-CTR with generated nonce
        - Wraps AES key with RSA-2048-OAEP-SHA256
    """
    # Generate unique AES-256 key for this chunk
    aes_key = os.urandom(32)  # 256 bits
    
    # Generate unique cryptographically random nonce (CRITICAL - must never reuse)
    nonce = os.urandom(16)  # 128 bits for AES-CTR
    
    # Encrypt chunk with AES-256-CTR
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_chunk = encryptor.update(chunk) + encryptor.finalize()
    
    # Wrap AES key with RSA-2048-OAEP-SHA256 (explicit parameters)
    encrypted_aes_key = recipient_public_key.encrypt(aes_key, RSA_OAEP_PADDING)
    
    return encrypted_chunk, encrypted_aes_key, nonce


def decrypt_chunk(
    encrypted_chunk: bytes,
    encrypted_aes_key: bytes,
    nonce: bytes,
    private_key
) -> bytes:
    """
    Decrypt a single chunk using provided nonce and wrapped key.
    
    Args:
        encrypted_chunk: Encrypted chunk data
        encrypted_aes_key: RSA-wrapped AES key
        nonce: AES-CTR nonce used during encryption
        private_key: RSA private key for unwrapping
    
    Returns:
        Decrypted chunk bytes
    
    Security:
        - Unwraps AES key with RSA-2048-OAEP-SHA256
        - Decrypts with AES-256-CTR using original nonce
    """
    # Unwrap AES key with RSA-2048-OAEP-SHA256 (explicit parameters)
    aes_key = private_key.decrypt(encrypted_aes_key, RSA_OAEP_PADDING)
    
    # Decrypt chunk with AES-256-CTR
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_chunk = decryptor.update(encrypted_chunk) + decryptor.finalize()
    
    return decrypted_chunk


def hash_chunk(chunk: bytes) -> str:
    """
    Compute SHA-256 hash of chunk for integrity verification.
    
    Args:
        chunk: Chunk bytes to hash
    
    Returns:
        Hex-encoded SHA-256 hash
    """
    return hashlib.sha256(chunk).hexdigest()
