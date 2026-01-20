import { useState, useEffect } from 'react';
import { Flame, Trophy, Zap, TrendingUp } from 'lucide-react';
import { fetchWithAuth } from '../../utils/api';

/**
 * StreakCounter - Shows user's posting streak and stats
 * Compact version for sidebar, detailed version for dashboard
 */
export default function StreakCounter({ variant = 'compact' }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await fetchWithAuth('/gamification/stats');
        setStats(data);
      } catch (e) {
        console.error('Failed to fetch gamification stats:', e);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStats();
    
    // Refresh every 5 minutes
    const interval = setInterval(fetchStats, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse bg-white/5 rounded-lg p-3 h-16" />
    );
  }

  if (!stats) {
    return null;
  }

  if (variant === 'compact') {
    return (
      <div className="bg-gradient-to-r from-orange-500/10 to-red-500/10 rounded-xl p-3 border border-orange-500/20">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${stats.current_streak > 0 ? 'bg-orange-500/20' : 'bg-gray-500/20'}`}>
            <Flame className={`w-5 h-5 ${stats.current_streak > 0 ? 'text-orange-400' : 'text-gray-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-1.5">
              <span className="text-xl font-bold text-white">
                {stats.current_streak}
              </span>
              <span className="text-xs text-gray-400">day streak</span>
            </div>
            <p className="text-xs text-gray-500 truncate">
              {stats.total_posts} total posts
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Detailed variant for dashboard
  return (
    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Flame className="w-5 h-5 text-orange-400" />
        Your Progress
      </h3>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Current Streak */}
        <div className="bg-gradient-to-br from-orange-500/20 to-red-500/20 rounded-xl p-4 border border-orange-500/30">
          <Flame className="w-8 h-8 text-orange-400 mb-2" />
          <p className="text-3xl font-bold text-white">{stats.current_streak}</p>
          <p className="text-sm text-gray-400">Day Streak</p>
        </div>

        {/* Total Posts */}
        <div className="bg-gradient-to-br from-blue-500/20 to-cyan-500/20 rounded-xl p-4 border border-blue-500/30">
          <TrendingUp className="w-8 h-8 text-blue-400 mb-2" />
          <p className="text-3xl font-bold text-white">{stats.total_posts}</p>
          <p className="text-sm text-gray-400">Total Posts</p>
        </div>

        {/* Level */}
        <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl p-4 border border-purple-500/30">
          <Zap className="w-8 h-8 text-purple-400 mb-2" />
          <p className="text-3xl font-bold text-white">Lvl {stats.level}</p>
          <p className="text-sm text-gray-400">{stats.xp_to_next_level} XP to next</p>
        </div>

        {/* Achievements */}
        <div className="bg-gradient-to-br from-yellow-500/20 to-amber-500/20 rounded-xl p-4 border border-yellow-500/30">
          <Trophy className="w-8 h-8 text-yellow-400 mb-2" />
          <p className="text-3xl font-bold text-white">{stats.achievements_count}</p>
          <p className="text-sm text-gray-400">Achievements</p>
        </div>
      </div>

      {/* Longest Streak */}
      <div className="text-center text-sm text-gray-400">
        🏆 Longest streak: <span className="text-white font-medium">{stats.longest_streak} days</span>
      </div>
    </div>
  );
}

/**
 * StreakMini - Very compact version for sidebar
 */
export function StreakMini() {
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await fetchWithAuth('/gamification/stats');
        setStreak(data.current_streak || 0);
      } catch (e) {
        console.error('Failed to fetch streak:', e);
      }
    };
    fetchStats();
  }, []);

  if (streak === 0) return null;

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-orange-500/10 rounded-full">
      <Flame className="w-3.5 h-3.5 text-orange-400" />
      <span className="text-xs font-medium text-orange-300">{streak}</span>
    </div>
  );
}
