const os = require('os');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

function isWindows() {
  return process.platform === 'win32';
}

function getSdkHome(customHome) {
  if (customHome) return customHome;
  if (process.env.SYNAP_JS_SDK_HOME) return process.env.SYNAP_JS_SDK_HOME;
  return path.join(os.homedir(), '.synap-js-sdk');
}

function getVenvPythonPath(venvPath) {
  if (isWindows()) return path.join(venvPath, 'Scripts', 'python.exe');
  return path.join(venvPath, 'bin', 'python');
}

function resolveBridgeScriptPath(customBridgeScriptPath) {
  if (customBridgeScriptPath) return customBridgeScriptPath;
  return path.join(__dirname, '..', 'bridge', 'synap_bridge.py');
}

function resolvePythonBin(options = {}) {
  const candidates = [];

  if (options.pythonBin) candidates.push(options.pythonBin);
  if (process.env.SYNAP_PYTHON_BIN) candidates.push(process.env.SYNAP_PYTHON_BIN);

  const sdkHome = getSdkHome(options.sdkHome);
  const venvPath = options.venvPath || path.join(sdkHome, '.venv');
  candidates.push(getVenvPythonPath(venvPath));

  if (isWindows()) {
    candidates.push('python.exe');
    candidates.push('python');
  } else {
    candidates.push('python3');
    candidates.push('python');
  }

  return candidates;
}

function resolveInstanceId(explicitInstanceId) {
  if (explicitInstanceId) return explicitInstanceId;
  if (process.env.SYNAP_INSTANCE_ID) return process.env.SYNAP_INSTANCE_ID;

  try {
    const instancesDir = path.join(os.homedir(), '.synap', 'instances');
    if (!fs.existsSync(instancesDir)) return '';

    const now = new Date();
    let best = null;

    for (const entry of fs.readdirSync(instancesDir)) {
      const metadataPath = path.join(instancesDir, entry, 'metadata.json');
      if (!fs.existsSync(metadataPath)) continue;

      try {
        const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
        const expiresAt = new Date(metadata.expires_at);
        const issuedAt = new Date(metadata.issued_at);

        if (Number.isNaN(expiresAt.getTime()) || Number.isNaN(issuedAt.getTime())) continue;
        if (expiresAt <= now) continue;

        if (!best || issuedAt > new Date(best.issued_at)) best = metadata;
      } catch (_) {
        // Ignore malformed metadata and continue scanning.
      }
    }

    return best ? best.instance_id || '' : '';
  } catch (_) {
    return '';
  }
}

function runCommand(command, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      ...opts,
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
    });

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', (error) => {
      reject(error);
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve({ code, stdout, stderr });
      } else {
        const err = new Error(`Command failed: ${command} ${args.join(' ')} (exit ${code})\n${stderr || stdout}`);
        err.code = code;
        err.stdout = stdout;
        err.stderr = stderr;
        reject(err);
      }
    });
  });
}

async function setupPythonRuntime(options = {}) {
  const sdkHome = getSdkHome(options.sdkHome);
  const venvPath = options.venvPath || path.join(sdkHome, '.venv');
  const pythonBootstrap = options.pythonBootstrap || process.env.SYNAP_PYTHON_BOOTSTRAP || (isWindows() ? 'python' : 'python3');
  const pythonPackage = options.pythonPackage || process.env.SYNAP_PY_SDK_PACKAGE || 'maximem-synap';
  const pythonSdkVersion = options.pythonSdkVersion || process.env.SYNAP_PY_SDK_VERSION || '';
  const packageSpec = pythonSdkVersion ? `${pythonPackage}==${pythonSdkVersion}` : pythonPackage;
  const pythonBin = getVenvPythonPath(venvPath);

  fs.mkdirSync(sdkHome, { recursive: true });

  if (!fs.existsSync(pythonBin) || options.forceRecreateVenv) {
    await runCommand(pythonBootstrap, ['-m', 'venv', venvPath], { env: process.env });
  }

  await runCommand(pythonBin, ['-m', 'pip', 'install', '--upgrade', 'pip'], { env: process.env });

  const installArgs = ['-m', 'pip', 'install'];
  if (options.upgrade) installArgs.push('--upgrade');
  if (options.noDeps) installArgs.push('--no-deps');
  if (options.noBuildIsolation) installArgs.push('--no-build-isolation');
  installArgs.push(packageSpec);

  await runCommand(pythonBin, installArgs, { env: process.env });

  return {
    sdkHome,
    venvPath,
    pythonBin,
    pythonPackage,
    pythonSdkVersion: pythonSdkVersion || null,
    installTarget: packageSpec,
  };
}

module.exports = {
  getSdkHome,
  getVenvPythonPath,
  resolveBridgeScriptPath,
  resolvePythonBin,
  resolveInstanceId,
  setupPythonRuntime,
  runCommand,
};
