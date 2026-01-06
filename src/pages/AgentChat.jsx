import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  Menu, X, Sparkles, Zap, AlertCircle, Bot, User, 
  Rocket, Calendar, TrendingUp, Lightbulb, Image as ImageIcon,
  BarChart3, Hash, Send, Plus, MessageSquare, Search,
  Settings, Trash2, Copy, RefreshCw, ThumbsUp, ThumbsDown,
  Paperclip, Mic, StopCircle, ChevronRight, Star
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { sendChatMessage, streamChatMessage, listConversations, getConversationHistory, deleteConversation } from '../lib/chatApi';
import { useAuthStore } from '../store/authStore';

// ============================================
// ANIMATED GRADIENT ORB COMPONENT
// ============================================
const GradientOrb = ({ className = "", delay = 0 }) => (
  <div 
    className={`absolute rounded-full blur-3xl opacity-30 animate-pulse ${className}`}
    style={{ animationDelay: `${delay}s`, animationDuration: '4s' }}
  />
);

// ============================================
// TYPING INDICATOR COMPONENT
// ============================================
const TypingIndicator = () => (
  <div className="flex items-center gap-1.5 px-4 py-2">
    <div className="flex gap-1">
      {[0, 1, 2].map((i) => (
        <span 
          key={i}
          className="w-2 h-2 rounded-full bg-gradient-to-r from-[#9945FF] to-[#14F195]"
          style={{ 
            animation: 'bounce 1.4s ease-in-out infinite',
            animationDelay: `${i * 0.16}s`
          }}
        />
      ))}
    </div>
    <span className="text-sm text-white/50 ml-2">Thinking...</span>
  </div>
);

// ============================================
// MESSAGE COMPONENT
// ============================================
const ChatMessage = ({ message, onRegenerate, onCopy, isStreaming = false }) => {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Simple markdown-like rendering
  const renderContent = (text) => {
    return text.split('\n').map((line, i) => {
      // Bold text
      line = line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
      // Headers
      if (line.startsWith('### ')) {
        return <h3 key={i} className="text-lg font-bold text-white mt-4 mb-2" dangerouslySetInnerHTML={{ __html: line.slice(4) }} />;
      }
      if (line.startsWith('## ')) {
        return <h2 key={i} className="text-xl font-bold text-white mt-4 mb-2" dangerouslySetInnerHTML={{ __html: line.slice(3) }} />;
      }
      // Bullet points
      if (line.startsWith('- ') || line.startsWith('• ')) {
        return <li key={i} className="ml-4 text-white/80" dangerouslySetInnerHTML={{ __html: line.slice(2) }} />;
      }
      // Numbered lists
      if (/^\d+\.\s/.test(line)) {
        return <li key={i} className="ml-4 text-white/80 list-decimal" dangerouslySetInnerHTML={{ __html: line.replace(/^\d+\.\s/, '') }} />;
      }
      // Blockquotes
      if (line.startsWith('> ')) {
        return (
          <blockquote key={i} className="border-l-2 border-[#14F195] pl-4 my-2 text-white/90 italic bg-white/5 py-2 rounded-r-lg">
            <span dangerouslySetInnerHTML={{ __html: line.slice(2) }} />
          </blockquote>
        );
      }
      // Empty lines
      if (!line.trim()) return <br key={i} />;
      // Regular text
      return <p key={i} className="text-white/80 leading-relaxed" dangerouslySetInnerHTML={{ __html: line }} />;
    });
  };

  return (
    <div className={`group py-6 px-4 md:px-8 transition-colors ${isUser ? '' : 'bg-white/[0.02]'}`}>
      <div className="max-w-3xl mx-auto flex gap-4">
        {/* Avatar */}
        <div className={`
          w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0
          ${isUser 
            ? 'bg-gradient-to-br from-blue-500 to-purple-600' 
            : 'bg-gradient-to-br from-[#9945FF] to-[#14F195] shadow-lg shadow-[#9945FF]/20'}
        `}>
          {isUser ? <User className="w-5 h-5 text-white" /> : <Bot className="w-5 h-5 text-white" />}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-white text-sm">
              {isUser ? 'You' : 'Social Sol AI'}
            </span>
            {!isUser && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-gradient-to-r from-[#9945FF]/20 to-[#14F195]/20 text-[#14F195] border border-[#14F195]/20">
                AI Agent
              </span>
            )}
          </div>
          
          <div className="prose prose-invert max-w-none">
            {renderContent(message.content)}
            {isStreaming && (
              <span className="inline-block w-2 h-5 ml-1 bg-[#14F195] animate-pulse rounded-sm" />
            )}
          </div>

          {/* Actions */}
          {!isUser && (
            <div className="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/60 hover:text-white hover:bg-white/10 transition-all"
              >
                <Copy className="w-3.5 h-3.5" />
                {copied ? 'Copied!' : 'Copy'}
              </button>
              <button 
                onClick={() => onRegenerate?.(message.id)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/60 hover:text-white hover:bg-white/10 transition-all"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate
              </button>
              <div className="flex items-center gap-1 ml-2">
                <button className="p-1.5 rounded-lg text-white/40 hover:text-[#14F195] hover:bg-white/10 transition-all">
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button className="p-1.5 rounded-lg text-white/40 hover:text-red-400 hover:bg-white/10 transition-all">
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ============================================
// QUICK ACTION CARD
// ============================================
const QuickActionCard = ({ icon: Icon, title, description, gradient, onClick }) => (
  <button
    onClick={onClick}
    className="group relative p-5 rounded-2xl text-left transition-all duration-300
               bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.12]
               hover:shadow-xl hover:shadow-black/20 hover:-translate-y-1 cursor-pointer"
  >
    {/* Gradient glow on hover */}
    <div className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${gradient} blur-xl -z-10`} />
    
    <div className={`w-10 h-10 rounded-xl mb-3 flex items-center justify-center ${gradient}`}>
      <Icon className="w-5 h-5 text-white" />
    </div>
    <h3 className="font-semibold text-white mb-1 group-hover:text-[#14F195] transition-colors">
      {title}
    </h3>
    <p className="text-sm text-white/50 line-clamp-2">
      {description}
    </p>
    <ChevronRight className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20 group-hover:text-white/60 group-hover:translate-x-1 transition-all" />
  </button>
);

// ============================================
// SIDEBAR COMPONENT
// ============================================
const Sidebar = ({ 
  conversations, 
  activeConversation, 
  onSelectConversation, 
  onNewConversation,
  onDeleteConversation,
  isOpen,
  onClose 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  const filteredConversations = conversations.filter(conv => 
    conv.title?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <aside className={`
      w-72 bg-black/40 backdrop-blur-xl border-r border-white/[0.06] flex flex-col h-full
      fixed lg:relative inset-y-0 left-0 z-40
      transform transition-transform duration-300 ease-out
      ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
    `}>
      {/* Header */}
      <div className="p-4">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl
                     bg-gradient-to-r from-[#9945FF] to-[#14F195] 
                     text-white font-semibold text-sm
                     hover:shadow-lg hover:shadow-[#9945FF]/30 
                     active:scale-[0.98] transition-all duration-200"
        >
          <Plus className="w-5 h-5" />
          New Chat
        </button>
      </div>

      {/* Search */}
      <div className="px-4 pb-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <input
            type="text"
            placeholder="Search..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl
                       bg-white/[0.05] border border-white/[0.08]
                       text-sm text-white placeholder:text-white/30
                       focus:outline-none focus:border-[#9945FF]/50 focus:bg-white/[0.08]
                       transition-all duration-200"
          />
        </div>
      </div>

      {/* Conversations */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 scrollbar-thin">
        {filteredConversations.length > 0 ? (
          <div className="space-y-1">
            {filteredConversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                onMouseEnter={() => setHoveredId(conv.id)}
                onMouseLeave={() => setHoveredId(null)}
                className={`
                  group relative flex items-center gap-3 px-3 py-3 rounded-xl cursor-pointer
                  transition-all duration-200
                  ${activeConversation === conv.id 
                    ? 'bg-gradient-to-r from-[#9945FF]/20 to-[#14F195]/10 border border-[#9945FF]/30' 
                    : 'hover:bg-white/[0.05] border border-transparent'}
                `}
              >
                <div className={`
                  w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors
                  ${activeConversation === conv.id 
                    ? 'bg-gradient-to-br from-[#9945FF] to-[#14F195]' 
                    : 'bg-white/[0.08] group-hover:bg-white/[0.12]'}
                `}>
                  <MessageSquare className="w-4 h-4 text-white/80" />
                </div>
                
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white/90 truncate">
                    {conv.title || conv.preview || 'New conversation'}
                  </p>
                </div>

                {hoveredId === conv.id && (
                  <button 
                    onClick={(e) => { e.stopPropagation(); onDeleteConversation?.(conv.id); }}
                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-white/40 hover:text-red-400 transition-all"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#9945FF]/20 to-[#14F195]/20 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-[#14F195]" />
            </div>
            <p className="text-sm text-white/50">
              {searchQuery ? 'No conversations found' : 'Start a new conversation'}
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-white/[0.06]">
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
                          text-white/60 hover:text-white hover:bg-white/[0.05] transition-all">
          <Settings className="w-5 h-5" />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </div>
    </aside>
  );
};

// ============================================
// INPUT COMPONENT
// ============================================
const ChatInput = ({ onSend, isLoading, onStop }) => {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [message]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage('');
    }
  };

  return (
    <div className="p-4 md:p-6 bg-gradient-to-t from-black via-black/80 to-transparent">
      <div className="max-w-3xl mx-auto">
        <form onSubmit={handleSubmit}>
          <div className={`
            relative flex items-end gap-2 p-2 rounded-2xl
            bg-white/[0.05] backdrop-blur-sm
            border transition-all duration-300
            ${isFocused 
              ? 'border-[#9945FF]/50 shadow-lg shadow-[#9945FF]/10' 
              : 'border-white/[0.08] hover:border-white/[0.15]'}
          `}>
            <button
              type="button"
              className="p-2.5 rounded-xl text-white/40 hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSubmit())}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask me to create posts, schedule campaigns, analyze trends..."
              rows={1}
              className="flex-1 bg-transparent text-white placeholder:text-white/30
                        text-base leading-relaxed resize-none py-2.5 px-2
                        focus:outline-none min-h-[44px] max-h-[200px]"
            />

            <button
              type="button"
              className="p-2.5 rounded-xl text-white/40 hover:text-white hover:bg-white/[0.08] transition-all"
            >
              <ImageIcon className="w-5 h-5" />
            </button>

            {isLoading ? (
              <button
                type="button"
                onClick={onStop}
                className="p-3 rounded-xl bg-red-500/80 hover:bg-red-500 text-white transition-all"
              >
                <StopCircle className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!message.trim()}
                className={`
                  p-3 rounded-xl transition-all duration-300
                  ${message.trim()
                    ? 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white shadow-lg shadow-[#9945FF]/30 hover:shadow-[#9945FF]/50 hover:scale-105 active:scale-95'
                    : 'bg-white/[0.08] text-white/30 cursor-not-allowed'}
                `}
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </form>

        <p className="text-center text-xs text-white/30 mt-3">
          Press <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-white/50 mx-1">Enter</kbd> to send · 
          <kbd className="px-1.5 py-0.5 rounded bg-white/10 text-white/50 mx-1">Shift + Enter</kbd> for new line
        </p>
      </div>
    </div>
  );
};

// ============================================
// MAIN AGENT CHAT COMPONENT
// ============================================
const AgentChat = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();
  
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  useEffect(() => {
    if (isAuthenticated) loadConversations();
  }, [isAuthenticated]);

  const loadConversations = async () => {
    try {
      const result = await listConversations(20);
      setConversations(result.conversations?.map(c => ({
        id: c.id,
        title: c.preview,
        preview: c.preview,
        updatedAt: c.timestamp,
      })) || []);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  };

  const handleSend = async (content) => {
    if (!content.trim()) return;
    setError(null);
    
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsStreaming(true);
    setStreamingContent('');

    try {
      // Use streaming API for real-time typing effect
      await streamChatMessage(
        content,
        activeConversation,
        // onChunk - called as content streams in
        (partialContent, intent, actions) => {
          setStreamingContent(partialContent);
        },
        // onComplete - called when stream is done
        (result) => {
          setIsStreaming(false);
          setStreamingContent('');
          
          if (result.conversationId && !activeConversation) {
            setActiveConversation(result.conversationId);
          }
          
          setMessages(prev => [...prev, {
            id: (Date.now() + 1).toString(),
            role: 'assistant',
            content: result.content,
            timestamp: new Date().toISOString(),
            intent: result.intent,
            actions: result.actions,
          }]);
          
          loadConversations();
          setIsLoading(false);
        },
        // onError - fallback to non-streaming
        async (err) => {
          console.error('Streaming failed, falling back:', err);
          setIsStreaming(false);
          setStreamingContent('');
          
          try {
            // Fallback to regular API
            const response = await sendChatMessage(content, activeConversation);
            
            if (!activeConversation && response.conversation_id) {
              setActiveConversation(response.conversation_id);
            }
            
            setMessages(prev => [...prev, {
              id: response.message_id || (Date.now() + 1).toString(),
              role: 'assistant',
              content: response.content,
              timestamp: response.timestamp,
            }]);
            
            loadConversations();
          } catch (fallbackErr) {
            // Use local fallback
            setMessages(prev => [...prev, {
              id: (Date.now() + 1).toString(),
              role: 'assistant',
              content: generateFallbackResponse(content),
              timestamp: new Date().toISOString(),
            }]);
          }
          setIsLoading(false);
        }
      );
    } catch (err) {
      setIsStreaming(false);
      setStreamingContent('');
      // Fallback response
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateFallbackResponse(content),
        timestamp: new Date().toISOString(),
      }]);
      setIsLoading(false);
    }
  };

  const generateFallbackResponse = (msg) => {
    const lower = msg.toLowerCase();
    if (lower.includes('post') || lower.includes('generate')) {
      return `## 🚀 Here's an engaging post for you:\n\n> "Building the future of social media automation with AI. 🤖✨\n>\n> Imagine scheduling posts, analyzing trends, and generating content - all with a single conversation.\n>\n> The future is here. Are you ready? 👇\n>\n> #AI #SocialMedia #Automation #Web3"\n\n**What's next?**\n- Generate variations\n- Schedule this post\n- Create more content`;
    }
    if (lower.includes('campaign')) {
      return `## 📊 Campaign Structure Ready!\n\n**Week 1: Awareness Phase**\n- 3 teaser posts across platforms\n- 1 behind-the-scenes video\n\n**Week 2: Engagement Phase**\n- Interactive polls and Q&As\n- User-generated content contest\n\n**Week 3: Launch Phase**\n- Main announcement\n- Influencer collaborations\n\nShall I generate the content for each phase?`;
    }
    if (lower.includes('idea') || lower.includes('trending')) {
      return `## 📈 Trending Topics Right Now:\n\n1. **AI & Automation** - Very high engagement\n2. **Crypto market updates** - Trending on Twitter\n3. **Year-end reflections** - Seasonal content\n4. **2025 predictions** - High shareability\n5. **Behind-the-scenes content** - Strong authenticity signals\n\nWhich topic would you like me to create content around?`;
    }
    if (lower.includes('schedule')) {
      return `## 📅 Optimal Posting Times\n\n| Platform | Best Times |\n|----------|------------|\n| **Twitter/X** | 9 AM, 12 PM, 5 PM |\n| **Instagram** | 11 AM, 2 PM, 7 PM |\n| **LinkedIn** | 7 AM, 12 PM, 5 PM |\n\n**Next steps:**\n1. Create a week's worth of content\n2. Schedule specific posts\n3. Analyze your best performing times`;
    }
    return `I can help you with:\n\n- 📝 **Create Content** - Generate posts, threads, captions\n- 📅 **Schedule & Plan** - Find optimal posting times\n- 📈 **Analyze & Optimize** - Review performance metrics\n- 💡 **Generate Ideas** - Viral content suggestions\n\nWhat would you like to do?`;
  };

  const quickActions = [
    { icon: Rocket, title: 'Create Campaign', description: 'Generate a full content campaign with AI', gradient: 'bg-gradient-to-br from-[#9945FF] to-[#6366F1]', prompt: 'Create a 2-week marketing campaign for my crypto project' },
    { icon: Lightbulb, title: 'Content Ideas', description: 'Get trending viral content suggestions', gradient: 'bg-gradient-to-br from-[#14F195] to-[#10B981]', prompt: 'Give me 5 viral content ideas for Twitter' },
    { icon: Calendar, title: 'Schedule Posts', description: 'Find optimal posting times for engagement', gradient: 'bg-gradient-to-br from-[#00D4FF] to-[#3B82F6]', prompt: 'What are the best times to post on Instagram?' },
    { icon: BarChart3, title: 'Analytics', description: 'Review your performance metrics', gradient: 'bg-gradient-to-br from-[#F59E0B] to-[#EF4444]', prompt: 'Show me my analytics for the past week' },
  ];

  return (
    <div className="flex h-screen bg-[#030303] overflow-hidden">
      {/* Ambient Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <GradientOrb className="w-[600px] h-[600px] -top-48 -left-48 bg-[#9945FF]" delay={0} />
        <GradientOrb className="w-[500px] h-[500px] top-1/2 -right-48 bg-[#14F195]" delay={2} />
        <GradientOrb className="w-[400px] h-[400px] -bottom-24 left-1/3 bg-[#00D4FF]" delay={1} />
        {/* Noise texture overlay */}
        <div className="absolute inset-0 opacity-[0.015]" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")' }} />
      </div>

      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2.5 rounded-xl bg-black/50 backdrop-blur-sm border border-white/10 text-white"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <Sidebar
        conversations={conversations}
        activeConversation={activeConversation}
        onSelectConversation={(id) => { setActiveConversation(id); setSidebarOpen(false); }}
        onNewConversation={() => { setActiveConversation(null); setMessages([]); }}
        onDeleteConversation={(id) => { deleteConversation(id); setConversations(prev => prev.filter(c => c.id !== id)); }}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-30" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main Area */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Header */}
        <header className="relative z-10 flex items-center justify-between px-6 py-4 border-b border-white/[0.06] bg-black/20 backdrop-blur-xl">
          <div className="flex items-center gap-3 pl-12 lg:pl-0">
            <div className="relative">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center shadow-lg shadow-[#9945FF]/30">
                <Bot className="w-6 h-6 text-white" />
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full bg-[#14F195] border-2 border-black" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Social Sol AI
              </h1>
              <p className="text-xs text-white/50">
                {user?.name ? `Hey ${user.name.split(' ')[0]}!` : 'Your AI social media agent'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#14F195]/10 border border-[#14F195]/20">
              <div className="w-2 h-2 rounded-full bg-[#14F195] animate-pulse" />
              <span className="text-xs font-medium text-[#14F195]">Online</span>
            </div>
          </div>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="px-6 py-3 bg-red-500/10 border-b border-red-500/20 flex items-center gap-2 text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center px-4 py-12">
              <div className="max-w-3xl mx-auto text-center">
                {/* Hero */}
                <div className="mb-10">
                  <div className="relative w-24 h-24 mx-auto mb-8">
                    <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-[#9945FF] to-[#14F195] animate-pulse opacity-50 blur-xl" />
                    <div className="relative w-full h-full rounded-3xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center shadow-2xl">
                      <Sparkles className="w-12 h-12 text-white" />
                    </div>
                  </div>
                  
                  <h2 className="text-4xl font-bold text-white mb-4 tracking-tight" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    Welcome to <span className="bg-gradient-to-r from-[#9945FF] via-[#14F195] to-[#00D4FF] bg-clip-text text-transparent">Social Sol AI</span>
                  </h2>
                  <p className="text-lg text-white/60 max-w-lg mx-auto leading-relaxed">
                    Your AI-powered assistant for creating, scheduling, and managing social media content.
                  </p>
                </div>

                {/* Quick Actions Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
                  {quickActions.map((action, i) => (
                    <QuickActionCard
                      key={i}
                      icon={action.icon}
                      title={action.title}
                      description={action.description}
                      gradient={action.gradient}
                      onClick={() => handleSend(action.prompt)}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div>
              {messages.map((message) => (
                <ChatMessage 
                  key={message.id} 
                  message={message}
                  onRegenerate={(id) => {
                    const idx = messages.findIndex(m => m.id === id);
                    if (idx > 0 && messages[idx-1].role === 'user') {
                      setMessages(prev => prev.filter(m => m.id !== id));
                      handleSend(messages[idx-1].content);
                    }
                  }}
                />
              ))}
              
              {/* Streaming Message Display */}
              {isStreaming && streamingContent && (
                <ChatMessage 
                  message={{
                    id: 'streaming',
                    role: 'assistant',
                    content: streamingContent,
                    timestamp: new Date().toISOString(),
                  }}
                  isStreaming={true}
                />
              )}
              
              {/* Loading Indicator (only when not streaming) */}
              {isLoading && !streamingContent && (
                <div className="py-6 px-4 md:px-8 bg-white/[0.02]">
                  <div className="max-w-3xl mx-auto flex gap-4">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center shadow-lg shadow-[#9945FF]/20">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <TypingIndicator />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input */}
        <ChatInput 
          onSend={handleSend}
          isLoading={isLoading}
          onStop={() => setIsLoading(false)}
        />
      </main>

      {/* Keyframe animations */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
      `}</style>
    </div>
  );
};

export default AgentChat;
