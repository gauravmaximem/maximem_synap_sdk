'use strict';

class SynapError extends Error {
  constructor(message, correlationId) {
    super(message);
    this.name = 'SynapError';
    this.correlationId = correlationId || null;
  }
}

class SynapTransientError extends SynapError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'SynapTransientError';
  }
}

class SynapPermanentError extends SynapError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'SynapPermanentError';
  }
}

class NetworkTimeoutError extends SynapTransientError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'NetworkTimeoutError';
  }
}

class RateLimitError extends SynapTransientError {
  constructor(message, retryAfterSeconds, correlationId) {
    super(message, correlationId);
    this.name = 'RateLimitError';
    this.retryAfterSeconds = retryAfterSeconds || null;
  }
}

class ServiceUnavailableError extends SynapTransientError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'ServiceUnavailableError';
  }
}

class AgentUnavailableError extends SynapTransientError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'AgentUnavailableError';
  }
}

class InvalidInputError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'InvalidInputError';
  }
}

class InvalidInstanceIdError extends InvalidInputError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'InvalidInstanceIdError';
  }
}

class InvalidConversationIdError extends InvalidInputError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'InvalidConversationIdError';
  }
}

class AuthenticationError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'AuthenticationError';
  }
}

class BootstrapKeyInvalidError extends AuthenticationError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'BootstrapKeyInvalidError';
  }
}

class BootstrapError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'BootstrapError';
  }
}

class ContextNotFoundError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'ContextNotFoundError';
  }
}

class SessionExpiredError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'SessionExpiredError';
  }
}

class ListeningAlreadyActiveError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'ListeningAlreadyActiveError';
  }
}

class ListeningNotActiveError extends SynapPermanentError {
  constructor(message, correlationId) {
    super(message, correlationId);
    this.name = 'ListeningNotActiveError';
  }
}

const ERROR_MAP = {
  SynapError,
  SynapTransientError,
  SynapPermanentError,
  NetworkTimeoutError,
  RateLimitError,
  ServiceUnavailableError,
  AgentUnavailableError,
  InvalidInputError,
  InvalidInstanceIdError,
  InvalidConversationIdError,
  AuthenticationError,
  BootstrapKeyInvalidError,
  BootstrapError,
  ContextNotFoundError,
  SessionExpiredError,
  ListeningAlreadyActiveError,
  ListeningNotActiveError,
};

function createSynapError(message, errorType) {
  const ErrorClass = ERROR_MAP[errorType];
  if (ErrorClass) return new ErrorClass(message);
  return new SynapError(message);
}

module.exports = {
  SynapError,
  SynapTransientError,
  SynapPermanentError,
  NetworkTimeoutError,
  RateLimitError,
  ServiceUnavailableError,
  AgentUnavailableError,
  InvalidInputError,
  InvalidInstanceIdError,
  InvalidConversationIdError,
  AuthenticationError,
  BootstrapKeyInvalidError,
  BootstrapError,
  ContextNotFoundError,
  SessionExpiredError,
  ListeningAlreadyActiveError,
  ListeningNotActiveError,
  createSynapError,
};
