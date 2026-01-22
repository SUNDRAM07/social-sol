/**
 * ProfileDropdown - Enhanced user menu with tier info, quick actions, and wallet status
 * 
 * Features:
 * - User avatar with tier badge
 * - Subscription status display
 * - Connected platforms count
 * - Quick actions (Upgrade, Settings, Help, Logout)
 * - Wallet connection status
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWallet } from '@solana/wallet-adapter-react';
import { useAuthStore } from '../../store/authStore';
import {
    User, LogOut, Settings, ChevronDown, Crown, Wallet,
    HelpCircle, Link2, ExternalLink, Zap, Bell, Shield,
    CreditCard, Sparkles, CheckCircle, AlertCircle, Coins
} from 'lucide-react';

// Tier badge colors and labels
const tierConfig = {
    free: {
        label: 'Free',
        color: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
        icon: null
    },
    basic: {
        label: 'Basic',
        color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        icon: Zap
    },
    premium: {
        label: 'Premium',
        color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
        icon: Crown
    },
    agency: {
        label: 'Agency',
        color: 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-amber-400 border-amber-500/30',
        icon: Sparkles
    },
};

const ProfileDropdown = ({
    variant = 'default', // 'default' | 'compact' | 'header'
    showSettingsModal,
    cachedSubscriptionData = null, // Accept cached data from parent
    cachedPlatformCount = 0,
    className = ''
}) => {
    const navigate = useNavigate();
    const { user, logout } = useAuthStore();
    const { connected, publicKey, disconnect } = useWallet();
    const [isOpen, setIsOpen] = useState(false);
    const [imageError, setImageError] = useState(false);
    const menuRef = useRef(null);

    // Use cached data if available (from useSidebarData hook)
    const subscriptionData = cachedSubscriptionData;
    const connectedPlatforms = cachedPlatformCount;

    // Close on outside click
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (menuRef.current && !menuRef.current.contains(e.target)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Reset image error on user change
    useEffect(() => {
        setImageError(false);
    }, [user?.picture_url]);

    const handleLogout = () => {
        if (connected) disconnect();
        logout();
        navigate('/login');
        setIsOpen(false);
    };

    const handleNavigate = (path) => {
        navigate(path);
        setIsOpen(false);
    };

    if (!user) return null;

    const tier = subscriptionData?.tier || 'free';
    const tierInfo = tierConfig[tier] || tierConfig.free;
    const TierIcon = tierInfo.icon;

    const shortWallet = publicKey
        ? `${publicKey.toString().slice(0, 4)}...${publicKey.toString().slice(-4)}`
        : null;

    return (
        <div className={`relative ${className}`} ref={menuRef}>
            {/* Trigger Button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`
          flex items-center gap-3 rounded-xl transition-all duration-200
          ${variant === 'compact'
                        ? 'p-2 hover:bg-white/5'
                        : 'p-2 pr-3 hover:bg-white/5 border border-transparent hover:border-white/10'}
        `}
            >
                {/* Avatar */}
                <div className="relative">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center overflow-hidden">
                        {user.picture_url && !imageError ? (
                            <img
                                src={user.picture_url}
                                alt={user.name}
                                className="w-9 h-9 rounded-xl object-cover"
                                onError={() => setImageError(true)}
                                referrerPolicy="no-referrer"
                            />
                        ) : (
                            <User className="w-5 h-5 text-white" />
                        )}
                    </div>
                    {/* Tier indicator dot */}
                    {tier !== 'free' && (
                        <div className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-black
              ${tier === 'premium' ? 'bg-purple-500' : tier === 'agency' ? 'bg-amber-500' : 'bg-blue-500'}`}
                        />
                    )}
                </div>

                {/* Name and tier (hidden on compact) */}
                {variant !== 'compact' && (
                    <div className="hidden sm:block text-left">
                        <div className="text-sm font-medium text-white truncate max-w-[120px]">
                            {user.name?.split(' ')[0] || 'User'}
                        </div>
                        <div className="flex items-center gap-1">
                            {TierIcon && <TierIcon className="w-3 h-3 text-purple-400" />}
                            <span className="text-xs text-white/50 capitalize">{tierInfo.label}</span>
                        </div>
                    </div>
                )}

                <ChevronDown className={`w-4 h-4 text-white/40 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {isOpen && (
                <div className="absolute right-0 bottom-full mb-2 w-72 bg-[#1a1a1a] border border-white/10 rounded-2xl shadow-2xl shadow-black/50 overflow-hidden z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
                    {/* User Header */}
                    <div className="p-4 bg-gradient-to-br from-[#9945FF]/10 to-[#14F195]/10 border-b border-white/10">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center overflow-hidden">
                                {user.picture_url && !imageError ? (
                                    <img
                                        src={user.picture_url}
                                        alt={user.name}
                                        className="w-12 h-12 rounded-xl object-cover"
                                        onError={() => setImageError(true)}
                                        referrerPolicy="no-referrer"
                                    />
                                ) : (
                                    <User className="w-6 h-6 text-white" />
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="font-semibold text-white truncate">{user.name}</div>
                                <div className="text-sm text-white/50 truncate">{user.email}</div>
                            </div>
                        </div>

                        {/* Tier Badge */}
                        <div className="flex items-center gap-2 mt-3">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${tierInfo.color}`}>
                                {TierIcon && <TierIcon className="w-3.5 h-3.5" />}
                                {tierInfo.label} Tier
                            </span>
                            {tier === 'free' || tier === 'basic' ? (
                                <button
                                    onClick={() => handleNavigate('/tokens')}
                                    className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
                                >
                                    <Crown className="w-3 h-3" />
                                    Upgrade
                                </button>
                            ) : null}
                        </div>
                    </div>

                    {/* Stats Row */}
                    <div className="flex border-b border-white/10">
                        <div className="flex-1 p-3 text-center border-r border-white/10">
                            <div className="text-lg font-bold text-white">{connectedPlatforms}</div>
                            <div className="text-[10px] text-white/40 uppercase tracking-wider">Platforms</div>
                        </div>
                        <div className="flex-1 p-3 text-center border-r border-white/10">
                            <div className="text-lg font-bold text-white">{subscriptionData?.posts_today || 0}</div>
                            <div className="text-[10px] text-white/40 uppercase tracking-wider">Posts Today</div>
                        </div>
                        <div className="flex-1 p-3 text-center">
                            <div className="text-lg font-bold text-[#14F195]">{subscriptionData?.credits || 0}</div>
                            <div className="text-[10px] text-white/40 uppercase tracking-wider">Credits</div>
                        </div>
                    </div>

                    {/* Wallet Status */}
                    <div className="p-2 border-b border-white/10">
                        <div className={`
              flex items-center justify-between px-3 py-2 rounded-xl
              ${connected ? 'bg-[#14F195]/10' : 'bg-orange-500/10'}
            `}>
                            <div className="flex items-center gap-2">
                                <Wallet className={`w-4 h-4 ${connected ? 'text-[#14F195]' : 'text-orange-400'}`} />
                                <span className="text-sm text-white">
                                    {connected ? shortWallet : 'Wallet not connected'}
                                </span>
                            </div>
                            {connected ? (
                                <CheckCircle className="w-4 h-4 text-[#14F195]" />
                            ) : (
                                <AlertCircle className="w-4 h-4 text-orange-400" />
                            )}
                        </div>
                    </div>

                    {/* Menu Items */}
                    <div className="p-2">
                        <MenuItem
                            icon={Coins}
                            label="Token Dashboard"
                            sublabel="Balance & tier"
                            onClick={() => handleNavigate('/tokens')}
                        />
                        <MenuItem
                            icon={Link2}
                            label="Connected Accounts"
                            sublabel={`${connectedPlatforms} connected`}
                            onClick={() => handleNavigate('/settings')}
                        />
                        <MenuItem
                            icon={Settings}
                            label="Settings"
                            onClick={() => showSettingsModal ? showSettingsModal() : handleNavigate('/settings')}
                        />
                        <MenuItem
                            icon={HelpCircle}
                            label="Help & Support"
                            onClick={() => handleNavigate('/help-support')}
                        />

                        <div className="my-2 border-t border-white/10" />

                        <MenuItem
                            icon={LogOut}
                            label="Sign Out"
                            variant="danger"
                            onClick={handleLogout}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

// Reusable menu item component
const MenuItem = ({ icon: Icon, label, sublabel, onClick, variant = 'default' }) => {
    const variants = {
        default: 'text-white/80 hover:text-white hover:bg-white/5',
        danger: 'text-red-400 hover:text-red-300 hover:bg-red-500/10',
        primary: 'text-purple-400 hover:text-purple-300 hover:bg-purple-500/10',
    };

    return (
        <button
            onClick={onClick}
            className={`
        w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150
        ${variants[variant]}
      `}
        >
            <Icon className="w-4 h-4 flex-shrink-0" />
            <div className="flex-1 text-left">
                <span className="font-medium">{label}</span>
                {sublabel && (
                    <span className="block text-xs text-white/40">{sublabel}</span>
                )}
            </div>
            <ChevronDown className="w-4 h-4 -rotate-90 opacity-40" />
        </button>
    );
};

export default ProfileDropdown;
