import { useEffect, useState } from 'react';
import apiService from '../services/api';
import logger from '../services/logging';
import { Conversation } from '../types';

function useChat(isLLM = false) {
  // Initialize conversations from localStorage if available
  const getInitialConversations = (): Conversation[] => {
    try {
      const stored = localStorage.getItem('chat-conversations');
      const conversations = stored ? JSON.parse(stored) : [];
      logger.debug('Loaded conversations from localStorage:', conversations);
      return conversations;
    } catch (error) {
      console.error('Error loading conversations from localStorage:', error);
      return [];
    }
  };

  const [conversations, setConversations] = useState<Conversation[]>(
    getInitialConversations
  );
  // Initialize selected conversation ID from localStorage if available
  const getInitialSelectedId = (): number | string | null => {
    try {
      const stored = localStorage.getItem('chat-selected-conversation');
      if (stored) {
        const selectedId = JSON.parse(stored);
        logger.debug(
          'Loaded selected conversation ID from localStorage:',
          selectedId
        );
        return selectedId;
      }
      // If no selected conversation stored, try to get the first conversation from localStorage
      const conversationsStored = localStorage.getItem('chat-conversations');
      if (conversationsStored) {
        const conversations = JSON.parse(conversationsStored);
        const firstId = conversations[0]?.id || null;
        logger.debug('Using first conversation ID as selected:', firstId);
        return firstId;
      }
      logger.debug('No conversations found in localStorage');
      return null;
    } catch (error) {
      console.error(
        'Error loading selected conversation from localStorage:',
        error
      );
      return null;
    }
  };

  const [selectedConversationId, setSelectedConversationId] = useState<
    number | string | null
  >(getInitialSelectedId);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Debug: Log current conversations state
  useEffect(() => {
    logger.debug('Current conversations state:', conversations);
    logger.debug('Current selected conversation ID:', selectedConversationId);
  }, [conversations, selectedConversationId]);

  // Save conversations to localStorage whenever they change
  const saveConversationsToStorage = (conversations: Conversation[]) => {
    try {
      localStorage.setItem('chat-conversations', JSON.stringify(conversations));
    } catch (error) {
      console.error('Error saving conversations to localStorage:', error);
    }
  };

  // Save selected conversation ID to localStorage
  const saveSelectedConversationToStorage = (id: number | string | null) => {
    try {
      localStorage.setItem('chat-selected-conversation', JSON.stringify(id));
    } catch (error) {
      console.error(
        'Error saving selected conversation to localStorage:',
        error
      );
    }
  };

  // Fetch conversations from the server
  useEffect(() => {
    let isMounted = true;

    const fetchConversations = async () => {
      try {
        let data: any;
        let aiConversations: any[] = [];

        if (isLLM) {
          data = await apiService.getLLMChatHistory('ai-assistant');
        } else {
          // Fetch both user conversations and AI conversations
          const [userConversations, llmChats] = await Promise.all([
            apiService.getUserConversations(),
            apiService.getLLMChatHistory('ai-assistant'),
          ]);

          data = userConversations;

          // For multiple AI conversations, we don't automatically create one
          // Users will create new AI conversations as needed
          aiConversations = [];
        }

        if (!isMounted) return;

        logger.debug('Fetched conversations:', data);
        logger.debug('Fetched AI conversations:', aiConversations);

        // Transform the data to match the frontend format
        let transformedData: any[] = [];
        if (data && Array.isArray(data)) {
          transformedData = data.map((conv: any) => ({
            id: conv.id,
            name: conv.name || 'Unknown User',
            lastMessage: conv.lastMessage || 'No messages yet',
            avatar:
              conv.avatar ||
              'https://ui-avatars.com/api/?name=User&background=random',
            messages: conv.messages || [],
            isAI: conv.isAI || false,
          }));
        }

        // Combine user conversations with AI conversations
        const allConversations = [...aiConversations, ...transformedData];

        if (!isMounted) return;

        // Preserve existing messages when updating conversations
        setConversations(prevConversations => {
          logger.debug(
            'Previous conversations from localStorage:',
            prevConversations
          );
          logger.debug('New conversations from server:', allConversations);

          // If we have conversations in localStorage but server returned empty, keep the localStorage ones
          if (prevConversations.length > 0 && allConversations.length === 0) {
            logger.debug('Keeping existing conversations from localStorage');
            return prevConversations;
          }

          // Merge server conversations with localStorage conversations
          const mergedConversations = [...prevConversations];

          allConversations.forEach((newConv: any) => {
            const existingIndex = mergedConversations.findIndex(
              prev => prev.id === newConv.id
            );

            if (existingIndex >= 0) {
              // Update existing conversation but preserve messages if they exist
              const existingConv = mergedConversations[existingIndex];
              mergedConversations[existingIndex] = {
                ...newConv,
                messages:
                  existingConv.messages && existingConv.messages.length > 0
                    ? existingConv.messages
                    : newConv.messages,
              };
              logger.debug('Updated existing conversation:', newConv.id);
            } else {
              // Add new conversation from server
              mergedConversations.push(newConv);
              logger.debug('Added new conversation from server:', newConv.id);
            }
          });

          logger.debug('Final merged conversations:', mergedConversations);
          saveConversationsToStorage(mergedConversations);
          return mergedConversations;
        });

        // Only set selected conversation if none is currently selected
        setSelectedConversationId(currentId => {
          const newId =
            !currentId && allConversations.length > 0
              ? allConversations[0].id
              : currentId;
          saveSelectedConversationToStorage(newId);
          return newId;
        });
      } catch (error) {
        console.error('Error fetching conversations:', error);
        if (isMounted) {
          // Fallback to empty array if fetch fails
          saveConversationsToStorage([]);
          setConversations([]);
          saveSelectedConversationToStorage(null);
          setSelectedConversationId(null);
        }
      }
    };

    fetchConversations();

    // Cleanup function to prevent memory leaks
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLLM]); // Only depend on isLLM to prevent infinite loops

  const selectedConversation = conversations.find(
    conv => conv.id === selectedConversationId
  );

  const handleSelectConversation = (id: number | string | null): void => {
    saveSelectedConversationToStorage(id);
    setSelectedConversationId(id);
    setNewMessage('');
  };

  const createNewConversation = (
    participantId: string,
    participantName: string,
    participantAvatar: string,
    isAI: boolean = false
  ) => {
    logger.debug(
      '[DEBUG] Creating new conversation with participantId:',
      participantId
    );

    // For AI conversations, generate a unique ID using timestamp
    // For user conversations, use the participantId
    const conversationId = isAI ? `ai-assistant-${Date.now()}` : participantId;

    logger.debug('Using conversation ID:', conversationId);

    const newConversation: Conversation = {
      id: conversationId,
      name: isAI ? 'AI Assistant' : participantName,
      lastMessage: 'New conversation',
      avatar: participantAvatar,
      messages: [],
      participantId: participantId,
      isAI: isAI,
    };

    setConversations(prev => {
      const updatedConversations = [newConversation, ...prev];
      saveConversationsToStorage(updatedConversations);
      return updatedConversations;
    });
    saveSelectedConversationToStorage(newConversation.id);
    setSelectedConversationId(newConversation.id);
    setNewMessage('');
  };

  const handleSend = async () => {
    if (!newMessage.trim()) return;

    setIsLoading(true);

    try {
      if (isLLM) {
        // For LLM chat, send the message to the LLM endpoint using apiService
        // Use the selected conversation ID for AI conversations
        const conversationId =
          selectedConversationId?.toString() || 'ai-assistant';
        const llmResponse = await apiService.sendLLMMessage(
          conversationId,
          newMessage
        );
        logger.debug('LLM Response:', llmResponse);

        // Add both user message and LLM response to the conversation
        const updatedConversations = conversations.map(conv => {
          if (conv.id === selectedConversationId) {
            return {
              ...conv,
              messages: [
                ...conv.messages,
                { sender: 'Me', text: newMessage },
                {
                  sender: 'AI Assistant',
                  text:
                    llmResponse.response ||
                    llmResponse.message ||
                    'I received your message.',
                },
              ],
              lastMessage: newMessage,
            };
          }
          return conv;
        });

        saveConversationsToStorage(updatedConversations);
        setConversations(updatedConversations);
      } else {
        // For regular chat, add the message locally and send to server using apiService
        const updatedConversations = conversations.map(conv => {
          if (conv.id === selectedConversationId) {
            return {
              ...conv,
              messages: [...conv.messages, { sender: 'Me', text: newMessage }],
              lastMessage: newMessage,
            };
          }
          return conv;
        });

        saveConversationsToStorage(updatedConversations);
        setConversations(updatedConversations);

        // Save to server
        await apiService.sendChatMessage(newMessage);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      // Still add the message locally even if server call fails
      const updatedConversations = conversations.map(conv => {
        if (conv.id === selectedConversationId) {
          return {
            ...conv,
            messages: [...conv.messages, { sender: 'Me', text: newMessage }],
            lastMessage: newMessage,
          };
        }
        return conv;
      });
      saveConversationsToStorage(updatedConversations);
      setConversations(updatedConversations);
    } finally {
      setIsLoading(false);
      setNewMessage('');
    }
  };

  // Debug function to clear localStorage (for testing)
  const clearConversations = () => {
    localStorage.removeItem('chat-conversations');
    localStorage.removeItem('chat-selected-conversation');
    setConversations([]);
    setSelectedConversationId(null);
    logger.debug('Cleared all conversations from localStorage');
  };

  // Debug function to add a test conversation (for testing)
  const addTestConversation = () => {
    const testConversation: Conversation = {
      id: 'test-conversation-' + Date.now(),
      name: 'Test Conversation',
      lastMessage: 'This is a test conversation',
      avatar: 'https://ui-avatars.com/api/?name=Test&background=random',
      messages: [
        { sender: 'Test User', text: 'Hello, this is a test message' },
        { sender: 'Me', text: 'Hi there! This is a test response' },
      ],
      isAI: false,
    };

    setConversations(prev => {
      const updated = [testConversation, ...prev];
      saveConversationsToStorage(updated);
      return updated;
    });

    saveSelectedConversationToStorage(testConversation.id);
    setSelectedConversationId(testConversation.id);
    logger.debug('Added test conversation:', testConversation);
  };

  return {
    conversations,
    setConversations,
    selectedConversation,
    selectedConversationId,
    newMessage,
    setNewMessage,
    handleSelectConversation,
    handleSend,
    createNewConversation,
    clearConversations, // Export for debugging
    addTestConversation, // Export for debugging
    isLoading,
  };
}

export { useChat };
