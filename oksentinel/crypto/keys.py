"""
OkShare SDK - RSA Key Management with PIN Protection

This module handles RSA key pair generation and PIN-based private key encryption.
Following zero-trust principles, private keys are always encrypted at rest and
can only be decrypted by providing the correct PIN.
"""

import os
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def generate_rsa_keypair(key_size: int = 2048) -> tuple[bytes, bytes]:
    """
    Generate an RSA key pair.
    
    Args:
        key_size: RSA key size in bits (default: 2048)
        
    Returns:
        Tuple of (public_key_pem, private_key_pem) as bytes
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    public_key = private_key.public_key()
    
    # Serialize to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return public_pem, private_pem


def _derive_key_from_pin(pin: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit encryption key from a PIN using PBKDF2.
    
    Args:
        pin: User's PIN (can be 4-digit or longer)
        salt: Random salt for key derivation
        
    Returns:
        32-byte encryption key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,  # NIST recommended minimum
        backend=default_backend()
    )
    return kdf.derive(pin.encode('utf-8'))


def encrypt_private_key(private_key_pem: bytes, pin: str) -> bytes:
    """
    Encrypt a private key using a PIN-derived key (Zero Trust: PIN is the lock).
    
    The encrypted data format:
    [16 bytes salt][16 bytes IV][encrypted key data]
    
    Args:
        private_key_pem: Private key in PEM format
        pin: User's PIN for encryption
        
    Returns:
        Encrypted private key data (salt + IV + ciphertext)
    """
    # Generate random salt and IV
    salt = os.urandom(16)
    iv = os.urandom(16)
    
    # Derive encryption key from PIN
    key = _derive_key_from_pin(pin, salt)
    
    # Encrypt the private key using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    
    # Pad the private key to AES block size (16 bytes)
    from cryptography.hazmat.primitives import padding as sym_padding
    padder = sym_padding.PKCS7(128).padder()
    padded_data = padder.update(private_key_pem) + padder.finalize()
    
    # Encrypt
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    # Return: salt + IV + ciphertext
    return salt + iv + ciphertext


def decrypt_private_key(encrypted_data: bytes, pin: str) -> bytes:
    """
    Decrypt a private key using the user's PIN (Zero Trust: PIN unlocks the key).
    
    Args:
        encrypted_data: Encrypted private key (salt + IV + ciphertext)
        pin: User's PIN for decryption
        
    Returns:
        Decrypted private key in PEM format
        
    Raises:
        ValueError: If PIN is incorrect or data is corrupted
    """
    if len(encrypted_data) < 32:
        raise ValueError("Invalid encrypted data: too short")
    
    # Extract salt, IV, and ciphertext
    salt = encrypted_data[:16]
    iv = encrypted_data[16:32]
    ciphertext = encrypted_data[32:]
    
    # Derive decryption key from PIN
    key = _derive_key_from_pin(pin, salt)
    
    try:
        # Decrypt using AES-256-CBC
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove padding
        from cryptography.hazmat.primitives import padding as sym_padding
        unpadder = sym_padding.PKCS7(128).unpadder()
        private_key_pem = unpadder.update(padded_data) + unpadder.finalize()
        
        return private_key_pem
    except Exception as e:
        raise ValueError(f"Failed to decrypt private key. Incorrect PIN or corrupted data: {e}")


def load_public_key(public_key_pem: bytes):
    """Load a public key from PEM format."""
    return serialization.load_pem_public_key(
        public_key_pem,
        backend=default_backend()
    )


def load_private_key(private_key_pem: bytes):
    """Load a private key from PEM format."""
    return serialization.load_pem_private_key(
        private_key_pem,
        password=None,
        backend=default_backend()
    )


def verify_pin(encrypted_private_key: bytes, pin: str) -> bool:
    """
    Verify if a PIN is correct by attempting to decrypt the private key.
    
    Args:
        encrypted_private_key: Encrypted private key data
        pin: PIN to verify
        
    Returns:
        True if PIN is correct, False otherwise
    """
    try:
        decrypt_private_key(encrypted_private_key, pin)
        return True
    except ValueError:
        return False

