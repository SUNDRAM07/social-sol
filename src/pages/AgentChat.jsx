import { useState, useRef, useEffect, useCallback } from 'react';
import { Menu, X, Sparkles, Zap, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ChatSidebar from '../components/chat/ChatSidebar';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import QuickActions from '../components/chat/QuickActions';
import { sendChatMessage, listConversations, getConversationHistory, deleteConversation } from '../lib/chatApi';
import { useAuthStore } from '../store/authStore';

const AgentChat = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuthStore();
  
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Load conversations on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadConversations = async () => {
    try {
      const result = await listConversations(20);
      // Transform to expected format
      const convos = result.conversations?.map(c => ({
        id: c.id,
        title: c.preview,
        preview: c.preview,
        updatedAt: c.timestamp,
      })) || [];
      setConversations(convos);
    } catch (err) {
      console.error('Failed to load conversations:', err);
      // Set sample conversations as fallback
      setConversations([]);
    }
  };

  const loadConversationHistory = async (conversationId) => {
    try {
      const history = await getConversationHistory(conversationId);
      const msgs = history.messages?.map((m, i) => ({
        id: `${conversationId}-${i}`,
        role: m.role,
        content: m.content,
        timestamp: m.created_at,
      })) || [];
      setMessages(msgs);
    } catch (err) {
      console.error('Failed to load history:', err);
    }
  };

  const handleSend = async (content) => {
    if (!content.trim()) return;
    
    setError(null);
    
    // Add user message
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setStreamingContent('');

    try {
      // Send to real backend
      const response = await sendChatMessage(content, activeConversation);
      
      // Update active conversation if new
      if (!activeConversation && response.conversation_id) {
        setActiveConversation(response.conversation_id);
      }
      
      // Add AI response
      const aiResponse = {
        id: response.message_id || (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: response.timestamp,
        intent: response.intent,
        entities: response.entities,
        actions: response.actions,
      };
      setMessages(prev => [...prev, aiResponse]);
      
      // Refresh conversations
      loadConversations();
      
    } catch (err) {
      console.error('Chat error:', err);
      
      // Check if it's an auth error
      if (err.message?.includes('401') || err.message?.includes('Unauthorized')) {
        setError('Session expired. Please log in again.');
        setTimeout(() => {
          logout();
          navigate('/login');
        }, 2000);
      } else {
        // Fallback to local response for demo
        setError(null);
        const fallbackResponse = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: generateFallbackResponse(content),
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, fallbackResponse]);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const generateFallbackResponse = (userMessage) => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('post') || lowerMessage.includes('generate')) {
      return `🚀 **Here's an engaging post for you:**\n\n> "Building the future of social media automation with AI. 🤖✨\n>\n> Imagine scheduling posts, analyzing trends, and generating content - all with a single conversation.\n>\n> The future is here. Are you ready? 👇\n>\n> #AI #SocialMedia #Automation #Web3"\n\n**What's next?**\n- Generate variations\n- Schedule this post\n- Create more content`;
    }
    
    if (lowerMessage.includes('campaign')) {
      return `📊 **Campaign Structure Ready!**\n\n**Week 1: Awareness Phase**\n- 3 teaser posts across platforms\n- 1 behind-the-scenes video\n\n**Week 2: Engagement Phase**\n- Interactive polls and Q&As\n- User-generated content contest\n\n**Week 3: Launch Phase**\n- Main announcement\n- Influencer collaborations\n\nShall I generate the content for each phase?`;
    }
    
    if (lowerMessage.includes('trending') || lowerMessage.includes('topics') || lowerMessage.includes('ideas')) {
      return `📈 **Trending Topics Right Now:**\n\n1. **AI & Automation** - Very high engagement\n2. **Crypto market updates** - Trending on Twitter\n3. **Year-end reflections** - Seasonal content\n4. **2025 predictions** - High shareability\n5. **Behind-the-scenes content** - Strong authenticity signals\n\nWhich topic would you like me to create content around?`;
    }
    
    if (lowerMessage.includes('schedule')) {
      return `📅 **Optimal Posting Times**\n\nBased on general engagement patterns:\n\n| Platform | Best Times |\n|----------|------------|\n| **Twitter/X** | 9 AM, 12 PM, 5 PM |\n| **Instagram** | 11 AM, 2 PM, 7 PM |\n| **LinkedIn** | 7 AM, 12 PM, 5 PM |\n| **Reddit** | 6 AM, 8 AM, 12 PM |\n\n**Next steps:**\n1. Create a week's worth of content\n2. Schedule specific posts\n3. Analyze your best performing times`;
    }

    if (lowerMessage.includes('analytics') || lowerMessage.includes('performance')) {
      return `📊 **Analytics Summary**\n\nI'll pull your performance data. In the meantime, here's what I can analyze:\n\n- **Engagement rates** by platform\n- **Best performing content** types\n- **Optimal posting times** for your audience\n- **Growth trends** over time\n\nWould you like me to focus on a specific metric?`;
    }

    if (lowerMessage.includes('help') || lowerMessage.includes('what can you')) {
      return `🤖 **I'm Social Sol AI - Your Social Media Agent**\n\nHere's what I can do:\n\n✨ **Create Content**\n- Generate posts, threads, and captions\n- Create content for any platform\n\n📅 **Schedule & Plan**\n- Find optimal posting times\n- Create content calendars\n\n📈 **Analyze & Optimize**\n- Review performance metrics\n- Suggest improvements\n\n💡 **Generate Ideas**\n- Viral content suggestions\n- Trending topic analysis\n\nJust tell me what you need!`;
    }
    
    return `I understand you want help with: "${userMessage}"\n\n**I can assist you with:**\n\n📝 Creating engaging posts\n📅 Scheduling content\n📈 Analyzing trends\n💡 Generating content ideas\n\nWhat would you like me to focus on?`;
  };

  const handleNewConversation = () => {
    setActiveConversation(null);
    setMessages([]);
    setError(null);
  };

  const handleSelectConversation = async (conversationId) => {
    setActiveConversation(conversationId);
    await loadConversationHistory(conversationId);
    setSidebarOpen(false);
  };

  const handleDeleteConversation = async (conversationId) => {
    try {
      await deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      if (activeConversation === conversationId) {
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const handleRegenerate = async (messageId) => {
    // Find the user message before this AI message
    const messageIndex = messages.findIndex(m => m.id === messageId);
    if (messageIndex <= 0) return;
    
    const userMessage = messages[messageIndex - 1];
    if (userMessage.role !== 'user') return;
    
    // Remove the current AI response
    setMessages(prev => prev.filter(m => m.id !== messageId));
    
    // Regenerate
    await handleSend(userMessage.content);
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen bg-[var(--bg-primary)] overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#9945FF]/5 via-transparent to-[#14F195]/5 pointer-events-none" />
      
      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] shadow-lg"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
      <div className={`
        fixed lg:relative inset-y-0 left-0 z-40
        transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <ChatSidebar
          conversations={conversations}
          activeConversation={activeConversation}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
        />
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-30 backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0 relative">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)] bg-[var(--bg-secondary)]/80 backdrop-blur-xl relative z-10">
          <div className="flex items-center gap-3 pl-12 lg:pl-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center shadow-lg shadow-[#9945FF]/20">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-[var(--text-primary)]" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                Social Sol AI
              </h1>
              <p className="text-xs text-[var(--text-muted)]">
                {user?.name ? `Hey ${user.name.split(' ')[0]}!` : 'Your AI social media agent'}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#14F195]/10 text-[#14F195] text-xs font-medium">
              <Zap className="w-3 h-3" />
              Online
            </span>
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
            /* Empty State */
            <div className="h-full flex flex-col items-center justify-center px-4 py-12">
              <div className="max-w-2xl mx-auto text-center">
                {/* Hero */}
                <div className="mb-8">
                  <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#9945FF] to-[#14F195] 
                                flex items-center justify-center shadow-2xl shadow-[#9945FF]/30 animate-float">
                    <Sparkles className="w-10 h-10 text-white" />
                  </div>
                  <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-3" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
                    Welcome to Social Sol AI
                  </h2>
                  <p className="text-[var(--text-secondary)] text-lg max-w-md mx-auto">
                    Your AI-powered assistant for creating, scheduling, and managing social media content.
                  </p>
                </div>

                {/* Quick Actions */}
                <QuickActions onSelect={handleSend} />
              </div>
            </div>
          ) : (
            /* Messages List */
            <div className="py-4">
              {messages.map((message) => (
                <ChatMessage 
                  key={message.id} 
                  message={message}
                  isStreaming={false}
                  onRegenerate={() => handleRegenerate(message.id)}
                />
              ))}
              
              {/* Streaming Content */}
              {streamingContent && (
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
              
              {/* Loading Indicator */}
              {isLoading && !streamingContent && (
                <div className="py-6 px-4 md:px-8 lg:px-16">
                  <div className="max-w-3xl mx-auto flex gap-4 md:gap-6">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#9945FF]/20 to-[#14F195]/20 border border-[var(--border)] 
                                  flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-5 h-5 text-[#14F195]" />
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-[#14F195] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-[#9945FF] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-[#00D4FF] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-sm text-[var(--text-muted)]">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <ChatInput 
          onSend={handleSend}
          isLoading={isLoading}
          onStop={handleStop}
          value={inputValue}
          onChange={setInputValue}
        />
      </main>
    </div>
  );
};

export default AgentChat;
