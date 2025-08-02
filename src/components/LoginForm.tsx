import React, { useState } from 'react';
import authService from '../services/auth';
import logger from '../services/logging';
import GoogleAuthButton from './GoogleAuthButton';
import './LoginForm.css';

const LoginForm = ({
  onLogin,
  onSwitchToRegister,
  onClose,
}: {
  onLogin: (user: any) => void;
  onSwitchToRegister: () => void;
  onClose: () => void;
}): JSX.Element => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: 'patient',
  });
  interface Errors {
    username?: string;
    password?: string;
  }
  const [errors, setErrors] = useState<Errors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState('');

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    // Clear field-specific error when user starts typing
    if (errors[name as keyof typeof errors]) {
      setErrors(prev => ({
        ...prev,
        [name]: '',
      }));
    }
    setGeneralError('');
  };

  const validateForm = () => {
    const newErrors: Errors = {};

    if (!formData.username.trim()) {
      newErrors.username = 'Username is required';
    }

    if (!formData.password) {
      newErrors.password = 'Password is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);
    setGeneralError('');

    try {
      logger.debug('Attempting login with:', formData.username);

      const result = await authService.login(
        formData.username,
        formData.password
      );

      logger.debug('Login result:', result); // Debug log

      if (result.success) {
        // The authService.login() returns { success: true, data: { token, user } }
        // We need to pass the user object to onLogin
        const userData = result.data.user || result.data;
        logger.debug('User data to pass:', userData); // Debug log
        logger.debug('Calling onLogin with userData:', userData);
        onLogin(userData);
        logger.debug('onLogin called successfully');
      } else {
        logger.debug('Login failed:', result.error);
        setGeneralError(result.error || 'Login failed');
      }
    } catch (error) {
      console.error('Login error:', error);
      setGeneralError('An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignin = () => {
    const url = authService.getFederatedSignInUrl('patient', 'signin');
    window.location.assign(url);
  };

  return (
    <div className="login-container">
      <div className="login-form">
        {onClose && (
          <button className="form-close-button" onClick={onClose}>
            ×
          </button>
        )}
        <h2>Welcome Back</h2>
        <p className="login-subtitle">Sign in to your account</p>

        {generalError && (
          <div className="error-message general-error">{generalError}</div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className={errors.username ? 'error' : ''}
              placeholder="Enter your username"
              disabled={isLoading}
            />
            {errors.username && (
              <span className="error-message">{errors.username}</span>
            )}
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className={errors.password ? 'error' : ''}
              placeholder="Enter your password"
              disabled={isLoading}
            />
            {errors.password && (
              <span className="error-message">{errors.password}</span>
            )}
          </div>
          <GoogleAuthButton onClick={handleGoogleSignin}>
            Sign in with Google
          </GoogleAuthButton>
          <button
            type="submit"
            className="login-button"
            disabled={isLoading}
            data-testid="login-submit"
          >
            {isLoading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>

        <div className="login-footer">
          <p>
            Don't have an account?{' '}
            <button
              type="button"
              className="link-button"
              onClick={onSwitchToRegister}
            >
              Sign up
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginForm;
