# Chat List API Changes

이 문서는 직원 웹이 PostgreSQL에 저장된 이전 상담 목록을 조회할 수 있도록 backend에 최소 변경으로 추가한 내용을 기록한다.

## 변경 원칙

- 기존 DB schema는 변경하지 않는다.
- 기존 entity는 변경하지 않는다.
- 기존 `ChatSessionResponse`를 재사용한다.
- 기존 `GET /api/chats/{chatId}` 상세 조회 구조를 유지한다.
- 직원 웹 초기 진입 시 사용할 목록 API `GET /api/chats`만 추가한다.

## 추가된 API

```txt
GET /api/chats
```

응답:

```txt
List<ChatSessionResponse>
```

즉 기존 상세 응답과 같은 구조를 배열로 반환한다.

```json
[
  {
    "id": "...",
    "citizenId": "...",
    "countryCode": "JP",
    "status": "OPEN",
    "createdAt": "...",
    "messages": [
      {
        "id": "...",
        "senderType": "CITIZEN",
        "content": "...",
        "createdAt": "..."
      }
    ]
  }
]
```

## 파일별 변경 사항

### `services/main-api/mofa/src/main/java/com/a2d2/mofa/chat/ChatController.java`

기존 코드:

```java
@GetMapping("/{chatId}")
public ChatSessionResponse getChat(@PathVariable String chatId) {
	return chatService.getChat(chatId);
}
```

변경 코드:

```java
@GetMapping
public List<ChatSessionResponse> listChats() {
	return chatService.listChats();
}

@GetMapping("/{chatId}")
public ChatSessionResponse getChat(@PathVariable String chatId) {
	return chatService.getChat(chatId);
}
```

추가 import:

```java
import java.util.List;
```

이유:

- 직원 웹이 처음 켜졌을 때 이미 DB에 저장된 상담 목록을 알 수 있어야 한다.
- 기존에는 `GET /api/chats/{chatId}`만 있어서, web이 이미 알고 있는 `chatId`만 조회할 수 있었다.
- `GET /api/chats`를 추가하면 web이 전체 상담 목록을 먼저 가져오고, 이후 SSE 이벤트로 변경분을 갱신할 수 있다.

### `services/main-api/mofa/src/main/java/com/a2d2/mofa/chat/ChatService.java`

기존 코드:

```java
@Transactional(readOnly = true)
public ChatSessionResponse getChat(String chatId) {
	return toResponse(findChat(chatId));
}
```

변경 코드:

```java
@Transactional(readOnly = true)
public ChatSessionResponse getChat(String chatId) {
	return toResponse(findChat(chatId));
}

@Transactional(readOnly = true)
public List<ChatSessionResponse> listChats() {
	return chatSessionRepository.findAllByOrderByCreatedAtDesc()
			.stream()
			.map(this::toResponse)
			.toList();
}
```

이유:

- 기존 `toResponse(ChatSessionEntity)` 변환 로직을 그대로 재사용한다.
- 별도 DTO를 새로 만들지 않아 backend 변경 범위를 줄인다.
- 최신 생성 상담이 먼저 오도록 `createdAt desc` 정렬을 repository에 위임한다.

### `services/main-api/mofa/src/main/java/com/a2d2/mofa/chat/ChatSessionRepository.java`

기존 코드:

```java
public interface ChatSessionRepository extends JpaRepository<ChatSessionEntity, String> {
}
```

변경 코드:

```java
public interface ChatSessionRepository extends JpaRepository<ChatSessionEntity, String> {

	List<ChatSessionEntity> findAllByOrderByCreatedAtDesc();
}
```

추가 import:

```java
import java.util.List;
```

이유:

- Spring Data JPA method name query를 사용해서 별도 JPQL이나 SQL 없이 목록 조회를 추가한다.
- DB schema와 entity를 바꾸지 않고 목록 정렬만 추가한다.

## 현재 한계

`GET /api/chats`는 각 상담의 `messages[]`까지 함께 반환한다. 현재 로컬 통합 단계에서는 단순하고 유리하지만, 상담 수가 많아지면 응답이 무거워질 수 있다.

추후 운영 단계에서는 다음처럼 가벼운 summary API로 분리하는 것이 좋다.

```txt
GET /api/chats
Response: [
  {
    id,
    citizenId,
    countryCode,
    status,
    createdAt,
    lastMessage,
    lastMessageAt
  }
]
```

하지만 현재 단계에서는 backend 수정 범위를 최소화하기 위해 기존 응답 구조를 재사용한다.
