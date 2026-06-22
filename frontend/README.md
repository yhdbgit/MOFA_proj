# MOFAapp Frontend

MOFAapp의 모바일 UI를 담당하는 Expo 기반 React Native 앱입니다. 현재 Expo Router가 아닌 React Navigation의 하단 탭 구조를 사용합니다.

## 기술 스택

- Expo SDK 56
- React 19
- React Native 0.85
- React Navigation 7
- `react-native-safe-area-context`
- `@expo/vector-icons`

Expo SDK 56의 패키지 호환성과 설정은 [공식 버전 문서](https://docs.expo.dev/versions/v56.0.0/)를 기준으로 확인합니다.

## 프론트엔드 책임 범위

프론트엔드는 화면과 사용자 입력 상태를 관리하고, AI 상담 요청을 백엔드의 `POST /chat` API로 전달합니다. Gemini API 키, 검색 데이터베이스, 답변 생성 로직은 앱에 포함하지 않고 백엔드가 담당합니다.

```text
HomeScreen.jsx
  -> initialMessage 화면 파라미터
ChatScreen.jsx
  -> messages 배열 구성
src/services/consularChatApi.js
  -> POST /chat
Backend
  -> { reply }
ChatScreen.jsx
  -> reply를 상담 메시지로 표시
```

## 폴더 구조

```text
frontend/
├── App.js                         앱 루트와 하단 탭 네비게이션
├── index.js                       Expo 앱 진입점
├── app.json                       앱 이름, 아이콘, 플랫폼 설정
├── .env.example                   채팅 API 주소 예시
└── src/
    ├── constants/routes.js        화면 이름 상수
    ├── screens/HomeScreen.jsx     홈 화면과 기능 진입점
    ├── screens/ChatScreen.jsx     AI 상담 UI와 메시지 상태
    ├── services/consularChatApi.js 채팅 API 통신
    └── styles/                    화면별 React Native 스타일
```

## 현재 구현 상태

| 기능 | 상태 | 관련 파일 |
| --- | --- | --- |
| 홈 화면 | 구현됨 | `src/screens/HomeScreen.jsx` |
| 하단 탭 이동 | 구현됨 | `App.js` |
| AI 상담 채팅 | 구현됨 | `src/screens/ChatScreen.jsx` |
| `POST /chat` 연동 | 구현됨 | `src/services/consularChatApi.js` |
| 영사안전콜센터 | 임시 화면 | `App.js` |
| 재외공관 연락처 | 임시 화면 | `App.js` |
| 내 위치 안전정보 | 임시 화면 | `App.js` |
| 일정, 알림, 설정, 여행경보, 여행일정 등록 | 준비 중 알림 | `src/screens/HomeScreen.jsx` |

## 실행 방법

의존성을 설치합니다.

```bash
npm install
```

필요하면 환경변수 파일을 만듭니다. 환경변수를 만들지 않으면 기본 주소인 `http://127.0.0.1:8787/chat`을 사용합니다.

```bash
cp .env.example .env
```

```env
EXPO_PUBLIC_CONSULAR_CHAT_API_URL=http://127.0.0.1:8787/chat
```

앱을 실행합니다.

```bash
npm start
npm run ios
npm run android
```

실제 휴대폰에서는 `127.0.0.1`이 휴대폰 자신을 가리킵니다. Expo Go로 테스트할 때는 환경변수의 호스트를 백엔드가 실행 중인 개발 PC의 로컬 IP로 바꾸고, 백엔드도 휴대폰에서 접근 가능한 주소로 실행해야 합니다.

## Chat API 계약

### 요청

```http
POST /chat
Content-Type: application/json
```

```json
{
  "messages": [
    {
      "id": "welcome",
      "role": "assistant",
      "text": "안녕하세요. AI 영사콜센터 상담사입니다."
    },
    {
      "id": "user-...",
      "role": "user",
      "text": "여권을 잃어버렸어요"
    }
  ]
}
```

- `role`: `user` 또는 `assistant`
- `text`: 비어 있지 않은 메시지 본문
- `id`: 화면의 목록 렌더링을 위한 프론트엔드 식별자입니다. 백엔드는 답변 생성에 사용하지 않으며 알 수 없는 추가 필드로 무시할 수 있어야 합니다.
- 프론트엔드는 현재 화면에 쌓인 대화 내역과 고정 환영 메시지를 함께 전송합니다. 사용할 대화 범위를 선택하거나 제한하는 것은 백엔드 책임입니다.
- 현재 `backend`는 마지막 12개 메시지만 AI 답변 생성에 사용합니다.

### 성공 응답

```json
{
  "reply": "가까운 경찰서에서 분실 신고를 먼저 진행해 주세요."
}
```

- `reply`: 프론트엔드가 필수로 사용하는 비어 있지 않은 문자열입니다.

백엔드 구현 언어나 내부 구조가 바뀌어도 위 요청과 `reply` 응답 형식이 유지되면 프론트엔드는 API 주소만 변경하여 연결할 수 있습니다.

### 실패 응답과 제한 시간

프론트엔드는 다음 오류 형식을 사용자 메시지로 변환합니다.

```json
{ "detail": "오류 내용" }
```

```json
{ "error": "오류 내용" }
```

요청 후 120초가 지나면 프론트엔드가 요청을 취소합니다. 이 값은 백엔드 내부 타임아웃이 아니라 프론트엔드의 대기 정책입니다.

## 주석 규칙

- `API CONTRACT`: 백엔드와 합의가 필요한 요청·응답 조건
- `TODO(frontend)`: 아직 연결되지 않은 프론트엔드 기능
- `NOTE`: 코드만 읽어서는 드러나지 않는 설계 이유

컴포넌트가 무엇을 화면에 그리는지 반복해서 설명하지 않고, 데이터 흐름·외부 계약·플랫폼별 처리처럼 변경 시 주의가 필요한 부분만 주석으로 남깁니다.
