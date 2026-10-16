const ts = require('/private/tmp/neural-showdown-native11-prompt38/sim-core/node_modules/typescript');
const root = '/private/tmp/neural-showdown-native11-prompt38/sim-core';
const config = ts.readConfigFile(root + '/tsconfig.json', ts.sys.readFile);
const options = ts.parseJsonConfigFileContent(config.config, ts.sys, root).options;
options.typeRoots = [root + '/node_modules/@types'];
const files = [root + '/src/owner_identity_events.ts', root + '/tests/owner_identity_events.test.ts'];
const program = ts.createProgram(files, options);
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length) { console.log(ts.formatDiagnosticsWithColorAndContext(diagnostics, {getCanonicalFileName:x=>x,getCurrentDirectory:()=>root,getNewLine:()=> '\n'})); process.exit(2); }
for (const file of files) { const result=program.emit(program.getSourceFile(file)); if(result.emitSkipped) process.exit(2); }
console.log('Strict changed-module/test typecheck and exact emit passed; no full rebuild.');
