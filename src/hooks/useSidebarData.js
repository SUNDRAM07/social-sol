/**
 * useSidebarData - Centralized hook for sidebar data fetching
 * 
 * Optimizations:
 * - Batches all API calls with Promise.all
 * - Caches results to prevent duplicate fetches
 * - Uses startTransition for non-blocking updates
 * - Provides loading states for skeleton UI
 */

import { useState, useEffect, useCallback, useTransition, useRef } from 'react';
import { useAuthStore } from '../store/authStore';

// Simple in-memory cache with TTL
const cache = {
  data: {},
  timestamps: {},
  TTL: 60000, // 1 minute cache
  
  get(key) {
    const timestamp = this.timestamps[key];
    if (timestamp && Date.now() - timestamp < this.TTL) {
      return this.data[key];
    }
    return null;
  },
  
  set(key, value) {
    this.data[key] = value;
    this.timestamps[key] = Date.now();
  },
  
  clear() {
    this.data = {};
    this.timestamps = {};
  }
};

export function useSidebarData() {
  const { token } = useAuthStore();
  const [isPending, startTransition] = useTransition();
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const fetchingRef = useRef(false);
  
  const [data, setData] = useState({
    subscriptionTier: 'free',
    subscriptionData: null,
    recentChats: [],
    connectedPlatforms: 0,
    platformsData: {},
    gamificationStats: null,
  });

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const fetchAllData = useCallback(async (forceRefresh = false) => {
    if (!token || fetchingRef.current) return;
    
    // Check cache first (unless force refresh)
    if (!forceRefresh) {
      const cachedData = cache.get('sidebarData');
      if (cachedData) {
        setData(cachedData);
        setIsInitialLoad(false);
        return;
      }
    }

    fetchingRef.current = true;

    try {
      // Batch all API calls with Promise.allSettled (won't fail if one fails)
      const [
        subscriptionRes,
        chatsRes,
        platformsRes,
        gamificationRes
      ] = await Promise.allSettled([
        fetch(`${API_URL}/subscription/status`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        fetch(`${API_URL}/chat/conversations?limit=5`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        fetch(`${API_URL}/social/connected`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
        fetch(`${API_URL}/gamification/stats`, {
          headers: { 'Authorization': `Bearer ${token}` },
        }),
      ]);

      // Parse responses safely
      const parseResponse = async (result) => {
        if (result.status === 'fulfilled' && result.value.ok) {
          try {
            return await result.value.json();
          } catch {
            return null;
          }
        }
        return null;
      };

      const [
        subscriptionData,
        chatsData,
        platformsData,
        gamificationData
      ] = await Promise.all([
        parseResponse(subscriptionRes),
        parseResponse(chatsRes),
        parseResponse(platformsRes),
        parseResponse(gamificationRes),
      ]);

      const newData = {
        subscriptionTier: subscriptionData?.tier || 'free',
        subscriptionData: subscriptionData || null,
        recentChats: chatsData?.conversations || [],
        connectedPlatforms: platformsData?.platforms 
          ? Object.values(platformsData.platforms).filter(Boolean).length 
          : 0,
        platformsData: platformsData?.platforms || {},
        gamificationStats: gamificationData || null,
      };

      // Use startTransition for non-blocking state update
      startTransition(() => {
        setData(newData);
        setIsInitialLoad(false);
      });

      // Cache the result
      cache.set('sidebarData', newData);

    } catch (error) {
      console.error('Error fetching sidebar data:', error);
      setIsInitialLoad(false);
    } finally {
      fetchingRef.current = false;
    }
  }, [token, API_URL]);

  // Initial fetch
  useEffect(() => {
    if (token) {
      fetchAllData();
    }
  }, [token, fetchAllData]);

  // Refresh function for manual refresh
  const refresh = useCallback(() => {
    cache.clear();
    fetchAllData(true);
  }, [fetchAllData]);

  return {
    ...data,
    isLoading: isInitialLoad,
    isPending,
    refresh,
  };
}

// Export cache clear for logout
export function clearSidebarCache() {
  cache.clear();
}

export default useSidebarData;
