package com.a2d2.mofa.chat;

import com.a2d2.mofa.agent.AgentAnalysisResult;

public record ChatMessageProcessingResponse(
		ChatMessageResponse message,
		AgentAnalysisResult agentResult
) {
}
