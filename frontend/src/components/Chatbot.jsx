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
    const halfHour = 30 * 60 * 1000; // نیم ساعت به میلی‌ثانیه

    // بررسی زمان ذخیره
    if (savedMessages && savedTime && Date.now() - parseInt(savedTime) < halfHour) {
      return JSON.parse(savedMessages).slice(-10); // محدود به 10 پیام
    } else {
      // پاک کردن اگر زمان گذشته باشد
      localStorage.removeItem('messages');
      localStorage.removeItem('chatId');
      localStorage.removeItem('messagesSavedTime');
      return [];
    }
  });
  const [newMessage, setNewMessage] = useState('');
  const streamRef = useRef(null);
  const shouldSaveToLocalStorage = useRef(true); // کنترل ذخیره‌سازی

  const isLoading = messages.length && messages[messages.length - 1].loading;

  // ذخیره messages با زمان
  useEffect(() => {
    if (!shouldSaveToLocalStorage.current) return;

    if (messages.length > 10) {
      setMessages(draft => draft.slice(-10));
    }
    try {
      localStorage.setItem('messages', JSON.stringify(messages));
      localStorage.setItem('messagesSavedTime', Date.now().toString()); // ذخیره زمان
    } catch (e) {
      console.warn('Failed to save messages to localStorage:', e);
    }
  }, [messages]);

  useEffect(() => {
    if (chatId) {
      localStorage.setItem('chatId', chatId);
    }
  }, [chatId]);

  // تمیز کردن استریم
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.cancel();
        streamRef.current = null;
      }
    };
  }, []);

  // تابع برای پاک کردن چت
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

    // غیرفعال کردن ذخیره‌سازی موقت برای کاهش بار
    shouldSaveToLocalStorage.current = false;

    setMessages(draft => [
      ...draft,
      { role: 'user', content: trimmedMessage },
      { role: 'assistant', content: '', sources: [], loading: true },
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
      });

      const stream = await api.sendChatMessage(chatIdOrNew, trimmedMessage, recentMessages);
      streamRef.current = stream;
      for await (const textChunk of parseSSEStream(stream)) {
        setMessages(draft => {
          draft[draft.length - 1].content += textChunk;
        });
      }
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
      });
      streamRef.current = null;
    } catch (err) {
      console.log(err);
      setMessages(draft => {
        draft[draft.length - 1].loading = false;
        draft[draft.length - 1].error = true;
      });
      streamRef.current = null;
    } finally {
      shouldSaveToLocalStorage.current = true; // فعال کردن ذخیره‌سازی پس از اتمام
    }
  }

  return (
    <div className="flex flex-col h-[550px] overflow-hidden">
      {messages.length === 0 && (
        <div className="p-4 text-primary-blue text-sm space-y-2">
          <p>👋 سلام!</p>
          <p>سوالتو بپرس آنلاین پاسخگو هستیم.</p>
        </div>
      )}
      <div className="flex justify-between p-2 bg-gray-50">
        <button
          onClick={clearChat}
          className="px-3 py-1 text-sm text-white bg-red-500 rounded-md hover:bg-red-600"
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