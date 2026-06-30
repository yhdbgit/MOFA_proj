import * as SecureStore from 'expo-secure-store';

const CITIZEN_ID_KEY = 'mofa.citizenId';

function createCitizenId() {
  if (globalThis.crypto?.randomUUID) {
    return `citizen-${globalThis.crypto.randomUUID()}`;
  }

  return `citizen-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`;
}

export async function getOrCreateCitizenId() {
  const existingCitizenId = await SecureStore.getItemAsync(CITIZEN_ID_KEY);

  if (existingCitizenId) {
    return existingCitizenId;
  }

  const citizenId = createCitizenId();
  await SecureStore.setItemAsync(CITIZEN_ID_KEY, citizenId);
  return citizenId;
}
