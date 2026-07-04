/**
 * 앱의 홈 화면과 주요 기능 진입점을 구성한다.
 * 이 파일은 화면 표시와 탭 이동만 담당하며, AI 상담 통신은 ChatScreen에서 시작한다.
 */
import React, {
  useCallback,
  useEffect,
  useRef,
  useMemo,
  useState,
} from 'react';
import {
  Animated,
  View,
  Text,
  ScrollView,
  TextInput,
  TouchableOpacity,
  Modal,
  StatusBar,
  Alert,
  Keyboard,
  Platform,
  KeyboardAvoidingView,
} from 'react-native';
import {
  SafeAreaView,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';
import { useBottomTabBarHeight } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import ROUTES from '../constants/routes';
import styles, { HOME_COLORS } from '../styles/homeStyles';
import {
  getCitizenProfile,
  saveCitizenProfile,
} from '../services/citizenProfileApi';

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

const DEFAULT_PROFILE_FORM = {
  name: '',
  birthDate: '',
  phoneNumber: '',
  gender: 'MALE',
};

const GENDER_OPTIONS = [
  { value: 'MALE', label: '남' },
  { value: 'FEMALE', label: '여' },
];

const REQUIRED_PRIVACY_CONSENTS = [
  {
    id: 'collectionUse',
    title: '개인정보 수집·이용 동의',
    description:
      '이름, 전화번호, 생년월일, 성별을 해외 위험상황 대응, 신원 확인, 공문 작성, 사용자 연락을 위해 수집·이용합니다.',
  },
  {
    id: 'thirdPartyTransfer',
    title: '긴급상황 대응을 위한 개인정보 제3자 제공 및 국외이전 동의',
    description:
      '위험상황 발생 시 사용자의 이름, 전화번호, 생년월일, 성별을 외교부, 재외공관, 현지 경찰·소방·의료기관·구조기관, 지정 긴급연락처에 제공할 수 있습니다.',
  },
  {
    id: 'privacyPolicy',
    title: '개인정보처리방침 확인',
    description:
      '개인정보 처리 목적, 보유 기간, 파기 절차, 위탁 업체, 국외이전 사항 등을 확인했습니다.',
  },
];

const INITIAL_PRIVACY_CONSENT_STATE = REQUIRED_PRIVACY_CONSENTS.reduce(
  (state, consent) => ({
    ...state,
    [consent.id]: false,
  }),
  {},
);

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

function GenderSegmentedControl({
  value,
  onChange,
}) {
  const slideValue = useRef(new Animated.Value(value === 'FEMALE' ? 1 : 0)).current;
  const [trackWidth, setTrackWidth] = useState(0);

  useEffect(() => {
    Animated.timing(slideValue, {
      toValue: value === 'FEMALE' ? 1 : 0,
      duration: 180,
      useNativeDriver: true,
    }).start();
  }, [slideValue, value]);

  const translateX = slideValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0, Math.max(trackWidth / 2 - 3, 0)],
  });

  return (
    <View
      style={styles.genderTrack}
      onLayout={(event) => setTrackWidth(event.nativeEvent.layout.width)}
    >
      <Animated.View
        pointerEvents="none"
        style={[
          styles.genderThumb,
          {
            transform: [{ translateX }],
          },
        ]}
      />

      {GENDER_OPTIONS.map((option) => {
        const isSelected = value === option.value;

        return (
          <TouchableOpacity
            key={option.value}
            activeOpacity={0.82}
            accessibilityRole="button"
            accessibilityState={isSelected ? { selected: true } : {}}
            accessibilityLabel={`${option.label} 선택`}
            onPress={() => onChange(option.value)}
            style={styles.genderOption}
          >
            <Text
              style={[
                styles.genderOptionText,
                isSelected && styles.genderOptionTextActive,
              ]}
            >
              {option.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

function BasicInfoModal({
  visible,
  form,
  isSaving,
  onChangeField,
  onClose,
  onSubmit,
}) {
  const [privacyConsents, setPrivacyConsents] = useState(
    INITIAL_PRIVACY_CONSENT_STATE,
  );
  const [expandedConsentIds, setExpandedConsentIds] = useState({});
  const [showConsentError, setShowConsentError] = useState(false);

  const isAllPrivacyConsented = REQUIRED_PRIVACY_CONSENTS.every(
    (consent) => privacyConsents[consent.id],
  );

  useEffect(() => {
    if (!visible) {
      return;
    }

    setPrivacyConsents(INITIAL_PRIVACY_CONSENT_STATE);
    setExpandedConsentIds({});
    setShowConsentError(false);
  }, [visible]);

  useEffect(() => {
    if (isAllPrivacyConsented) {
      setShowConsentError(false);
    }
  }, [isAllPrivacyConsented]);

  const toggleAllPrivacyConsents = useCallback(() => {
    const nextValue = !isAllPrivacyConsented;

    setPrivacyConsents(
      REQUIRED_PRIVACY_CONSENTS.reduce(
        (state, consent) => ({
          ...state,
          [consent.id]: nextValue,
        }),
        {},
      ),
    );
    setShowConsentError(false);
  }, [isAllPrivacyConsented]);

  const togglePrivacyConsent = useCallback((consentId) => {
    setPrivacyConsents((currentConsents) => {
      return {
        ...currentConsents,
        [consentId]: !currentConsents[consentId],
      };
    });
  }, []);

  const toggleConsentDetails = useCallback((consentId) => {
    setExpandedConsentIds((currentIds) => ({
      ...currentIds,
      [consentId]: !currentIds[consentId],
    }));
  }, []);

  const handleSubmitPress = useCallback(() => {
    if (!isAllPrivacyConsented) {
      setShowConsentError(true);
      return;
    }

    onSubmit();
  }, [isAllPrivacyConsented, onSubmit]);

  return (
    <Modal
      visible={visible}
      animationType="fade"
      transparent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={styles.modalBackdrop}
      >
        <View style={styles.profileModal}>
          <ScrollView
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
            style={styles.profileModalScroll}
            contentContainerStyle={styles.profileModalContent}
          >
            <Text style={styles.modalTitle}>기본 정보 등록</Text>

            <View style={styles.formGroup}>
              <Text style={styles.inputLabel}>이름</Text>
              <TextInput
                value={form.name}
                onChangeText={(value) => onChangeField('name', value)}
                placeholder="이름을 입력하세요"
                placeholderTextColor={HOME_COLORS.placeholder}
                autoCapitalize="none"
                style={styles.modalInput}
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.inputLabel}>생년월일</Text>
              <TextInput
                value={form.birthDate}
                onChangeText={(value) => onChangeField('birthDate', value)}
                placeholder="예: 1990-01-01"
                placeholderTextColor={HOME_COLORS.placeholder}
                keyboardType="numbers-and-punctuation"
                style={styles.modalInput}
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.inputLabel}>전화번호</Text>
              <TextInput
                value={form.phoneNumber}
                onChangeText={(value) => onChangeField('phoneNumber', value)}
                placeholder="예: 01012345678"
                placeholderTextColor={HOME_COLORS.placeholder}
                keyboardType="phone-pad"
                style={styles.modalInput}
              />
            </View>

            <View style={styles.formGroup}>
              <Text style={styles.inputLabel}>성별</Text>
              <GenderSegmentedControl
                value={form.gender}
                onChange={(value) => onChangeField('gender', value)}
              />
            </View>

            <View style={styles.privacyConsentSection}>
              <View style={styles.privacyConsentAllRow}>
                <TouchableOpacity
                  activeOpacity={0.75}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: isAllPrivacyConsented }}
                  accessibilityLabel="개인정보 필수 항목 전체동의"
                  onPress={toggleAllPrivacyConsents}
                  style={styles.privacyConsentAllButton}
                >
                  <Ionicons
                    name={isAllPrivacyConsented ? 'checkbox' : 'square-outline'}
                    size={22}
                    color={
                      isAllPrivacyConsented
                        ? HOME_COLORS.primary
                        : HOME_COLORS.textMuted
                    }
                  />
                  <Text style={styles.privacyConsentAllText}>전체동의</Text>
                </TouchableOpacity>

                {showConsentError ? (
                  <Text style={styles.privacyConsentError}>
                    필수 항목을 동의해주세요
                  </Text>
                ) : null}
              </View>

              <View style={styles.privacyConsentDivider} />

              {REQUIRED_PRIVACY_CONSENTS.map((consent) => {
                const isChecked = privacyConsents[consent.id];
                const isExpanded = expandedConsentIds[consent.id];

                return (
                  <View key={consent.id} style={styles.privacyConsentItem}>
                    <View style={styles.privacyConsentRow}>
                      <TouchableOpacity
                        activeOpacity={0.75}
                        accessibilityRole="checkbox"
                        accessibilityState={{ checked: isChecked }}
                        accessibilityLabel={`${consent.title} 필수 동의`}
                        onPress={() => togglePrivacyConsent(consent.id)}
                        style={styles.privacyConsentCheckButton}
                      >
                        <Ionicons
                          name={isChecked ? 'checkbox' : 'square-outline'}
                          size={21}
                          color={
                            isChecked
                              ? HOME_COLORS.primary
                              : HOME_COLORS.textMuted
                          }
                        />
                      </TouchableOpacity>

                      <TouchableOpacity
                        activeOpacity={0.75}
                        accessibilityRole="button"
                        accessibilityLabel={`${consent.title} 내용 ${
                          isExpanded ? '접기' : '보기'
                        }`}
                        onPress={() => toggleConsentDetails(consent.id)}
                        style={styles.privacyConsentTextButton}
                      >
                        <Text style={styles.privacyConsentTitle}>
                          {consent.title}
                        </Text>
                        <Text style={styles.privacyConsentRequired}>필수</Text>
                      </TouchableOpacity>

                      <TouchableOpacity
                        activeOpacity={0.75}
                        accessibilityRole="button"
                        accessibilityLabel={`${consent.title} 내용 ${
                          isExpanded ? '접기' : '보기'
                        }`}
                        onPress={() => toggleConsentDetails(consent.id)}
                        style={styles.privacyConsentChevronButton}
                      >
                        <Ionicons
                          name={isExpanded ? 'chevron-up' : 'chevron-down'}
                          size={19}
                          color={HOME_COLORS.textMuted}
                        />
                      </TouchableOpacity>
                    </View>

                    {isExpanded ? (
                      <Text style={styles.privacyConsentDescription}>
                        {consent.description}
                      </Text>
                    ) : null}
                  </View>
                );
              })}
            </View>
          </ScrollView>

          <View style={styles.modalButtonRow}>
            <TouchableOpacity
              activeOpacity={0.75}
              accessibilityRole="button"
              accessibilityLabel="기본 정보 등록 취소"
              disabled={isSaving}
              onPress={onClose}
              style={[styles.modalButton, styles.cancelButton]}
            >
              <Text style={styles.cancelButtonText}>취소</Text>
            </TouchableOpacity>

            <TouchableOpacity
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel="기본 정보 등록"
              disabled={isSaving}
              onPress={handleSubmitPress}
              style={[
                styles.modalButton,
                styles.submitButton,
                isSaving && styles.submitButtonDisabled,
              ]}
            >
              <Text style={styles.submitButtonText}>
                {isSaving ? '등록 중' : '등록'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

function BasicInfoSection({
  isRegistered,
  showWarning,
  onDismissWarning,
  onPress,
}) {
  return (
    <View style={styles.profileSectionWrapper}>
      {showWarning ? (
        <View style={styles.profileWarningBubble}>
          <Text style={styles.profileWarningText}>
            ⚠️ 사용자의 기본 정보가 등록되지 않았습니다.
          </Text>
          <TouchableOpacity
            activeOpacity={0.75}
            accessibilityRole="button"
            accessibilityLabel="기본 정보 미등록 안내 닫기"
            onPress={onDismissWarning}
            style={styles.warningCloseButton}
          >
            <Ionicons name="close" size={16} color={HOME_COLORS.warningText} />
          </TouchableOpacity>
        </View>
      ) : null}

      <TouchableOpacity
        activeOpacity={0.82}
        accessibilityRole="button"
        accessibilityLabel="나의 기본 정보 등록하기"
        onPress={onPress}
        style={[
          styles.profileSection,
          !isRegistered && styles.profileSectionUnregistered,
        ]}
      >
        <View style={styles.profileSectionTextBlock}>
          <View style={styles.profileHeader}>
            <Text style={styles.profileTitle}>나의 기본 정보 등록하기</Text>
            <Ionicons
              name="chevron-forward"
              size={18}
              color={HOME_COLORS.textDefault}
            />
          </View>

          <Text style={styles.profileDesc}>
            신속한 당국 협조를 위해 필요한 최소한의 정보를 등록해 주세요.
          </Text>
        </View>

        <View
          style={[
            styles.profileStatusBadge,
            isRegistered
              ? styles.profileStatusBadgeRegistered
              : styles.profileStatusBadgeUnregistered,
          ]}
        >
          <Ionicons
            name={isRegistered ? 'checkmark' : 'close'}
            size={18}
            color={isRegistered ? HOME_COLORS.registeredIcon : HOME_COLORS.white}
          />
        </View>
      </TouchableOpacity>
    </View>
  );
}

function normalizeProfileForm(profile) {
  if (!profile) {
    return { ...DEFAULT_PROFILE_FORM };
  }

  return {
    name: profile.name ?? '',
    birthDate: profile.birthDate ?? '',
    phoneNumber: profile.phoneNumber ?? '',
    gender: profile.gender === 'FEMALE' ? 'FEMALE' : 'MALE',
  };
}

function isProfileFormValid(form) {
  return (
    form.name.trim().length > 0 &&
    form.birthDate.trim().length > 0 &&
    form.phoneNumber.trim().length > 0
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
  const [profile, setProfile] = useState(null);
  const [profileForm, setProfileForm] = useState(DEFAULT_PROFILE_FORM);
  const [isProfileModalVisible, setIsProfileModalVisible] = useState(false);
  const [isProfileSaving, setIsProfileSaving] = useState(false);
  const [isProfileWarningDismissed, setIsProfileWarningDismissed] = useState(false);

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

  const handleBasicInfoPress = useCallback(() => {
    setProfileForm(normalizeProfileForm(profile));
    setIsProfileModalVisible(true);
  }, [profile]);

  const handleProfileModalClose = useCallback(() => {
    if (isProfileSaving) {
      return;
    }

    setIsProfileModalVisible(false);
  }, [isProfileSaving]);

  const handleProfileFieldChange = useCallback((field, value) => {
    setProfileForm((currentForm) => ({
      ...currentForm,
      [field]: value,
    }));
  }, []);

  const handleProfileSubmit = useCallback(async () => {
    if (!isProfileFormValid(profileForm)) {
      Alert.alert('입력 확인', '이름, 생년월일, 전화번호를 모두 입력해 주세요.');
      return;
    }

    setIsProfileSaving(true);
    try {
      const savedProfile = await saveCitizenProfile({
        name: profileForm.name.trim(),
        birthDate: profileForm.birthDate.trim(),
        phoneNumber: profileForm.phoneNumber.trim(),
        gender: profileForm.gender,
      });

      setProfile(savedProfile);
      setIsProfileWarningDismissed(false);
      setIsProfileModalVisible(false);
    } catch (error) {
      Alert.alert(
        '저장 실패',
        error.message ?? '기본 정보를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.',
      );
    } finally {
      setIsProfileSaving(false);
    }
  }, [profileForm]);

  const handleFloatingButtonPress = useCallback(() => {
    navigateToRoute(ROUTES.CONSULAR_CALL);
  }, [navigateToRoute]);

  useEffect(() => {
    let isMounted = true;

    async function loadProfile() {
      try {
        const loadedProfile = await getCitizenProfile();

        if (isMounted) {
          setProfile(loadedProfile);
          setProfileForm(normalizeProfileForm(loadedProfile));
        }
      } catch (error) {
        if (isMounted) {
          setProfile(null);
        }
      }
    }

    loadProfile();

    return () => {
      isMounted = false;
    };
  }, []);

  const isProfileRegistered = profile !== null;
  const shouldShowProfileWarning =
    !isProfileRegistered && !isProfileWarningDismissed;

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

        <BasicInfoSection
          isRegistered={isProfileRegistered}
          showWarning={shouldShowProfileWarning}
          onDismissWarning={() => setIsProfileWarningDismissed(true)}
          onPress={handleBasicInfoPress}
        />
      </ScrollView>

      <FloatingButton
        bottomOffset={floatingBottomOffset}
        onPress={handleFloatingButtonPress}
      />

      <BasicInfoModal
        visible={isProfileModalVisible}
        form={profileForm}
        isSaving={isProfileSaving}
        onChangeField={handleProfileFieldChange}
        onClose={handleProfileModalClose}
        onSubmit={handleProfileSubmit}
      />
    </SafeAreaView>
  );
}
