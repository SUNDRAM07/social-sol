import { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Mic, Image, Sparkles, StopCircle } from 'lucide-react';

const ChatInput = ({ 
  onSend, 
  isLoading = false,
  onStop,
  placeholder = "Ask me to create posts, schedule campaigns, analyze trends...",
  disabled = false,
  value,
  onChange
}) => {
  // Support both controlled and uncontrolled modes
  const [internalMessage, setInternalMessage] = useState('');
  const message = value !== undefined ? value : internalMessage;
  const setMessage = onChange || setInternalMessage;
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [message]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim());
      setMessage('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="p-4 md:p-6 bg-gradient-to-t from-[var(--color-bg-primary)] via-[var(--color-bg-primary)] to-transparent">
      <div className="max-w-3xl mx-auto">
        {/* Input Container */}
        <form onSubmit={handleSubmit}>
          <div 
            className={`
              relative flex items-end gap-2 p-2 rounded-2xl
              bg-[var(--color-bg-tertiary)] 
              border transition-all duration-300
              ${isFocused 
                ? 'border-[var(--color-brand-primary)] shadow-lg shadow-[var(--color-brand-primary)]/10' 
                : 'border-[var(--color-border)] hover:border-[var(--color-border-hover)]'}
            `}
          >
            {/* Attachment Button */}
            <button
              type="button"
              className="p-2.5 rounded-xl text-[var(--color-text-muted)] 
                        hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]
                        transition-all duration-200 flex-shrink-0"
              title="Attach file"
            >
              <Paperclip className="w-5 h-5" />
            </button>

            {/* Text Input */}
            <textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              className="flex-1 bg-transparent text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)]
                        text-base leading-relaxed resize-none py-2.5 px-1
                        focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed
                        min-h-[44px] max-h-[200px]"
            />

            {/* Image Button */}
            <button
              type="button"
              className="p-2.5 rounded-xl text-[var(--color-text-muted)] 
                        hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface)]
                        transition-all duration-200 flex-shrink-0"
              title="Add image"
            >
              <Image className="w-5 h-5" />
            </button>

            {/* Send/Stop Button */}
            {isLoading ? (
              <button
                type="button"
                onClick={onStop}
                className="p-3 rounded-xl bg-red-500 text-white
                          hover:bg-red-600 transition-all duration-200 flex-shrink-0"
                title="Stop generating"
              >
                <StopCircle className="w-5 h-5" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!message.trim() || disabled}
                className={`
                  p-3 rounded-xl flex-shrink-0 transition-all duration-200
                  ${message.trim() && !disabled
                    ? 'bg-gradient-to-r from-[#9945FF] to-[#14F195] text-white shadow-lg shadow-[#9945FF]/30 hover:shadow-[#9945FF]/50 hover:scale-105'
                    : 'bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] cursor-not-allowed'}
                `}
                title="Send message"
              >
                <Send className="w-5 h-5" />
              </button>
            )}
          </div>
        </form>

        {/* Hint Text */}
        <div className="flex items-center justify-center gap-2 mt-3 text-xs text-[var(--color-text-muted)]">
          <Sparkles className="w-3 h-3 text-[var(--color-brand-primary)]" />
          <span>Press Enter to send, Shift + Enter for new line</span>
        </div>
      </div>
    </div>
  );
};

export default ChatInput;

