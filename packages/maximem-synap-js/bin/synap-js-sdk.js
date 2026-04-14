#!/usr/bin/env node

const { setupPythonRuntime } = require('../src/runtime');
const { setupTypeScriptExtension } = require('../src/setup-typescript');

function parseArgs(argv) {
  const args = { _: [] };

  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];

    if (!token.startsWith('--')) {
      args._.push(token);
      continue;
    }

    const key = token.slice(2);
    const next = argv[i + 1];

    if (!next || next.startsWith('--')) {
      args[key] = true;
      continue;
    }

    args[key] = next;
    i += 1;
  }

  return args;
}

function printHelp() {
  console.log(`synap-js-sdk

Usage:
  synap-js-sdk setup [options]
  synap-js-sdk setup-ts [options]

setup options:
  --python <bin>             Python bootstrap binary (default: python3)
  --sdk-home <path>          SDK home (default: ~/.synap-js-sdk)
  --venv <path>              Virtualenv path (default: <sdk-home>/.venv)
  --package <name>           Python package name (default: maximem-synap)
  --sdk-version <ver>        Python SDK version to install
  --no-deps                  Install without dependencies
  --no-build-isolation       Disable pip build isolation
  --upgrade                  Use pip --upgrade
  --force-recreate-venv      Recreate virtualenv

setup-ts options:
  --project-dir <path>       Target Node project directory (default: cwd)
  --package-manager <name>   npm | pnpm | yarn | bun (auto-detect if omitted)
  --skip-install             Skip installing typescript and @types/node
  --tsconfig-path <path>     tsconfig output path (default: tsconfig.json)
  --wrapper-path <path>      Typed wrapper output path (default: src/synap.ts)
  --no-wrapper               Do not generate the typed wrapper file
  --force                    Overwrite generated files when they already exist

global:
  --help                     Show this help
`);
}

async function run() {
  const args = parseArgs(process.argv.slice(2));
  const command = args._[0];

  if (!command || args.help || command === 'help') {
    printHelp();
    process.exit(0);
  }

  if (command === 'setup') {
    try {
      const result = await setupPythonRuntime({
        pythonBootstrap: args.python,
        sdkHome: args['sdk-home'],
        venvPath: args.venv,
        pythonPackage: args.package,
        pythonSdkVersion: args['sdk-version'],
        noDeps: !!args['no-deps'],
        noBuildIsolation: !!args['no-build-isolation'],
        upgrade: !!args.upgrade,
        forceRecreateVenv: !!args['force-recreate-venv'],
      });

      console.log('Synap JS SDK Python runtime setup complete.');
      console.log(JSON.stringify(result, null, 2));
      return;
    } catch (error) {
      console.error('Setup failed:');
      console.error(error.message || String(error));
      process.exit(1);
    }
  }

  if (command === 'setup-ts') {
    try {
      const result = await setupTypeScriptExtension({
        projectDir: args['project-dir'],
        packageManager: args['package-manager'],
        skipInstall: !!args['skip-install'],
        tsconfigPath: args['tsconfig-path'],
        wrapperPath: args['wrapper-path'],
        noWrapper: !!args['no-wrapper'],
        force: !!args.force,
      });

      console.log('Synap JS SDK TypeScript extension setup complete.');
      console.log(JSON.stringify(result, null, 2));
      return;
    } catch (error) {
      console.error('TypeScript setup failed:');
      console.error(error.message || String(error));
      process.exit(1);
    }
  }

  console.error(`Unknown command: ${command}`);
  printHelp();
  process.exit(1);
}

run();
