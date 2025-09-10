"""
Utility code for interacting with the ArsMedicaTech API.
"""
from typing import Dict, Optional

import json

import requests

from bench.settings import API_URL, OPENAI_API_KEY


def provision_api_key(session_token: str) -> str:
    """
    Provisions an API key with specific permissions.

    The simplest way to obtain a valid session token is to log in via the web interface,
    then go to this specially made URL: `/api/debug/session_v2` and copy the `auth_token` value.

    :param session_token: The session token for authentication.
    :return: The provisioned API key.
    """
    url = f"{API_URL}/api/keys"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_token}"
    }

    data = {
        "name": "LLM Agent Testing",
        "permissions": ["llm:chat", "llm:read"],
        "rate_limit_per_hour": 1000,
        "expires_in_days": 30
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        api_key = response.json().get("api_key")
        if api_key:
            print("API key provisioned successfully.")
            return api_key
        else:
            raise Exception("API key not found in response.")
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


def call_llm_chat(prompt: str, openai_api_key: str, api_key: str) -> Dict[str, str]:
    """
    Calls the LLM chat endpoint with the given prompt and API keys.
    :param prompt: The prompt to send to the LLM.
    :param openai_api_key: The OpenAI API key for the LLM service.
    :param api_key: The ArsMedicaTech API key for authentication.
    :return:
    """
    url = f"{API_URL}/api/llm_chat"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key
    }
    data = {
        "prompt": prompt,
        "openai_api_key": openai_api_key,
        #"response_format": MCQQuestionResponse.schema(),
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")


def call_your_system(prompt: str, api_key: str) -> Optional[Dict[str, str]]:
    """
    Call your system's API with the provided prompt.
    :param prompt: str - The prompt to send to your system.
    :return: str - The response from your system.
    """
    try:
        response = call_llm_chat(prompt, openai_api_key=OPENAI_API_KEY, api_key=api_key)
        print(f"Response from your system: {response}")
        # {'sender': 'AI Assistant', 'text': 'D', 'timestamp': '2025-08-14T15:56:02.729533+00:00', 'used_tools': ['rag']}
        text = response.get('messages', [{}])[-1].get('text', '')
        used_tools = response.get('messages', [{}])[-1].get('used_tools', [])
        print(f"Text: {text}")
        print(f"Used tools: {used_tools}")
        try:
            return json.loads(text)
        except:
            return {"result": text}
    except Exception as e:
        print(f"Error calling your system: {e}")
        return None
