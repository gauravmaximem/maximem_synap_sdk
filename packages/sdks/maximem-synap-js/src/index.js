const { SynapClient } = require('./synap-client');
const { setupPythonRuntime, resolveInstanceId } = require('./runtime');
const { setupTypeScriptExtension } = require('./setup-typescript');
const errors = require('./errors');

module.exports = {
  SynapClient,
  createClient: (options = {}) => new SynapClient(options),
  setupPythonRuntime,
  setupTypeScriptExtension,
  resolveInstanceId,
  ...errors,
};
