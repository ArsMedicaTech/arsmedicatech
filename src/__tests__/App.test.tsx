import { render, screen } from '@testing-library/react';
import React from 'react';
import App from '../App';

// Mock react-joyride to silence warnings during tests
jest.mock('react-joyride', () => () => null);

// Mock the router creation to avoid conflicts
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  createBrowserRouter: (routes: any[]) => ({
    routes,
    element: routes[0].element,
  }),
  RouterProvider: ({ router }: { router: any }) => router.element,
  useNavigate: () => jest.fn(),
}));

// Mock the UserContext
jest.mock('../components/UserContext', () => ({
  UserProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="user-provider">{children}</div>
  ),
}));

// Mock the NotificationContext
jest.mock('../components/NotificationContext', () => ({
  NotificationProvider: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="notification-provider">{children}</div>
  ),
  useNotificationContext: () => ({
    unreadCount: 0,
    getRecentNotifications: () => [],
    markAsRead: jest.fn(),
    markAllAsRead: jest.fn(),
    clearNotification: jest.fn(),
    clearAllNotifications: jest.fn(),
  }),
}));

// Mock the useSignupPopup hook
jest.mock('../hooks/useSignupPopup', () => ({
  useSignupPopup: () => ({
    isPopupOpen: false,
    showSignupPopup: jest.fn(),
    hideSignupPopup: jest.fn(),
  }),
}));

// Mock components that might cause issues in tests
jest.mock('../components/Sidebar', () => {
  return function MockSidebar() {
    return <div data-testid="sidebar">Sidebar</div>;
  };
});

jest.mock('../components/Topbar', () => {
  return function MockTopbar() {
    return <div data-testid="topbar">Topbar</div>;
  };
});

jest.mock('../components/PatientTable', () => ({
  PatientTable: function MockPatientTable() {
    return <div data-testid="patient-table">Patient Table</div>;
  },
}));

jest.mock('../pages/Dashboard', () => {
  return function MockDashboard() {
    return <div data-testid="dashboard">Dashboard</div>;
  };
});

jest.mock('../pages/Messages', () => {
  return function MockMessages() {
    return <div data-testid="messages">Messages</div>;
  };
});

jest.mock('../pages/Schedule', () => {
  return function MockSchedule() {
    return <div data-testid="schedule">Schedule</div>;
  };
});

jest.mock('../components/PatientList', () => {
  return function MockPatientList() {
    return <div data-testid="patient-list">Patient List</div>;
  };
});

jest.mock('../components/PatientForm', () => {
  return function MockPatientForm() {
    return <div data-testid="patient-form">Patient Form</div>;
  };
});

jest.mock('../components/Patient', () => {
  return function MockPatient() {
    return <div data-testid="patient">Patient</div>;
  };
});

jest.mock('../components/PatientIntakeForm', () => {
  return function MockPatientIntakeForm() {
    return <div data-testid="patient-intake-form">Patient Intake Form</div>;
  };
});

jest.mock('../components/Settings', () => {
  return function MockSettings() {
    return <div data-testid="settings">Settings</div>;
  };
});

// Mock the usePatientSearch hook
jest.mock('../hooks/usePatientSearch', () => ({
  usePatientSearch: () => ({
    query: '',
    setQuery: jest.fn(),
    results: [],
    loading: false,
  }),
}));

describe('App Component', () => {
  it('renders the main app structure', () => {
    render(<App />);

    expect(screen.getByTestId('user-provider')).toBeInTheDocument();
    expect(screen.getByTestId('sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('topbar')).toBeInTheDocument();
  });

  it('renders the main content area', () => {
    render(<App />);

    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});
