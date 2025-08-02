"""
LLM Chat Service
"""
from typing import List, Optional

from lib.data_types import UserID
from lib.db.surreal import DbController
from lib.models.llm_chat import LLMChat
from settings import logger


class LLMChatService:
    """
    Service for managing LLM chats, including creating, retrieving, and updating chats.
    """
    def __init__(self, db_controller: Optional[DbController] = None) -> None:
        """
        Initialize the LLMChatService with a database controller.
        :param db_controller: Optional[DbController] - The database controller to use. If None, a new DbController instance is created.
        :return: None
        """
        self.db = db_controller or DbController()

    def connect(self) -> None:
        """
        Connect to the database.
        :return: None
        """
        try:
            self.db.connect()
        except Exception as e:
            logger.error(f"Error connecting to the database: {e}")
            raise

    def close(self) -> None:
        """
        Close the database connection.
        :return: None
        """
        self.db.close()

    def get_llm_chats_for_user(self, user_id: UserID) -> List[LLMChat]:
        """
        Get all LLM chats for a user

        :param user_id: UserID - The ID of the user for whom to retrieve chats.
        :return: List[LLMChat] - A list of LLMChat objects for the specified user.
        """
        result = self.db.query(
            "SELECT * FROM LLMChat WHERE user_id = $user_id",
            {"user_id": user_id}
        )
        chats = []
        if result and isinstance(result, list):
            for chat_data in result:
                if isinstance(chat_data, dict):
                    chats.append(LLMChat.from_dict(chat_data))
        return chats

    def get_llm_chat(self, user_id: UserID, assistant_id: str) -> Optional[LLMChat]:
        """
        Get a specific LLM chat for a user and assistant

        :param user_id: UserID - The ID of the user.
        :param assistant_id: str - The ID of the assistant.
        :return: Optional[LLMChat] - The LLMChat object if found, otherwise None.
        """
        result = self.db.query(
            "SELECT * FROM LLMChat WHERE user_id = $user_id AND assistant_id = $assistant_id",
            {"user_id": user_id, "assistant_id": assistant_id}
        )
        if result and isinstance(result, list) and len(result) > 0:
            return LLMChat.from_dict(result[0])
        return None

    def create_llm_chat(self, user_id: UserID, assistant_id: str) -> LLMChat:
        """
        Create a new LLM chat for a user and assistant

        :param user_id: UserID - The ID of the user.
        :param assistant_id: str - The ID of the assistant.
        :return: LLMChat - The newly created LLMChat object.
        """
        chat = LLMChat(user_id=user_id, assistant_id=assistant_id)
        result = self.db.create('LLMChat', chat.to_dict())
        if result and isinstance(result, dict):
            chat.id = result.get('id')
        return chat

    def add_message(self, user_id: UserID, assistant_id: str, sender: str, text: str, used_tools: Optional[List[str]] = None) -> LLMChat:
        """
        Add a message to the LLM chat, creating the chat if needed

        :param user_id: UserID - The ID of the user.
        :param assistant_id: str - The ID of the assistant.
        :param sender: str - The sender of the message (e.g., 'user' or 'assistant').
        :param text: str - The content of the message.
        :param used_tools: Optional list of tools used in this message.
        :return: LLMChat - The updated LLMChat object with the new message added.
        """
        chat = self.get_llm_chat(user_id, assistant_id)
        if not chat:
            chat = self.create_llm_chat(user_id, assistant_id)
        chat.add_message(sender, text, used_tools)
        # Save updated chat
        chat_id: str = chat.id or ""
        if not chat_id:
            raise ValueError("Chat ID is not set")
        
        self.db.update(f"LLMChat:{chat_id.split(':', 1)[1]}", chat.to_dict())
        return chat 