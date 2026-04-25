import readline from 'node:readline';
import { performance } from 'node:perf_hooks';
import { EnvironmentManager } from './env_manager';
import type { ControllerSpec, ControllerType, PlayerID, StepResultOptions } from './types';

type SingleRPCRequest =
  | {
      id: string;
      type: 'create_env';
      format: string;
      seed?: number[];
      players?: Partial<Record<PlayerID, ControllerSpec>>;
    }
  | {
      id: string;
      type: 'reset';
      env_id: string;
      options?: StepResultOptions;
    }
  | {
      id: string;
      type: 'step';
      env_id: string;
      choices: Partial<Record<PlayerID, string>>;
      options?: StepResultOptions;
    }
  | {
      id: string;
      type: 'close_env';
      env_id: string;
    }
  | {
      id: string;
      type: 'agent_action';
      env_id: string;
      player: PlayerID;
      agent: ControllerType;
    }
  | {
      id: string;
      type: 'ping';
    };

type RPCRequest =
  | SingleRPCRequest
  | {
      id: string;
      type: 'batch';
      requests: SingleRPCRequest[];
    };

const manager = new EnvironmentManager();
const traceRpcSetting = String(process.env.SIM_CORE_TRACE_RPC || '').toLowerCase();
const traceRpc = traceRpcSetting !== '' && !['0', 'false', 'off'].includes(traceRpcSetting);
const configuredSlowTraceMs = Number(process.env.SIM_CORE_TRACE_SLOW_MS || 5000);
const slowTraceMs = Number.isFinite(configuredSlowTraceMs) && configuredSlowTraceMs > 0 ? configuredSlowTraceMs : 5000;

function writeResponse(payload: unknown): void {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

function memorySnapshot(): Record<string, number> {
  const memory = process.memoryUsage();
  return {
    rss_mb: Number((memory.rss / 1024 / 1024).toFixed(1)),
    heap_used_mb: Number((memory.heapUsed / 1024 / 1024).toFixed(1)),
    heap_total_mb: Number((memory.heapTotal / 1024 / 1024).toFixed(1)),
    external_mb: Number((memory.external / 1024 / 1024).toFixed(1)),
  };
}

function managerSnapshot(): Record<string, unknown> {
  const diagnostics = manager.diagnostics();
  return {
    open_env_count: diagnostics.open_env_count,
    next_env_id: diagnostics.next_env_id,
  };
}

function trace(event: string, payload: Record<string, unknown>): void {
  if (!traceRpc) {
    return;
  }
  process.stderr.write(
    `[sim-core] ${JSON.stringify({
      event,
      at_ms: Number(performance.now().toFixed(3)),
      ...payload,
    })}\n`,
  );
}

function summarizeRequest(request: RPCRequest | SingleRPCRequest): Record<string, unknown> {
  const summary: Record<string, unknown> = {
    id: request.id,
    type: request.type,
  };

  if (request.type === 'batch') {
    const requestTypes: Record<string, number> = {};
    const envIds: string[] = [];
    for (const subrequest of request.requests) {
      requestTypes[subrequest.type] = (requestTypes[subrequest.type] || 0) + 1;
      const envId = resolveEnvId(subrequest);
      if (envId && !envIds.includes(envId)) {
        envIds.push(envId);
      }
    }
    return {
      ...summary,
      request_count: request.requests.length,
      request_types: requestTypes,
      env_ids: envIds,
    };
  }

  const envId = resolveEnvId(request);
  if (envId) {
    summary.env_id = envId;
  }
  if (request.type === 'create_env') {
    summary.format = request.format;
    summary.seed = request.seed;
  }
  if (request.type === 'step') {
    summary.choice_players = Object.keys(request.choices || {});
    summary.choices = request.choices;
  }
  if (request.type === 'agent_action') {
    summary.player = request.player;
    summary.agent = request.agent;
  }
  return summary;
}

function summarizeResult(result: unknown): Record<string, unknown> | null {
  if (!result || typeof result !== 'object') {
    return null;
  }
  const record = result as Record<string, unknown>;
  const summary: Record<string, unknown> = {};
  for (const key of ['env_id', 'terminated', 'winner']) {
    if (key in record) {
      summary[key] = record[key];
    }
  }
  const info = record.info;
  if (info && typeof info === 'object') {
    const infoRecord = info as Record<string, unknown>;
    summary.turn = infoRecord.turn;
    summary.format = infoRecord.format;
  }
  return summary;
}

function beginTrace(
  event: string,
  payload: Record<string, unknown>,
): (ok: boolean, extra?: Record<string, unknown>) => void {
  if (!traceRpc) {
    return () => undefined;
  }
  const startedAt = performance.now();
  trace(`${event}_start`, payload);
  let waitCount = 0;
  const timer = setInterval(() => {
    waitCount += 1;
    trace(`${event}_waiting`, {
      ...payload,
      elapsed_ms: Number((performance.now() - startedAt).toFixed(3)),
      wait_count: waitCount,
      memory: memorySnapshot(),
      manager: managerSnapshot(),
    });
  }, slowTraceMs);
  timer.unref?.();

  return (ok: boolean, extra: Record<string, unknown> = {}) => {
    clearInterval(timer);
    const elapsedMs = performance.now() - startedAt;
    if (!ok || elapsedMs >= slowTraceMs || event === 'request') {
      trace(`${event}_end`, {
        ...payload,
        elapsed_ms: Number(elapsedMs.toFixed(3)),
        ok,
        memory: event === 'request' ? memorySnapshot() : undefined,
        ...extra,
      });
    }
  };
}

function resolveEnvId(request: SingleRPCRequest, result?: unknown): string | null {
  if ('env_id' in request && typeof request.env_id === 'string') {
    return request.env_id;
  }
  if (request.type === 'create_env' && result && typeof result === 'object' && 'env_id' in result) {
    const envId = (result as { env_id?: unknown }).env_id;
    return typeof envId === 'string' ? envId : null;
  }
  return null;
}

async function handleSingleRequest(request: SingleRPCRequest): Promise<unknown> {
  switch (request.type) {
    case 'create_env':
      return manager.createEnv(request.format, request.seed, request.players);
    case 'reset':
      return manager.resetEnv(request.env_id, request.options);
    case 'step':
      return manager.stepEnv(request.env_id, request.choices || {}, request.options);
    case 'close_env':
      return manager.closeEnv(request.env_id);
    case 'agent_action':
      if (request.agent !== 'random' && request.agent !== 'heuristic') {
        throw new Error(`Unsupported agent ${request.agent}.`);
      }
      return manager.getAgentAction(request.env_id, request.player, request.agent);
    case 'ping':
      return { pong: true };
    default:
      throw new Error(`Unknown RPC type ${(request as { type?: string }).type || 'unknown'}.`);
  }
}

async function handleRequest(request: RPCRequest): Promise<unknown> {
  if (request.type !== 'batch') {
    return handleSingleRequest(request);
  }

  const responses = [];
  for (const [index, subrequest] of request.requests.entries()) {
    const startedAt = performance.now();
    const envId = resolveEnvId(subrequest);
    const finishSubrequestTrace = beginTrace(
      'subrequest',
      traceRpc
        ? {
            batch_id: request.id,
            index,
            ...summarizeRequest(subrequest),
            env: envId ? manager.describeEnv(envId) : null,
          }
        : {},
    );
    try {
      const result = await handleSingleRequest(subrequest);
      finishSubrequestTrace(true, { result: summarizeResult(result) });
      responses.push({
        id: subrequest.id,
        ok: true,
        result,
        meta: {
          request_type: subrequest.type,
          env_id: resolveEnvId(subrequest, result),
          queue_wait_ms: 0,
          server_elapsed_ms: Number((performance.now() - startedAt).toFixed(3)),
        },
      });
    } catch (error) {
      finishSubrequestTrace(false, { error: (error as Error).message });
      responses.push({
        id: subrequest.id,
        ok: false,
        error: {
          message: (error as Error).message,
        },
        meta: {
          request_type: subrequest.type,
          env_id: resolveEnvId(subrequest),
          queue_wait_ms: 0,
          server_elapsed_ms: Number((performance.now() - startedAt).toFixed(3)),
        },
      });
    }
  }

  return { responses };
}

const rl = readline.createInterface({
  input: process.stdin,
  crlfDelay: Infinity,
});

let queue = Promise.resolve();

rl.on('line', (line) => {
  const trimmed = line.trim();
  if (!trimmed) {
    return;
  }

  const enqueuedAt = performance.now();
  queue = queue.then(async () => {
    let request: RPCRequest;
    try {
      request = JSON.parse(trimmed) as RPCRequest;
    } catch (error) {
      writeResponse({
        id: null,
        ok: false,
        error: {
          message: `Invalid JSON: ${(error as Error).message}`,
        },
      });
      return;
    }

    const startedAt = performance.now();
    const queueWaitMs = startedAt - enqueuedAt;
    const finishRequestTrace = beginTrace(
      'request',
      traceRpc
        ? {
            ...summarizeRequest(request),
            queue_wait_ms: Number(queueWaitMs.toFixed(3)),
            memory: memorySnapshot(),
            manager: managerSnapshot(),
          }
        : {},
    );
    try {
      const result = await handleRequest(request);
      const serverElapsedMs = performance.now() - startedAt;
      finishRequestTrace(true, { result: summarizeResult(result) });
      writeResponse({
        id: request.id,
        ok: true,
        result,
        meta: {
          request_type: request.type,
          env_id: request.type === 'batch' ? null : resolveEnvId(request, result),
          queue_wait_ms: Number(queueWaitMs.toFixed(3)),
          server_elapsed_ms: Number(serverElapsedMs.toFixed(3)),
        },
      });
    } catch (error) {
      const serverElapsedMs = performance.now() - startedAt;
      finishRequestTrace(false, { error: (error as Error).message });
      writeResponse({
        id: request.id,
        ok: false,
        error: {
          message: (error as Error).message,
        },
        meta: {
          request_type: request.type,
          env_id: request.type === 'batch' ? null : resolveEnvId(request),
          queue_wait_ms: Number(queueWaitMs.toFixed(3)),
          server_elapsed_ms: Number(serverElapsedMs.toFixed(3)),
        },
      });
    }
  }).catch((error) => {
    writeResponse({
      id: null,
      ok: false,
      error: {
        message: (error as Error).message,
      },
    });
  });
});

async function shutdown(): Promise<void> {
  await manager.closeAll();
  rl.close();
}

process.on('SIGINT', () => {
  void shutdown().finally(() => process.exit(0));
});

process.on('SIGTERM', () => {
  void shutdown().finally(() => process.exit(0));
});
