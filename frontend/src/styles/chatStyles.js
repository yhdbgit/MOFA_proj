/** AI 상담 화면의 메시지 목록, 말풍선, 입력 영역에 사용하는 스타일이다. */
import { StyleSheet } from 'react-native';

// 이 화면 안에서만 쓰는 색상은 외부로 노출하지 않는다.
const CHAT_COLORS = {
  primary: '#00B4C8',
  background: '#F5F8FA',
  white: '#FFFFFF',
  textDark: '#172026',
  textSub: '#5E6A70',
  textMuted: '#7A878D',
  assistantBubble: '#FFFFFF',
  assistantBorder: '#E4ECEF',
  inputBorder: '#DAE3E7',
  disabled: '#B8C7CD',
};

const chatStyles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: CHAT_COLORS.background,
  },
  keyboardView: {
    flex: 1,
  },

  header: {
    minHeight: 68,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingVertical: 12,
    backgroundColor: CHAT_COLORS.white,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: CHAT_COLORS.assistantBorder,
  },
  headerIcon: {
    width: 42,
    height: 42,
    borderRadius: 21,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: CHAT_COLORS.primary,
  },
  headerTextBlock: {
    flex: 1,
    marginLeft: 12,
  },
  headerTitle: {
    fontSize: 16,
    lineHeight: 21,
    fontWeight: '800',
    color: CHAT_COLORS.textDark,
  },
  headerSubtitle: {
    marginTop: 2,
    fontSize: 12,
    lineHeight: 16,
    color: CHAT_COLORS.textSub,
  },

  messageList: {
    flexGrow: 1,
    paddingHorizontal: 14,
    paddingTop: 16,
    paddingBottom: 14,
  },
  messageRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 10,
  },
  assistantMessageRow: {
    justifyContent: 'flex-start',
  },
  userMessageRow: {
    justifyContent: 'flex-end',
  },
  avatar: {
    width: 30,
    height: 30,
    borderRadius: 15,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    backgroundColor: CHAT_COLORS.primary,
  },
  messageBubble: {
    // 긴 답변에서도 사용자/상담사 방향을 구분할 수 있도록 화면 전체를 채우지 않는다.
    maxWidth: '78%',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 18,
  },
  userBubble: {
    borderBottomRightRadius: 6,
    backgroundColor: CHAT_COLORS.primary,
  },
  assistantBubble: {
    borderBottomLeftRadius: 6,
    backgroundColor: CHAT_COLORS.assistantBubble,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: CHAT_COLORS.assistantBorder,
  },
  messageText: {
    fontSize: 14,
    lineHeight: 21,
  },
  userMessageText: {
    color: CHAT_COLORS.white,
  },
  assistantMessageText: {
    color: CHAT_COLORS.textDark,
  },

  typingRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 10,
  },
  typingBubble: {
    minHeight: 40,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    borderRadius: 18,
    borderBottomLeftRadius: 6,
    backgroundColor: CHAT_COLORS.white,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: CHAT_COLORS.assistantBorder,
  },
  typingText: {
    marginLeft: 8,
    fontSize: 13,
    lineHeight: 18,
    color: CHAT_COLORS.textMuted,
  },

  inputArea: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 12,
    backgroundColor: CHAT_COLORS.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: CHAT_COLORS.assistantBorder,
  },
  input: {
    flex: 1,
    maxHeight: 120,
    minHeight: 44,
    paddingHorizontal: 14,
    paddingTop: 11,
    paddingBottom: 11,
    borderWidth: 1,
    borderColor: CHAT_COLORS.inputBorder,
    borderRadius: 22,
    fontSize: 14,
    lineHeight: 20,
    color: CHAT_COLORS.textDark,
    backgroundColor: CHAT_COLORS.background,
  },
  sendButton: {
    width: 44,
    height: 44,
    marginLeft: 8,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: CHAT_COLORS.primary,
  },
  sendButtonDisabled: {
    backgroundColor: CHAT_COLORS.disabled,
  },
});

export default chatStyles;
