'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const R=path.resolve(__dirname,'..');
const files=[];
function flat(dir){for(const e of fs.readdirSync(path.join(R,dir),{withFileTypes:true})){if(e.isFile())files.push(path.posix.join(dir,e.name));}}
// Enumerate only explicit new evidence directories; NEVER recurse into browser runtime.
flat('execution');flat('preflight');flat('attempt-01');flat('attempt-01/evidence');flat('attempt-01/evidence/fixtures');flat('preflight-recheck');flat('preflight-recheck/fixtures');
for(const d of ['model-harness','model-cases','model-harness-review','model-cases-review','model-audit','model-audit-small'])flat(d);
for(const e of fs.readdirSync(R,{withFileTypes:true}))if(e.isFile() && !['protected-before.json','evidence-index.json','evidence-index.sha256','evidence-index-validation.json'].includes(e.name))files.push(e.name);
const uniq=[...new Set(files)].sort();
const records=uniq.map(f=>{const b=fs.readFileSync(path.join(R,f));return {path:f,bytes:b.length,sha256:crypto.createHash('sha256').update(b).digest('hex')}});
const data={at:new Date().toISOString(),root:R,scope:'Explicit current-run evidence directories, flat enumeration only. No browser profile/home/temp or historical data.',excluded:['protected-before.json (initial erroneous broad manifest preserved untouched; not reread)','all profile/home/temp directories','index and its validation/self hash'],files:records};
fs.writeFileSync(path.join(R,'evidence-index.json'),JSON.stringify(data,null,2));
const digest=crypto.createHash('sha256').update(fs.readFileSync(path.join(R,'evidence-index.json'))).digest('hex');
fs.writeFileSync(path.join(R,'evidence-index.sha256'),digest+'  evidence-index.json\n');
const mismatches=records.filter(r=>crypto.createHash('sha256').update(fs.readFileSync(path.join(R,r.path))).digest('hex')!==r.sha256).map(r=>r.path);
fs.writeFileSync(path.join(R,'evidence-index-validation.json'),JSON.stringify({at:new Date().toISOString(),checked:records.length,mismatches,passed:!mismatches.length},null,2));
console.log(JSON.stringify({indexed:records.length,mismatches:mismatches.length}));
if(mismatches.length)process.exitCode=1;
