'use strict';
const fs = require('node:fs/promises');
const {performance} = require('node:perf_hooks');
const transient = new Set(['EBUSY', 'EPERM', 'EACCES']);
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

// libuv opens Windows files with FILE_SHARE_READ | FILE_SHARE_WRITE |
// FILE_SHARE_DELETE. An existing non-sharing handle can still deny the open.
async function retry(operation, {notify = () => {}, windowMs = 60000, delay = sleep} = {}) {
  let since, attempts = 0;
  for (;;) {
    try {
      const result = await operation();
      if (since !== undefined) notify({status:'running', write_recovered:true});
      return result;
    } catch (error) {
      if (!transient.has(error.code)) throw error;
      since ??= performance.now();
      notify({status:'blocked-write', error:error.code, path:error.path,
        write_attempts:++attempts, blocked_ms:Math.round(performance.now()-since)});
      // After the first minute, remain paused and retry at the capped interval.
      await delay(Math.min(windowMs, 5000, 100 * 2 ** Math.min(attempts-1, 6)));
    }
  }
}

async function atomicWrite(file, text, options) {
  const temporary = file + '.tmp-' + process.pid;
  let handle;
  try {
    handle = await retry(() => fs.open(temporary, 'w'), options);
    const bytes=Buffer.from(text);let offset=0;
    while(offset<bytes.length){const result=await retry(()=>handle.write(bytes,offset,bytes.length-offset,offset),options);if(!result.bytesWritten)throw new Error('Atomic write made no progress');offset+=result.bytesWritten;}
    await retry(() => handle.sync(), options);
    await handle.close(); handle = undefined;
    await retry(() => fs.rename(temporary, file), options);
  } finally {
    await handle?.close();
    await fs.unlink(temporary).catch(error => {if(error.code !== 'ENOENT') throw error;});
  }
}

/** One writer, fsynced complete lines. Recover only a torn final line on resume. */
class Journal {
  constructor(file, options = {}) {this.file=file; this.options=options; this.tail=Promise.resolve();}
  async open(resume) {
    this.handle = await retry(async () => {try{return await fs.open(this.file,resume?'r+':'w+');}catch(error){if(!resume||error.code!=='ENOENT')throw error;return fs.open(this.file,'wx+');}},this.options);
    try {
    const bytes = await retry(() => this.handle.readFile(), this.options);
    const end = bytes.lastIndexOf(10) + 1;
    this.offset=end;
    const complete = bytes.subarray(0,end).toString('utf8');
    const rows = complete.split('\n').filter(Boolean).map(JSON.parse);
    if(end !== bytes.length) {
      await retry(() => this.handle.truncate(end), this.options);
      await retry(()=>this.handle.sync(),this.options);
    }
    return rows;
    } catch(error){await this.handle.close();this.handle=undefined;throw error;}
  }
  append(row) {
    const bytes = Buffer.from(JSON.stringify(row)+'\n');
    const operation = async () => {
      let offset=0;
      while(offset<bytes.length) {
        const result=await retry(() => this.handle.write(bytes,offset,bytes.length-offset,this.offset+offset),this.options);
        if(!result.bytesWritten)throw new Error('Journal write made no progress');
        offset+=result.bytesWritten;
      }
      await retry(() => this.handle.sync(),this.options);
      this.offset+=bytes.length;
    };
    const result=this.tail.then(operation); this.tail=result;
    return result;
  }
  async close() {try {await this.tail;} finally {await this.handle?.close();}}
}

/** A delayed tick invalidates all in-flight deadlines, including queued replies. */
class SuspensionClock {
  constructor({tickMs=1000,gapMs=15000,mono=()=>performance.now(),wall=Date.now}={}) {
    Object.assign(this,{tickMs,gapMs,mono,wall});this.previous={mono:mono(),wall:wall()};this.epoch=0;
  }
  sample() {
    const now={mono:this.mono(),wall:this.wall()},m=now.mono-this.previous.mono,w=now.wall-this.previous.wall;
    this.previous=now;
    if(m>this.gapMs || Math.abs(w-m)>this.gapMs) {this.epoch++;return true;}
    return false;
  }
}
function complete(summary){if(process.connected)process.send({type:'complete',summary},()=>process.disconnect());return summary;}
function failure(error){console.error(error);process.exitCode=1;if(process.connected)process.disconnect();}
module.exports={retry,atomicWrite,Journal,SuspensionClock,sleep,complete,failure};
