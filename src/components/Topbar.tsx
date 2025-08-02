import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline';
import { Notification } from '../hooks/useNotifications';
import { useSignupPopup } from '../hooks/useSignupPopup';
import authService from '../services/auth';
import NotificationIndicator from './NotificationIndicator';
import SignupPopup from './SignupPopup';
import './Topbar.css';
import { useUser } from './UserContext';

interface Props {
  // Notification props
  unreadCount: number;
  recentNotifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onMarkAllAsRead: () => void;
  onClearNotification: (id: string) => void;
  onClearAll: () => void;
}

export default function Topbar(props: Props) {
  const { user, isAuthenticated, setUser } = useUser();
  const { isPopupOpen, showSignupPopup, hideSignupPopup } = useSignupPopup();

  const handleLogout = async () => {
    try {
      await authService.logout();
      setUser(null);
      window.location.href = '/';
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <>
      <header className="topbar">
        <div className="topbar-actions">
          {/* Notification Indicator */}
          {isAuthenticated && (
            <NotificationIndicator
              unreadCount={props.unreadCount}
              recentNotifications={props.recentNotifications}
              onMarkAsRead={props.onMarkAsRead}
              onMarkAllAsRead={props.onMarkAllAsRead}
              onClearNotification={props.onClearNotification}
              onClearAll={props.onClearAll}
            />
          )}

          <div className="auth-status">
            {isAuthenticated && user ? (
              <div className="profile-container">
                <span className="user-name">
                  {`${user.first_name || ''} ${user.last_name || ''}`.trim() ||
                    user.username}
                </span>
                <span className="user-role">{user.role}</span>
                <button onClick={handleLogout} className="logout-button">
                  <ArrowRightOnRectangleIcon className="logout-icon" />
                  Logout
                </button>
              </div>
            ) : (
              <div className="guest-auth">
                <span className="guest-label">Guest User</span>
                <button onClick={showSignupPopup} className="auth-button">
                  Sign Up / Login
                </button>
              </div>
            )}
          </div>
        </div>
        <div className="release-info">Version 0.0.1 (alpha)</div>
      </header>
      <SignupPopup isOpen={isPopupOpen} onClose={hideSignupPopup} />
    </>
  );
}
