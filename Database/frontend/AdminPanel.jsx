// Database/frontend/AdminPanel.jsx

import { useEffect, useState } from 'react';
import { fetchChats, deleteChat, fetchStats } from './api';

function AdminPanel() {
  const [chats, setChats] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [chatList, statData] = await Promise.all([
        fetchChats(),
        fetchStats()
      ]);
      setChats(chatList);
      setStats(statData);
    } catch (err) {
      console.error('Error loading admin data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (chatId) => {
    if (!window.confirm(`آیا مطمئنی می‌خواهی چت ${chatId} را حذف کنی؟`)) return;
    try {
      await deleteChat(chatId);
      setChats(prev => prev.filter(chat => chat.id !== chatId));
    } catch (err) {
      alert('خطا در حذف چت');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold">📊 پنل مدیریت NeuraQueen</h1>

      {stats && (
        <div className="bg-gray-100 p-4 rounded-lg shadow">
          <p>تعداد کل چت‌ها: <strong>{stats.total_chats}</strong></p>
          <p>میانگین پیام در هر چت: <strong>{stats.average_messages_per_chat}</strong></p>
        </div>
      )}

      <div className="overflow-x-auto bg-white shadow rounded-lg">
        <table className="min-w-full divide-y divide-gray-200 text-right">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2">شناسه چت</th>
              <th className="px-4 py-2">تعداد پیام</th>
              <th className="px-4 py-2">زمان شروع</th>
              <th className="px-4 py-2">عملیات</th>
            </tr>
          </thead>
          <tbody>
            {chats.map(chat => (
              <tr key={chat.id} className="border-b">
                <td className="px-4 py-2 font-mono text-sm">{chat.id}</td>
                <td className="px-4 py-2">{chat.messages?.length || 0}</td>
                <td className="px-4 py-2">
                  {new Date(chat.created * 1000).toLocaleString('fa-IR')}
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => handleDelete(chat.id)}
                    className="text-red-600 hover:underline"
                  >
                    حذف
                  </button>
                </td>
              </tr>
            ))}
            {chats.length === 0 && !loading && (
              <tr><td colSpan="4" className="text-center py-4">چتی یافت نشد</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {loading && <p>در حال بارگذاری...</p>}
    </div>
  );
}

export default AdminPanel;
