const MISSING_FIELD_LABELS = {
  citizen_name: '민원인 이름',
  victim_name: '피해자 이름',
  contact: '연락처',
  relationship: '민원인과 피해자의 관계',
  location: '사건 발생 국가·도시',
  incident_datetime: '사건 발생 일시',
  incident_summary: '사건 내용',
  requested_assistance: '요청 영사조력',
  birth_date: '생년월일',
};

const DOCUMENT_FIELDS = [
  ['document_number', '문서번호', 'text'],
  ['document_date', '작성일', 'text'],
  ['recipient', '수신', 'text'],
  ['via', '경유', 'text'],
  ['sender', '발신', 'text'],
  ['title', '제목', 'text'],
  ['body', '본문', 'textarea'],
  ['issuer', '발신 명의', 'text'],
  ['approver', '담당자', 'text'],
];

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
  empty.innerHTML = '<span aria-hidden="true">📄</span><p>공문 생성 버튼을 누르면<br />편집 가능한 초안이 표시됩니다.</p>';
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

export function renderDocumentDraft(container, result) {
  container.replaceChildren();
  const scroll = document.createElement('div');
  scroll.className = 'document-scroll';

  if (result.missing_fields.length > 0) {
    const notice = document.createElement('div');
    notice.className = 'missing-information-notice';

    const title = document.createElement('strong');
    title.textContent = '확인되지 않은 정보';

    const description = document.createElement('p');
    description.textContent = result.missing_fields
      .map((field) => MISSING_FIELD_LABELS[field] || field)
      .join(', ');

    notice.append(title, description);
    scroll.append(notice);
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

  form.append(organization, organizationEnglish);

  DOCUMENT_FIELDS.forEach(([fieldName, label, inputType]) => {
    form.append(
      createField(fieldName, label, inputType, result.draft[fieldName]),
    );
  });

  scroll.append(form);
  container.append(scroll);
}

export function readDocumentDraft(container) {
  const draft = {};

  container.querySelectorAll('[data-document-field]').forEach((input) => {
    draft[input.dataset.documentField] = input.value.trim();
  });

  const requiredFields = ['document_number', 'document_date', 'sender', 'title', 'body'];
  const missingRequiredField = requiredFields.find((field) => !draft[field]);

  if (missingRequiredField) {
    const label = DOCUMENT_FIELDS.find(([field]) => field === missingRequiredField)?.[1];
    throw new Error(`${label || missingRequiredField} 항목을 입력해 주세요.`);
  }

  return draft;
}
