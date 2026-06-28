/**
 * 앱의 홈 화면과 주요 기능 진입점을 구성한다.
 * 이 파일은 화면 표시와 탭 이동만 담당하며, AI 상담 통신은 ChatScreen에서 시작한다.
 */
import React, {
  useCallback,
  useMemo,
  useState,
} from 'react';
import {
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  StatusBar,
  Alert,
  Keyboard,
  Platform,
} from 'react-native';
import {
  SafeAreaView,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import ROUTES from '../constants/routes';
import styles, { HOME_COLORS } from '../styles/homeStyles';

const HEADER_ACTIONS = [
  {
    key: 'calendar',
    label: '일정',
    icon: 'calendar-outline',
  },
  {
    key: 'notification',
    label: '알림',
    icon: 'notifications-outline',
  },
  {
    key: 'settings',
    label: '설정',
    icon: 'settings-outline',
  },
  {
    key: 'menu',
    label: '메뉴',
    icon: 'menu-outline',
  },
];

const MAIN_FEATURE = {
  key: 'location-safety',
  title: '내 위치 안전정보',
  description: 'GPS기준 국가별\n안전정보를 제공합니다.',
  emoji: '🗺️',
  routeName: ROUTES.LOCATION_SAFETY,
};

// TODO(frontend): routeName이 null인 카드는 아직 화면이 없어 준비 중 알림을 표시한다.
const SUB_FEATURES = [
  {
    key: 'country-warning',
    title: '국가/지역별\n여행경보',
    emoji: '🚨',
    routeName: null,
  },
  {
    key: 'map-warning',
    title: '지도로 보는\n여행경보',
    emoji: '🌐',
    routeName: null,
  },
];

function Header({ onActionPress }) {
  return (
    <View style={styles.header}>
      <View style={styles.headerLeft}>
        <View style={styles.logoCircle}>
          <Text style={styles.logoText}>🇰🇷</Text>
        </View>

        <View>
          <Text style={styles.headerTitle}>외교부</Text>
          <Text style={styles.headerSubtitle}>해외안전여행</Text>
        </View>
      </View>

      <View style={styles.headerIcons}>
        {HEADER_ACTIONS.map((action) => (
          <TouchableOpacity
            key={action.key}
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityLabel={`${action.label} 열기`}
            onPress={() => onActionPress(action)}
            style={styles.iconBtn}
          >
            <Ionicons
              name={action.icon}
              size={action.key === 'menu' ? 24 : 22}
              color={HOME_COLORS.textDefault}
            />
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );
}

function HeroSection() {
  return (
    <View style={styles.hero}>
      <View style={styles.heroContent}>
        <View style={styles.heroTextBlock}>
          <Text style={styles.heroText}>안전한 해외여행,</Text>
          <Text style={styles.heroBold}>
            외교부 해외안전여행 앱과{'\n'}함께하세요.
          </Text>
        </View>

        <View style={styles.heroBalloon}>
          <Text style={styles.balloonEmoji}>🎈</Text>
        </View>
      </View>
    </View>
  );
}

function AiChatInput({
  value,
  onChangeText,
  onSubmit,
}) {
  const showAndroidClearButton = Platform.OS !== 'ios' && value.length > 0;

  return (
    <View style={styles.chatInputWrapper}>
      <View style={styles.chatInputBox}>
        <Ionicons
          name="sparkles-outline"
          size={18}
          color={HOME_COLORS.primary}
          style={styles.chatInputIcon}
        />

        <TextInput
          value={value}
          onChangeText={onChangeText}
          onSubmitEditing={onSubmit}
          placeholder="AI 상담사에게 무엇이든 물어보세요."
          placeholderTextColor={HOME_COLORS.placeholder}
          returnKeyType="send"
          autoCorrect={false}
          autoCapitalize="none"
          clearButtonMode="while-editing"
          style={styles.chatTextInput}
        />

        {showAndroidClearButton && (
          <TouchableOpacity
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityLabel="입력 내용 지우기"
            onPress={() => onChangeText('')}
            style={styles.clearInputButton}
          >
            <Ionicons
              name="close-circle"
              size={18}
              color={HOME_COLORS.placeholder}
            />
          </TouchableOpacity>
        )}

        <TouchableOpacity
          activeOpacity={0.8}
          accessibilityRole="button"
          accessibilityLabel="AI 상담사 화면으로 이동"
          onPress={onSubmit}
          style={styles.chatSubmitButton}
        >
          <Ionicons
            name="arrow-forward"
            size={18}
            color={HOME_COLORS.white}
          />
        </TouchableOpacity>
      </View>
    </View>
  );
}

function LargeFeatureCard({ item, onPress }) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={item.title.replace(/\n/g, ' ')}
      onPress={onPress}
      style={styles.cardLarge}
    >
      <View style={styles.cardTextBlock}>
        <Text style={styles.cardTitle}>{item.title}</Text>
        <Text style={styles.cardDesc}>{item.description}</Text>
      </View>

      <View style={styles.cardIconWrap}>
        <View style={styles.cardIconBg}>
          <Text style={styles.cardIconEmoji}>{item.emoji}</Text>
        </View>
      </View>
    </TouchableOpacity>
  );
}

function SmallFeatureCard({
  item,
  onPress,
  isFirst,
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={item.title.replace(/\n/g, ' ')}
      onPress={onPress}
      style={[
        styles.cardSmall,
        isFirst && styles.cardSmallSpacing,
      ]}
    >
      <Text style={styles.cardSmallTitle}>{item.title}</Text>
      <Text style={styles.cardSmallEmoji}>{item.emoji}</Text>
    </TouchableOpacity>
  );
}

function SafetyCards({ onFeaturePress }) {
  return (
    <View style={styles.cardsSection}>
      <LargeFeatureCard
        item={MAIN_FEATURE}
        onPress={() => onFeaturePress(MAIN_FEATURE)}
      />

      <View style={styles.cardRow}>
        {SUB_FEATURES.map((item, index) => (
          <SmallFeatureCard
            key={item.key}
            item={item}
            isFirst={index === 0}
            onPress={() => onFeaturePress(item)}
          />
        ))}
      </View>
    </View>
  );
}

function TripRegisterSection({ onPress }) {
  return (
    <TouchableOpacity
      activeOpacity={0.8}
      accessibilityRole="button"
      accessibilityLabel="여행일정 등록하기"
      onPress={onPress}
      style={styles.tripSection}
    >
      <View style={styles.tripHeader}>
        <Text style={styles.tripTitle}>여행일정 등록하기</Text>
        <Ionicons
          name="chevron-forward"
          size={18}
          color={HOME_COLORS.textDefault}
        />
      </View>

      <Text style={styles.tripDesc}>
        실시간 해외안전정보와 위급상황 발생 시 가족 또는 지인에게{'\n'}
        내 위치를 전송할 수 있습니다.
      </Text>
    </TouchableOpacity>
  );
}

function FloatingButton({
  bottomOffset,
  onPress,
}) {
  return (
    <TouchableOpacity
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel="영사안전 콜센터 열기"
      onPress={onPress}
      style={[
        styles.floatingBtn,
        {
          bottom: bottomOffset,
        },
      ]}
    >
      <Text style={styles.floatingBtnText}>
        영사안전{'\n'}콜센터
      </Text>
    </TouchableOpacity>
  );
}

export default function HomeScreen({ navigation }) {
  const [chatMessage, setChatMessage] = useState('');

  const insets = useSafeAreaInsets();
  const tabBarHeight = useBottomTabBarHeight();

  // 커스텀 탭바 및 기기 하단 안전 영역과 플로팅 버튼이 겹치지 않게 한다.
  const floatingBottomOffset = Math.max(tabBarHeight + 16, insets.bottom + 24);

  // 스크롤 마지막 콘텐츠가 플로팅 버튼과 탭바 뒤에 가려지지 않도록 여백을 확보한다.
  const scrollContentStyle = useMemo(
    () => [
      styles.scrollContent,
      {
        paddingBottom: tabBarHeight + 112,
      },
    ],
    [tabBarHeight],
  );

  const showPendingFeatureAlert = useCallback((featureName) => {
    Alert.alert(
      '준비 중',
      `${featureName} 기능은 다음 단계에서 연결하면 됩니다.`,
    );
  }, []);

  const navigateToRoute = useCallback(
    (routeName, params) => {
      if (!routeName) {
        return;
      }

      navigation.navigate(routeName, params);
    },
    [navigation],
  );

  const handleHeaderActionPress = useCallback(
    (action) => {
      showPendingFeatureAlert(action.label);
    },
    [showPendingFeatureAlert],
  );

  const handleAiChatSubmit = useCallback(() => {
    const initialMessage = chatMessage.trim();

    Keyboard.dismiss();

    // NAVIGATION CONTRACT: 홈에서 입력한 질문은 AI 상담 탭의 initialMessage로 넘긴다.
    // ChatScreen은 이 값을 최초 한 번 자동 전송한다.
    navigateToRoute(
      ROUTES.AI_CHAT,
      initialMessage ? { initialMessage } : undefined,
    );
    setChatMessage('');
  }, [chatMessage, navigateToRoute]);

  const handleFeaturePress = useCallback(
    (item) => {
      if (item.routeName) {
        navigateToRoute(item.routeName);
        return;
      }

      showPendingFeatureAlert(item.title.replace(/\n/g, ' '));
    },
    [navigateToRoute, showPendingFeatureAlert],
  );

  const handleTripRegisterPress = useCallback(() => {
    showPendingFeatureAlert('여행일정 등록');
  }, [showPendingFeatureAlert]);

  const handleFloatingButtonPress = useCallback(() => {
    navigateToRoute(ROUTES.CONSULAR_CALL);
  }, [navigateToRoute]);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor={HOME_COLORS.white} />

      <Header onActionPress={handleHeaderActionPress} />

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={scrollContentStyle}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <HeroSection />

        <AiChatInput
          value={chatMessage}
          onChangeText={setChatMessage}
          onSubmit={handleAiChatSubmit}
        />

        <SafetyCards onFeaturePress={handleFeaturePress} />

        <TripRegisterSection onPress={handleTripRegisterPress} />
      </ScrollView>

      <FloatingButton
        bottomOffset={floatingBottomOffset}
        onPress={handleFloatingButtonPress}
      />
    </SafeAreaView>
  );
}
