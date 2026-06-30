# Mobile Basic Info Registration Changes

## Goal

회원가입/로그인 없이 앱 설치 단위의 `citizenId`를 발급하고, 홈 화면에서 최소 기본 정보를 바로 등록할 수 있게 한다.

## Added Flow

```txt
앱에서 기본 정보 필요
-> SecureStore에서 citizenId 조회
-> 없으면 citizenId 생성 후 SecureStore 저장
-> GET /api/citizen-profile 로 등록 여부 확인
-> 미등록이면 홈 화면 기본정보 영역을 옅은 빨간색으로 표시
-> 사용자가 "나의 기본 정보 등록하기"를 누름
-> 홈 화면 modal에서 이름, 생년월일, 전화번호, 성별 입력
-> PUT /api/citizen-profile 로 저장
-> 저장 후 홈 화면에 등록 완료 체크 표시
```

## Changed Files

- `package.json`, `package-lock.json`
  - Expo SDK 56 호환 `expo-secure-store`를 추가했다.
- `app.json`
  - `expo-secure-store` config plugin이 추가됐다.
- `src/services/deviceIdentityStore.js`
  - SecureStore 기반 `getOrCreateCitizenId()`를 추가했다.
- `src/services/citizenProfileApi.js`
  - `GET /api/citizen-profile`, `PUT /api/citizen-profile` 호출을 추가했다.
  - `X-Citizen-Id` header에 SecureStore의 `citizenId`를 실어 보낸다.
- `src/services/consularChatApi.js`
  - 기존 고정 `citizen-mobile-demo` 대신 SecureStore의 `citizenId`로 채팅방을 생성한다.
- `src/screens/HomeScreen.jsx`
  - 기존 여행일정 등록 영역을 기본정보 등록 영역으로 변경했다.
  - 등록 modal, 미등록 경고 말풍선, 등록/미등록 상태 표시, 성별 슬라이드 선택 UI를 추가했다.
- `src/styles/homeStyles.js`
  - 기본정보 영역, modal, 입력 필드, 성별 segmented control 스타일을 분리해 추가했다.
- `.env.example`
  - 더 이상 사용하지 않는 `EXPO_PUBLIC_MOFA_CITIZEN_ID` 예시를 제거했다.

## Profile Payload

```json
{
  "name": "홍길동",
  "birthDate": "1990-01-01",
  "phoneNumber": "01012345678",
  "gender": "MALE"
}
```

`gender` 값은 `MALE` 또는 `FEMALE`이다. UI 초기값은 `MALE`이다.

## MVP Boundaries

- 로그인, JWT, refresh token, 생체 인증은 추가하지 않는다.
- 개인정보 원문은 SecureStore에 저장하지 않는다.
- SecureStore에는 `citizenId`만 저장한다.
- 기본정보 등록 화면은 별도 페이지가 아니라 홈 화면 modal이다.
