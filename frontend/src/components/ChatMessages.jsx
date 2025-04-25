import Markdown from 'react-markdown';
import useAutoScroll from '@/hooks/useAutoScroll';
import Spinner from '@/components/Spinner';
import userIcon from '@/assets/images/user.svg';
import errorIcon from '@/assets/images/error.svg';

function ChatMessages({ messages, isLoading }) {
  const scrollContentRef = useAutoScroll(isLoading);

  return (
    <div ref={scrollContentRef} className="chat-messages grow space-y-4 px-2 overflow-y-auto">
      {messages.map(({ role, content, loading, error }, idx) => (
        <div
          key={idx}
          className={`flex flex-row-reverse items-start gap-4 py-3 px-2 rounded-xl ${
            role === 'user' ? 'bg-primary-blue/10' : ''
          }`}
          dir="rtl"
        >
          {role === 'user' && (
            <img
              className="h-[20px] w-[20px] shrink-0"
              src={userIcon}
              alt="user"
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
                        className="text-primary-blue underline hover:text-primary-blue/80"
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
              <div
                className={`flex items-center gap-1 text-xs text-error-red ${
                  content && 'mt-1'
                }`}
              >
                <img className="h-4 w-4" src={errorIcon} alt="error" />
                <span>خطا در تولید پاسخ 🛑</span>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default ChatMessages;