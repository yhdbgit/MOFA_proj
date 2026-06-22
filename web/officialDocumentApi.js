const OFFICIAL_DOCUMENT_DRAFT_URL =
  'http://127.0.0.1:8787/official-documents/draft';
const OFFICIAL_DOCUMENT_PDF_URL =
  'http://127.0.0.1:8787/official-documents/pdf';
const REQUEST_TIMEOUT_MS = 60000;

async function readErrorMessage(response, fallback) {
  const payload = await response.json().catch(() => null);
  return payload?.detail || fallback;
}

async function requestWithTimeout(url, options) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );

  try {
    return await fetch(url, {
      ...options,
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

export async function createOfficialDocumentDraft(messages) {
  const response = await requestWithTimeout(OFFICIAL_DOCUMENT_DRAFT_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    cache: 'no-store',
    body: JSON.stringify({ messages }),
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, `공문 생성 실패 (${response.status})`),
    );
  }

  const payload = await response.json();

  if (!payload?.draft || !Array.isArray(payload?.missing_fields)) {
    throw new Error('공문 초안 응답 형식이 올바르지 않습니다.');
  }

  return payload;
}

function createPdfFilename(title) {
  const safeTitle = String(title || '공문-초안')
    .replace(/[\\/:*?"<>|]/g, '')
    .trim()
    .slice(0, 60);

  return `${safeTitle || '공문-초안'}.pdf`;
}

export async function downloadOfficialDocumentPdf(draft) {
  const response = await requestWithTimeout(OFFICIAL_DOCUMENT_PDF_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ draft }),
  });

  if (!response.ok) {
    throw new Error(
      await readErrorMessage(response, `PDF 저장 실패 (${response.status})`),
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
  link.download = createPdfFilename(draft.title);
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
}
