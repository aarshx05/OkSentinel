"""
OkShare SDK - User Identity Management

This module manages user identities with cryptographic key pairs.
Each user has a unique ID, username, and RSA key pair. The private key
is always encrypted with the user's PIN following zero-trust principles.
"""

import uuid
from dataclasses import dataclass
from typing import Optional
from ..crypto import (
    generate_rsa_keypair,
    encrypt_private_key,
    decrypt_private_key,
    load_private_key,
    verify_pin
)


@dataclass
class User:
    """
    User with cryptographic identity.
    
    Attributes:
        user_id: Unique identifier
        username: Human-readable username
        public_key_pem: Public RSA key (PEM format, stored unencrypted)
        encrypted_private_key: Encrypted private RSA key (encrypted with PIN)
    """
    user_id: str
    username: str
    public_key_pem: bytes
    encrypted_private_key: bytes


def create_user(username: str, pin: str) -> User:
    """
    Create a new user with cryptographic identity.
    
    This generates an RSA key pair and encrypts the private key with the user's PIN.
    Following zero-trust principles, the PIN is never stored - only used to encrypt.
    
    Args:
        username: Human-readable username
        pin: User's PIN for private key encryption (custom set by user)
        
    Returns:
        User object with encrypted private key
        
    Raises:
        ValueError: If username or PIN is invalid
    """
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
    
    if not pin:
        raise ValueError("PIN cannot be empty")
    
    # Generate unique user ID
    user_id = str(uuid.uuid4())
    
    # Generate RSA key pair
    public_key_pem, private_key_pem = generate_rsa_keypair()
    
    # Encrypt private key with PIN (zero-trust: PIN is the lock)
    encrypted_private_key = encrypt_private_key(private_key_pem, pin)
    
    return User(
        user_id=user_id,
        username=username.strip(),
        public_key_pem=public_key_pem,
        encrypted_private_key=encrypted_private_key
    )


def verify_user_pin(user: User, pin: str) -> bool:
    """
    Verify if a PIN is correct for a user.
    
    Args:
        user: User object
        pin: PIN to verify
        
    Returns:
        True if PIN is correct, False otherwise
    """
    return verify_pin(user.encrypted_private_key, pin)


def get_private_key(user: User, pin: str):
    """
    Decrypt and return the user's private key.
    
    This is the critical operation where the PIN "unlocks" the private key.
    Following zero-trust principles, the private key can only be accessed
    by providing the correct PIN.
    
    Args:
        user: User object
        pin: User's PIN
        
    Returns:
        RSA private key object
        
    Raises:
        ValueError: If PIN is incorrect
    """
    private_key_pem = decrypt_private_key(user.encrypted_private_key, pin)
    return load_private_key(private_key_pem)


def to_dict(user: User) -> dict:
    """
    Convert User to dictionary for serialization.
    
    Note: Private key is kept encrypted in the dictionary.
    """
    return {
        'user_id': user.user_id,
        'username': user.username,
        'public_key_pem': user.public_key_pem.decode('utf-8'),
        'encrypted_private_key': user.encrypted_private_key.hex()
    }


def from_dict(data: dict) -> User:
    """
    Create User from dictionary (deserialization).
    """
    return User(
        user_id=data['user_id'],
        username=data['username'],
        public_key_pem=data['public_key_pem'].encode('utf-8'),
        encrypted_private_key=bytes.fromhex(data['encrypted_private_key'])
    )

