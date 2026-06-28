import {
  fetchChat,
  fetchChatList,
  openChatEventStream,
} from './chatMonitorApi.js';

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

const chatsById = new Map();
let activeChatId = null;
let eventSource = null;

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

function disableDocumentGeneration() {
  elements.generateDocumentButton.disabled = true;
  elements.generateDocumentButton.textContent = '공문 생성';
  elements.saveDocumentButton.hidden = true;
  elements.documentStatusText.textContent = '';
  elements.documentPanelContent.replaceChildren();
  closeDocumentPanel();
}

function getChats() {
  return [...chatsById.values()].sort((left, right) => {
    return getActivityTime(right) - getActivityTime(left);
  });
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

function formatChatId(chatId) {
  if (typeof chatId !== 'string' || chatId.length <= 8) {
    return chatId;
  }

  return `채팅방 ${chatId.slice(0, 8)}`;
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

function upsertChat(chat) {
  chatsById.set(chat.id, chat);

  if (!activeChatId) {
    activeChatId = chat.id;
  }
}

async function loadChat(chatId, { select = false } = {}) {
  const chat = await fetchChat(chatId);
  upsertChat(chat);

  if (select) {
    activeChatId = chat.id;
  }

  render();
}

async function selectChat(chatId) {
  activeChatId = chatId;
  render();

  try {
    await loadChat(chatId, { select: true });
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
    title.textContent = `${chat.countryCode} 상담`;

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

  const activeChat = activeChatId ? chatsById.get(activeChatId) : null;

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
    article.className = `message ${message.role}`;

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

function renderHeader() {
  const chats = getChats();
  const activeChat = activeChatId ? chatsById.get(activeChatId) : null;
  const count = chats.length;

  elements.activeConversationCount.textContent = String(count);
  elements.conversationCountText.textContent =
    count > 0 ? `누적 상담 ${count}건` : '현재 진행 중인 상담이 없습니다.';

  if (!activeChat) {
    elements.chatTitle.textContent = '상담을 기다리는 중입니다';
    elements.chatSubtitle.textContent =
      '왼쪽 목록에서 상담을 선택하면 대화가 표시됩니다.';
    elements.messageCountBadge.hidden = true;
    return;
  }

  elements.chatTitle.textContent = `${activeChat.countryCode} 상담`;
  elements.chatSubtitle.textContent = `${formatChatId(activeChat.id)} · ${activeChat.status} · ${formatRelativeTime(
    getActivityIso(activeChat),
  )}`;
  elements.chatSubtitle.title = activeChat.id;
  elements.messageCountBadge.hidden = false;
  elements.messageCountBadge.textContent = `${activeChat.messages.length}개 메시지`;
}

function render() {
  disableDocumentGeneration();
  renderHeader();
  renderConversationList();
  renderMessages();
}

function parseEventChatId(eventData) {
  try {
    return JSON.parse(eventData)?.chatSessionId ?? null;
  } catch {
    return null;
  }
}

async function handleRealtimeEvent(event) {
  if (event.name === 'CONNECTED') {
    setConnectionStatus('online');
    return;
  }

  const chatId = parseEventChatId(event.data);

  if (!chatId) {
    return;
  }

  try {
    await loadChat(chatId, { select: !activeChatId });
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

    setConnectionStatus('online');
    render();
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

elements.closeDocumentPanelButton.addEventListener('click', closeDocumentPanel);

disableDocumentGeneration();
render();
loadInitialChats();
connectEventStream();
window.setInterval(render, 60 * 1000);
