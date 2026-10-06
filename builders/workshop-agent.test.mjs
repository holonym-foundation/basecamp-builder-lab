import test from 'node:test';
import assert from 'node:assert/strict';
import {rebalance, guardian, run} from './workshop-agent.mjs';
test('balanced portfolio holds; targets change the proposal direction',()=>{
 assert.equal(rebalance(1).decision,'HOLD');
 assert.equal(rebalance(1,.7).decision,'PROPOSE_BUY_SUI');
 assert.equal(rebalance(1,.3).decision,'PROPOSE_SELL_SUI');
 assert.ok(Math.abs(rebalance(1,.7).proposedValueUsdc-4)<1e-8);
});
test('bad numerical inputs stop instead of making proposals',()=>{
 for(const v of [NaN,Infinity,-1,0])assert.throws(()=>rebalance(v));
 assert.throws(()=>rebalance(1,1.1));assert.throws(()=>guardian('at-risk',NaN));
});
test('Guardian respects cap without claiming restored target',()=>{
 const x=guardian();assert.equal(x.proposedRepayUsd,10);assert.equal(x.targetRestoredWithinCap,false);
 assert.ok(x.neededRepayUsd>10);assert.equal(x.decision,'PROPOSE_REPAY');
});
test('healthy, debt-free and unknown are distinct non-action outcomes',()=>{
 assert.equal(guardian('healthy').decision,'OBSERVE');
 assert.equal(guardian('no-debt').decision,'NO_DEBT');
 assert.equal(guardian('unknown').decision,'STOP_UNKNOWN_DATA');
 assert.throws(()=>guardian('missing'));
});
test('Guardian offline loop never makes a network call',async()=>{
 const old=globalThis.fetch;globalThis.fetch=()=>{throw Error('unexpected network')};
 try{assert.equal((await run('guardian')).source,'SIMULATED lending scenario');}finally{globalThis.fetch=old;}
});
