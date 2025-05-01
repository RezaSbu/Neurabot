import { memo, useMemo } from 'react';
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
  const scrollContentRef = useAutoScroll(messages);
  const displayedMessages = useMemo(() => messages.slice(-15), [messages]);

  return (
    <div ref={scrollContentRef} className="chat-messages">
      {displayedMessages.map(({ role, content, loading, error }, idx) => (
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