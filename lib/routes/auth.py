"""
Auth routes for handling authentication with AWS Cognito and federated identity providers like Google.
"""
import base64
import secrets
from typing import Any, Dict, Tuple, Union
from urllib import parse

import jwt
import requests
from flask import Response, jsonify, redirect, request, session, url_for
from werkzeug.wrappers.response import Response as BaseResponse

from lib.services.user_service import UserService
from settings import (APP_URL, CLIENT_ID, CLIENT_SECRET, COGNITO_DOMAIN,
                      LOGOUT_URI, REDIRECT_URI, logger)


def generate_safe_username(email: str, sub: str) -> str:
    """
    Generate a safe username based on email or sub (Cognito subject ID).
    :param email: The user's email address.
    :param sub: The Cognito subject ID (unique identifier for the user).
    :return: A safe username string that is at least 3 characters long and no longer than 30 characters.
    """
    import re

    base = email.split('@')[0] if email else f"user_{sub[:8]}"

    # Strip invalid characters
    base = re.sub(r'[^a-zA-Z0-9_]', '_', base)

    # Pad if too short
    if len(base) < 3:
        base = f"{base}_{sub[:4]}"

    # Truncate if too long
    return base[:30]

def cognito_login_route() -> Union[Tuple[Response, int], BaseResponse]:
    # Handle error returned from Cognito
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    if error:
        decoded_description = parse.unquote(error_description or '')
        logger.warning("Cognito auth error: %s - %s", error, decoded_description)
        
        # Get intent from state parameter for error handling
        state = request.args.get('state', 'patient:signin')
        if ':' in state:
            _, intent = state.split(':', 1)
        else:
            intent = 'signin'  # Default to signin for backward compatibility
        
        # Handle specific Cognito errors
        if error == 'invalid_request' and 'email' in decoded_description.lower():
            # This is likely the "email cannot be updated" error
            logger.info("User attempted to sign up with existing email in Cognito")
            
            # Only show email error for signup intent
            if intent == 'signup':
                # Redirect to frontend with error parameters
                error_url = f"{APP_URL}?error=invalid_request&error_description={parse.quote('Email already exists. Please try signing in instead.')}&suggested_action=login&intent=signup"
                return redirect(error_url)
            else:
                # For signin intent, this means the user exists in Cognito but there's a linking issue
                # This typically happens when:
                # 1. User was created via traditional registration (not Google)
                # 2. User is trying to sign in with Google for the first time
                # 3. Cognito can't link the accounts due to email-as-username configuration
                error_url = f"{APP_URL}?error=invalid_request&error_description={parse.quote('This email is associated with a traditional account. Please sign in with your username and password instead.')}&suggested_action=home&intent=signin"
                return redirect(error_url)
        
        # Handle other common Cognito errors
        if error == 'access_denied':
            error_url = f"{APP_URL}?error=access_denied&error_description={parse.quote('Access was denied. Please try again.')}&suggested_action=home"
            return redirect(error_url)
        
        if error == 'server_error':
            error_url = f"{APP_URL}?error=server_error&error_description={parse.quote('Authentication service is temporarily unavailable. Please try again later.')}&suggested_action=home"
            return redirect(error_url)
        
        if error == 'temporarily_unavailable':
            error_url = f"{APP_URL}?error=temporarily_unavailable&error_description={parse.quote('Authentication service is temporarily unavailable. Please try again later.')}&suggested_action=home"
            return redirect(error_url)
        
        # Default error handling
        # Whitelist of allowed error types
        allowed_errors = {'invalid_request', 'access_denied', 'server_error', 'temporarily_unavailable'}
        if error not in allowed_errors:
            logger.warning("Unrecognized error type: %s", error)
            error = 'unknown_error'
            decoded_description = 'An unknown error occurred.'
        
        # Sanitize error_description
        sanitized_description = parse.quote(decoded_description)
        
        error_url = f"{APP_URL}?error={error}&error_description={sanitized_description}&suggested_action=home"
        return redirect(error_url)

    code = request.args.get('code')

    token_url = f'https://{COGNITO_DOMAIN}/oauth2/token'

    auth_string = f'{CLIENT_ID}:{CLIENT_SECRET}'
    auth_header = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': f'Basic {auth_header}'
    }

    body = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'code': code,
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=body)

    if response.status_code != 200:
        logger.error("Token exchange failed: %s - %s", response.status_code, response.text)
        return jsonify({'status': response.status_code, 'message': response.text}), 400

    if response.status_code == 200:
        tokens = response.json()

        user_info_url = f'https://{COGNITO_DOMAIN}/oauth2/userInfo'
        headers = {
            'Authorization': f'Bearer {tokens["access_token"]}'
        }

        user_response = requests.get(user_info_url, headers=headers)

        if user_response.status_code != 200:
            logger.error("Failed to fetch user info: %s - %s", user_response.status_code, user_response.text)
            return jsonify({'status': user_response.status_code, 'message': user_response.text}), 400

        if user_response.status_code == 200:
            user_info = user_response.json()

            id_token = tokens["id_token"]

            claims = jwt.decode(id_token, options={"verify_signature": False})

            email = user_info.get("email") or claims.get("email")
            name = user_info.get("name") or claims.get("name", "")
            sub = claims.get("sub")
            cognito_username = claims.get("cognito:username")

            # Generate a fallback username
            username = cognito_username if cognito_username else generate_safe_username(email, sub)

            if not username:
                logger.error("Could not determine username from federated identity")
                return jsonify({"error": "Unable to derive username"}), 500

            # Get role and intent from state parameter
            state = request.args.get('state', 'patient:signin')
            if ':' in state:
                role_from_query, intent = state.split(':', 1)
            else:
                # Fallback for backward compatibility
                role_from_query = state
                intent = 'signin'

            user_service = UserService()
            user_service.connect()
            try:
                user = user_service.get_user_by_email(email)
                if not user:
                    # Create user with a random password (not used for federated login)
                    random_password = secrets.token_urlsafe(16)
                    success, message, user = user_service.create_user(
                        username=username,
                        email=email,
                        password=random_password,
                        first_name="",
                        last_name="",
                        role=role_from_query,
                        is_federated=True  # Mark as federated user
                    )
                    if not success or not user or not getattr(user, "id", None):
                        logger.error(f"Failed to create user from federated login: {message}")
                        return jsonify({'error': 'Failed to create user', 'message': message}), 500
                else:
                    # User exists in our database - check intent
                    if intent == 'signup':
                        # User tried to sign up but account already exists
                        logger.info(f"User attempted to sign up with existing email: {email}")
                        error_url = f"{APP_URL}?error=invalid_request&error_description={parse.quote('This email address is already registered. Please try signing in instead.')}&suggested_action=login&intent=signup"
                        return redirect(error_url)
                    else:
                        # User is signing in with existing account - this is fine
                        # Note: If Cognito is still returning "email cannot be updated" error,
                        # it means the Cognito configuration needs to be updated to remove
                        # UsernameAttributes: [email] from the User Pool configuration
                        logger.info(f"Existing user logged in via federated identity: {email}")
                        # Optionally update user info if changed
                        updates: Dict[str, Any] = {}
                        if updates and user.id is not None:
                            user_service.update_user(str(user.id), updates)
                
                # Store user info in session (mimic other routes)
                session['user_id'] = user.id
                session['auth_token'] = tokens['id_token']
                session_token = tokens['id_token']

                if not user.id:
                    logger.error("User ID is missing after creation")
                    return jsonify({'error': 'User ID is missing'}), 500

                user_service.create_session(
                    user_id=user.id,
                    username=user.username,
                    role=role_from_query,
                    session_token=session_token,
                    expires_at=claims["exp"]
                )
                session.modified = True
                
                # Return a success response with token information for the frontend
                # The frontend will handle storing the token in localStorage
                success_url = f"{APP_URL}?auth_success=true&token={session_token}&user_id={user.id}&username={user.username}&role={role_from_query}"
                return redirect(success_url)
            except Exception as e:
                logger.error("Failed to create/update user in database: %s", e)
                session['user'] = user_info
                return redirect(APP_URL)
            finally:
                user_service.close()

    return jsonify({'error': 'Unknown error occurred during authentication'}), 500


def auth_logout_route() -> BaseResponse:
    session.clear()

    logout_url = (
        f'https://{COGNITO_DOMAIN}/logout?'
        f'client_id={CLIENT_ID}&'
        f'logout_uri={parse.quote(LOGOUT_URI)}'
    )

    return redirect(logout_url)
