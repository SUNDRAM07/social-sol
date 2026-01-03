import React, { useState, useEffect, useRef } from 'react';
import { ChevronDown, Settings, LogOut, Key, Crown, User } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Modal from './Modal.jsx';
import Button from './Button.jsx';
import { useAuthStore } from '../../store/authStore';

export default function UserProfile() {
    const [open, setOpen] = useState(false);
    const [showChange, setShowChange] = useState(false);
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const dropdownRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setOpen(false);
            }
        }

        if (open) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [open]);

    function onLogout() {
        logout();
        navigate('/login');
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                aria-haspopup="true"
                aria-expanded={open}
                onClick={() => {
                    console.log('Dropdown clicked, current state:', open);
                    setOpen((s) => {
                        console.log('Setting dropdown state to:', !s);
                        return !s;
                    });
                }}
                className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-white/10 transition-colors duration-200 group"
            >
                {/* Avatar */}
                <div className="w-8 h-8 rounded-lg bg-gradient-primary flex items-center justify-center flex-shrink-0 overflow-hidden">
                    {user?.picture_url ? (
                        <img
                            src={user.picture_url}
                            alt={user.name}
                            className="w-full h-full object-cover"
                        />
                    ) : (
                        <span className="font-semibold text-black text-sm">
                            {user?.name ? user.name.charAt(0).toUpperCase() : 'A'}
                        </span>
                    )}
                </div>

                {/* User Info */}
                <div className="flex-1 min-w-0 text-left">
                    <div className="text-sm font-medium text-black truncate">
                        {user?.name || 'User'}
                    </div>
                    <div className="text-xs text-black/60 truncate">
                        {user?.email || 'user@example.com'}
                    </div>
                </div>

                {/* Dropdown Arrow */}
                <ChevronDown
                    className={`w-4 h-4 text-black/60 transition-transform duration-200 ${open ? 'rotate-180' : ''
                        }`}
                />
            </button>

            {open && (() => {
                console.log('Rendering dropdown menu');
                return (
                    <div
                        role="menu"
                        className="absolute bg-white border-2 border-red-500 rounded-lg shadow-2xl py-2 min-w-[200px]"
                        style={{
                            position: 'fixed',
                            top: '50%',
                            left: '50%',
                            transform: 'translate(-50%, -50%)',
                            maxHeight: '300px',
                            overflowY: 'auto',
                            display: 'block',
                            zIndex: 99999,
                            backgroundColor: 'white',
                            boxShadow: '0 10px 25px rgba(0,0,0,0.3)',
                            border: '3px solid red'
                        }}
                        onMouseLeave={() => setOpen(false)}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="px-4 py-2 text-xs text-gray-500 border-b border-gray-200">
                            User Menu (Debug: Dropdown is open!)
                        </div>
                        <button
                            role="menuitem"
                            className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:bg-gray-50 transition-colors duration-200"
                            onClick={() => {
                                navigate('/settings');
                                setOpen(false);
                            }}
                        >
                            <Settings className="w-4 h-4" />
                            Settings
                        </button>

                        <button
                            role="menuitem"
                            className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus-visible:bg-gray-50 transition-colors duration-200"
                            onClick={() => { setShowChange(true); setOpen(false); }}
                        >
                            <Key className="w-4 h-4" />
                            Change password
                        </button>

                        <button
                            role="menuitem"
                            className="w-full flex items-center gap-3 px-4 py-2 text-sm text-purple-600 hover:bg-purple-50 focus-visible:bg-purple-50 transition-colors duration-200"
                            onClick={() => {
                                // Navigate to upgrade page or show upgrade modal
                                setOpen(false);
                            }}
                        >
                            <Crown className="w-4 h-4" />
                            Upgrade to Premium
                        </button>

                        <div className="border-t border-gray-200 my-1" />

                        <button
                            role="menuitem"
                            className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 focus-visible:bg-red-50 transition-colors duration-200"
                            onClick={onLogout}
                        >
                            <LogOut className="w-4 h-4" />
                            Logout
                        </button>
                    </div>
                );
            })()}

            <Modal open={showChange} onOpenChange={setShowChange} title="Change password">
                <ChangePasswordForm onDone={() => setShowChange(false)} />
            </Modal>
        </div>
    );
}

function ChangePasswordForm({ onDone }) {
    const [formData, setFormData] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
    });

    const handleSubmit = (e) => {
        e.preventDefault();
        // Handle password change logic here
        console.log('Password change requested:', formData);
        onDone();
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Current Password
                </label>
                <input
                    type="password"
                    value={formData.currentPassword}
                    onChange={(e) => handleInputChange('currentPassword', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    New Password
                </label>
                <input
                    type="password"
                    value={formData.newPassword}
                    onChange={(e) => handleInputChange('newPassword', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                />
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confirm New Password
                </label>
                <input
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    required
                />
            </div>

            <div className="flex justify-end space-x-3 pt-4">
                <Button variant="secondary" onClick={onDone}>
                    Cancel
                </Button>
                <Button variant="primary" type="submit">
                    Change Password
                </Button>
            </div>
        </form>
    );
}
