# Citizen Profile API Changes

## Goal

로그인 없이 모바일 앱의 `citizenId` 기준으로 시민 기본정보를 저장하고 조회한다.

## Added API

### Get Profile

```http
GET /api/citizen-profile
X-Citizen-Id: <citizenId>
```

등록된 기본정보가 있으면 `200 OK`와 프로필을 반환한다. 등록된 정보가 없으면 `404 Not Found`를 반환한다.

### Save Profile

```http
PUT /api/citizen-profile
X-Citizen-Id: <citizenId>
Content-Type: application/json

{
  "name": "홍길동",
  "birthDate": "1990-01-01",
  "phoneNumber": "01012345678",
  "gender": "MALE"
}
```

같은 `citizenId`로 다시 저장하면 기존 프로필을 갱신한다.

## Added Files

- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileEntity.java`
  - `citizen_profiles` 테이블 엔티티다.
- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileRepository.java`
  - `citizenId` 기준 JPA repository다.
- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileRequest.java`
  - 기본정보 저장 요청 body다.
- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileResponse.java`
  - 기본정보 조회/저장 응답 body다.
- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileService.java`
  - 프로필 조회, 생성, 갱신 로직을 담당한다.
- `src/main/java/com/a2d2/mofa/citizen/CitizenProfileController.java`
  - `/api/citizen-profile` HTTP API를 제공한다.
- `src/test/java/com/a2d2/mofa/citizen/CitizenProfilePersistenceTests.java`
  - 프로필 저장 및 갱신 persistence 테스트다.

## Table Shape

```txt
citizen_profiles
- citizen_id
- name
- birth_date
- phone_number
- gender
- created_at
- updated_at
```

## MVP Boundaries

- 이 API는 인증 API가 아니다.
- `citizenId`는 모바일 앱이 `X-Citizen-Id` header로 전달한다.
- 로그인, JWT, refresh token, 본인인증은 이번 범위에 포함하지 않는다.
