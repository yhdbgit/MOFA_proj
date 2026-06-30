# MOFAapp Mobile

민원인용 Expo React Native 앱입니다. 현재 Expo Router가 아닌 React Navigation 하단 탭 구조를 사용합니다.

## 기술 스택

- Expo SDK 56
- React 19
- React Native 0.85
- React Navigation 7
- Expo SecureStore
- `@expo/vector-icons`
- `react-native-safe-area-context`

Expo SDK 56의 패키지 호환성과 설정은 [공식 버전 문서](https://docs.expo.dev/versions/v56.0.0/)를 기준으로 확인합니다.

## 역할

Mobile은 사용자 화면과 입력 상태를 담당합니다. Gemini API 키, 검색 데이터베이스, agent 실행 로직은 포함하지 않습니다.

현재 mobile이 담당하는 주요 기능:

- 홈 화면과 하단 탭 네비게이션
- AI 상담 채팅 UI
- Spring Boot main API에 상담방 생성 및 메시지 전송
- 앱 설치 단위 `citizenId` 발급 및 SecureStore 저장
- 이름, 생년월일, 전화번호, 성별 기본정보 등록
- 등록된 기본정보 여부를 홈 화면에서 표시

## 폴더 구조

```txt
mobile/
├── App.js
├── index.js
├── app.json
├── .env.example
└── src/
    ├── constants/routes.js
    ├── screens/
    │   ├── HomeScreen.jsx
    │   └── ChatScreen.jsx
    ├── services/
    │   ├── consularChatApi.js
    │   ├── citizenProfileApi.js
    │   └── deviceIdentityStore.js
    └── styles/
        ├── appStyles.js
        ├── chatStyles.js
        └── homeStyles.js
```

## Backend 연동 구조

기존 목업 백엔드 연동은 `POST /chat`에 화면의 `messages` 배열을 보내고 `{ reply }`를 받는 방식이었습니다. 현재 mobile은 팀원 backend와 결합되면서 Spring Boot main API 기준으로 동작합니다.

```txt
ChatScreen.jsx
  -> consularChatApi.js
  -> POST /api/chats
  -> POST /api/chats/{chatId}/messages
  -> agentResult.citizenReply 표시
```

첫 메시지를 보내기 전 API layer가 채팅방을 생성하고, 이후 같은 `chatId`로 메시지를 보냅니다. 화면의 `messages` 배열은 UI 렌더링용 상태이고, 실제 대화 이력은 Spring Boot backend가 DB에서 관리합니다.

## 환경변수

`.env.example`:

```env
EXPO_PUBLIC_MOFA_API_BASE_URL=http://127.0.0.1:8080
EXPO_PUBLIC_MOFA_COUNTRY_CODE=JP
```

Android Emulator에서 host Mac의 Spring Boot에 붙을 때는 `.env`를 다음처럼 둡니다.

```env
EXPO_PUBLIC_MOFA_API_BASE_URL=http://10.0.2.2:8080
EXPO_PUBLIC_MOFA_COUNTRY_CODE=JP
```

`EXPO_PUBLIC_` 값은 앱 번들에 포함될 수 있으므로 비밀값을 넣지 않습니다.

## Chat API 계약

### 상담방 생성

```http
POST /api/chats
Content-Type: application/json
```

요청 Body:

```json
{
  "citizenId": "citizen-...",
  "countryCode": "JP"
}
```

응답:

```json
{
  "id": "...",
  "citizenId": "citizen-...",
  "countryCode": "JP",
  "status": "OPEN",
  "createdAt": "...",
  "messages": []
}
```

### 메시지 전송

```http
POST /api/chats/{chatId}/messages
Content-Type: application/json
```

요청 Body:

```json
{
  "senderType": "CITIZEN",
  "content": "도와주세요"
}
```

응답:

```json
{
  "message": {
    "id": "...",
    "senderType": "CITIZEN",
    "content": "도와주세요",
    "createdAt": "..."
  },
  "agentResult": {
    "status": "COMPLETED",
    "citizenReply": "...",
    "severity": "...",
    "recommendedActions": [],
    "officialDocumentDraft": null,
    "ragSources": []
  }
}
```

현재 mobile UI는 `agentResult.citizenReply`만 채팅 말풍선으로 표시합니다. `severity`, `recommendedActions`, `officialDocumentDraft`, `ragSources`는 추후 기능 후보입니다.

## 기본정보 API 계약

상세 흐름은 `BASIC_INFO_REGISTRATION_README.md`에 별도로 유지합니다.

```http
GET /api/citizen-profile
X-Citizen-Id: <citizenId>
```

```http
PUT /api/citizen-profile
X-Citizen-Id: <citizenId>
Content-Type: application/json
```

요청 Body:

```json
{
  "name": "홍길동",
  "birthDate": "1990-01-01",
  "phoneNumber": "01012345678",
  "gender": "MALE"
}
```

## 보류 중인 화면/기능

- 홈 화면의 일부 카드형 기능은 아직 준비 중 알림만 표시합니다.
- 모바일 화면에서는 `severity`, `recommendedActions`, `ragSources`를 아직 표시하지 않습니다.
- 공문 작성 UI는 현재 mobile 범위에 포함하지 않습니다.

## 실행

전체 앱 실행 순서는 루트 `README.md`의 실행 방법을 따릅니다.
