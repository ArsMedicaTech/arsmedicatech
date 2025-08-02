import { useState } from 'react';
import { createErrorModalState } from '../components/ErrorModal';

interface ErrorModalState {
  isOpen: boolean;
  error: string;
  description: string;
  suggested_action?: string;
}

export const useErrorModal = () => {
  const [errorModal, setErrorModal] = useState<ErrorModalState>({
    isOpen: false,
    error: 'Something went wrong',
    description:
      'An unknown error has occurred. Please return to the home screen. The error has been logged and is being investigated.',
  });

  const showError = (
    error: string,
    description: string,
    suggested_action?: string
  ) => {
    setErrorModal(createErrorModalState(error, description, suggested_action));
  };

  const hideError = () => {
    setErrorModal(prev => ({ ...prev, isOpen: false }));
  };

  const showNetworkError = () => {
    showError(
      'Network Error',
      'Unable to connect to the server. Please check your internet connection and try again.',
      'home'
    );
  };

  const showAuthError = (description: string) => {
    showError('Authentication Error', description, 'login');
  };

  const showPermissionError = () => {
    showError(
      'Permission Denied',
      'You do not have permission to perform this action. Please contact your administrator if you believe this is an error.',
      'home'
    );
  };

  return {
    errorModal,
    showError,
    hideError,
    showNetworkError,
    showAuthError,
    showPermissionError,
  };
};
