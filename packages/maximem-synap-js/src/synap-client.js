const { BridgeManager } = require('./bridge-manager');

function pickDefined(...values) {
  for (const value of values) {
    if (value !== undefined) return value;
  }
  return undefined;
}

function normalizeTemporalFields(item = {}) {
  return {
    eventDate: pickDefined(item.eventDate, item.event_date, null),
    validUntil: pickDefined(item.validUntil, item.valid_until, null),
    temporalCategory: pickDefined(item.temporalCategory, item.temporal_category, null),
    temporalConfidence: pickDefined(item.temporalConfidence, item.temporal_confidence, 0),
  };
}

function normalizeMemoryItem(item = {}) {
  return {
    id: item.id || '',
    memory: pickDefined(item.memory, item.content, ''),
    score: item.score,
    source: item.source,
    metadata: item.metadata || {},
    contextType: pickDefined(item.contextType, item.context_type),
    ...normalizeTemporalFields(item),
  };
}

function normalizeContextMetadata(metadata = {}) {
  return {
    correlationId: pickDefined(metadata.correlationId, metadata.correlation_id, ''),
    ttlSeconds: pickDefined(metadata.ttlSeconds, metadata.ttl_seconds, 0),
    source: metadata.source || 'unknown',
    retrievedAt: pickDefined(metadata.retrievedAt, metadata.retrieved_at, null),
    compactionApplied: pickDefined(metadata.compactionApplied, metadata.compaction_applied, null),
  };
}

function normalizeConversationContext(value) {
  if (!value) return null;
  return {
    summary: value.summary || null,
    currentState: pickDefined(value.currentState, value.current_state, {}),
    keyExtractions: pickDefined(value.keyExtractions, value.key_extractions, {}),
    recentTurns: pickDefined(value.recentTurns, value.recent_turns, []),
    compactionId: pickDefined(value.compactionId, value.compaction_id, null),
    compactedAt: pickDefined(value.compactedAt, value.compacted_at, null),
    conversationId: pickDefined(value.conversationId, value.conversation_id, null),
  };
}

function normalizeFact(item = {}) {
  return {
    id: item.id || '',
    content: item.content || '',
    confidence: pickDefined(item.confidence, 0),
    source: item.source || '',
    extractedAt: pickDefined(item.extractedAt, item.extracted_at, null),
    metadata: item.metadata || {},
    ...normalizeTemporalFields(item),
  };
}

function normalizePreference(item = {}) {
  return {
    id: item.id || '',
    category: item.category || '',
    content: item.content || '',
    strength: pickDefined(item.strength, item.confidence, 0),
    source: item.source || '',
    extractedAt: pickDefined(item.extractedAt, item.extracted_at, null),
    metadata: item.metadata || {},
    ...normalizeTemporalFields(item),
  };
}

function normalizeEpisode(item = {}) {
  return {
    id: item.id || '',
    summary: pickDefined(item.summary, item.content, ''),
    occurredAt: pickDefined(item.occurredAt, item.occurred_at, null),
    significance: pickDefined(item.significance, item.confidence, 0),
    participants: item.participants || [],
    metadata: item.metadata || {},
    ...normalizeTemporalFields(item),
  };
}

function normalizeEmotion(item = {}) {
  return {
    id: item.id || '',
    emotionType: pickDefined(item.emotionType, item.emotion_type, ''),
    intensity: pickDefined(item.intensity, item.confidence, 0),
    detectedAt: pickDefined(item.detectedAt, item.detected_at, null),
    context: item.context || '',
    metadata: item.metadata || {},
    ...normalizeTemporalFields(item),
  };
}

function normalizeTemporalEvent(item = {}) {
  return {
    id: item.id || '',
    content: item.content || '',
    eventDate: pickDefined(item.eventDate, item.event_date, null),
    validUntil: pickDefined(item.validUntil, item.valid_until, null),
    temporalCategory: pickDefined(item.temporalCategory, item.temporal_category, ''),
    temporalConfidence: pickDefined(item.temporalConfidence, item.temporal_confidence, 0),
    confidence: pickDefined(item.confidence, 0),
    source: item.source || '',
    extractedAt: pickDefined(item.extractedAt, item.extracted_at, null),
    metadata: item.metadata || {},
  };
}

function normalizeContextResponse(result = {}) {
  const context = result.context || result;
  return {
    facts: (context.facts || []).map(normalizeFact),
    preferences: (context.preferences || []).map(normalizePreference),
    episodes: (context.episodes || []).map(normalizeEpisode),
    emotions: (context.emotions || []).map(normalizeEmotion),
    temporalEvents: (pickDefined(context.temporalEvents, context.temporal_events, []) || []).map(normalizeTemporalEvent),
    conversationContext: normalizeConversationContext(
      pickDefined(context.conversationContext, context.conversation_context, null)
    ),
    metadata: normalizeContextMetadata(context.metadata || {}),
    rawResponse: pickDefined(context.rawResponse, context.raw_response, {}),
    bridgeTiming: result.bridgeTiming,
  };
}

function normalizeRecentMessage(item = {}) {
  return {
    role: item.role || 'user',
    content: item.content || '',
    timestamp: item.timestamp || null,
    messageId: pickDefined(item.messageId, item.message_id, ''),
  };
}

function normalizeContextForPromptResult(result = {}) {
  const payload = pickDefined(result.contextForPrompt, result.context_for_prompt, result);
  return {
    formattedContext: pickDefined(payload.formattedContext, payload.formatted_context, null),
    available: !!payload.available,
    isStale: !!pickDefined(payload.isStale, payload.is_stale, false),
    compressionRatio: pickDefined(payload.compressionRatio, payload.compression_ratio, null),
    validationScore: pickDefined(payload.validationScore, payload.validation_score, null),
    compactionAgeSeconds: pickDefined(payload.compactionAgeSeconds, payload.compaction_age_seconds, null),
    qualityWarning: !!pickDefined(payload.qualityWarning, payload.quality_warning, false),
    recentMessages: (pickDefined(payload.recentMessages, payload.recent_messages, []) || []).map(normalizeRecentMessage),
    recentMessageCount: pickDefined(payload.recentMessageCount, payload.recent_message_count, 0),
    compactedMessageCount: pickDefined(payload.compactedMessageCount, payload.compacted_message_count, 0),
    totalMessageCount: pickDefined(payload.totalMessageCount, payload.total_message_count, 0),
    bridgeTiming: result.bridgeTiming,
  };
}

function normalizeSearchMemoryResult(result = {}) {
  return {
    success: !!result.success,
    latencyMs: result.latencyMs || 0,
    results: (result.results || []).map(normalizeMemoryItem),
    resultsCount: pickDefined(result.resultsCount, result.results?.length, 0),
    rawResponse: result.rawResponse || {},
    source: result.source,
    bridgeTiming: result.bridgeTiming,
  };
}

function normalizeGetMemoriesResult(result = {}) {
  const memories = (result.memories || []).map(normalizeMemoryItem);
  return {
    success: !!result.success,
    latencyMs: result.latencyMs || 0,
    memories,
    totalCount: pickDefined(result.totalCount, result.memoriesCount, memories.length, 0),
    rawResponse: pickDefined(result.rawResponse, null),
    source: result.source,
    bridgeTiming: result.bridgeTiming,
  };
}

function normalizeDeleteMemoryResult(result = {}) {
  return {
    success: !!result.success,
    latencyMs: result.latencyMs || 0,
    deletedCount: pickDefined(result.deletedCount, result.rawResponse?.deleted, 0),
    rawResponse: pickDefined(result.rawResponse, null),
    note: result.note,
    bridgeTiming: result.bridgeTiming,
  };
}

class SynapClient {
  constructor(options = {}) {
    this.bridge = new BridgeManager(options);
    this.options = {
      ingestTimeoutMs: options.ingestTimeoutMs || 120_000,
    };

    this.#registerShutdownHooks();
  }

  async init() {
    await this.bridge.ensureStarted();
  }

  async addMemory({
    userId,
    customerId,
    conversationId,
    sessionId,
    messages,
    mode,
    documentType,
    documentId,
    documentCreatedAt,
    metadata,
  }) {
    this.#assert(userId, 'userId is required');
    this.#assert(customerId, 'customerId is required');
    this.#assert(Array.isArray(messages), 'messages must be an array');

    const params = { user_id: userId, messages };
    params.customer_id = customerId;
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (sessionId !== undefined) params.session_id = sessionId;
    if (mode !== undefined) params.mode = mode;
    if (documentType !== undefined) params.document_type = documentType;
    if (documentId !== undefined) params.document_id = documentId;
    if (documentCreatedAt !== undefined) params.document_created_at = documentCreatedAt;
    if (metadata !== undefined) params.metadata = metadata;

    return this.bridge.call('add_memory', params, this.options.ingestTimeoutMs);
  }

  async searchMemory({ userId, customerId, query, maxResults = 10, mode, conversationId, types }) {
    this.#assert(userId, 'userId is required');
    this.#assert(query, 'query is required');
    this.#assertArray(types, 'types must be an array when provided');

    const params = { user_id: userId, query, max_results: maxResults };
    if (customerId !== undefined) params.customer_id = customerId;
    if (mode !== undefined) params.mode = mode;
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (types !== undefined) params.types = types;

    return normalizeSearchMemoryResult(await this.bridge.call('search_memory', params));
  }

  async getMemories({ userId, customerId, mode, conversationId, maxResults, types }) {
    this.#assert(userId, 'userId is required');
    this.#assertArray(types, 'types must be an array when provided');

    const params = { user_id: userId };
    if (customerId !== undefined) params.customer_id = customerId;
    if (mode !== undefined) params.mode = mode;
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (maxResults !== undefined) params.max_results = maxResults;
    if (types !== undefined) params.types = types;

    return normalizeGetMemoriesResult(await this.bridge.call('get_memories', params));
  }

  async fetchUserContext({ userId, customerId, conversationId, searchQuery, maxResults = 10, types, mode }) {
    this.#assert(userId, 'userId is required');
    this.#assertArray(searchQuery, 'searchQuery must be an array when provided');
    this.#assertArray(types, 'types must be an array when provided');

    const params = { user_id: userId, max_results: maxResults };
    if (customerId !== undefined) params.customer_id = customerId;
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (searchQuery !== undefined) params.search_query = searchQuery;
    if (types !== undefined) params.types = types;
    if (mode !== undefined) params.mode = mode;

    return normalizeContextResponse(await this.bridge.call('fetch_user_context', params));
  }

  async fetchCustomerContext({ customerId, conversationId, searchQuery, maxResults = 10, types, mode }) {
    this.#assert(customerId, 'customerId is required');
    this.#assertArray(searchQuery, 'searchQuery must be an array when provided');
    this.#assertArray(types, 'types must be an array when provided');

    const params = { customer_id: customerId, max_results: maxResults };
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (searchQuery !== undefined) params.search_query = searchQuery;
    if (types !== undefined) params.types = types;
    if (mode !== undefined) params.mode = mode;

    return normalizeContextResponse(await this.bridge.call('fetch_customer_context', params));
  }

  async fetchClientContext({ conversationId, searchQuery, maxResults = 10, types, mode } = {}) {
    this.#assertArray(searchQuery, 'searchQuery must be an array when provided');
    this.#assertArray(types, 'types must be an array when provided');

    const params = { max_results: maxResults };
    if (conversationId !== undefined) params.conversation_id = conversationId;
    if (searchQuery !== undefined) params.search_query = searchQuery;
    if (types !== undefined) params.types = types;
    if (mode !== undefined) params.mode = mode;

    return normalizeContextResponse(await this.bridge.call('fetch_client_context', params));
  }

  async getContextForPrompt({ conversationId, style } = {}) {
    this.#assert(conversationId, 'conversationId is required');

    const params = { conversation_id: conversationId };
    if (style !== undefined) params.style = style;

    return normalizeContextForPromptResult(await this.bridge.call('get_context_for_prompt', params));
  }

  async deleteMemory({ userId, customerId, memoryId = null }) {
    this.#assert(userId, 'userId is required');
    if (memoryId == null) this.#assert(customerId, 'customerId is required when memoryId is not provided');

    const params = { user_id: userId, memory_id: memoryId };
    if (customerId !== undefined) params.customer_id = customerId;

    return normalizeDeleteMemoryResult(await this.bridge.call('delete_memory', params));
  }

  async shutdown() {
    await this.bridge.shutdown();
  }

  #assert(value, message) {
    if (!value) throw new Error(message);
  }

  #assertArray(value, message) {
    if (value !== undefined && !Array.isArray(value)) throw new Error(message);
  }

  #registerShutdownHooks() {
    const close = async () => {
      try {
        await this.shutdown();
      } catch (_) {
        // Best-effort shutdown.
      }
    };

    process.once('beforeExit', close);
    process.once('SIGINT', async () => {
      await close();
      process.exit(0);
    });
    process.once('SIGTERM', async () => {
      await close();
      process.exit(0);
    });
  }
}

module.exports = { SynapClient };
