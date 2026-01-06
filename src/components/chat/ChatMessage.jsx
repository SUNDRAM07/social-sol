import { useState } from 'react';
import { User, Bot, Copy, Check, RefreshCw, ThumbsUp, ThumbsDown, Sparkles } from 'lucide-react';

const ChatMessage = ({ 
  message, 
  isStreaming = false,
  onRegenerate,
  onCopy 
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

  return (
    <div 
      className={`
        group relative py-6 px-4 md:px-8 lg:px-16
        ${isUser ? 'bg-[var(--color-bg-secondary)]' : 'bg-[var(--color-bg-primary)]'}
        transition-colors duration-200
      `}
    >
      <div className="max-w-3xl mx-auto flex gap-4 md:gap-6">
        {/* Avatar */}
        <div className={`
          w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 mt-1
          ${isUser 
            ? 'bg-gradient-to-br from-[#9945FF] to-[#14F195] shadow-lg shadow-[#9945FF]/20' 
            : 'bg-[var(--color-bg-elevated)] border border-[var(--color-border)]'}
        `}>
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Sparkles className="w-5 h-5 text-[var(--color-brand-secondary)]" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Role Label */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-semibold text-[var(--color-text-primary)]">
              {isUser ? 'You' : 'Social Sol AI'}
            </span>
            {!isUser && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium 
                             bg-[var(--color-brand-primary)]/10 text-[var(--color-brand-primary)]
                             border border-[var(--color-brand-primary)]/20">
                AI Agent
              </span>
            )}
          </div>

          {/* Message Text */}
          <div className="prose prose-invert prose-sm max-w-none">
            <div className="text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">
              {message.content}
              {isStreaming && (
                <span className="inline-block w-0.5 h-5 ml-1 bg-[var(--color-brand-primary)] animate-pulse" />
              )}
            </div>
          </div>

          {/* Generated Content Preview (for AI responses with content) */}
          {!isUser && message.generatedContent && (
            <div className="mt-4 p-4 rounded-xl bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-[var(--color-brand-secondary)]" />
                <span className="text-xs font-medium text-[var(--color-text-secondary)]">
                  Generated Content
                </span>
              </div>
              <div className="text-sm text-[var(--color-text-primary)]">
                {message.generatedContent}
              </div>
            </div>
          )}

          {/* Actions (visible on hover for AI messages) */}
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                          text-xs font-medium text-[var(--color-text-muted)]
                          hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]
                          transition-all duration-200"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied!' : 'Copy'}</span>
              </button>

              <button
                onClick={onRegenerate}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg
                          text-xs font-medium text-[var(--color-text-muted)]
                          hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]
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
                      ? 'bg-green-500/20 text-green-400' 
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]'}`}
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => handleFeedback('down')}
                  className={`p-1.5 rounded-lg transition-all duration-200
                    ${feedback === 'down' 
                      ? 'bg-red-500/20 text-red-400' 
                      : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]'}`}
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


