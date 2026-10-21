import {mkdirSync, mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {after} from 'node:test';
const shared=process.env.NEURAL_TEST_OUTPUT_DIR;
const directory=shared ? path.resolve(shared) : mkdtempSync(path.join(tmpdir(),'neural-test-'));
mkdirSync(directory,{recursive:true});
if (!shared) after(()=>rmSync(directory,{recursive:true,force:true}));
export const testOutput=(name:string):string=>path.join(directory,name);
