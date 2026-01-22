/**
 * SettingsModal - Quick in-app settings without leaving the page
 * 
 * Tabs:
 * - Platforms: Connect/disconnect social media accounts
 * - Notifications: Email, push, in-app notifications
 * - Appearance: Theme, sidebar, display options
 * - Account: Email, password, delete account
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/authStore';
import {
  X, Settings, Link2, Bell, Palette, User, Shield,
  Twitter, Instagram, Youtube, Linkedin, MessageCircle,
  Check, AlertCircle, ExternalLink, ChevronRight, Loader2,
  Sun, Moon, Monitor, Mail, Smartphone, Globe
} from 'lucide-react';

// Platform configuration
const platforms = [
  { 
    id: 'twitter', 
    name: 'Twitter/X', 
    icon: Twitter, 
    color: 'from-sky-400 to-blue-500',
    connectUrl: '/auth/twitter' 
  },
  { 
    id: 'instagram', 
    name: 'Instagram', 
    icon: Instagram, 
    color: 'from-pink-500 via-purple-500 to-orange-400',
    connectUrl: '/auth/instagram' 
  },
  { 
    id: 'linkedin', 
    name: 'LinkedIn', 
    icon: Linkedin, 
    color: 'from-blue-600 to-blue-700',
    connectUrl: '/auth/linkedin' 
  },
  { 
    id: 'youtube', 
    name: 'YouTube', 
    icon: Youtube, 
    color: 'from-red-500 to-red-600',
    connectUrl: '/auth/youtube' 
  },
  { 
    id: 'reddit', 
    name: 'Reddit', 
    icon: MessageCircle, 
    color: 'from-orange-500 to-orange-600',
    connectUrl: '/auth/reddit' 
  },
  { 
    id: 'discord', 
    name: 'Discord', 
    icon: MessageCircle, 
    color: 'from-indigo-500 to-purple-600',
    connectUrl: '/auth/discord',
    comingSoon: true
  },
];

const SettingsModal = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { token, user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('platforms');
  const [connectedPlatforms, setConnectedPlatforms] = useState({});
  const [loading, setLoading] = useState(false);
  const [notifications, setNotifications] = useState({
    email_posts: true,
    email_weekly: true,
    push_enabled: false,
    in_app: true,
  });
  const [theme, setTheme] = useState('dark');

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (isOpen && token) {
      fetchConnectedPlatforms();
    }
  }, [isOpen, token]);

  const fetchConnectedPlatforms = async () => {
    try {
      const res = await fetch(`${API_URL}/social/connected`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setConnectedPlatforms(data.platforms || {});
      }
    } catch (err) {
      console.error('Error fetching platforms:', err);
    }
  };

  const handleConnect = (platform) => {
    // Open OAuth flow in new window
    const width = 600;
    const height = 700;
    const left = window.screenX + (window.outerWidth - width) / 2;
    const top = window.screenY + (window.outerHeight - height) / 2;
    
    window.open(
      `${API_URL}${platform.connectUrl}?token=${token}`,
      `Connect ${platform.name}`,
      `width=${width},height=${height},left=${left},top=${top}`
    );

    // Poll for connection status
    const pollInterval = setInterval(async () => {
      await fetchConnectedPlatforms();
    }, 2000);

    // Stop polling after 2 minutes
    setTimeout(() => clearInterval(pollInterval), 120000);
  };

  const handleDisconnect = async (platformId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/social/disconnect/${platformId}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      if (res.ok) {
        await fetchConnectedPlatforms();
      }
    } catch (err) {
      console.error('Error disconnecting:', err);
    }
    setLoading(false);
  };

  if (!isOpen) return null;

  const tabs = [
    { id: 'platforms', label: 'Platforms', icon: Link2 },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'account', label: 'Account', icon: User },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-[#111] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Settings</h2>
              <p className="text-xs text-white/50">Manage your account and preferences</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-white/10">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium
                  transition-colors relative
                  ${activeTab === tab.id 
                    ? 'text-white' 
                    : 'text-white/50 hover:text-white/80'}
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-[#9945FF] to-[#14F195]" />
                )}
              </button>
            );
          })}
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[60vh]">
          {/* Platforms Tab */}
          {activeTab === 'platforms' && (
            <div className="space-y-3">
              <p className="text-sm text-white/60 mb-4">
                Connect your social media accounts to start posting and scheduling content.
              </p>
              
              {platforms.map((platform) => {
                const Icon = platform.icon;
                const isConnected = connectedPlatforms[platform.id];
                
                return (
                  <div
                    key={platform.id}
                    className={`
                      flex items-center gap-4 p-4 rounded-xl border transition-all
                      ${isConnected 
                        ? 'bg-[#14F195]/5 border-[#14F195]/30' 
                        : 'bg-white/[0.02] border-white/10 hover:border-white/20'}
                    `}
                  >
                    <div className={`
                      w-12 h-12 rounded-xl flex items-center justify-center
                      bg-gradient-to-br ${platform.color}
                    `}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium text-white">{platform.name}</h4>
                        {platform.comingSoon && (
                          <span className="px-2 py-0.5 text-[10px] font-medium bg-purple-500/20 text-purple-400 rounded-full">
                            Coming Soon
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-white/50">
                        {isConnected 
                          ? `Connected as @${connectedPlatforms[platform.id]?.username || 'user'}`
                          : 'Not connected'}
                      </p>
                    </div>

                    {isConnected ? (
                      <div className="flex items-center gap-2">
                        <span className="flex items-center gap-1 text-sm text-[#14F195]">
                          <Check className="w-4 h-4" />
                          Connected
                        </span>
                        <button
                          onClick={() => handleDisconnect(platform.id)}
                          disabled={loading}
                          className="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                        >
                          Disconnect
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => !platform.comingSoon && handleConnect(platform)}
                        disabled={platform.comingSoon || loading}
                        className={`
                          flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                          transition-all
                          ${platform.comingSoon 
                            ? 'bg-white/5 text-white/30 cursor-not-allowed'
                            : 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white hover:shadow-lg hover:shadow-[#9945FF]/30'}
                        `}
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Link2 className="w-4 h-4" />
                        )}
                        Connect
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Notifications Tab */}
          {activeTab === 'notifications' && (
            <div className="space-y-4">
              <p className="text-sm text-white/60 mb-4">
                Choose how you want to be notified about activity on your account.
              </p>

              <div className="space-y-3">
                <ToggleSetting
                  icon={Mail}
                  title="Email - Post Published"
                  description="Get notified when your posts are published"
                  enabled={notifications.email_posts}
                  onChange={(v) => setNotifications({...notifications, email_posts: v})}
                />
                <ToggleSetting
                  icon={Mail}
                  title="Weekly Summary"
                  description="Receive a weekly performance report"
                  enabled={notifications.email_weekly}
                  onChange={(v) => setNotifications({...notifications, email_weekly: v})}
                />
                <ToggleSetting
                  icon={Smartphone}
                  title="Push Notifications"
                  description="Browser push notifications for important updates"
                  enabled={notifications.push_enabled}
                  onChange={(v) => setNotifications({...notifications, push_enabled: v})}
                />
                <ToggleSetting
                  icon={Globe}
                  title="In-App Notifications"
                  description="Show notifications within the app"
                  enabled={notifications.in_app}
                  onChange={(v) => setNotifications({...notifications, in_app: v})}
                />
              </div>
            </div>
          )}

          {/* Appearance Tab */}
          {activeTab === 'appearance' && (
            <div className="space-y-4">
              <p className="text-sm text-white/60 mb-4">
                Customize how SocialAnywhere looks and feels.
              </p>

              <div>
                <h4 className="text-sm font-medium text-white mb-3">Theme</h4>
                <div className="flex gap-3">
                  {[
                    { id: 'light', label: 'Light', icon: Sun },
                    { id: 'dark', label: 'Dark', icon: Moon },
                    { id: 'system', label: 'System', icon: Monitor },
                  ].map((option) => {
                    const Icon = option.icon;
                    return (
                      <button
                        key={option.id}
                        onClick={() => setTheme(option.id)}
                        className={`
                          flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border transition-all
                          ${theme === option.id 
                            ? 'bg-[#9945FF]/10 border-[#9945FF]/50 text-white' 
                            : 'bg-white/[0.02] border-white/10 text-white/60 hover:border-white/20'}
                        `}
                      >
                        <Icon className="w-6 h-6" />
                        <span className="text-sm font-medium">{option.label}</span>
                        {theme === option.id && (
                          <Check className="w-4 h-4 text-[#14F195]" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-white/40">
                  More customization options coming soon! Including custom accent colors and sidebar preferences.
                </p>
              </div>
            </div>
          )}

          {/* Account Tab */}
          {activeTab === 'account' && (
            <div className="space-y-4">
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                <h4 className="text-sm font-medium text-white mb-1">Email Address</h4>
                <p className="text-white/60">{user?.email || 'Not set'}</p>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
                <h4 className="text-sm font-medium text-white mb-1">Account Type</h4>
                <p className="text-white/60">
                  {user?.wallet_address ? 'Wallet-based account' : 'Email-based account'}
                </p>
              </div>

              <button
                onClick={() => { onClose(); navigate('/settings'); }}
                className="w-full flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/10 hover:border-white/20 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-white/60" />
                  <div className="text-left">
                    <h4 className="text-sm font-medium text-white">Security Settings</h4>
                    <p className="text-xs text-white/50">Password, 2FA, sessions</p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-white/40" />
              </button>

              <div className="pt-4 border-t border-white/10">
                <button className="text-sm text-red-400 hover:text-red-300 transition-colors">
                  Delete Account
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t border-white/10 bg-white/[0.02]">
          <button
            onClick={() => navigate('/settings')}
            className="text-sm text-white/50 hover:text-white flex items-center gap-1"
          >
            <ExternalLink className="w-4 h-4" />
            Full Settings Page
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium text-white transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

// Toggle setting component
const ToggleSetting = ({ icon: Icon, title, description, enabled, onChange }) => (
  <div className="flex items-center justify-between p-4 rounded-xl bg-white/[0.02] border border-white/10">
    <div className="flex items-center gap-3">
      <Icon className="w-5 h-5 text-white/60" />
      <div>
        <h4 className="text-sm font-medium text-white">{title}</h4>
        <p className="text-xs text-white/50">{description}</p>
      </div>
    </div>
    <button
      onClick={() => onChange(!enabled)}
      className={`
        relative w-11 h-6 rounded-full transition-colors
        ${enabled ? 'bg-[#14F195]' : 'bg-white/20'}
      `}
    >
      <div className={`
        absolute top-1 w-4 h-4 rounded-full bg-white shadow-md transition-transform
        ${enabled ? 'left-6' : 'left-1'}
      `} />
    </button>
  </div>
);

export default SettingsModal;
