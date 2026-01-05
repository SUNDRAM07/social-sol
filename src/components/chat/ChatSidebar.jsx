import { useState } from 'react';
import { Plus, MessageSquare, Search, Settings, Sparkles, MoreHorizontal, Trash2, Edit2 } from 'lucide-react';

const ChatSidebar = ({ 
  conversations = [], 
  activeConversation, 
  onSelectConversation, 
  onNewConversation,
  onDeleteConversation,
  collapsed = false 
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  const filteredConversations = conversations.filter(conv => 
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group conversations by date
  const groupedConversations = filteredConversations.reduce((groups, conv) => {
    const date = new Date(conv.updatedAt);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    let group;
    if (date.toDateString() === today.toDateString()) {
      group = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      group = 'Yesterday';
    } else if (date > new Date(today.setDate(today.getDate() - 7))) {
      group = 'Previous 7 Days';
    } else {
      group = 'Older';
    }
    
    if (!groups[group]) groups[group] = [];
    groups[group].push(conv);
    return groups;
  }, {});

  if (collapsed) return null;

  return (
    <aside className="w-72 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-[var(--color-border)]">
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                     bg-gradient-to-r from-[#9945FF] to-[#14F195] 
                     text-white font-semibold text-sm
                     hover:opacity-90 transition-all duration-200
                     shadow-lg shadow-[#9945FF]/20 hover:shadow-[#9945FF]/30"
        >
          <Plus className="w-5 h-5" />
          <span>New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg
                       bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]
                       text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                       focus:outline-none focus:border-[var(--color-brand-primary)]
                       transition-colors duration-200"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-2 pb-4">
        {Object.entries(groupedConversations).map(([group, convs]) => (
          <div key={group} className="mb-4">
            <h3 className="px-3 py-2 text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
              {group}
            </h3>
            <div className="space-y-1">
              {convs.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => onSelectConversation(conv.id)}
                  onMouseEnter={() => setHoveredId(conv.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  className={`
                    group relative flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer
                    transition-all duration-200
                    ${activeConversation === conv.id 
                      ? 'bg-[var(--color-surface-active)] border border-[var(--color-brand-primary)]/30' 
                      : 'hover:bg-[var(--color-surface)] border border-transparent'}
                  `}
                >
                  <div className={`
                    w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0
                    ${activeConversation === conv.id 
                      ? 'bg-gradient-to-br from-[#9945FF] to-[#14F195]' 
                      : 'bg-[var(--color-bg-elevated)]'}
                  `}>
                    <MessageSquare className="w-4 h-4 text-white" />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                      {conv.title}
                    </p>
                    <p className="text-xs text-[var(--color-text-muted)] truncate">
                      {conv.preview}
                    </p>
                  </div>

                  {/* Actions */}
                  {hoveredId === conv.id && (
                    <div className="absolute right-2 flex items-center gap-1">
                      <button 
                        onClick={(e) => { e.stopPropagation(); onDeleteConversation?.(conv.id); }}
                        className="p-1.5 rounded-md hover:bg-[var(--color-bg-hover)] text-[var(--color-text-muted)] hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {filteredConversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="w-12 h-12 rounded-full bg-[var(--color-bg-tertiary)] flex items-center justify-center mb-3">
              <Sparkles className="w-6 h-6 text-[var(--color-brand-primary)]" />
            </div>
            <p className="text-sm text-[var(--color-text-secondary)]">
              {searchQuery ? 'No conversations found' : 'Start a new conversation'}
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg
                          text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]
                          hover:bg-[var(--color-surface)] transition-all duration-200">
          <Settings className="w-5 h-5" />
          <span className="text-sm font-medium">Settings</span>
        </button>
      </div>
    </aside>
  );
};

export default ChatSidebar;

