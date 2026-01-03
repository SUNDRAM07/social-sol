import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { checkPlatformConnections } from '../lib/apiClient';
import { Loader2 } from 'lucide-react';

/**
 * Component that checks if user has platform integrations
 * and redirects to settings if none exist, otherwise to dashboard
 */
function FirstTimeUserRedirect() {
  const { isAuthenticated, token } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);
  const [redirectTo, setRedirectTo] = useState('/dashboard');

  useEffect(() => {
    const checkAndRedirect = async () => {
      if (!isAuthenticated || !token) {
        setRedirectTo('/login');
        setIsChecking(false);
        return;
      }

      try {
        const connections = await checkPlatformConnections();
        
        if (connections && !connections.has_connections) {
          // First-time user with no platform integrations - redirect to settings
          setRedirectTo('/settings');
        } else {
          // User has platform integrations - go to dashboard
          setRedirectTo('/dashboard');
        }
      } catch (error) {
        console.error('Error checking platform connections:', error);
        // If check fails, default to dashboard
        setRedirectTo('/dashboard');
      } finally {
        setIsChecking(false);
      }
    };

    checkAndRedirect();
  }, [isAuthenticated, token]);

  if (isChecking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background via-background to-background/80 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[var(--primary)] mx-auto mb-4" />
          <p className="text-[var(--text-muted)]">Loading...</p>
        </div>
      </div>
    );
  }

  return <Navigate to={redirectTo} replace />;
}

export default FirstTimeUserRedirect;

