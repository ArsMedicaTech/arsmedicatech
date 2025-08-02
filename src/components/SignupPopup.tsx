import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/auth';
import GoogleAuthButton from './GoogleAuthButton';
import RoleSelect from './RoleSelect';
import './SignupPopup.css';

interface SignupPopupProps {
  isOpen: boolean;
  onClose: () => void;
  onSwitchToLogin?: () => void;
}

const SignupPopup = ({
  isOpen,
  onClose,
  onSwitchToLogin,
}: SignupPopupProps): JSX.Element | null => {
  const navigate = useNavigate();
  const [role, setRole] = useState('patient');

  if (!isOpen) return null;

  const handleSignupClick = () => {
    onClose();
    navigate('/?auth=register');
  };

  const handleLoginClick = () => {
    onClose();
    navigate('/?auth=login');
  };

  const handleRoleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setRole(e.target.value);
  };

  const handleGoogleSignup = () => {
    const url = authService.getFederatedSignInUrl(role, 'signup');
    window.location.assign(url);
  };

  return (
    <div className="signup-popup-overlay" onClick={onClose}>
      <div className="signup-popup" onClick={e => e.stopPropagation()}>
        <button className="popup-close-button" onClick={onClose}>
          ×
        </button>

        <div className="popup-content">
          <div className="popup-icon">🔒</div>

          <h2>Sign Up to Continue</h2>

          <p className="popup-description">
            You need to create an account to perform this action. Sign up now to
            unlock all features and start managing your patients.
          </p>

          <div className="popup-benefits">
            <div className="benefit-item">
              <span className="benefit-icon">✓</span>
              <span>Create and manage patient records</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">✓</span>
              <span>Send and receive messages</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">✓</span>
              <span>Schedule appointments</span>
            </div>
            <div className="benefit-item">
              <span className="benefit-icon">✓</span>
              <span>Access advanced features</span>
            </div>
          </div>

          <div className="popup-actions">
            <RoleSelect value={role} onChange={handleRoleChange} />
            <GoogleAuthButton onClick={handleGoogleSignup}>
              Sign up with Google
            </GoogleAuthButton>
            <button className="popup-signup-button" onClick={handleSignupClick}>
              Sign Up Now
            </button>

            <div className="popup-login-link">
              Already have an account?{' '}
              <button className="popup-login-button" onClick={handleLoginClick}>
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPopup;
