# Web Basic Info Header Changes

## Goal

상담 상세 화면 상단에서 민원인의 기본정보 등록 여부를 바로 확인하고, 담당자가 `citizenId`를 빠르게 복사할 수 있게 한다.

## Changed Flow

```txt
상담 상세 선택
-> chat.citizenId 확인
-> GET /api/citizen-profile 호출
-> 기본정보가 있으면 "신원 확인" 표시
-> 기본정보가 없으면 "신원 미상" 표시
-> "신원 확인" 클릭 시 이름/나이/성별/생년월일/전화번호를 확장 표시
-> citizenId 앞 8자리 표시 및 전체 citizenId 복사 지원
```

## Changed Files

- `chatMonitorApi.js`
  - `fetchCitizenProfile(citizenId)`를 추가했다.
  - `GET /api/citizen-profile` 요청 시 `X-Citizen-Id` header로 `citizenId`를 전달한다.
  - `404 Not Found`는 등록된 기본정보가 없는 상태로 보고 `null`을 반환한다.

- `app.js`
  - 선택된 상담의 `citizenId`로 기본정보를 조회한다.
  - `citizenId`별 profile cache를 추가했다.
  - 상담 제목 아래 메타 정보를 `신원 상태`, `citizenId chip`, `국가 코드`, `상태` 순서로 표시한다.
  - 복사 버튼은 별도 token이 아니라 `citizenId chip` 내부 오른쪽에 배치한다.
  - `신원 확인` badge를 클릭하면 기본정보가 확장되고, 다시 클릭하면 축소된다.
  - 복사 버튼 클릭 시 전체 `citizenId`를 클립보드에 복사하고, 복사 아이콘을 1초 동안 check 표시로 바꾼다.

- `styles.css`
  - 신원 상태 badge, `citizenId` chip, 복사 버튼, 국가/상태 token 스타일을 추가했다.

## Backend Contract Used

```http
GET /api/citizen-profile
X-Citizen-Id: <citizenId>
```