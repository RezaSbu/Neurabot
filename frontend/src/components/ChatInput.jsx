import useAutosize from '@/hooks/useAutosize';

const SendIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);

function ChatInput({ newMessage, isLoading, setNewMessage, submitNewMessage }) {
  const textareaRef = useAutosize(newMessage);

  function handleKeyDown(e) {
    if (e.keyCode === 13 && !e.shiftKey && !isLoading) {
      e.preventDefault();
      submitNewMessage();
    }
  }

  return (
    <div className="sticky bottom-0 bg-white py-1 px-2">
      <div className="p-1 bg-gray-100 rounded-xl">
        <div className="bg-white relative rounded-xl ring-1 ring-gray-300">
          <textarea
            className="block w-full max-h-[100px] py-2 px-4 pr-10 bg-white rounded-xl resize-none placeholder:text-gray-500 placeholder:text-base text-gray-800 text-base focus:ring-2 focus:ring-blue-500 transition duration-200"
            ref={textareaRef}
            rows="1"
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="پیام خود را بنویسید..."
            maxLength={5000}
          />
          <button
            className="absolute top-1/2 -translate-y-1/2 right-1 p-1"
            onClick={submitNewMessage}
          >
            <SendIcon />
          </button>
        </div>
        {newMessage.length > 4900 && (
          <p className="text-xs text-red-500 mt-1 text-right">
            {5000 - newMessage.length} کاراکتر باقی‌مانده
          </p>
        )}
      </div>
    </div>
  );
}

export default ChatInput;