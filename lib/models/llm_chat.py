"""
LLM Chat Model
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from lib.data_types import UserID


class LLMChat:
    """
    Represents a chat session with an LLM (Large Language Model) assistant.
    """
    def __init__(
            self,
            user_id: UserID,
            assistant_id: str = "ai-assistant",
            messages: Optional[List[Dict[str, Any]]] = None,
            created_at: Optional[str] = None,
            id: Optional[str] = None
    ) -> None:
        """
        Initializes an LLMChat instance.
        :param user_id: User ID of the chat participant.
        :param assistant_id: ID of the assistant (default is "ai-assistant").
        :param messages: List of messages in the chat. Each message should be a dictionary with keys like 'sender', 'text', and 'timestamp'.
        :param created_at: Creation timestamp of the chat session in ISO format. If not provided, the current time is used.
        :param id: Optional unique identifier for the chat session. If not provided, it will be generated.
        :return: None
        """
        self.user_id = user_id
        self.assistant_id = assistant_id
        self.messages = messages or []
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.id = id

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the LLMChat instance to a dictionary representation.
        :return: Dict containing the chat details.
        """
        return {
            "user_id": self.user_id,
            "assistant_id": self.assistant_id,
            "messages": self.messages,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMChat':
        """
        Creates an LLMChat instance from a dictionary.
        :param data: Dictionary containing chat details. Expected keys are 'user_id', 'assistant_id', 'messages', 'created_at', and 'id'.
        :return: LLMChat instance
        """
        chat_id = data.get('id')
        if hasattr(chat_id, '__str__'):
            chat_id = str(chat_id)
        user_id = data.get('user_id')
        if user_id is None:
            raise ValueError("user_id is required and cannot be None")
        return cls(
            user_id=user_id,
            assistant_id=data.get('assistant_id', 'ai-assistant'),
            messages=data.get('messages', []),
            created_at=data.get('created_at'),
            id=chat_id
        )

    def add_message(self, sender: str, text: str, used_tools: Optional[List[str]] = None) -> None:
        """
        Adds a new message to the chat session.
        :param sender: The sender of the message (e.g., 'user' or 'assistant').
        :param text: The text content of the message.
        :param used_tools: Optional list of tools used in this message.
        :return: None
        """
        message: Dict[str, Any] = {
            "sender": sender,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        if used_tools:
            message["usedTools"] = used_tools
        self.messages.append(message) 