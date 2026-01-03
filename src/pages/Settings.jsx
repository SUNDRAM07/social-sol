import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { toast } from "sonner";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";
import SocialMediaConnectionModal from "../components/ui/SocialMediaConnectionModal.jsx";
import { Facebook, Twitter, MessageCircle, Instagram, HardDrive, CalendarDays } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import GoogleCalendarIntegration from "../components/GoogleCalendarIntegration.jsx";
import EventCalendarModal from "../components/EventCalendarModal.jsx";

// ========== Usage Widget ==========
function UsageWidget() {
  const [usage, setUsage] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsageStats();
  }, []);

  const fetchUsageStats = async () => {
    try {
      const response = await apiFetch('/api/usage-stats');
      const data = await response.json();
      console.log('Usage stats response:', data);
      if (data.success) {
        setUsage(data.usage || {});
      }
    } catch (error) {
      console.error('Failed to fetch usage stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading usage...</div>;
  }

  const totalTokens = Object.values(usage).reduce((sum, service) => sum + (service.tokens_used || 0), 0);
  const totalCredits = Object.values(usage).reduce((sum, service) => sum + (service.credits_used || 0), 0);

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-600">Total Tokens:</span>
        <span className="font-medium">{totalTokens.toLocaleString()}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-600">Total Credits:</span>
        <span className="font-medium">{totalCredits.toLocaleString()}</span>
      </div>
      {Object.keys(usage).length > 0 && (
        <div className="pt-2 border-t">
          <div className="text-xs text-gray-500 mb-1">By Service:</div>
          {Object.entries(usage).map(([service, stats]) => (
            <div key={service} className="flex justify-between text-xs">
              <span className="capitalize">{service}:</span>
              <span>{stats.tokens_used || 0} tokens, {stats.credits_used || 0} credits</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ========== Settings Page ==========
function Settings() {
  const [driveConnected, setDriveConnected] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showCalendarModal, setShowCalendarModal] = useState(false);
  const { user, logout } = useAuthStore();

  // Delete account function
  const handleDeleteAccount = async () => {
    setDeleteLoading(true);
    try {
      const response = await apiClient.deleteAccount();

      if (response) {
        toast.success('Account deleted successfully');
        logout();
        window.location.href = '/socialanywhere/login';
      } else {
        throw new Error('Failed to delete account');
      }
    } catch (error) {
      console.error('Delete account error:', error);
      toast.error('Failed to delete account. Please try again.');
    } finally {
      setDeleteLoading(false);
      setShowDeleteConfirm(false);
    }
  };

  // Social media connection states
  const [socialMediaModal, setSocialMediaModal] = useState({ open: false, platform: null });
  const [platformStatus, setPlatformStatus] = useState({
    facebook: { connected: false, checking: false, accounts: [] },
    instagram: { connected: false, checking: false, accounts: [] },
    twitter: { connected: false, checking: false, accounts: [] },
    reddit: { connected: false, checking: false, accounts: [] }
  });

  // Handler to save Instagram static credentials
  const handleSaveInstagramCredentials = async (credentials) => {
    try {
      const payload = {
        user_id: user?.id || 'demo_user_123',
        account_id: credentials.INSTAGRAM_ACCOUNT_ID,
        access_token: credentials.INSTAGRAM_ACCESS_TOKEN,
        username: credentials.INSTAGRAM_USERNAME || ''
      };

      const response = await apiFetch('/social-media/instagram/select-account', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(data.message || 'Instagram connected successfully!');
        setSocialMediaModal({ open: false, platform: null });
        await checkSocialMediaPlatformStatus('instagram');
        return true;
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || 'Failed to connect Instagram');
        return false;
      }
    } catch (error) {
      console.error('Error saving Instagram credentials:', error);
      toast.error('Failed to connect Instagram. Please check your credentials.');
      return false;
    }
  };

  // Check Google Drive and Calendar connection status on page load
  useEffect(() => {
    checkGoogleStatus(); // This checks both Drive and Calendar
    checkAllSocialMediaStatus();
    
    // Check if we just returned from Google OAuth (hash indicates success)
    if (window.location.hash === '#google-connected') {
      // Remove hash from URL
      window.history.replaceState(null, '', window.location.pathname);
      // Wait a moment for token.json to be written, then check status
      setTimeout(async () => {
        await checkGoogleStatus();
        toast.success("Successfully connected to Google Calendar!");
      }, 1000);
    }

    // Listen for postMessage from OAuth popup windows
    const handleMessage = (event) => {
      if (event.data && event.data.type) {
        if (event.data.type === 'SOCIAL_CONNECT_SUCCESS') {
          toast.success(event.data.message || 'Successfully connected!');
          checkAllSocialMediaStatus();
        } else if (event.data.type === 'SOCIAL_CONNECT_ERROR') {
          toast.error(event.data.message || 'Connection failed');
        }
      }
    };

    window.addEventListener('message', handleMessage);

    // Check for OAuth callback errors or success messages
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    const success = urlParams.get('success');
    const connected = urlParams.get('connected');
    const platform = urlParams.get('platform');

    if (error) {
      // Decode error message
      const errorMsg = decodeURIComponent(error);
      if (errorMsg.includes('app is not active') || errorMsg.includes('app_not_active')) {
        toast.error(
          `Facebook/Instagram app is not active. Please check your Facebook App Dashboard and ensure the app is active.`,
          { duration: 10000 }
        );
      } else if (connected === 'twitter') {
        // Twitter-specific error handling
        if (errorMsg.includes('redirect_uri') || errorMsg.includes('invalid redirect')) {
          toast.error(
            `Twitter OAuth Error: Redirect URI mismatch. Please check your Twitter app settings and ensure the callback URL matches exactly.`,
            { duration: 10000 }
          );
        } else if (errorMsg.includes('access_denied') || errorMsg.includes('denied')) {
          toast.error(
            `Twitter connection was cancelled or denied. Please try again and approve all permissions.`,
            { duration: 8000 }
          );
        } else {
          toast.error(`Twitter connection error: ${errorMsg}`, { duration: 8000 });
        }
      } else {
        toast.error(`Connection error: ${errorMsg}`, { duration: 8000 });
      }
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (success && connected) {
      const platformName = connected.charAt(0).toUpperCase() + connected.slice(1);
      toast.success(`Successfully connected to ${platformName}!`);
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      // Refresh status
      checkAllSocialMediaStatus();
    } else if (success === 'false' && connected) {
      // Handle explicit failure case
      const platformName = connected.charAt(0).toUpperCase() + connected.slice(1);
      toast.error(`Failed to connect to ${platformName}. Please try again.`, { duration: 8000 });
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);

  const checkGoogleStatus = async () => {
    try {
      setCheckingStatus(true);
      const response = await apiFetch("/google/status");
      const data = await response.json();
      // Check Drive and Calendar separately
      setDriveConnected(data.connected);
      // For Calendar, check if connected (same token but separate check)
      setCalendarConnected(data.connected);
    } catch (error) {
      console.error("Failed to check Google status:", error);
      setDriveConnected(false);
      setCalendarConnected(false);
    } finally {
      setCheckingStatus(false);
    }
  };

  const checkCalendarStatus = async () => {
    try {
      setCheckingStatus(true);
      const response = await apiFetch("/google/status");
      const data = await response.json();
      setCalendarConnected(data.connected);
    } catch (error) {
      console.error("Failed to check Google Calendar status:", error);
      setCalendarConnected(false);
    } finally {
      setCheckingStatus(false);
    }
  };

  const connectToGoogle = async () => {
    try {
      setLoading(true);
      // Open Google OAuth in a new window
      const authWindow = window.open(
        apiUrl("/google/connect"),
        "GoogleAuth",
        "width=500,height=600,scrollbars=yes,resizable=yes"
      );

      // Poll for connection status
      const pollInterval = setInterval(async () => {
        if (authWindow.closed) {
          clearInterval(pollInterval);
          await checkGoogleStatus();
          if (driveConnected) {
            toast.success("Successfully connected to Google Drive!");
          }
          setLoading(false);
          return;
        }

        try {
          const statusResponse = await apiFetch("/google/status");
          const statusData = await statusResponse.json();
          if (statusData.connected) {
            setDriveConnected(true);
            clearInterval(pollInterval);
            authWindow.close();
            toast.success("Successfully connected to Google Drive!");
            setLoading(false);
          }
        } catch (error) {
          // Continue polling
        }
      }, 2000);

      // Stop polling after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        if (!authWindow.closed) {
          authWindow.close();
        }
        setLoading(false);
      }, 60000);
    } catch (error) {
      console.error("Failed to connect to Google:", error);
      toast.error("Failed to connect to Google Drive");
      setLoading(false);
    }
  };

  const connectToGoogleCalendar = async () => {
    try {
      setCalendarLoading(true);
      // Open Google OAuth in a new window
      const authWindow = window.open(
        apiUrl("/google/connect"),
        "GoogleCalendarAuth",
        "width=500,height=600,scrollbars=yes,resizable=yes"
      );

      // Poll for connection status
      const pollInterval = setInterval(async () => {
        if (authWindow.closed) {
          clearInterval(pollInterval);
          await checkCalendarStatus();
          if (calendarConnected) {
            toast.success("Successfully connected to Google Calendar!");
          }
          setCalendarLoading(false);
          return;
        }

        try {
          const statusResponse = await apiFetch("/google/status");
          const statusData = await statusResponse.json();
          if (statusData.connected) {
            setCalendarConnected(true);
            clearInterval(pollInterval);
            authWindow.close();
            toast.success("Successfully connected to Google Calendar!");
            setCalendarLoading(false);
          }
        } catch (error) {
          // Continue polling
        }
      }, 2000);

      // Stop polling after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        if (!authWindow.closed) {
          authWindow.close();
        }
        setCalendarLoading(false);
      }, 60000);
    } catch (error) {
      console.error("Failed to connect to Google Calendar:", error);
      toast.error("Failed to connect to Google Calendar");
      setCalendarLoading(false);
    }
  };

  const disconnectGoogle = async () => {
    try {
      setLoading(true);
      const response = await apiFetch("/google/disconnect", { method: "POST" });

      if (response.ok) {
        setDriveConnected(false);
        setCalendarConnected(false);
        toast.success("Successfully disconnected from Google services");
      } else {
        throw new Error("Failed to disconnect");
      }
    } catch (error) {
      console.error("Failed to disconnect from Google:", error);
      toast.error("Failed to disconnect from Google services");
    } finally {
      setLoading(false);
    }
  };

  const disconnectGoogleCalendar = async () => {
    try {
      setLoading(true);
      const response = await apiFetch("/google/disconnect", { method: "POST" });

      if (response.ok) {
        setCalendarConnected(false);
        // Note: This disconnects both Drive and Calendar since they share the same token
        // If Drive was also connected, it will be disconnected too
        setDriveConnected(false);
        toast.success("Successfully disconnected from Google Calendar");
      } else {
        throw new Error("Failed to disconnect");
      }
    } catch (error) {
      console.error("Failed to disconnect from Google Calendar:", error);
      toast.error("Failed to disconnect from Google Calendar");
    } finally {
      setLoading(false);
    }
  };

  // Social media platform management functions
  const checkAllSocialMediaStatus = async () => {
    const platforms = ['facebook', 'instagram', 'twitter', 'reddit'];

    for (const platform of platforms) {
      setPlatformStatus(prev => ({ ...prev, [platform]: { ...prev[platform], checking: true } }));

      try {
        // Get accounts from database - this is the source of truth
        const accountsResponse = await apiFetch(`/api/social-media/accounts?platform=${platform}`);
        const accountsData = await accountsResponse.json();

        // Filter to only show active accounts (defensive filtering)
        const allAccounts = accountsData.success && accountsData.accounts ? accountsData.accounts : [];
        const activeAccounts = allAccounts.filter(acc => acc.is_active !== false);

        // Only show as connected if we have actual active accounts in the database
        // Don't rely on status API - only use database accounts
        const isConnected = activeAccounts.length > 0;

        console.log(`[${platform}] Status check:`, {
          success: accountsData.success,
          totalAccounts: allAccounts.length,
          activeAccounts: activeAccounts.length,
          accounts: activeAccounts,
          isConnected: isConnected
        });

        setPlatformStatus(prev => ({
          ...prev,
          [platform]: {
            connected: isConnected,
            checking: false,
            accounts: activeAccounts,
            allAccounts: activeAccounts // Use same for now
          }
        }));
      } catch (error) {
        console.error(`Failed to check ${platform} status:`, error);
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { connected: false, checking: false, accounts: [], allAccounts: [] }
        }));
      }
    }
  };

  const handleSocialMediaConnect = async (platform) => {
    try {
      setLoading(true);

      // Instagram uses STATIC credential entry (manual input)
      if (platform === 'instagram') {
        setLoading(false);
        setSocialMediaModal({ open: true, platform: 'instagram' });
        return;
      }

      // For Facebook, Reddit, and Twitter, use OAuth2 flow
      if (platform === 'facebook' || platform === 'reddit' || platform === 'twitter') {
        // Make API call to initiate OAuth2 flow
        const response = await apiFetch(`/social-media/${platform}/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
          // The backend returns JSON with auth_url
          const data = await response.json();
          const authUrl = data.auth_url;
          const authWindow = window.open(
            authUrl,
            `${platform}Auth`,
            "width=500,height=600,scrollbars=yes,resizable=yes"
          );

          // Poll for connection status
          const pollInterval = setInterval(async () => {
            if (authWindow.closed) {
              clearInterval(pollInterval);
              await checkAllSocialMediaStatus();
              setLoading(false);
              return;
            }

            try {
              // Check for accounts in database instead of status
              const accountsResponse = await apiFetch(`/api/social-media/accounts?platform=${platform}`);
              const accountsData = await accountsResponse.json();
              const allAccounts = accountsData.success && accountsData.accounts ? accountsData.accounts : [];
              // Filter to only show active accounts
              const activeAccounts = allAccounts.filter(acc => acc.is_active !== false);

              if (activeAccounts.length > 0) {
                setPlatformStatus(prev => ({
                  ...prev,
                  [platform]: { connected: true, checking: false, accounts: activeAccounts, allAccounts: activeAccounts }
                }));
                clearInterval(pollInterval);
                authWindow.close();
                toast.success(`Successfully connected to ${platform.charAt(0).toUpperCase() + platform.slice(1)}!`);
                setLoading(false);
                // Refresh all statuses
                checkAllSocialMediaStatus();
              }
            } catch (error) {
              // Continue polling
            }
          }, 2000);

          // Stop polling after 60 seconds
          setTimeout(() => {
            clearInterval(pollInterval);
            if (!authWindow.closed) {
              authWindow.close();
            }
            setLoading(false);
          }, 60000);
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || errorData.error || 'Failed to initiate OAuth flow');
        }
      } else {
        // For other platforms, use manual credential entry (if needed)
        setSocialMediaModal({ open: true, platform });
      }
    } catch (error) {
      console.error(`Failed to connect to ${platform}:`, error);
      toast.error(`Failed to connect to ${platform}: ${error.message}`);
      setLoading(false);
    }
  };

  const handleSocialMediaDisconnect = async (platform, accountId = null) => {
    try {
      console.log(`🔌 Disconnecting ${platform} account:`, accountId);

      if (accountId) {
        // Disconnect specific account
        const response = await apiFetch(`/api/social-media/accounts/${accountId}`, { method: "DELETE" });
        const responseData = await response.json();

        console.log(`Disconnect response:`, { ok: response.ok, data: responseData });

        if (response.ok && responseData.success) {
          toast.success(`Account disconnected successfully`);

          // Immediately update local state to reflect disconnect
          setPlatformStatus(prev => {
            const currentAccounts = prev[platform]?.accounts || [];
            const remainingAccounts = currentAccounts.filter(acc => acc.id !== accountId);
            return {
              ...prev,
              [platform]: {
                ...prev[platform],
                connected: remainingAccounts.length > 0,
                accounts: remainingAccounts,
                allAccounts: remainingAccounts
              }
            };
          });

          // Wait a moment for database to update, then refresh from server
          setTimeout(() => {
            checkAllSocialMediaStatus();
          }, 500);
        } else {
          const errorMsg = responseData.error || "Failed to disconnect account";
          throw new Error(errorMsg);
        }
      } else {
        // Disconnect all accounts for platform - get all accounts and disconnect each one
        const currentAccounts = platformStatus[platform]?.accounts || [];
        if (currentAccounts.length === 0) {
          toast.error(`No accounts found to disconnect for ${platform}`);
          return;
        }

        // Disconnect each account
        let successCount = 0;
        let failCount = 0;
        for (const account of currentAccounts) {
          try {
            const response = await apiFetch(`/api/social-media/accounts/${account.id}`, { method: "DELETE" });
            const responseData = await response.json();
            if (response.ok && responseData.success) {
              successCount++;
            } else {
              failCount++;
              console.error(`Failed to disconnect account ${account.id}:`, responseData.error);
            }
          } catch (err) {
            failCount++;
            console.error(`Error disconnecting account ${account.id}:`, err);
          }
        }

        if (successCount > 0) {
          // Immediately update local state
          setPlatformStatus(prev => ({
            ...prev,
            [platform]: { ...prev[platform], connected: false, accounts: [], allAccounts: [] }
          }));

          // Wait a moment for database to update, then refresh from server
          setTimeout(() => {
            checkAllSocialMediaStatus();
          }, 500);

          if (failCount === 0) {
            toast.success(`Successfully disconnected all accounts from ${platform.charAt(0).toUpperCase() + platform.slice(1)}`);
          } else {
            toast.warning(`Disconnected ${successCount} account(s), but ${failCount} failed for ${platform.charAt(0).toUpperCase() + platform.slice(1)}`);
          }
        } else {
          throw new Error(`Failed to disconnect any accounts from ${platform}`);
        }
      }
    } catch (error) {
      console.error(`Failed to disconnect from ${platform}:`, error);
      toast.error(`Failed to disconnect account: ${error.message || error}`);
    }
  };

  const handleSaveCredentials = async (platform, credentials) => {
    try {
      const response = await apiFetch(`/social-media/${platform}/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials)
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { ...prev[platform], connected: true }
        }));
        toast.success(`Successfully connected to ${platform.charAt(0).toUpperCase() + platform.slice(1)}!`);
      } else {
        throw new Error(result.error || 'Connection failed');
      }
    } catch (error) {
      console.error(`Failed to connect to ${platform}:`, error);
      toast.error(`Failed to connect to ${platform}: ${error.message}`);
      throw error;
    }
  };

  const getSocialMediaPlatformConfig = (platform) => {
    const configs = {
      facebook: {
        name: 'Facebook',
        icon: Facebook,
        color: 'bg-blue-600',
        description: 'Connect your Facebook page to post content automatically'
      },
      instagram: {
        name: 'Instagram',
        icon: Instagram,
        color: 'bg-gradient-to-r from-purple-500 to-pink-500',
        description: 'Connect your Instagram account to post content automatically'
      },
      twitter: {
        name: 'Twitter',
        icon: Twitter,
        color: 'bg-black',
        description: 'Connect your Twitter account to post tweets automatically'
      },
      reddit: {
        name: 'Reddit',
        icon: MessageCircle,
        color: 'bg-orange-600',
        description: 'Connect your Reddit account to post to subreddits automatically'
      }
    };
    return configs[platform];
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* Social Media Connections Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-gray-900">Social Media Connections</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {['facebook', 'instagram', 'twitter', 'reddit'].map((platform) => {
            const cfg = getSocialMediaPlatformConfig(platform);
            const st = platformStatus[platform];
            const Icon = cfg.icon;

            // Platform stats + background images (hero area)
            const platformStats = {
              facebook: { users: '3.0B+ users', note: 'High engagement', handle: '@yourbusiness' },
              instagram: { users: '2.4B+ users', note: 'Visual content', handle: '@yourbrand' },
              twitter: { users: '550M+ users', note: 'Real-time updates', handle: '@yourhandle' },
              reddit: { users: '430M+ users', note: 'Community driven', handle: 'r/yourcommunity' },
            }[platform];

            const platformBg = {
              facebook: 'https://images.unsplash.com/photo-1729860648432-723ae383cad9?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmYWNlYm9vayUyMG1vYmlsZSUyMGFwcHxlbnwxfHx8fDE3NjE3MjQ2NDh8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              instagram: 'https://images.unsplash.com/photo-1759912255512-c5e56b4e5e82?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbnN0YWdyYW0lMjBhcHAlMjBpbnRlcmZhY2V8ZW58MXx8fHwxNzYxNzI0NjQ4fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              twitter: 'https://images.unsplash.com/photo-1743582733049-dcb16521f6fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0d2l0dGVyJTIwc29jaWFsJTIwbWVkaWF8ZW58MXx8fHwxNzYxNzI0NjQ4fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              reddit: 'https://images.unsplash.com/photo-1734004691776-d7f04732c174?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzb2NpYWwlMjBtZWRpYSUyMHdvcmtzcGFjZSUyMG1vZGVybnxlbnwxfHx8fDE3NjE3MjQ2NDd8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
            }[platform];

            return (
              <div
                key={platform}
                className={`relative rounded-2xl overflow-hidden border-2 bg-white shadow-sm ${st.connected ? 'border-green-400 ring-1 ring-green-300' : 'border-gray-200'}`}
              >
                {/* Hero background */}
                <div className="relative h-36 md:h-40">
                  <div
                    className="absolute inset-0 bg-center bg-cover"
                    style={{ backgroundImage: `url('${platformBg}')` }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-b from-black/15 via-white/10 to-white" />

                  {/* Platform icon */}
                  <div className={`absolute top-3 left-3 w-11 h-11 ${cfg.color} rounded-xl flex items-center justify-center shadow-md`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>

                  {/* Status badge */}
                  <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${st.connected && st.accounts && st.accounts.length > 0 ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                    <span className={`w-2 h-2 rounded-full ${st.connected && st.accounts && st.accounts.length > 0 ? 'bg-green-500' : 'bg-red-500'}`} />
                    {st.connected && st.accounts && st.accounts.length > 0 ? 'Active' : 'Disconnected'}
                  </span>
                </div>

                {/* Body */}
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-lg font-semibold">{cfg.name}</div>
                      <p className="text-sm text-gray-600 max-w-md">{cfg.description}</p>
                    </div>
                  </div>

                  {/* Connected Account Display (Facebook & Instagram - single account only) */}
                  {st.accounts && st.accounts.length > 0 && (platform === 'facebook' || platform === 'instagram') && (
                    <div className="mt-3 space-y-2 border-t pt-3">
                      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Connected Account
                      </div>
                      {st.accounts.slice(0, 1).map((account) => (
                        <div
                          key={account.id}
                          className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-900 truncate">
                              {account.display_name || account.username || `Account ${account.account_id?.slice(0, 8)}...`}
                            </div>
                            {account.username && account.username !== account.display_name && (
                              <div className="text-xs text-gray-500 truncate">
                                @{account.username}
                              </div>
                            )}
                            {account.account_id && (
                              <div className="text-xs text-gray-400 truncate mt-1">
                                ID: {account.account_id.slice(0, 12)}...
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Connected Accounts List (for platforms that support multiple) */}
                  {st.accounts && st.accounts.length > 0 && platform !== 'instagram' && (
                    <div className="mt-3 space-y-2 border-t pt-3">
                      <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Connected Accounts ({st.accounts.length})
                      </div>
                      {st.accounts.map((account) => (
                        <div
                          key={account.id}
                          className="flex items-center justify-between p-2 bg-gray-50 rounded-lg border border-gray-200"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium text-gray-900 truncate">
                              {account.display_name || account.username || `Account ${account.account_id?.slice(0, 8)}...`}
                            </div>
                            {account.username && account.username !== account.display_name && (
                              <div className="text-xs text-gray-500 truncate">
                                @{account.username}
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => handleSocialMediaDisconnect(platform, account.id)}
                            disabled={loading}
                            className="ml-2 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded border border-red-200"
                            title="Disconnect this account"
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="mt-3 grid grid-cols-1 gap-3 text-sm text-gray-700">
                    <div className="flex items-center gap-3">
                      <span className="text-gray-600">{platformStats.users}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600">{platformStats.note}</span>
                    </div>
                    <div>
                      <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs border ${st.connected ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-50 border-gray-200 text-gray-600'}`}>
                        ✓ {platformStats.handle}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-3">
                    {st.connected ? (
                      <>
                        {platform === 'instagram' && st.accounts && st.accounts.length > 0 ? (
                          <button
                            onClick={() => handleSocialMediaDisconnect(platform, st.accounts[0].id)}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50"
                            disabled={st.checking || loading}
                          >
                            <span className="text-lg leading-none">✖</span> Disconnect
                          </button>
                        ) : (
                          <button
                            onClick={() => handleSocialMediaDisconnect(platform)}
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50"
                            disabled={st.checking || loading}
                          >
                            <span className="text-lg leading-none">✖</span> Disconnect All
                          </button>
                        )}
                        {platform === 'instagram' && (
                          <span className="text-xs text-gray-500">
                            Disconnect to connect a different account
                          </span>
                        )}
                      </>
                    ) : (
                      <button
                        onClick={() => handleSocialMediaConnect(platform)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90"
                        disabled={st.checking}
                      >
                        Connect Now
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setPlatformStatus(prev => ({ ...prev, [platform]: { ...prev[platform], checking: true } }));
                        checkAllSocialMediaStatus();
                      }}
                      className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50"
                      disabled={st.checking}
                    >
                      {st.checking ? 'Checking...' : 'Refresh'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Google Integrations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            {/* Hero background */}
            <div className="relative -mx-5 -mt-5 h-32 md:h-36 overflow-hidden rounded-t-xl">
              <div className="absolute inset-0 bg-center bg-cover" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1600&auto=format&fit=crop')" }} />
              <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-white/10 to-white" />
              {/* Icon */}
              <div className="absolute top-3 left-3 w-11 h-11 bg-emerald-600 rounded-xl flex items-center justify-center shadow-md">
                <HardDrive className="w-6 h-6 text-white" />
              </div>
              {/* Status */}
              <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${driveConnected ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                <span className={`w-2 h-2 rounded-full ${driveConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                {driveConnected ? 'Active' : 'Disconnected'}
              </span>
            </div>

            {/* Body */}
            <div className="p-0 space-y-3">
              <div>
                <div className="text-lg font-semibold">Google Drive</div>
                <p className="text-sm text-gray-600">Save your campaigns and images to Google Drive in JSON format</p>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-700">
                <span className="text-gray-600">Cloud storage</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-600">JSON exports</span>
              </div>
              <div className="mt-2 flex items-center gap-3">
                {driveConnected ? (
                  <button onClick={disconnectGoogle} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                    <span className="text-lg leading-none">✖</span> Disconnect
                  </button>
                ) : (
                  <button onClick={connectToGoogle} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90">
                    Connect Now
                  </button>
                )}
                <button onClick={checkGoogleStatus} disabled={checkingStatus} className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50">
                  {checkingStatus ? 'Checking...' : 'Refresh'}
                </button>
              </div>
            </div>
          </Card>

          <Card>
            {/* Hero background */}
            <div className="relative -mx-5 -mt-5 h-32 md:h-36 overflow-hidden rounded-t-xl">
              <div className="absolute inset-0 bg-center bg-cover" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1506784983877-45594efa4cbe?q=80&w=1600&auto=format&fit=crop')" }} />
              <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-white/10 to-white" />
              {/* Icon */}
              <div className="absolute top-3 left-3 w-11 h-11 bg-indigo-600 rounded-xl flex items-center justify-center shadow-md">
                <CalendarDays className="w-6 h-6 text-white" />
              </div>
              {/* Status */}
              <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${calendarConnected ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                <span className={`w-2 h-2 rounded-full ${calendarConnected ? 'bg-green-500' : 'bg-red-500'}`} />
                {calendarConnected ? 'Active' : 'Disconnected'}
              </span>
            </div>

            {/* Body */}
            <div className="p-0 space-y-3">
              <div>
                <div className="text-lg font-semibold">Google Calendar</div>
                <p className="text-sm text-gray-600">Create calendar events for scheduled social media posts with reminders</p>
              </div>
              <div className="flex items-center gap-3 text-sm text-gray-700">
                <span className="text-gray-600">Reminders</span>
                <span className="text-gray-400">•</span>
                <span className="text-gray-600">Calendar sync</span>
              </div>
              <div className="mt-2 flex items-center gap-3">
                {calendarConnected ? (
                  <>
                    <button onClick={disconnectGoogleCalendar} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                      <span className="text-lg leading-none">✖</span> Disconnect
                    </button>
                    <button 
                      onClick={() => setShowCalendarModal(true)} 
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90"
                    >
                      View More
                    </button>
                  </>
                ) : (
                  <button onClick={connectToGoogleCalendar} disabled={calendarLoading || loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90">
                    Connect Now
                  </button>
                )}
                <button onClick={checkCalendarStatus} disabled={checkingStatus} className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50">
                  {checkingStatus ? 'Checking...' : 'Refresh'}
                </button>
              </div>

              {/* Google Calendar events & campaign mapping */}
              {calendarConnected && (
                <div className="mt-4 border-t pt-4">
                  <GoogleCalendarIntegration 
                    campaigns={[]} 
                    onOpenCalendarModal={() => setShowCalendarModal(true)}
                  />
                </div>
              )}
            </div>
          </Card>
          

          <Card title="Notifications">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Enable notifications</div>
                <div className="text-sm text-gray-600">
                  Receive updates about campaign status
                </div>
              </div>
              <button
                role="switch"
                aria-checked={notifications}
                onClick={() => setNotifications((v) => !v)}
                className={
                  (notifications ? "bg-blue-600" : "bg-gray-300") +
                  " relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                }
              >
                <span
                  className={
                    (notifications ? "translate-x-6" : "translate-x-1") +
                    " inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                  }
                />
              </button>
            </div>
          </Card>

          <Card title="API Usage">
            <UsageWidget />
          </Card>

          <Card title="Account">
            <div className="space-y-3">
              <div className="text-sm text-gray-600">
                User: {user?.name || 'User'} ({user?.email || 'user@example.com'})
              </div>
              <Button
                variant="danger"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={deleteLoading}
              >
                {deleteLoading ? 'Deleting...' : 'Delete account'}
              </Button>
            </div>
          </Card>
        </div>
      </div>

      {/* Social Media Connection Modal */}
      <SocialMediaConnectionModal
        open={socialMediaModal.open}
        onOpenChange={(open) => setSocialMediaModal({ open, platform: socialMediaModal.platform })}
        platform={socialMediaModal.platform}
        onSave={handleSaveCredentials}
      />

      {/* Event Calendar Modal */}
      <EventCalendarModal
        isOpen={showCalendarModal}
        onClose={() => setShowCalendarModal(false)}
        calendarConnected={calendarConnected}
      />

      {/* Delete Account Confirmation Modal */}
      {showDeleteConfirm && createPortal(
        <div className="fixed inset-0 z-[10000] flex items-center justify-center p-4" style={{ backgroundColor: 'transparent' }}>
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-md w-full mx-4 border border-gray-200">
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Delete Account
              </h3>
              <p className="text-sm text-gray-600">
                Are you sure you want to delete your account? This action cannot be undone.
                All your data, campaigns, and posts will be permanently deleted.
              </p>
            </div>
            <div className="flex gap-3 justify-end pt-4 border-t border-gray-200">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {deleteLoading && (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                )}
                {deleteLoading ? 'Deleting...' : 'Yes, Delete Account'}
              </button>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Social Media Connection Modal (for Instagram static credentials) */}
      <SocialMediaConnectionModal
        open={socialMediaModal.open}
        onOpenChange={(open) => setSocialMediaModal({ open, platform: open ? socialMediaModal.platform : null })}
        platform={socialMediaModal.platform}
        onSave={socialMediaModal.platform === 'instagram' ? handleSaveInstagramCredentials : undefined}
      />
    </div>
  );
}

export default Settings;
