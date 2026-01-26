"""
OkShare SDK - Local Filesystem Transport

This module implements a local filesystem-based transport for MVP demonstration.
Packages are stored in the filesystem and can be "sent" and "received" between users.
This simulates real network transport and can be easily replaced later.
"""

import os
import json
from pathlib import Path
from typing import List
from datetime import datetime
from .base import Transport, TransportError
from ..crypto import EncryptedPackage, serialize_package, deserialize_package


class LocalFileTransport(Transport):
    """
    Local filesystem-based transport implementation.
    
    Stores packages in a directory structure:
    {packages_dir}/{recipient_id}/{package_id}.json
    """
    
    def __init__(self, packages_dir: str = "./data/packages"):
        """
        Initialize local file transport.
        
        Args:
            packages_dir: Directory to store packages
        """
        self.packages_dir = Path(packages_dir)
        self.packages_dir.mkdir(parents=True, exist_ok=True)
    
    def send(self, package: EncryptedPackage, recipient_id: str) -> str:
        """
        Send a package by writing it to the recipient's directory.
        
        Args:
            package: EncryptedPackage to send
            recipient_id: ID of the recipient
            
        Returns:
            Package ID
        """
        # Create recipient's directory if it doesn't exist
        recipient_dir = self.packages_dir / recipient_id
        recipient_dir.mkdir(parents=True, exist_ok=True)
        
        # Write package to file
        package_file = recipient_dir / f"{package.package_id}.json"
        
        try:
            with open(package_file, 'w') as f:
                f.write(serialize_package(package))
            
            return package.package_id
        except Exception as e:
            raise TransportError(f"Failed to send package: {e}")
    
    def list_packages(self, user_id: str) -> List[str]:
        """
        List all packages for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of package IDs
        """
        user_dir = self.packages_dir / user_id
        
        if not user_dir.exists():
            return []
        
        try:
            package_ids = [
                f.stem  # filename without extension
                for f in user_dir.glob("*.json")
            ]
            return sorted(package_ids)
        except Exception as e:
            raise TransportError(f"Failed to list packages: {e}")
    
    def receive(self, package_id: str, user_id: str) -> EncryptedPackage:
        """
        Retrieve a package for a user.
        
        Args:
            package_id: ID of the package
            user_id: ID of the user
            
        Returns:
            EncryptedPackage object
            
        Raises:
            TransportError: If package not found
        """
        package_file = self.packages_dir / user_id / f"{package_id}.json"
        
        if not package_file.exists():
            raise TransportError(f"Package {package_id} not found for user {user_id}")
        
        try:
            with open(package_file, 'r') as f:
                package_json = f.read()
            
            return deserialize_package(package_json)
        except Exception as e:
            raise TransportError(f"Failed to receive package: {e}")
    
    def delete_package(self, package_id: str, user_id: str) -> None:
        """
        Delete a package after it has been retrieved.
        
        Args:
            package_id: ID of the package
            user_id: ID of the user
        """
        package_file = self.packages_dir / user_id / f"{package_id}.json"
        
        if package_file.exists():
            package_file.unlink()
    
    def get_package_info(self, package_id: str, user_id: str) -> dict:
        """
        Get metadata about a package without retrieving the full content.
        
        Args:
            package_id: ID of the package
            user_id: ID of the user
            
        Returns:
            Dictionary with package metadata
        """
        package = self.receive(package_id, user_id)
        
        return {
            'package_id': package.package_id,
            'sender_id': package.sender_id,
            'recipient_id': package.recipient_id,
            'filename': package.filename,
            'version': package.version
        }

