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

            // Actions
            setUser: (user) => set({ user, isAuthenticated: !!user }),

            setToken: (token) => set({ token }),

            setLoading: (isLoading) => set({ isLoading }),

            setError: (error) => set({ error }),

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
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);

export { useAuthStore };
export default useAuthStore;
