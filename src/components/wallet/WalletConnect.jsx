import { useWallet } from '@solana/wallet-adapter-react';
import { useWalletModal } from '@solana/wallet-adapter-react-ui';
import { Wallet, LogOut, Copy, Check, ExternalLink } from 'lucide-react';
import { useState } from 'react';
import { formatWalletAddress } from '../../lib/solana';

export function WalletConnect({ className = '', variant = 'default' }) {
  const { publicKey, connected, disconnect, connecting } = useWallet();
  const { setVisible } = useWalletModal();
  const [copied, setCopied] = useState(false);

  const handleConnect = () => {
    setVisible(true);
  };

  const handleCopy = async () => {
    if (publicKey) {
      await navigator.clipboard.writeText(publicKey.toBase58());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDisconnect = () => {
    disconnect();
  };

  const openExplorer = () => {
    if (publicKey) {
      window.open(`https://solscan.io/account/${publicKey.toBase58()}`, '_blank');
    }
  };

  // Compact variant for header/nav
  if (variant === 'compact') {
    if (connected && publicKey) {
      return (
        <div className={`flex items-center gap-2 ${className}`}>
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-500/20 to-cyan-500/20 border border-purple-500/30 hover:border-purple-400/50 transition-all"
          >
            <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            <span className="text-sm font-mono text-purple-300">
              {formatWalletAddress(publicKey.toBase58())}
            </span>
            {copied ? (
              <Check className="w-3.5 h-3.5 text-green-400" />
            ) : (
              <Copy className="w-3.5 h-3.5 text-purple-400" />
            )}
          </button>
          <button
            onClick={handleDisconnect}
            className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/20 transition-colors"
            title="Disconnect wallet"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      );
    }

    return (
      <button
        onClick={handleConnect}
        disabled={connecting}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-medium transition-all shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 disabled:opacity-50 ${className}`}
      >
        <Wallet className="w-4 h-4" />
        <span>{connecting ? 'Connecting...' : 'Connect Wallet'}</span>
      </button>
    );
  }

  // Full variant for login/settings pages
  if (connected && publicKey) {
    return (
      <div className={`space-y-4 ${className}`}>
        <div className="p-4 rounded-xl bg-gradient-to-br from-purple-500/10 to-cyan-500/10 border border-purple-500/20">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-400 animate-pulse" />
              <span className="text-sm text-green-400 font-medium">Connected</span>
            </div>
            <button
              onClick={handleDisconnect}
              className="text-sm text-red-400 hover:text-red-300 transition-colors flex items-center gap-1"
            >
              <LogOut className="w-3.5 h-3.5" />
              Disconnect
            </button>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center">
              <Wallet className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-gray-400 mb-0.5">Wallet Address</p>
              <p className="font-mono text-sm text-white truncate">
                {publicKey.toBase58()}
              </p>
            </div>
          </div>
          
          <div className="flex gap-2 mt-3">
            <button
              onClick={handleCopy}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-green-400" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  Copy Address
                </>
              )}
            </button>
            <button
              onClick={openExplorer}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              View on Solscan
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={handleConnect}
      disabled={connecting}
      className={`w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-cyan-600 hover:from-purple-500 hover:to-cyan-500 text-white font-semibold transition-all shadow-lg shadow-purple-500/25 hover:shadow-purple-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      <Wallet className="w-5 h-5" />
      <span>{connecting ? 'Connecting...' : 'Connect Solana Wallet'}</span>
    </button>
  );
}

export default WalletConnect;

