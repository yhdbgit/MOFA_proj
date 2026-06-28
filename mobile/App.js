/**
 - 앱 전체의 Provider와 하단 탭 네비게이션을 구성하는 루트 컴포넌트다.
 - 실제 기능 화면과 준비 중인 임시 화면을 같은 탭 구조 안에서 연결한다.
 */
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import {
  View,
  Text,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';

import HomeScreen from './src/screens/HomeScreen';
import ChatScreen from './src/screens/ChatScreen';
import ROUTES from './src/constants/routes';
import styles, {
  APP_COLORS,
  TAB_BAR_BASE_HEIGHT,
  TAB_BAR_MIN_BOTTOM_PADDING,
} from './src/styles/appStyles';

const Tab = createBottomTabNavigator();

// 라우트 이름과 탭에 표시할 텍스트/아이콘을 분리해 탭 UI를 한곳에서 관리한다.
const TAB_CONFIG = {
  [ROUTES.CONSULAR_CALL]: {
    label: '영사안전\n콜센터',
    icon: 'headset-outline',
  },
  [ROUTES.EMBASSY_CONTACTS]: {
    label: '재외공관\n연락처',
    icon: 'phone-portrait-outline',
  },
  [ROUTES.HOME]: {
    label: '홈',
    icon: 'home',
    isCenter: true,
  },
  [ROUTES.LOCATION_SAFETY]: {
    label: '내 위치\n안전정보',
    icon: 'radio-button-on-outline',
  },
  [ROUTES.AI_CHAT]: {
    label: 'AI\n상담사',
    icon: 'chatbubble-ellipses-outline',
  },
};

// 아래 임시 화면은 각 기능이 구현되면 실제 Screen으로 교체한다.
function EmptyScreen({ title }) {
  return (
    <View style={styles.emptyScreen}>
      <Text style={styles.emptyText}>{title}</Text>
    </View>
  );
}

function ConsularCallScreen() {
  return <EmptyScreen title="영사안전콜센터" />;
}

function EmbassyContactsScreen() {
  return <EmptyScreen title="재외공관연락처" />;
}

function LocationSafetyScreen() {
  return <EmptyScreen title="내 위치 안전정보" />;
}

/**
 - React Navigation의 현재 route 상태를 사용해 프로젝트 전용 하단 탭 UI를 그린다.
 - 중앙 홈 버튼만 강조하고, 기기의 하단 안전 영역만큼 탭바 높이를 늘린다.
 */
function CustomTabBar({ state, descriptors, navigation }) {
  const insets = useSafeAreaInsets();

  // 홈 인디케이터가 없는 기기에서도 최소 여백을 유지한다.
  const bottomPadding = Math.max(insets.bottom, TAB_BAR_MIN_BOTTOM_PADDING);

  return (
    <View
      style={[
        styles.tabBar,
        {
          height: TAB_BAR_BASE_HEIGHT + bottomPadding,
          paddingBottom: bottomPadding,
        },
      ]}
    >
      {state.routes.map((route, index) => {
        const tab = TAB_CONFIG[route.name];

        if (!tab) {
          return null;
        }

        const isFocused = state.index === index;
        const options = descriptors[route.key]?.options ?? {};

        const onPress = () => {
          // 기본 tabPress 이벤트를 먼저 보내 다른 리스너가 이동을 막을 수 있게 한다.
          const event = navigation.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });

          if (!isFocused && !event.defaultPrevented) {
            navigation.navigate(route.name);
          }
        };

        const onLongPress = () => {
          navigation.emit({
            type: 'tabLongPress',
            target: route.key,
          });
        };

        const accessibilityLabel =
          options.tabBarAccessibilityLabel ?? `${tab.label.replace(/\n/g, ' ')} 탭`;

        if (tab.isCenter) {
          return (
            <TouchableOpacity
              key={route.key}
              activeOpacity={0.85}
              accessibilityRole="button"
              accessibilityState={isFocused ? { selected: true } : {}}
              accessibilityLabel={accessibilityLabel}
              testID={options.tabBarButtonTestID}
              onPress={onPress}
              onLongPress={onLongPress}
              style={styles.centerTabWrapper}
            >
              <View
                style={[
                  styles.centerTab,
                  !isFocused && styles.centerTabInactive,
                ]}
              >
                <Ionicons name={tab.icon} size={26} color={APP_COLORS.white} />
              </View>

              <Text
                style={[
                  styles.centerTabLabel,
                  !isFocused && styles.centerTabLabelInactive,
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          );
        }

        return (
          <TouchableOpacity
            key={route.key}
            activeOpacity={0.75}
            accessibilityRole="button"
            accessibilityState={isFocused ? { selected: true } : {}}
            accessibilityLabel={accessibilityLabel}
            testID={options.tabBarButtonTestID}
            onPress={onPress}
            onLongPress={onLongPress}
            style={styles.tabItem}
          >
            <Ionicons
              name={tab.icon}
              size={22}
              color={isFocused ? APP_COLORS.primary : APP_COLORS.textMuted}
            />

            <Text
              style={[
                styles.tabLabel,
                isFocused && styles.tabLabelActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

export default function App() {
  return (
    // SafeAreaProvider는 하위 화면과 커스텀 탭바에 기기별 inset 정보를 제공한다.
    <SafeAreaProvider>
      <NavigationContainer>
        <Tab.Navigator
          initialRouteName={ROUTES.HOME}
          tabBar={(props) => <CustomTabBar {...props} />}
          screenOptions={{
            headerShown: false,
            lazy: true,
          }}
        >
          <Tab.Screen
            name={ROUTES.CONSULAR_CALL}
            component={ConsularCallScreen}
          />

          <Tab.Screen
            name={ROUTES.EMBASSY_CONTACTS}
            component={EmbassyContactsScreen}
          />

          <Tab.Screen
            name={ROUTES.HOME}
            component={HomeScreen}
          />

          <Tab.Screen
            name={ROUTES.LOCATION_SAFETY}
            component={LocationSafetyScreen}
          />

          <Tab.Screen
            name={ROUTES.AI_CHAT}
            component={ChatScreen}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
