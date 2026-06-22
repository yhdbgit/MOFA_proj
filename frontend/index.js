import { registerRootComponent } from 'expo';

import App from './App';

// Expo 앱 진입점이다. package.json의 main이 이 파일을 가리키며,
// registerRootComponent가 App을 Android, iOS, 웹의 루트 컴포넌트로 등록한다.
registerRootComponent(App);
