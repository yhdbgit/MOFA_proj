/**
 - React Navigation에서 사용하는 화면 식별자를 한곳에서 관리한다.
 - 값을 변경하면 App.js의 TAB_CONFIG와 각 navigation.navigate 호출에 함께 영향을 준다.
 */
const ROUTES = {
  CONSULAR_CALL: '영사안전콜센터',
  EMBASSY_CONTACTS: '재외공관연락처',
  HOME: '홈',
  LOCATION_SAFETY: '내위치안전정보',
  AI_CHAT: '상담접수',
};

export default ROUTES;
