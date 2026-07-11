const STATUS_LABELS = {
  DRAFT: '초안',
  REVIEWED: '검토 저장',
  APPROVED: '승인 완료',
};

function createField(fieldName, labelText, inputType, value) {
  const wrapper = document.createElement('label');
  wrapper.className = `document-field document-field-${fieldName}`;

  const label = document.createElement('span');
  label.className = 'document-field-label';
  label.textContent = labelText;

  const input = document.createElement(
    inputType === 'textarea' ? 'textarea' : 'input',
  );
  input.className = 'document-field-input';
  input.dataset.documentField = fieldName;
  input.value = String(value ?? '');
  input.setAttribute('aria-label', labelText);

  if (inputType === 'textarea') {
    input.rows = 18;
  } else {
    input.type = 'text';
  }

  wrapper.append(label, input);
  return wrapper;
}

function createInfoList(title, values, className) {
  if (!Array.isArray(values) || values.length === 0) {
    return null;
  }

  const container = document.createElement('section');
  container.className = className;

  const heading = document.createElement('strong');
  heading.textContent = title;

  const list = document.createElement('ul');
  values.forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    list.append(item);
  });

  container.append(heading, list);
  return container;
}

function extractLegalBasisFromBody(body) {
  const lines = String(body ?? '').split(/\r?\n/);
  const basisLines = [];
  let inBasisSection = false;

  lines.forEach((rawLine) => {
    const line = rawLine.trim();

    if (/^\d+\.\s*관련 근거$/.test(line)) {
      inBasisSection = true;
      return;
    }

    if (!inBasisSection) {
      return;
    }

    if (!line || /^\d+\.\s+/.test(line)) {
      inBasisSection = false;
      return;
    }

    basisLines.push(line.replace(/^[-*]\s*/, ''));
  });

  return basisLines;
}

export function renderDocumentLoading(container) {
  container.replaceChildren();

  const loading = document.createElement('div');
  loading.className = 'document-loading';
  loading.innerHTML =
    '<span class="document-spinner" aria-hidden="true"></span><p>상담 내용을 분석해 공문 초안을 생성하고 있습니다.</p>';
  container.append(loading);
}

export function renderDocumentEmpty(container) {
  container.replaceChildren();

  const empty = document.createElement('div');
  empty.className = 'document-empty';
  empty.innerHTML = '<span aria-hidden="true">📄</span><h3>빈 공문입니다.</h3><p>아직 이 상담에 작성된 공문 초안이 없습니다.<br />공문 수동 생성 버튼으로 Agent 초안을 만들 수 있습니다.</p>';
  container.append(empty);
}

export function renderDocumentError(container, message) {
  container.replaceChildren();

  const error = document.createElement('div');
  error.className = 'document-error';

  const icon = document.createElement('span');
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = '⚠️';

  const text = document.createElement('p');
  text.textContent = message;

  error.append(icon, text);
  container.append(error);
}

export function renderDocumentDraft(container, officialDocument) {
  container.replaceChildren();

  const scroll = document.createElement('div');
  scroll.className = 'document-scroll';

  const meta = document.createElement('div');
  meta.className = 'document-meta';

  const status = document.createElement('span');
  status.className = `document-status document-status-${String(officialDocument.status).toLowerCase()}`;
  status.textContent = STATUS_LABELS[officialDocument.status] || officialDocument.status;

  const runId = document.createElement('span');
  runId.className = 'document-run-id';
  runId.textContent = officialDocument.agentRunId
    ? `Agent ${officialDocument.agentRunId}`
    : 'Agent run 없음';

  meta.append(status, runId);
  scroll.append(meta);

  const missingFields = createInfoList(
    '확인 필요 정보',
    officialDocument.missingFields,
    'missing-information-notice',
  );
  if (missingFields) {
    scroll.append(missingFields);
  }

  const reviewNotes = createInfoList(
    '검토 권고',
    officialDocument.recommendedReviewNotes,
    'review-note-list',
  );
  if (reviewNotes) {
    scroll.append(reviewNotes);
  }

  const legalBasis = createInfoList(
    '관련 근거',
    extractLegalBasisFromBody(officialDocument.body),
    'legal-basis-list',
  );
  if (legalBasis) {
    scroll.append(legalBasis);
  }

  const form = document.createElement('form');
  form.id = 'officialDocumentForm';
  form.className = 'official-document';
  form.addEventListener('submit', (event) => event.preventDefault());

  const organization = document.createElement('div');
  organization.className = 'document-organization';
  organization.textContent = '외 교 부';

  const organizationEnglish = document.createElement('div');
  organizationEnglish.className = 'document-organization-english';
  organizationEnglish.textContent = 'MINISTRY OF FOREIGN AFFAIRS';

  form.append(
    organization,
    organizationEnglish,
    createField('title', '제목', 'text', officialDocument.title),
    createField('body', '본문', 'textarea', officialDocument.body),
  );

  scroll.append(form);
  container.append(scroll);
}

export function readDocumentDraft(container) {
  const draft = {};

  container.querySelectorAll('[data-document-field]').forEach((input) => {
    draft[input.dataset.documentField] = input.value.trim();
  });

  if (!draft.title) {
    throw new Error('제목을 입력해 주세요.');
  }

  if (!draft.body) {
    throw new Error('본문을 입력해 주세요.');
  }

  return draft;
}
