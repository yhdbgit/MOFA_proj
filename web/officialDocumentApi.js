import { buildBackendUrl } from './config.js';

const REQUEST_TIMEOUT_MS = 120000;

async function readErrorMessage(response, fallback) {
  const payload = await response.json().catch(() => null);
  return payload?.message || payload?.detail || fallback;
}

async function requestWithTimeout(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );

  try {
    return await fetch(buildBackendUrl(path), {
      ...options,
      cache: 'no-store',
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('공문 처리 시간이 초과되었습니다. 다시 시도해 주세요.');
    }

    throw new Error('공문 서버와 연결하지 못했습니다.');
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function requestJson(path, options, fallbackMessage) {
  const response = await requestWithTimeout(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, `${fallbackMessage} (${response.status})`),
    );
  }

  return response.json();
}

export async function createOfficialDocumentDraft(chatId) {
  return requestJson(
    `/api/chats/${chatId}/official-documents/draft`,
    { method: 'POST' },
    '공문 초안 생성 실패',
  );
}

export async function fetchOfficialDocuments(chatId) {
  const payload = await requestJson(
    `/api/chats/${chatId}/official-documents`,
    { method: 'GET' },
    '공문 목록 조회 실패',
  );

  if (!Array.isArray(payload)) {
    throw new Error('공문 목록 응답 형식이 올바르지 않습니다.');
  }

  return payload;
}

export async function fetchOfficialDocument(documentId) {
  return requestJson(
    `/api/official-documents/${documentId}`,
    { method: 'GET' },
    '공문 상세 조회 실패',
  );
}

export async function updateOfficialDocument(documentId, draft) {
  return requestJson(
    `/api/official-documents/${documentId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({
        title: draft.title,
        body: draft.body,
      }),
    },
    '공문 저장 실패',
  );
}

export async function approveOfficialDocument(documentId) {
  return requestJson(
    `/api/official-documents/${documentId}/approve`,
    { method: 'POST' },
    '공문 승인 실패',
  );
}

function createDownloadFilename(document, extension) {
  const safeTitle = String(document?.title || '공문')
    .replace(/[\\/:*?"<>|]/g, '')
    .trim()
    .slice(0, 60);

  return `${safeTitle || '공문'}.${extension}`;
}

export async function downloadOfficialDocumentDocx(officialDocument) {
  const response = await requestWithTimeout(
    `/api/official-documents/${officialDocument.id}/docx`,
    { method: 'GET' },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, `DOCX 다운로드 실패 (${response.status})`),
    );
  }

  const contentType = response.headers.get('Content-Type') || '';
  if (!contentType.includes('wordprocessingml.document')) {
    throw new Error('DOCX 응답 형식이 올바르지 않습니다.');
  }

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = createDownloadFilename(officialDocument, 'docx');
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}

export async function downloadOfficialDocumentPdf(officialDocument) {
  const response = await requestWithTimeout(
    `/api/official-documents/${officialDocument.id}/pdf`,
    { method: 'GET' },
  );

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, `PDF 다운로드 실패 (${response.status})`),
    );
  }

  const contentType = response.headers.get('Content-Type') || '';
  if (!contentType.includes('application/pdf')) {
    throw new Error('PDF 응답 형식이 올바르지 않습니다.');
  }

  const blob = await response.blob();
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = createDownloadFilename(officialDocument, 'pdf');
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}
