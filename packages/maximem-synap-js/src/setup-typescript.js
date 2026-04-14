const fs = require('fs');
const path = require('path');
const { runCommand } = require('./runtime');

function detectPackageManager(projectDir, explicitPackageManager) {
  if (explicitPackageManager) return explicitPackageManager;

  if (fs.existsSync(path.join(projectDir, 'pnpm-lock.yaml'))) return 'pnpm';
  if (fs.existsSync(path.join(projectDir, 'yarn.lock'))) return 'yarn';
  if (fs.existsSync(path.join(projectDir, 'bun.lockb')) || fs.existsSync(path.join(projectDir, 'bun.lock'))) {
    return 'bun';
  }

  return 'npm';
}

function getInstallArgs(packageManager) {
  switch (packageManager) {
    case 'pnpm':
      return { command: 'pnpm', args: ['add', '-D', 'typescript', '@types/node'] };
    case 'yarn':
      return { command: 'yarn', args: ['add', '-D', 'typescript', '@types/node'] };
    case 'bun':
      return { command: 'bun', args: ['add', '-d', 'typescript', '@types/node'] };
    case 'npm':
      return { command: 'npm', args: ['install', '-D', 'typescript', '@types/node'] };
    default:
      throw new Error(`Unsupported package manager '${packageManager}'. Use npm, pnpm, yarn, or bun.`);
  }
}

function writeFileIfNeeded(filePath, contents, force) {
  if (fs.existsSync(filePath) && !force) {
    return false;
  }

  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, contents, 'utf8');
  return true;
}

function getTsconfigTemplate() {
  return `{
  "compilerOptions": {
    "target": "ES2020",
    "module": "CommonJS",
    "moduleResolution": "Node",
    "strict": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["src/**/*.ts", "types/**/*.d.ts"]
}
`;
}

function getWrapperTemplate() {
  return `import {
  createClient,
  type SynapClient,
  type SynapClientOptions,
  type AddMemoryInput,
  type SearchMemoryInput,
  type GetMemoriesInput,
  type FetchUserContextInput,
  type FetchCustomerContextInput,
  type FetchClientContextInput,
  type GetContextForPromptInput,
  type DeleteMemoryInput,
} from '@maximem/synap-js-sdk';

export class SynapTsClient {
  private readonly client: SynapClient;

  constructor(options: SynapClientOptions = {}) {
    this.client = createClient(options);
  }

  init() {
    return this.client.init();
  }

  addMemory(input: AddMemoryInput) {
    return this.client.addMemory(input);
  }

  searchMemory(input: SearchMemoryInput) {
    return this.client.searchMemory(input);
  }

  getMemories(input: GetMemoriesInput) {
    return this.client.getMemories(input);
  }

  fetchUserContext(input: FetchUserContextInput) {
    return this.client.fetchUserContext(input);
  }

  fetchCustomerContext(input: FetchCustomerContextInput) {
    return this.client.fetchCustomerContext(input);
  }

  fetchClientContext(input?: FetchClientContextInput) {
    return this.client.fetchClientContext(input);
  }

  getContextForPrompt(input: GetContextForPromptInput) {
    return this.client.getContextForPrompt(input);
  }

  deleteMemory(input: DeleteMemoryInput) {
    return this.client.deleteMemory(input);
  }

  shutdown() {
    return this.client.shutdown();
  }
}

export const createTsClient = (options: SynapClientOptions = {}) => new SynapTsClient(options);
`;
}

async function setupTypeScriptExtension(options = {}) {
  const projectDir = path.resolve(options.projectDir || process.cwd());
  const packageJsonPath = path.join(projectDir, 'package.json');

  if (!fs.existsSync(packageJsonPath)) {
    throw new Error(`No package.json found in ${projectDir}. Run setup-ts inside a Node project.`);
  }

  const packageManager = detectPackageManager(projectDir, options.packageManager);
  const tsconfigPath = path.resolve(projectDir, options.tsconfigPath || 'tsconfig.json');
  const wrapperPath = path.resolve(projectDir, options.wrapperPath || path.join('src', 'synap.ts'));

  if (!options.skipInstall) {
    const install = getInstallArgs(packageManager);
    await runCommand(install.command, install.args, { env: process.env, cwd: projectDir });
  }

  const tsconfigCreated = writeFileIfNeeded(tsconfigPath, getTsconfigTemplate(), options.force);
  const wrapperCreated = options.noWrapper
    ? false
    : writeFileIfNeeded(wrapperPath, getWrapperTemplate(), options.force);

  return {
    projectDir,
    packageManager,
    installedDevDependencies: !options.skipInstall,
    tsconfigPath,
    tsconfigCreated,
    wrapperPath: options.noWrapper ? null : wrapperPath,
    wrapperCreated,
  };
}

module.exports = {
  setupTypeScriptExtension,
};
