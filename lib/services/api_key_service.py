"""
API Key Service for managing 3rd party API access
"""
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from lib.db.surreal import DbController
from lib.models.api_key import APIKey
from lib.services.redis_client import get_redis_connection
from settings import logger


class APIKeyService:
    """
    Service for managing API keys, including creation, validation, rate limiting, and usage tracking
    """
    
    def __init__(self) -> None:
        """
        Initialize the API key service
        """
        self.db = DbController()
        self.rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        self.rate_limit_window = 3600  # 1 hour
    
    def connect(self) -> None:
        """
        Connect to the database
        """
        self.db.connect()
    
    def close(self) -> None:
        """
        Close the database connection
        """
        self.db.close()
    
    def create_api_key(
            self,
            user_id: str,
            name: str,
            permissions: List[str],
            rate_limit_per_hour: int = 1000,
            expires_in_days: Optional[int] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new API key
        
        :param user_id: ID of the user creating the key
        :param name: Human-readable name for the key
        :param permissions: List of permissions for the key
        :param rate_limit_per_hour: Maximum requests per hour
        :param expires_in_days: Days until expiration (None for no expiration)
        :return: Tuple (success: bool, message: str, api_key: Optional[str])
        """
        try:
            # Validate inputs
            valid_name, name_error = APIKey.validate_name(name)
            if not valid_name:
                return False, name_error, None
            
            valid_permissions, perm_error = APIKey.validate_permissions(permissions)
            if not valid_permissions:
                return False, perm_error, None
            
            # Generate new API key
            api_key = APIKey.generate_key()
            key_hash = APIKey.hash_key(api_key)
            
            # Set expiration if specified
            expires_at = None
            if expires_in_days:
                expires_at = (datetime.now(timezone.utc) + timedelta(days=expires_in_days)).isoformat()
            
            # Create API key object
            api_key_obj = APIKey(
                name=name,
                user_id=user_id,
                key_hash=key_hash,
                permissions=permissions,
                rate_limit_per_hour=rate_limit_per_hour,
                expires_at=expires_at
            )
            
            # Store in database
            self.connect()
            record_id = f"api_key:{api_key_obj.id or 'temp'}"
            content_data = api_key_obj.to_dict()
            
            query = f"CREATE {record_id} CONTENT $data"
            params = {"data": content_data}
            
            result = self.db.query(query, params)
            
            if result and len(result) > 0:
                # Extract the created record ID
                created_record = result[0]
                if 'result' in created_record and created_record['result']:
                    api_key_obj.id = str(created_record['result'][0]['id'])
                
                logger.info(f"Created API key '{name}' for user {user_id}")
                return True, "API key created successfully", api_key
            else:
                return False, "Failed to create API key", None
                
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return False, f"Error creating API key: {str(e)}", None
        finally:
            self.close()
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, str, Optional[APIKey]]:
        """
        Validate an API key and return the key object if valid
        
        :param api_key: The API key to validate
        :return: Tuple (is_valid: bool, error_message: str, api_key_obj: Optional[APIKey])
        """
        if not api_key:
            return False, "API key is required", None
        
        try:
            self.connect()
            
            # Get all API keys and check each one
            query = "SELECT * FROM api_key WHERE is_active = true"
            result = self.db.query(query)
            
            if not result or len(result) == 0:
                return False, "No API keys found", None
            
            # Extract API keys from result
            api_keys_data = result[0].get('result', []) if result[0] else result
            
            for key_data in api_keys_data:
                api_key_obj = APIKey.from_dict(key_data)
                
                # Check if key matches
                if api_key_obj.verify_key(api_key):
                    # Check if key is expired
                    if api_key_obj.is_expired():
                        return False, "API key has expired", None
                    
                    # Update last used timestamp
                    api_key_obj.update_last_used()
                    if api_key_obj.id:
                        self._update_last_used(api_key_obj.id)
                    
                    return True, "API key is valid", api_key_obj
            
            return False, "Invalid API key", None
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return False, f"Error validating API key: {str(e)}", None
        finally:
            self.close()
    
    def _update_last_used(self, key_id: str) -> None:
        """
        Update the last used timestamp for an API key
        
        :param key_id: ID of the API key to update
        """
        try:
            query = "UPDATE api_key SET last_used_at = $timestamp WHERE id = $key_id"
            params = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "key_id": key_id
            }
            self.db.query(query, params)
        except Exception as e:
            logger.error(f"Error updating last used timestamp: {e}")
    
    def check_rate_limit(self, api_key_obj: APIKey) -> Tuple[bool, str]:
        """
        Check if the API key is within its rate limit
        
        :param api_key_obj: The API key object to check
        :return: Tuple (within_limit: bool, error_message: str)
        """
        try:
            redis = get_redis_connection()
            key = f"api_key_rate_limit:{api_key_obj.id}"
            current_time = time.time()
            
            # Get current usage count
            usage_data = redis.get(key)
            if usage_data:
                usage = eval(usage_data)  # type: ignore
                if current_time - usage['window_start'] < self.rate_limit_window:
                    if usage['count'] >= api_key_obj.rate_limit_per_hour:
                        return False, f"Rate limit exceeded. Maximum {api_key_obj.rate_limit_per_hour} requests per hour."
                else:
                    # Reset window
                    usage = {'count': 0, 'window_start': current_time}
            else:
                usage = {'count': 0, 'window_start': current_time}
            
            # Increment count
            usage['count'] += 1
            
            # Store updated usage
            redis.setex(key, self.rate_limit_window, str(usage))
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False, f"Error checking rate limit: {str(e)}"
    
    def get_api_keys_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all API keys for a specific user
        
        :param user_id: ID of the user
        :return: List of API key dictionaries (without the actual key)
        """
        try:
            self.connect()
            query = "SELECT * FROM api_key WHERE user_id = $user_id ORDER BY created_at DESC"
            params = {"user_id": user_id}
            
            result = self.db.query(query, params)
            
            if not result or len(result) == 0:
                return []
            
            api_keys_data = result[0].get('result', []) if isinstance(result[0], dict) else result
            api_keys = []
            
            for key_data in api_keys_data:
                api_key_obj = APIKey.from_dict(key_data)
                # Don't include the actual key hash in the response
                key_dict = api_key_obj.to_dict()
                key_dict.pop('key_hash', None)
                api_keys.append(key_dict)
            
            return api_keys
            
        except Exception as e:
            logger.error(f"Error getting API keys for user: {e}")
            return []
        finally:
            self.close()
    
    def delete_api_key(self, key_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Delete an API key
        
        :param key_id: ID of the API key to delete
        :param user_id: ID of the user (for authorization)
        :return: Tuple (success: bool, message: str)
        """
        try:
            self.connect()
            
            # First check if the key exists and belongs to the user
            query = "SELECT * FROM api_key WHERE id = $key_id AND user_id = $user_id"
            params = {"key_id": key_id, "user_id": user_id}
            
            result = self.db.query(query, params)
            
            if not result or len(result) == 0:
                return False, "API key not found or access denied"
            
            # Delete the key
            delete_query = "DELETE FROM api_key WHERE id = $key_id"
            delete_params = {"key_id": key_id}
            
            delete_result = self.db.query(delete_query, delete_params)
            
            if delete_result and len(delete_result) > 0:
                logger.info(f"Deleted API key {key_id} for user {user_id}")
                return True, "API key deleted successfully"
            else:
                return False, "Failed to delete API key"
                
        except Exception as e:
            logger.error(f"Error deleting API key: {e}")
            return False, f"Error deleting API key: {str(e)}"
        finally:
            self.close()
    
    def deactivate_api_key(self, key_id: str, user_id: str) -> Tuple[bool, str]:
        """
        Deactivate an API key (soft delete)
        
        :param key_id: ID of the API key to deactivate
        :param user_id: ID of the user (for authorization)
        :return: Tuple (success: bool, message: str)
        """
        try:
            self.connect()
            
            query = "UPDATE api_key SET is_active = false WHERE id = $key_id AND user_id = $user_id"
            params = {"key_id": key_id, "user_id": user_id}
            
            result = self.db.query(query, params)
            
            if result and len(result) > 0:
                logger.info(f"Deactivated API key {key_id} for user {user_id}")
                return True, "API key deactivated successfully"
            else:
                return False, "API key not found or access denied"
                
        except Exception as e:
            logger.error(f"Error deactivating API key: {e}")
            return False, f"Error deactivating API key: {str(e)}"
        finally:
            self.close()
    
    def get_usage_stats(self, api_key_obj: APIKey) -> Dict[str, Any]:
        """
        Get usage statistics for an API key
        
        :param api_key_obj: The API key object
        :return: Dictionary with usage statistics
        """
        try:
            redis = get_redis_connection()
            key = f"api_key_rate_limit:{api_key_obj.id}"
            
            usage_data = redis.get(key)
            if usage_data:
                usage = eval(usage_data)  # type: ignore
                current_time = time.time()
                
                if current_time - usage['window_start'] < self.rate_limit_window:
                    return {
                        'requests_this_hour': usage['count'],
                        'rate_limit': api_key_obj.rate_limit_per_hour,
                        'remaining_requests': max(0, api_key_obj.rate_limit_per_hour - usage['count']),
                        'window_resets_in': int(self.rate_limit_window - (current_time - usage['window_start']))
                    }
            
            return {
                'requests_this_hour': 0,
                'rate_limit': api_key_obj.rate_limit_per_hour,
                'remaining_requests': api_key_obj.rate_limit_per_hour,
                'window_resets_in': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                'requests_this_hour': 0,
                'rate_limit': api_key_obj.rate_limit_per_hour,
                'remaining_requests': api_key_obj.rate_limit_per_hour,
                'window_resets_in': 0,
                'error': str(e)
            } 