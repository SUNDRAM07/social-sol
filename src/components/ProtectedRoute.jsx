import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../store/authStore.js';
import { Loader2 } from 'lucide-react';

function ProtectedRoute({ children }) {
    const { isAuthenticated, isLoading, getCurrentUser } = useAuthStore();
    const location = useLocation();

    useEffect(() => {
        // Check if user is authenticated on mount
        if (!isAuthenticated && !isLoading) {
            getCurrentUser();
        }
    }, [isAuthenticated, isLoading, getCurrentUser]);

    // Show loading spinner while checking authentication
    if (isLoading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-background via-background to-background/80 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-8 h-8 animate-spin text-[var(--primary)] mx-auto mb-4" />
                    <p className="text-[var(--text-muted)]">Loading...</p>
                </div>
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Render protected content
    return children;
}

export default ProtectedRoute;
