import { useState } from 'react';
import apiService from '../services/api';
import { createErrorModalState } from './ErrorModal';
import './NewConversationModal.css';

interface NewConversationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartChatbot: () => void;
  onStartUserChat: (
    userId: string,
    userInfo?: { display_name: string; avatar: string }
  ) => void;
  onShowError: (errorState: ReturnType<typeof createErrorModalState>) => void;
}

const NewConversationModal = ({
  isOpen,
  onClose,
  onStartChatbot,
  onStartUserChat,
  onShowError,
}: NewConversationModalProps): JSX.Element | null => {
  const [selectedOption, setSelectedOption] = useState<
    'chatbot' | 'user' | null
  >(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<
    Array<{
      id: string;
      name: string;
      avatar: string;
      display_name: string;
      role: string;
    }>
  >([]);
  const [isSearching, setIsSearching] = useState(false);

  if (!isOpen) return null;

  const handleOptionSelect = (option: 'chatbot' | 'user') => {
    setSelectedOption(option);
    if (option === 'chatbot') {
      setSearchResults([]);
    }
  };

  const handleSearch = async (query: string) => {
    setSearchQuery(query);

    if (query.trim().length > 2) {
      setIsSearching(true);
      try {
        const response = await apiService.searchUsers(query);
        if (response.users) {
          setSearchResults(
            response.users.map((user: any) => ({
              id: user.id,
              name: user.display_name,
              avatar: user.avatar,
              display_name: user.display_name,
              role: user.role,
            }))
          );
        }
      } catch (error) {
        console.error('Error searching users:', error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    } else {
      setSearchResults([]);
    }
  };

  const checkOpenAIAPIKey = async (): Promise<boolean> => {
    try {
      const response = await apiService.getAPI('/settings');
      if (response.success && response.settings) {
        return response.settings.has_openai_api_key === true;
      }
      return false;
    } catch (error) {
      console.error('Error checking OpenAI API key:', error);
      return false;
    }
  };

  const handleStartConversation = async () => {
    if (selectedOption === 'chatbot') {
      const hasAPIKey = await checkOpenAIAPIKey();

      if (!hasAPIKey) {
        onShowError(
          createErrorModalState(
            'OpenAI API Key Required',
            'To use the AI Assistant, you need to configure your OpenAI API key in Settings. This key is required for AI-powered features and is stored securely.',
            'settings'
          )
        );
        onClose();
        return;
      }

      onStartChatbot();
      onClose();
    }
  };

  const handleUserSelect = (user: {
    id: string;
    name: string;
    avatar: string;
    display_name: string;
    role: string;
  }) => {
    onStartUserChat(user.id, {
      display_name: user.display_name,
      avatar: user.avatar,
    });
    onClose();
  };

  const handleClose = () => {
    setSelectedOption(null);
    setSearchQuery('');
    setSearchResults([]);
    onClose();
  };

  return (
    <div className="new-conversation-modal-overlay" onClick={handleClose}>
      <div
        className="new-conversation-modal"
        onClick={e => e.stopPropagation()}
      >
        <button className="modal-close-button" onClick={handleClose}>
          ×
        </button>

        <div className="modal-content">
          <div className="modal-icon">💬</div>

          <h2>Start New Conversation</h2>

          <p className="modal-description">
            Choose how you'd like to start a new conversation
          </p>

          <div className="conversation-options">
            <div
              className={`option-card ${selectedOption === 'chatbot' ? 'selected' : ''}`}
              onClick={() => handleOptionSelect('chatbot')}
            >
              <div className="option-icon">🤖</div>
              <div className="option-content">
                <h3>AI Assistant</h3>
                <p>
                  Chat with our intelligent AI assistant for medical guidance
                  and support
                </p>
              </div>
            </div>

            <div
              className={`option-card ${selectedOption === 'user' ? 'selected' : ''}`}
              onClick={() => handleOptionSelect('user')}
            >
              <div className="option-icon">👥</div>
              <div className="option-content">
                <h3>Find User</h3>
                <p>
                  Search for and start a conversation with another healthcare
                  professional
                </p>
              </div>
            </div>
          </div>

          {selectedOption === 'user' && (
            <div className="user-search-section">
              <div className="search-container">
                <input
                  type="text"
                  placeholder="Search for users..."
                  value={searchQuery}
                  onChange={e => handleSearch(e.target.value)}
                  className="user-search-input"
                />
                {isSearching && (
                  <div className="search-loading">Searching...</div>
                )}
              </div>

              {searchResults.length > 0 && (
                <div className="search-results">
                  {searchResults.map(user => (
                    <div
                      key={user.id}
                      className="user-result"
                      onClick={() => handleUserSelect(user)}
                    >
                      <img
                        src={user.avatar}
                        alt={user.name}
                        className="user-avatar"
                      />
                      <div className="user-info">
                        <span className="user-name">{user.display_name}</span>
                        <span className="user-role">{user.role}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {searchQuery.length > 2 &&
                searchResults.length === 0 &&
                !isSearching && (
                  <div className="no-results">
                    No users found matching "{searchQuery}"
                  </div>
                )}
            </div>
          )}

          {selectedOption === 'chatbot' && (
            <div className="modal-actions">
              <button
                className="start-chatbot-button"
                onClick={handleStartConversation}
              >
                Start AI Assistant Chat
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NewConversationModal;
