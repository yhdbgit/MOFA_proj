/** 홈 화면 전용 색상 토큰과 레이아웃 스타일이다. */
import { StyleSheet } from 'react-native';

export const HOME_COLORS = {
  primary: '#00B4C8',
  white: '#FFFFFF',
  black: '#111111',
  textDark: '#222222',
  textDefault: '#333333',
  textSub: '#555555',
  textMuted: '#666666',
  placeholder: '#AAAAAA',
  cardBg: '#F0F4F8',
  logoBg: '#F0F0F0',
  inputBorder: '#222222',
};

const homeStyles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: HOME_COLORS.white,
  },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    minHeight: 64,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: HOME_COLORS.white,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flexShrink: 1,
  },
  logoCircle: {
    width: 40,
    height: 40,
    marginRight: 10,
    borderRadius: 20,
    backgroundColor: HOME_COLORS.logoBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  logoText: {
    fontSize: 20,
  },
  headerTitle: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '700',
    color: HOME_COLORS.textDark,
  },
  headerSubtitle: {
    fontSize: 12,
    lineHeight: 16,
    color: HOME_COLORS.textSub,
  },
  headerIcons: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
  },
  iconBtn: {
    width: 34,
    height: 34,
    marginLeft: 2,
    justifyContent: 'center',
    alignItems: 'center',
  },

  scrollView: {
    flex: 1,
    backgroundColor: HOME_COLORS.white,
  },
  scrollContent: {
    paddingBottom: 20,
  },

  hero: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
  },
  heroContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  heroTextBlock: {
    flex: 1,
  },
  heroText: {
    marginBottom: 4,
    fontSize: 16,
    color: HOME_COLORS.textDefault,
  },
  heroBold: {
    fontSize: 20,
    lineHeight: 28,
    fontWeight: '800',
    color: HOME_COLORS.black,
  },
  heroBalloon: {
    width: 90,
    height: 90,
    marginLeft: 12,
    borderRadius: 45,
    backgroundColor: HOME_COLORS.cardBg,
    justifyContent: 'center',
    alignItems: 'center',
  },
  balloonEmoji: {
    fontSize: 50,
  },

  chatInputWrapper: {
    paddingHorizontal: 20,
    marginBottom: 18,
  },
  chatInputBox: {
    minHeight: 50,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 16,
    paddingRight: 6,
    borderWidth: 1.5,
    borderColor: HOME_COLORS.inputBorder,
    borderRadius: 25,
    backgroundColor: HOME_COLORS.white,
  },
  chatInputIcon: {
    marginRight: 8,
  },
  chatTextInput: {
    flex: 1,
    paddingVertical: 0,
    fontSize: 14,
    color: HOME_COLORS.textDefault,
  },
  clearInputButton: {
    marginLeft: 8,
  },
  chatSubmitButton: {
    width: 38,
    height: 38,
    marginLeft: 8,
    borderRadius: 19,
    backgroundColor: HOME_COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
  },

  cardsSection: {
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  cardLarge: {
    minHeight: 120,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    padding: 20,
    borderRadius: 16,
    backgroundColor: HOME_COLORS.cardBg,
  },
  cardTextBlock: {
    flex: 1,
  },
  cardTitle: {
    marginBottom: 6,
    fontSize: 16,
    fontWeight: '700',
    color: HOME_COLORS.black,
  },
  cardDesc: {
    fontSize: 13,
    lineHeight: 19,
    color: HOME_COLORS.textSub,
  },
  cardIconWrap: {
    marginLeft: 12,
  },
  cardIconBg: {
    width: 70,
    height: 70,
    borderRadius: 35,
    backgroundColor: HOME_COLORS.white,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardIconEmoji: {
    fontSize: 36,
  },
  cardRow: {
    flexDirection: 'row',
  },
  cardSmall: {
    flex: 1,
    minHeight: 110,
    padding: 18,
    borderRadius: 16,
    backgroundColor: HOME_COLORS.cardBg,
    justifyContent: 'space-between',
  },
  cardSmallSpacing: {
    marginRight: 10,
  },
  cardSmallTitle: {
    fontSize: 14,
    lineHeight: 20,
    fontWeight: '700',
    color: HOME_COLORS.black,
  },
  cardSmallEmoji: {
    marginTop: 8,
    fontSize: 36,
    alignSelf: 'flex-end',
  },

  tripSection: {
    paddingHorizontal: 20,
    paddingVertical: 16,
  },
  tripHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  tripTitle: {
    marginRight: 4,
    fontSize: 16,
    fontWeight: '700',
    color: HOME_COLORS.black,
  },
  tripDesc: {
    fontSize: 13,
    lineHeight: 20,
    color: HOME_COLORS.textMuted,
  },

  floatingBtn: {
    // bottom 위치는 기기 safe area와 커스텀 탭바 높이를 반영해 HomeScreen에서 계산한다.
    position: 'absolute',
    right: 16,
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: HOME_COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.25)',
  },
  floatingBtnText: {
    fontSize: 11,
    lineHeight: 15,
    fontWeight: '700',
    color: HOME_COLORS.white,
    textAlign: 'center',
  },
});

export default homeStyles;
