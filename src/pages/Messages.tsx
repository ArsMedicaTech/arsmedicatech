import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ErrorModal from '../components/ErrorModal';
import NewConversationModal from '../components/NewConversationModal';
import { useNotificationContext } from '../components/NotificationContext';
import NotificationTest from '../components/NotificationTest';
import SignupPopup from '../components/SignupPopup';
import ToolUsageModal from '../components/ToolUsageModal';
import { DEBUG } from '../env_vars';
import { useChat } from '../hooks/useChat';
import useEvents from '../hooks/useEvents';
import { useNewConversationModal } from '../hooks/useNewConversationModal';
import { useSignupPopup } from '../hooks/useSignupPopup';
import apiService from '../services/api';
import authService from '../services/auth';
import logger from '../services/logging';
import './Messages.css';

function truncateLastMsg(lastMessage: string, maxLength = 30): string {
  if (lastMessage.length <= maxLength) return lastMessage;
  return lastMessage.slice(0, maxLength) + '...';
}

const Messages = () => {
  logger.debug('Messages component rendering');

  const [isAuthChecking, setIsAuthChecking] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [toolUsageModal, setToolUsageModal] = useState({
    isOpen: false,
    usedTools: [] as string[],
  });

  // Error modal state
  const [errorModal, setErrorModal] = useState({
    isOpen: false,
    error: '',
    description: '',
    suggested_action: '' as string | undefined,
  });

  // Check authentication status
  useEffect(() => {
    const checkAuth = () => {
      const authStatus = authService.isAuthenticated();
      setIsAuthenticated(authStatus);
      setIsAuthChecking(false);
    };
    checkAuth();
  }, []);

  const handleShowError = (errorState: {
    isOpen: boolean;
    error: string;
    description: string;
    suggested_action: string | undefined;
  }) => {
    setErrorModal(errorState);
  };

  const handleCloseErrorModal = () => {
    setErrorModal(prev => ({ ...prev, isOpen: false }));
  };
  const { isPopupOpen, showSignupPopup, hideSignupPopup } = useSignupPopup();
  const { isModalOpen, showModal, hideModal } = useNewConversationModal();
  const [selectedMessages, setSelectedMessages] = useState<
    { sender: string; text: string; usedTools?: string[] }[]
  >([]);

  logger.debug('Messages: isAuthenticated:', isAuthenticated);

  // Initialize notification system
  const {
    notifications,
    unreadCount,
    addNotification,
    markAsRead,
    markAllAsRead,
    clearNotification,
    clearAllNotifications,
    getRecentNotifications,
  } = useNotificationContext();

  const {
    conversations,
    setConversations,
    selectedConversationId,
    handleSelectConversation,
    newMessage,
    setNewMessage,
    handleSend,
    createNewConversation,
    clearConversations,
    addTestConversation,
    isLoading,
  } = useChat(false); // Default to regular chat, will be overridden per conversation

  // Memoize selectedConversation to prevent unnecessary re-renders
  const selectedConversation = useMemo(() => {
    return conversations.find(conv => conv.id === selectedConversationId);
  }, [conversations, selectedConversationId]);

  // Handle real-time notifications
  const handleNewMessage = useCallback(
    (data: any) => {
      logger.debug('Received new message notification:', data);

      // Add notification for new message
      const notification = {
        type: 'new_message' as const,
        title: 'New Message',
        message: data.text,
        timestamp: data.timestamp,
        data: {
          sender: data.sender,
          conversation_id: data.conversation_id,
        },
      };

      logger.debug('Adding notification:', notification);
      addNotification(notification);
      logger.debug('Notification added successfully');

      // Update conversation list with new message
      setConversations(prevConversations =>
        prevConversations.map(conv => {
          if (conv.id.toString() === data.conversation_id) {
            return {
              ...conv,
              lastMessage: data.text,
            };
          }
          return conv;
        })
      );

      // If this conversation is currently selected, refresh messages
      if (selectedConversationId?.toString() === data.conversation_id) {
        // Only refresh messages for real conversations (string IDs)
        if (typeof selectedConversationId === 'string') {
          const fetchMessages = async () => {
            try {
              const response = await apiService.getConversationMessages(
                selectedConversationId.toString()
              );
              const fetchedMessages = (response.messages || []).map(
                (msg: any) => ({
                  sender: msg.sender,
                  text: msg.text,
                })
              );

              // Update both selectedMessages and conversations state
              setSelectedMessages(fetchedMessages);

              // Update the conversation in the conversations state with the fetched messages
              setConversations(prevConversations =>
                prevConversations.map(conv => {
                  if (conv.id === selectedConversationId) {
                    return {
                      ...conv,
                      messages: fetchedMessages,
                    };
                  }
                  return conv;
                })
              );
            } catch (error) {
              console.error('Error refreshing messages:', error);
            }
          };
          fetchMessages();
        }
      }
    },
    [selectedConversationId, setConversations, addNotification]
  );

  const handleAppointmentReminder = useCallback(
    (data: any) => {
      logger.debug('Received appointment reminder:', data);

      // Add notification for appointment reminder
      addNotification({
        type: 'appointment_reminder',
        title: 'Appointment Reminder',
        message: data.content,
        timestamp: data.timestamp,
        data: {
          appointmentId: data.appointmentId,
          time: data.time,
        },
      });
    },
    [addNotification]
  );

  const handleSystemNotification = useCallback(
    (data: any) => {
      logger.debug('Received system notification:', data);

      // Add notification for system notification
      addNotification({
        type: 'system_notification',
        title: 'System Notification',
        message: data.content,
        timestamp: data.timestamp,
        data: data,
      });
    },
    [addNotification]
  );

  // Initialize SSE connection
  logger.debug('Messages: Setting up SSE connection with callbacks');
  useEvents({
    onNewMessage: handleNewMessage,
    onAppointmentReminder: handleAppointmentReminder,
    onSystemNotification: handleSystemNotification,
  });
  logger.debug('Messages: SSE connection setup complete');

  // Fetch messages when a conversation is selected
  useEffect(() => {
    let isMounted = true;

    const fetchMessages = async () => {
      if (!selectedConversationId || !selectedConversation) return;

      // Check if this is a dummy conversation (has numeric ID and messages already loaded)
      const isDummyConversation =
        typeof selectedConversationId === 'number' &&
        selectedConversation.messages &&
        selectedConversation.messages.length > 0;

      if (isDummyConversation) {
        // For dummy conversations, use the pre-loaded messages
        if (isMounted) {
          setSelectedMessages(selectedConversation.messages);
        }
        return;
      }

      if (selectedConversation.isAI) {
        // For AI assistant, fetch from LLM chat history endpoint
        try {
          const assistantId =
            selectedConversation.participantId || 'ai-assistant';
          const response = await apiService.getLLMChatHistory(assistantId);
          const fetchedMessages = response.messages || [];

          if (isMounted) {
            // Process messages to include tool usage information
            const processedMessages = fetchedMessages.map((msg: any) => ({
              sender: msg.sender,
              text: msg.text,
              usedTools: msg.usedTools || [],
            }));

            // Update both selectedMessages and conversations state
            setSelectedMessages(processedMessages);

            // Update the conversation in the conversations state with the fetched messages
            setConversations(prevConversations =>
              prevConversations.map(conv => {
                if (conv.id === selectedConversationId) {
                  return {
                    ...conv,
                    messages: processedMessages,
                  };
                }
                return conv;
              })
            );
          }
        } catch (error) {
          console.error('Error fetching LLM messages:', error);
          if (isMounted) {
            setSelectedMessages([]);
          }
        }
        return;
      }

      // Only fetch from database for real conversations (string IDs)
      if (typeof selectedConversationId === 'string') {
        // Check if this conversation has messages already loaded (like test conversations)
        if (
          selectedConversation.messages &&
          selectedConversation.messages.length > 0
        ) {
          // Use the messages that are already in the conversation object
          if (isMounted) {
            setSelectedMessages(selectedConversation.messages);
          }
          return;
        }

        try {
          const response = await apiService.getConversationMessages(
            selectedConversationId.toString()
          );
          // The backend returns { messages: [...] }
          const fetchedMessages = (response.messages || []).map((msg: any) => ({
            sender: msg.sender,
            text: msg.text,
          }));

          if (isMounted) {
            // Update both selectedMessages and conversations state
            setSelectedMessages(fetchedMessages);

            // Update the conversation in the conversations state with the fetched messages
            setConversations(prevConversations =>
              prevConversations.map(conv => {
                if (conv.id === selectedConversationId) {
                  return {
                    ...conv,
                    messages: fetchedMessages,
                  };
                }
                return conv;
              })
            );
          }
        } catch (error) {
          console.error('Error fetching messages:', error);
          if (isMounted) {
            setSelectedMessages([]);
          }
        }
      } else {
        // For other cases, set empty messages
        if (isMounted) {
          setSelectedMessages([]);
        }
      }
    };

    fetchMessages();

    // Cleanup function to prevent memory leaks
    return () => {
      isMounted = false;
    };
  }, [selectedConversationId]); // Only depend on selectedConversationId to prevent circular dependencies

  const handleSendMessage = async () => {
    if (!isAuthenticated) {
      showSignupPopup();
      return;
    }

    if (!newMessage.trim()) return;

    setIsSendingMessage(true);

    try {
      // Check if this is an AI conversation or user-to-user conversation
      if (selectedConversation?.isAI) {
        // Use LLM chat for AI conversations
        const assistantId =
          selectedConversation.participantId || 'ai-assistant';

        logger.debug('Sending LLM message:', {
          assistantId,
          prompt: newMessage,
        });

        // Send message to LLM endpoint
        const sendResponse = await apiService.sendLLMMessage(
          assistantId,
          newMessage
        );
        logger.debug('LLM send response:', sendResponse);

        // Fetch updated LLM chat history for this assistant
        const response = await apiService.getLLMChatHistory(assistantId);
        const fetchedMessages = response.messages || [];
        logger.debug('Fetched LLM messages:', fetchedMessages);

        // Process messages to include tool usage information
        const processedMessages = fetchedMessages.map((msg: any) => ({
          sender: msg.sender,
          text: msg.text,
          usedTools: msg.usedTools || [],
        }));

        // Update both selectedMessages and conversations state
        setSelectedMessages(processedMessages);

        // Update the conversation in the conversations state with the fetched messages
        setConversations(prevConversations =>
          prevConversations.map(conv => {
            if (conv.id === selectedConversationId) {
              return {
                ...conv,
                messages: processedMessages,
              };
            }
            return conv;
          })
        );
      } else {
        // Use regular chat for user-to-user conversations
        await handleSendUserMessage();
      }

      // Clear the input after successful send
      setNewMessage('');
    } catch (error) {
      console.error('Error sending message:', error);

      // Show user-friendly error message
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to send message';
      alert(`Error: ${errorMessage}`);

      // Don't clear the message input so user can try again
    } finally {
      setIsSendingMessage(false);
    }
  };

  const handleSendUserMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    const messageText = newMessage;

    logger.debug(
      '[DEBUG] Sending user message to conversation:',
      selectedConversation.id
    );
    logger.debug('Selected conversation:', selectedConversation);

    // Add message locally first for immediate feedback
    const updatedConversations = conversations.map(conv => {
      if (conv.id === selectedConversationId) {
        return {
          ...conv,
          messages: [...conv.messages, { sender: 'Me', text: messageText }],
          lastMessage: messageText,
        };
      }
      return conv;
    });

    // Update conversations state immediately for UI feedback
    // We need to update the conversations state since useChat doesn't handle user-to-user messages
    setConversations(updatedConversations);

    // Only send message to backend for real conversations (string IDs)
    if (typeof selectedConversation.id === 'string') {
      try {
        await apiService.sendMessage(
          selectedConversation.id.toString(),
          messageText
        );
        logger.debug(
          'Message sent successfully to conversation:',
          selectedConversation.id
        );
      } catch (error) {
        console.error('Error sending message:', error);
        // In a real app, you might want to show an error message to the user
        // and potentially revert the local state change
      }
    } else {
      logger.debug(
        'Message added locally for dummy conversation:',
        selectedConversation.id
      );
    }
  };

  const handleStartChatbot = () => {
    // Create AI Assistant conversation with unique ID
    createNewConversation(
      `ai-assistant-${Date.now()}`,
      'AI Assistant',
      'https://ui-avatars.com/api/?name=AI&background=random',
      true
    );
  };

  const handleStartUserChat = async (
    userId: string,
    userInfo?: { display_name: string; avatar: string }
  ) => {
    logger.debug('Starting user chat with:', { userId, userInfo });
    try {
      // Create conversation in database
      logger.debug('Creating conversation in database...');
      const response = await apiService.createConversation(
        [userId],
        'user_to_user'
      );
      logger.debug('Conversation creation response:', response);

      if (response.conversation_id) {
        logger.debug(
          '[DEBUG] Creating conversation in frontend with ID:',
          response.conversation_id
        );
        // Create conversation in frontend with the database ID
        createNewConversation(
          response.conversation_id,
          userInfo?.display_name || 'Unknown User',
          userInfo?.avatar ||
            'https://ui-avatars.com/api/?name=User&background=random',
          false
        );
      } else {
        console.error('Failed to create conversation:', response);
      }
    } catch (error) {
      console.error('Error creating conversation:', error);
      // Fallback: create conversation locally
      logger.debug('Falling back to local conversation creation');
      createNewConversation(
        userId,
        userInfo?.display_name || 'Unknown User',
        userInfo?.avatar ||
          'https://ui-avatars.com/api/?name=User&background=random',
        false
      );
    }
  };

  const handleNewConversation = () => {
    if (!isAuthenticated) {
      showSignupPopup();
      return;
    }
    showModal();
  };

  return (
    <>
      {isAuthChecking ? (
        <div className="auth-required-container">
          <div className="auth-required-content">
            <div className="auth-required-icon">⏳</div>
            <h2>Loading...</h2>
            <p>Checking authentication status...</p>
          </div>
        </div>
      ) : !isAuthenticated ? (
        <div className="auth-required-container">
          <div className="auth-required-content">
            <div className="auth-required-icon">🔐</div>
            <h2>Sign In Required</h2>
            <p>
              You need to be signed in to access messages and start
              conversations.
            </p>
            <button className="auth-required-button" onClick={showSignupPopup}>
              Sign In / Sign Up
            </button>
          </div>
        </div>
      ) : (
        <div className="messages-container">
          {/* Left sidebar: conversation list */}
          <div className="conversations-list">
            <div className="conversation-list-header">
              <h3 className="conversation-list-title">Conversations</h3>
              <div className="conversation-header-buttons">
                <button
                  className="new-conversation-button"
                  onClick={handleNewConversation}
                  title="Start new conversation"
                >
                  <span className="button-icon">+</span>
                </button>
                {DEBUG && (
                  <>
                    <button
                      className="debug-button"
                      onClick={clearConversations}
                      style={{ marginLeft: '10px', fontSize: '12px' }}
                      title="Clear all conversations (debug)"
                    >
                      Clear
                    </button>
                    <button
                      className="debug-button"
                      onClick={addTestConversation}
                      style={{
                        marginLeft: '5px',
                        fontSize: '12px',
                        backgroundColor: '#28a745',
                        borderColor: '#28a745',
                      }}
                      title="Add test conversation (debug)"
                    >
                      Test
                    </button>
                  </>
                )}
              </div>
            </div>
            <ul>
              {conversations.length > 0 ? (
                conversations.map(conv => (
                  <li
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={
                      conv.id === selectedConversationId
                        ? 'conversation active'
                        : 'conversation'
                    }
                  >
                    <img className="avatar" src={conv.avatar} alt={conv.name} />
                    <div className="conversation-info">
                      <p className="conversation-name">{conv.name}</p>
                      <p className="conversation-last">
                        {truncateLastMsg(conv.lastMessage)}
                      </p>
                    </div>
                  </li>
                ))
              ) : (
                <li className="no-conversations">
                  <p>
                    No conversations yet. Start a new conversation to begin
                    messaging!
                  </p>
                </li>
              )}
            </ul>
          </div>

          {/* Right side: chat window */}
          <div className="chat-window">
            {selectedConversation ? (
              <>
                <div className="chat-header">
                  <h3>{selectedConversation.name}</h3>
                </div>
                <div className="messages-list">
                  {selectedMessages.map((msg, index) => (
                    <div
                      key={index}
                      className={msg.sender === 'Me' ? 'message me' : 'message'}
                    >
                      <div className="message-sender">
                        {msg.sender}
                        {msg.sender === 'AI Assistant' &&
                          msg.usedTools &&
                          msg.usedTools.length > 0 && (
                            <button
                              className="tool-debug-button"
                              onClick={() =>
                                setToolUsageModal({
                                  isOpen: true,
                                  usedTools: msg.usedTools || [],
                                })
                              }
                              title="View tools used"
                            >
                              🔧
                            </button>
                          )}
                      </div>
                      <div className="message-text">
                        <ReactMarkdown>{msg.text}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="message">
                      <div className="message-sender">AI Assistant</div>
                      <div className="message-text">
                        <div className="loading-indicator">Thinking...</div>
                      </div>
                    </div>
                  )}
                  {isSendingMessage && (
                    <div className="message-sending-indicator">
                      <div className="loading-spinner"></div>
                      <span>Sending message...</span>
                    </div>
                  )}
                </div>
                <div className="message-input-container">
                  <input
                    type="text"
                    placeholder="Type a message..."
                    value={newMessage}
                    onChange={e => setNewMessage(e.target.value)}
                    onKeyPress={e => {
                      if (e.key === 'Enter' && !isSendingMessage) {
                        handleSendMessage();
                      }
                    }}
                    disabled={isSendingMessage}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={isSendingMessage || !newMessage.trim()}
                  >
                    {isSendingMessage ? 'Sending...' : 'Send'}
                  </button>
                </div>
              </>
            ) : (
              <div className="no-conversation-selected">
                <p>Select a conversation to start messaging</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SSE Notification Test Component */}
      {DEBUG && <NotificationTest />}

      <SignupPopup isOpen={isPopupOpen} onClose={hideSignupPopup} />
      <NewConversationModal
        isOpen={isModalOpen}
        onClose={hideModal}
        onStartChatbot={handleStartChatbot}
        onStartUserChat={handleStartUserChat}
        onShowError={handleShowError}
      />
      <ErrorModal
        isOpen={errorModal.isOpen}
        error={errorModal.error}
        description={errorModal.description}
        suggested_action={errorModal.suggested_action}
        onClose={handleCloseErrorModal}
      />
      <ToolUsageModal
        isOpen={toolUsageModal.isOpen}
        usedTools={toolUsageModal.usedTools}
        onClose={() => setToolUsageModal({ isOpen: false, usedTools: [] })}
      />
    </>
  );
};

export default Messages;
