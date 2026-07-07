package com.a2d2.mofa.document;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface OfficialDocumentRepository extends JpaRepository<OfficialDocumentEntity, String> {

	List<OfficialDocumentEntity> findByChatSessionIdOrderByCreatedAtDesc(String chatSessionId);

	boolean existsByChatSessionId(String chatSessionId);
}
