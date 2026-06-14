import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import LoadingState from './LoadingState';

interface ProtectedRouteProps {
  children: React.ReactNode;
  roles?: string[]; // empty or undefined = any authenticated user
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, roles }) => {
  const { isAuthenticated, fetchUser, hasRole } = useAuthStore();
  const token = localStorage.getItem('access_token');
  // Start checking if there is a token (not based on store's optimistic state)
  const [checking, setChecking] = useState(!!token);
  const location = useLocation();

  useEffect(() => {
    if (token) {
      // Always verify token against server, regardless of current store state
      fetchUser().finally(() => setChecking(false));
    } else {
      setChecking(false);
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (checking) {
    return <LoadingState tip="验证身份中..." fullPage />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (roles && roles.length > 0 && !hasRole(roles)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
