import { useState } from 'react';
import Chatbot from '@/components/Chatbot';

function App() {
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);

  const toggleWidget = () => {
    setIsWidgetOpen(!isWidgetOpen);
  };

  return (
    <div className="relative min-h-screen">
      <button
        className="chat-button"
        onClick={toggleWidget}
      >
        💬
      </button>

      {isWidgetOpen && (
        <div className="chat-widget">
          <header className="sticky top-0 z-20 bg-primary-blue text-white p-4 flex justify-between items-center rounded-t-2xl">
            <div className="flex items-center gap-2">
              <a href="https://codeawake.com">
                <span className="text-lg font-semibold">NQ</span>
              </a>
              <h1 className="text-lg font-semibold">NeuraQueen</h1>
            </div>
            <button onClick={toggleWidget} className="text-white">
              ✕
            </button>
          </header>
          <Chatbot />
        </div>
      )}
    </div>
  );
}

export default App;