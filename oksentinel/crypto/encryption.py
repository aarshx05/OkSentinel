"""
OkShare SDK - File Encryption and Key Wrapping

This module implements AES-CTR file encryption and RSA-based key wrapping.
All file encryption uses randomly generated AES-256 keys, which are then
wrapped (encrypted) using the recipient's RSA public key.
"""

import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


def generate_aes_key(key_size: int = 32) -> bytes:
    """
    Generate a random AES key.
    
    Args:
        key_size: Key size in bytes (default: 32 for AES-256)
        
    Returns:
        Random AES key
    """
    return os.urandom(key_size)


def encrypt_file(file_bytes: bytes, aes_key: bytes) -> bytes:
    """
    Encrypt file data using AES-256-CTR mode.
    
    Output format: [16 bytes nonce/IV][encrypted data]
    
    Args:
        file_bytes: Raw file data to encrypt
        aes_key: 256-bit AES key
        
    Returns:
        Encrypted data (nonce + ciphertext)
    """
    # Generate random nonce for CTR mode
    nonce = os.urandom(16)
    
    # Create AES-CTR cipher
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    # Encrypt the file data
    ciphertext = encryptor.update(file_bytes) + encryptor.finalize()
    
    # Return: nonce + ciphertext
    return nonce + ciphertext


def decrypt_file(encrypted_data: bytes, aes_key: bytes) -> bytes:
    """
    Decrypt file data using AES-256-CTR mode.
    
    Args:
        encrypted_data: Encrypted data (nonce + ciphertext)
        aes_key: 256-bit AES key
        
    Returns:
        Decrypted file data
        
    Raises:
        ValueError: If data is invalid or corrupted
    """
    if len(encrypted_data) < 16:
        raise ValueError("Invalid encrypted data: too short")
    
    # Extract nonce and ciphertext
    nonce = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    
    # Create AES-CTR cipher
    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CTR(nonce),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    
    # Decrypt the file data
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    
    return plaintext


def wrap_key(aes_key: bytes, rsa_public_key) -> bytes:
    """
    Wrap (encrypt) an AES key using an RSA public key.
    
    This ensures only the holder of the corresponding RSA private key
    can unwrap (decrypt) the AES key and access the file.
    
    Args:
        aes_key: AES key to wrap
        rsa_public_key: Recipient's RSA public key object
        
    Returns:
        Encrypted AES key
    """
    wrapped_key = rsa_public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return wrapped_key


def unwrap_key(wrapped_key: bytes, rsa_private_key) -> bytes:
    """
    Unwrap (decrypt) an AES key using an RSA private key.
    
    Args:
        wrapped_key: Encrypted AES key
        rsa_private_key: User's RSA private key object
        
    Returns:
        Decrypted AES key
        
    Raises:
        ValueError: If decryption fails (wrong key or corrupted data)
    """
    try:
        aes_key = rsa_private_key.decrypt(
            wrapped_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return aes_key
    except Exception as e:
        raise ValueError(f"Failed to unwrap AES key: {e}")

