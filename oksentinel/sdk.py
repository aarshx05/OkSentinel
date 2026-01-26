"""
OkSentinel SDK - Main SDK with Chunked ByteArray Support

Primary APIs (v2.0 - Chunked Architecture):
- encrypt_bytes_to_asset() - Encrypt ByteArray to portable .ok asset
- load_asset() - Load and validate .ok asset
- decrypt_chunk() - Decrypt specific chunk progressively
- get_chunk_count() - Get total number of chunks

Legacy APIs (v1.0 - deprecated):
- encrypt_to_ok_file(), decrypt_ok_file() - Single-file .ok format
- create_user(), list_users() - User management
"""

import os
import uuid
import time
from pathlib import Path
from typing import List, Optional, Dict, Tuple

# New chunked crypto imports
from .crypto.chunking import (
    chunk_bytes,
    encrypt_chunk,
    decrypt_chunk as decrypt_chunk_crypto,
    hash_chunk
)
from .crypto.metadata import (
    encrypt_metadata,
    decrypt_metadata
)
from .crypto.manifest import (
    create_manifest,
    serialize_manifest,
    hash_manifest
)

# New asset imports
from .asset import (
    OkAsset,
    create_asset,
    load_asset as load_asset_fn,
    validate_asset_metadata,
    verify_chunk_integrity
)

# Legacy crypto imports
from .crypto import (
    create_ok_file,
    decrypt_ok_file,
    get_ok_file_metadata,
    OkFileMetadata,
    decrypt_private_key,  # Import from crypto instead of identity
    # Legacy imports for backward compatibility
    generate_aes_key,
    encrypt_file,
    decrypt_file,
    wrap_key,
    unwrap_key,
    create_package,
    serialize_package,
    deserialize_package,
    extract_encrypted_file,
    extract_encrypted_key,
    load_public_key,
    load_private_key,
)
from .identity import (
    User,
    create_user as create_user_identity,
    get_private_key,
    UserRegistry,
)
from .transport import Transport, LocalFileTransport


class SecureShareSDK:
    """
    High-level SDK for secure content delivery with chunked ByteArray encryption.
    
    Primary APIs (v2.0):
    - encrypt_bytes_to_asset() - Create portable chunked .ok asset
    - load_asset() - Load and validate asset with metadata check
    - decrypt_chunk() - Progressive chunk decryption
    - get_chunk_count() - Get total chunks
    
    Legacy APIs (v1.0 - deprecated):
    - encrypt_to_ok_file(), decrypt_ok_file() - Single-file .ok format
    """
    
    def __init__(self, data_dir: str = "./data", transport: Optional[Transport] = None):
        """
        Initialize the SDK.
        
        Args:
            data_dir: Directory for storing user data
            transport: Optional custom transport (for legacy mode)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize user registry
        self.registry = UserRegistry(str(self.data_dir))
        
        # Initialize transport (for legacy mode)
        self.transport = transport or LocalFileTransport(str(self.data_dir / "packages"))
        
        # Temporary storage for encrypted packages (legacy)
        self.temp_packages = {}
    
    # ==================== User Management ====================
    
    def create_user(self, username: str, pin: str) -> str:
        """
        Create a new user with cryptographic identity.
        
        Args:
            username: Human-readable username
            pin: User's custom PIN for private key protection
            
        Returns:
            User ID (UUID)
        """
        user = create_user_identity(username, pin)
        self.registry.add_user(user)
        return user.user_id
    
    def list_users(self) -> List[Dict[str, str]]:
        """List all registered users."""
        users = self.registry.list_users()
        return [
            {'user_id': user.user_id, 'username': user.username}
            for user in users
        ]
    
    def get_user(self, user_id: str) -> Optional[Dict[str, str]]:
        """Get user information by ID."""
        user = self.registry.get_user(user_id)
        if user:
            return {'user_id': user.user_id, 'username': user.username}
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, str]]:
        """Get user information by username."""
        user = self.registry.get_user_by_username(username)
        if user:
            return {'user_id': user.user_id, 'username': user.username}
        return None
    
    # ==================== Chunked ByteArray APIs (v2.0 - Primary) ====================
    
    def encrypt_bytes_to_asset(
        self,
        byte_array: bytes,
        recipient_id: str,
        sender_id: str,
        sender_pin: str,
        filename: str = "unknown.bin",  # Added filename support
        expiry_hours: int = 24,
        chunk_size: int = 4 * 1024 * 1024,  # 4MB default
        output_dir: Optional[str] = None
    ) -> str:
        """
        Encrypt ByteArray to portable chunked .ok asset.
        
        Args:
            byte_array: ByteArray data to encrypt
            recipient_id: ID of recipient user
            sender_id: ID of sender user
            sender_pin: Sender's PIN for authentication
            filename: Original filename (stored in metadata)
            expiry_hours: Hours until expiry (default 24)
            chunk_size: Size of each chunk in bytes (default 4MB)
            output_dir: Optional output directory
        
        Returns:
            Path to created asset directory
        
        Process:
            1. Validate sender and recipient
            2. Chunk ByteArray into fixed-size pieces
            3. Encrypt each chunk with unique AES key and nonce
            4. Create manifest with chunk hashes
            5. Encrypt metadata with manifest hash
            6. Create .ok asset directory structure
        
        Security:
            - Each chunk uses unique AES-256-CTR key and nonce
            - All keys wrapped with RSA-2048-OAEP-SHA256
            - Manifest hash stored in encrypted metadata
            - Chunk hashes stored in manifest for integrity
        """
        # Validate sender
        sender = self.registry.get_user(sender_id)
        if not sender:
            raise ValueError(f"Sender {sender_id} not found")
        
        # Authenticate sender with PIN
        try:
            sender_private_key = get_private_key(sender, sender_pin)
        except ValueError:
            raise ValueError("Incorrect sender PIN")
        
        # Validate recipient
        recipient = self.registry.get_user(recipient_id)
        if not recipient:
            raise ValueError(f"Recipient {recipient_id} not found")
        
        # Load recipient's public key
        recipient_public_key = load_public_key(recipient.public_key_pem)
        
        # Determine output directory
        if output_dir is None:
            output_dir = self.data_dir / "ok_assets" / recipient_id
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique asset ID
        asset_id = str(uuid.uuid4())
        
        # Chunk the ByteArray
        chunks = chunk_bytes(byte_array, chunk_size)
        total_chunks = len(chunks)
        
        # Encrypt each chunk
        chunk_data = []  # List of (encrypted_chunk, encrypted_key, nonce) tuples
        chunk_metadata = []
        
        for i, chunk in enumerate(chunks):
            # Encrypt chunk with unique key and nonce
            enc_chunk, enc_key, nonce = encrypt_chunk(chunk, recipient_public_key)
            chunk_data.append((enc_chunk, enc_key, nonce))
            
            # Compute hash of original chunk for integrity verification
            chunk_hash = hash_chunk(chunk)
            
            # Add chunk metadata to manifest
            chunk_metadata.append({
                "index": i,
                "hash_sha256": chunk_hash,
                "size": len(chunk),
                "encrypted_key_file": f"chunk_{i}.key",
                "nonce_file": f"chunk_{i}.nonce"
            })
        
        # Create manifest
        manifest = create_manifest(
            asset_id=asset_id,
            chunk_size=chunk_size,
            chunks=chunk_metadata,
            total_size=len(byte_array)
        )
        
        # Compute manifest hash for integrity protection
        manifest_hash = hash_manifest(manifest)
        
        # Create metadata
        metadata = {
            "created_at": int(time.time()),
            "expiry_at": int(time.time() + (expiry_hours * 3600)),
            "version": "2.0",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "filename": filename,  # Added filename to metadata
            "manifest_hash": manifest_hash  # CRITICAL: prevents tampering
        }
        
        # Encrypt metadata
        enc_metadata, enc_metadata_key, metadata_nonce = encrypt_metadata(
            metadata,
            recipient_public_key
        )
        
        # Create asset directory structure
        asset_path = create_asset(
            output_dir=str(output_path),
            asset_id=asset_id,
            manifest=manifest,
            encrypted_metadata=enc_metadata,
            encrypted_metadata_key=enc_metadata_key,
            metadata_nonce=metadata_nonce,
            chunk_data=chunk_data
        )
        
        return asset_path
    
    def load_asset(
        self,
        asset_path: str,
        user_id: str,
        pin: str
    ) -> Dict:
        """Load and validate .ok asset with metadata check."""
        user = self.registry.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        try:
            private_key_pem = decrypt_private_key(user.encrypted_private_key, pin)
            private_key = load_private_key(private_key_pem)
        except ValueError:
            raise ValueError("Incorrect PIN")
        
        asset = load_asset_fn(asset_path)
        
        try:
            metadata = validate_asset_metadata(asset, private_key, check_expiry=True)
        except ValueError as e:
            raise ValueError(f"Asset validation failed: {e}")
        
        return {
            "asset_id": asset.manifest['asset_id'],
            "chunk_count": asset.manifest['total_chunks'],
            "metadata": metadata,
            "is_expired": asset.is_expired
        }
    
    
    def list_assets(self, user_id: str) -> List[Dict[str, str]]:
        """
        List all chunked .ok assets for a user.
        
        Args:
            user_id: ID of user
            
        Returns:
            List of dictionaries with asset info (path, id, name)
        """
        assets_dir = self.data_dir / "ok_assets" / user_id
        
        if not assets_dir.exists():
            return []
        
        assets = []
        for asset_path in assets_dir.iterdir():
            if asset_path.is_dir():
                # For now, just use directory name as asset ID and default name
                # In future, could read manifest for more info without full validation
                assets.append({
                    'asset_id': asset_path.name,
                    'path': str(asset_path),
                    'name': asset_path.name  # Can improve by storing name in manifest or folder name
                })
        
        return assets
    
    def get_chunk_count(self, asset_path: str) -> int:
        """Get total number of chunks in an asset."""
        asset = load_asset_fn(asset_path)
        return asset.manifest['total_chunks']
    
    def decrypt_chunk(
        self,
        asset_path: str,
        chunk_index: int,
        user_id: str,
        pin: str
    ) -> bytes:
        """Decrypt a specific chunk from an asset."""
        user = self.registry.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        try:
            private_key_pem = decrypt_private_key(user.encrypted_private_key, pin)
            private_key = load_private_key(private_key_pem)
        except ValueError:
            raise ValueError("Incorrect PIN")
        
        asset = load_asset_fn(asset_path)
        
        try:
            metadata = validate_asset_metadata(asset, private_key, check_expiry=True)
        except ValueError as e:
            raise ValueError(f"Cannot decrypt chunk: {e}")
        
        if chunk_index < 0 or chunk_index >= asset.manifest['total_chunks']:
            raise ValueError(f"Invalid chunk index: {chunk_index}")
        
        with open(asset.get_chunk_path(chunk_index), 'rb') as f:
            encrypted_chunk = f.read()
        with open(asset.get_chunk_key_path(chunk_index), 'rb') as f:
            encrypted_key = f.read()
        with open(asset.get_chunk_nonce_path(chunk_index), 'rb') as f:
            nonce = f.read()
        
        decrypted_chunk = decrypt_chunk_crypto(
            encrypted_chunk,
            encrypted_key,
            nonce,
            private_key
        )
        
        expected_hash = asset.manifest['chunks'][chunk_index]['hash_sha256']
        if not verify_chunk_integrity(decrypted_chunk, expected_hash):
            raise ValueError(f"Chunk {chunk_index} integrity verification failed - possible corruption")
        
        return decrypted_chunk

    
    # ==================== .ok File APIs (Primary) ====================
    
    def encrypt_to_ok_file(
        self,
        input_file_path: str,
        recipient_id: str,
        sender_id: str,
        sender_pin: str,
        expiry_hours: int = 24,
        output_dir: Optional[str] = None
    ) -> str:
        """
        Create a portable .ok file with embedded expiry enforcement.
        """
        # Validate sender
        sender = self.registry.get_user(sender_id)
        if not sender:
            raise ValueError(f"Sender {sender_id} not found")
        
        # Validate sender's PIN (authentication)
        try:
            get_private_key(sender, sender_pin)
        except ValueError:
            raise ValueError("Incorrect sender PIN")
        
        # Validate recipient
        recipient = self.registry.get_user(recipient_id)
        if not recipient:
            raise ValueError(f"Recipient {recipient_id} not found")
        
        # Verify file exists
        file_path = Path(input_file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Determine output directory
        if output_dir is None:
            output_dir = self.data_dir / "ok_files" / recipient_id
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate .ok filename: {filename}__from_{sender}__id.ok
        # Added sender name to filename for easier UI display before decryption
        safe_filename = file_path.stem.replace(' ', '_')
        ok_filename = f"{safe_filename}__from_{sender.username}__{uuid.uuid4().hex[:6]}.ok"
        ok_file_path = output_path / ok_filename
        
        # Create .ok file
        create_ok_file(
            input_file_path=str(file_path),
            output_ok_path=str(ok_file_path),
            recipient_public_key_pem=recipient.public_key_pem,
            sender_id=sender_id,  # Embed verified sender ID
            expiry_hours=expiry_hours
        )
        
        return str(ok_file_path)
    
    def decrypt_ok_file(
        self,
        ok_file_path: str,
        user_id: str,
        pin: str,
        output_dir: Optional[str] = None,
        return_bytes: bool = False
    ) -> tuple[Optional[str], Dict[str, str], Optional[bytes]]:
        """
        Decrypt a .ok file with expiry enforcement.
        
        Args:
            return_bytes: If True, returns (None, metadata, bytes) for zero-leak memory usage.
        """
        # Validate user
        user = self.registry.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Unlock user's private key with PIN
        try:
            private_key_pem = decrypt_private_key(user.encrypted_private_key, pin)
        except ValueError:
            raise ValueError("Incorrect PIN")
        
        # Determine output directory (if not return_bytes)
        if output_dir is None and not return_bytes:
            output_dir = self.data_dir / "downloads" / user_id
            Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Decrypt .ok file (includes expiry check)
        output_path, metadata, file_bytes = decrypt_ok_file(
            ok_file_path=ok_file_path,
            recipient_private_key_pem=private_key_pem,
            output_dir=output_dir,
            return_bytes=return_bytes
        )
        
        # Convert metadata to dict
        metadata_dict = {
            'filename': metadata.filename,
            'creation_time': metadata.creation_time.isoformat(),
            'expiry_time': metadata.expiry_time.isoformat(),
            'sender_id': metadata.sender_id,
            'version': metadata.version,
            'is_expired': metadata.is_expired()
        }
        
        return output_path, metadata_dict, file_bytes
    
    def get_ok_file_info(
        self,
        ok_file_path: str,
        user_id: str,
        pin: str
    ) -> Dict[str, str]:
        """
        Get metadata from .ok file without decrypting the full file.
        
        Args:
            ok_file_path: Path to .ok file
            user_id: ID of user
            pin: User's PIN
            
        Returns:
            Metadata dictionary
        """
        user = self.registry.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        private_key_pem = decrypt_private_key(user.encrypted_private_key, pin)
        
        metadata = get_ok_file_metadata(
            ok_file_path=ok_file_path,
            recipient_private_key_pem=private_key_pem
        )
        
        return {
            'filename': metadata.filename,
            'creation_time': metadata.creation_time.isoformat(),
            'expiry_time': metadata.expiry_time.isoformat(),
            'version': metadata.version,
            'is_expired': metadata.is_expired(),
            'hours_remaining': (metadata.expiry_time - metadata.creation_time).total_seconds() / 3600 if not metadata.is_expired() else 0
        }
    
    def list_ok_files(self, user_id: str) -> List[Dict[str, str]]:
        """
        List all .ok files for a user.
        
        Args:
            user_id: ID of user
            
        Returns:
            List of dictionaries with file info
        """
        ok_dir = self.data_dir / "ok_files" / user_id
        
        if not ok_dir.exists():
            return []
        
        ok_files = []
        for ok_file in ok_dir.glob("*.ok"):
            ok_files.append({
                'filename': ok_file.name,
                'path': str(ok_file),
                'size': ok_file.stat().st_size
            })
        
        return ok_files
    
    # ==================== Legacy APIs (Backward Compatibility) ====================
    
    def encrypt_file(self, file_path: str, recipient_id: str, sender_id: str, sender_pin: str) -> str:
        """LEGACY: Use encrypt_to_ok_file() instead."""
        # Validate sender
        sender = self.registry.get_user(sender_id)
        if not sender:
            raise ValueError(f"Sender {sender_id} not found")
        
        try:
            get_private_key(sender, sender_pin)
        except ValueError:
            raise ValueError("Incorrect sender PIN")
        
        recipient = self.registry.get_user(recipient_id)
        if not recipient:
            raise ValueError(f"Recipient {recipient_id} not found")
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, 'rb') as f:
            file_bytes = f.read()
        
        aes_key = generate_aes_key()
        encrypted_file_data = encrypt_file(file_bytes, aes_key)
        
        recipient_public_key = load_public_key(recipient.public_key_pem)
        encrypted_aes_key = wrap_key(aes_key, recipient_public_key)
        
        package_id = str(uuid.uuid4())
        package = create_package(
            package_id=package_id,
            sender_id=sender_id,
            recipient_id=recipient_id,
            filename=file_path.name,
            encrypted_file_bytes=encrypted_file_data,
            encrypted_aes_key_bytes=encrypted_aes_key
        )
        
        self.temp_packages[package_id] = package
        return package_id
    
    def send_package(self, package_id: str, recipient_id: str) -> None:
        """LEGACY: Transport layer method."""
        if package_id not in self.temp_packages:
            raise ValueError(f"Package {package_id} not found")
        
        package = self.temp_packages[package_id]
        self.transport.send(package, recipient_id)
        del self.temp_packages[package_id]
    
    def list_received_packages(self, user_id: str) -> List[Dict[str, str]]:
        """LEGACY: List packages in transport layer."""
        package_ids = self.transport.list_packages(user_id)
        
        packages_info = []
        for pkg_id in package_ids:
            try:
                package = self.transport.receive(pkg_id, user_id)
                sender = self.registry.get_user(package.sender_id)
                
                packages_info.append({
                    'package_id': pkg_id,
                    'filename': package.filename,
                    'sender_id': package.sender_id,
                    'sender_username': sender.username if sender else 'Unknown'
                })
            except Exception:
                continue
        
        return packages_info
    
    def decrypt_file(self, package_id: str, pin: str, user_id: str, output_dir: str = "./downloads") -> str:
        """LEGACY: Use decrypt_ok_file() instead."""
        user = self.registry.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        package = self.transport.receive(package_id, user_id)
        
        if package.recipient_id != user_id:
            raise ValueError("This package is not for you")
        
        try:
            private_key = get_private_key(user, pin)
        except ValueError:
            raise ValueError("Incorrect PIN")
        
        encrypted_file_bytes = extract_encrypted_file(package)
        encrypted_aes_key_bytes = extract_encrypted_key(package)
        
        aes_key = unwrap_key(encrypted_aes_key_bytes, private_key)
        decrypted_file_bytes = decrypt_file(encrypted_file_bytes, aes_key)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_file = output_path / package.filename
        with open(output_file, 'wb') as f:
            f.write(decrypted_file_bytes)
        
        return str(output_file)
    
    def register_transport(self, transport: Transport) -> None:
        """LEGACY: Replace transport."""
        self.transport = transport

