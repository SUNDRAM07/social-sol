import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';
import { checkPlatformConnections } from '../lib/apiClient';
import { Loader2 } from 'lucide-react';

/**
 * Component that checks if user needs onboarding or has platform integrations
 * Redirects accordingly:
 * - Not authenticated -> /login
 * - First time (no onboarding completed) -> /onboarding
 * - Returning user -> /chat
 */
function FirstTimeUserRedirect() {
  const { isAuthenticated, token } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);
  const [redirectTo, setRedirectTo] = useState('/chat');

  useEffect(() => {
    const checkAndRedirect = async () => {
      if (!isAuthenticated || !token) {
        setRedirectTo('/login');
        setIsChecking(false);
        return;
      }

      // Check if onboarding has been completed
      const onboardingCompleted = localStorage.getItem('onboarding_completed');
      
      if (!onboardingCompleted) {
        // First-time user - show onboarding
        setRedirectTo('/onboarding');
        setIsChecking(false);
        return;
      }

      // Returning user - go to chat
      setRedirectTo('/chat');
      setIsChecking(false);
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

