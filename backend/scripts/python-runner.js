const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const backendRoot = path.resolve(__dirname, '..');

const candidates = [
  {
    command: path.join(backendRoot, '.venv', 'Scripts', 'python.exe'),
    args: [],
    exists: true,
  },
  {
    command: path.join(backendRoot, '.venv', 'bin', 'python3'),
    args: [],
    exists: true,
  },
  {
    command: path.join(backendRoot, '.venv', 'bin', 'python'),
    args: [],
    exists: true,
  },
  {
    command: process.env.PYTHON,
    args: [],
    exists: false,
  },
  {
    command: 'python3',
    args: [],
    exists: false,
  },
  {
    command: 'python',
    args: [],
    exists: false,
  },
  {
    command: 'py',
    args: ['-3'],
    exists: false,
  },
].filter((candidate) => candidate.command);

function resolvePython() {
  for (const candidate of candidates) {
    if (candidate.exists && !fs.existsSync(candidate.command)) {
      continue;
    }

    const probe = spawnSync(candidate.command, [...candidate.args, '--version'], {
      cwd: backendRoot,
      encoding: 'utf8',
      stdio: 'pipe',
    });

    if (probe.status === 0) {
      return candidate;
    }
  }

  throw new Error(
    'Python 실행 파일을 찾지 못했습니다. .venv를 만들거나 PYTHON 환경변수를 설정하세요.',
  );
}

const scriptArgs = process.argv.slice(2);

if (scriptArgs.length === 0) {
  console.error('실행할 Python 스크립트 또는 인자를 지정하세요.');
  process.exit(1);
}

try {
  const python = resolvePython();
  const result = spawnSync(python.command, [...python.args, ...scriptArgs], {
    cwd: backendRoot,
    stdio: 'inherit',
  });

  process.exit(result.status ?? 1);
} catch (error) {
  console.error(error.message);
  process.exit(1);
}
