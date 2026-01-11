import { useMemo } from 'react';
import { ConnectionProvider, WalletProvider as SolanaWalletProvider } from '@solana/wallet-adapter-react';
import { WalletModalProvider } from '@solana/wallet-adapter-react-ui';
import { SOLANA_RPC_ENDPOINT, getWalletAdapters } from './solana';

// Import wallet adapter styles
import '@solana/wallet-adapter-react-ui/styles.css';

export function WalletProvider({ children }) {
  // Initialize wallets - memoized to prevent re-initialization
  const wallets = useMemo(() => getWalletAdapters(), []);

  return (
    <ConnectionProvider endpoint={SOLANA_RPC_ENDPOINT}>
      <SolanaWalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>
          {children}
        </WalletModalProvider>
      </SolanaWalletProvider>
    </ConnectionProvider>
  );
}

export default WalletProvider;

