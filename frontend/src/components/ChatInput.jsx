import useAutosize from '@/hooks/useAutosize';
import sendIcon from '@/assets/images/send.svg';

function ChatInput({ newMessage, isLoading, setNewMessage, submitNewMessage }) {
  const textareaRef = useAutosize(newMessage);

  function handleKeyDown(e) {
    if (e.keyCode === 13 && !e.shiftKey && !isLoading) {
      e.preventDefault();
      submitNewMessage();
    }
  }

  return (
    <div className="sticky bottom-0 shrink-0 bg-white py-2 px-3">
      <div className="p-1 bg-primary-blue/35 rounded-2xl z-50 font-mono">
        <div className="pr-0.5 bg-white relative shrink-0 rounded-2xl overflow-hidden ring-primary-blue ring-1 focus-within:ring-2 transition-all">
          <textarea
            className="block w-full max-h-[100px] py-1.5 px-3 pr-10 bg-white rounded-2xl resize-none placeholder:text-primary-blue placeholder:text-sm focus:outline-none text-sm"
            ref={textareaRef}
            rows="1"
            value={newMessage}
            onChange={e => setNewMessage(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="absolute top-1/2 -translate-y-1/2 right-2 p-1 rounded-md hover:bg-primary-blue/20"
            onClick={submitNewMessage}
          >
            <img src={sendIcon} alt="send" className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default ChatInput;