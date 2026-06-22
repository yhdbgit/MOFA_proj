/**
 * AI 상담 화면과 백엔드 사이의 HTTP 통신을 한곳에서 담당한다.
 *
 * API CONTRACT:
 * - 성공 응답: { reply: string }
 */
const DEFAULT_CHAT_API_URL = 'http://127.0.0.1:8787/chat';

// NOTE: 실제 휴대폰에서는 127.0.0.1이 휴대폰 자신을 가리키므로
// EXPO_PUBLIC_CONSULAR_CHAT_API_URL에 개발 PC 또는 배포 서버 주소를 지정해야 한다.
const CHAT_API_URL =
  process.env.EXPO_PUBLIC_CONSULAR_CHAT_API_URL ?? DEFAULT_CHAT_API_URL;

// NOTE: 백엔드 내부 제한 시간이 아닌 프론트엔드의 최대 대기 시간이다.
const REQUEST_TIMEOUT_MS = 120000;

// FastAPI의 detail 형식과 일반 error 형식을 화면에서 사용할 한 문장으로 통일한다.
function resolveServerError(payload) {
  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }

  if (Array.isArray(payload?.detail) && payload.detail.length > 0) {
    return '상담 요청 형식이 올바르지 않습니다.';
  }

  return payload?.error ?? '상담 서버 응답을 처리하지 못했습니다.';
}

/**
 * 현재 채팅 내역을 백엔드에 전달하고 상담 답변 문자열을 반환한다.
 *
 * @param {Array<{role: 'user'|'assistant', text: string}>} messages
 * @returns {Promise<string>} 공백을 제거한 백엔드 reply
 * @throws {Error} HTTP 오류, 잘못된 응답 또는 120초 초과 시 사용자용 오류
 */
export async function sendConsularChatMessage(messages) {
  const controller = new AbortController();
  let didTimeout = false;
  const timeoutId = setTimeout(() => {
    didTimeout = true;
    controller.abort();
  }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
      signal: controller.signal,
    });

    // 오류 응답이 JSON이 아니어도 아래 공통 오류 처리까지 진행한다.
    const payload = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(resolveServerError(payload));
    }

    if (typeof payload.reply !== 'string' || payload.reply.trim().length === 0) {
      throw new Error('상담 서버에서 답변을 받지 못했습니다.');
    }

    return payload.reply.trim();
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
}
