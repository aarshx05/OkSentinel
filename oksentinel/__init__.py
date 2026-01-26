"""
OkSentinel SDK - Enterprise Secure Content Sharing

SDK-first platform for post-access controlled encrypted file sharing.
"""

__version__ = "1.0.0"

from .sdk import SecureShareSDK
from .transport import Transport, LocalFileTransport
from .identity import User

__all__ = [
    'SecureShareSDK',
    'Transport',
    'LocalFileTransport',
    'User',
]

