import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore.js';
import { User, LogOut, Settings, ChevronDown, Crown } from 'lucide-react';

function UserMenu() {
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const [isOpen, setIsOpen] = useState(false);
    const [imageError, setImageError] = useState(false);
    const menuRef = useRef(null);

    // Reset image error when user changes
    useEffect(() => {
        setImageError(false);
    }, [user?.picture_url]);

    // Close menu when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    const handleLogout = () => {
        logout();
        navigate('/login');
        setIsOpen(false);
    };

    const handleSettings = () => {
        navigate('/settings');
        setIsOpen(false);
    };

    if (!user) return null;


    return (
        <div className="relative" ref={menuRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--surface)] transition-colors"
            >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gradient-primary-start to-gradient-primary-end flex items-center justify-center">
                    {user.picture_url && !imageError ? (
                        <img
                            src={user.picture_url}
                            alt={user.name}
                            className="w-8 h-8 rounded-full object-cover"
                            onError={() => setImageError(true)}
                            referrerPolicy="no-referrer"
                        />
                    ) : (
                        <User className="w-4 h-4 text-white" />
                    )}
                </div>
                <div className="hidden md:block text-left">
                    <div className="text-sm font-medium text-[var(--text)]">{user.name}</div>
                    <div className="text-xs text-[var(--text-muted)]">{user.email}</div>
                </div>
                <ChevronDown className={`w-4 h-4 text-[var(--text-muted)] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute right-0 bottom-full mb-2 w-64 bg-[var(--surface)] border border-[var(--border)] rounded-lg shadow-lg z-50">
                    <div className="p-4 border-b border-[var(--border)]">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gradient-primary-start to-gradient-primary-end flex items-center justify-center">
                                {user.picture_url && !imageError ? (
                                    <img
                                        src={user.picture_url}
                                        alt={user.name}
                                        className="w-10 h-10 rounded-full object-cover"
                                        onError={() => setImageError(true)}
                                        referrerPolicy="no-referrer"
                                    />
                                ) : (
                                    <User className="w-5 h-5 text-white" />
                                )}
                            </div>
                            <div>
                                <div className="font-medium text-[var(--text)]">{user.name}</div>
                                <div className="text-sm text-[var(--text-muted)]">{user.email}</div>
                            </div>
                        </div>
                    </div>

                    <div className="p-2">
                        <button
                            onClick={handleSettings}
                            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-[var(--text)] hover:bg-[var(--surface)] rounded-lg transition-colors"
                        >
                            <Settings className="w-4 h-4" />
                            Settings
                        </button>

                        <button
                            onClick={() => {
                                // Navigate to upgrade page or show upgrade modal
                                setIsOpen(false);
                            }}
                            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                        >
                            <Crown className="w-4 h-4" />
                            Upgrade to Premium
                        </button>

                        <button
                            onClick={handleLogout}
                            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                        >
                            <LogOut className="w-4 h-4" />
                            Sign Out
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

export default UserMenu;
