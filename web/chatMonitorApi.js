import { buildBackendUrl } from './config.js';

const CHAT_MESSAGES_URL = buildBackendUrl('/chat/messages');

export async function fetchLatestChatMessages() {
  const response = await fetch(CHAT_MESSAGES_URL, {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new Error(`상담 조회 실패 (${response.status})`);
  }

  const payload = await response.json();

  if (!Array.isArray(payload.messages)) {
    throw new Error('상담 메시지 응답 형식이 올바르지 않습니다.');
  }

  return payload.messages.filter(
    (message) =>
      (message?.role === 'user' || message?.role === 'assistant') &&
      typeof message?.text === 'string' &&
      message.text.trim().length > 0,
  );
}
