// Database/frontend/api.js

const BASE_URL = import.meta.env.VITE_API_URL + '/admin';

export async function fetchChats() {
  const res = await fetch(`${BASE_URL}/chats`);
  if (!res.ok) throw new Error('Failed to load chats');
  return await res.json();
}

export async function deleteChat(chatId) {
  const res = await fetch(`${BASE_URL}/chats/${chatId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete chat');
  return await res.json();
}

export async function fetchStats() {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to load stats');
  return await res.json();
}
