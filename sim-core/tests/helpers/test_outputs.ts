import {mkdtempSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {after} from 'node:test';
const directory=mkdtempSync(path.join(tmpdir(),'neural-test-'));
after(()=>rmSync(directory,{recursive:true,force:true}));
export const testOutput=(name:string):string=>path.join(directory,name);
