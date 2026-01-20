import { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { Wallet, X, Sparkles, Gift } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';

/**
 * WalletConnectionBanner - Shows a dismissible banner prompting wallet connection
 * Appears at the top of the main content area
 */
export default function WalletConnectionBanner() {
  const { connected, publicKey } = useWallet();
  const { user, linkWallet } = useAuthStore();
  const [dismissed, setDismissed] = useState(false);
  const [isLinking, setIsLinking] = useState(false);

  // Check if user has already dismissed this session
  useEffect(() => {
    const wasDismissed = sessionStorage.getItem('wallet_banner_dismissed');
    if (wasDismissed) {
      setDismissed(true);
    }
  }, []);

  // Auto-link wallet when connected and not yet linked
  useEffect(() => {
    const autoLink = async () => {
      if (connected && publicKey && user && !user.wallet_address && !isLinking) {
        setIsLinking(true);
        try {
          await linkWallet(publicKey.toBase58());
        } catch (e) {
          console.error('Auto-link failed:', e);
        }
        setIsLinking(false);
      }
    };
    autoLink();
  }, [connected, publicKey, user, linkWallet, isLinking]);

  const handleDismiss = () => {
    setDismissed(true);
    sessionStorage.setItem('wallet_banner_dismissed', 'true');
  };

  // Don't show if:
  // - User has connected wallet
  // - User has wallet linked to account
  // - Banner was dismissed
  if ((connected && publicKey) || user?.wallet_address || dismissed) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-purple-600/20 via-pink-600/20 to-purple-600/20 border-b border-purple-500/30 px-4 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <Gift className="h-5 w-5 text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-medium text-white">
              Connect your wallet to unlock more features!
            </p>
            <p className="text-xs text-gray-400">
              Hold $SOCIAL tokens for unlimited posts, auto-scheduling, and more
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <WalletMultiButton className="!bg-gradient-to-r from-purple-500 to-pink-500 !rounded-lg !py-2 !px-4 !text-sm !font-medium" />
          
          <button
            onClick={handleDismiss}
            className="p-2 text-gray-400 hover:text-white transition-colors"
            title="Dismiss"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * WalletStatusIndicator - Small indicator showing wallet status
 * Can be placed in header/sidebar
 */
export function WalletStatusIndicator() {
  const { connected, publicKey } = useWallet();
  const { user } = useAuthStore();

  if (!connected || !publicKey) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
        <Wallet className="h-4 w-4 text-yellow-400" />
        <span className="text-xs text-yellow-300">Wallet not connected</span>
      </div>
    );
  }

  const shortAddress = `${publicKey.toBase58().slice(0, 4)}...${publicKey.toBase58().slice(-4)}`;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-green-500/10 rounded-lg border border-green-500/30">
      <Wallet className="h-4 w-4 text-green-400" />
      <span className="text-xs text-green-300">{shortAddress}</span>
      {user?.tier && user.tier !== 'free' && (
        <span className="px-2 py-0.5 bg-purple-500/30 rounded text-xs text-purple-300 font-medium uppercase">
          {user.tier}
        </span>
      )}
    </div>
  );
}
