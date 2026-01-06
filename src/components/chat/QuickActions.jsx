import { 
  Sparkles, 
  Calendar, 
  TrendingUp, 
  Lightbulb,
  Image as ImageIcon,
  MessageSquare,
  Zap,
  Target
} from 'lucide-react';

const quickActionsList = [
  {
    id: 'generate-post',
    icon: Sparkles,
    label: 'Generate a post',
    prompt: 'Generate an engaging social media post about',
    color: 'from-[#9945FF] to-[#14F195]'
  },
  {
    id: 'create-campaign',
    icon: Target,
    label: 'Create campaign',
    prompt: 'Help me create a marketing campaign for',
    color: 'from-[#FF6B6B] to-[#FFE66D]'
  },
  {
    id: 'schedule-posts',
    icon: Calendar,
    label: 'Schedule posts',
    prompt: 'Schedule posts for the next week about',
    color: 'from-[#4ECDC4] to-[#45B7D1]'
  },
  {
    id: 'trending-topics',
    icon: TrendingUp,
    label: 'Trending topics',
    prompt: 'What are the trending topics right now that I could post about?',
    color: 'from-[#A8E6CF] to-[#88D8B0]'
  },
  {
    id: 'content-ideas',
    icon: Lightbulb,
    label: 'Content ideas',
    prompt: 'Give me 5 creative content ideas for',
    color: 'from-[#FFB347] to-[#FFCC33]'
  },
  {
    id: 'generate-image',
    icon: ImageIcon,
    label: 'Generate image',
    prompt: 'Create an image for a post about',
    color: 'from-[#E040FB] to-[#7C4DFF]'
  },
  {
    id: 'write-caption',
    icon: MessageSquare,
    label: 'Write caption',
    prompt: 'Write a compelling caption for',
    color: 'from-[#00BCD4] to-[#2196F3]'
  },
  {
    id: 'optimize-timing',
    icon: Zap,
    label: 'Best posting times',
    prompt: 'When are the best times to post on',
    color: 'from-[#FF9A9E] to-[#FAD0C4]'
  },
];

const QuickActions = ({ onSelect, compact = false }) => {
  return (
    <div className={`${compact ? 'px-4 pb-4' : 'px-8 py-6'}`}>
      <div className="max-w-3xl mx-auto">
        {!compact && (
          <h3 className="text-sm font-medium text-[var(--color-text-muted)] mb-4">
            Quick Actions
          </h3>
        )}
        
        <div className={`
          flex flex-wrap gap-2
          ${compact ? 'justify-center' : 'justify-start'}
        `}>
          {quickActionsList.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.id}
                onClick={() => onSelect(action.prompt)}
                className={`
                  group flex items-center gap-2 px-4 py-2.5 rounded-full
                  bg-[var(--color-surface)] border border-[var(--color-border)]
                  text-[var(--color-text-secondary)] text-sm font-medium
                  hover:text-[var(--color-text-primary)] hover:border-[var(--color-brand-primary)]/50
                  hover:bg-[var(--color-surface-hover)]
                  transition-all duration-300 hover:-translate-y-0.5
                  hover:shadow-lg hover:shadow-[var(--color-brand-primary)]/10
                `}
              >
                <div className={`
                  w-6 h-6 rounded-md flex items-center justify-center
                  bg-gradient-to-br ${action.color}
                  opacity-80 group-hover:opacity-100
                  transition-opacity duration-200
                `}>
                  <Icon className="w-3.5 h-3.5 text-white" />
                </div>
                <span>{action.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default QuickActions;


