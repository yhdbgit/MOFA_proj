/**
 * AI 상담 대화 UI와 메시지 상태를 관리한다.
 * 사용자가 보낸 메시지를 누적해 consularChatApi로 전달하고 reply를 새 상담 메시지로
 * 추가한다. 백엔드 통신 규칙 자체는 services/consularChatApi.js에 모아 둔다.
 */
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  TextInput,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import styles from '../styles/chatStyles';
import { sendConsularChatMessage } from '../services/consularChatApi';

const INITIAL_ASSISTANT_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  text: '안녕하세요. AI 영사콜센터 상담사입니다. 현재 계신 국가/도시와 상황을 알려주시면 필요한 조치를 안내드리겠습니다.',
};

// id는 FlatList 렌더링용이며, 백엔드가 답변을 만들 때 사용하는 값은 role과 text다.
function createMessage(role, text) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    role,
    text,
  };
}

function MessageBubble({ item }) {
  const isUser = item.role === 'user';

  return (
    <View
      style={[
        styles.messageRow,
        isUser ? styles.userMessageRow : styles.assistantMessageRow,
      ]}
    >
      {!isUser ? (
        <View style={styles.avatar}>
          <Ionicons name="headset-outline" size={17} color="#FFFFFF" />
        </View>
      ) : null}

      <View
        style={[
          styles.messageBubble,
          isUser ? styles.userBubble : styles.assistantBubble,
        ]}
      >
        <Text
          selectable
          style={[
            styles.messageText,
            isUser ? styles.userMessageText : styles.assistantMessageText,
          ]}
        >
          {item.text}
        </Text>
      </View>
    </View>
  );
}

export default function ChatScreen({ route }) {
  const [messages, setMessages] = useState([INITIAL_ASSISTANT_MESSAGE]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);

  const listRef = useRef(null);

  // NOTE: state가 반영되기 전 연속 탭도 차단하기 위해 즉시 갱신되는 ref를 함께 쓴다.
  const isSendingRef = useRef(false);

  // 홈 화면에서 전달한 첫 질문은 화면이 다시 렌더링되어도 한 번만 전송한다.
  const initialMessageRef = useRef(route?.params?.initialMessage?.trim() ?? '');

  const canSend = inputText.trim().length > 0 && !isSending;

  const scrollToEnd = useCallback(() => {
    requestAnimationFrame(() => {
      listRef.current?.scrollToEnd({ animated: true });
    });
  }, []);

  const sendMessage = useCallback(
    async (rawText) => {
      const text = rawText.trim();

      if (!text || isSendingRef.current) {
        return;
      }

      const userMessage = createMessage('user', text);

      // API CONTRACT: 환영 메시지를 포함해 현재 화면에 누적된 대화 전체를 전달한다.
      // 백엔드는 필요한 대화 범위를 자체 정책에 따라 선택할 수 있다.
      const nextMessages = [...messages, userMessage];

      isSendingRef.current = true;
      setMessages(nextMessages);
      setInputText('');
      setIsSending(true);

      try {
        const reply = await sendConsularChatMessage(nextMessages);
        setMessages((currentMessages) => [
          ...currentMessages,
          createMessage('assistant', reply),
        ]);
      } catch (error) {
        setMessages((currentMessages) => [
          ...currentMessages,
          createMessage(
            'assistant',
            error.message ??
              '상담 서버와 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.',
          ),
        ]);
      } finally {
        isSendingRef.current = false;
        setIsSending(false);
      }
    },
    [messages],
  );

  const handleSubmit = useCallback(() => {
    sendMessage(inputText);
  }, [inputText, sendMessage]);

  const handleInputKeyPress = useCallback(
    (event) => {
      const { key, shiftKey } = event.nativeEvent;

      if (key !== 'Enter' || shiftKey) {
        return;
      }

      event.preventDefault?.();
      handleSubmit();
    },
    [handleSubmit],
  );

  const footer = useMemo(() => {
    if (!isSending) {
      return null;
    }

    return (
      <View style={styles.typingRow}>
        <View style={styles.avatar}>
          <Ionicons name="headset-outline" size={17} color="#FFFFFF" />
        </View>
        <View style={styles.typingBubble}>
          <ActivityIndicator size="small" color="#00B4C8" />
          <Text style={styles.typingText}>답변 작성 중</Text>
        </View>
      </View>
    );
  }, [isSending]);

  useEffect(() => {
    const initialMessage = initialMessageRef.current;

    if (!initialMessage) {
      return;
    }

    initialMessageRef.current = '';
    sendMessage(initialMessage);
  }, [sendMessage]);

  // 새 메시지와 답변 작성 표시가 추가될 때 항상 최신 대화가 보이도록 이동한다.
  useEffect(() => {
    scrollToEnd();
  }, [messages, isSending, scrollToEnd]);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 8 : 0}
        style={styles.keyboardView}
      >
        <View style={styles.header}>
          <View style={styles.headerIcon}>
            <Ionicons name="shield-checkmark-outline" size={22} color="#FFFFFF" />
          </View>
          <View style={styles.headerTextBlock}>
            <Text style={styles.headerTitle}>AI 영사콜센터 상담사</Text>
            <Text style={styles.headerSubtitle}>해외안전여행 상담</Text>
          </View>
        </View>

        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <MessageBubble item={item} />}
          ListFooterComponent={footer}
          contentContainerStyle={styles.messageList}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
          onContentSizeChange={scrollToEnd}
        />

        <View style={styles.inputArea}>
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            onKeyPress={handleInputKeyPress}
            onSubmitEditing={handleSubmit}
            placeholder="상담 내용을 입력하세요."
            placeholderTextColor="#9AA3A7"
            returnKeyType="send"
            submitBehavior="submit"
            multiline
            maxLength={1200}
            style={styles.input}
          />

          <TouchableOpacity
            activeOpacity={0.8}
            accessibilityRole="button"
            accessibilityLabel="메시지 보내기"
            disabled={!canSend}
            onPress={handleSubmit}
            style={[
              styles.sendButton,
              !canSend && styles.sendButtonDisabled,
            ]}
          >
            <Ionicons name="arrow-up" size={20} color="#FFFFFF" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
