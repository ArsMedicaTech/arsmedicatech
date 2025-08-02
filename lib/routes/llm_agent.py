"""
LLM Agent Endpoint
"""
import asyncio
from typing import Any, Dict, Optional, Tuple

from flask import Response, jsonify, request, session

from lib.data_types import UserID
from lib.llm.agent import LLMAgent, LLMModel
from lib.services.auth_decorators import get_current_user
from lib.services.llm_chat_service import LLMChatService
from lib.services.openai_security import get_openai_security_service
from settings import MCP_URL, logger


def llm_agent_endpoint_route() -> Tuple[Response, int]:
    """
    Route for the LLM agent endpoint.
    :return: Response object with JSON data or error message.
    """
    logger.debug('[DEBUG] /api/llm_chat called')
    logger.debug('[DEBUG] Request headers: %s', str(dict(request.headers)))
    # Get current user from auth decorator
    current_user = get_current_user()
    if not current_user:
        logger.debug('[DEBUG] Not authenticated in /api/llm_chat')
        return jsonify({"error": "Not authenticated"}), 401
    
    current_user_id = current_user.user_id
    logger.debug('[DEBUG] User authenticated: %s', current_user_id)

    llm_chat_service = LLMChatService()
    llm_chat_service.connect()
    try:
        if request.method == 'GET':
            chats = llm_chat_service.get_llm_chats_for_user(UserID(current_user_id))
            return jsonify([chat.to_dict() for chat in chats]), 200
        elif request.method == 'POST':
            data: Optional[Dict[str, Any]] = request.json
            if data is None:
                return jsonify({"error": "Invalid JSON data"}), 400
                
            assistant_id = data.get('assistant_id', 'ai-assistant')
            prompt = data.get('prompt')
            if not prompt:
                return jsonify({"error": "No prompt provided"}), 400

            # Get user's OpenAI API key with security validation
            security_service = get_openai_security_service()
            openai_api_key, error = security_service.get_user_api_key_with_validation(str(current_user_id))
            
            if not openai_api_key:
                return jsonify({"error": error}), 400

            # Add user message to persistent chat
            chat = llm_chat_service.add_message(UserID(current_user_id), assistant_id, 'Me', prompt)

            agent = asyncio.run(
                LLMAgent.from_mcp(
                    mcp_url=MCP_URL,
                    api_key=openai_api_key,
                    model=LLMModel.GPT_4_1_NANO,
                )
            )

            # Use the persistent chat history as context
            history: list[Dict[str, Any]] = chat.messages
            print(f"History: {history}")  # Debugging line to check history content
            # You may want to format this for your LLM
            response = asyncio.run(agent.complete(prompt))  # Remove history parameter as it's not supported
            logger.debug('response', type(response), response)

            # Log API usage
            security_service.log_api_usage(str(current_user_id), str(LLMModel.GPT_4_1_NANO))

            # Add assistant response to persistent chat
            used_tools = response.get('used_tools', [])
            chat = llm_chat_service.add_message(
                UserID(current_user_id), 
                assistant_id, 
                'AI Assistant',
                response.get('response', ''),
                used_tools
            )

            # Save updated agent state to session
            session['agent_data'] = agent.to_dict()

            # Return chat data with tool usage information
            chat_data = chat.to_dict()
            chat_data['used_tools'] = response.get('used_tools', [])
            
            return jsonify(chat_data), 200
        else:
            return jsonify({"error": "Method not allowed"}), 405
    except Exception as e:
        logger.error(f"Error in llm_agent_endpoint: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        llm_chat_service.close()
