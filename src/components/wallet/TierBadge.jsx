import { Sparkles, Zap, Crown } from 'lucide-react';
import { getTierFromBalance, TIER_THRESHOLDS } from '../../lib/solana';

const TIER_CONFIG = {
  FREE: {
    label: 'Free',
    icon: Sparkles,
    gradient: 'from-gray-500 to-gray-600',
    textColor: 'text-gray-300',
    borderColor: 'border-gray-500/30',
    bgColor: 'bg-gray-500/10',
  },
  PRO: {
    label: 'Pro',
    icon: Zap,
    gradient: 'from-purple-500 to-pink-500',
    textColor: 'text-purple-300',
    borderColor: 'border-purple-500/30',
    bgColor: 'bg-purple-500/10',
  },
  AGENCY: {
    label: 'Agency',
    icon: Crown,
    gradient: 'from-amber-500 to-orange-500',
    textColor: 'text-amber-300',
    borderColor: 'border-amber-500/30',
    bgColor: 'bg-amber-500/10',
  },
};

export function TierBadge({ balance = 0, showBalance = false, size = 'default' }) {
  const tier = getTierFromBalance(balance);
  const config = TIER_CONFIG[tier];
  const Icon = config.icon;

  const sizeClasses = {
    small: 'text-xs px-2 py-0.5 gap-1',
    default: 'text-sm px-3 py-1 gap-1.5',
    large: 'text-base px-4 py-2 gap-2',
  };

  const iconSizes = {
    small: 'w-3 h-3',
    default: 'w-4 h-4',
    large: 'w-5 h-5',
  };

  return (
    <div className="flex items-center gap-2">
      <div
        className={`inline-flex items-center rounded-full border ${config.borderColor} ${config.bgColor} ${sizeClasses[size]}`}
      >
        <div className={`bg-gradient-to-r ${config.gradient} rounded-full p-0.5`}>
          <Icon className={`${iconSizes[size]} text-white`} />
        </div>
        <span className={`font-medium ${config.textColor}`}>
          {config.label}
        </span>
      </div>
      
      {showBalance && (
        <span className="text-xs text-gray-500">
          {balance.toLocaleString()} $SOCIAL
        </span>
      )}
    </div>
  );
}

export function TierProgress({ balance = 0 }) {
  const tier = getTierFromBalance(balance);
  const nextTier = tier === 'FREE' ? 'PRO' : tier === 'PRO' ? 'AGENCY' : null;
  
  if (!nextTier) {
    return (
      <div className="text-center py-2">
        <p className="text-amber-400 text-sm font-medium">🎉 Maximum tier reached!</p>
      </div>
    );
  }

  const currentThreshold = TIER_THRESHOLDS[tier];
  const nextThreshold = TIER_THRESHOLDS[nextTier];
  const progress = ((balance - currentThreshold) / (nextThreshold - currentThreshold)) * 100;
  const tokensNeeded = nextThreshold - balance;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{balance.toLocaleString()} $SOCIAL</span>
        <span>{nextThreshold.toLocaleString()} for {nextTier}</span>
      </div>
      <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${TIER_CONFIG[nextTier].gradient} transition-all duration-500`}
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 text-center">
        {tokensNeeded.toLocaleString()} more tokens to unlock {nextTier}
      </p>
    </div>
  );
}

export default TierBadge;

