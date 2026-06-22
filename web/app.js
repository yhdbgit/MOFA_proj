import { fetchLatestChatMessages } from './chatMonitorApi.js';
import {
  createOfficialDocumentDraft,
  downloadOfficialDocumentPdf,
} from './officialDocumentApi.js';
import {
  readDocumentDraft,
  renderDocumentDraft,
  renderDocumentEmpty,
  renderDocumentError,
  renderDocumentLoading,
} from './documentPanel.js';

const POLL_INTERVAL_MS = 1000;

const elements = {
  activeConversationCount: document.getElementById('activeConversationCount'),
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
  generateDocumentButton: document.getElementById('generateDocumentButton'),
  messageCountBadge: document.getElementById('messageCountBadge'),
  messageList: document.getElementById('messageList'),
  saveDocumentButton: document.getElementById('saveDocumentButton'),
};

let latestMessages = [];
let latestFingerprint = '';
let isConversationSelected = false;
let currentDocumentResult = null;
let documentSourceFingerprint = '';
let isDocumentGenerating = false;
let isDocumentSaving = false;

function setDocumentPanelOpen(isOpen) {
  elements.documentPanel.classList.toggle('open', isOpen);
  elements.documentPanel.setAttribute('aria-hidden', String(!isOpen));
}

function setDocumentStatus(message = '', type = '') {
  elements.documentStatusText.textContent = message;
  elements.documentStatusText.className = type;
}

function resetDocumentDraft() {
  currentDocumentResult = null;
  documentSourceFingerprint = '';
  elements.saveDocumentButton.hidden = true;
  setDocumentStatus();
  renderDocumentEmpty(elements.documentPanelContent);
  setDocumentPanelOpen(false);
}

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

function selectCurrentConversation() {
  isConversationSelected = true;
  render();
}

function updateDocumentButton() {
  const canGenerate =
    isConversationSelected &&
    latestMessages.length > 0 &&
    !isDocumentGenerating;

  elements.generateDocumentButton.disabled = !canGenerate;
  elements.generateDocumentButton.textContent = isDocumentGenerating
    ? '생성 중…'
    : '📄 공문 생성';
}

function renderConversationList() {
  elements.conversationList.replaceChildren();

  if (latestMessages.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'sidebar-empty';

    const icon = document.createElement('span');
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '📭';

    const text = document.createElement('p');
    text.innerHTML = '민원인이 채팅을 시작하면<br />현재 상담이 표시됩니다.';

    empty.append(icon, text);
    elements.conversationList.append(empty);
    return;
  }

  const lastMessage = latestMessages.at(-1);
  const item = document.createElement('button');
  item.type = 'button';
  item.className = `conversation-item${isConversationSelected ? ' active' : ''}`;
  item.setAttribute('aria-pressed', String(isConversationSelected));
  item.addEventListener('click', selectCurrentConversation);

  const header = document.createElement('div');
  header.className = 'conversation-item-header';

  const title = document.createElement('span');
  title.className = 'conversation-item-title';
  title.textContent = '현재 AI 상담';

  const live = document.createElement('span');
  live.className = 'live-label';
  live.textContent = '실시간';

  const preview = document.createElement('p');
  preview.className = 'conversation-preview';
  preview.textContent = lastMessage.text;

  const footer = document.createElement('div');
  footer.className = 'conversation-item-footer';

  const sender = document.createElement('span');
  sender.textContent = lastMessage.role === 'user' ? '민원인 메시지' : 'AI 답변';

  const count = document.createElement('span');
  count.textContent = `${latestMessages.length}개 메시지`;

  header.append(title, live);
  footer.append(sender, count);
  item.append(header, preview, footer);
  elements.conversationList.append(item);
}

function renderMessages() {
  elements.messageList.replaceChildren();

  if (latestMessages.length === 0) {
    elements.messageList.append(
      createEmptyState(
        '💬',
        '표시할 상담이 없습니다',
        '모바일 앱에서 메시지를 보내면 이 화면에 최신 대화가 표시됩니다.',
      ),
    );
    return;
  }

  if (!isConversationSelected) {
    elements.messageList.append(
      createEmptyState(
        '👈',
        '상담을 선택해 주세요',
        '왼쪽의 현재 상담을 선택하면 전체 대화가 표시됩니다.',
      ),
    );
    return;
  }

  const fragment = document.createDocumentFragment();

  latestMessages.forEach((message) => {
    const article = document.createElement('article');
    article.className = `message ${message.role}`;

    const sender = document.createElement('div');
    sender.className = 'message-sender';
    sender.textContent = message.role === 'user' ? '민원인' : 'AI 상담사';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = message.text;

    article.append(sender, bubble);
    fragment.append(article);
  });

  elements.messageList.append(fragment);
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function renderHeader() {
  const hasConversation = latestMessages.length > 0;

  elements.activeConversationCount.textContent = hasConversation ? '1' : '0';
  elements.conversationCountText.textContent = hasConversation
    ? '현재 진행 중인 상담 1건'
    : '현재 진행 중인 상담이 없습니다.';

  if (!hasConversation) {
    elements.chatTitle.textContent = '상담을 기다리는 중입니다';
    elements.chatSubtitle.textContent =
      '왼쪽 목록에서 상담을 선택하면 대화가 표시됩니다.';
    elements.messageCountBadge.hidden = true;
    updateDocumentButton();
    return;
  }

  elements.chatTitle.textContent = isConversationSelected
    ? '현재 AI 상담'
    : '상담을 선택해 주세요';
  elements.chatSubtitle.textContent = isConversationSelected
    ? '민원인과 AI 상담사의 대화를 읽기 전용으로 표시합니다.'
    : '왼쪽 목록에서 현재 상담을 선택하세요.';
  elements.messageCountBadge.hidden = false;
  elements.messageCountBadge.textContent = `${latestMessages.length}개 메시지`;
  updateDocumentButton();
}

function render() {
  renderHeader();
  renderConversationList();
  renderMessages();
}

async function pollLatestMessages() {
  try {
    const messages = await fetchLatestChatMessages();
    const nextFingerprint = JSON.stringify(messages);

    setConnectionStatus('online');

    if (nextFingerprint !== latestFingerprint) {
      if (
        currentDocumentResult &&
        nextFingerprint !== documentSourceFingerprint
      ) {
        resetDocumentDraft();
      }

      latestMessages = messages;
      latestFingerprint = nextFingerprint;

      if (latestMessages.length === 0) {
        isConversationSelected = false;
      }

      render();
    }
  } catch {
    setConnectionStatus('offline');
  } finally {
    window.setTimeout(pollLatestMessages, POLL_INTERVAL_MS);
  }
}

async function handleGenerateDocument() {
  if (!isConversationSelected || latestMessages.length === 0) {
    return;
  }

  if (
    currentDocumentResult &&
    documentSourceFingerprint === latestFingerprint
  ) {
    setDocumentPanelOpen(true);
    return;
  }

  const sourceFingerprint = latestFingerprint;
  isDocumentGenerating = true;
  updateDocumentButton();
  setDocumentPanelOpen(true);
  elements.saveDocumentButton.hidden = true;
  setDocumentStatus('상담 내용을 분석하고 있습니다.');
  renderDocumentLoading(elements.documentPanelContent);

  try {
    const result = await createOfficialDocumentDraft(latestMessages);

    if (sourceFingerprint !== latestFingerprint) {
      throw new Error(
        '공문 생성 중 상담 내용이 변경되었습니다. 다시 생성해 주세요.',
      );
    }

    currentDocumentResult = result;
    documentSourceFingerprint = sourceFingerprint;
    renderDocumentDraft(elements.documentPanelContent, result);
    elements.saveDocumentButton.hidden = false;
    setDocumentStatus(
      result.status === 'incomplete'
        ? '확인되지 않은 항목을 수정한 뒤 저장해 주세요.'
        : '초안을 바로 수정할 수 있습니다.',
    );
  } catch (error) {
    currentDocumentResult = null;
    documentSourceFingerprint = '';
    elements.saveDocumentButton.hidden = true;
    renderDocumentError(
      elements.documentPanelContent,
      error.message || '공문 초안을 생성하지 못했습니다.',
    );
    setDocumentStatus('공문 생성에 실패했습니다.', 'error');
  } finally {
    isDocumentGenerating = false;
    updateDocumentButton();
  }
}

async function handleSaveDocument() {
  if (!currentDocumentResult || isDocumentSaving) {
    return;
  }

  try {
    const editedDraft = readDocumentDraft(elements.documentPanelContent);
    isDocumentSaving = true;
    elements.saveDocumentButton.disabled = true;
    elements.saveDocumentButton.textContent = '저장 중…';
    setDocumentStatus('PDF 파일을 생성하고 있습니다.');
    await downloadOfficialDocumentPdf(editedDraft);
    currentDocumentResult = {
      ...currentDocumentResult,
      draft: editedDraft,
    };
    setDocumentStatus('PDF 파일이 저장되었습니다.', 'success');
  } catch (error) {
    setDocumentStatus(
      error.message || 'PDF 파일을 저장하지 못했습니다.',
      'error',
    );
  } finally {
    isDocumentSaving = false;
    elements.saveDocumentButton.disabled = false;
    elements.saveDocumentButton.textContent = '저장';
  }
}

elements.generateDocumentButton.addEventListener('click', handleGenerateDocument);
elements.closeDocumentPanelButton.addEventListener('click', () => {
  setDocumentPanelOpen(false);
});
elements.saveDocumentButton.addEventListener('click', handleSaveDocument);

renderDocumentEmpty(elements.documentPanelContent);
render();
pollLatestMessages();
