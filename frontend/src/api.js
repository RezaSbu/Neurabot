const BASE_URL = import.meta.env.VITE_API_URL;

// تولید session_id یک‌بار و ذخیره در localStorage
function getSessionId() {
  let id = localStorage.getItem('session_id');
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem('session_id', id);
  }
  return id;
}

async function createChat() {
  const sessionId = getSessionId();
  const res = await fetch(BASE_URL + '/chats', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId
    }
  });
  const data = await res.json();
  if (!res.ok) {
    return Promise.reject({ status: res.status, data });
  }
  return data;
}

async function sendChatMessage(chatId, message, recentMessages = []) {
  const sessionId = getSessionId();
  const res = await fetch(BASE_URL + `/chats/${chatId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-ID': sessionId
    },
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
