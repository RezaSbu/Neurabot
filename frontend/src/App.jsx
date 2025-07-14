// frontend/src/App.jsx

import { useState, useEffect } from 'react';
import Chatbot from '@/components/Chatbot';
import AdminPanel from '../../Database/frontend/AdminPanel';

function App() {
  const [isAdminView, setIsAdminView] = useState(false);
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('admin') === 'true') {
      setIsAdminView(true);
    }
  }, []);

  if (isAdminView) {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <h1 className="text-xl font-bold mb-4">🛠 پنل مدیریت NeuraQueen</h1>
        <AdminPanel />
      </div>
    );
  }

  // حالت معمولی: چت‌بات شناور
  const toggleWidget = () => setIsWidgetOpen(!isWidgetOpen);

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
          <header className="sticky top-0 z-20 bg-blue-700 text-white p-4 flex justify-between items-center rounded-t-3xl">
            <div className="flex items-center gap-2">
              <a href="https://codeawake.com">
                <span className="text-lg font-bold">NQ</span>
              </a>
              <h1 className="text-lg font-semibold">Chat with NeuraQueen AI</h1>
            </div>
            <button onClick={toggleWidget} className="text-white hover:text-gray-300 transition">
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
