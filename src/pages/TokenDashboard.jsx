import { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { 
  Coins, 
  Flame, 
  TrendingUp, 
  Calendar, 
  Zap, 
  Crown, 
  Building2,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  Sparkles,
  Shield,
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import useAuthStore from '../store/authStore';

const TIER_COLORS = {
  free: 'from-gray-500 to-gray-600',
  basic: 'from-blue-500 to-blue-600',
  premium: 'from-purple-500 to-pink-500',
  agency: 'from-amber-500 to-orange-500',
};

const TIER_ICONS = {
  free: Shield,
  basic: Zap,
  premium: Crown,
  agency: Building2,
};

const TIER_FEATURES = {
  free: {
    posts: '3/day',
    platforms: '2',
    aiGen: '5/day',
    autoPost: false,
    flows: '0',
  },
  basic: {
    posts: '5/day',
    platforms: '3',
    aiGen: '10/day',
    autoPost: false,
    flows: '0',
  },
  premium: {
    posts: 'Unlimited',
    platforms: 'All',
    aiGen: 'Unlimited',
    autoPost: true,
    flows: '5',
  },
  agency: {
    posts: 'Unlimited',
    platforms: 'All',
    aiGen: 'Unlimited',
    autoPost: true,
    flows: 'Unlimited',
  },
};

export default function TokenDashboard() {
  const { publicKey, connected } = useWallet();
  const { token } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [subscriptionData, setSubscriptionData] = useState(null);
  const [burnStats, setBurnStats] = useState(null);
  const [error, setError] = useState(null);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [selectedUpgrade, setSelectedUpgrade] = useState(null);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (token) {
      fetchSubscriptionData();
      fetchBurnStats();
    }
  }, [token]);

  const fetchSubscriptionData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/subscription/status`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSubscriptionData(data);
      } else {
        // Use default free tier data
        setSubscriptionData({
          tier: 'free',
          token_balance: 0,
          is_subscribed: false,
          subscription_active: false,
          posts_used_today: 0,
          posts_limit: 3,
          ai_generations_today: 0,
          ai_generations_limit: 5,
          credits_balance: 0,
          tokens_burned_total: 0,
          can_auto_post: false,
        });
      }
    } catch (err) {
      console.error('Error fetching subscription:', err);
      setError('Failed to load subscription data');
    } finally {
      setLoading(false);
    }
  };

  const fetchBurnStats = async () => {
    try {
      const response = await fetch(`${API_URL}/subscription/burn-stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setBurnStats(data);
      }
    } catch (err) {
      console.error('Error fetching burn stats:', err);
    }
  };

  const handleRefreshBalance = async () => {
    if (!publicKey) return;
    
    setRefreshing(true);
    try {
      const response = await fetch(`${API_URL}/subscription/refresh-balance`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          wallet_address: publicKey.toBase58(),
        }),
      });
      
      if (response.ok) {
        await fetchSubscriptionData();
      }
    } catch (err) {
      console.error('Error refreshing balance:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleUpgrade = async (tier) => {
    setSelectedUpgrade(tier);
    setShowUpgradeModal(true);
  };

  const confirmUpgrade = async () => {
    if (!selectedUpgrade || !publicKey) return;
    
    try {
      const response = await fetch(`${API_URL}/subscription/subscribe`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tier: selectedUpgrade,
          wallet_address: publicKey.toBase58(),
          auto_renew: true,
        }),
      });
      
      const data = await response.json();
      
      if (data.success) {
        await fetchSubscriptionData();
        setShowUpgradeModal(false);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Upgrade failed. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  const tier = subscriptionData?.tier || 'free';
  const TierIcon = TIER_ICONS[tier];
  const features = TIER_FEATURES[tier];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <Coins className="h-8 w-8 text-yellow-400" />
              Token Dashboard
            </h1>
            <p className="text-gray-400 mt-1">Manage your $SOCIAL tokens and subscription</p>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefreshBalance}
              disabled={refreshing || !connected}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg flex items-center gap-2 text-white transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <WalletMultiButton className="!bg-gradient-to-r from-purple-500 to-pink-500 !rounded-lg" />
          </div>
        </div>

        {/* Main Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Token Balance Card */}
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400 text-sm">Your Balance</span>
              <Coins className="h-5 w-5 text-yellow-400" />
            </div>
            <div className="text-4xl font-bold text-white mb-2">
              {subscriptionData?.token_balance?.toLocaleString() || 0}
              <span className="text-lg text-gray-400 ml-2">$SOCIAL</span>
            </div>
            <a 
              href="https://jup.ag/swap/SOL-SOCIAL"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-purple-400 hover:text-purple-300 text-sm mt-2"
            >
              Buy on Jupiter <ExternalLink className="h-3 w-3" />
            </a>
          </div>

          {/* Current Tier Card */}
          <div className={`bg-gradient-to-br ${TIER_COLORS[tier]} rounded-2xl p-6 relative overflow-hidden`}>
            <div className="absolute top-0 right-0 opacity-10">
              <TierIcon className="h-32 w-32 -mt-4 -mr-4" />
            </div>
            <div className="relative">
              <div className="flex items-center gap-2 mb-4">
                <TierIcon className="h-5 w-5 text-white" />
                <span className="text-white/80 text-sm">Current Tier</span>
              </div>
              <div className="text-3xl font-bold text-white capitalize mb-2">
                {tier}
              </div>
              {subscriptionData?.subscription_active && (
                <div className="flex items-center gap-2 text-white/80 text-sm">
                  <CheckCircle2 className="h-4 w-4" />
                  Active Subscription
                </div>
              )}
            </div>
          </div>

          {/* Renewal / Upgrade Card */}
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-4">
              <span className="text-gray-400 text-sm">
                {subscriptionData?.is_subscribed ? 'Next Renewal' : 'Upgrade Available'}
              </span>
              <Calendar className="h-5 w-5 text-blue-400" />
            </div>
            
            {subscriptionData?.is_subscribed && subscriptionData?.renews_at ? (
              <>
                <div className="text-2xl font-bold text-white mb-2">
                  {new Date(subscriptionData.renews_at).toLocaleDateString()}
                </div>
                <div className="text-sm text-gray-400">
                  {subscriptionData.days_until_renewal} days remaining
                </div>
                {subscriptionData.auto_renew && (
                  <div className="flex items-center gap-2 text-green-400 text-sm mt-2">
                    <CheckCircle2 className="h-4 w-4" />
                    Auto-renewal enabled
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="text-xl font-bold text-white mb-3">
                  Unlock Premium Features
                </div>
                <button
                  onClick={() => handleUpgrade('premium')}
                  className="w-full py-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
                >
                  Upgrade Now
                </button>
              </>
            )}
          </div>
        </div>

        {/* Usage Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Daily Usage */}
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-400" />
              Today's Usage
            </h3>
            
            <div className="space-y-4">
              {/* Posts */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Posts</span>
                  <span className="text-white">
                    {subscriptionData?.posts_used_today || 0} / {subscriptionData?.posts_limit === -1 ? '∞' : subscriptionData?.posts_limit || 3}
                  </span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all"
                    style={{ 
                      width: subscriptionData?.posts_limit === -1 
                        ? '10%' 
                        : `${Math.min(100, ((subscriptionData?.posts_used_today || 0) / (subscriptionData?.posts_limit || 3)) * 100)}%` 
                    }}
                  />
                </div>
              </div>
              
              {/* AI Generations */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">AI Generations</span>
                  <span className="text-white">
                    {subscriptionData?.ai_generations_today || 0} / {subscriptionData?.ai_generations_limit === -1 ? '∞' : subscriptionData?.ai_generations_limit || 5}
                  </span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all"
                    style={{ 
                      width: subscriptionData?.ai_generations_limit === -1 
                        ? '10%' 
                        : `${Math.min(100, ((subscriptionData?.ai_generations_today || 0) / (subscriptionData?.ai_generations_limit || 5)) * 100)}%` 
                    }}
                  />
                </div>
              </div>
              
              {/* Credits */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Credits Balance</span>
                  <span className="text-white">{subscriptionData?.credits_balance || 0}</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Token Burns */}
          <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Flame className="h-5 w-5 text-orange-400" />
              Token Burns (Deflationary)
            </h3>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                <span className="text-gray-400">Your Total Burns</span>
                <span className="text-xl font-bold text-orange-400">
                  {subscriptionData?.tokens_burned_total?.toLocaleString() || 0} $SOCIAL
                </span>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                <span className="text-gray-400">Platform Total Burns</span>
                <span className="text-xl font-bold text-red-400">
                  {burnStats?.total_burned?.toLocaleString() || 0} $SOCIAL
                </span>
              </div>
              
              <div className="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                <span className="text-gray-400">Unique Burners</span>
                <span className="text-xl font-bold text-purple-400">
                  {burnStats?.unique_burners?.toLocaleString() || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Tier Comparison */}
        <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
          <h3 className="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-400" />
            Subscription Tiers
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Free Tier */}
            <TierCard 
              name="Free"
              price="$0"
              requirement="No wallet needed"
              features={TIER_FEATURES.free}
              current={tier === 'free'}
              gradient={TIER_COLORS.free}
              icon={Shield}
            />
            
            {/* Basic Tier */}
            <TierCard 
              name="Basic"
              price="Hold 100 $SOCIAL"
              requirement="One-time purchase"
              features={TIER_FEATURES.basic}
              current={tier === 'basic'}
              gradient={TIER_COLORS.basic}
              icon={Zap}
              onUpgrade={() => handleUpgrade('basic')}
              canUpgrade={tier === 'free' && connected}
            />
            
            {/* Premium Tier */}
            <TierCard 
              name="Premium"
              price="25 $SOCIAL/mo"
              requirement="Hold 100 + burn monthly"
              features={TIER_FEATURES.premium}
              current={tier === 'premium'}
              gradient={TIER_COLORS.premium}
              icon={Crown}
              popular
              onUpgrade={() => handleUpgrade('premium')}
              canUpgrade={['free', 'basic'].includes(tier) && connected}
            />
            
            {/* Agency Tier */}
            <TierCard 
              name="Agency"
              price="100 $SOCIAL/mo"
              requirement="Hold 500 + burn monthly"
              features={TIER_FEATURES.agency}
              current={tier === 'agency'}
              gradient={TIER_COLORS.agency}
              icon={Building2}
              onUpgrade={() => handleUpgrade('agency')}
              canUpgrade={['free', 'basic', 'premium'].includes(tier) && connected}
            />
          </div>
        </div>

        {/* Auto-Post Status */}
        {!subscriptionData?.can_auto_post && (
          <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 rounded-2xl p-6 border border-purple-500/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-500/20 rounded-full">
                  <Clock className="h-6 w-6 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Unlock Automatic Posting</h3>
                  <p className="text-gray-400 text-sm">
                    Upgrade to Premium to have your posts automatically published at scheduled times
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleUpgrade('premium')}
                className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white font-medium hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                Upgrade to Premium
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        {/* Upgrade Modal */}
        {showUpgradeModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-800 rounded-2xl p-6 max-w-md w-full border border-white/10">
              <h3 className="text-xl font-bold text-white mb-4">
                Upgrade to {selectedUpgrade?.charAt(0).toUpperCase() + selectedUpgrade?.slice(1)}
              </h3>
              
              <div className="bg-white/5 rounded-lg p-4 mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-gray-400">Monthly Burn</span>
                  <span className="text-white font-bold">
                    {selectedUpgrade === 'premium' ? '25' : selectedUpgrade === 'agency' ? '100' : '0'} $SOCIAL
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Your Balance</span>
                  <span className="text-white font-bold">{subscriptionData?.token_balance || 0} $SOCIAL</span>
                </div>
              </div>
              
              {error && (
                <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-4 flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-red-400" />
                  <span className="text-red-400 text-sm">{error}</span>
                </div>
              )}
              
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowUpgradeModal(false);
                    setError(null);
                  }}
                  className="flex-1 py-3 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmUpgrade}
                  className="flex-1 py-3 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white font-medium hover:opacity-90 transition-opacity"
                >
                  Confirm Upgrade
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Tier Card Component
function TierCard({ name, price, requirement, features, current, gradient, icon: Icon, popular, onUpgrade, canUpgrade }) {
  return (
    <div className={`relative rounded-xl p-5 border ${current ? 'border-purple-500 bg-purple-500/10' : 'border-white/10 bg-white/5'}`}>
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full text-xs font-bold text-white">
          POPULAR
        </div>
      )}
      
      <div className={`inline-flex p-2 rounded-lg bg-gradient-to-br ${gradient} mb-3`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
      
      <h4 className="text-lg font-bold text-white">{name}</h4>
      <p className="text-sm text-purple-400 font-medium">{price}</p>
      <p className="text-xs text-gray-500 mb-4">{requirement}</p>
      
      <ul className="space-y-2 text-sm">
        <li className="flex justify-between">
          <span className="text-gray-400">Posts</span>
          <span className="text-white">{features.posts}</span>
        </li>
        <li className="flex justify-between">
          <span className="text-gray-400">Platforms</span>
          <span className="text-white">{features.platforms}</span>
        </li>
        <li className="flex justify-between">
          <span className="text-gray-400">AI Gen</span>
          <span className="text-white">{features.aiGen}</span>
        </li>
        <li className="flex justify-between">
          <span className="text-gray-400">Auto-Post</span>
          <span className={features.autoPost ? 'text-green-400' : 'text-gray-500'}>
            {features.autoPost ? '✓' : '✗'}
          </span>
        </li>
        <li className="flex justify-between">
          <span className="text-gray-400">Flows</span>
          <span className="text-white">{features.flows}</span>
        </li>
      </ul>
      
      {current ? (
        <div className="mt-4 py-2 text-center text-sm font-medium text-purple-400 border border-purple-500/50 rounded-lg">
          Current Plan
        </div>
      ) : canUpgrade ? (
        <button
          onClick={onUpgrade}
          className="mt-4 w-full py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white text-sm font-medium transition-colors"
        >
          Upgrade
        </button>
      ) : null}
    </div>
  );
}
