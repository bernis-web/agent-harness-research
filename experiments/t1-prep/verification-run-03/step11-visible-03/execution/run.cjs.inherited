'use strict';
const fs=require('fs'),path=require('path');
const OUT=path.resolve(__dirname,'../evidence');
process.env.T1_OUT=OUT;process.env.T1_REFERENCE='D:/projects/agent-harness-research/experiments/t1-prep/reference/mindmap.html';process.env.T1_PLAYWRIGHT='D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core';
let t,closing;
async function close(){if(closing)return closing;closing=(async()=>{let r={ownedContextCloseCompleted:false,at:new Date().toISOString()};try{if(t)Object.assign(r,await t.close());else r.reason='harness not returned';}catch(e){r.error=String(e);process.exitCode=1;}fs.writeFileSync(path.join(OUT,'cleanup.json'),JSON.stringify(r,null,2));})();return closing;}
const timer=setTimeout(async()=>{fs.writeFileSync(path.join(OUT,'timeout.json'),JSON.stringify({timeoutSeconds:90}));await close();process.exit(124);},90000);
(async()=>{try{t=await require('./harness.cjs').createHarness();const r=await require('./step11.cjs')(t,OUT);console.log(JSON.stringify({status:r.status,classification:r.classification}));}catch(e){fs.writeFileSync(path.join(OUT,'execution-error.json'),JSON.stringify({classification:'BLOCKED_DRIVER',name:e.name,message:e.message}));process.exitCode=1;}finally{clearTimeout(timer);await close();}})();
