import {
  fetchChat,
  fetchChatList,
  fetchCitizenProfile,
  openChatEventStream,
  sendStaffChatMessage,
} from './chatMonitorApi.js';
import {
  approveOfficialDocument,
  createOfficialDocumentDraft,
  downloadOfficialDocumentPdf,
  fetchOfficialDocuments,
  updateOfficialDocument,
} from './officialDocumentApi.js';
import {
  readDocumentDraft,
  renderDocumentDraft,
  renderDocumentEmpty,
  renderDocumentError,
  renderDocumentLoading,
} from './documentPanel.js';

const elements = {
  activeConversationCount: document.getElementById('activeConversationCount'),
  assistantPanelContent: document.getElementById('assistantPanelContent'),
  assistantPanelMeta: document.getElementById('assistantPanelMeta'),
  assistantStatusBadge: document.getElementById('assistantStatusBadge'),
  chatSubtitle: document.getElementById('chatSubtitle'),
  chatTitle: document.getElementById('chatTitle'),
  connectionBadge: document.getElementById('connectionBadge'),
  connectionLabel: document.getElementById('connectionLabel'),
  closeDocumentPanelButton: document.getElementById(
    'closeDocumentPanelButton',
  ),
  conversationCountText: document.getElementById('conversationCountText'),
  conversationList: document.getElementById('conversationList'),
  documentPanel: document.getElementById('documentPanel'),
  documentPanelContent: document.getElementById('documentPanelContent'),
  documentStatusText: document.getElementById('documentStatusText'),
  approveDocumentButton: document.getElementById('approveDocumentButton'),
  downloadDocumentButton: document.getElementById('downloadDocumentButton'),
  generateDocumentButton: document.getElementById('generateDocumentButton'),
  manualGenerateDocumentButton: document.getElementById(
    'manualGenerateDocumentButton',
  ),
  messageCountBadge: document.getElementById('messageCountBadge'),
  messageList: document.getElementById('messageList'),
  quoteAssistantReplyButton: document.getElementById('quoteAssistantReplyButton'),
  saveDocumentButton: document.getElementById('saveDocumentButton'),
  sendStaffMessageButton: document.getElementById('sendStaffMessageButton'),
  staffReplyInput: document.getElementById('staffReplyInput'),
  staffReplyStatus: document.getElementById('staffReplyStatus'),
};

const chatsById = new Map();
const assistantSuggestionsByChatId = new Map();
const expandedEvidenceChunkIds = new Set();
const pendingAssistantChatIds = new Set();
const pendingChatPayloads = new Map();
const profilesByCitizenId = new Map();
const profileRequestsByCitizenId = new Map();
const documentsByChatId = new Map();
let activeChatId = null;
let activeDocumentId = null;
let copiedCitizenId = null;
let copyResetTimeoutId = null;
let expandedIdentityCitizenId = null;
let eventSource = null;
let assistantEvidenceFilter = 'all';
let isDocumentBusy = false;
let isSendingStaffMessage = false;

const EVIDENCE_FILTERS = [
  { value: 'all', label: '전체' },
  { value: 'manual', label: '매뉴얼' },
  { value: 'legal', label: '법률' },
  { value: 'country', label: '국가' },
];

function createEmptyState(icon, title, description) {
  const container = document.createElement('div');
  container.className = 'chat-empty';

  const iconElement = document.createElement('div');
  iconElement.className = 'empty-icon';
  iconElement.setAttribute('aria-hidden', 'true');
  iconElement.textContent = icon;

  const heading = document.createElement('h3');
  heading.textContent = title;

  const text = document.createElement('p');
  text.textContent = description;

  container.append(iconElement, heading, text);
  return container;
}

function setConnectionStatus(status) {
  const labels = {
    checking: '서버 확인 중',
    online: '서버 연결됨',
    offline: '서버 연결 끊김',
  };

  elements.connectionBadge.className = `connection-badge ${status}`;
  elements.connectionLabel.textContent = labels[status];
}

function closeDocumentPanel() {
  elements.documentPanel.classList.remove('open');
  elements.documentPanel.setAttribute('aria-hidden', 'true');
}

function openDocumentPanel() {
  elements.documentPanel.classList.add('open');
  elements.documentPanel.setAttribute('aria-hidden', 'false');
}

function setDocumentStatus(message, type = '') {
  elements.documentStatusText.textContent = message;
  elements.documentStatusText.className = type;
}

function getChats() {
  return [...chatsById.values()].sort((left, right) => {
    return getActivityTime(right) - getActivityTime(left);
  });
}

function getActiveChat() {
  return activeChatId ? chatsById.get(activeChatId) : null;
}

function getAssistantSuggestion(chatId) {
  return chatId ? assistantSuggestionsByChatId.get(chatId) ?? null : null;
}

function getActiveAssistantSuggestion() {
  const activeChat = getActiveChat();
  return activeChat ? getAssistantSuggestion(activeChat.id) : null;
}

function getDocumentsForChat(chatId) {
  return documentsByChatId.get(chatId) ?? [];
}

function getActiveDocument() {
  const activeChat = getActiveChat();
  if (!activeChat || !activeDocumentId) {
    return null;
  }

  return getDocumentsForChat(activeChat.id).find(
    (document) => document.id === activeDocumentId,
  ) ?? null;
}

function upsertDocument(document) {
  const currentDocuments = getDocumentsForChat(document.chatSessionId);
  const nextDocuments = [
    document,
    ...currentDocuments.filter((item) => item.id !== document.id),
  ].sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt));

  documentsByChatId.set(document.chatSessionId, nextDocuments);
  activeDocumentId = document.id;
}

function getLastMessage(chat) {
  return chat.messages.at(-1) ?? null;
}

function getActivityIso(chat) {
  return getLastMessage(chat)?.createdAt ?? chat.createdAt;
}

function getActivityTime(chat) {
  const timestamp = Date.parse(getActivityIso(chat));
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function formatCitizenId(citizenId) {
  if (typeof citizenId !== 'string' || citizenId.length <= 8) {
    return citizenId || 'ID 없음';
  }

  return `${citizenId.slice(0, 8)}...`;
}

function formatGender(gender) {
  if (gender === 'MALE') {
    return '남';
  }

  if (gender === 'FEMALE') {
    return '여';
  }

  return '';
}

function calculateAge(birthDate) {
  if (typeof birthDate !== 'string' || birthDate.trim().length === 0) {
    return null;
  }

  const birth = new Date(birthDate);

  if (Number.isNaN(birth.getTime())) {
    return null;
  }

  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const didBirthdayPass =
    today.getMonth() > birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() >= birth.getDate());

  if (!didBirthdayPass) {
    age -= 1;
  }

  return age >= 0 ? age : null;
}

function formatProfileSummary(profile) {
  const age = calculateAge(profile?.birthDate);
  const parts = [
    profile?.name,
    age === null ? '' : `${age}세`,
    formatGender(profile?.gender),
    profile?.birthDate,
    profile?.phoneNumber,
  ].filter((value) => typeof value === 'string' && value.trim().length > 0);

  return parts.join('/');
}

const COUNTRY_NAMES_BY_CODE = {
  GH: '가나',
  JP: '일본',
  MX: '멕시코',
  NP: '네팔',
};

const COUNTRY_KEYWORDS = [
  '네팔',
  '멕시코',
  '일본',
  '가나',
  '미국',
  '중국',
  '태국',
  '베트남',
  '필리핀',
  '인도네시아',
  '프랑스',
  '독일',
  '영국',
  '스페인',
  '이탈리아',
  '호주',
  '캐나다',
  '브라질',
  '인도',
].sort((left, right) => right.length - left.length);

const INCIDENT_RULES = [
  {
    label: '납치 신고',
    keywords: ['납치', '인질', '감금', '억류'],
  },
  {
    label: '여권 분실 상담',
    keywords: ['여권 분실', '여권 잃어', '여권을 잃', '여권 도난'],
  },
  {
    label: '도난 신고',
    keywords: ['도난', '절도', '지갑', '소매치기', '강도'],
  },
  {
    label: '체포·구금 상담',
    keywords: ['체포', '구금', 'detained', 'arrest'],
  },
  {
    label: '사고 신고',
    keywords: ['교통사고', '사고', '응급', '부상', '병원'],
  },
  {
    label: '사망 신고',
    keywords: ['사망', '해외사망'],
  },
  {
    label: '재난 대피 상담',
    keywords: ['지진', '자연재해', '태풍', '홍수', '전쟁', '공습', '폭격'],
  },
  {
    label: '시위 안전 상담',
    keywords: ['시위', '집회', '폭동'],
  },
];

const OUT_OF_SCOPE_INCIDENT_TYPE = 'OUT_OF_SCOPE';
const OUT_OF_SCOPE_INCIDENT_LABEL = '상담 범위 외 질문';

function normalizeText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function isOutOfScopeChat(chat) {
  return (
    normalizeText(chat?.incidentType) === OUT_OF_SCOPE_INCIDENT_TYPE ||
    normalizeText(chat?.incidentLabel) === OUT_OF_SCOPE_INCIDENT_LABEL
  );
}

function collectChatText(chat) {
  const messageText = Array.isArray(chat?.messages)
    ? chat.messages.map((message) => message.text).join('\n')
    : '';

  return `${messageText}\n${chat?.incidentLabel ?? ''}\n${chat?.detectedCountry ?? ''}`;
}

function inferCountryFromText(text) {
  return COUNTRY_KEYWORDS.find((country) => text.includes(country)) ?? '';
}

function resolveCountryName(chat) {
  if (isOutOfScopeChat(chat)) {
    return '국가 미확인';
  }

  const detectedCountry = normalizeText(chat?.detectedCountry);
  if (detectedCountry) {
    return detectedCountry;
  }

  const inferredCountry = inferCountryFromText(collectChatText(chat));
  if (inferredCountry) {
    return inferredCountry;
  }

  return COUNTRY_NAMES_BY_CODE[chat?.countryCode] ?? '국가 미확인';
}

function inferIncidentLabelFromText(text) {
  const lowerText = text.toLowerCase();
  const rule = INCIDENT_RULES.find((item) =>
    item.keywords.some((keyword) => lowerText.includes(keyword.toLowerCase())),
  );

  return rule?.label ?? '';
}

function resolveIncidentLabel(chat) {
  if (isOutOfScopeChat(chat)) {
    return OUT_OF_SCOPE_INCIDENT_LABEL;
  }

  const incidentLabel = normalizeText(chat?.incidentLabel);
  if (incidentLabel) {
    return incidentLabel;
  }

  return inferIncidentLabelFromText(collectChatText(chat)) || '영사 상담';
}

function formatChatTitle(chat) {
  if (isOutOfScopeChat(chat)) {
    return OUT_OF_SCOPE_INCIDENT_LABEL;
  }

  return `${resolveCountryName(chat)} ${resolveIncidentLabel(chat)}`;
}

function formatRelativeTime(isoValue) {
  const timestamp = Date.parse(isoValue);

  if (Number.isNaN(timestamp)) {
    return '';
  }

  const diffSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);
  const diffWeeks = Math.floor(diffDays / 7);
  const diffMonths = Math.floor(diffDays / 30);

  if (diffMinutes < 1) {
    return '방금 전';
  }

  if (diffHours < 1) {
    return `${diffMinutes}분 전`;
  }

  if (diffDays < 1) {
    return `${diffHours}시간 전`;
  }

  if (diffWeeks < 1) {
    return `${diffDays}일 전`;
  }

  if (diffMonths < 1) {
    return `${diffWeeks}주 전`;
  }

  return `${diffMonths}개월 전`;
}

function upsertChat(chat, { selectIfNone = true } = {}) {
  const currentChat = chatsById.get(chat.id) ?? null;
  const currentMessages = Array.isArray(currentChat?.messages)
    ? currentChat.messages
    : [];
  const nextMessages = Array.isArray(chat.messages) ? chat.messages : [];
  const messages =
    currentMessages.length > nextMessages.length ? currentMessages : nextMessages;

  chatsById.set(chat.id, {
    ...currentChat,
    ...chat,
    messages,
  });

  if (selectIfNone && !activeChatId) {
    activeChatId = chat.id;
  }
}

function senderTypeToWebRole(senderType) {
  if (senderType === 'CITIZEN') {
    return 'user';
  }

  if (senderType === 'STAFF') {
    return 'staff';
  }

  return 'assistant';
}

function senderTypeToLabel(senderType) {
  if (senderType === 'CITIZEN') {
    return '민원인';
  }

  if (senderType === 'STAFF') {
    return '담당자';
  }

  return 'AI 답변';
}

function createRealtimeMessage(eventPayload) {
  const payload = eventPayload?.payload ?? {};
  const senderType = String(payload.senderType ?? 'AGENT');

  return {
    id: String(payload.messageId ?? `${eventPayload.chatSessionId}-${eventPayload.occurredAt}`),
    role: senderTypeToWebRole(senderType),
    senderType,
    senderLabel: senderTypeToLabel(senderType),
    text: String(payload.content ?? ''),
    createdAt: eventPayload.occurredAt ?? new Date().toISOString(),
  };
}

function upsertChatMessage(chatId, message, eventPayload = null) {
  if (!chatId || message.text.trim().length === 0) {
    return null;
  }

  if (message.senderType === 'STAFF') {
    pendingAssistantChatIds.delete(chatId);
  }

  const pendingPayload = pendingChatPayloads.get(chatId)?.payload ?? {};
  const currentChat = chatsById.get(chatId) ?? null;
  const currentMessages = Array.isArray(currentChat?.messages)
    ? currentChat.messages
    : [];
  const messages = [
    ...currentMessages.filter((item) => item.id !== message.id),
    message,
  ].sort((left, right) => Date.parse(left.createdAt) - Date.parse(right.createdAt));
  const nextChat = {
    id: chatId,
    citizenId: currentChat?.citizenId ?? pendingPayload.citizenId ?? '',
    countryCode: currentChat?.countryCode ?? pendingPayload.countryCode ?? '',
    status: currentChat?.status ?? pendingPayload.status ?? 'OPEN',
    detectedCountry: currentChat?.detectedCountry ?? null,
    incidentType: currentChat?.incidentType ?? null,
    incidentLabel: currentChat?.incidentLabel ?? null,
    severity: currentChat?.severity ?? null,
    createdAt:
      currentChat?.createdAt ??
      pendingChatPayloads.get(chatId)?.occurredAt ??
      eventPayload?.occurredAt ??
      new Date().toISOString(),
    messages,
  };

  pendingChatPayloads.delete(chatId);
  upsertChat(nextChat);

  if (!activeChatId || !currentChat || currentMessages.length === 0) {
    activeChatId = chatId;
  }

  if (nextChat.citizenId) {
    void ensureCitizenProfile(nextChat.citizenId);
  }

  return nextChat;
}

function upsertRealtimeChatMessage(eventPayload) {
  const chatId = eventPayload?.chatSessionId;
  const message = createRealtimeMessage(eventPayload);

  if (message.senderType === 'CITIZEN') {
    assistantSuggestionsByChatId.delete(chatId);
    pendingAssistantChatIds.add(chatId);
  } else if (message.senderType === 'STAFF') {
    pendingAssistantChatIds.delete(chatId);
  }

  return upsertChatMessage(chatId, message, eventPayload);
}

function shouldShowAnalysisPending(chat) {
  const lastMessage = getLastMessage(chat);
  return (
    lastMessage?.role === 'user' &&
    pendingAssistantChatIds.has(chat.id) &&
    !getAssistantSuggestion(chat.id)
  );
}

function normalizeEvidenceType(value) {
  const type = normalizeText(value).toLowerCase();

  if (['manual', 'manuals', '매뉴얼'].includes(type)) {
    return 'manual';
  }

  if (['legal', 'law', '법률'].includes(type)) {
    return 'legal';
  }

  if (['country', 'countries', '국가'].includes(type)) {
    return 'country';
  }

  return 'unknown';
}

function evidenceTypeLabel(type) {
  if (type === 'manual') {
    return '매뉴얼';
  }

  if (type === 'legal') {
    return '법률';
  }

  if (type === 'country') {
    return '국가';
  }

  return '근거';
}

function normalizeRagSource(source) {
  const type = normalizeEvidenceType(source?.type ?? source?.documentGroup);
  const title = normalizeText(source?.title) || '제목 없음';
  const chunkId = normalizeText(source?.chunkId);

  return {
    title,
    chunkId,
    type,
    source: normalizeText(source?.source),
    category: normalizeText(source?.category),
    country: normalizeText(source?.country),
    score: Number.isFinite(Number(source?.score)) ? Number(source.score) : null,
    preview: normalizeText(source?.preview),
    content: normalizeText(source?.content),
  };
}

function normalizeAssistantSuggestion(eventPayload) {
  const payload = eventPayload?.payload ?? {};
  const suggestedReply = normalizeText(payload.citizenReply);

  return {
    chatId: eventPayload?.chatSessionId ?? '',
    status: normalizeText(payload.status) || 'UNKNOWN',
    agentRunId: normalizeText(payload.agentRunId),
    suggestedReply,
    severity: normalizeText(payload.severity),
    detectedCountry: normalizeText(payload.detectedCountry),
    incidentType: normalizeText(payload.incidentType),
    incidentLabel: normalizeText(payload.incidentLabel),
    recommendedActions: Array.isArray(payload.recommendedActions)
      ? payload.recommendedActions.filter((item) => normalizeText(item))
      : [],
    ragSources: Array.isArray(payload.ragSources)
      ? payload.ragSources
          .map(normalizeRagSource)
          .filter((source) => source.chunkId || source.title !== '제목 없음')
      : [],
    generatedAt:
      normalizeText(payload.generatedAt) ||
      normalizeText(eventPayload?.occurredAt) ||
      new Date().toISOString(),
    errorMessage: normalizeText(payload.errorMessage),
  };
}

function upsertAssistantSuggestion(eventPayload) {
  const suggestion = normalizeAssistantSuggestion(eventPayload);

  if (!suggestion.chatId) {
    return null;
  }

  pendingAssistantChatIds.delete(suggestion.chatId);
  assistantSuggestionsByChatId.set(suggestion.chatId, suggestion);
  return suggestion;
}

async function ensureCitizenProfile(citizenId) {
  if (!citizenId) {
    return null;
  }

  if (profilesByCitizenId.has(citizenId) && profilesByCitizenId.get(citizenId)) {
    return profilesByCitizenId.get(citizenId);
  }

  if (profileRequestsByCitizenId.has(citizenId)) {
    return profileRequestsByCitizenId.get(citizenId);
  }

  const request = fetchCitizenProfile(citizenId)
    .catch(() => null)
    .then((profile) => {
      profilesByCitizenId.set(citizenId, profile);
      profileRequestsByCitizenId.delete(citizenId);
      return profile;
    });

  profileRequestsByCitizenId.set(citizenId, request);
  return request;
}

async function loadChat(chatId, { select = false } = {}) {
  const chat = await fetchChat(chatId);
  upsertChat(chat);

  if (select) {
    activeChatId = chat.id;
  }

  await ensureCitizenProfile(chat.citizenId);
  render();
}

async function loadDocumentsForChat(
  chatId,
  { openExisting = false, preferredDocumentId = null, activate = true } = {},
) {
  const documents = await fetchOfficialDocuments(chatId);
  documentsByChatId.set(chatId, documents);

  const preferredDocument = documents.find(
    (document) => document.id === preferredDocumentId,
  );

  if (!activate) {
    render();
    return;
  }

  if (preferredDocument) {
    activeDocumentId = preferredDocument.id;
  } else if (documents.length > 0 && (!activeDocumentId || openExisting)) {
    activeDocumentId = documents[0].id;
  } else if (documents.length === 0) {
    activeDocumentId = null;
  }

  if (documents.length > 0 && openExisting && chatId === activeChatId) {
    openDocumentPanel();
  }

  render();
}

async function selectChat(chatId) {
  activeChatId = chatId;
  activeDocumentId = null;
  setDocumentStatus('');
  closeDocumentPanel();
  render();

  try {
    await loadChat(chatId, { select: true });
    await loadDocumentsForChat(chatId, { openExisting: true });
    setConnectionStatus('online');
  } catch {
    setConnectionStatus('offline');
  }
}

function renderConversationList() {
  elements.conversationList.replaceChildren();

  const chats = getChats();

  if (chats.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'sidebar-empty';

    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '📭';

    const text = document.createElement('p');
    text.innerHTML = '민원인이 채팅을 시작하면<br />상담 목록이 표시됩니다.';

    empty.append(icon, text);
    elements.conversationList.append(empty);
    return;
  }

  const fragment = document.createDocumentFragment();

  chats.forEach((chat) => {
    const lastMessage = getLastMessage(chat);
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `conversation-item${chat.id === activeChatId ? ' active' : ''}`;
    item.setAttribute('aria-pressed', String(chat.id === activeChatId));
    item.addEventListener('click', () => selectChat(chat.id));

    const header = document.createElement('div');
    header.className = 'conversation-item-header';

    const title = document.createElement('span');
    title.className = 'conversation-item-title';
    title.textContent = formatChatTitle(chat);

    const status = document.createElement('span');
    status.className = 'live-label';
    status.textContent = chat.status;

    const preview = document.createElement('p');
    preview.className = 'conversation-preview';
    preview.textContent = lastMessage?.text ?? '아직 메시지가 없습니다.';

    const footer = document.createElement('div');
    footer.className = 'conversation-item-footer';

    const sender = document.createElement('span');
    sender.textContent = lastMessage
      ? `${lastMessage.senderLabel} 메시지`
      : chat.citizenId;

    const time = document.createElement('span');
    time.className = 'conversation-time';
    time.textContent = formatRelativeTime(getActivityIso(chat));

    header.append(title, status);
    footer.append(sender, time);
    item.append(header, preview, footer);
    fragment.append(item);
  });

  elements.conversationList.append(fragment);
}

function renderMessages() {
  elements.messageList.replaceChildren();

  const activeChat = getActiveChat();

  if (!activeChat) {
    elements.messageList.append(
      createEmptyState(
        '💬',
        '표시할 상담이 없습니다',
        '모바일 앱에서 메시지를 보내면 이 화면에 상담이 표시됩니다.',
      ),
    );
    return;
  }

  if (activeChat.messages.length === 0) {
    elements.messageList.append(
      createEmptyState('💬', '메시지가 없습니다', '상담 메시지를 기다리고 있습니다.'),
    );
    return;
  }

  const fragment = document.createDocumentFragment();

  activeChat.messages.forEach((message) => {
    const article = document.createElement('article');
    article.className = `message ${message.role}${message.isPending ? ' pending' : ''}`;

    const sender = document.createElement('div');
    sender.className = 'message-sender';
    sender.textContent = message.senderLabel;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message.text;

    const time = document.createElement('time');
    time.className = 'message-time';
    time.dateTime = message.createdAt;
    time.textContent = formatRelativeTime(message.createdAt);

    article.append(sender, bubble, time);
    fragment.append(article);
  });

  elements.messageList.append(fragment);
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function createIdentityBadge(chat, profile) {
  const isVerified = Boolean(profile);
  const isExpanded = isVerified && expandedIdentityCitizenId === chat.citizenId;
  const element = document.createElement(isVerified ? 'button' : 'span');
  element.className = `identity-badge ${isVerified ? 'verified' : 'unknown'}${
    isExpanded ? ' expanded' : ''
  }`;

  if (!isVerified) {
    element.textContent = '신원 미상';
    return element;
  }

  element.type = 'button';
  element.setAttribute('aria-expanded', String(isExpanded));
  element.textContent = isExpanded
    ? formatProfileSummary(profile)
    : '신원 확인';
  element.addEventListener('click', () => {
    expandedIdentityCitizenId = isExpanded ? null : chat.citizenId;
    renderHeader();
  });

  return element;
}

function copyTextFallback(value) {
  const textarea = document.createElement('textarea');
  textarea.value = value;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.append(textarea);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
}

async function copyCitizenId(citizenId) {
  if (!citizenId) {
    return;
  }

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(citizenId);
    } else {
      copyTextFallback(citizenId);
    }
  } catch {
    copyTextFallback(citizenId);
  }

  copiedCitizenId = citizenId;
  window.clearTimeout(copyResetTimeoutId);
  copyResetTimeoutId = window.setTimeout(() => {
    copiedCitizenId = null;
    renderHeader();
  }, 1000);
  renderHeader();
}

function renderChatMeta(activeChat) {
  const fragment = document.createDocumentFragment();
  const profile = profilesByCitizenId.get(activeChat.citizenId) ?? null;
  const identityBadge = createIdentityBadge(activeChat, profile);

  const citizenIdChip = document.createElement('span');
  citizenIdChip.className = 'citizen-id-chip';
  citizenIdChip.title = activeChat.citizenId;

  const citizenIdText = document.createElement('span');
  citizenIdText.className = 'citizen-id-text';
  citizenIdText.textContent = formatCitizenId(activeChat.citizenId);

  const copyButton = document.createElement('button');
  const isCopied = copiedCitizenId === activeChat.citizenId;
  copyButton.type = 'button';
  copyButton.className = `copy-button${isCopied ? ' copied' : ''}`;
  copyButton.setAttribute('aria-label', 'citizenId 복사');
  copyButton.title = 'citizenId 복사';
  copyButton.textContent = isCopied ? '✓' : '⧉';
  copyButton.addEventListener('click', () => copyCitizenId(activeChat.citizenId));
  citizenIdChip.append(citizenIdText, copyButton);

  const country = document.createElement('span');
  country.className = 'meta-token country';
  country.textContent = resolveCountryName(activeChat);
  country.title = activeChat.countryCode && !isOutOfScopeChat(activeChat)
    ? `초기 국가코드: ${activeChat.countryCode}`
    : '';

  const status = document.createElement('span');
  status.className = 'meta-token status';
  status.textContent = activeChat.status;

  fragment.append(identityBadge, citizenIdChip);
  fragment.append(country, status);
  return fragment;
}

function renderHeader() {
  const chats = getChats();
  const activeChat = getActiveChat();
  const count = chats.length;

  elements.activeConversationCount.textContent = String(count);
  elements.conversationCountText.textContent =
    count > 0 ? `누적 상담 ${count}건` : '현재 진행 중인 상담이 없습니다.';

  if (!activeChat) {
    elements.chatTitle.textContent = '상담을 기다리는 중입니다';
    elements.chatSubtitle.className = '';
    elements.chatSubtitle.textContent =
      '왼쪽 목록에서 상담을 선택하면 대화가 표시됩니다.';
    elements.chatSubtitle.title = '';
    elements.messageCountBadge.hidden = true;
    return;
  }

  elements.chatTitle.textContent = formatChatTitle(activeChat);
  elements.chatSubtitle.className = 'chat-meta-row';
  elements.chatSubtitle.title = activeChat.citizenId;
  elements.chatSubtitle.replaceChildren(renderChatMeta(activeChat));
  elements.messageCountBadge.hidden = false;
  elements.messageCountBadge.textContent = `${activeChat.messages.length}개 메시지`;
}

function renderDocumentControls() {
  const activeChat = getActiveChat();
  const activeDocument = getActiveDocument();
  const isApproved = activeDocument?.status === 'APPROVED';

  elements.generateDocumentButton.disabled = !activeChat || isDocumentBusy;
  elements.generateDocumentButton.textContent = isDocumentBusy
    ? '공문 처리 중'
    : '📄 공문 확인';

  elements.manualGenerateDocumentButton.disabled = !activeChat || isDocumentBusy;

  elements.saveDocumentButton.hidden = !activeDocument;
  elements.saveDocumentButton.disabled = isDocumentBusy || isApproved;

  elements.approveDocumentButton.hidden = !activeDocument;
  elements.approveDocumentButton.disabled = isDocumentBusy || isApproved;

  elements.downloadDocumentButton.hidden = !activeDocument;
  elements.downloadDocumentButton.disabled = isDocumentBusy || !isApproved;
}

function renderDocumentPanel() {
  const activeChat = getActiveChat();
  const activeDocument = getActiveDocument();

  renderDocumentControls();

  if (activeDocument) {
    renderDocumentDraft(elements.documentPanelContent, activeDocument);
    if (!elements.documentStatusText.textContent) {
      setDocumentStatus(
        activeDocument.status === 'APPROVED'
          ? '승인 완료. PDF 다운로드가 가능합니다.'
          : '공문 초안을 검토한 뒤 임시 저장 또는 승인할 수 있습니다.',
      );
    }
    return;
  }

  if (activeChat && shouldShowAnalysisPending(activeChat)) {
    if (elements.documentPanel.classList.contains('open')) {
      renderDocumentLoading(elements.documentPanelContent);
      setDocumentStatus('AI 분석 완료 후 공문 초안이 표시됩니다.');
    }
    return;
  }

  if (elements.documentPanel.classList.contains('open')) {
    renderDocumentEmpty(elements.documentPanelContent);
    if (!elements.documentStatusText.textContent) {
      setDocumentStatus('빈 공문입니다.');
    }
  }
}

function setStaffReplyStatus(message, type = '') {
  elements.staffReplyStatus.textContent = message;
  elements.staffReplyStatus.className = `staff-reply-status${type ? ` ${type}` : ''}`;
}

function renderComposer() {
  const activeChat = getActiveChat();
  const hasDraft = elements.staffReplyInput.value.trim().length > 0;

  elements.staffReplyInput.disabled = !activeChat || isSendingStaffMessage;
  elements.sendStaffMessageButton.disabled =
    !activeChat || !hasDraft || isSendingStaffMessage;
  elements.sendStaffMessageButton.textContent = isSendingStaffMessage
    ? '전송 중'
    : '전송';
}

function createAssistantEmptyState(title, description) {
  const empty = document.createElement('div');
  empty.className = 'assistant-empty';

  const heading = document.createElement('h3');
  heading.textContent = title;

  const text = document.createElement('p');
  text.textContent = description;

  empty.append(heading, text);
  return empty;
}

function createAssistantToken(label, value) {
  const token = document.createElement('span');
  token.className = 'assistant-token';
  token.textContent = value ? `${label} ${value}` : label;
  return token;
}

function formatEvidenceScore(score) {
  if (!Number.isFinite(score)) {
    return '';
  }

  if (score >= 0 && score <= 1) {
    return `유사도 ${Math.round(score * 100)}%`;
  }

  return `점수 ${score.toFixed(2)}`;
}

function evidenceSourceKey(source) {
  return source.chunkId || `${source.type}:${source.title}`;
}

function renderEvidenceFilterButton(filter, sources) {
  const count = filter.value === 'all'
    ? sources.length
    : sources.filter((source) => source.type === filter.value).length;
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `assistant-evidence-filter-button${
    assistantEvidenceFilter === filter.value ? ' active' : ''
  }`;
  button.textContent = `${filter.label} ${count}`;
  button.disabled = count === 0 && filter.value !== 'all';
  button.addEventListener('click', () => {
    assistantEvidenceFilter = filter.value;
    renderAssistantPanel();
  });
  return button;
}

function renderEvidenceCard(source) {
  const sourceKey = evidenceSourceKey(source);
  const isExpanded = expandedEvidenceChunkIds.has(sourceKey);
  const fullText = source.content || source.preview;
  const previewText = source.preview || source.content;
  const hasExpandableText = Boolean(fullText && previewText && fullText !== previewText);
  const item = document.createElement('article');
  item.className = `assistant-evidence-card${isExpanded ? ' expanded' : ''}`;

  const top = document.createElement('div');
  top.className = 'assistant-evidence-card-top';

  const header = document.createElement('div');
  header.className = 'assistant-evidence-head';

  const badge = document.createElement('span');
  badge.className = `assistant-evidence-type ${source.type}`;
  badge.textContent = evidenceTypeLabel(source.type);

  const title = document.createElement('h4');
  title.className = 'assistant-evidence-title';
  title.textContent = source.title;

  header.append(badge, title);

  const toggleButton = document.createElement('button');
  toggleButton.type = 'button';
  toggleButton.className = 'assistant-evidence-toggle';
  toggleButton.textContent = isExpanded ? '⌃' : '⌄';
  toggleButton.hidden = !hasExpandableText;
  toggleButton.title = isExpanded ? '접기' : '펼치기';
  toggleButton.setAttribute('aria-label', isExpanded ? '근거 자료 접기' : '근거 자료 펼치기');
  toggleButton.setAttribute('aria-expanded', String(isExpanded));
  toggleButton.addEventListener('click', () => {
    if (isExpanded) {
      expandedEvidenceChunkIds.delete(sourceKey);
    } else {
      expandedEvidenceChunkIds.add(sourceKey);
    }
    renderAssistantPanel();
  });

  top.append(header, toggleButton);

  const metaValues = [
    source.source,
    source.category,
    source.country,
    formatEvidenceScore(source.score),
  ].filter(Boolean);

  const meta = document.createElement('p');
  meta.className = 'assistant-evidence-meta';
  meta.textContent = metaValues.length > 0 ? metaValues.join(' · ') : '메타데이터 없음';

  item.append(top, meta);

  if (previewText) {
    const preview = document.createElement('p');
    preview.className = `assistant-evidence-preview${isExpanded ? ' expanded' : ''}`;
    preview.textContent = isExpanded ? fullText : previewText;
    item.append(preview);
  }

  if (source.chunkId) {
    const chunk = document.createElement('code');
    chunk.className = 'assistant-evidence-chunk';
    chunk.textContent = source.chunkId;
    item.append(chunk);
  }

  return item;
}

function renderEvidenceSources(sources) {
  const section = document.createElement('section');
  section.className = 'assistant-evidence';

  const header = document.createElement('div');
  header.className = 'assistant-evidence-header';

  const titleRow = document.createElement('div');
  titleRow.className = 'assistant-evidence-title-row';

  const title = document.createElement('h3');
  title.textContent = '근거 자료';

  const count = document.createElement('span');
  count.textContent = `${sources.length}개 청크`;

  titleRow.append(title, count);

  const filters = document.createElement('div');
  filters.className = 'assistant-evidence-filter';
  EVIDENCE_FILTERS.forEach((filter) => {
    filters.append(renderEvidenceFilterButton(filter, sources));
  });

  header.append(titleRow, filters);
  section.append(header);

  const filteredSources = assistantEvidenceFilter === 'all'
    ? sources
    : sources.filter((source) => source.type === assistantEvidenceFilter);

  if (filteredSources.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'assistant-evidence-empty';
    empty.textContent = sources.length === 0
      ? '검색된 근거 청크가 없습니다.'
      : '선택한 유형의 근거 청크가 없습니다.';
    section.append(empty);
    return section;
  }

  const list = document.createElement('div');
  list.className = 'assistant-evidence-list';
  filteredSources.forEach((source) => {
    list.append(renderEvidenceCard(source));
  });
  section.append(list);
  return section;
}

function renderAssistantPanel() {
  const activeChat = getActiveChat();
  const suggestion = getActiveAssistantSuggestion();
  const isPending = activeChat ? shouldShowAnalysisPending(activeChat) : false;
  const canQuote = Boolean(suggestion?.suggestedReply);

  elements.assistantPanelContent.replaceChildren();
  elements.quoteAssistantReplyButton.disabled = !canQuote;

  if (!activeChat) {
    elements.assistantPanelMeta.textContent = '상담 선택 대기';
    elements.assistantStatusBadge.className = 'assistant-status-badge idle';
    elements.assistantStatusBadge.textContent = '대기';
    elements.assistantPanelContent.append(
      createAssistantEmptyState('상담 없음', '왼쪽 목록에서 상담을 선택하세요.'),
    );
    return;
  }

  elements.assistantPanelMeta.textContent = formatChatTitle(activeChat);

  if (isPending) {
    elements.assistantStatusBadge.className = 'assistant-status-badge pending';
    elements.assistantStatusBadge.textContent = '생성 중';
    elements.assistantPanelContent.append(
      createAssistantEmptyState('답변 생성 중', '상담사 검토용 답변을 준비하고 있습니다.'),
    );
    return;
  }

  if (!suggestion) {
    elements.assistantStatusBadge.className = 'assistant-status-badge idle';
    elements.assistantStatusBadge.textContent = '대기';
    elements.assistantPanelContent.append(
      createAssistantEmptyState('답변 없음', '새 민원인 메시지가 들어오면 표시됩니다.'),
    );
    return;
  }

  if (!suggestion.suggestedReply) {
    elements.assistantStatusBadge.className = 'assistant-status-badge error';
    elements.assistantStatusBadge.textContent = '확인 필요';
    elements.assistantPanelContent.append(
      createAssistantEmptyState(
        '생성 실패',
        suggestion.errorMessage || '답변 후보를 생성하지 못했습니다.',
      ),
    );
    return;
  }

  elements.assistantStatusBadge.className = 'assistant-status-badge ready';
  elements.assistantStatusBadge.textContent = '준비됨';

  const suggestionArticle = document.createElement('article');
  suggestionArticle.className = 'assistant-suggestion';

  const meta = document.createElement('div');
  meta.className = 'assistant-suggestion-meta';
  [
    createAssistantToken('긴급도', suggestion.severity || '미분류'),
    createAssistantToken('국가', suggestion.detectedCountry || resolveCountryName(activeChat)),
    createAssistantToken('유형', suggestion.incidentLabel || resolveIncidentLabel(activeChat)),
  ].forEach((token) => meta.append(token));

  const body = document.createElement('p');
  body.className = 'assistant-suggestion-body';
  body.textContent = suggestion.suggestedReply;

  const generatedAt = document.createElement('time');
  generatedAt.className = 'assistant-generated-time';
  generatedAt.dateTime = suggestion.generatedAt;
  generatedAt.textContent = `${formatRelativeTime(suggestion.generatedAt)} 생성`;

  suggestionArticle.append(meta, body, generatedAt);

  elements.assistantPanelContent.append(
    suggestionArticle,
    renderEvidenceSources(suggestion.ragSources),
  );
}

function render() {
  renderHeader();
  renderConversationList();
  renderMessages();
  renderDocumentPanel();
  renderAssistantPanel();
  renderComposer();
}

function parseEventChatId(eventData) {
  try {
    return JSON.parse(eventData)?.chatSessionId ?? null;
  } catch {
    return null;
  }
}

function parseEventPayload(eventData) {
  try {
    return JSON.parse(eventData);
  } catch {
    return null;
  }
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

async function refreshChatAfterCommit(chatId, { includeDocuments = false } = {}) {
  const delays = [250, 750, 1500];

  for (const delayMs of delays) {
    await delay(delayMs);

    try {
      await loadChat(chatId, { select: chatId === activeChatId });
      if (includeDocuments && chatId === activeChatId) {
        await loadDocumentsForChat(chatId);
      }

      setConnectionStatus('online');
      return;
    } catch {
      setConnectionStatus('offline');
    }
  }
}

async function handleDocumentEvent(event) {
  const eventPayload = parseEventPayload(event.data);
  const documentId = eventPayload?.payload?.documentId;
  const chatId = eventPayload?.chatSessionId;

  if (!chatId) {
    return;
  }

  if (event.name === 'OFFICIAL_DOCUMENT_DRAFT_FAILED') {
    if (!activeChatId) {
      activeChatId = chatId;
    }

    if (activeChatId === chatId) {
      openDocumentPanel();
      renderDocumentError(
        elements.documentPanelContent,
        eventPayload?.payload?.errorMessage ?? '공문 초안 생성에 실패했습니다.',
      );
      setDocumentStatus('공문 초안 생성에 실패했습니다.', 'error');
      renderDocumentControls();
    }

    return;
  }

  await delay(750);
  if (!activeChatId) {
    activeChatId = chatId;
  }

  const shouldActivatePanel = activeChatId === chatId;
  await loadDocumentsForChat(chatId, {
    openExisting: shouldActivatePanel,
    preferredDocumentId: documentId,
    activate: shouldActivatePanel,
  });

  if (shouldActivatePanel) {
    openDocumentPanel();
  }

  if (event.name === 'OFFICIAL_DOCUMENT_DRAFTED') {
    setDocumentStatus('AI Agent가 공문 초안을 생성했습니다.', 'success');
  } else if (event.name === 'OFFICIAL_DOCUMENT_APPROVED') {
    setDocumentStatus('공문이 승인되었습니다. PDF 다운로드가 가능합니다.', 'success');
  } else {
    setDocumentStatus('공문 수정사항이 저장되었습니다.', 'success');
  }

  render();
}

async function handleRealtimeEvent(event) {
  if (event.name === 'CONNECTED') {
    setConnectionStatus('online');
    return;
  }

  if (event.name.startsWith('OFFICIAL_DOCUMENT_')) {
    try {
      await handleDocumentEvent(event);
      setConnectionStatus('online');
    } catch (error) {
      console.warn('Document event synchronization failed:', error);
      setDocumentStatus(error.message, 'error');
    }
    return;
  }

  const eventPayload = parseEventPayload(event.data);
  const chatId = eventPayload?.chatSessionId ?? parseEventChatId(event.data);

  if (!chatId) {
    return;
  }

  if (event.name === 'CHAT_CREATED') {
    pendingChatPayloads.set(chatId, eventPayload);
    setConnectionStatus('online');
    return;
  }

  if (event.name === 'CHAT_MESSAGE_CREATED') {
    const chat = upsertRealtimeChatMessage(eventPayload);
    render();
    setConnectionStatus('online');

    if (chat?.messages.at(-1)?.role === 'assistant') {
      void refreshChatAfterCommit(chatId, { includeDocuments: true });
    }
    return;
  }

  if (event.name === 'AGENT_RESULT_READY') {
    upsertAssistantSuggestion(eventPayload);
    render();
    setConnectionStatus('online');
    void refreshChatAfterCommit(chatId, { includeDocuments: true });
    return;
  }

  try {
    await loadChat(chatId, { select: !activeChatId });
    if (chatId === activeChatId) {
      await loadDocumentsForChat(chatId);
    }
    setConnectionStatus('online');
  } catch {
    setConnectionStatus('offline');
  }
}

async function loadInitialChats() {
  try {
    const chats = await fetchChatList();
    chats.forEach(upsertChat);

    if (!activeChatId && chats.length > 0) {
      activeChatId = getChats()[0].id;
    }

    const activeChat = getActiveChat();

    if (activeChat) {
      await ensureCitizenProfile(activeChat.citizenId);
    }

    setConnectionStatus('online');
    render();

    if (activeChatId) {
      await loadDocumentsForChat(activeChatId, { openExisting: true });
    }
  } catch {
    setConnectionStatus('offline');
    render();
  }
}

function connectEventStream() {
  eventSource?.close();
  eventSource = openChatEventStream({
    onOpen: () => setConnectionStatus('online'),
    onError: () => setConnectionStatus('offline'),
    onEvent: handleRealtimeEvent,
  });
}

function quoteActiveAssistantReply() {
  const suggestion = getActiveAssistantSuggestion();

  if (!suggestion?.suggestedReply) {
    return;
  }

  elements.staffReplyInput.value = suggestion.suggestedReply;
  setStaffReplyStatus('답변 후보를 입력창에 복사했습니다.', 'success');
  renderComposer();
  elements.staffReplyInput.focus();
}

async function handleStaffMessageSubmit() {
  const activeChat = getActiveChat();
  const content = elements.staffReplyInput.value.trim();

  if (!activeChat || !content || isSendingStaffMessage) {
    return;
  }

  isSendingStaffMessage = true;
  setStaffReplyStatus('');
  renderComposer();

  try {
    const message = await sendStaffChatMessage(activeChat.id, content);
    upsertChatMessage(activeChat.id, message);
    elements.staffReplyInput.value = '';
    setStaffReplyStatus('담당자 답변을 전송했습니다.', 'success');
    setConnectionStatus('online');
  } catch (error) {
    setStaffReplyStatus(error.message, 'error');
    setConnectionStatus('offline');
  } finally {
    isSendingStaffMessage = false;
    render();
  }
}

elements.closeDocumentPanelButton.addEventListener('click', closeDocumentPanel);
elements.quoteAssistantReplyButton.addEventListener('click', quoteActiveAssistantReply);
elements.sendStaffMessageButton.addEventListener('click', () => {
  void handleStaffMessageSubmit();
});
elements.staffReplyInput.addEventListener('input', () => {
  if (elements.staffReplyStatus.classList.contains('error')) {
    setStaffReplyStatus('');
  }
  renderComposer();
});
elements.staffReplyInput.addEventListener('keydown', (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) {
    return;
  }

  event.preventDefault();
  void handleStaffMessageSubmit();
});

elements.generateDocumentButton.addEventListener('click', async () => {
  const activeChat = getActiveChat();
  if (!activeChat || isDocumentBusy) {
    return;
  }

  openDocumentPanel();
  const activeDocument = getActiveDocument();
  if (!activeDocument) {
    setDocumentStatus('빈 공문입니다.');
  } else {
    setDocumentStatus(
      activeDocument.status === 'APPROVED'
        ? '승인 완료. PDF 다운로드가 가능합니다.'
        : '공문 초안을 검토한 뒤 임시 저장 또는 승인할 수 있습니다.',
    );
  }
  render();
});

elements.manualGenerateDocumentButton.addEventListener('click', async () => {
  const activeChat = getActiveChat();
  if (!activeChat || isDocumentBusy) {
    return;
  }

  isDocumentBusy = true;
  activeDocumentId = null;
  openDocumentPanel();
  renderDocumentLoading(elements.documentPanelContent);
  setDocumentStatus('공문 작성 Agent가 초안을 생성하고 있습니다.');
  renderDocumentControls();

  try {
    const officialDocument = await createOfficialDocumentDraft(activeChat.id);
    upsertDocument(officialDocument);
    setDocumentStatus('공문 초안이 생성되었습니다.', 'success');
  } catch (error) {
    renderDocumentError(elements.documentPanelContent, error.message);
    setDocumentStatus(error.message, 'error');
  } finally {
    isDocumentBusy = false;
    render();
  }
});

elements.saveDocumentButton.addEventListener('click', async () => {
  const activeDocument = getActiveDocument();
  if (!activeDocument || isDocumentBusy) {
    return;
  }

  try {
    isDocumentBusy = true;
    renderDocumentControls();
    const draft = readDocumentDraft(elements.documentPanelContent);
    const document = await updateOfficialDocument(activeDocument.id, draft);
    upsertDocument(document);
    setDocumentStatus('공문 수정사항이 저장되었습니다.', 'success');
  } catch (error) {
    setDocumentStatus(error.message, 'error');
  } finally {
    isDocumentBusy = false;
    render();
  }
});

elements.approveDocumentButton.addEventListener('click', async () => {
  const activeDocument = getActiveDocument();
  if (!activeDocument || isDocumentBusy) {
    return;
  }

  try {
    isDocumentBusy = true;
    renderDocumentControls();
    const draft = readDocumentDraft(elements.documentPanelContent);
    const reviewedDocument = await updateOfficialDocument(activeDocument.id, draft);
    const approvedDocument = await approveOfficialDocument(reviewedDocument.id);
    upsertDocument(approvedDocument);
    setDocumentStatus('승인 완료. PDF 다운로드가 가능합니다.', 'success');
  } catch (error) {
    setDocumentStatus(error.message, 'error');
  } finally {
    isDocumentBusy = false;
    render();
  }
});

elements.downloadDocumentButton.addEventListener('click', async () => {
  const activeDocument = getActiveDocument();
  if (!activeDocument || isDocumentBusy) {
    return;
  }

  try {
    isDocumentBusy = true;
    renderDocumentControls();
    await downloadOfficialDocumentPdf(activeDocument);
    setDocumentStatus('PDF 다운로드를 시작했습니다.', 'success');
  } catch (error) {
    setDocumentStatus(error.message, 'error');
  } finally {
    isDocumentBusy = false;
    renderDocumentControls();
  }
});

renderDocumentEmpty(elements.documentPanelContent);
render();
loadInitialChats();
connectEventStream();
window.setInterval(() => {
  renderHeader();
  renderConversationList();
}, 60 * 1000);
