import { useState, memo } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useWallet } from '@solana/wallet-adapter-react';
import clsx from "clsx";
import ThemeToggle from "../components/ThemeToggle.jsx";
import ProfileDropdown from "../components/ui/ProfileDropdown.jsx";
import SettingsModal from "../components/ui/SettingsModal.jsx";
import useAuthStore from "../store/authStore";
import useSidebarData from "../hooks/useSidebarData";
import {
  MessageSquarePlus,
  LayoutDashboard,
  Calendar,
  BarChart3,
  Lightbulb,
  FolderOpen,
  Coins,
  Settings,
  HelpCircle,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  Crown,
  Flame,
  Zap
} from "lucide-react";

// Main navigation items
const mainNavItems = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/idea-generator", label: "Idea Generator", icon: Lightbulb },
  { to: "/campaigns", label: "Campaigns", icon: FolderOpen },
];

// Token/Automation section
const tokenNavItems = [
  { to: "/tokens", label: "Token Dashboard", icon: Coins, badge: null },
  { to: "/flows", label: "Automations", icon: Zap, badge: "New" },
];

// Secondary nav items (bottom section)
const secondaryNavItems = [
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/help-support", label: "Help & Support", icon: HelpCircle },
];

// Memoized navigation item to prevent unnecessary re-renders
const NavItem = memo(({ item, isActive }) => {
  const Icon = item.icon;
  return (
    <NavLink
      to={item.to}
      className={clsx(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
        isActive
          ? "bg-white/10 text-white"
          : "text-gray-400 hover:bg-white/5 hover:text-white"
      )}
    >
      <Icon className="h-5 w-5" />
      <span>{item.label}</span>
      {item.badge && (
        <span className="ml-auto text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">
          {item.badge}
        </span>
      )}
    </NavLink>
  );
});

NavItem.displayName = 'NavItem';

// Compact streak counter using cached data
const CompactStreak = memo(({ stats }) => {
  if (!stats) {
    return <div className="animate-pulse bg-white/5 rounded-lg p-3 h-14" />;
  }

  return (
    <div className="bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded-xl p-3 border border-orange-500/20">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${stats.current_streak > 0 ? 'bg-orange-500/20' : 'bg-gray-500/20'}`}>
          <Flame className={`w-5 h-5 ${stats.current_streak > 0 ? 'text-orange-400' : 'text-gray-400'}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-1.5">
            <span className="text-xl font-bold text-white">
              {stats.current_streak || 0}
            </span>
            <span className="text-xs text-gray-400">day streak</span>
          </div>
          <p className="text-xs text-gray-500 truncate">
            {stats.total_posts || 0} total posts
          </p>
        </div>
      </div>
    </div>
  );
});

CompactStreak.displayName = 'CompactStreak';

function Sidebar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [showChats, setShowChats] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

  // Use centralized data hook - single source of truth
  const {
    subscriptionTier,
    subscriptionData,
    recentChats,
    connectedPlatforms,
    gamificationStats,
    isLoading,
  } = useSidebarData();

  const handleNewChat = () => {
    navigate('/chat');
  };

  const getTierBadge = () => {
    const badges = {
      free: { text: "Free", color: "bg-gray-500/20 text-gray-400" },
      basic: { text: "Basic", color: "bg-blue-500/20 text-blue-400" },
      premium: { text: "Premium", color: "bg-purple-500/20 text-purple-400" },
      agency: { text: "Agency", color: "bg-amber-500/20 text-amber-400" },
    };
    return badges[subscriptionTier] || badges.free;
  };

  const tierBadge = getTierBadge();

  return (
    <aside className="fixed left-0 top-0 h-full w-[280px] bg-slate-900/95 backdrop-blur-xl flex flex-col z-20 border-r border-white/10">
      {/* Header with Logo */}
      <div className="p-3 border-b border-white/10">
        <div className="flex items-center justify-between gap-2">
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity focus:outline-none focus:ring-2 focus:ring-purple-500/50 rounded-lg overflow-hidden"
            aria-label="Go to Dashboard"
          >
            {/* Logo icon only - cropped to show just the emblem */}
            <div className="w-9 h-9 rounded-lg overflow-hidden flex-shrink-0 bg-gradient-to-br from-purple-500/20 to-pink-500/20 p-0.5">
              <img
                src="/Gemini_Generated_Image_en4aq2en4aq2en4a.png"
                alt="SocialSol"
                className="w-full h-full object-cover object-top scale-[1.8] translate-y-1"
              />
            </div>
            <span className="text-white font-semibold text-sm">SocialSol</span>
          </button>
          <div className="flex items-center gap-2">
            {isLoading ? (
              <div className="animate-pulse bg-white/10 rounded-full w-12 h-5" />
            ) : (
              <span className={clsx("text-xs px-2 py-1 rounded-full", tierBadge.color)}>
                {tierBadge.text}
              </span>
            )}
            <ThemeToggle />
          </div>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-3 px-4 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-xl text-white font-medium transition-all shadow-lg hover:shadow-purple-500/25"
        >
          <MessageSquarePlus className="h-5 w-5" />
          New Chat
        </button>
      </div>

      {/* Scrollable Navigation Area */}
      <div className="flex-1 overflow-y-auto py-2">
        {/* Main Navigation */}
        <nav className="px-3 space-y-1">
          {mainNavItems.map((item) => (
            <NavItem
              key={item.to}
              item={item}
              isActive={pathname === item.to || pathname.startsWith(item.to + '/')}
            />
          ))}
        </nav>

        {/* Divider */}
        <div className="my-3 mx-3 border-t border-white/10" />

        {/* Token & Automations Section */}
        <nav className="px-3 space-y-1">
          {tokenNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.to;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  isActive
                    ? "bg-gradient-to-r from-purple-500/20 to-pink-500/20 text-purple-300 border border-purple-500/30"
                    : "text-gray-400 hover:bg-white/5 hover:text-white"
                )}
              >
                <Icon className="h-5 w-5" />
                <span>{item.label}</span>
                {item.badge && (
                  <span className="ml-auto text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded-full">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Divider */}
        <div className="my-3 mx-3 border-t border-white/10" />

        {/* Recent Chats Section */}
        <div className="px-3">
          <button
            onClick={() => setShowChats(!showChats)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wider hover:text-gray-400 transition-colors"
          >
            <span>Recent Chats</span>
            {showChats ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>

          {showChats && (
            <div className="mt-1 space-y-1">
              {isLoading ? (
                // Skeleton loading for chats
                <div className="space-y-2 px-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse bg-white/5 rounded-lg h-8" />
                  ))}
                </div>
              ) : recentChats.length > 0 ? (
                recentChats.map((chat) => (
                  <NavLink
                    key={chat.id}
                    to={`/chat?conversation=${chat.id}`}
                    className={clsx(
                      "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all",
                      pathname.includes(chat.id)
                        ? "bg-white/10 text-white"
                        : "text-gray-400 hover:bg-white/5 hover:text-gray-300"
                    )}
                  >
                    <MessageSquare className="h-4 w-4 flex-shrink-0" />
                    <span className="truncate">{chat.title || chat.preview || 'New conversation'}</span>
                  </NavLink>
                ))
              ) : (
                <div className="px-3 py-4 text-center">
                  <MessageSquare className="h-8 w-8 text-gray-600 mx-auto mb-2" />
                  <p className="text-xs text-gray-500">No recent chats</p>
                  <button
                    onClick={handleNewChat}
                    className="text-xs text-purple-400 hover:text-purple-300 mt-1"
                  >
                    Start a conversation
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Section */}
      <div className="mt-auto border-t border-white/10">
        {/* Streak Counter - Using cached data */}
        <div className="p-3">
          <CompactStreak stats={gamificationStats} />
        </div>

        {/* Upgrade Banner (show only for free/basic tiers) */}
        {(subscriptionTier === "free" || subscriptionTier === "basic") && (
          <div className="p-3">
            <NavLink
              to="/tokens"
              className="block p-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20 rounded-xl hover:from-purple-500/20 hover:to-pink-500/20 transition-all"
            >
              <div className="flex items-center gap-2 mb-1">
                <Crown className="h-4 w-4 text-purple-400" />
                <span className="text-sm font-medium text-white">Upgrade to Premium</span>
              </div>
              <p className="text-xs text-gray-400">Unlock auto-posting & unlimited features</p>
            </NavLink>
          </div>
        )}

        {/* Settings & Help */}
        <nav className="p-3 space-y-1">
          {secondaryNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.to;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all",
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-gray-400 hover:bg-white/5 hover:text-gray-300"
                )}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* User Profile with Enhanced Dropdown - Pass cached data */}
        <div className="p-3 border-t border-white/10">
          <ProfileDropdown
            showSettingsModal={() => setShowSettings(true)}
            cachedSubscriptionData={subscriptionData}
            cachedPlatformCount={connectedPlatforms}
          />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </aside>
  );
}

export default Sidebar;
