import { getOrCreateCitizenId } from './deviceIdentityStore';

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8080';
const CITIZEN_ID_HEADER = 'X-Citizen-Id';

const API_BASE_URL = trimTrailingSlash(
  process.env.EXPO_PUBLIC_MOFA_API_BASE_URL ?? DEFAULT_API_BASE_URL,
);

function trimTrailingSlash(value) {
  return String(value).replace(/\/+$/, '');
}

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
}

async function parseJson(response) {
  return response.json().catch(() => ({}));
}

function resolveServerError(payload, fallback) {
  if (typeof payload?.message === 'string') {
    return payload.message;
  }

  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }

  return payload?.error ?? fallback;
}

async function requestCitizenProfile(path, options = {}) {
  const citizenId = await getOrCreateCitizenId();
  const response = await fetch(buildUrl(path), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      [CITIZEN_ID_HEADER]: citizenId,
      ...options.headers,
    },
  });
  const payload = await parseJson(response);

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(
      resolveServerError(payload, `기본 정보 요청에 실패했습니다. (${response.status})`),
    );
  }

  return payload;
}

export async function getCitizenProfile() {
  return requestCitizenProfile('/api/citizen-profile');
}

export async function saveCitizenProfile(profile) {
  return requestCitizenProfile('/api/citizen-profile', {
    method: 'PUT',
    body: JSON.stringify(profile),
  });
}
