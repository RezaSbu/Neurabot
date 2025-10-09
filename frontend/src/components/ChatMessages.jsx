import { memo, useMemo, useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import useAutoScroll from '@/hooks/useAutoScroll';
import Spinner from '@/components/Spinner';

const ErrorIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="red">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4" />
    <path d="M12 16h.01" />
  </svg>
);

function ChatMessages({ messages, isLoading }) {
  const containerRef = useAutoScroll(messages);
  const [visibleCount, setVisibleCount] = useState(15);

  // Debug: Log messages to console to understand the structure
  useEffect(() => {
    if (messages.length > 0) {
      console.log('Messages structure:', messages);
    }
  }, [messages]);

  // Function to clean and format message content
  const formatMessageContent = (content) => {
    if (!content) return '';
    
    // Remove any unwanted formatting characters and normalize whitespace
    return content
      .replace(/\n\s*\n/g, '\n\n') // Normalize multiple newlines
      .replace(/^\s+|\s+$/g, '') // Trim whitespace
      .replace(/\r\n/g, '\n') // Normalize line endings
      .replace(/\r/g, '\n'); // Convert old Mac line endings
  };

  const displayedMessages = useMemo(
    () => messages.slice(-visibleCount),
    [messages, visibleCount]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      if (el.scrollTop === 0 && visibleCount < messages.length) {
        const oldHeight = el.scrollHeight;
        setVisibleCount(prev => Math.min(prev + 10, messages.length));
        requestAnimationFrame(() => {
          const newHeight = el.scrollHeight;
          el.scrollTop = newHeight - oldHeight;
        });
      }
    };

    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, [visibleCount, messages.length]);

  return (
    <div ref={containerRef} className="chat-messages">
      {displayedMessages.map(({ role, content, loading, error, timestamp }, idx) => (
        <div
          key={idx}
          className={`chat-message ${role === 'user' ? 'chat-message-user' : 'chat-message-assistant'}`}
          dir="rtl"
        >
          {/* آواتار چت‌بات و کاربر */}
          {role === 'user' ? (
            <img
              src="/user-avatar.png"
              alt="User"
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            <img
              src="/chatbot2.png"
              alt="Bot"
              className="w-8 h-8 rounded-full object-cover"
            />
          )}

          <div className="flex flex-col text-right text-sm">
            <div className="markdown-container">
              {loading && !content ? (
                <Spinner />
              ) : role === 'assistant' ? (
                <Markdown
                  components={{
                    a: ({ href, children }) => (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-blue underline"
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {formatMessageContent(content)}
                </Markdown>
              ) : (
                <div className="whitespace-pre-wrap break-words">{formatMessageContent(content)}</div>
              )}
            </div>

            {/* زمان پیام */}
            {timestamp && (
              <div className="text-xs text-gray-400 self-end mt-1">
                {new Date(timestamp).toLocaleTimeString('fa-IR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            )}

            {/* نمایش خطا (در صورت وجود) */}
            {error && (
              <div className={`flex items-center gap-1 text-xs text-error-red ${content && 'mt-1'}`}>
                <ErrorIcon />
                <span>خطا در تولید پاسخ 🛑</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default memo(ChatMessages);
