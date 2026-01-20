import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { Wallet, Lock, Coins, ArrowRight, Sparkles } from 'lucide-react';

/**
 * WalletGate - Requires wallet connection for certain features
 * 
 * Usage:
 * <WalletGate feature="auto_posting" fallback={<UpgradePrompt />}>
 *   <PremiumContent />
 * </WalletGate>
 * 
 * Or for full page blocking:
 * <WalletGate mode="full">
 *   <ProtectedPage />
 * </WalletGate>
 */

export default function WalletGate({ 
  children, 
  mode = "prompt",  // "prompt" shows connect UI inline, "full" blocks entire page
  feature = null,   // Feature name for messaging
  title = "Connect Wallet to Continue",
  description = "Connect your Solana wallet to access this feature and check your $SOCIAL token balance."
}) {
  const { connected, connecting, publicKey } = useWallet();

  // If wallet is connected, render children
  if (connected && publicKey) {
    return children;
  }

  // Full page blocking mode
  if (mode === "full") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-6">
        <div className="max-w-md w-full">
          <div className="bg-white/5 backdrop-blur-xl rounded-2xl p-8 border border-white/10 text-center">
            {/* Icon */}
            <div className="mx-auto w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-2xl flex items-center justify-center mb-6 shadow-lg shadow-purple-500/25">
              <Wallet className="h-10 w-10 text-white" />
            </div>

            {/* Title */}
            <h2 className="text-2xl font-bold text-white mb-3">{title}</h2>
            
            {/* Description */}
            <p className="text-gray-400 mb-6">{description}</p>

            {/* Features list */}
            <div className="bg-white/5 rounded-xl p-4 mb-6 text-left">
              <h4 className="text-sm font-medium text-gray-300 mb-3">With $SOCIAL tokens you can:</h4>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-purple-400" />
                  <span>Unlock unlimited AI generations</span>
                </li>
                <li className="flex items-center gap-2">
                  <Coins className="h-4 w-4 text-yellow-400" />
                  <span>Access automatic posting</span>
                </li>
                <li className="flex items-center gap-2">
                  <ArrowRight className="h-4 w-4 text-green-400" />
                  <span>Create unlimited campaigns</span>
                </li>
              </ul>
            </div>

            {/* Connect Button */}
            <div className="flex justify-center">
              <WalletMultiButton className="!bg-gradient-to-r from-purple-500 to-pink-500 !rounded-xl !py-3 !px-6 !text-base !font-medium" />
            </div>

            {connecting && (
              <p className="text-sm text-gray-500 mt-4">Connecting to wallet...</p>
            )}

            {/* Skip option for basic features */}
            <p className="text-xs text-gray-500 mt-6">
              Don't have tokens yet? You can still use basic features with limited access.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Inline prompt mode
  return (
    <div className="bg-white/5 backdrop-blur-lg rounded-xl p-6 border border-white/10">
      <div className="flex items-start gap-4">
        <div className="p-3 bg-purple-500/20 rounded-xl">
          <Lock className="h-6 w-6 text-purple-400" />
        </div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-white mb-1">
            {feature ? `Connect Wallet for ${feature}` : title}
          </h3>
          <p className="text-sm text-gray-400 mb-4">{description}</p>
          <WalletMultiButton className="!bg-gradient-to-r from-purple-500 to-pink-500 !rounded-lg !py-2 !px-4 !text-sm" />
        </div>
      </div>
    </div>
  );
}

/**
 * WalletRequired - HOC to wrap components that require wallet
 */
export function WalletRequired({ children, ...props }) {
  return (
    <WalletGate mode="full" {...props}>
      {children}
    </WalletGate>
  );
}

/**
 * useWalletRequired - Hook to check if wallet is required
 */
export function useWalletRequired() {
  const { connected, publicKey } = useWallet();
  
  return {
    isConnected: connected && !!publicKey,
    walletAddress: publicKey?.toBase58() || null,
    needsWallet: !connected || !publicKey,
  };
}
