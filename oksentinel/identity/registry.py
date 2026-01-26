"""
OkShare SDK - User Registry

This module manages the user registry - a simple local storage for user accounts.
Public keys are stored in the registry for easy lookup, while encrypted private keys
are stored separately per user. The registry enables users to discover and share
files with other users without manual key exchange.
"""

import json
import os
from pathlib import Path
from typing import List, Optional
from .user import User, to_dict, from_dict


class UserRegistry:
    """
    Local file-based user registry.
    
    Stores user accounts with public keys and encrypted private keys.
    Users can list available recipients without manual key exchange.
    """
    
    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the user registry.
        
        Args:
            data_dir: Directory for storing user data
        """
        self.data_dir = Path(data_dir)
        self.users_dir = self.data_dir / "users"
        self.registry_file = self.users_dir / "registry.json"
        
        # Create directories if they don't exist
        self.users_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing registry or create new
        self._users = {}
        self._load()
    
    def add_user(self, user: User) -> None:
        """
        Add a user to the registry.
        
        Args:
            user: User object to add
            
        Raises:
            ValueError: If user_id or username already exists
        """
        if user.user_id in self._users:
            raise ValueError(f"User ID {user.user_id} already exists")
        
        # Check for duplicate username
        for existing_user in self._users.values():
            if existing_user.username.lower() == user.username.lower():
                raise ValueError(f"Username '{user.username}' already exists")
        
        self._users[user.user_id] = user
        self._save()
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User object or None if not found
        """
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User object or None if not found
        """
        for user in self._users.values():
            if user.username.lower() == username.lower():
                return user
        return None
    
    def list_users(self) -> List[User]:
        """
        List all registered users.
        
        Returns:
            List of all User objects
        """
        return list(self._users.values())
    
    def user_exists(self, user_id: str) -> bool:
        """Check if a user exists."""
        return user_id in self._users
    
    def _save(self) -> None:
        """Save registry to disk."""
        registry_data = {
            'users': {uid: to_dict(user) for uid, user in self._users.items()}
        }
        
        with open(self.registry_file, 'w') as f:
            json.dump(registry_data, f, indent=2)
    
    def _load(self) -> None:
        """Load registry from disk."""
        if not self.registry_file.exists():
            return
        
        try:
            with open(self.registry_file, 'r') as f:
                registry_data = json.load(f)
            
            self._users = {
                uid: from_dict(user_data)
                for uid, user_data in registry_data.get('users', {}).items()
            }
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Warning: Failed to load registry: {e}. Starting with empty registry.")
            self._users = {}

