"""
OkShare SDK - Transport Layer Base

This module defines the abstract transport interface for package delivery.
The transport layer is designed to be extensible - implementations can use
local filesystem (for MVP), HTTP, gRPC, or any other protocol.
"""

from abc import ABC, abstractmethod
from typing import List
from ..crypto import EncryptedPackage


class Transport(ABC):
    """
    Abstract base class for transport implementations.
    
    The transport layer handles the delivery of encrypted packages between users.
    Different implementations can support various delivery mechanisms while
    maintaining the same interface.
    """
    
    @abstractmethod
    def send(self, package: EncryptedPackage, recipient_id: str) -> str:
        """
        Send an encrypted package to a recipient.
        
        Args:
            package: EncryptedPackage to send
            recipient_id: ID of the recipient user
            
        Returns:
            Delivery identifier (can be used to track the package)
            
        Raises:
            TransportError: If delivery fails
        """
        pass
    
    @abstractmethod
    def list_packages(self, user_id: str) -> List[str]:
        """
        List all packages for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of package IDs
        """
        pass
    
    @abstractmethod
    def receive(self, package_id: str, user_id: str) -> EncryptedPackage:
        """
        Retrieve a package for a user.
        
        Args:
            package_id: ID of the package to retrieve
            user_id: ID of the user receiving the package
            
        Returns:
            EncryptedPackage object
            
        Raises:
            TransportError: If package not found or access denied
        """
        pass


class TransportError(Exception):
    """Exception raised for transport-related errors."""
    pass

