import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useSignupPopup } from '../hooks/useSignupPopup';
import './ErrorModal.css';

interface ErrorModalProps {
  error?: string;
  description?: string;
  suggested_action?: string;
  isOpen: boolean;
  onClose: () => void;
}

// Utility function to create error modal state
export const createErrorModalState = (
  error: string,
  description: string,
  suggested_action?: string
) => ({
  isOpen: true,
  error,
  description,
  suggested_action,
});

const ErrorModal: React.FC<ErrorModalProps> = ({
  error = 'Something went wrong',
  description = 'An unknown error has occurred. Please return to the home screen. The error has been logged and is being investigated.',
  suggested_action,
  isOpen,
  onClose,
}) => {
  const navigate = useNavigate();
  const { showSignupPopup } = useSignupPopup();

  if (!isOpen) return null;

  const handleSuggestedAction = () => {
    onClose();

    switch (suggested_action) {
      case 'login':
        showSignupPopup();
        // Set the auth parameter to show login form
        window.history.replaceState(null, '', '/?auth=login');
        break;
      case 'register':
        showSignupPopup();
        // Set the auth parameter to show register form
        window.history.replaceState(null, '', '/?auth=register');
        break;
      case 'home':
      default:
        navigate('/');
        break;
    }
  };

  const getActionButtonText = () => {
    switch (suggested_action) {
      case 'login':
        return 'Login';
      case 'register':
        return 'Sign Up';
      case 'home':
      default:
        return 'Home';
    }
  };

  return (
    <div className="error-modal-overlay">
      <div className="error-modal">
        <div className="error-modal-header">
          <h3 className="error-modal-title">{error}</h3>
          <button
            className="error-modal-close"
            onClick={onClose}
            aria-label="Close error modal"
          >
            ×
          </button>
        </div>

        <div className="error-modal-body">
          <p className="error-modal-description">{description}</p>
        </div>

        <div className="error-modal-footer">
          {suggested_action && (
            <button
              onClick={handleSuggestedAction}
              className="error-modal-action-button"
            >
              {getActionButtonText()}
            </button>
          )}
          <button onClick={onClose} className="error-modal-dismiss-button">
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
};

export default ErrorModal;
