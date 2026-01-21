/**
 * ChatActionCard - Rich interactive cards for AI responses
 * 
 * Renders different card types based on the AI's detected intent:
 * - PostPreviewCard: Shows generated posts with schedule/edit actions
 * - ScheduleCard: Shows optimal posting times
 * - AnalyticsCard: Shows performance metrics summary
 * - PlatformCard: Shows platform connection status
 * - IdeasCard: Shows content ideas with quick actions
 * - QuickActionsCard: Generic follow-up suggestions
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Calendar, Clock, Edit3, Copy, Check, Send, ChevronRight,
  Twitter, Instagram, Linkedin, Youtube, MessageCircle,
  TrendingUp, Users, Eye, Heart, BarChart3, Zap,
  Lightbulb, Sparkles, Link2, ExternalLink, Plus,
  Play, Pause, RefreshCw, Share2, Bookmark
} from 'lucide-react';

// Platform icon mapping
const PlatformIcon = ({ platform, className = "w-4 h-4" }) => {
  const icons = {
    twitter: Twitter,
    x: Twitter,
    instagram: Instagram,
    linkedin: Linkedin,
    youtube: Youtube,
    discord: MessageCircle,
    reddit: MessageCircle,
  };
  const Icon = icons[platform?.toLowerCase()] || MessageCircle;
  return <Icon className={className} />;
};

// Platform colors
const platformColors = {
  twitter: 'from-sky-400 to-blue-500',
  x: 'from-zinc-600 to-zinc-800',
  instagram: 'from-pink-500 via-purple-500 to-orange-400',
  linkedin: 'from-blue-600 to-blue-700',
  youtube: 'from-red-500 to-red-600',
  discord: 'from-indigo-500 to-purple-600',
  reddit: 'from-orange-500 to-orange-600',
};

// ============================================
// POST PREVIEW CARD
// Shows generated posts with actions
// ============================================
export const PostPreviewCard = ({ 
  posts = [], 
  onSchedule, 
  onEdit, 
  onCopy,
  onSendMessage 
}) => {
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [selectedPosts, setSelectedPosts] = useState(new Set());

  const handleCopy = async (content, index) => {
    await navigator.clipboard.writeText(content);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
    onCopy?.(content);
  };

  const toggleSelect = (index) => {
    const newSelected = new Set(selectedPosts);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedPosts(newSelected);
  };

  const selectAll = () => {
    if (selectedPosts.size === posts.length) {
      setSelectedPosts(new Set());
    } else {
      setSelectedPosts(new Set(posts.map((_, i) => i)));
    }
  };

  if (!posts.length) return null;

  return (
    <div className="mt-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold text-white">
            Generated Posts ({posts.length})
          </span>
        </div>
        <button
          onClick={selectAll}
          className="text-xs text-white/60 hover:text-white transition-colors"
        >
          {selectedPosts.size === posts.length ? 'Deselect All' : 'Select All'}
        </button>
      </div>

      {/* Posts Grid */}
      <div className="space-y-2">
        {posts.map((post, index) => (
          <div
            key={index}
            className={`
              relative p-4 rounded-xl border transition-all duration-200
              ${selectedPosts.has(index)
                ? 'bg-[#9945FF]/10 border-[#9945FF]/40'
                : 'bg-white/[0.03] border-white/[0.08] hover:border-white/[0.15]'}
            `}
          >
            {/* Select checkbox */}
            <button
              onClick={() => toggleSelect(index)}
              className={`
                absolute top-3 right-3 w-5 h-5 rounded border-2 flex items-center justify-center
                transition-all duration-200
                ${selectedPosts.has(index)
                  ? 'bg-[#14F195] border-[#14F195]'
                  : 'border-white/30 hover:border-white/60'}
              `}
            >
              {selectedPosts.has(index) && <Check className="w-3 h-3 text-black" />}
            </button>

            {/* Platform badge */}
            {post.platform && (
              <div className={`
                inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium mb-2
                bg-gradient-to-r ${platformColors[post.platform] || 'from-gray-600 to-gray-700'} text-white
              `}>
                <PlatformIcon platform={post.platform} className="w-3 h-3" />
                {post.platform}
              </div>
            )}

            {/* Post content */}
            <p className="text-sm text-white/90 leading-relaxed pr-8 whitespace-pre-wrap">
              {post.content || post}
            </p>

            {/* Post actions */}
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/[0.06]">
              <button
                onClick={() => handleCopy(post.content || post, index)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                          bg-white/[0.05] text-white/70 hover:text-white hover:bg-white/[0.1]
                          transition-all duration-200"
              >
                {copiedIndex === index ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#14F195]" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5" />
                    Copy
                  </>
                )}
              </button>
              <button
                onClick={() => onEdit?.(post, index)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
                          bg-white/[0.05] text-white/70 hover:text-white hover:bg-white/[0.1]
                          transition-all duration-200"
              >
                <Edit3 className="w-3.5 h-3.5" />
                Edit
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Bulk Actions */}
      {selectedPosts.size > 0 && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-gradient-to-r from-[#9945FF]/10 to-[#14F195]/10 border border-[#9945FF]/30">
          <span className="text-sm text-white/80 mr-auto">
            {selectedPosts.size} post{selectedPosts.size > 1 ? 's' : ''} selected
          </span>
          <button
            onClick={() => onSchedule?.(Array.from(selectedPosts).map(i => posts[i]))}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                      bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white
                      hover:shadow-lg hover:shadow-[#9945FF]/30 transition-all duration-200"
          >
            <Calendar className="w-4 h-4" />
            Schedule Selected
          </button>
        </div>
      )}

      {/* Quick Follow-up */}
      <div className="flex flex-wrap gap-2 pt-2">
        <QuickActionButton
          icon={RefreshCw}
          label="Generate More"
          onClick={() => onSendMessage?.('Generate 5 more variations')}
        />
        <QuickActionButton
          icon={Calendar}
          label="Schedule All"
          onClick={() => onSchedule?.(posts)}
        />
        <QuickActionButton
          icon={Sparkles}
          label="Make Shorter"
          onClick={() => onSendMessage?.('Make these posts shorter and punchier')}
        />
      </div>
    </div>
  );
};

// ============================================
// SCHEDULE CARD
// Shows optimal posting times
// ============================================
export const ScheduleCard = ({ 
  times = [], 
  platform,
  onApply,
  onSendMessage 
}) => {
  const navigate = useNavigate();

  const defaultTimes = [
    { time: '9:00 AM', day: 'Mon', score: 95 },
    { time: '12:00 PM', day: 'Tue', score: 88 },
    { time: '5:00 PM', day: 'Wed', score: 82 },
    { time: '7:00 PM', day: 'Thu', score: 78 },
  ];

  const displayTimes = times.length > 0 ? times : defaultTimes;

  return (
    <div className="mt-4 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00D4FF] to-[#3B82F6] flex items-center justify-center">
          <Clock className="w-4 h-4 text-white" />
        </div>
        <div>
          <span className="text-sm font-semibold text-white block">
            Optimal Posting Times
          </span>
          {platform && (
            <span className="text-xs text-white/50">for {platform}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        {displayTimes.map((slot, index) => (
          <div
            key={index}
            className="relative p-3 rounded-lg bg-white/[0.05] border border-white/[0.06]
                      hover:border-[#14F195]/30 transition-all duration-200 cursor-pointer group"
          >
            <div className="text-xs text-white/50 mb-1">{slot.day}</div>
            <div className="text-sm font-semibold text-white">{slot.time}</div>
            {slot.score && (
              <div className="absolute top-2 right-2 text-[10px] font-medium text-[#14F195]">
                {slot.score}%
              </div>
            )}
            <div 
              className="absolute bottom-0 left-0 h-0.5 rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195]"
              style={{ width: `${slot.score || 80}%` }}
            />
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => navigate('/calendar')}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                    bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white
                    hover:shadow-lg hover:shadow-[#9945FF]/30 transition-all duration-200"
        >
          <Calendar className="w-4 h-4" />
          Open Calendar
        </button>
        <QuickActionButton
          icon={Sparkles}
          label="Auto-Schedule"
          onClick={() => onSendMessage?.('Auto-schedule my posts for optimal times')}
        />
      </div>
    </div>
  );
};

// ============================================
// ANALYTICS CARD
// Shows performance metrics summary
// ============================================
export const AnalyticsCard = ({ 
  metrics = {},
  period = 'Last 7 days',
  onViewFull 
}) => {
  const navigate = useNavigate();

  const defaultMetrics = {
    impressions: { value: '12.5K', change: '+15%', positive: true },
    engagement: { value: '8.2%', change: '+2.1%', positive: true },
    followers: { value: '+234', change: '+12%', positive: true },
    posts: { value: '28', change: '-3', positive: false },
  };

  const displayMetrics = Object.keys(metrics).length > 0 ? metrics : defaultMetrics;

  const metricIcons = {
    impressions: Eye,
    engagement: Heart,
    followers: Users,
    posts: Send,
    reach: TrendingUp,
    clicks: Zap,
  };

  return (
    <div className="mt-4 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#F59E0B] to-[#EF4444] flex items-center justify-center">
            <BarChart3 className="w-4 h-4 text-white" />
          </div>
          <div>
            <span className="text-sm font-semibold text-white block">
              Performance Overview
            </span>
            <span className="text-xs text-white/50">{period}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {Object.entries(displayMetrics).map(([key, data]) => {
          const Icon = metricIcons[key] || TrendingUp;
          return (
            <div
              key={key}
              className="p-3 rounded-lg bg-white/[0.05] border border-white/[0.06]"
            >
              <div className="flex items-center gap-1.5 mb-2">
                <Icon className="w-3.5 h-3.5 text-white/50" />
                <span className="text-xs text-white/50 capitalize">{key}</span>
              </div>
              <div className="text-lg font-bold text-white">{data.value}</div>
              <div className={`text-xs font-medium ${data.positive ? 'text-[#14F195]' : 'text-red-400'}`}>
                {data.change}
              </div>
            </div>
          );
        })}
      </div>

      <button
        onClick={() => navigate('/analytics')}
        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
                  bg-white/[0.05] text-white hover:bg-white/[0.1]
                  transition-all duration-200 w-full justify-center"
      >
        <ExternalLink className="w-4 h-4" />
        View Full Analytics
      </button>
    </div>
  );
};

// ============================================
// PLATFORM CONNECTION CARD
// Shows platform with connect button
// ============================================
export const PlatformCard = ({ 
  platform,
  isConnected = false,
  onConnect,
  onDisconnect 
}) => {
  const navigate = useNavigate();

  const platformInfo = {
    twitter: { name: 'Twitter/X', color: 'from-sky-400 to-blue-500' },
    instagram: { name: 'Instagram', color: 'from-pink-500 via-purple-500 to-orange-400' },
    linkedin: { name: 'LinkedIn', color: 'from-blue-600 to-blue-700' },
    youtube: { name: 'YouTube', color: 'from-red-500 to-red-600' },
    discord: { name: 'Discord', color: 'from-indigo-500 to-purple-600' },
    reddit: { name: 'Reddit', color: 'from-orange-500 to-orange-600' },
  };

  const info = platformInfo[platform?.toLowerCase()] || { name: platform, color: 'from-gray-600 to-gray-700' };

  return (
    <div className="mt-4 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08]">
      <div className="flex items-center gap-4">
        <div className={`
          w-12 h-12 rounded-xl flex items-center justify-center
          bg-gradient-to-br ${info.color}
        `}>
          <PlatformIcon platform={platform} className="w-6 h-6 text-white" />
        </div>
        
        <div className="flex-1">
          <h4 className="text-sm font-semibold text-white">{info.name}</h4>
          <p className="text-xs text-white/50">
            {isConnected ? 'Connected and ready to post' : 'Connect to start posting'}
          </p>
        </div>

        <button
          onClick={() => isConnected ? onDisconnect?.() : navigate('/settings')}
          className={`
            flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium
            transition-all duration-200
            ${isConnected
              ? 'bg-white/[0.05] text-white hover:bg-white/[0.1]'
              : 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white hover:shadow-lg hover:shadow-[#9945FF]/30'}
          `}
        >
          {isConnected ? (
            <>
              <Check className="w-4 h-4 text-[#14F195]" />
              Connected
            </>
          ) : (
            <>
              <Link2 className="w-4 h-4" />
              Connect
            </>
          )}
        </button>
      </div>
    </div>
  );
};

// ============================================
// IDEAS CARD
// Shows content ideas with generate buttons
// ============================================
export const IdeasCard = ({ 
  ideas = [],
  onGenerate,
  onSendMessage 
}) => {
  const defaultIdeas = [
    { title: 'Behind the scenes', description: 'Show your team or process' },
    { title: 'Industry hot take', description: 'Share a bold opinion' },
    { title: 'User success story', description: 'Highlight a customer win' },
    { title: 'Educational thread', description: 'Teach something valuable' },
  ];

  const displayIdeas = ideas.length > 0 ? ideas : defaultIdeas;

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#14F195] to-[#10B981] flex items-center justify-center">
          <Lightbulb className="w-4 h-4 text-white" />
        </div>
        <span className="text-sm font-semibold text-white">
          Content Ideas
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {displayIdeas.map((idea, index) => (
          <button
            key={index}
            onClick={() => onSendMessage?.(`Create a post about: ${idea.title || idea}`)}
            className="group flex items-start gap-3 p-3 rounded-xl text-left
                      bg-white/[0.03] border border-white/[0.08]
                      hover:border-[#14F195]/30 hover:bg-white/[0.05]
                      transition-all duration-200"
          >
            <div className="w-6 h-6 rounded-lg bg-white/[0.05] flex items-center justify-center flex-shrink-0 mt-0.5
                          group-hover:bg-[#14F195]/20 transition-colors">
              <Sparkles className="w-3.5 h-3.5 text-white/50 group-hover:text-[#14F195]" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-medium text-white truncate">
                {idea.title || idea}
              </h4>
              {idea.description && (
                <p className="text-xs text-white/50 truncate">{idea.description}</p>
              )}
            </div>
            <ChevronRight className="w-4 h-4 text-white/20 group-hover:text-[#14F195] group-hover:translate-x-0.5 transition-all" />
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 pt-2">
        <QuickActionButton
          icon={RefreshCw}
          label="More Ideas"
          onClick={() => onSendMessage?.('Give me more content ideas')}
        />
        <QuickActionButton
          icon={TrendingUp}
          label="Trending Topics"
          onClick={() => onSendMessage?.('What topics are trending right now?')}
        />
      </div>
    </div>
  );
};

// ============================================
// QUICK ACTIONS CARD
// Generic follow-up suggestions
// ============================================
export const QuickActionsCard = ({ 
  actions = [],
  intent,
  onSendMessage 
}) => {
  // Default actions based on intent
  const intentActions = {
    create_campaign: [
      { label: 'Schedule these posts', message: 'Schedule these posts for optimal times' },
      { label: 'Generate more', message: 'Generate 5 more variations' },
      { label: 'Make them shorter', message: 'Make these posts shorter' },
    ],
    generate_ideas: [
      { label: 'Create posts from ideas', message: 'Create posts for all these ideas' },
      { label: 'More ideas', message: 'Give me more content ideas' },
      { label: 'Trending topics', message: 'What topics are trending?' },
    ],
    schedule_posts: [
      { label: 'Open calendar', message: 'Show me my content calendar' },
      { label: 'Best times today', message: 'What are the best times to post today?' },
      { label: 'Auto-schedule all', message: 'Auto-schedule my pending posts' },
    ],
    get_analytics: [
      { label: 'Top performing posts', message: 'Show me my top performing posts' },
      { label: 'Engagement tips', message: 'How can I improve my engagement?' },
      { label: 'Compare platforms', message: 'Compare my performance across platforms' },
    ],
    default: [
      { label: 'Create a post', message: 'Create a viral post for Twitter' },
      { label: 'View analytics', message: 'Show me my analytics' },
      { label: 'Get ideas', message: 'Give me content ideas' },
    ],
  };

  const displayActions = actions.length > 0 
    ? actions 
    : intentActions[intent] || intentActions.default;

  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {displayActions.map((action, index) => (
        <button
          key={index}
          onClick={() => onSendMessage?.(action.message || action)}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm
                    bg-white/[0.05] border border-white/[0.08]
                    text-white/70 hover:text-white hover:bg-white/[0.08] hover:border-white/[0.15]
                    transition-all duration-200"
        >
          <ChevronRight className="w-3.5 h-3.5" />
          {action.label || action}
        </button>
      ))}
    </div>
  );
};

// ============================================
// QUICK ACTION BUTTON (reusable)
// ============================================
const QuickActionButton = ({ icon: Icon, label, onClick, variant = 'default' }) => {
  const variants = {
    default: 'bg-white/[0.05] text-white/70 hover:text-white hover:bg-white/[0.1] border-white/[0.08]',
    primary: 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white hover:shadow-lg hover:shadow-[#9945FF]/30',
    success: 'bg-[#14F195]/10 text-[#14F195] hover:bg-[#14F195]/20 border-[#14F195]/30',
  };

  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
        border transition-all duration-200
        ${variants[variant]}
      `}
    >
      {Icon && <Icon className="w-3.5 h-3.5" />}
      {label}
    </button>
  );
};

// ============================================
// MAIN CHAT ACTION CARD COMPONENT
// Renders appropriate card based on intent
// ============================================
const ChatActionCard = ({ 
  intent,
  data = {},
  onSendMessage,
  onAction 
}) => {
  // Parse content for posts if applicable
  const parsePostsFromContent = (content) => {
    if (!content) return [];
    
    // Try to extract numbered posts
    const postMatches = content.match(/(?:^|\n)(?:\d+[\.\)]\s*)?[""](.+?)[""]/g);
    if (postMatches && postMatches.length > 0) {
      return postMatches.map(match => ({
        content: match.replace(/(?:^|\n)(?:\d+[\.\)]\s*)?[""](.+?)[""]/g, '$1').trim(),
        platform: data.platform || 'twitter'
      }));
    }

    // Try to extract blockquoted posts
    const blockquotes = content.match(/>\s*[""]?(.+?)[""]?(?=\n|$)/g);
    if (blockquotes && blockquotes.length > 0) {
      return blockquotes.map(q => ({
        content: q.replace(/^>\s*[""]?|[""]?$/g, '').trim(),
        platform: data.platform || 'twitter'
      }));
    }

    return [];
  };

  const renderCard = () => {
    switch (intent) {
      case 'create_campaign':
        const posts = data.posts || parsePostsFromContent(data.content);
        return posts.length > 0 ? (
          <PostPreviewCard
            posts={posts}
            onSchedule={(selected) => onAction?.('schedule', selected)}
            onEdit={(post, index) => onAction?.('edit', { post, index })}
            onCopy={(content) => onAction?.('copy', content)}
            onSendMessage={onSendMessage}
          />
        ) : (
          <QuickActionsCard intent={intent} onSendMessage={onSendMessage} />
        );

      case 'generate_ideas':
        return (
          <IdeasCard
            ideas={data.ideas || []}
            onGenerate={(idea) => onAction?.('generate', idea)}
            onSendMessage={onSendMessage}
          />
        );

      case 'schedule_posts':
        return (
          <ScheduleCard
            times={data.times || []}
            platform={data.platform}
            onApply={(times) => onAction?.('apply_schedule', times)}
            onSendMessage={onSendMessage}
          />
        );

      case 'get_analytics':
        return (
          <AnalyticsCard
            metrics={data.metrics || {}}
            period={data.period}
            onViewFull={() => onAction?.('view_analytics')}
          />
        );

      case 'connect_platform':
        return (
          <PlatformCard
            platform={data.platform}
            isConnected={data.isConnected}
            onConnect={() => onAction?.('connect', data.platform)}
            onDisconnect={() => onAction?.('disconnect', data.platform)}
          />
        );

      case 'help':
      case 'general_chat':
      default:
        return <QuickActionsCard intent={intent} onSendMessage={onSendMessage} />;
    }
  };

  return (
    <div className="chat-action-card">
      {renderCard()}
    </div>
  );
};

export default ChatActionCard;
