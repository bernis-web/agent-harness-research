'use strict';
const fs=require('fs');
process.env.T1_PLAYWRIGHT='D:/projects/npm-cache/_npx/cbf1b8a072280925/node_modules/playwright-core';
process.env.T1_REFERENCE="D:/projects/agent-harness-research/experiments/t1-prep/reference/mindmap.html";
process.env.T1_OUT="D:/projects/agent-harness-research/experiments/t1-prep/verification-run-03/public-batch-01";
let t; const timer=setTimeout(async()=>{fs.writeFileSync(process.env.T1_OUT+'/execution-timeout.json',JSON.stringify({timeout_seconds:300}));if(t)await t.close();process.exit(124);},300000);
(async()=>{try{t=await require('./harness.cjs').createHarness();await require('./public-chain.cjs')(t);await require('./fragments.cjs')(t);console.log('BATCH_FINISHED');}catch(e){console.error(e.stack);fs.writeFileSync(process.env.T1_OUT+'/execution-error.json',JSON.stringify({name:e.name,message:e.message,stack:e.stack},null,2));process.exitCode=1;}finally{clearTimeout(timer);if(t)await t.close();}})();
