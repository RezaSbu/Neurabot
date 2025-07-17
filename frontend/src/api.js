const BASE_URL = import.meta.env.VITE_API_URL;

async function getToken() {
  const res = await fetch(BASE_URL + '/token', { method: 'POST' });
  const data = await res.json();
  return data.access_token;
}

let token = localStorage.getItem('token');
if (!token) {
  token = await getToken();
  localStorage.setItem('token', token);
}

async function createChat() {
  const res = await fetch(BASE_URL + '/chats', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  if (!res.ok) {
    return Promise.reject({ status: res.status, data });
  }
  return data;
}

async function sendChatMessage(chatId, message, recentMessages = []) {
  const res = await fetch(BASE_URL + `/chats/${chatId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
    body: JSON.stringify({ message, recentMessages })
  });
  if (!res.ok) {
    return Promise.reject({ status: res.status, data: await res.json() });
  }
  return res.body;
}

export default {
  createChat, sendChatMessage
};