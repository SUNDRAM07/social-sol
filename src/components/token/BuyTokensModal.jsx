import { useState } from 'react';
import { 
  X, 
  ExternalLink, 
  Coins, 
  ArrowRight,
  Copy,
  Check,
  AlertCircle
} from 'lucide-react';

// Jupiter aggregator URL template
const JUPITER_SWAP_URL = "https://jup.ag/swap/SOL-";

// Raydium swap URL template
const RAYDIUM_SWAP_URL = "https://raydium.io/swap/?inputMint=So11111111111111111111111111111111111111112&outputMint=";

// Placeholder token mint - will be replaced with actual $SOCIAL mint address
const SOCIAL_TOKEN_MINT = "SoCiaLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";

export default function BuyTokensModal({ isOpen, onClose, tokenMint = SOCIAL_TOKEN_MINT, currentBalance = 0, targetAmount = 100 }) {
  const [copied, setCopied] = useState(false);
  const [selectedDex, setSelectedDex] = useState('jupiter');

  if (!isOpen) return null;

  const tokensNeeded = Math.max(0, targetAmount - currentBalance);
  
  const jupiterUrl = `${JUPITER_SWAP_URL}${tokenMint}`;
  const raydiumUrl = `${RAYDIUM_SWAP_URL}${tokenMint}`;
  
  const handleCopyMint = () => {
    navigator.clipboard.writeText(tokenMint);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleOpenDex = () => {
    const url = selectedDex === 'jupiter' ? jupiterUrl : raydiumUrl;
    window.open(url, '_blank');
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-2xl max-w-lg w-full border border-white/10 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <Coins className="h-6 w-6 text-yellow-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Buy $SOCIAL Tokens</h2>
                <p className="text-gray-400 text-sm">Unlock platform features</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Current Status */}
          <div className="bg-white/5 rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
              <span className="text-gray-400">Your Balance</span>
              <span className="text-xl font-bold text-white">{currentBalance.toLocaleString()} $SOCIAL</span>
            </div>
            <div className="flex justify-between items-center mb-3">
              <span className="text-gray-400">Target</span>
              <span className="text-white">{targetAmount.toLocaleString()} $SOCIAL</span>
            </div>
            {tokensNeeded > 0 && (
              <div className="flex justify-between items-center pt-3 border-t border-white/10">
                <span className="text-purple-400 font-medium">Tokens Needed</span>
                <span className="text-xl font-bold text-purple-400">{tokensNeeded.toLocaleString()} $SOCIAL</span>
              </div>
            )}
          </div>

          {/* Token Contract */}
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Token Contract Address</label>
            <div className="flex items-center gap-2 bg-white/5 rounded-lg p-3">
              <code className="text-xs text-purple-400 flex-1 truncate">{tokenMint}</code>
              <button
                onClick={handleCopyMint}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                title="Copy address"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-400" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          {/* DEX Selection */}
          <div>
            <label className="text-sm text-gray-400 mb-2 block">Select Exchange</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setSelectedDex('jupiter')}
                className={`p-4 rounded-xl border-2 transition-all ${
                  selectedDex === 'jupiter'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="text-lg font-bold text-white mb-1">Jupiter</div>
                <div className="text-xs text-gray-400">Best rates aggregator</div>
              </button>
              <button
                onClick={() => setSelectedDex('raydium')}
                className={`p-4 rounded-xl border-2 transition-all ${
                  selectedDex === 'raydium'
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-white/10 bg-white/5 hover:border-white/20'
                }`}
              >
                <div className="text-lg font-bold text-white mb-1">Raydium</div>
                <div className="text-xs text-gray-400">Direct AMM swap</div>
              </button>
            </div>
          </div>

          {/* Info Box */}
          <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
            <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-200">
              <p className="font-medium mb-1">How it works:</p>
              <ol className="list-decimal list-inside space-y-1 text-blue-300">
                <li>Click "Buy on {selectedDex === 'jupiter' ? 'Jupiter' : 'Raydium'}"</li>
                <li>Connect your wallet on the exchange</li>
                <li>Swap SOL for $SOCIAL tokens</li>
                <li>Return here and refresh your balance</li>
              </ol>
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={handleOpenDex}
            className="w-full py-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl text-white font-bold text-lg hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
          >
            Buy on {selectedDex === 'jupiter' ? 'Jupiter' : 'Raydium'}
            <ExternalLink className="h-5 w-5" />
          </button>

          {/* Quick Links */}
          <div className="flex items-center justify-center gap-4 text-sm">
            <a 
              href={jupiterUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-purple-400 transition-colors flex items-center gap-1"
            >
              Jupiter <ExternalLink className="h-3 w-3" />
            </a>
            <span className="text-gray-600">|</span>
            <a 
              href={raydiumUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-purple-400 transition-colors flex items-center gap-1"
            >
              Raydium <ExternalLink className="h-3 w-3" />
            </a>
            <span className="text-gray-600">|</span>
            <a 
              href={`https://solscan.io/token/${tokenMint}`}
              target="_blank" 
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-purple-400 transition-colors flex items-center gap-1"
            >
              Solscan <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
