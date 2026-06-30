import { buildBackendUrl } from './config.js';

const CHAT_LIST_URL = buildBackendUrl('/api/chats');
const EVENT_STREAM_URL = buildBackendUrl('/api/events/stream');
const CITIZEN_PROFILE_URL = buildBackendUrl('/api/citizen-profile');

async function requestJson(url, fallbackMessage) {
  const response = await fetch(url, {
    cache: 'no-store',
  });

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(payload?.message || `${fallbackMessage} (${response.status})`);
  }

  return payload;
}

function toWebRole(senderType) {
  if (senderType === 'CITIZEN') {
    return 'user';
  }

  if (senderType === 'STAFF') {
    return 'staff';
  }

  return 'assistant';
}

function toSenderLabel(senderType) {
  if (senderType === 'CITIZEN') {
    return '민원인';
  }

  if (senderType === 'STAFF') {
    return '담당자';
  }

  return 'AI 상담사';
}

function normalizeMessage(message) {
  return {
    id: message.id,
    role: toWebRole(message.senderType),
    senderType: message.senderType,
    senderLabel: toSenderLabel(message.senderType),
    text: message.content,
    createdAt: message.createdAt,
  };
}

export function normalizeChat(chat) {
  const messages = Array.isArray(chat?.messages)
    ? chat.messages
        .filter(
          (message) =>
            typeof message?.id === 'string' &&
            typeof message?.content === 'string' &&
            message.content.trim().length > 0,
        )
        .map(normalizeMessage)
    : [];

  return {
    id: chat.id,
    citizenId: chat.citizenId,
    countryCode: chat.countryCode,
    status: chat.status,
    createdAt: chat.createdAt,
    messages,
  };
}

export async function fetchChatList() {
  const payload = await requestJson(CHAT_LIST_URL, '상담 목록 조회 실패');

  if (!Array.isArray(payload)) {
    throw new Error('상담 목록 응답 형식이 올바르지 않습니다.');
  }

  return payload.map(normalizeChat);
}

export async function fetchChat(chatId) {
  const payload = await requestJson(
    buildBackendUrl(`/api/chats/${chatId}`),
    '상담 상세 조회 실패',
  );

  return normalizeChat(payload);
}

export async function fetchCitizenProfile(citizenId) {
  const response = await fetch(CITIZEN_PROFILE_URL, {
    cache: 'no-store',
    headers: {
      'X-Citizen-Id': citizenId,
    },
  });

  if (response.status === 404) {
    return null;
  }

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(payload?.message || `기본 정보 조회 실패 (${response.status})`);
  }

  return payload;
}

export function openChatEventStream({ onEvent, onOpen, onError }) {
  const source = new EventSource(EVENT_STREAM_URL);
  const eventNames = [
    'CONNECTED',
    'CHAT_CREATED',
    'CHAT_MESSAGE_CREATED',
    'AGENT_RESULT_READY',
  ];

  source.onopen = () => {
    onOpen?.();
  };

  source.onerror = (event) => {
    onError?.(event);
  };

  eventNames.forEach((eventName) => {
    source.addEventListener(eventName, (event) => {
      onEvent?.({
        name: eventName,
        data: event.data,
      });
    });
  });

  return source;
}
