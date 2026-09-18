'use strict';
const fs=require('fs'),path=require('path');
const OUT=process.env.T1_OUT;
if(!OUT || !path.resolve(OUT).startsWith(path.resolve("D:/projects/agent-harness-research/experiments/t1-prep/verification-hidden-01")+path.sep)) throw new Error('outside authorized root');
let t,h,closing; const started=new Date().toISOString();
const save=(name,x)=>fs.writeFileSync(path.join(OUT,name),JSON.stringify(x,null,2));
async function close(){if(!closing)closing=(async()=>{if(t)await t.close();else if(h?.emergencyClose)await h.emergencyClose();})();return closing;}
const timer=setTimeout(async()=>{save('timeout.json',{timeoutSeconds:300});try{await close();}catch(e){save('cleanup-error.json',{message:e.message});}process.exit(124)},300000);
(async()=>{try{h=require('./harness.cjs');t=await h.createHarness();await require('./cases.cjs')(t,OUT);save('execution-result.json',{status:'FINISHED',started,ended:new Date().toISOString()});console.log('HIDDEN_EXECUTION_FINISHED');}catch(e){save('execution-error.json',{name:e.name,message:e.message,stack:e.stack,started,ended:new Date().toISOString()});process.exitCode=1;console.error(e.stack);}finally{clearTimeout(timer);try{await close()}catch(e){save('cleanup-error.json',{message:e.message});process.exitCode=1;}}})();
