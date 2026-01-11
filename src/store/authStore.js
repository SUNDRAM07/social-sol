import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiUrl } from '../lib/api.js';

const useAuthStore = create(
    persist(
        (set, get) => ({
            // State
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            walletAddress: null, // Connected Solana wallet

            // Actions
            setUser: (user) => set({ user, isAuthenticated: !!user }),

            setToken: (token) => set({ token }),

            setLoading: (isLoading) => set({ isLoading }),

            setError: (error) => set({ error }),

            setWalletAddress: (walletAddress) => set({ walletAddress }),

            // Wallet-based login
            loginWithWallet: async (walletAddress, signMessage) => {
                set({ isLoading: true, error: null });

                try {
                    console.log('🔐 AuthStore - Wallet login started for:', walletAddress);

                    // Step 1: Get a nonce/message to sign from backend
                    const nonceResponse = await fetch(apiUrl('/auth/wallet/nonce'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ wallet_address: walletAddress }),
                    });

                    if (!nonceResponse.ok) {
                        throw new Error('Failed to get authentication message');
                    }

                    const { message, nonce } = await nonceResponse.json();

                    // Step 2: Sign the message with wallet
                    const encodedMessage = new TextEncoder().encode(message);
                    const signature = await signMessage(encodedMessage);
                    
                    // Convert signature to base58
                    const bs58 = await import('bs58');
                    const signatureBase58 = bs58.default.encode(signature);

                    // Step 3: Verify signature and get JWT
                    const verifyResponse = await fetch(apiUrl('/auth/wallet/verify'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            wallet_address: walletAddress,
                            signature: signatureBase58,
                            nonce: nonce,
                        }),
                    });

                    if (!verifyResponse.ok) {
                        const errorData = await verifyResponse.json();
                        throw new Error(errorData.detail || 'Wallet verification failed');
                    }

                    const data = await verifyResponse.json();

                    set({
                        user: data.user,
                        token: data.access_token,
                        walletAddress: walletAddress,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });

                    console.log('✅ AuthStore - Wallet login successful');
                    return { success: true, user: data.user };
                } catch (error) {
                    console.error('❌ AuthStore - Wallet login failed:', error);
                    set({
                        user: null,
                        token: null,
                        walletAddress: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: error.message,
                    });
                    return { success: false, error: error.message };
                }
            },

            // Link wallet to existing account
            linkWallet: async (walletAddress, signMessage) => {
                const { token } = get();
                if (!token) {
                    return { success: false, error: 'Not authenticated' };
                }

                set({ isLoading: true, error: null });

                try {
                    // Get nonce
                    const nonceResponse = await fetch(apiUrl('/auth/wallet/link/nonce'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`,
                        },
                        body: JSON.stringify({ wallet_address: walletAddress }),
                    });

                    if (!nonceResponse.ok) {
                        throw new Error('Failed to get link message');
                    }

                    const { message, nonce } = await nonceResponse.json();

                    // Sign message
                    const encodedMessage = new TextEncoder().encode(message);
                    const signature = await signMessage(encodedMessage);
                    const bs58 = await import('bs58');
                    const signatureBase58 = bs58.default.encode(signature);

                    // Verify and link
                    const linkResponse = await fetch(apiUrl('/auth/wallet/link'), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`,
                        },
                        body: JSON.stringify({
                            wallet_address: walletAddress,
                            signature: signatureBase58,
                            nonce: nonce,
                        }),
                    });

                    if (!linkResponse.ok) {
                        const errorData = await linkResponse.json();
                        throw new Error(errorData.detail || 'Failed to link wallet');
                    }

                    const data = await linkResponse.json();
                    set({
                        user: data.user,
                        walletAddress: walletAddress,
                        isLoading: false,
                    });

                    return { success: true };
                } catch (error) {
                    set({ isLoading: false, error: error.message });
                    return { success: false, error: error.message };
                }
            },

            // Google OAuth login (existing)
            login: async (googleToken) => {
                set({ isLoading: true, error: null });

                try {
                    console.log('🔍 AuthStore - Google token received:', googleToken);
                    console.log('🔍 AuthStore - Token type:', typeof googleToken);
                    console.log('🔍 AuthStore - Token length:', googleToken ? googleToken.length : 'undefined');

                    if (!googleToken) {
                        throw new Error('No Google token provided');
                    }

                    const authUrl = apiUrl('/auth/google');
                    console.log('🔍 AuthStore - Calling API:', authUrl);

                    const response = await fetch(authUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ token: googleToken }),
                    });

                    if (!response.ok) {
                        let errorMessage = 'Authentication failed';
                        try {
                            const errorData = await response.json();
                            errorMessage = errorData.detail || errorData.message || errorMessage;
                        } catch (e) {
                            // If response is not JSON, use status text
                            errorMessage = response.statusText || errorMessage;
                        }
                        throw new Error(errorMessage);
                    }

                    const data = await response.json();


                    set({
                        user: data.user,
                        token: data.access_token,
                        isAuthenticated: true,
                        isLoading: false,
                        error: null,
                    });

                    return { success: true, user: data.user };
                } catch (error) {
                    set({
                        user: null,
                        token: null,
                        isAuthenticated: false,
                        isLoading: false,
                        error: error.message,
                    });
                    return { success: false, error: error.message };
                }
            },

            logout: () => {
                set({
                    user: null,
                    token: null,
                    walletAddress: null,
                    isAuthenticated: false,
                    isLoading: false,
                    error: null,
                });
            },

            getCurrentUser: async () => {
                const { token } = get();
                if (!token) return null;

                set({ isLoading: true });

                try {
                    const response = await fetch(apiUrl('/auth/me'), {
                        headers: {
                            'Authorization': `Bearer ${token}`,
                        },
                    });

                    if (!response.ok) {
                        throw new Error('Failed to get user info');
                    }

                    const user = await response.json();
                    set({ user, isLoading: false });
                    return user;
                } catch (error) {
                    set({ isLoading: false, error: error.message });
                    return null;
                }
            },

            clearError: () => set({ error: null }),

            // Force clear all auth data (including localStorage)
            forceLogout: () => {
                console.log('Auth Store - Force logout, clearing all data');
                localStorage.removeItem('auth-storage');
                set({
                    user: null,
                    token: null,
                    walletAddress: null,
                    isAuthenticated: false,
                    isLoading: false,
                    error: null,
                });
            },
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                walletAddress: state.walletAddress,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

export { useAuthStore };
export default useAuthStore;
