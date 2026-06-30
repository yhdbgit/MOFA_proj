/**
 * AI 상담 화면과 Spring Boot backend 사이의 HTTP 통신을 담당한다.
 *
 * API CONTRACT:
 * - POST /api/chats
 * - POST /api/chats/{chatId}/messages
 *
 * Mobile UI still uses { role, text }, while backend uses { senderType, content }.
 */
import { getOrCreateCitizenId } from './deviceIdentityStore';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8080';
const DEFAULT_COUNTRY_CODE = 'JP';

const API_BASE_URL = trimTrailingSlash(
  process.env.EXPO_PUBLIC_MOFA_API_BASE_URL ?? DEFAULT_API_BASE_URL,
);

const COUNTRY_CODE =
  process.env.EXPO_PUBLIC_MOFA_COUNTRY_CODE ?? DEFAULT_COUNTRY_CODE;

// NOTE: 백엔드 내부 제한 시간이 아닌 프론트엔드의 최대 대기 시간이다.
const REQUEST_TIMEOUT_MS = 120000;

function trimTrailingSlash(value) {
  return String(value).replace(/\/+$/, '');
}

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function resolveServerError(payload, fallback) {
  if (typeof payload?.message === 'string') {
    return payload.message;
  }

  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }

  if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
    return '상담 요청 형식이 올바르지 않습니다.';
  }

  return payload?.error ?? fallback;
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  let didTimeout = false;
  let response;
  let payload;
  const timeoutId = setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    response = await fetch(buildUrl(path), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
    });

    payload = await response.json().catch(() => ({}));
  } catch (error) {
    // Expo fetch는 환경에 따라 AbortError 대신
    // "Fetch request has been canceled" TypeError를 반환할 수 있다.
    if (didTimeout || error.name === 'AbortError') {
      throw new Error(
        '상담 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요.',
      );
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw new Error(
      resolveServerError(payload, `상담 서버 요청에 실패했습니다. (${response.status})`),
    );
  }

  return payload;
}

export async function createConsularChatSession() {
  const citizenId = await getOrCreateCitizenId();
  const payload = await requestJson('/api/chats', {
    method: 'POST',
    body: JSON.stringify({
      citizenId,
      countryCode: COUNTRY_CODE,
    }),
  });

  if (typeof payload.id !== 'string' || payload.id.trim().length === 0) {
    throw new Error('상담 서버에서 채팅방 ID를 받지 못했습니다.');
  }

  return payload;
}

/**
 * 사용자의 메시지를 Spring Boot backend에 저장하고 agent 답변 문자열을 반환한다.
 *
 * @param {{ chatId?: string | null, text: string }} params
 * @returns {Promise<{ chatId: string, reply: string, agentResult: object | null }>}
 */
export async function sendConsularChatMessage({ chatId, text }) {
  const activeChat =
    typeof chatId === 'string' && chatId.trim().length > 0
      ? { id: chatId }
      : await createConsularChatSession();

  const payload = await requestJson(`/api/chats/${activeChat.id}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      senderType: 'CITIZEN',
      content: text,
    }),
  });

  const agentResult = payload.agentResult ?? null;
  const reply = agentResult?.citizenReply;

  if (typeof reply !== 'string' || reply.trim().length === 0) {
    throw new Error(
      agentResult?.errorMessage ??
        '상담 서버에서 답변을 받지 못했습니다.',
    );
  }

  return {
    chatId: activeChat.id,
    reply: reply.trim(),
    agentResult,
  };
}
