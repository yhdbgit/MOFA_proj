/** 앱 루트와 커스텀 하단 탭에서 공통으로 사용하는 디자인 값과 스타일이다. */
import { StyleSheet } from 'react-native';

export const APP_COLORS = {
  primary: '#00B4C8',
  white: '#FFFFFF',
  border: '#E8E8E8',
  textMuted: '#999999',
  centerInactive: '#BFC8CC',
};

// 탭바의 기본 콘텐츠 높이와 기기 하단에 보장할 최소 여백이다.
export const TAB_BAR_BASE_HEIGHT = 64;
export const TAB_BAR_MIN_BOTTOM_PADDING = 12;

const appStyles = StyleSheet.create({
  emptyScreen: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: APP_COLORS.white,
  },
  emptyText: {
    fontSize: 18,
    color: APP_COLORS.textMuted,
  },

  tabBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingTop: 8,
    backgroundColor: APP_COLORS.white,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: APP_COLORS.border,
  },
  tabItem: {
    flex: 1,
    minWidth: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tabLabel: {
    marginTop: 3,
    fontSize: 10,
    lineHeight: 13,
    color: APP_COLORS.textMuted,
    textAlign: 'center',
  },
  tabLabelActive: {
    color: APP_COLORS.primary,
    fontWeight: '600',
  },

  centerTabWrapper: {
    flex: 1,
    minWidth: 0,
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  centerTab: {
    width: 56,
    height: 56,
    marginBottom: 2,
    borderRadius: 28,
    backgroundColor: APP_COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: '0 4px 8px rgba(0, 180, 200, 0.35)',
  },
  centerTabInactive: {
    backgroundColor: APP_COLORS.centerInactive,
    boxShadow: '0 4px 8px rgba(0, 180, 200, 0.12)',
  },
  centerTabLabel: {
    fontSize: 10,
    lineHeight: 13,
    color: APP_COLORS.primary,
    fontWeight: '700',
    textAlign: 'center',
  },
  centerTabLabelInactive: {
    color: APP_COLORS.textMuted,
    fontWeight: '500',
  },
});

export default appStyles;
