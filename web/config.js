// 관리자 웹이 사용하는 백엔드 주소다. 배포 또는 다른 PC에서 실행할 때 이 값만 변경한다.
export const BACKEND_BASE_URL = 'http://127.0.0.1:8787';

export function buildBackendUrl(path) {
  return `${BACKEND_BASE_URL}${path}`;
}
