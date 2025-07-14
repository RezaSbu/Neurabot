import { memo, useMemo, useState, useEffect } from 'react';
import Markdown from 'react-markdown';
import useAutoScroll from '@/hooks/useAutoScroll';
import Spinner from '@/components/Spinner';

const UserIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const ErrorIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="red">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4" />
    <path d="M12 16h.01" />
  </svg>
);

function ChatMessages({ messages, isLoading }) {
  // ref برای اسکرول خودکار به پایین
  const containerRef = useAutoScroll(messages);

  // تعداد پیام‌های قابل نمایش فعلی
  const [visibleCount, setVisibleCount] = useState(15);

  // برش آخرین visibleCount پیام
  const displayedMessages = useMemo(
    () => messages.slice(-visibleCount),
    [messages, visibleCount]
  );

  // مدیریت infinite scroll هنگام اسکرول به بالای کانتینر
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      if (el.scrollTop === 0 && visibleCount < messages.length) {
        const oldHeight = el.scrollHeight;
        setVisibleCount(prev => Math.min(prev + 10, messages.length));
        // بعد از رندر مجدد، حفظ موقعیت اسکرول
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
          {role === 'user' && <UserIcon />}
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
                  {content}
                </Markdown>
              ) : (
                <div className="whitespace-pre-line">{content}</div>
              )}
            </div>
            {/* نمایش تایم‌استمپ */}
            {timestamp && (
              <div className="text-xs text-gray-400 self-end mt-1">
                {new Date(timestamp).toLocaleTimeString('fa-IR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            )}
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
