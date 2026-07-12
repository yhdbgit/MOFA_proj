/**
 * 상담 접수 UI와 메시지 상태를 관리한다.
 * 사용자가 보낸 메시지를 Spring Boot backend에 저장하고 상담사가 웹에서 보낸
 * 답변을 같은 채팅방 기준으로 갱신한다.
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
import {
  fetchConsularChatSession,
  sendConsularChatMessage,
} from '../services/consularChatApi';

const INITIAL_ASSISTANT_MESSAGE = {
  id: 'welcome',
  role: 'assistant',
  text: '안녕하세요. 영사콜센터 상담 접수입니다. 현재 계신 국가/도시와 상황을 알려주시면 상담사가 확인 후 답변드리겠습니다.',
};

const STAFF_MESSAGE_POLL_INTERVAL_MS = 2500;

// id는 FlatList 렌더링용이며, backend에는 API layer가 senderType/content로 변환해 보낸다.
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

export default function ChatScreen({ navigation, route }) {
  const [messages, setMessages] = useState([INITIAL_ASSISTANT_MESSAGE]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [chatId, setChatId] = useState(null);

  const listRef = useRef(null);

  // NOTE: state가 반영되기 전 연속 탭도 차단하기 위해 즉시 갱신되는 ref를 함께 쓴다.
  const isSendingRef = useRef(false);

  // 홈 화면에서 전달한 질문은 route 상태가 갱신되기 전 중복 렌더링되어도 한 번만 전송한다.
  const handledInitialMessageRef = useRef(null);
  const initialMessage = route?.params?.initialMessage?.trim() ?? '';

  const canSend = inputText.trim().length > 0 && !isSending;

  const scrollToEnd = useCallback(() => {
    requestAnimationFrame(() => {
      listRef.current?.scrollToEnd({ animated: true });
    });
  }, []);

  const refreshMessages = useCallback(async (nextChatId) => {
    if (!nextChatId) {
      return;
    }

    const chat = await fetchConsularChatSession(nextChatId);
    setMessages([INITIAL_ASSISTANT_MESSAGE, ...chat.messages]);
  }, []);

  const sendMessage = useCallback(
    async (rawText) => {
      const text = rawText.trim();

      if (!text || isSendingRef.current) {
        return;
      }

      const userMessage = createMessage('user', text);

      // API CONTRACT: backend가 chatId 기준으로 대화 이력을 저장한다.
      // 화면에는 기존 message shape을 유지하고, API layer에서 senderType으로 변환한다.
      const nextMessages = [...messages, userMessage];

      isSendingRef.current = true;
      setMessages(nextMessages);
      setInputText('');
      setIsSending(true);

      try {
        const result = await sendConsularChatMessage({ chatId, text });
        const nextChatId = chatId || result.chatId;

        if (!chatId) {
          setChatId(nextChatId);
        }

        await refreshMessages(nextChatId);
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
    [chatId, messages, refreshMessages],
  );

  const handleSubmit = useCallback(() => {
    void sendMessage(inputText);
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
          <Text style={styles.typingText}>상담 접수 중</Text>
        </View>
      </View>
    );
  }, [isSending]);

  useEffect(() => {
    if (!initialMessage) {
      handledInitialMessageRef.current = null;
      return;
    }

    if (handledInitialMessageRef.current === initialMessage) {
      return;
    }

    handledInitialMessageRef.current = initialMessage;
    navigation.setParams({ initialMessage: undefined });
    void sendMessage(initialMessage);
  }, [initialMessage, navigation, sendMessage]);

  useEffect(() => {
    if (!chatId) {
      return undefined;
    }

    let isMounted = true;

    const refresh = async () => {
      if (isSendingRef.current) {
        return;
      }

      try {
        const chat = await fetchConsularChatSession(chatId);
        if (isMounted) {
          setMessages([INITIAL_ASSISTANT_MESSAGE, ...chat.messages]);
        }
      } catch {
        // 기존 입력 흐름을 막지 않기 위해 다음 주기에서 다시 시도한다.
      }
    };

    const intervalId = setInterval(refresh, STAFF_MESSAGE_POLL_INTERVAL_MS);
    void refresh();

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [chatId]);

  // 새 메시지와 접수 상태가 추가될 때 항상 최신 대화가 보이도록 이동한다.
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
            <Text style={styles.headerTitle}>영사콜센터 상담 접수</Text>
            <Text style={styles.headerSubtitle}>상담사 확인 후 답변</Text>
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
