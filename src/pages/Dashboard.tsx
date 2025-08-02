import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import BarChart from '../components/BarChart';
import LoginForm from '../components/LoginForm';
import RegisterForm from '../components/RegisterForm';
import SignupPopup from '../components/SignupPopup';
import { useUser } from '../components/UserContext';
import { API_URL } from '../env_vars';
import { useSignupPopup } from '../hooks/useSignupPopup';
import apiService from '../services/api';
import authService from '../services/auth';
import logger from '../services/logging';

const Panel1 = () => {
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    fetch(`${API_URL}/time`, {
      headers: {
        'Access-Control-Allow-Origin': 'http://127.0.0.1:3010',
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    })
      .then(res => res.json())
      .then(data => {
        setCurrentTime(data.time);
      });
  }, []);

  return (
    <header className="App-header">
      <p>The current time is {currentTime}.</p>
      <p>
        <Link to="patients">Patients</Link>
      </p>
      <p>
        <Link to="about">About</Link>
      </p>
      <p>
        <Link to="contact">Contact</Link>
      </p>
      <button className="sidebar-toggle-button">Toggle Sidebar</button>
      <button className="profile-button">Profile</button>
    </header>
  );
};

const DashboardOld = () => {
  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      <div className="cards-grid">
        <div className="card">
          <Panel1 />
        </div>
        <div className="card">
          <BarChart />
        </div>
        <div className="card">Panel 3</div>
        <div className="card">Panel 4</div>
      </div>
    </div>
  );
};

const dashboardData = {
  totalPatients: '1,083',
  totalIncome: '723.43',
  appointments: '324',
  reports: '1,083',
};

const AuthenticatedDashboard = ({
  user,
  onLogout,
}: {
  user: any;
  onLogout: () => void;
}): JSX.Element => {
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <h1>Dashboard</h1>
          <p>Welcome back, {user.first_name || user.username}!</p>
        </div>
        <div className="user-info">
          <span className="user-role">{user.role}</span>
          <button onClick={onLogout} className="logout-button">
            Logout
          </button>
        </div>
      </div>
      <div className="dashboard-grid">
        <div className="card stats-card">
          <div className="card-title">Total Patients</div>
          <h2>{dashboardData.totalPatients}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Total Income</div>
          <h2>${dashboardData.totalIncome}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Appointments</div>
          <h2>{dashboardData.appointments}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Reports</div>
          <h2>{dashboardData.reports}</h2>
          <p>+2.7%</p>
        </div>

        <div className="card appointments-card">
          <div className="card-title">Appointments</div>
          {/* This would be a list rendered from data */}
        </div>

        <div className="card activity-card">
          <div className="card-title">Recent Activity</div>
          {/* This would be a list rendered from data */}
        </div>
      </div>
    </div>
  );
};

const PublicDashboard = ({
  showSignupPopup,
}: {
  showSignupPopup: () => void;
}) => {
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-title">
          <h1>Dashboard</h1>
          <p>Welcome to ArsMedicaTech - Your Healthcare Management Solution</p>
        </div>
        <div className="user-info">
          <span className="user-role">Guest</span>
          <button onClick={showSignupPopup} className="signup-button">
            Sign Up
          </button>
        </div>
      </div>
      <div className="dashboard-grid">
        <div className="card stats-card">
          <div className="card-title">Total Patients</div>
          <h2>{dashboardData.totalPatients}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Total Income</div>
          <h2>${dashboardData.totalIncome}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Appointments</div>
          <h2>{dashboardData.appointments}</h2>
          <p>+2.7%</p>
        </div>
        <div className="card stats-card">
          <div className="card-title">Reports</div>
          <h2>{dashboardData.reports}</h2>
          <p>+2.7%</p>
        </div>

        <div className="card appointments-card">
          <div className="card-title">Appointments</div>
          <div className="guest-notice">
            <p>Sign up to view and manage appointments</p>
            <button onClick={showSignupPopup} className="guest-action-button">
              Get Started
            </button>
          </div>
        </div>

        <div className="card activity-card">
          <div className="card-title">Recent Activity</div>
          <div className="guest-notice">
            <p>Sign up to view recent activity</p>
            <button onClick={showSignupPopup} className="guest-action-button">
              Get Started
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

interface UserData {
  id: number;
  username: string;
  first_name?: string;
  last_name?: string;
  email?: string;
  role: string;
}

const Dashboard = () => {
  const { user, isAuthenticated, setUser, isLoading: userLoading } = useUser();
  const [showLogin, setShowLogin] = useState(true);
  const {
    isPopupOpen,
    showSignupPopup,
    hideSignupPopup: originalHideSignupPopup,
  } = useSignupPopup();
  const [usersExist, setUsersExist] = useState<boolean | null>(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Custom hideSignupPopup that also clears auth query parameter
  const hideSignupPopup = () => {
    originalHideSignupPopup();
    // Clear auth query parameter
    const newSearchParams = new URLSearchParams(searchParams);
    newSearchParams.delete('auth');
    window.history.replaceState(null, '', `?${newSearchParams.toString()}`);
  };

  // Check for auth query parameter and automatically show the appropriate form
  useEffect(() => {
    const authParam = searchParams.get('auth');
    if (authParam === 'login' && !isAuthenticated) {
      setShowLogin(true);
      showSignupPopup();
    } else if (authParam === 'register' && !isAuthenticated) {
      setShowLogin(false);
      showSignupPopup();
    }
  }, [searchParams, isAuthenticated, showSignupPopup]);

  // Debug logging
  logger.debug('Dashboard render - user:', user);
  logger.debug('Dashboard render - isAuthenticated:', isAuthenticated);
  logger.debug('Dashboard render - userLoading:', userLoading);

  // Track authentication state changes
  useEffect(() => {
    logger.debug('Dashboard - Authentication state changed:', {
      user,
      isAuthenticated,
      userLoading,
    });
  }, [user, isAuthenticated, userLoading]);

  useEffect(() => {
    // Check if any users exist
    const checkUsersExist = async () => {
      try {
        const response = await apiService.checkUsersExist();
        setUsersExist(response.users_exist);
      } catch (error) {
        // If error (e.g. 403), assume users exist to avoid exposing admin setup
        setUsersExist(true);
      }
    };

    checkUsersExist();
  }, []);

  const handleLogin = (userData: UserData): void => {
    logger.debug('Dashboard handleLogin called with:', userData);
    const userForContext = {
      id: userData.id.toString(),
      username: userData.username,
      email: userData.email,
      first_name: userData.first_name,
      last_name: userData.last_name,
      role: userData.role,
    };
    logger.debug('Setting user in context:', userForContext);
    setUser(userForContext);
    logger.debug('User set in context successfully');

    // Close the popup after successful login
    hideSignupPopup();
    logger.debug('Signup popup closed after login');
  };

  const handleRegister = (userData: UserData): void => {
    logger.debug('Dashboard handleRegister called with:', userData);
    const userForContext = {
      id: userData.id.toString(),
      username: userData.username,
      email: userData.email,
      first_name: userData.first_name,
      last_name: userData.last_name,
      role: userData.role,
    };
    logger.debug('Setting user in context:', userForContext);
    setUser(userForContext);
    logger.debug('User set in context successfully');

    // Close the popup after successful registration
    hideSignupPopup();
    logger.debug('Signup popup closed after registration');

    // Redirect admin to organization creation page
    if (userForContext.role === 'admin') {
      navigate('/organization');
    }
  };

  const handleLogout = async () => {
    logger.debug('Dashboard handleLogout called');
    await authService.logout();
    setUser(null);
    logger.debug('User cleared from context');
    window.location.href = '/';
  };

  const handleSetupAdmin = async () => {
    const result = await authService.setupDefaultAdmin();
    if (result.success) {
      alert('Default admin user created! Username: admin, Password: Admin123!');
    } else {
      alert('Error creating admin user: ' + result.error);
    }
  };

  if (userLoading) {
    logger.debug('Dashboard - showing loading state');
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    );
  }

  if (isAuthenticated && user) {
    logger.debug('Dashboard - showing authenticated dashboard');
    return (
      <>
        <AuthenticatedDashboard user={user} onLogout={handleLogout} />
        <SignupPopup isOpen={isPopupOpen} onClose={hideSignupPopup} />
      </>
    );
  }

  logger.debug('Dashboard - showing public dashboard');
  logger.debug('Dashboard - popup state:', { isPopupOpen, showLogin });
  return (
    <>
      <PublicDashboard showSignupPopup={showSignupPopup} />
      <SignupPopup isOpen={isPopupOpen} onClose={hideSignupPopup} />

      {/* Show auth forms when popup is triggered */}
      {isPopupOpen && (
        <div className="auth-overlay">
          <div className="auth-container">
            {showLogin ? (
              <LoginForm
                onLogin={handleLogin}
                onSwitchToRegister={() => setShowLogin(false)}
                onClose={hideSignupPopup}
              />
            ) : (
              <RegisterForm
                onRegister={handleRegister}
                onSwitchToLogin={() => setShowLogin(true)}
                onClose={hideSignupPopup}
              />
            )}

            {/* Admin setup button - only show if no users exist */}
            {usersExist === false && (
              <div className="admin-setup">
                <button
                  onClick={handleSetupAdmin}
                  className="setup-admin-button"
                >
                  Setup Default Admin
                </button>
                <p className="setup-note">
                  Use this to create the first admin user if no users exist in
                  the system.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};

export default Dashboard;
