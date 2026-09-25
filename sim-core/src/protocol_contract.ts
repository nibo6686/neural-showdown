import fs from 'node:fs';
import path from 'node:path';

interface SharedProtocolContract {
  schema_version: string;
  supported_commands: string[];
  recognized_unsupported_commands: Array<{ token: string; kind: string; reason: string }>;
}

function loadProtocolContract(): SharedProtocolContract {
  let directory = __dirname;
  for (let depth = 0; depth < 8; depth += 1) {
    const candidate = path.join(directory, 'trainer', 'src', 'neural', 'protocol_contract.json');
    if (fs.existsSync(candidate)) return JSON.parse(fs.readFileSync(candidate, 'utf8')) as SharedProtocolContract;
    const parent = path.dirname(directory);
    if (parent === directory) break;
    directory = parent;
  }
  throw new Error('Shared trainer/src/neural/protocol_contract.json was not found.');
}

export const PROTOCOL_CONTRACT = loadProtocolContract();
export const SUPPORTED_RAW_COMMANDS = new Set(PROTOCOL_CONTRACT.supported_commands);
export const RECOGNIZED_UNSUPPORTED_RAW_COMMANDS = new Map(
  PROTOCOL_CONTRACT.recognized_unsupported_commands.map((entry) => [entry.token, entry]),
);

if (SUPPORTED_RAW_COMMANDS.size !== PROTOCOL_CONTRACT.supported_commands.length
  || PROTOCOL_CONTRACT.recognized_unsupported_commands.some((entry) => SUPPORTED_RAW_COMMANDS.has(entry.token))) {
  throw new Error('Shared protocol contract contains duplicate or conflicting command dispositions.');
}
