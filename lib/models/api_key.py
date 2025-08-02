"""
API Key Model for 3rd Party Access
"""
import secrets
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from settings import logger


class APIKey:
    """
    Represents an API key for 3rd party access to the system
    """
    
    def __init__(
            self,
            name: str,
            user_id: str,
            key_hash: Optional[str] = None,
            permissions: Optional[List[str]] = None,
            rate_limit_per_hour: int = 1000,
            is_active: bool = True,
            expires_at: Optional[str] = None,
            last_used_at: Optional[str] = None,
            created_at: Optional[str] = None,
            id: Optional[str] = None
    ) -> None:
        """
        Initialize an API key
        
        :param name: Human-readable name for the API key
        :param user_id: ID of the user who owns this API key
        :param key_hash: Hashed version of the API key (for storage)
        :param permissions: List of permissions this key has
        :param rate_limit_per_hour: Maximum requests per hour
        :param is_active: Whether the key is active
        :param expires_at: Expiration timestamp (ISO format)
        :param last_used_at: Last usage timestamp (ISO format)
        :param created_at: Creation timestamp (ISO format)
        :param id: Database record ID
        """
        self.name = name
        self.user_id = user_id
        self.key_hash = key_hash
        self.permissions = permissions or []
        self.rate_limit_per_hour = rate_limit_per_hour
        self.is_active = is_active
        self.expires_at = expires_at
        self.last_used_at = last_used_at
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.id = id
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new API key
        
        :return: New API key string
        """
        # Generate a secure random key
        return f"ars_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def hash_key(key: str) -> str:
        """
        Hash an API key for secure storage
        
        :param key: Plain text API key
        :return: Hashed API key
        """
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256()
        hash_obj.update((key + salt).encode('utf-8'))
        return f"{salt}${hash_obj.hexdigest()}"
    
    def verify_key(self, key: str) -> bool:
        """
        Verify an API key against the stored hash
        
        :param key: Plain text API key to verify
        :return: True if key matches, False otherwise
        """
        if not self.key_hash:
            return False
        
        try:
            salt, hash_value = self.key_hash.split('$', 1)
            hash_obj = hashlib.sha256()
            hash_obj.update((key + salt).encode('utf-8'))
            computed_hash = hash_obj.hexdigest()
            return computed_hash == hash_value
        except (ValueError, AttributeError) as e:
            logger.error(f"API key verification error: {e}")
            return False
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if the API key has a specific permission
        
        :param permission: Permission to check
        :return: True if key has permission, False otherwise
        """
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[str]) -> bool:
        """
        Check if the API key has any of the specified permissions
        
        :param permissions: List of permissions to check
        :return: True if key has any permission, False otherwise
        """
        return any(permission in self.permissions for permission in permissions)
    
    def has_all_permissions(self, permissions: List[str]) -> bool:
        """
        Check if the API key has all of the specified permissions
        
        :param permissions: List of permissions to check
        :return: True if key has all permissions, False otherwise
        """
        return all(permission in self.permissions for permission in permissions)
    
    def is_expired(self) -> bool:
        """
        Check if the API key has expired
        
        :return: True if expired, False otherwise
        """
        if not self.expires_at:
            return False
        
        try:
            expires_at = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00'))
            return datetime.now(timezone.utc) > expires_at
        except (ValueError, AttributeError) as e:
            logger.error(f"Error checking API key expiration: {e}")
            return False
    
    def update_last_used(self) -> None:
        """
        Update the last used timestamp
        """
        self.last_used_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert API key to dictionary for database storage
        
        :return: Dictionary representation of the API key
        """
        return {
            'name': self.name,
            'user_id': self.user_id,
            'key_hash': self.key_hash,
            'permissions': self.permissions,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'is_active': self.is_active,
            'expires_at': self.expires_at,
            'last_used_at': self.last_used_at,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIKey':
        """
        Create API key from dictionary
        
        :param data: Dictionary containing API key data
        :return: APIKey instance
        """
        # Convert RecordID to string if it exists
        key_id = data.get('id')
        if hasattr(key_id, '__str__'):
            key_id = str(key_id)
        
        return cls(
            name=str(data.get('name') or ""),
            user_id=str(data.get('user_id') or ""),
            key_hash=data.get('key_hash'),
            permissions=data.get('permissions', []),
            rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
            is_active=data.get('is_active', True),
            expires_at=data.get('expires_at'),
            last_used_at=data.get('last_used_at'),
            created_at=data.get('created_at'),
            id=key_id
        )
    
    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """
        Validate API key name
        
        :param name: Name to validate
        :return: Tuple (is_valid: bool, error_message: str)
        """
        if not name:
            return False, "API key name is required"
        if len(name) < 3:
            return False, "API key name must be at least 3 characters long"
        if len(name) > 50:
            return False, "API key name must be less than 50 characters"
        return True, ""
    
    @staticmethod
    def validate_permissions(permissions: List[str]) -> tuple[bool, str]:
        """
        Validate API key permissions
        
        :param permissions: Permissions to validate
        :return: Tuple (is_valid: bool, error_message: str)
        """
        valid_permissions = {
            'patients:read', 'patients:write', 'patients:delete',
            'encounters:read', 'encounters:write', 'encounters:delete',
            'appointments:read', 'appointments:write', 'appointments:delete',
            'users:read', 'users:write', 'users:delete',
            'admin:read', 'admin:write', 'admin:delete'
        }
        
        for permission in permissions:
            if permission not in valid_permissions:
                return False, f"Invalid permission: {permission}"
        
        return True, ""
    
    def __repr__(self) -> str:
        return f"<APIKey: {self.name} (ID: {self.id})>"
    
    def schema(self) -> List[str]:
        """
        Defines the schema for the API Key table in SurrealDB.
        :return: list of schema definition statements.
        """
        statements: List[str] = []
        statements.append('DEFINE TABLE api_key SCHEMAFULL;')
        statements.append('DEFINE FIELD name ON api_key TYPE string ASSERT $value != none;')
        statements.append('DEFINE FIELD user_id ON api_key TYPE string ASSERT $value != none;')
        statements.append('DEFINE FIELD key_hash ON api_key TYPE string;')
        statements.append('DEFINE FIELD permissions ON api_key TYPE array;')
        statements.append('DEFINE FIELD rate_limit_per_hour ON api_key TYPE int;')
        statements.append('DEFINE FIELD is_active ON api_key TYPE bool;')
        statements.append('DEFINE FIELD expires_at ON api_key TYPE string;')
        statements.append('DEFINE FIELD last_used_at ON api_key TYPE string;')
        statements.append('DEFINE FIELD created_at ON api_key TYPE string;')
        
        statements.append('DEFINE INDEX idx_api_key_user_id ON api_key FIELDS user_id;')
        statements.append('DEFINE INDEX idx_api_key_active ON api_key FIELDS is_active;')
        
        return statements


def create_api_key_schema() -> None:
    """
    Creates the schema for API Key table in SurrealDB.
    :return: None
    """
    from lib.db.surreal import DbController
    
    db = DbController(namespace='arsmedicatech', database='patients')
    db.connect()

    api_key = APIKey("", "")
    
    for stmt in api_key.schema():
        db.query(stmt)

    db.close() 