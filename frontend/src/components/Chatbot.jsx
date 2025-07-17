import { useState, useEffect, useRef } from 'react';
import { useImmer } from 'use-immer';
import api from '@/api';
import { parseSSEStream } from '@/utils';
import ChatMessages from '@/components/ChatMessages';
import ChatInput from '@/components/ChatInput';

function Chatbot() {
  const [chatId, setChatId] = useState(() => localStorage.getItem('chatId') || null);
  const [messages, setMessages] = useImmer(() => {
    const savedMessages = localStorage.getItem('messages');
    const savedTime = localStorage.getItem('messagesSavedTime');
    const halfHour = 30 * 60 * 1000;

    if (savedMessages && savedTime && Date.now() - parseInt(savedTime, 10) < halfHour) {
      return JSON.parse(savedMessages);
    } else {
      localStorage.removeItem('messages');
      localStorage.removeItem('chatId');
      localStorage.removeItem('messagesSavedTime');
      return [];
    }
  });
  const [newMessage, setNewMessage] = useState('');
  const streamRef = useRef(null);
  const shouldSaveToLocalStorage = useRef(true);

  const isLoading = messages.length && messages[messages.length - 1].loading;

  // لود پیام‌ها از سرور موقع استارت
  useEffect(() => {
    async function loadMessages() {
      if (chatId) {
        try {
          const serverMessages = await fetch(`http://localhost:8000/chats/${chatId}/messages`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
          }).then(res => res.json());
          setMessages(draft => {
            draft.length = 0; // پاک کردن پیام‌های محلی
            draft.push(...serverMessages.map(msg => ({
              role: msg.role,
              content: msg.content,
              timestamp: new Date().toISOString()
            })));
          });
        } catch (err) {
          console.error('Failed to load messages from server:', err);
        }
      }
    }
    loadMessages();
  }, [chatId]);

  useEffect(() => {
    if (!shouldSaveToLocalStorage.current) return;
    try {
      localStorage.setItem('messages', JSON.stringify(messages));
      localStorage.setItem('messagesSavedTime', Date.now().toString());
    } catch (e) {
      console.warn('Failed to save messages to localStorage:', e);
    }
  }, [messages]);

  useEffect(() => {
    if (chatId) {
      localStorage.setItem('chatId', chatId);
    }
  }, [chatId]);

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.cancel();
        streamRef.current = null;
      }
    };
  }, []);

  const clearChat = () => {
    setMessages([]);
    setChatId(null);
    localStorage.removeItem('messages');
    localStorage.removeItem('chatId');
    localStorage.removeItem('messagesSavedTime');
    if (streamRef.current) {
      streamRef.current.cancel();
      streamRef.current = null;
    }
  };

  async function submitNewMessage() {
    const trimmedMessage = newMessage.trim();
    if (!trimmedMessage || isLoading) return;

    shouldSaveToLocalStorage.current = false;
    const timestamp = new Date().toISOString();

    setMessages(draft => [
      ...draft,
      { role: 'user', content: trimmedMessage, timestamp },
      { role: 'assistant', content: '', sources: [], loading: true, timestamp }
    ]);
    setNewMessage('');

    let chatIdOrNew = chatId;
    try {
      if (!chatId) {
        const { id } = await api.createChat();
        setChatId(id);
        chatIdOrNew = id;
      }

      const recentMessages = messages.slice(-8).concat({
        role: 'user',
        content: trimmedMessage,
        timestamp,
      });

      const stream = await api.sendChatMessage(chatIdOrNew, trimmedMessage, recentMessages);
      streamRef.current = stream;
      let retryCount = 0;
      const maxRetries = 3;
      while (retryCount < maxRetries) {
        try {
          for await (const textChunk of parseSSEStream(stream)) {
            setMessages(draft => {
              draft[draft.length - 1].content += textChunk;
            });
          }
          break;
        } catch (err) {
          retryCount++;
          if (retryCount >= maxRetries) throw err;
          await new Promise(resolve => setTimeout(resolve, 5000)); // Retry after 5s
        }
      }
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
      });
      streamRef.current = null;
    } catch (err) {
      console.error(err);
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
        draft[draft.length - 1].error = true;
      });
      streamRef.current = null;
    } finally {
      shouldSaveToLocalStorage.current = true;
    }
  }

  return (
    <div className="flex flex-col h-full md:h-[550px] overflow-hidden">
      {messages.length === 0 && (
        <div className="p-5 text-center text-gray-700 text-base space-y-3 bg-gray-50">
          <p className="text-lg font-semibold">سلام! 😊</p>
          <p>چطور می‌تونم کمکتون کنم؟ سؤالتون رو بپرسید.</p>
        </div>
      )}
      <div className="flex justify-end p-3 bg-gray-50 border-t border-gray-200">
        <button
          onClick={clearChat}
          className="px-4 py-2 text-sm text-white bg-red-500 rounded-lg hover:bg-red-600 transition duration-200 shadow-sm"
        >
          پاک کردن چت
        </button>
      </div>
      <ChatMessages messages={messages} isLoading={isLoading} />
      <ChatInput
        newMessage={newMessage}
        isLoading={isLoading}
        setNewMessage={setNewMessage}
        submitNewMessage={submitNewMessage}
      />
    </div>
  );
}

export default Chatbot;