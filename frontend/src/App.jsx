import { useState } from 'react';
import Chatbot from '@/components/Chatbot';
import logo from '@/assets/images/logo.svg';

function App() {
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);

  const toggleWidget = () => {
    setIsWidgetOpen(!isWidgetOpen);
  };

  return (
    <div className="relative min-h-screen">
      {/* دکمه شناور برای باز کردن ویجت */}
      <button
        className="fixed bottom-4 right-4 z-50 p-3 bg-primary-blue rounded-full shadow-lg hover:bg-primary-blue/80 transition"
        onClick={toggleWidget}
      >
        💬
      </button>

      {/* ویجت چت‌بات */}
      {isWidgetOpen && (
        <div className="fixed bottom-16 right-4 w-96 max-h-[600px] bg-white rounded-lg shadow-xl z-50 flex flex-col">
          <header className="sticky top-0 z-20 bg-white border-b p-4 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <a href="https://codeawake.com">
              </a>
              <h1 className="font-urbanist text-lg font-semibold">NeuraQueen</h1>
            </div>
            <button onClick={toggleWidget} className="text-gray-500 hover:text-gray-700">
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