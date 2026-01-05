import { useState, useRef, useEffect } from 'react';
import { Menu, X, Sparkles, Zap } from 'lucide-react';
import ChatSidebar from '../components/chat/ChatSidebar';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import QuickActions from '../components/chat/QuickActions';

// Sample conversations for demo
const sampleConversations = [
  {
    id: '1',
    title: 'Marketing campaign for NFT launch',
    preview: 'Create a viral marketing campaign...',
    updatedAt: new Date().toISOString(),
  },
  {
    id: '2', 
    title: 'Weekly content calendar',
    preview: 'Schedule posts for the week...',
    updatedAt: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: '3',
    title: 'Twitter thread ideas',
    preview: 'Generate engaging thread topics...',
    updatedAt: new Date(Date.now() - 172800000).toISOString(),
  },
];

const AgentChat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [conversations, setConversations] = useState(sampleConversations);
  const [activeConversation, setActiveConversation] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (content) => {
    // Add user message
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    // Simulate AI response with streaming effect
    setTimeout(() => {
      const aiResponse = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: generateSampleResponse(content),
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, aiResponse]);
      setIsLoading(false);
    }, 1500);
  };

  const generateSampleResponse = (userMessage) => {
    const lowerMessage = userMessage.toLowerCase();
    
    if (lowerMessage.includes('post') || lowerMessage.includes('generate')) {
      return `🚀 Here's an engaging post for you:\n\n"Building the future of social media automation with AI. 🤖✨\n\nImagine scheduling posts, analyzing trends, and generating content - all with a single conversation.\n\nThe future is here. Are you ready? 👇\n\n#AI #SocialMedia #Automation #Web3"\n\nWant me to generate variations or schedule this post?`;
    }
    
    if (lowerMessage.includes('campaign')) {
      return `📊 I'll help you create a comprehensive campaign!\n\n**Campaign Structure:**\n\n1. **Week 1: Awareness Phase**\n   - 3 teaser posts across platforms\n   - 1 behind-the-scenes video\n\n2. **Week 2: Engagement Phase**\n   - Interactive polls and Q&As\n   - User-generated content contest\n\n3. **Week 3: Launch Phase**\n   - Main announcement\n   - Influencer collaborations\n\nShall I generate the content for each phase?`;
    }
    
    if (lowerMessage.includes('trending') || lowerMessage.includes('topics')) {
      return `📈 **Trending Topics Right Now:**\n\n1. **AI & Automation** - Very high engagement\n2. **Crypto market updates** - Trending on Twitter\n3. **Year-end reflections** - Seasonal content\n4. **2024 predictions** - High shareability\n5. **Behind-the-scenes content** - Strong authenticity signals\n\nWhich topic would you like me to create content around?`;
    }
    
    if (lowerMessage.includes('schedule')) {
      return `📅 I can help you schedule posts!\n\n**Recommended posting times based on your audience:**\n\n• **Twitter/X:** 9 AM, 12 PM, 5 PM\n• **Instagram:** 11 AM, 2 PM, 7 PM\n• **LinkedIn:** 7 AM, 12 PM, 5 PM\n\nWould you like me to:\n1. Create a week's worth of content\n2. Schedule specific posts\n3. Analyze your best performing times`;
    }
    
    return `I understand you want help with: "${userMessage}"\n\nI can assist you with:\n• 📝 Creating engaging posts\n• 📅 Scheduling content\n• 📈 Analyzing trends\n• 💡 Generating content ideas\n• 🎨 Creating images\n\nWhat would you like me to focus on?`;
  };

  const handleNewConversation = () => {
    setActiveConversation(null);
    setMessages([]);
  };

  const handleQuickAction = (prompt) => {
    setInputValue(prompt);
    // Focus the input
  };

  const handleStop = () => {
    setIsLoading(false);
  };

  return (
    <div className="flex h-screen bg-[var(--color-bg-primary)] overflow-hidden">
      {/* Mobile Menu Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)]"
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
          onSelectConversation={setActiveConversation}
          onNewConversation={handleNewConversation}
        />
      </div>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#9945FF] to-[#14F195] flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-[var(--color-text-primary)] font-[var(--font-heading)]">
                Social Sol AI
              </h1>
              <p className="text-xs text-[var(--color-text-muted)]">
                Your AI-powered social media agent
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[var(--color-brand-secondary)]/10 text-[var(--color-brand-secondary)] text-xs font-medium">
              <Zap className="w-3 h-3" />
              Online
            </span>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {messages.length === 0 ? (
            /* Empty State */
            <div className="h-full flex flex-col items-center justify-center px-4 py-12">
              <div className="max-w-2xl mx-auto text-center">
                {/* Hero */}
                <div className="mb-8">
                  <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#9945FF] to-[#14F195] 
                                flex items-center justify-center shadow-2xl shadow-[#9945FF]/30">
                    <Sparkles className="w-10 h-10 text-white" />
                  </div>
                  <h2 className="text-3xl font-bold text-[var(--color-text-primary)] mb-3 font-[var(--font-heading)]">
                    Welcome to Social Sol AI
                  </h2>
                  <p className="text-[var(--color-text-secondary)] text-lg max-w-md mx-auto">
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
                  onRegenerate={() => {}}
                />
              ))}
              
              {/* Loading Indicator */}
              {isLoading && (
                <div className="py-6 px-4 md:px-8 lg:px-16">
                  <div className="max-w-3xl mx-auto flex gap-4 md:gap-6">
                    <div className="w-9 h-9 rounded-xl bg-[var(--color-bg-elevated)] border border-[var(--color-border)] 
                                  flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-5 h-5 text-[var(--color-brand-secondary)]" />
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-[var(--color-brand-secondary)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 bg-[var(--color-brand-secondary)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 bg-[var(--color-brand-secondary)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                      <span className="text-sm text-[var(--color-text-muted)]">Thinking...</span>
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
        />
      </main>
    </div>
  );
};

export default AgentChat;

