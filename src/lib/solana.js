import { WalletAdapterNetwork } from '@solana/wallet-adapter-base';
import { clusterApiUrl } from '@solana/web3.js';
import {
  PhantomWalletAdapter,
  SolflareWalletAdapter,
  BackpackWalletAdapter,
  CoinbaseWalletAdapter,
} from '@solana/wallet-adapter-wallets';

// Network configuration - use mainnet for production
export const SOLANA_NETWORK = WalletAdapterNetwork.Mainnet;

// RPC endpoint - using public endpoint, can upgrade to Helius/QuickNode later
export const SOLANA_RPC_ENDPOINT = clusterApiUrl(SOLANA_NETWORK);

// For production, you may want to use a private RPC:
// export const SOLANA_RPC_ENDPOINT = import.meta.env.VITE_SOLANA_RPC_URL || clusterApiUrl(SOLANA_NETWORK);

// $SOCIAL Token Configuration (placeholder - update with real token address)
export const SOCIAL_TOKEN_MINT = import.meta.env.VITE_SOCIAL_TOKEN_MINT || 'SoCiALtokenMintAddressHere111111111111111';

// Tier thresholds (in token units)
export const TIER_THRESHOLDS = {
  FREE: 0,
  PRO: 1000,
  AGENCY: 10000,
};

// Features per tier
export const TIER_FEATURES = {
  FREE: {
    postsPerDay: 3,
    platforms: 2,
    aiRequests: 10,
    scheduling: false,
    analytics: 'basic',
    multiProject: false,
  },
  PRO: {
    postsPerDay: -1, // unlimited
    platforms: -1,   // unlimited
    aiRequests: -1,  // unlimited
    scheduling: true,
    analytics: 'advanced',
    multiProject: false,
  },
  AGENCY: {
    postsPerDay: -1,
    platforms: -1,
    aiRequests: -1,
    scheduling: true,
    analytics: 'enterprise',
    multiProject: true,
    whiteLabel: true,
  },
};

// Initialize wallet adapters
export const getWalletAdapters = () => {
  return [
    new PhantomWalletAdapter(),
    new BackpackWalletAdapter(),
    new SolflareWalletAdapter(),
    new CoinbaseWalletAdapter(),
  ];
};

// Helper to determine tier from balance
export const getTierFromBalance = (balance) => {
  if (balance >= TIER_THRESHOLDS.AGENCY) return 'AGENCY';
  if (balance >= TIER_THRESHOLDS.PRO) return 'PRO';
  return 'FREE';
};

// Helper to check if feature is available for tier
export const isFeatureAvailable = (tier, feature) => {
  const tierFeatures = TIER_FEATURES[tier] || TIER_FEATURES.FREE;
  return tierFeatures[feature] !== undefined && tierFeatures[feature] !== false;
};

// Format wallet address for display (e.g., "7xKX...3bN9")
export const formatWalletAddress = (address, chars = 4) => {
  if (!address) return '';
  return `${address.slice(0, chars)}...${address.slice(-chars)}`;
};

