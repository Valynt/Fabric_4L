import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDir, '../..');

const requiredBuildEnv = {
  VITE_API_BASE: '/api/v1',
  VITE_L1_PREFIX: '/ingest',
  VITE_L2_PREFIX: '/extract',
  VITE_L2_5_PREFIX: '/signals',
  VITE_L3_PREFIX: '/graph',
  VITE_L4_PREFIX: '/agents',
  VITE_L5_PREFIX: '/truths',
  VITE_L6_PREFIX: '/benchmarks',
  VITE_L7_PREFIX: '/billing',
};

const env = {
  ...process.env,
  ...requiredBuildEnv,
};

const child = spawnSync('pnpm', ['run', 'test:prod-auth-bypass'], {
  cwd: webRoot,
  stdio: 'inherit',
  env,
  shell: true,
});

if (child.error) {
  console.error('Failed to execute production auth bypass gate:', child.error.message);
  process.exit(1);
}

process.exit(child.status ?? 1);
