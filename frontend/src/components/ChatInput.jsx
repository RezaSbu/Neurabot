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
            className="block w-full max-h-[80px] py-1 px-2 pr-8 bg-white rounded-xl resize-none placeholder:text-gray-500 placeholder:text-sm text-sm"
            ref={textareaRef}
            rows="1"
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="absolute top-1/2 -translate-y-1/2 right-1 p-1"
            onClick={submitNewMessage}
          >
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInput;