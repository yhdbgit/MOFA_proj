import { buildAiAgentUrl } from "./config.js";

const REALTIME_MODEL = "gpt-realtime-whisper";
const TARGET_SAMPLE_RATE = 24000;
const MIC_COMMIT_INTERVAL_MS = 2800;
const FINAL_TRANSCRIPT_WAIT_MS = 1800;

const recommendationCatalog = [
  {
    id: "passport-emergency",
    type: "manual",
    title: "여권 분실 시 긴급여권·여행증명서 안내",
    source: "영사업무처리지침 / 여권 관련 민원",
    revision: "2026.05",
    score: 94,
    keywords: ["여권", "분실", "귀국", "긴급여권", "여행증명서"],
    summary:
      "귀국 일정이 임박한 여권 분실 민원은 신원 확인, 분실 신고 여부, 항공권 보유 여부를 우선 확인합니다.",
    detail:
      "민원인이 여권을 분실했고 단기간 내 귀국해야 하는 경우 관할 공관 방문 가능 여부, 신분 확인 자료, 항공권, 현지 경찰 신고 가능 여부를 순서대로 확인합니다. 긴급여권 또는 여행증명서 발급 가능성은 공관별 운영 시간과 현지 사정에 따라 달라질 수 있습니다.",
    answer:
      "우선 현재 위치와 안전 여부를 확인하고, 가능한 경우 현지 경찰 분실 신고 후 관할 공관에 방문하도록 안내하세요.",
  },
  {
    id: "police-report",
    type: "manual",
    title: "현지 경찰 신고 및 사건 접수 확인",
    source: "위기상황별 대처매뉴얼 / 도난·분실",
    revision: "2026.04",
    score: 88,
    keywords: ["경찰", "신고", "도난", "분실", "지갑"],
    summary:
      "분실·도난 피해는 현지 경찰 신고 접수 여부와 접수번호 확보 가능성을 확인합니다.",
    detail:
      "여권, 지갑, 휴대품 분실이나 도난 상담에서는 경찰 신고서 또는 접수번호 확보 가능 여부를 확인합니다. 현지 신고가 어려운 경우에는 경위서 작성 가능성과 공관 확인 절차를 함께 안내합니다.",
    answer:
      "가능하면 가까운 경찰서에서 분실 또는 도난 신고를 진행하고, 접수번호나 신고서를 보관하도록 안내하세요.",
  },
  {
    id: "wallet-card-loss",
    type: "manual",
    title: "해외 지갑 도난 시 카드 정지 및 피해 신고 절차",
    source: "위기상황별 대처매뉴얼 / 도난·분실",
    revision: "2026.04",
    score: 91,
    keywords: ["지갑", "도난", "신용카드", "카드", "현금", "운전면허증"],
    summary:
      "지갑 도난 상담은 신변 안전, 여권 보관 여부, 카드사 분실 정지, 현지 경찰 신고를 우선 처리합니다.",
    detail:
      "민원인이 해외에서 지갑을 도난당한 경우 추가 피해 방지를 위해 카드사 분실 정지를 먼저 안내합니다. 현금, 운전면허증, 보험 관련 물품이 포함된 경우 현지 경찰 신고서나 접수번호 확보가 추후 피해 확인과 보험 청구에 도움이 될 수 있습니다.",
    answer:
      "현재 안전한 장소에 있는지 확인한 뒤 카드사 분실 정지를 우선 안내하고, 현지 경찰서에서 도난 신고 접수번호를 확보하도록 설명하세요.",
  },
  {
    id: "consular-help-law",
    type: "legal",
    title: "재외국민보호를 위한 영사조력의 범위",
    source: "영사조력법 / 일반 조력",
    revision: "2026.03",
    score: 84,
    keywords: ["영사", "조력", "대사관", "공관", "안전", "보호", "도난", "분실", "사고", "체포", "구금"],
    summary:
      "공관은 재외국민의 생명·신체·재산 보호를 위해 필요한 범위에서 영사조력을 제공합니다.",
    detail:
      "영사조력은 현지 법령과 국제법, 주재국 관할권 범위 안에서 제공됩니다. 상담관은 민원인의 안전, 위치, 연락 가능성, 현지 기관 접수 여부를 확인한 뒤 공관 또는 관계기관 연계를 검토합니다.",
    answer:
      "공관 조력은 현지 법령 범위 안에서 가능하므로, 사실관계와 긴급성을 먼저 확인한 뒤 관할 공관으로 연결하세요.",
  },
  {
    id: "consular-work-guideline",
    type: "legal",
    title: "영사업무처리지침상 민원 처리 기준",
    source: "영사업무처리지침 / 민원 처리 기준",
    revision: "2026.05",
    score: 86,
    keywords: ["여권", "긴급여권", "여행증명서", "발급", "신고", "접수", "공관", "민원"],
    summary:
      "여권, 여행증명서, 신고 접수처럼 공관 절차가 필요한 상담은 업무처리지침상 확인 순서를 우선 적용합니다.",
    detail:
      "영사업무처리지침은 상담원이 사실관계 확인, 필요 서류, 관할 공관 방문 가능 여부, 접수 절차를 안내할 때 기준으로 삼는 절차성 근거입니다. 민원인이 실제 발급이나 신고 처리를 요청하는 경우에는 법률 조항보다 구체적인 업무처리 기준을 함께 확인해야 합니다.",
    answer:
      "민원인의 신원, 현재 위치, 필요 서류 보유 여부, 관할 공관 방문 가능 시간을 확인한 뒤 업무처리지침 기준으로 접수 가능성을 안내하세요.",
  },
  {
    id: "mexico-office",
    type: "country",
    title: "멕시코 지역 공관 연결 및 위치 확인",
    source: "국가·지역별 정보 / 멕시코",
    revision: "2026.06",
    score: 82,
    keywords: ["멕시코", "멕시코시티", "대사관", "호텔"],
    summary:
      "멕시코 체류 민원은 도시, 연락처, 이동 가능 여부를 확인하고 관할 공관 안내를 검토합니다.",
    detail:
      "멕시코 지역 상담에서는 민원인의 현재 도시, 숙소 또는 대기 장소, 연락 가능한 전화번호, 공관 방문 가능 시간을 확인합니다. 야간이나 휴일이면 긴급 연락 체계로 전환할 필요가 있는지 판단합니다.",
    answer:
      "현재 도시와 숙소 주소, 연락처를 확인하고 멕시코 지역 관할 공관 방문 가능 시간을 안내하세요.",
  },
  {
    id: "ghana-country",
    type: "country",
    title: "가나 국가 안전·공관 정보",
    source: "국가·지역별 정보 / 가나",
    revision: "2026.06",
    score: 82,
    keywords: ["가나", "아크라", "쿠마시", "타말레"],
    summary:
      "가나 체류 민원은 현재 위치, 이동 가능 여부, 현지 기관 접수 여부, 공관 연결 필요성을 확인합니다.",
    detail:
      "가나 관련 상담에서는 민원인의 현재 도시와 안전 여부, 연락 가능한 번호, 현지 경찰 또는 의료기관 이용 가능성, 관할 공관 연결 필요성을 우선 확인합니다. 야간이나 이동이 어려운 상황이면 긴급 연락 체계로 전환할 필요가 있는지 판단합니다.",
    answer:
      "현재 위치와 안전 여부를 확인하고, 현지 기관 신고 또는 치료가 필요한지 판단한 뒤 관할 공관 연결을 검토하세요.",
  },
  {
    id: "nepal-country",
    type: "country",
    title: "네팔 국가 안전·공관 정보",
    source: "국가·지역별 정보 / 네팔",
    revision: "2026.06",
    score: 82,
    keywords: ["네팔", "카트만두", "포카라", "랄릿푸르", "박타푸르"],
    summary:
      "네팔 체류 민원은 현재 도시와 이동 가능 여부, 현지 기관 접수 여부, 공관 연결 필요성을 확인합니다.",
    detail:
      "네팔 관련 상담에서는 민원인의 현재 도시, 숙소 또는 대기 장소, 연락 가능한 전화번호, 현지 경찰 또는 의료기관 이용 가능성, 관할 공관 연결 필요성을 우선 확인합니다. 산악 지역 이동 중 사고나 연락 두절 가능성이 있으면 위치와 동행자 여부를 함께 확인합니다.",
    answer:
      "현재 네팔 내 도시와 안전 여부를 확인하고, 현지 기관 신고 또는 치료가 필요한지 판단한 뒤 관할 공관 연결을 검토하세요.",
  },
  {
    id: "detention-manual",
    type: "manual",
    title: "부당한 체포 및 구금 시 초기 대응",
    source: "위기상황별 대처매뉴얼 / 부당한 체포 및 구금",
    revision: "2026.05",
    score: 90,
    keywords: ["체포", "구금", "사법당국", "통역", "면담", "서명", "변호사", "가혹행위"],
    summary:
      "체포·구금 상담은 현지 절차 준수, 공관 통보 요청, 통역 지원 가능 여부, 서명 주의 여부를 우선 확인합니다.",
    detail:
      "민원인이 해외에서 체포 또는 구금된 경우 당황하지 말고 현지 사법당국 절차에 따르도록 안내합니다. 우리 공관에 구금 사실을 알리도록 요청했는지, 통역 지원이 가능한지, 이해하지 못하는 외국어 문서에 서명하지 않았는지, 영사 면담이나 가족 연락 협조가 필요한지 확인합니다. 부당한 대우나 가혹 행위가 있었다면 영사 면담 시 관련 사실을 알리도록 안내합니다.",
    answer:
      "현지 사법당국 절차에 따르되, 공관 통보 요청 여부와 통역 필요 여부를 확인하고 이해하지 못하는 문서에는 함부로 서명하지 않도록 안내하세요.",
  },
  {
    id: "detention",
    type: "legal",
    title: "체포·구금 통보 및 접견 관련 조력",
    source: "영사조력법 / 체포·구금",
    revision: "2026.02",
    score: 78,
    keywords: ["체포", "구금", "경찰서", "detained", "arrest"],
    summary:
      "체포·구금 상담은 장소, 적용 혐의, 접견 가능 여부, 가족 연락 필요성을 우선 확인합니다.",
    detail:
      "체포 또는 구금 정황이 있으면 민원인의 위치, 구금 기관, 현지 담당자, 통역 필요 여부, 가족 통보 희망 여부를 확인합니다. 공관은 현지 절차에 개입할 수 없지만 적법 절차와 기본권 보호를 위한 영사조력을 검토할 수 있습니다.",
    answer:
      "구금 장소와 담당기관을 확인하고, 본인 또는 가족의 공관 통보 희망 여부를 기록하세요.",
  },
  {
    id: "medical",
    type: "manual",
    title: "사고·부상 발생 시 의료기관 및 보호자 확인",
    source: "위기상황별 대처매뉴얼 / 사건사고",
    revision: "2026.05",
    score: 75,
    keywords: ["사고", "부상", "병원", "응급", "치료"],
    summary:
      "부상 상담은 생명·신체 위험, 병원 이송 여부, 보호자 연락 필요성을 먼저 확인합니다.",
    detail:
      "사고나 응급 상황에서는 현재 안전 여부와 치료 가능성을 우선 확인합니다. 필요한 경우 현지 응급번호, 의료기관, 보험사, 보호자 연락, 공관 연계를 단계적으로 검토합니다.",
    answer:
      "현재 의식과 부상 정도를 확인하고 응급 상황이면 현지 응급번호 또는 가까운 의료기관 이용을 먼저 안내하세요.",
  },
];

const checklistByIncident = {
  PASSPORT_LOSS: [
    "현재 위치와 안전 여부 확인",
    "귀국 일정과 항공권 보유 여부 확인",
    "여권 사본 또는 신분 확인 자료 보유 여부 확인",
    "현지 경찰 신고 가능 여부 확인",
    "관할 공관 방문 가능 시간 확인",
  ],
  DETENTION: [
    "구금 장소와 담당기관 확인",
    "적용 혐의 또는 조사 사유 확인",
    "통역 필요 여부 확인",
    "가족 통보 희망 여부 확인",
    "관할 공관 연결 필요성 판단",
  ],
  MEDICAL: [
    "의식과 부상 정도 확인",
    "현재 위치와 동행자 여부 확인",
    "현지 응급번호 또는 의료기관 이용 여부 확인",
    "보험사와 보호자 연락 필요성 확인",
    "공관 후속 조력 필요성 판단",
  ],
  THEFT: [
    "현재 안전한 장소에 있는지 확인",
    "여권 분실 여부와 보관 상태 확인",
    "신용카드 정지 여부 확인",
    "현지 경찰 도난 신고 가능 여부 확인",
    "보험 청구 또는 피해 사실 확인용 접수번호 확보 안내",
  ],
  DEFAULT: [
    "민원인 성명과 연락처 확인",
    "현재 국가와 도시 확인",
    "신변 안전 여부 확인",
    "현지 기관 접수 여부 확인",
    "관할 공관 연결 필요성 판단",
  ],
};

const CRISIS_KEYWORDS = [
  "여권",
  "분실",
  "잃어",
  "도난",
  "지갑",
  "카드",
  "현금",
  "소매치기",
  "체포",
  "구금",
  "경찰",
  "신고",
  "사고",
  "부상",
  "병원",
  "응급",
  "치료",
  "폭행",
  "납치",
  "사망",
  "재난",
  "위험",
];

const LEGAL_TRIGGER_KEYWORDS = [
  "영사",
  "조력",
  "공관",
  "대사관",
  "재외국민",
  "보호",
  "발급",
  "접수",
  "절차",
  "처리",
  "신고",
  "여권",
  "긴급여권",
  "여행증명서",
  "체포",
  "구금",
];

const COUNTRY_HIGHLIGHT_KEYWORDS = ["멕시코", "가나", "네팔"];
const CRISIS_HIGHLIGHT_KEYWORDS = [...CRISIS_KEYWORDS];

const elements = {
  startButton: document.getElementById("startButton"),
  stopButton: document.getElementById("stopButton"),
  clearButton: document.getElementById("clearButton"),
  recordingStatus: document.getElementById("recordingStatus"),
  recordingLabel: document.getElementById("recordingLabel"),
  elapsedTime: document.getElementById("elapsedTime"),
  countryValue: document.getElementById("countryValue"),
  incidentValue: document.getElementById("incidentValue"),
  severityMetric: document.getElementById("severityMetric"),
  severityValue: document.getElementById("severityValue"),
  transcriptMeta: document.getElementById("transcriptMeta"),
  transcriptList: document.getElementById("transcriptList"),
  recommendationMeta: document.getElementById("recommendationMeta"),
  recommendationList: document.getElementById("recommendationList"),
  summaryText: document.getElementById("summaryText"),
  nextActionText: document.getElementById("nextActionText"),
  detailTitle: document.getElementById("detailTitle"),
  detailSource: document.getElementById("detailSource"),
  detailBody: document.getElementById("detailBody"),
  checklistMeta: document.getElementById("checklistMeta"),
  checklistList: document.getElementById("checklistList"),
  consultationSummaryMeta: document.getElementById("consultationSummaryMeta"),
  consultationSummaryBody: document.getElementById("consultationSummaryBody"),
};

let realtimeSocket = null;
let mediaStream = null;
let audioContext = null;
let micSource = null;
let micProcessor = null;
let silentOutput = null;
let commitTimer = null;
let elapsedTimer = null;
let elapsedSeconds = 0;
let isTranscribing = false;
let realtimeReady = false;
let audioSinceLastCommit = false;
let stopRequested = false;
let audioChunksSent = 0;
let audioCommitsSent = 0;
let realtimeEventsSeen = 0;
let lastAudioStatusAt = 0;
let filter = "all";
let selectedRecommendationId = null;
let pinnedRecommendationId = null;
let transcript = [];
let isGeneratingSummary = false;

function formatElapsed(totalSeconds) {
  const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, "0");
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function setStatus(status, label) {
  elements.recordingStatus.className = `status-pill ${status}`;
  elements.recordingLabel.textContent = label;
}

function startElapsedTimer() {
  window.clearInterval(elapsedTimer);
  elapsedTimer = window.setInterval(() => {
    elapsedSeconds += 1;
    elements.elapsedTime.textContent = formatElapsed(elapsedSeconds);
  }, 1000);
}

function setControlsBusy(isBusy) {
  isTranscribing = isBusy;
  elements.startButton.disabled = isBusy || !canUseMicrophoneRealtime();
  elements.stopButton.disabled = !isBusy;
  elements.startButton.textContent = isBusy
    ? "전사 진행 중"
    : canUseMicrophoneRealtime()
      ? "상담 시작"
      : "마이크 미지원";
}

function showTranscriptMessage(title, description) {
  elements.transcriptList.innerHTML = `<div class="empty-state"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(description)}</span></div>`;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function canUseMicrophoneRealtime() {
  return Boolean(window.WebSocket && navigator.mediaDevices?.getUserMedia);
}

function startSession() {
  startMicrophoneRealtime().catch((error) => {
    failRealtimeSession(error);
  });
}

function stopSession(label = "상담 종료") {
  stopRequested = true;
  commitRealtimeAudio();
  stopRealtimeResources();
  window.clearInterval(elapsedTimer);
  elapsedTimer = null;
  isTranscribing = false;
  realtimeReady = false;
  audioSinceLastCommit = false;
  elements.startButton.disabled = !canUseMicrophoneRealtime();
  elements.stopButton.disabled = true;
  elements.startButton.textContent = canUseMicrophoneRealtime() ? "상담 시작" : "마이크 미지원";
  setStatus("ready", label);
  elements.transcriptMeta.textContent = `${transcript.length}개 전사 segment`;
}

async function endSessionWithSummary() {
  if (isGeneratingSummary) {
    return;
  }

  stopRequested = true;
  elements.stopButton.disabled = true;
  elements.startButton.disabled = true;
  setStatus("ready", "상담 종료 처리 중");
  elements.transcriptMeta.textContent = "마지막 전사 결과 확인 중";
  commitRealtimeAudio();

  if (realtimeSocket?.readyState === WebSocket.OPEN) {
    await delay(FINAL_TRANSCRIPT_WAIT_MS);
  }

  stopSession("상담 종료");
  await generateConsultationSummary();
}

function resetSession() {
  stopSession("대기 중");
  setStatus("idle", "대기 중");
  stopRequested = false;
  elapsedSeconds = 0;
  isTranscribing = false;
  realtimeReady = false;
  audioSinceLastCommit = false;
  audioChunksSent = 0;
  audioCommitsSent = 0;
  realtimeEventsSeen = 0;
  lastAudioStatusAt = 0;
  transcript = [];
  selectedRecommendationId = null;
  pinnedRecommendationId = null;
  elements.elapsedTime.textContent = "00:00";
  elements.countryValue.textContent = "미감지";
  elements.incidentValue.textContent = "미분류";
  elements.severityValue.textContent = "보통";
  elements.severityMetric.className = "session-metric severity-normal";
  elements.transcriptMeta.textContent = "상담 시작 전";
  elements.recommendationMeta.textContent = "대화 내용 감지 대기";
  elements.summaryText.textContent = "전사 내용이 쌓이면 상담 요약이 표시됩니다.";
  elements.nextActionText.textContent = "신원, 위치, 연락 가능 여부를 우선 확인합니다.";
  isGeneratingSummary = false;
  elements.startButton.disabled = !canUseMicrophoneRealtime();
  elements.stopButton.disabled = true;
  elements.startButton.textContent = canUseMicrophoneRealtime() ? "상담 시작" : "마이크 미지원";
  renderConsultationSummaryPlaceholder(
    "상담이 종료된 후 출력됩니다.",
    "상담 요약 대기 중",
  );
  renderTranscript();
  renderRecommendations([]);
  renderChecklist(checklistByIncident.DEFAULT);
  clearDetail();
}

function getConversationText() {
  return transcript.map((item) => item.text).join(" ");
}

function detectContext(text) {
  const hasPassport = /여권|긴급여권|여행증명서|귀국/.test(text);
  const hasDetention = /체포|구금|detained|arrest/i.test(text);
  const hasMedical = /사고|부상|병원|응급|치료/.test(text);
  const hasTheft = /도난|지갑|카드|현금|운전면허|소매치기|분실 신고|분실신고/.test(text);
  const country = detectCountry(text);

  if (hasDetention) {
    return {
      country,
      incident: "체포·구금",
      incidentKey: "DETENTION",
      severity: "높음",
      severityClass: "severity-high",
    };
  }

  if (hasMedical) {
    return {
      country,
      incident: "사고·부상",
      incidentKey: "MEDICAL",
      severity: "주의",
      severityClass: "severity-watch",
    };
  }

  if (hasPassport) {
    return {
      country,
      incident: "여권 분실",
      incidentKey: "PASSPORT_LOSS",
      severity: "보통",
      severityClass: "severity-normal",
    };
  }

  if (hasTheft) {
    return {
      country,
      incident: "지갑 도난",
      incidentKey: "THEFT",
      severity: "주의",
      severityClass: "severity-watch",
    };
  }

  return {
    country,
    incident: "일반 상담",
    incidentKey: "DEFAULT",
    severity: "보통",
    severityClass: "severity-normal",
  };
}

function detectCountry(text) {
  if (/멕시코|멕시코시티/.test(text)) {
    return "멕시코";
  }
  if (/가나|아크라|쿠마시|타말레/.test(text)) {
    return "가나";
  }
  if (/네팔|카트만두|포카라|랄릿푸르|박타푸르/.test(text)) {
    return "네팔";
  }
  return "미감지";
}

function includesAnyKeyword(text, keywords) {
  const normalized = text.toLowerCase();
  return keywords.some((keyword) => normalized.includes(keyword.toLowerCase()));
}

function shouldRecommendItem(item, text, matched) {
  if (matched.length === 0) {
    return false;
  }

  if (item.type === "country") {
    return true;
  }

  if (item.type === "manual") {
    return includesAnyKeyword(text, CRISIS_KEYWORDS);
  }

  if (item.type === "legal") {
    return (
      includesAnyKeyword(text, CRISIS_KEYWORDS) ||
      includesAnyKeyword(text, LEGAL_TRIGGER_KEYWORDS)
    );
  }

  return true;
}

function scoreRecommendations(text) {
  const normalized = text.toLowerCase();

  return recommendationCatalog
    .map((item) => {
      const matched = item.keywords.filter((keyword) =>
        normalized.includes(keyword.toLowerCase()),
      );
      const score = Math.min(99, item.score + matched.length * 3);
      return {
        ...item,
        score,
        matched,
      };
    })
    .filter((item) => shouldRecommendItem(item, text, item.matched))
    .sort((left, right) => {
      if (left.id === pinnedRecommendationId) {
        return -1;
      }
      if (right.id === pinnedRecommendationId) {
        return 1;
      }
      return right.score - left.score;
    })
    .slice(0, 5);
}

function updateContext() {
  const text = getConversationText();
  const context = detectContext(text);
  const recommendations = scoreRecommendations(text);

  elements.countryValue.textContent = context.country;
  elements.incidentValue.textContent = context.incident;
  elements.severityValue.textContent = context.severity;
  elements.severityMetric.className = `session-metric ${context.severityClass}`;
  elements.recommendationMeta.textContent = `${recommendations.length}개 근거 추천`;

  renderRecommendations(recommendations);
  renderChecklist(checklistByIncident[context.incidentKey] || checklistByIncident.DEFAULT);
  updateSummary(context);

  if (!selectedRecommendationId && recommendations.length > 0) {
    selectedRecommendationId = recommendations[0].id;
    renderDetail(recommendations[0]);
    renderRecommendations(recommendations);
  }
}

function updateSummary(context) {
  if (transcript.length === 0) {
    return;
  }

  if (context.incidentKey === "PASSPORT_LOSS") {
    elements.summaryText.textContent =
      "민원인은 멕시코시티 체류 중 여권을 분실했으며 내일 귀국 예정입니다. 경찰 신고는 아직 진행하지 않았고, 여권 사진과 항공권 확인이 가능한 상태로 보입니다.";
    elements.nextActionText.textContent =
      "신원 확인 자료, 항공권, 현지 경찰 신고 가능 여부, 공관 방문 가능 시간을 확인하세요.";
    return;
  }

  if (context.incidentKey === "THEFT") {
    elements.summaryText.textContent =
      "민원인은 멕시코 체류 중 지갑 도난 피해를 상담 중입니다. 여권 분실 여부, 카드 정지, 현지 경찰 신고, 보험 청구용 접수번호 확보가 핵심 확인 사항입니다.";
    elements.nextActionText.textContent =
      "안전 장소 여부, 여권 보관 상태, 카드사 분실 정지, 경찰 신고 가능 여부를 순서대로 확인하세요.";
    return;
  }

  elements.summaryText.textContent =
    "민원인의 현재 위치, 안전 여부, 연락 가능성, 현지 기관 접수 여부를 중심으로 상담이 진행 중입니다.";
  elements.nextActionText.textContent =
    "위치와 안전 여부를 확인한 뒤 관할 공관 연결 필요성을 판단하세요.";
}

function highlightKeywords(text) {
  const countryWords = new Set(COUNTRY_HIGHLIGHT_KEYWORDS);
  const crisisWords = new Set(CRISIS_HIGHLIGHT_KEYWORDS);
  const words = [...new Set([...COUNTRY_HIGHLIGHT_KEYWORDS, ...CRISIS_HIGHLIGHT_KEYWORDS])]
    .sort((left, right) => right.length - left.length);

  if (words.length === 0) {
    return escapeHtml(text);
  }

  const pattern = new RegExp(words.map(escapeRegExp).join("|"), "g");
  const value = String(text);
  let html = "";
  let cursor = 0;
  let match;

  while ((match = pattern.exec(value)) !== null) {
    const [matchedText] = match;
    html += escapeHtml(value.slice(cursor, match.index));

    const className = countryWords.has(matchedText)
      ? "keyword keyword-country"
      : crisisWords.has(matchedText)
        ? "keyword keyword-crisis"
        : "keyword";

    html += `<mark class="${className}">${escapeHtml(matchedText)}</mark>`;
    cursor = match.index + matchedText.length;
  }

  html += escapeHtml(value.slice(cursor));
  return html;
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderTranscript() {
  if (transcript.length === 0) {
    elements.transcriptList.innerHTML =
      '<div class="empty-state"><strong>전사 내용이 없습니다</strong><span>마이크 전사를 시작하면 표시됩니다.</span></div>';
    return;
  }

  elements.transcriptList.replaceChildren(
    ...transcript.map((item) => {
      const row = document.createElement("article");
      row.className = "transcript-item";
      row.innerHTML = `
        <time class="transcript-time">${item.time}</time>
        <div class="transcript-content">
          <div class="speaker-row">
            <span class="speaker-badge speaker-${item.role}">${item.speaker}</span>
            <span class="confidence">${item.pending ? "수신 중" : formatConfidence(item.confidence)}</span>
          </div>
          <p class="transcript-text">${highlightKeywords(item.text)}</p>
        </div>
      `;
      return row;
    }),
  );

  elements.transcriptList.scrollTop = elements.transcriptList.scrollHeight;
}

function formatConfidence(confidence) {
  return Number.isFinite(confidence) ? `신뢰도 ${confidence}%` : "신뢰도 미제공";
}

function recommendationTypeLabel(type) {
  if (type === "legal") {
    return "법률";
  }
  if (type === "country") {
    return "국가";
  }
  return "매뉴얼";
}

function renderRecommendations(items) {
  const visibleItems = items.filter((item) => filter === "all" || item.type === filter);

  if (visibleItems.length === 0) {
    elements.recommendationList.innerHTML =
      '<div class="empty-state"><strong>추천 대기 중</strong><span>위기상황 또는 지원 국가가 감지되면 관련 근거가 표시됩니다.</span></div>';
    return;
  }

  elements.recommendationList.replaceChildren(
    ...visibleItems.map((item) => {
      const card = document.createElement("article");
      const isSelected = item.id === selectedRecommendationId;
      const isPinned = item.id === pinnedRecommendationId;
      card.className = `recommendation-card${isSelected ? " selected" : ""}${isPinned ? " pinned" : ""}`;
      card.tabIndex = 0;
      card.dataset.id = item.id;
      card.innerHTML = `
        <div class="recommendation-head">
          <div>
            <h3 class="recommendation-title">${escapeHtml(item.title)}</h3>
          </div>
          <span class="score-badge">${item.score}%</span>
        </div>
        <span class="type-badge">${recommendationTypeLabel(item.type)}</span>
        <p class="recommendation-summary">${escapeHtml(item.summary)}</p>
        <div class="recommendation-actions">
          <button class="mini-button primary" type="button" data-action="detail">자세히</button>
          <button class="mini-button" type="button" data-action="pin">${isPinned ? "고정 해제" : "고정"}</button>
          <button class="mini-button" type="button" data-action="answer">답변 문구</button>
        </div>
      `;

      card.addEventListener("click", (event) => {
        const action = event.target?.dataset?.action;
        const shouldShowAnswer = action === "answer";
        if (action === "pin") {
          pinnedRecommendationId = isPinned ? null : item.id;
        }
        selectedRecommendationId = item.id;
        renderDetail(item);
        updateContext();
        if (shouldShowAnswer) {
          elements.summaryText.textContent = item.answer;
        }
      });

      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectedRecommendationId = item.id;
          renderDetail(item);
          updateContext();
        }
      });

      return card;
    }),
  );
}

function renderDetail(item) {
  elements.detailTitle.textContent = item.title;
  elements.detailSource.textContent = item.source;
  elements.detailBody.innerHTML = `
    <div class="detail-meta">
      <span>문서 유형 <strong>${recommendationTypeLabel(item.type)}</strong></span>
      <span>관련도 <strong>${item.score}%</strong></span>
      <span>개정 기준 <strong>${item.revision}</strong></span>
    </div>
    <p>${escapeHtml(item.detail)}</p>
    <p><strong>상담 답변:</strong> ${escapeHtml(item.answer)}</p>
  `;
}

function clearDetail() {
  elements.detailTitle.textContent = "선택된 근거 없음";
  elements.detailSource.textContent = "추천 항목을 선택하면 원문 근거가 표시됩니다.";
  elements.detailBody.innerHTML = "<p>상담 중 고정하거나 자세히 볼 매뉴얼/법률을 선택하세요.</p>";
}

function renderChecklist(items) {
  elements.checklistMeta.textContent = `${items.length}개 항목`;
  elements.checklistList.replaceChildren(
    ...items.map((text, index) => {
      const label = document.createElement("label");
      label.className = "check-item";
      label.innerHTML = `
        <input type="checkbox" />
        <span>${index + 1}. ${escapeHtml(text)}</span>
      `;
      return label;
    }),
  );
}

function activateDetailTab(tabName) {
  const button = document.querySelector(`.detail-tab[data-tab="${tabName}"]`);
  const section = document.getElementById(`${tabName}Tab`);

  if (!button || !section) {
    return;
  }

  document
    .querySelectorAll(".detail-tab")
    .forEach((item) => item.classList.remove("active"));
  document
    .querySelectorAll(".detail-section")
    .forEach((item) => item.classList.remove("active"));

  button.classList.add("active");
  section.classList.add("active");
}

function renderConsultationSummaryPlaceholder(title, description) {
  elements.consultationSummaryMeta.textContent = "상담 종료 후 자동 생성";
  elements.consultationSummaryBody.innerHTML = `
    <div class="summary-waiting">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(description)}</span>
    </div>
  `;
}

function renderConsultationSummaryLoading() {
  elements.consultationSummaryMeta.textContent = "요약 생성 중";
  elements.consultationSummaryBody.innerHTML = `
    <div class="summary-waiting">
      <strong>상담 내용을 정리하고 있습니다.</strong>
      <span>누적 전사 내용을 6하원칙 기준으로 요약 중입니다.</span>
    </div>
  `;
}

function renderConsultationSummaryError(message) {
  elements.consultationSummaryMeta.textContent = "요약 생성 실패";
  elements.consultationSummaryBody.innerHTML = `
    <div class="summary-waiting">
      <strong>상담 요약을 생성하지 못했습니다.</strong>
      <span>${escapeHtml(message || "잠시 후 다시 시도해 주세요.")}</span>
    </div>
  `;
}

function renderConsultationSummary(payload) {
  const summary = payload?.summary;

  if (!summary) {
    renderConsultationSummaryError("요약 응답이 비어 있습니다.");
    return;
  }

  const principles = [
    ["누가", summary.who],
    ["언제", summary.when],
    ["어디서", summary.where],
    ["무엇을", summary.what],
    ["어떻게", summary.how],
    ["왜", summary.why],
  ];
  const nextActions = Array.isArray(summary.nextActions) ? summary.nextActions : [];
  elements.consultationSummaryMeta.textContent = `${payload.model || "LLM"} · 6하원칙 요약`;
  elements.consultationSummaryBody.innerHTML = `
    <div class="six-principle-list">
      ${principles
        .map(
          ([label, value]) => `
            <section class="six-principle-item">
              <strong>${escapeHtml(label)}</strong>
              <p>${escapeHtml(value || "확인 필요")}</p>
            </section>
          `,
        )
        .join("")}
    </div>
    <section class="consultation-result">
      <strong>상담 결과</strong>
      ${escapeHtml(summary.consultationResult || "확인 필요")}
    </section>
    <ul class="summary-actions">
      ${nextActions.map((action) => `<li>${escapeHtml(action)}</li>`).join("")}
    </ul>
  `;
}

function getSummarySegments() {
  return transcript
    .map((item) => ({
      time: item.time,
      speaker: item.speaker || "통화 음성",
      text: String(item.text || "").trim(),
    }))
    .filter((item) => item.text);
}

function getSummaryContext() {
  return {
    country: elements.countryValue.textContent,
    incident: elements.incidentValue.textContent,
    severity: elements.severityValue.textContent,
    durationSeconds: elapsedSeconds,
  };
}

async function requestConsultationSummary(segments) {
  const response = await fetch(buildAiAgentUrl("/v1/call-assist/summary"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      segments,
      context: getSummaryContext(),
    }),
  });
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "";
    throw new Error(detail || `상담 요약 생성 실패 (${response.status})`);
  }

  return payload;
}

async function generateConsultationSummary() {
  const segments = getSummarySegments();
  activateDetailTab("summary");

  if (segments.length === 0) {
    renderConsultationSummaryPlaceholder(
      "요약할 전사 내용이 없습니다.",
      "마이크 전사 내용이 생성된 뒤 상담을 종료하면 요약본이 표시됩니다.",
    );
    return;
  }

  isGeneratingSummary = true;
  elements.startButton.disabled = true;
  elements.stopButton.disabled = true;
  renderConsultationSummaryLoading();

  try {
    const payload = await requestConsultationSummary(segments);
    renderConsultationSummary(payload);
  } catch (error) {
    renderConsultationSummaryError(error.message);
  } finally {
    isGeneratingSummary = false;
    elements.startButton.disabled = !canUseMicrophoneRealtime();
    elements.stopButton.disabled = true;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function startMicrophoneRealtime() {
  if (isTranscribing) {
    return;
  }

  if (!canUseMicrophoneRealtime()) {
    throw new Error("이 브라우저는 마이크 실시간 전사를 지원하지 않습니다.");
  }

  resetSession();
  setControlsBusy(true);
  stopRequested = false;
  setStatus("recording", "Realtime 세션 연결 중");
  elements.transcriptMeta.textContent = "OpenAI Realtime 세션 발급 중";
  showTranscriptMessage("마이크 연결 중", "브라우저 마이크 권한을 허용하면 전사가 시작됩니다.");
  startElapsedTimer();

  const session = await createRealtimeSession();
  await openRealtimeSocket(session);
  await startMicrophoneAudioPipeline();

  setStatus("recording", "마이크 전사 중");
  elements.transcriptMeta.textContent = `${session.model || REALTIME_MODEL} 음성 수신 중`;
  showTranscriptMessage(
    "음성 수신 중",
    session.model === "gpt-realtime-whisper"
      ? "말을 시작하면 실시간 전사 문장이 표시됩니다."
      : "현재 모델은 문장 단위로 처리되어 몇 초 뒤 전사 결과가 표시됩니다.",
  );
}

async function createRealtimeSession() {
  try {
    const response = await fetch(buildAiAgentUrl("/v1/realtime/transcription-session"), {
      method: "POST",
    });
    const payload = await response.json().catch(() => null);

    if (!response.ok) {
      throw new Error(formatRealtimeServerError(payload?.detail, response.status));
    }

    if (!payload?.value) {
      throw new Error("Realtime client secret을 받지 못했습니다.");
    }

    return payload;
  } catch (error) {
    if (error instanceof Error && !error.message.includes("Failed to fetch")) {
      throw error;
    }

    throw new Error(
      "AI agent server에 연결하지 못했습니다. backend/services/ai-agent-server에서 uvicorn app.main:app --reload --port 8000을 먼저 실행해 주세요.",
    );
  }
}

function formatRealtimeServerError(detail, status) {
  const message = typeof detail === "string" ? detail : "";

  if (message.includes("model_not_found") || message.includes("does not have access to model")) {
    return "OpenAI 프로젝트가 gpt-realtime-whisper 모델에 접근할 수 없습니다.";
  }

  if (message.includes("OPENAI_API_KEY")) {
    return "AI agent server에 OPENAI_API_KEY가 설정되어 있지 않습니다.";
  }

  return message || `Realtime 세션 발급 실패 (${status})`;
}

function openRealtimeSocket(session) {
  return new Promise((resolve, reject) => {
    const token = session.value;
    const url = session.wsUrl || "wss://api.openai.com/v1/realtime";
    const socket = new WebSocket(url, [
      "realtime",
      `openai-insecure-api-key.${token}`,
    ]);
    let settled = false;

    realtimeSocket = socket;
    realtimeReady = false;

    socket.addEventListener("open", () => {
      realtimeReady = true;
      settled = true;
      resolve();
    });

    socket.addEventListener("message", (event) => {
      handleRealtimeEvent(event.data);
    });

    socket.addEventListener("error", () => {
      if (!settled) {
        settled = true;
        reject(new Error("OpenAI Realtime WebSocket 연결에 실패했습니다."));
        return;
      }

      failRealtimeSession(new Error("OpenAI Realtime WebSocket 오류가 발생했습니다."));
    });

    socket.addEventListener("close", () => {
      realtimeReady = false;

      if (!settled) {
        settled = true;
        reject(new Error("OpenAI Realtime WebSocket 연결이 닫혔습니다."));
        return;
      }

      if (isTranscribing && !stopRequested) {
        failRealtimeSession(new Error("OpenAI Realtime 연결이 종료되었습니다."));
      }
    });
  });
}

async function startMicrophoneAudioPipeline() {
  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  });

  audioContext = createAudioContext();
  await audioContext.resume();

  micSource = audioContext.createMediaStreamSource(mediaStream);
  micProcessor = audioContext.createScriptProcessor(4096, 1, 1);
  silentOutput = audioContext.createGain();
  silentOutput.gain.value = 0;

  micProcessor.onaudioprocess = (event) => {
    if (!isTranscribing || !realtimeReady || stopRequested) {
      return;
    }

    const input = event.inputBuffer.getChannelData(0);
    const resampled = resampleFloat32(input, audioContext.sampleRate, TARGET_SAMPLE_RATE);
    appendRealtimeAudio(float32ToPcm16(resampled));
  };

  micSource.connect(micProcessor);
  micProcessor.connect(silentOutput);
  silentOutput.connect(audioContext.destination);
  commitTimer = window.setInterval(commitRealtimeAudio, MIC_COMMIT_INTERVAL_MS);
}

function handleRealtimeEvent(rawData) {
  let event;

  try {
    event = JSON.parse(rawData);
  } catch (_error) {
    return;
  }

  realtimeEventsSeen += 1;

  if (event.type === "session.created") {
    elements.transcriptMeta.textContent = "Realtime 세션 생성됨 · 마이크 대기";
    return;
  }

  if (event.type === "input_audio_buffer.committed") {
    elements.transcriptMeta.textContent = `음성 전사 요청 ${audioCommitsSent}회 · 결과 대기`;
    return;
  }

  if (event.type === "conversation.item.added") {
    applyTranscriptFromConversationItem(event.item);
    return;
  }

  if (event.type === "conversation.item.input_audio_transcription.delta") {
    applyRealtimeDelta(event);
    return;
  }

  if (event.type === "conversation.item.input_audio_transcription.completed") {
    applyRealtimeCompleted(event);
    return;
  }

  if (event.type === "conversation.item.input_audio_transcription.failed") {
    const message =
      event.error?.message || "OpenAI Realtime 전사가 실패했습니다. 입력 음성 또는 모델 설정을 확인하세요.";
    failRealtimeSession(new Error(message));
    return;
  }

  if (event.type === "error") {
    const message = event.error?.message || "OpenAI Realtime 처리 중 오류가 발생했습니다.";
    failRealtimeSession(new Error(message));
  }
}

function applyTranscriptFromConversationItem(item) {
  if (!item || !Array.isArray(item.content)) {
    return;
  }

  const transcriptText = item.content
    .map((content) => content?.transcript)
    .filter((value) => typeof value === "string" && value.trim())
    .join(" ")
    .trim();

  if (!transcriptText) {
    return;
  }

  applyRealtimeCompleted({
    item_id: item.id,
    transcript: transcriptText,
  });
}

function applyRealtimeDelta(event) {
  const delta = String(event.delta || "");
  if (!delta) {
    return;
  }

  const itemId = String(event.item_id || `live-${Date.now()}`);
  let item = transcript.find((segment) => segment.id === itemId);

  if (!item) {
    item = {
      id: itemId,
      time: formatElapsed(elapsedSeconds),
      speaker: "통화 음성",
      role: "citizen",
      confidence: null,
      text: "",
      pending: true,
    };
    transcript.push(item);
  }

  item.text = `${item.text}${delta}`;
  item.pending = true;
  renderTranscript();
  updateContext();
}

function applyRealtimeCompleted(event) {
  const text = String(event.transcript || "").trim();
  if (!text) {
    return;
  }

  const itemId = String(event.item_id || `segment-${transcript.length + 1}`);
  let item = transcript.find((segment) => segment.id === itemId);

  if (!item) {
    item = {
      id: itemId,
      time: formatElapsed(elapsedSeconds),
      speaker: "통화 음성",
      role: "citizen",
      confidence: null,
      text,
      pending: false,
    };
    transcript.push(item);
  } else {
    item.text = text;
    item.pending = false;
  }

  elements.transcriptMeta.textContent = `${transcript.length}개 전사 segment`;
  renderTranscript();
  updateContext();
}

function sendRealtimeEvent(event) {
  if (realtimeSocket?.readyState === WebSocket.OPEN) {
    realtimeSocket.send(JSON.stringify(event));
  }
}

function appendRealtimeAudio(pcm16) {
  if (!pcm16.length || realtimeSocket?.readyState !== WebSocket.OPEN) {
    return;
  }

  sendRealtimeEvent({
    type: "input_audio_buffer.append",
    audio: pcm16ToBase64(pcm16),
  });
  audioSinceLastCommit = true;
  audioChunksSent += 1;
  updateAudioSendStatus();
}

function commitRealtimeAudio() {
  if (!audioSinceLastCommit || realtimeSocket?.readyState !== WebSocket.OPEN) {
    return;
  }

  sendRealtimeEvent({ type: "input_audio_buffer.commit" });
  audioSinceLastCommit = false;
  audioCommitsSent += 1;
  elements.transcriptMeta.textContent = `음성 전송 ${audioChunksSent}개 · 전사 요청 ${audioCommitsSent}회`;
}

function updateAudioSendStatus() {
  const now = Date.now();
  if (now - lastAudioStatusAt < 1000) {
    return;
  }

  lastAudioStatusAt = now;
  elements.transcriptMeta.textContent = `마이크 음성 전송 중 · ${audioChunksSent}개 chunk`;
}

function stopRealtimeResources() {
  window.clearInterval(commitTimer);
  commitTimer = null;

  if (micProcessor) {
    micProcessor.onaudioprocess = null;
    micProcessor.disconnect();
    micProcessor = null;
  }

  if (micSource) {
    micSource.disconnect();
    micSource = null;
  }

  if (silentOutput) {
    silentOutput.disconnect();
    silentOutput = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    audioContext.close().catch(() => undefined);
    audioContext = null;
  }

  if (realtimeSocket && realtimeSocket.readyState <= WebSocket.OPEN) {
    realtimeSocket.close();
  }

  realtimeSocket = null;
}

function failRealtimeSession(error) {
  window.clearInterval(elapsedTimer);
  elapsedTimer = null;
  stopRequested = true;
  stopRealtimeResources();
  setStatus("idle", "전사 실패");
  elements.transcriptMeta.textContent = "전사 실패";
  showTranscriptMessage("전사 실패", error.message || "Realtime 전사 중 오류가 발생했습니다.");
  setControlsBusy(false);
}

function createAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  return new AudioContextClass();
}

function resampleFloat32(input, inputRate, outputRate) {
  if (inputRate === outputRate) {
    return input.slice();
  }

  const ratio = inputRate / outputRate;
  const outputLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Float32Array(outputLength);

  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = index * ratio;
    const before = Math.floor(sourceIndex);
    const after = Math.min(before + 1, input.length - 1);
    const weight = sourceIndex - before;
    output[index] = input[before] * (1 - weight) + input[after] * weight;
  }

  return output;
}

function float32ToPcm16(input) {
  const output = new Int16Array(input.length);

  for (let index = 0; index < input.length; index += 1) {
    const value = Math.max(-1, Math.min(1, input[index]));
    output[index] = value < 0 ? value * 0x8000 : value * 0x7fff;
  }

  return output;
}

function pcm16ToBase64(pcm16) {
  const bytes = new Uint8Array(pcm16.buffer, pcm16.byteOffset, pcm16.byteLength);
  const chunkSize = 0x8000;
  let binary = "";

  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }

  return window.btoa(binary);
}

function normalizeSpeakerLabel(value) {
  const label = String(value || "").trim();
  return label || "화자";
}

elements.startButton.addEventListener("click", () => startSession());
elements.stopButton.addEventListener("click", () => {
  endSessionWithSummary();
});
elements.clearButton.addEventListener("click", resetSession);

document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    document
      .querySelectorAll(".filter-button")
      .forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    filter = button.dataset.filter;
    renderRecommendations(scoreRecommendations(getConversationText()));
  });
});

document.querySelectorAll(".detail-tab").forEach((button) => {
  button.addEventListener("click", () => {
    activateDetailTab(button.dataset.tab);
  });
});

resetSession();
