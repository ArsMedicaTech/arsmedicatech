"""
Main application file for the Flask server.
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import sentry_sdk
import werkzeug
from flask import (Blueprint, Flask, Response, abort, jsonify, redirect,
                   request, send_from_directory, session)
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
from werkzeug.wrappers.response import Response as BaseResponse

from lib.dummy_data import DUMMY_CONVERSATIONS
from lib.event_handlers import register_event_handlers
from lib.routes.administration import (get_administrators_route,
                                       get_clinics_route,
                                       get_organizations_route,
                                       get_patients_route, get_providers_route)
from lib.routes.appointments import (cancel_appointment_route,
                                     confirm_appointment_route,
                                     create_appointment_route,
                                     get_appointment_route,
                                     get_appointment_statuses_route,
                                     get_appointment_types_route,
                                     get_appointments_route,
                                     get_available_slots_route,
                                     update_appointment_route)
from lib.routes.auth import auth_logout_route, cognito_login_route
from lib.routes.chat import (create_conversation_route,
                             get_conversation_messages_route,
                             get_user_conversations_route, send_message_route)
from lib.routes.llm_agent import llm_agent_endpoint_route
from lib.routes.api_keys import (create_api_key_route, deactivate_api_key_route,
                                 delete_api_key_route, get_api_key_usage_route,
                                 list_api_keys_route)
from lib.routes.metrics import metrics_bp
from lib.routes.optimal import call_optimal_route
from lib.routes.organizations import get_organizations_route
from lib.routes.patients import (create_encounter_route,
                                 delete_encounter_route,
                                 extract_entities_from_notes_route,
                                 get_all_encounters_route,
                                 get_cache_stats_route,
                                 get_encounter_by_id_route,
                                 get_encounters_by_patient_route,
                                 patch_intake_route, patient_endpoint_route,
                                 patients_endpoint_route,
                                 search_encounters_route,
                                 search_patients_route, update_encounter_route)
from lib.routes.testing import (debug_session_route, test_crud_route,
                                test_surrealdb_route)
from lib.routes.uploads import uploads_bp
from lib.routes.user_notes import (create_note_route, delete_note_route,
                                   get_note_by_id_route, get_user_notes_route,
                                   update_note_route)
from lib.routes.users import (activate_user_route, change_password_route,
                              check_users_exist_route, deactivate_user_route,
                              get_all_users_route, get_api_usage_route,
                              get_current_user_info_route,
                              get_user_profile_route, login_route,
                              logout_route, register_route, search_users_route,
                              settings_route, setup_default_admin_route,
                              update_user_profile_route)
from lib.services.auth_decorators import (optional_auth, require_admin, require_api_key,
                                          require_api_permission, require_auth)
from lib.routes.webhooks import (create_webhook_subscription_route,
                                 delete_webhook_subscription_route,
                                 get_webhook_events_route,
                                 get_webhook_subscription_route,
                                 get_webhook_subscriptions_route,
                                 update_webhook_subscription_route)
from lib.services.auth_decorators import (optional_auth, require_admin,
                                          require_auth)
from lib.services.lab_results import (LabResultsService,
                                      differential_hematology,
                                      general_chemistry, hematology,
                                      serum_proteins)
from lib.services.notifications import publish_event_with_buffer
from lib.services.redis_client import get_redis_connection
from lib.services.user_service import UserNotAffiliatedError, UserService
from settings import (APP_URL, CLIENT_ID, COGNITO_DOMAIN, DEBUG,
                      FLASK_SECRET_KEY, HOST, PORT, REDIRECT_URI, SENTRY_DSN,
                      logger)

#from flask_jwt_extended import jwt_required, get_jwt_identity


sentry_sdk.init(
    dsn=SENTRY_DSN,
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3012", "http://127.0.0.1:3012", "https://demo.arsmedicatech.com"], "supports_credentials": True, "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

app.secret_key = FLASK_SECRET_KEY

app.config["SESSION_COOKIE_NAME"] = "amt_session"
app.config["SESSION_TYPE"] = "filesystem"

if DEBUG:
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # False only on http://localhost
        SESSION_COOKIE_SAMESITE='Lax',  # 'Lax' if SPA and API are same origin
        SESSION_COOKIE_DOMAIN=None  # No domain set for local development
    )
else:
    app.config.update(
        SESSION_COOKIE_SECURE=True,  # False only on http://localhost
        SESSION_COOKIE_SAMESITE='None',  # 'Lax' if SPA and API are same origin
        SESSION_COOKIE_DOMAIN='.arsmedicatech.com'  # leading dot, covers sub-domains
    )

@app.route("/api/debug/session_v2")
def debug_session_v2():
    return jsonify({
        "user_id": session.get("user_id"),
        "auth_token": session.get("auth_token"),
        "session_keys": list(session.keys()),
    })

# Global OPTIONS handler for CORS preflight
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
@metrics_bp.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@metrics_bp.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path: str) -> Tuple[Response, int]:
    """
    Global OPTIONS handler to handle CORS preflight requests.
    :param path: The path for which the OPTIONS request is made.
    :return: Response object with CORS headers.
    """
    logger.debug(f"Global OPTIONS handler called for path: {path}")
    response = Response()
    origin = request.headers.get('Origin')
    logger.debug(f"Global OPTIONS Origin: {origin}")
    response.headers['Access-Control-Allow-Origin'] = origin or '*'
    #response.headers['Access-Control-Allow-Credentials'] = 'false'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Cache-Control'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Max-Age'] = '86400'
    logger.debug(f"Global OPTIONS response headers: {dict(response.headers)}")
    return response

metrics = PrometheusMetrics(app)

app.config['CORS_HEADERS'] = 'Content-Type'

app.register_blueprint(metrics_bp)

sse_bp = Blueprint('sse', __name__)


@sse_bp.route('/api/events/stream')
@sse_bp.route('/api/events/stream', methods=['OPTIONS'])
#@jwt_required()
def stream_events() -> Tuple[Response, int]:
    """
    Server-Sent Events (SSE) endpoint to stream events to the client.
    :return: Response object with the event stream.
    """
    logger.debug(f"SSE endpoint called - Method: {request.method}")
    logger.debug(f"SSE endpoint - Origin: {request.headers.get('Origin')}")
    logger.debug(f"SSE endpoint - Headers: {dict(request.headers)}")
    logger.debug(f"SSE endpoint - Session: {dict(session)}")
    logger.debug(f"SSE endpoint - Session cookie: {request.cookies.get('session')}")
    logger.debug(f"SSE endpoint - All cookies: {dict(request.cookies)}")
    logger.debug(f"SSE endpoint - Request URL: {request.url}")
    logger.debug(f"SSE endpoint - Request args: {dict(request.args)}")
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        logger.debug("SSE endpoint - Handling OPTIONS preflight request")
        response = Response()
        origin = request.headers.get('Origin')
        logger.debug(f"OPTIONS Origin: {origin}")
        # Always allow the origin for SSE
        response.headers['Access-Control-Allow-Origin'] = origin or '*'
        logger.debug(f"Setting Access-Control-Allow-Origin to: {origin or '*'}")
        response.headers['Access-Control-Allow-Credentials'] = 'false'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Cache-Control'
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Max-Age'] = '86400'
        logger.debug(f"OPTIONS response headers: {dict(response.headers)}")
        logger.debug("SSE endpoint - Returning OPTIONS response")
        return response

    user_id = session.get('user_id')
    logger.debug(f"SSE endpoint - user_id from session: {user_id}")

    # For testing, also try to get user_id from query parameter
    if not user_id:
        user_id = request.args.get('user_id')
        logger.debug(f"SSE endpoint - user_id from query param: {user_id}")

    if not user_id:
        logger.debug("SSE endpoint - No user_id in session or query param, returning 401")
        return Response("Unauthorized", status=401, mimetype="text/plain")

    redis = get_redis_connection()
    pubsub = redis.pubsub()
    pubsub.subscribe(f"user:{user_id}")

    # Optionally: get last known timestamp or event ID
    # For simplicity, we assume the frontend sends ?since=timestamp
    since = request.args.get('since')

    def event_stream() -> str:
        """
        Generator function to stream events to the client.
        :return: Yields event data as a string in SSE format.
        """
        # Replay missed events
        key = f"user:{user_id}:events"
        past_events = redis.lrange(key, 0, -1)

        for raw in past_events:
            try:
                event = json.loads(raw)
                if not since or event.get("timestamp") > since:
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as e:
                logger.error("Error parsing replay event:", e)

        for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"

    response = Response(event_stream(), mimetype="text/event-stream")
    # Allow both localhost and 127.0.0.1 for development
    origin = request.headers.get('Origin')
    logger.debug(f"GET Origin: {origin}")
    # Always allow the origin for SSE
    response.headers['Access-Control-Allow-Origin'] = origin or '*'
    logger.debug(f"Setting GET Access-Control-Allow-Origin to: {origin or '*'}")
    # Don't require credentials for SSE
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, Cache-Control'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    logger.debug(f"GET response headers: {dict(response.headers)}")
    return response


@app.route('/api/sse', methods=['GET'])
def sse() -> Tuple[Response, int]:
    """
    Test endpoint to publish an event to the SSE stream.
    :return: Response object indicating success or failure.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Example event data
    event_data = {
        "type": "new_message",
        "conversation_id": "test-123",
        "sender": "Test User",
        "text": "This is a test message",
        "timestamp": str(time.time())
    }
    publish_event_with_buffer(user_id, event_data)

    return jsonify({"message": "Event published successfully"}), 200

@app.route('/api/test/appointment-reminder', methods=['POST'])
def test_appointment_reminder() -> Tuple[Response, int]:
    """
    Test endpoint to send an appointment reminder event.
    :return: Response object indicating success or failure.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    event_data = {
        "type": "appointment_reminder",
        "appointmentId": data.get('appointmentId', 'test-123'),
        "time": data.get('time', str(time.time())),
        "content": data.get('content', 'Test appointment reminder'),
        "timestamp": str(time.time())
    }
    publish_event_with_buffer(user_id, event_data)

    return jsonify({"message": "Appointment reminder sent successfully"}), 200



# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
def register() -> Tuple[Response, int]:
    """
    Register a new user.
    :return: Response object with registration status.
    """
    return register_route()

@app.route('/api/auth/login', methods=['POST'])
def login() -> Tuple[Response, int]:
    """
    Login endpoint for users.
    :return: Response object with login status.
    """
    return login_route()

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout() -> Tuple[Response, int]:
    """
    Logout endpoint for users.
    :return: Response object with logout status.
    """
    return logout_route()

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user_info() -> Tuple[Response, int]:
    """
    Get the current user's information.
    :return: Response object with user information.
    """
    return get_current_user_info_route()

@app.route('/api/auth/change-password', methods=['POST'])
@require_auth
def change_password() -> Tuple[Response, int]:
    """
    Change the password for the current user.
    :return: Response object with change password status.
    """
    return change_password_route()

# Admin endpoints
@app.route('/api/admin/users', methods=['GET'])
@require_admin
def get_all_users() -> Tuple[Response, int]:
    """
    Get a list of all users.
    :return: Response object with user list.
    """
    return get_all_users_route()

@app.route('/api/admin/users/<user_id>/deactivate', methods=['POST'])
@require_admin
def deactivate_user(user_id: str) -> Tuple[Response, int]:
    """
    Deactivate a user by their user ID.
    :param user_id: The ID of the user to deactivate.
    :return: Response object with deactivation status.
    """
    return deactivate_user_route(user_id)

@app.route('/api/admin/users/<user_id>/activate', methods=['POST'])
@require_admin
def activate_user(user_id: str) -> Tuple[Response, int]:
    """
    Activate a user by their user ID.
    :param user_id: The ID of the user to activate.
    :return: Response object with activation status.
    """
    return activate_user_route(user_id)

@app.route('/api/admin/setup', methods=['POST'])
def setup_default_admin() -> Tuple[Response, int]:
    """
    Setup the default admin user and initial configuration.
    :return: Response object with setup status.
    """
    return setup_default_admin_route()

@app.route('/api/users/exist', methods=['GET'])
def check_users_exist() -> Tuple[Response, int]:
    """
    Check if users exist in the system.
    :return: Response object with existence check status.
    """
    return check_users_exist_route()

@app.route('/api/debug/session', methods=['GET'])
def debug_session() -> Tuple[Response, int]:
    """
    Debug endpoint to inspect the current session.
    :return: Response object with session data.
    """
    return debug_session_route()

@app.route('/api/users/search', methods=['GET'])
@require_auth
def search_users() -> Tuple[Response, int]:
    """
    Search for users in the system.
    :return: Response object with search results.
    """
    return search_users_route()

@app.route('/api/conversations', methods=['GET'])
@require_auth
def get_user_conversations() -> Tuple[Response, int]:
    """
    Get conversations for the authenticated user.
    :return: Response object with user conversations.
    """
    return get_user_conversations_route()

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
@require_auth
def get_conversation_messages(conversation_id: str) -> Tuple[Response, int]:
    """
    Get messages for a specific conversation.
    :param conversation_id: The ID of the conversation to retrieve messages for.
    :return: Response object with conversation messages.
    """
    return get_conversation_messages_route(conversation_id)

@app.route('/api/conversations/<conversation_id>/messages', methods=['POST'])
@require_auth
def send_message(conversation_id: str) -> Tuple[Response, int]:
    """
    Send a message to a specific conversation.
    :param conversation_id: The ID of the conversation to send a message to.
    :return: Response object with message sending status.
    """
    return send_message_route(conversation_id)

@app.route('/api/conversations', methods=['POST'])
@require_auth
def create_conversation() -> Tuple[Response, int]:
    """
    Create a new conversation for the authenticated user.
    :return: Response object with conversation creation status.
    """
    return create_conversation_route()

# TODO: Do we even use this one?
@app.route('/api/chat', methods=['GET', 'POST'])
@optional_auth
def chat_endpoint() -> Tuple[Response, int]:
    """
    Endpoint to handle chat conversations.
    :return: Response object with chat data.
    """
    if request.method == 'GET':
        return jsonify(DUMMY_CONVERSATIONS), 200
    elif request.method == 'POST':
        data = request.json
        # In a real app, you'd save this to a database
        # For now, we'll just return success
        return jsonify({"message": "Conversations saved successfully"}), 200
    else:
        return jsonify({"error": "Method not allowed"}), 405

@app.route('/api/llm_chat', methods=['GET', 'POST'])
@require_auth
def llm_agent_endpoint() -> Tuple[Response, int]:
    """
    Endpoint for LLM agent interactions.
    :return: Response object with LLM agent data.
    """
    return llm_agent_endpoint_route()

@app.route('/api/llm_chat/reset', methods=['POST'])
@optional_auth
def reset_llm_chat() -> Tuple[Response, int]:
    """
    Reset the LLM chat session
    :return: Response object indicating the reset status.
    """
    session.pop('agent_data', None)
    return jsonify({"message": "Chat session reset successfully"}), 200

@app.route('/api/time')
#@cross_origin()
def get_current_time() -> Tuple[Response, int]:
    """
    Endpoint to get the current server time.
    :return: Response object with the current time.
    """
    response = jsonify({'time': time.time()})
    return response

@app.route('/api/patients', methods=['GET', 'POST'])
def patients_endpoint() -> Tuple[Response, int]:
    """
    Endpoint to handle patient data.
    :return: Response object with patient data.
    """
    return patients_endpoint_route()

@app.route('/api/patients/<patient_id>', methods=['GET', 'PUT', 'DELETE'])
def patient_endpoint(patient_id: str) -> Tuple[Response, int]:
    """
    Endpoint to handle a specific patient by ID.
    :param patient_id: The ID of the patient to retrieve or modify.
    :return: Response object with patient data.
    """
    return patient_endpoint_route(patient_id)

@app.route('/api/patients/search', methods=['GET'])
@require_auth
def search_patients() -> Tuple[Response, int]:
    """
    Search for patients in the system.
    :return: Response object with search results.
    """
    return search_patients_route()

# Encounter endpoints
@app.route('/api/encounters', methods=['GET'])
@require_auth
@require_api_key
@require_api_permission('encounters:read')
def get_all_encounters() -> Tuple[Response, int]:
    """
    Get all encounters in the system.
    :return: Response object with all encounters.
    """
    return get_all_encounters_route()

@app.route('/api/encounters/search', methods=['GET'])
@require_auth
@require_api_key
@require_api_permission('encounters:read')
def search_encounters() -> Tuple[Response, int]:
    """
    Search for encounters in the system.
    :return: Response object with search results.
    """
    return search_encounters_route()

@app.route('/api/patients/<patient_id>/encounters', methods=['GET'])
@require_auth
@require_api_key
@require_api_permission('encounters:read')
def get_patient_encounters(patient_id: str) -> Tuple[Response, int]:
    """
    Get all encounters for a specific patient.
    :param patient_id: The ID of the patient to retrieve encounters for.
    :return: Response object with patient encounters.
    """
    return get_encounters_by_patient_route(patient_id)

@app.route('/api/encounters/<encounter_id>', methods=['GET'])
@require_auth
@require_api_key
@require_api_permission('encounters:read')
def get_encounter(encounter_id: str) -> Tuple[Response, int]:
    """
    Get a specific encounter by its ID.
    :param encounter_id: The ID of the encounter to retrieve.
    :return: Response object with encounter data.
    """
    return get_encounter_by_id_route(encounter_id)

@app.route('/api/patients/<patient_id>/encounters', methods=['POST'])
@require_auth
@require_api_key
@require_api_permission('encounters:write')
def create_patient_encounter(patient_id: str) -> Tuple[Response, int]:
    """
    Create a new encounter for a specific patient.
    :param patient_id: The ID of the patient to create an encounter for.
    :return: Response object with encounter creation status.
    """
    return create_encounter_route(patient_id)

@app.route('/api/encounters/<encounter_id>', methods=['PUT'])
@require_auth
@require_api_key
@require_api_permission('encounters:write')
def update_encounter(encounter_id: str) -> Tuple[Response, int]:
    """
    Update an existing encounter by its ID.
    :param encounter_id: The ID of the encounter to update.
    :return: Response object with encounter update status.
    """
    return update_encounter_route(encounter_id)

@app.route('/api/encounters/<encounter_id>', methods=['DELETE'])
@require_auth
@require_api_key
@require_api_permission('encounters:write')
def delete_encounter(encounter_id: str) -> Tuple[Response, int]:
    """
    Delete an existing encounter by its ID.
    :param encounter_id: The ID of the encounter to delete.
    :return: Response object with encounter deletion status.
    """
    return delete_encounter_route(encounter_id)

# API Key Management endpoints
@app.route('/api/keys', methods=['GET'])
@require_auth
def list_api_keys() -> Tuple[Response, int]:
    """
    List all API keys for the authenticated user.
    :return: Response object with API keys list.
    """
    return list_api_keys_route()

@app.route('/api/keys', methods=['POST'])
@require_auth
def create_api_key() -> Tuple[Response, int]:
    """
    Create a new API key for the authenticated user.
    :return: Response object with API key creation status.
    """
    return create_api_key_route()

@app.route('/api/keys/<key_id>', methods=['DELETE'])
@require_auth
def delete_api_key(key_id: str) -> Tuple[Response, int]:
    """
    Delete an API key.
    :param key_id: The ID of the API key to delete.
    :return: Response object with deletion status.
    """
    return delete_api_key_route(key_id)

@app.route('/api/keys/<key_id>/deactivate', methods=['POST'])
@require_auth
def deactivate_api_key(key_id: str) -> Tuple[Response, int]:
    """
    Deactivate an API key (soft delete).
    :param key_id: The ID of the API key to deactivate.
    :return: Response object with deactivation status.
    """
    return deactivate_api_key_route(key_id)

@app.route('/api/keys/<key_id>/usage', methods=['GET'])
@require_auth
def get_api_key_usage(key_id: str) -> Tuple[Response, int]:
    """
    Get usage statistics for an API key.
    :param key_id: The ID of the API key.
    :return: Response object with usage statistics.
    """
    return get_api_key_usage_route(key_id)

@app.route('/api/encounters/extract-entities', methods=['POST'])
@require_auth
def extract_entities_from_notes() -> Tuple[Response, int]:
    """
    Extract entities and ICD codes from encounter notes.
    :return: Response object with extracted entities and ICD codes.
    """
    return extract_entities_from_notes_route()


@app.route('/api/encounters/cache-stats', methods=['GET'])
@require_auth
def get_cache_stats() -> Tuple[Response, int]:
    """
    Get entity cache statistics.
    :return: Response object with cache statistics.
    """
    return get_cache_stats_route()

@app.route('/api/test_surrealdb', methods=['GET'])
@require_admin
def test_surrealdb() -> Tuple[Response, int]:
    """
    Test endpoint to verify SurrealDB connection
    :return: Response object with test status.
    """
    return test_surrealdb_route()

@app.route('/api/test_crud', methods=['GET'])
def test_crud() -> Tuple[Response, int]:
    """
    Test endpoint to verify CRUD operations
    :return: Response object with CRUD test status.
    """
    return test_crud_route()

@app.route('/api/intake/<patient_id>', methods=['PATCH'])
def patch_intake(patient_id: str) -> Tuple[Response, int]:
    """
    Patch the intake information for a specific patient.
    :param patient_id: The ID of the patient to patch intake information for.
    :return: Response object with intake patch status.
    """
    return patch_intake_route(patient_id)

@app.route('/api/settings', methods=['GET', 'POST'])
@require_auth
def settings() -> Tuple[Response, int]:
    """
    Endpoint to get or update user settings.
    :return: Response object with settings data or update status.
    """
    return settings_route()

@app.route('/api/usage', methods=['GET'])
@require_auth
def api_usage() -> Tuple[Response, int]:
    """
    Endpoint to get API usage statistics.
    :return: Response object with API usage data.
    """
    return get_api_usage_route()

@app.route('/api/profile', methods=['GET'])
@require_auth
def get_user_profile() -> Tuple[Response, int]:
    """
    Endpoint to get the user profile information.
    :return: Response object with user profile data.
    """
    return get_user_profile_route()

@app.route('/api/profile', methods=['POST'])
@require_auth
def update_user_profile() -> Tuple[Response, int]:
    """
    Endpoint to update the user profile information.
    :return: Response object with user profile update status.
    """
    return update_user_profile_route()

# Appointment endpoints
@app.route('/api/appointments', methods=['GET'])
@require_auth
def get_appointments() -> Tuple[Response, int]:
    """
    Get a list of appointments for the authenticated user.
    :return: Response object with appointments data.
    """
    return get_appointments_route()

@app.route('/api/appointments', methods=['POST'])
@require_auth
def create_appointment() -> Tuple[Response, int]:
    """
    Create a new appointment for the authenticated user.
    :return: Response object with appointment creation status.
    """
    return create_appointment_route()

@app.route('/api/appointments/<appointment_id>', methods=['GET'])
@require_auth
def get_appointment(appointment_id: str) -> Tuple[Response, int]:
    """
    Get details of a specific appointment by its ID.
    :param appointment_id: The ID of the appointment to retrieve.
    :return: Response object with appointment details.
    """
    return get_appointment_route(appointment_id)

@app.route('/api/appointments/<appointment_id>', methods=['PUT'])
@require_auth
def update_appointment(appointment_id: str) -> Tuple[Response, int]:
    """
    Update an existing appointment by its ID.
    :param appointment_id: The ID of the appointment to update.
    :return: Response object with appointment update status.
    """
    return update_appointment_route(appointment_id)

@app.route('/api/appointments/<appointment_id>/cancel', methods=['POST'])
@require_auth
def cancel_appointment(appointment_id: str) -> Tuple[Response, int]:
    """
    Cancel an existing appointment by its ID.
    :param appointment_id: The ID of the appointment to cancel.
    :return: Response object with appointment cancellation status.
    """
    return cancel_appointment_route(appointment_id)

@app.route('/api/appointments/<appointment_id>/confirm', methods=['POST'])
@require_auth
def confirm_appointment(appointment_id: str) -> Tuple[Response, int]:
    """
    Confirm an existing appointment by its ID.
    :param appointment_id: The ID of the appointment to confirm.
    :return: Response object with appointment confirmation status.
    """
    return confirm_appointment_route(appointment_id)

@app.route('/api/appointments/available-slots', methods=['GET'])
@require_auth
def get_available_slots() -> Tuple[Response, int]:
    """
    Get available time slots for appointments.
    :return: Response object with available slots data.
    """
    return get_available_slots_route()

@app.route('/api/appointments/types', methods=['GET'])
@require_auth
def get_appointment_types() -> Tuple[Response, int]:
    """
    Get a list of appointment types.
    :return: Response object with appointment types data.
    """
    return get_appointment_types_route()

@app.route('/api/appointments/statuses', methods=['GET'])
@require_auth
def get_appointment_statuses() -> Tuple[Response, int]:
    """
    Get a list of appointment statuses.
    :return: Response object with appointment statuses data.
    """
    return get_appointment_statuses_route()


# Webhook endpoints
@app.route('/api/webhooks', methods=['GET'])
@require_auth
def get_webhook_subscriptions() -> Tuple[Response, int]:
    """
    Get webhook subscriptions for the authenticated user.
    :return: Response object with webhook subscriptions data.
    """
    return get_webhook_subscriptions_route()


@app.route('/api/webhooks', methods=['POST'])
@require_auth
def create_webhook_subscription() -> Tuple[Response, int]:
    """
    Create a new webhook subscription.
    :return: Response object with webhook subscription creation status.
    """
    return create_webhook_subscription_route()


@app.route('/api/webhooks/<subscription_id>', methods=['GET'])
@require_auth
def get_webhook_subscription(subscription_id: str) -> Tuple[Response, int]:
    """
    Get a specific webhook subscription by its ID.
    :param subscription_id: The ID of the subscription to retrieve.
    :return: Response object with webhook subscription details.
    """
    return get_webhook_subscription_route(subscription_id)


@app.route('/api/webhooks/<subscription_id>', methods=['PUT'])
@require_auth
def update_webhook_subscription(subscription_id: str) -> Tuple[Response, int]:
    """
    Update an existing webhook subscription by its ID.
    :param subscription_id: The ID of the subscription to update.
    :return: Response object with webhook subscription update status.
    """
    return update_webhook_subscription_route(subscription_id)


@app.route('/api/webhooks/<subscription_id>', methods=['DELETE'])
@require_auth
def delete_webhook_subscription(subscription_id: str) -> Tuple[Response, int]:
    """
    Delete an existing webhook subscription by its ID.
    :param subscription_id: The ID of the subscription to delete.
    :return: Response object with webhook subscription deletion status.
    """
    return delete_webhook_subscription_route(subscription_id)

@app.route('/api/webhooks/events', methods=['GET'])
@require_auth
def get_webhook_events() -> Tuple[Response, int]:
    """
    Get available webhook events.
    :return: Response object with webhook events data.
    """
    return get_webhook_events_route()

@app.route('/api/lab_results', methods=['GET'])
@require_auth
def get_lab_results() -> Tuple[Response, int]:
    """
    Get lab results for the authenticated user.
    :return: Response object with lab results data.
    """
    lab_results_service: LabResultsService = LabResultsService(
        hematology=hematology,
        differential_hematology=differential_hematology,
        general_chemistry=general_chemistry,
        serum_proteins=serum_proteins,
    )
    return jsonify(lab_results_service.lab_results), 200

@app.route('/api/optimal', methods=['POST'])
@require_auth
def call_optimal() -> Tuple[Response, int]:
    """
    Process the optimal table data and call the Optimal service.
    :return: Response object with optimal table data.
    """
    return call_optimal_route()

# Organizations endpoints
@app.route('/api/organizations/<org_id>', methods=['GET'])
def get_organization(org_id: str) -> Union[Tuple[Response, int], werkzeug.wrappers.response.Response]:
    """
    Get a specific organization by ID.
    :return: Response object with organization data.
    """
    print(f"get_organization: {org_id}")
    if org_id.startswith('User:'):
        print(f"redirecting to /api/organizations/user/{org_id}")
        return redirect(f'/api/organizations/user/{org_id}')
    from lib.routes.organizations import get_organization_route
    return get_organization_route(org_id)

@app.route('/api/organizations/user/<user_id>', methods=['GET'])
def get_organization_by_user_id(user_id: str) -> Tuple[Response, int]:
    """
    Get a specific organization by ID.
    :return: Response object with organization data.
    """
    from lib.routes.organizations import get_organization_by_user_id_route
    return get_organization_by_user_id_route(user_id)

@app.route('/api/organizations', methods=['POST'])
def create_organization_api() -> Tuple[Response, int]:
    """
    Create a new organization.
    :return: Response object with created organization data.
    """
    from lib.routes.organizations import create_organization_route
    return create_organization_route()

@app.route('/api/organizations/<org_id>', methods=['PUT'])
def update_organization_api(org_id: str) -> Tuple[Response, int]:
    """
    Update an organization by ID.
    :return: Response object with updated organization data.
    """
    from lib.routes.organizations import update_organization_route
    return update_organization_route(org_id)

@app.route('/api/organizations/<org_id>/clinics', methods=['GET'])
def get_organization_clinics(org_id: str) -> Tuple[Response, int]:
    """
    Get all clinics for an organization.
    :return: Response object with clinics data.
    """
    from lib.routes.organizations import get_organization_clinics_route
    return get_organization_clinics_route(org_id)

@app.route('/api/organizations/<org_id>/clinics', methods=['POST'])
def add_clinic_to_organization(org_id: str) -> Tuple[Response, int]:
    """
    Add a clinic to an organization.
    :return: Response object with updated organization data.
    """
    from lib.routes.organizations import add_clinic_to_organization_route
    return add_clinic_to_organization_route(org_id)

@app.route('/api/organizations/<org_id>/clinics', methods=['DELETE'])
def remove_clinic_from_organization(org_id: str) -> Tuple[Response, int]:
    """
    Remove a clinic from an organization.
    :return: Response object with updated organization data.
    """
    from lib.routes.organizations import remove_clinic_from_organization_route
    return remove_clinic_from_organization_route(org_id)


# User Notes endpoints
@app.route('/api/user-notes', methods=['GET'])
@require_auth
def get_user_notes() -> Tuple[Response, int]:
    """
    Get all notes for the current user.
    :return: Response object with user notes data.
    """
    return get_user_notes_route()

@app.route('/api/user-notes', methods=['POST'])
@require_auth
def create_note() -> Tuple[Response, int]:
    """
    Create a new note for the current user.
    :return: Response object with created note data.
    """
    return create_note_route()

@app.route('/api/user-notes/<note_id>', methods=['GET'])
@require_auth
def get_note_by_id(note_id: str) -> Tuple[Response, int]:
    """
    Get a specific note by ID.
    :return: Response object with note data.
    """
    return get_note_by_id_route(note_id)

@app.route('/api/user-notes/<note_id>', methods=['PUT'])
@require_auth
def update_note(note_id: str) -> Tuple[Response, int]:
    """
    Update a note by ID.
    :return: Response object with updated note data.
    """
    return update_note_route(note_id)

@app.route('/api/user-notes/<note_id>', methods=['DELETE'])
@require_auth
def delete_note(note_id: str) -> Tuple[Response, int]:
    """
    Delete a note by ID.
    :return: Response object with deletion status.
    """
    return delete_note_route(note_id)

@app.route('/auth/login/cognito')
def login_cognito():
    role = request.args.get('role', 'patient')
    intent = request.args.get('intent', 'signin')
    
    # Validate and set default role if empty or invalid
    if not role or role.strip() == '':
        role = 'patient'
        logger.info("Invalid role: . Defaulting to 'patient'.")
    
    # Validate role is one of the allowed values
    valid_roles = ['patient', 'provider', 'admin']
    if role not in valid_roles:
        role = 'patient'
        logger.info(f"Invalid role: {role}. Defaulting to 'patient'.")
    
    # Validate and set default intent if empty or invalid
    valid_intents = ['signin', 'signup', 'reset']
    if intent not in valid_intents:
        intent = 'signin'
        logger.info(f"Invalid intent: {intent}. Defaulting to 'signin'.")
    
    # Pass both role and intent in the state parameter
    state = f"{role}:{intent}"
    cognito_url = (
        f"https://{COGNITO_DOMAIN}/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"  # e.g., https://demo.arsmedicatech.com/auth/cognito
        f"&scope=openid+email+profile"
        f"&state={state}"
    )
    return redirect(cognito_url)

@app.route('/auth/callback', methods=['GET', 'POST'])
def cognito_callback() -> Union[Tuple[Response, int], BaseResponse]:
    """
    Cognito login endpoint.
    :return: Response object with login status.
    """
    return cognito_login_route()

@app.route('/test/auth-error')
def test_auth_error():
    """
    Test route to simulate OAuth callback errors for testing the ErrorModal component.
    """
    error = request.args.get('error', 'invalid_request')
    error_description = request.args.get('error_description', 'Email already exists')
    suggested_action = request.args.get('suggested_action', 'login')
    intent = request.args.get('intent', 'signup')  # Add intent parameter
    
    # Redirect to frontend with error parameters (simulating the OAuth callback error flow)
    from urllib import parse
    error_url = f"{APP_URL}?error={error}&error_description={parse.quote(error_description)}&suggested_action={suggested_action}&intent={intent}"
    return redirect(error_url)

@app.route('/auth/logout', methods=['GET'])
def auth_logout() -> BaseResponse:
    """
    Logout endpoint.
    :return: Response object with logout status.
    """
    return auth_logout_route()

# Register event handlers for webhook delivery
register_event_handlers()


def validate_plugin_manifest(manifest: Dict[str, Any]) -> bool:
    """
    Validate the plugin manifest to ensure it has the required fields.
    :param manifest: The plugin manifest dictionary.
    :return: True if valid, False otherwise.
    """
    required_fields = ['name', 'version', 'description']
    return all(field in manifest for field in required_fields)

def is_plugin_frontend_only(manifest: Dict[str, Any]) -> bool:
    """
    Check if the plugin is frontend only.
    :param manifest: The plugin manifest dictionary.
    :return: True if frontend only, False otherwise.
    """
    if 'main_js' in manifest and not 'main_py' in manifest:
        return True
    return False

def load_and_attach_plugins() -> None:
    """
    Load and attach plugins to the Flask app.
    This function should be called after the app is created.
    """
    PLUGIN_DIR = 'plugins'
    import os
    from importlib import import_module

    # Iterate through all directories in the plugins directory
    for plugin_name in os.listdir(PLUGIN_DIR):
        plugin_path = os.path.join(PLUGIN_DIR, plugin_name)
        if os.path.isdir(plugin_path):
            try:
                # validate the plugin manifest
                manifest_path = os.path.join(plugin_path, 'manifest.json')
                if not os.path.exists(manifest_path):
                    logger.error(f"Plugin {plugin_name} is missing manifest.json")
                    continue
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                if not validate_plugin_manifest(manifest):
                    logger.error(f"Plugin {plugin_name} manifest is invalid: {manifest}")
                    continue
                if is_plugin_frontend_only(manifest):
                    logger.debug(f"Plugin {plugin_name} is frontend only.")
                    continue
                entry_point = manifest.get('main_py')
                if plugin_name != manifest.get('name'):
                    logger.error(f"Plugin {plugin_name} name does not match manifest name: {manifest.get('name')}")
                    continue
                plugin_module = import_module(f"{PLUGIN_DIR}.{plugin_name}.py.{entry_point.replace('.py', '')}")
                plugin_bp = plugin_module.plugin_bp
                app.register_blueprint(plugin_bp)
                logger.debug(f"Registered plugin {plugin_name} with blueprint {plugin_bp}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_name}: {e}")


load_and_attach_plugins()


@app.route('/api/plugins', methods=['GET'])
def get_plugins():
    """
    Get a list of plugins by reading their manifest.json files.
    """
    import os
    PLUGIN_DIR = 'plugins'
    plugins: List[Dict[str, Any]] = []
    for plugin_name in os.listdir(PLUGIN_DIR):
        manifest_path = os.path.join(PLUGIN_DIR, plugin_name, 'manifest.json')
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
                plugins.append({
                    'name': manifest.get('name'),
                    'main_js': manifest.get('main_js'),
                    'description': manifest.get('description'),
                })
    return jsonify(plugins), 200

@app.route('/plugin/<plugin_name>', methods=['GET'])
def serve_plugin_js(plugin_name: str) -> Tuple[Response, int]:
    import os
    plugin_js_path = Path(f'plugins/{plugin_name}/js')
    js_file: str = os.path.join(plugin_js_path, 'index.js')
    if not os.path.exists(js_file):
        abort(404)
    print(f"Serving plugin JS for {plugin_name} from {js_file}")
    response = send_from_directory(plugin_js_path, 'index.js', mimetype='application/javascript')
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response, 200


# Register the SSE blueprint
app.register_blueprint(sse_bp)
app.register_blueprint(uploads_bp)

from asgiref.wsgi import WsgiToAsgi

asgi_app = WsgiToAsgi(app)

@app.route('/api/admin/organizations', methods=['GET'])
def get_organizations() -> Tuple[Response, int]:
    """
    Get a list of organizations.
    :return: Response object with organizations data.
    """
    return get_organizations_route()

@app.route('/api/admin/my_organization', methods=['GET'])
def get_my_organization() -> Tuple[Response, int]:
    """
    Get the organization of the current user.
    :return: Response object with organization data.
    """
    current_user = session.get('user_id')
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    user_service = UserService()
    try:
        org_d = user_service.get_organization_id(current_user)
        if not org_d:
            return jsonify({"error": "Organization not found"}), 404
        return jsonify(dict(org_id=org_d)), 200
    except UserNotAffiliatedError as e:
        logger.error(f"User {current_user} is not affiliated with an organization: {e}")
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        logger.error(f"Error getting organization for user {current_user}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/clinics/<org_id>', methods=['GET'])
def get_clinics(org_id: str) -> Tuple[Response, int]:
    """
    Get a list of clinics.
    :param org_id: The ID of the organization to retrieve clinics for.
    :return: Response object with clinics data.
    """
    return get_clinics_route(org_id)

@app.route('/api/admin/patients/<org_id>', methods=['GET'])
def get_patients(org_id: str) -> Tuple[Response, int]:
    """
    Get a list of patients.
    :param org_id: The ID of the organization to retrieve patients for.
    :return: Response object with patients data.
    """
    return get_patients_route(org_id)

@app.route('/api/admin/providers/<org_id>', methods=['GET'])
def get_providers(org_id: str) -> Tuple[Response, int]:
    """
    Get a list of providers.
    :param org_id: The ID of the organization to retrieve providers for.
    :return: Response object with providers data.
    """
    return get_providers_route(org_id)

@app.route('/api/admin/administrators/<org_id>', methods=['GET'])
def get_administrators(org_id: str) -> Tuple[Response, int]:
    """
    Get a list of administrators.
    :param org_id: The ID of the organization to retrieve administrators for.
    :return: Response object with administrators data.
    """
    return get_administrators_route(org_id)


if __name__ == '__main__': app.run(port=PORT, debug=DEBUG, host=HOST)
