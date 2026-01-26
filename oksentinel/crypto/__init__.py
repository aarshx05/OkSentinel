"""OkSentinel SDK - Cryptography Module"""

from .keys import (
    generate_rsa_keypair,
    encrypt_private_key,
    decrypt_private_key,
    load_public_key,
    load_private_key,
    verify_pin
)

from .encryption import (
    generate_aes_key,
    encrypt_file,
    decrypt_file,
    wrap_key,
    unwrap_key
)

from .package import (
    EncryptedPackage,
    create_package,
    serialize_package,
    deserialize_package,
    extract_encrypted_file,
    extract_encrypted_key
)

from .okfile import (
    create_ok_file,
    decrypt_ok_file,
    get_ok_file_metadata,
    OkFileMetadata
)

__all__ = [
    # Key management
    'generate_rsa_keypair',
    'encrypt_private_key',
    'decrypt_private_key',
    'load_public_key',
    'load_private_key',
    'verify_pin',
    
    # File encryption
    'generate_aes_key',
    'encrypt_file',
    'decrypt_file',
    'wrap_key',
    'unwrap_key',
    
    # Package format (legacy)
    'EncryptedPackage',
    'create_package',
    'serialize_package',
    'deserialize_package',
    'extract_encrypted_file',
    'extract_encrypted_key',
    
    # .ok file format (new)
    'create_ok_file',
    'decrypt_ok_file',
    'get_ok_file_metadata',
    'OkFileMetadata',
]

