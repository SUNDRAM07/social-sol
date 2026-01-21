import { useState } from 'react';
import { User, Bot, Copy, Check, RefreshCw, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react';
import ChatActionCard from './ChatActionCard';

const ChatMessage = ({
  message,
  isStreaming = false,
  onRegenerate,
  onCopy,
  onSendMessage,
  onAction
}) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  const handleFeedback = (type) => {
    setFeedback(type);
  };

  // Simple markdown-like rendering
  const renderContent = (text) => {
    if (!text) return null;

    return text.split('\n').map((line, i) => {
      // Bold text
      let processedLine = line.replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>');
      // Inline code
      processedLine = processedLine.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-white/10 text-[#14F195] text-sm font-mono">$1</code>');

      // Headers
      if (line.startsWith('### ')) {
        return <h3 key={i} className="text-lg font-bold text-white mt-4 mb-2" dangerouslySetInnerHTML={{ __html: processedLine.slice(4) }} />;
      }
      if (line.startsWith('## ')) {
        return <h2 key={i} className="text-xl font-bold text-white mt-4 mb-2" dangerouslySetInnerHTML={{ __html: processedLine.slice(3) }} />;
      }
      // Bullet points
      if (line.startsWith('- ') || line.startsWith('• ')) {
        return <li key={i} className="ml-4 text-white/80 list-disc" dangerouslySetInnerHTML={{ __html: processedLine.slice(2) }} />;
      }
      // Numbered lists
      if (/^\d+\.\s/.test(line)) {
        return <li key={i} className="ml-4 text-white/80 list-decimal" dangerouslySetInnerHTML={{ __html: processedLine.replace(/^\d+\.\s/, '') }} />;
      }
      // Blockquotes - styled as post previews
      if (line.startsWith('> ')) {
        return (
          <blockquote key={i} className="border-l-2 border-[#14F195] pl-4 my-2 text-white/90 italic bg-white/5 py-2 rounded-r-lg">
            <span dangerouslySetInnerHTML={{ __html: processedLine.slice(2) }} />
          </blockquote>
        );
      }
      // Table rows (basic support)
      if (line.startsWith('|') && line.endsWith('|')) {
        const cells = line.split('|').filter(c => c.trim());
        const isHeader = i > 0 && text.split('\n')[i - 1]?.includes('---');
        return (
          <div key={i} className="flex gap-4 py-1">
            {cells.map((cell, j) => (
              <span
                key={j}
                className={`flex-1 text-sm ${isHeader ? 'font-semibold text-white' : 'text-white/70'}`}
              >
                {cell.trim()}
              </span>
            ))}
          </div>
        );
      }
      // Horizontal rule / table separator
      if (line.match(/^\|?\s*[-:]+\s*\|/)) {
        return <hr key={i} className="border-white/10 my-2" />;
      }
      // Empty lines
      if (!line.trim()) return <br key={i} />;
      // Regular text
      return <p key={i} className="text-white/80 leading-relaxed" dangerouslySetInnerHTML={{ __html: processedLine }} />;
    });
  };

  return (
    <div
      className={`
        group relative py-6 px-4 md:px-8
        ${isUser ? '' : 'bg-white/[0.02]'}
        transition-colors duration-200
      `}
    >
      <div className="max-w-3xl mx-auto flex gap-4">
        {/* Avatar */}
        <div className={`
          w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0
          ${isUser
            ? 'bg-gradient-to-br from-blue-500 to-purple-600'
            : 'bg-gradient-to-br from-[#9945FF] to-[#14F195] shadow-lg shadow-[#9945FF]/20'}
        `}>
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Role Label */}
          <div className="flex items-center gap-2 mb-2">
            <span className="font-semibold text-white text-sm">
              {isUser ? 'You' : 'Social Sol AI'}
            </span>
            {!isUser && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium 
                             bg-gradient-to-r from-[#9945FF]/20 to-[#14F195]/20 text-[#14F195]
                             border border-[#14F195]/20">
                AI Agent
              </span>
            )}
          </div>

          {/* Message Text */}
          <div className="prose prose-invert max-w-none">
            {renderContent(message.content)}
            {isStreaming && (
              <span className="inline-block w-2 h-5 ml-1 bg-[#14F195] animate-pulse rounded-sm" />
            )}
          </div>

          {/* Action Cards - Only for AI responses with intent */}
          {!isUser && !isStreaming && message.intent && (
            <ChatActionCard
              intent={message.intent}
              data={{
                content: message.content,
                posts: message.posts,
                ideas: message.ideas,
                times: message.times,
                metrics: message.metrics,
                platform: message.entities?.platforms?.[0] || message.platform,
                actions: message.actions,
                ...message.entities, // Spread all entities
              }}
              onSendMessage={onSendMessage}
              onAction={onAction}
            />
          )}

          {/* Quick Actions for responses without specific intent */}
          {!isUser && !isStreaming && !message.intent && message.content && (
            <ChatActionCard
              intent="general_chat"
              data={{ content: message.content }}
              onSendMessage={onSendMessage}
              onAction={onAction}
            />
          )}

          {/* Actions (visible on hover for AI messages) */}
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                          text-xs font-medium text-white/40
                          hover:text-white hover:bg-white/[0.08]
                          transition-all duration-200"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[#14F195]" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy'}</span>
              </button>

              <button
                onClick={onRegenerate}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                          text-xs font-medium text-white/40
                          hover:text-white hover:bg-white/[0.08]
                          transition-all duration-200"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Regenerate</span>
              </button>

              <div className="flex items-center gap-1 ml-2">
                <button
                  onClick={() => handleFeedback('up')}
                  className={`p-1.5 rounded-lg transition-all duration-200
                    ${feedback === 'up'
                      ? 'bg-[#14F195]/20 text-[#14F195]'
                      : 'text-white/30 hover:text-white hover:bg-white/[0.08]'}`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleFeedback('down')}
                  className={`p-1.5 rounded-lg transition-all duration-200
                    ${feedback === 'down'
                      ? 'bg-red-500/20 text-red-400'
                      : 'text-white/30 hover:text-white hover:bg-white/[0.08]'}`}
                >
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

export default ChatMessage;
