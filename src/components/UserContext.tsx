import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useState,
} from 'react';
import authService from '../services/auth';
import logger from '../services/logging';

export interface User {
  id: string;
  username: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  role: string;
  max_organizations?: number;
  user_organizations?: number;
  appointments?: number; // Optional, if needed
}

interface UserContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  isAuthenticated: boolean;
  isLoading: boolean;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Debug logging for state changes
  useEffect(() => {
    logger.debug('UserContext - user state changed:', user);
    logger.debug('UserContext - isAuthenticated state changed:', !!user);
  }, [user]);

  useEffect(() => {
    const checkAuth = async () => {
      const currentUser = await authService.getCurrentUser();
      console.debug('getCurrentUser result:', currentUser);
      if (currentUser) {
        setUser(currentUser);
        setIsAuthenticated(true);
      } else {
        setUser(null);
        setIsAuthenticated(false);
      }
      setIsLoading(false);
    };
    checkAuth();
  }, []);

  const setUserWithLogging = (newUser: User | null) => {
    logger.debug('UserContext - setUser called with:', newUser);
    setUser(newUser);
    setIsAuthenticated(!!newUser);
    logger.debug('UserContext - isAuthenticated set to:', !!newUser);
  };

  return (
    <UserContext.Provider
      value={{ user, setUser: setUserWithLogging, isAuthenticated, isLoading }}
    >
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};
