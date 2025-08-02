"""
API Key Management Routes
"""
from typing import Tuple

from flask import Response, g, jsonify, request

from lib.services.api_key_service import APIKeyService
from settings import logger


def create_api_key_route() -> Tuple[Response, int]:
    """
    Create a new API key for the authenticated user
    :return: Response object with API key creation status
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        name = data.get('name')
        permissions = data.get('permissions', [])
        rate_limit_per_hour = data.get('rate_limit_per_hour', 1000)
        expires_in_days = data.get('expires_in_days')
        
        if not name:
            return jsonify({"error": "API key name is required"}), 400
        
        # Get user ID from session or API key context
        user_id = None
        if hasattr(g, 'user_id'):
            user_id = g.user_id
        elif hasattr(g, 'api_key_user_id'):
            user_id = g.api_key_user_id
        
        if not user_id:
            return jsonify({"error": "User authentication required"}), 401
        
        # Create API key
        api_key_service = APIKeyService()
        success, message, api_key = api_key_service.create_api_key(
            user_id=user_id,
            name=name,
            permissions=permissions,
            rate_limit_per_hour=rate_limit_per_hour,
            expires_in_days=expires_in_days
        )
        
        if success and api_key:
            return jsonify({
                "message": message,
                "api_key": api_key,
                "name": name,
                "permissions": permissions,
                "rate_limit_per_hour": rate_limit_per_hour
            }), 201
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        return jsonify({"error": "Internal server error"}), 500


def list_api_keys_route() -> Tuple[Response, int]:
    """
    List all API keys for the authenticated user
    :return: Response object with API keys list
    """
    try:
        # Get user ID from session or API key context
        user_id = None
        if hasattr(g, 'user_id'):
            user_id = g.user_id
        elif hasattr(g, 'api_key_user_id'):
            user_id = g.api_key_user_id
        
        if not user_id:
            return jsonify({"error": "User authentication required"}), 401
        
        # Get API keys
        api_key_service = APIKeyService()
        api_keys = api_key_service.get_api_keys_for_user(user_id)
        
        return jsonify({
            "api_keys": api_keys,
            "count": len(api_keys)
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        return jsonify({"error": "Internal server error"}), 500


def delete_api_key_route(key_id: str) -> Tuple[Response, int]:
    """
    Delete an API key
    :param key_id: ID of the API key to delete
    :return: Response object with deletion status
    """
    try:
        # Get user ID from session or API key context
        user_id = None
        if hasattr(g, 'user_id'):
            user_id = g.user_id
        elif hasattr(g, 'api_key_user_id'):
            user_id = g.api_key_user_id
        
        if not user_id:
            return jsonify({"error": "User authentication required"}), 401
        
        # Delete API key
        api_key_service = APIKeyService()
        success, message = api_key_service.delete_api_key(key_id, user_id)
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logger.error(f"Error deleting API key: {e}")
        return jsonify({"error": "Internal server error"}), 500


def deactivate_api_key_route(key_id: str) -> Tuple[Response, int]:
    """
    Deactivate an API key (soft delete)
    :param key_id: ID of the API key to deactivate
    :return: Response object with deactivation status
    """
    try:
        # Get user ID from session or API key context
        user_id = None
        if hasattr(g, 'user_id'):
            user_id = g.user_id
        elif hasattr(g, 'api_key_user_id'):
            user_id = g.api_key_user_id
        
        if not user_id:
            return jsonify({"error": "User authentication required"}), 401
        
        # Deactivate API key
        api_key_service = APIKeyService()
        success, message = api_key_service.deactivate_api_key(key_id, user_id)
        
        if success:
            return jsonify({"message": message}), 200
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logger.error(f"Error deactivating API key: {e}")
        return jsonify({"error": "Internal server error"}), 500


def get_api_key_usage_route(key_id: str) -> Tuple[Response, int]:
    """
    Get usage statistics for an API key
    :param key_id: ID of the API key
    :return: Response object with usage statistics
    """
    try:
        # Get user ID from session or API key context
        user_id = None
        if hasattr(g, 'user_id'):
            user_id = g.user_id
        elif hasattr(g, 'api_key_user_id'):
            user_id = g.api_key_user_id
        
        if not user_id:
            return jsonify({"error": "User authentication required"}), 401
        
        # Get API key and usage stats
        api_key_service = APIKeyService()
        
        # First get the API key to validate ownership
        api_keys = api_key_service.get_api_keys_for_user(user_id)
        target_key = None
        for key in api_keys:
            if key.get('id') == key_id:
                target_key = key
                break
        
        if not target_key:
            return jsonify({"error": "API key not found or access denied"}), 404
        
        # Get usage stats (this would need to be implemented in the service)
        # For now, return basic info
        return jsonify({
            "api_key": target_key,
            "usage_stats": {
                "requests_this_hour": 0,  # Would be populated from Redis
                "rate_limit": target_key.get('rate_limit_per_hour', 1000),
                "remaining_requests": target_key.get('rate_limit_per_hour', 1000)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting API key usage: {e}")
        return jsonify({"error": "Internal server error"}), 500 