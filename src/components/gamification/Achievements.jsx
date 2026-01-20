import { useState, useEffect } from 'react';
import { Trophy, Lock, Sparkles } from 'lucide-react';
import { fetchWithAuth } from '../../utils/api';

// All possible achievements (to show locked ones)
const ALL_ACHIEVEMENTS = {
  first_post: { name: "First Steps", description: "Created your first post", icon: "🎯", xp: 50 },
  streak_7: { name: "Weekly Warrior", description: "Posted for 7 days in a row", icon: "🔥", xp: 100 },
  streak_30: { name: "Monthly Master", description: "Posted for 30 days in a row", icon: "⭐", xp: 500 },
  posts_10: { name: "Content Creator", description: "Created 10 posts", icon: "📝", xp: 75 },
  posts_50: { name: "Prolific Poster", description: "Created 50 posts", icon: "🚀", xp: 200 },
  posts_100: { name: "Social Media Pro", description: "Created 100 posts", icon: "🏆", xp: 500 },
  platforms_3: { name: "Multi-Platform", description: "Connected 3 social platforms", icon: "🌐", xp: 100 },
  ai_master: { name: "AI Master", description: "Generated 50 AI captions", icon: "🤖", xp: 150 },
  early_bird: { name: "Early Bird", description: "Posted before 8 AM", icon: "🌅", xp: 25 },
  night_owl: { name: "Night Owl", description: "Posted after 10 PM", icon: "🦉", xp: 25 },
};

export default function Achievements({ showLocked = true }) {
  const [achievements, setAchievements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAchievements = async () => {
      try {
        const data = await fetchWithAuth('/gamification/achievements');
        setAchievements(data.achievements || []);
      } catch (e) {
        console.error('Failed to fetch achievements:', e);
      } finally {
        setLoading(false);
      }
    };
    fetchAchievements();
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse bg-white/5 rounded-xl p-6 h-48" />
    );
  }

  const earnedTypes = new Set(achievements.map(a => a.achievement_type));

  return (
    <div className="bg-white/5 backdrop-blur-lg rounded-2xl p-6 border border-white/10">
      <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
        <Trophy className="w-5 h-5 text-yellow-400" />
        Achievements
        <span className="text-sm font-normal text-gray-400">
          ({achievements.length}/{Object.keys(ALL_ACHIEVEMENTS).length})
        </span>
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        {Object.entries(ALL_ACHIEVEMENTS).map(([type, info]) => {
          const isEarned = earnedTypes.has(type);
          const earnedData = achievements.find(a => a.achievement_type === type);

          return (
            <div
              key={type}
              className={`relative group p-4 rounded-xl border text-center transition-all ${
                isEarned
                  ? 'bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border-yellow-500/30'
                  : 'bg-white/5 border-white/10 opacity-50'
              }`}
            >
              {/* Badge icon */}
              <div className="text-3xl mb-2">
                {isEarned ? info.icon : '🔒'}
              </div>

              {/* Name */}
              <p className={`text-sm font-medium mb-1 ${isEarned ? 'text-white' : 'text-gray-400'}`}>
                {info.name}
              </p>

              {/* XP */}
              <p className={`text-xs ${isEarned ? 'text-yellow-400' : 'text-gray-500'}`}>
                +{info.xp} XP
              </p>

              {/* Tooltip on hover */}
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 rounded-lg text-xs text-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10 border border-white/10">
                <p className="text-white font-medium">{info.name}</p>
                <p className="text-gray-400">{info.description}</p>
                {earnedData?.achieved_at && (
                  <p className="text-green-400 mt-1">
                    ✓ Earned {new Date(earnedData.achieved_at).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {achievements.length === 0 && (
        <div className="text-center py-4 text-gray-400">
          <Sparkles className="w-8 h-8 mx-auto mb-2 text-gray-500" />
          <p>Create your first post to start earning achievements!</p>
        </div>
      )}
    </div>
  );
}

/**
 * AchievementToast - Shows when a new achievement is earned
 */
export function AchievementToast({ achievement, onClose }) {
  if (!achievement) return null;

  return (
    <div className="fixed bottom-4 right-4 animate-slide-in-right z-50">
      <div className="bg-gradient-to-r from-yellow-500/90 to-amber-500/90 backdrop-blur-lg rounded-xl p-4 shadow-xl border border-yellow-400/50 max-w-sm">
        <div className="flex items-start gap-3">
          <div className="text-4xl">{achievement.icon}</div>
          <div className="flex-1">
            <p className="text-xs text-yellow-100 uppercase tracking-wide">Achievement Unlocked!</p>
            <p className="text-lg font-bold text-white">{achievement.name}</p>
            <p className="text-sm text-yellow-100">{achievement.description}</p>
            <p className="text-sm font-medium text-white mt-1">+{achievement.xp} XP</p>
          </div>
          <button
            onClick={onClose}
            className="text-yellow-100 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * AchievementBadge - Small badge for displaying earned achievement
 */
export function AchievementBadge({ type }) {
  const info = ALL_ACHIEVEMENTS[type];
  if (!info) return null;

  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-500/20 rounded-full border border-yellow-500/30">
      <span>{info.icon}</span>
      <span className="text-xs text-yellow-300">{info.name}</span>
    </div>
  );
}
