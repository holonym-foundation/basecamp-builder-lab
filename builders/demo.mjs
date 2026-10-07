import {run} from './workshop-agent.mjs';
const $=id=>document.getElementById(id);
const present=new URLSearchParams(location.search).get('present')==='1';
document.body.classList.toggle('present',present);
let recipe='rebalancer',stage=0,runs=[],busy=false,evidenceReviewed=false,finished=false;
const lessons={
  rebalancer:{name:'Sui Rebalancer',boundary:'Live Sui mainnet pool price; sample holdings of 10 SUI + 10 USDC. This proposes an allocation change, not a swap quote or execution.',command:'node workshop-agent.mjs rebalancer',edit:'Change the SUI target from 50% to 70%. A HOLD is a valid outcome. Each run reads again, so price can also change.',change:'node workshop-agent.mjs rebalancer --target 0.7'},
  guardian:{name:'Liquidation Guardian',boundary:'Simulated lending scenarios with a $10 action cap. This teaches risk decisions and missing-data handling; it does not monitor or repay a real loan.',command:'node workshop-agent.mjs guardian --scenario at-risk',edit:'Switch from at-risk to healthy, then unknown. Compare the decision and whether the cap would restore the target.',change:'node workshop-agent.mjs guardian --scenario healthy\nnode workshop-agent.mjs guardian --scenario unknown'}
};
const money=x=>typeof x==='number'?'$'+x.toFixed(2):'Unknown';
const percent=x=>(x*100).toFixed(1)+'%';
const readable={HOLD:'Hold allocation',PROPOSE_BUY_SUI:'Propose buying SUI',PROPOSE_SELL_SUI:'Propose selling SUI',STOP_UNKNOWN_DATA:'Stop: missing data',NO_DEBT:'No debt to repay',PROPOSE_REPAY:'Propose repayment',OBSERVE:'Observe: healthy'};
function paragraph(parent,label,value){const p=document.createElement('p');const strong=document.createElement('strong');strong.textContent=label+' ';p.append(strong,document.createTextNode(String(value)));parent.append(p);}
function drawResults(){
  $('results').replaceChildren();
  const visible=stage===0?runs.filter(r=>r.kind==='baseline'):stage===1?runs.filter(r=>r.kind==='baseline'||r.kind==='changed'):runs;
  for(const record of visible){const o=record.output,card=document.createElement('article');card.className='result';
    const label=document.createElement('div');label.className='label';label.textContent=record.kind==='baseline'?'Baseline':record.kind==='changed'?'Your changed setting':'Unknown-data check';
    const heading=document.createElement('h4');heading.textContent=readable[o.decision]||o.decision;card.append(label,heading);
    if(recipe==='rebalancer'){
      paragraph(card,'Inputs:', '10 sample SUI + 10 sample USDC; target '+percent(o.target)+', band '+percent(o.band));
      paragraph(card,'Live SUI price:',money(o.price));paragraph(card,'Current share:',percent(o.currentAllocation));paragraph(card,'Proposed value:',money(o.proposedValueUsdc));
      paragraph(card,'Source:', 'Sui mainnet · checkpoint '+o.checkpoint);
      paragraph(card,'Limit:','Sample holdings; no route, fees or slippage. No swap sent.');
    }else{
      paragraph(card,'Inputs:',o.scenario+' scenario; capacity '+money(o.liquidationCapacityUsd)+', weighted debt '+money(o.weightedDebtUsd)+', target '+o.target);
      paragraph(card,'Health factor:',o.healthFactor===undefined?'Unknown':o.healthFactor===null?'No debt':o.healthFactor.toFixed(2));
      if(o.proposedRepayUsd!==undefined){paragraph(card,'Proposed repayment:',money(o.proposedRepayUsd)+' / $10 cap');paragraph(card,'Target restored within cap:',o.targetRestoredWithinCap?'Yes, in this scenario':'No — human review needed');}
      paragraph(card,'Source:','Simulated lending scenario, not a live position');paragraph(card,'Limit:','Decision only. No loan opened or repayment sent.');
    }
    const details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='Inspect full output and settings';pre.textContent=JSON.stringify(record,null,2);details.append(summary,pre);card.append(details);$('results').append(card);
  }
}
function render(){
  $('step-label').textContent='Step '+(stage+1)+' of 5';
  const titles=['Run the baseline','Change one setting and run again','Compare the two decisions','Inspect the Sui evidence','Save your evidence and stop'];
  const descriptions=[recipe==='rebalancer'?'Start with a 50% SUI target and a 5-point band. Click once to read the pool and calculate a decision.':'Start with an at-risk scenario and a 1.3 health-factor target. Click once to calculate the capped repayment.',recipe==='rebalancer'?'The target is now 70%. Run again and compare it with the baseline. You can change the target or band before running.':'The scenario is now healthy. Run again and compare it with the at-risk baseline.','Explain what changed, which input caused it and what this decision cannot prove.'+(recipe==='guardian'?' Then optionally test missing data: the expected result is STOP_UNKNOWN_DATA.':' Price is sampled again on each run; changing prices can also affect the comparison.'),'Open the lab or receipt in a new tab, inspect it, then return here. A previous on-chain action is separate evidence from your current decision loop.','Download both runs, their settings and the evidence links as one JSON file. Each run has already stopped; no process is running in the background.'];
  $('stage-title').textContent=finished?'Evidence saved. Your run is complete.':titles[stage];$('stage-description').textContent=finished?'During 34–51 min, choose Start again and try your own setting. Keep the original evidence file to compare.':descriptions[stage];
  $('reb-controls').hidden=stage!==1||recipe!=='rebalancer';$('guard-controls').hidden=stage!==1||recipe!=='guardian';$('evidence').hidden=stage!==3;
  $('run').hidden=stage>1;$('run').textContent=stage===0?'Run baseline':'Run with changed setting';
  $('unknown').hidden=stage!==2||recipe!=='guardian';
  $('next').hidden=stage===4||(stage===0&&!runs.some(r=>r.kind==='baseline'))||(stage===1&&!runs.some(r=>r.kind==='changed'));
  $('next').textContent=['Change one setting','Compare results','Inspect evidence','I inspected the evidence · continue'][stage]||'Continue';
  $('save').hidden=stage!==4;$('save').textContent=finished?'Download evidence again':'Save evidence and finish';
  document.querySelectorAll('.progress li').forEach((li,i)=>{li.className=i===stage?'current':i<stage?'complete':'';if(i===stage)li.setAttribute('aria-current','step');else li.removeAttribute('aria-current');});
  const current=runs.filter(r=>r.output.explorer).at(-1);$('current-evidence').hidden=!current;if(current)$('current-evidence').href=current.output.explorer;
  drawResults();
}
function choose(name,updateHash=true){recipe=name;stage=0;runs=[];evidenceReviewed=false;finished=false;const l=lessons[name];$('name').textContent=l.name;$('boundary').textContent=l.boundary;$('commands').textContent='node --version  # use Node 24\n'+l.command;$('edit').textContent=l.edit;$('edit-command').textContent=l.change;$('target').value=70;$('band').value=5;$('scenario').value='healthy';$('hf').value=1.3;$('run-status').textContent='';$('execution').hidden=true;$('execution-log').replaceChildren();document.querySelectorAll('[data-recipe]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.recipe===name)));if(updateHash)history.replaceState(null,'',location.pathname+location.search+'#'+name);render();}
function logExecution(operation, detail) {
  const li=document.createElement('li'),time=document.createElement('time');
  time.dateTime=new Date().toISOString();time.textContent=new Date().toLocaleTimeString('en-GB',{hour12:false});
  li.append(time,document.createTextNode(operation+' — '+detail));$('execution-log').append(li);
}
function setBusy(value){busy=value;document.querySelectorAll('#lesson button,[data-recipe],#lesson input,#lesson select').forEach(b=>b.disabled=value);}
async function execute(kind){
  if(busy)return;
  let settings=recipe==='rebalancer'?{target:kind==='baseline'?.5:Number($('target').value)/100,band:kind==='baseline'?.05:Number($('band').value)/100}:{scenario:kind==='baseline'?'at-risk':kind==='unknown'?'unknown':$('scenario').value,target:kind==='baseline'?1.3:Number($('hf').value)};
  if(kind==='changed'){
    const inputs=recipe==='rebalancer'?[$('target'),$('band')]:[$('hf')];
    if(inputs.some(el=>!el.reportValidity()))return;
  }
  // Retrying a failed new read must not retain an older successful current run.
  runs=runs.filter(r=>r.kind!==kind);render();setBusy(true);$('execution').hidden=false;$('execution-log').replaceChildren();$('invocation').textContent='await run('+JSON.stringify(recipe)+', '+JSON.stringify(settings)+')';logExecution('Started',recipe==='rebalancer'?'Browser execution · live price read':'Browser execution · scenario calculation');$('run-status').textContent=recipe==='rebalancer'?'Reading Sui mainnet…':'Calculating the labelled scenario…';
  try{const output=await run(recipe,{...settings,onEvent:event=>logExecution(event.operation,event.detail)});logExecution('Returned',output.decision+' · no transaction submitted');runs.push({kind,settings,completedAt:new Date().toISOString(),output});$('run-status').textContent=kind==='unknown'?'Missing-data check complete. The decision stops without proposing an action.':'Run complete. '+(kind==='baseline'?'Continue to change one setting.':'Continue to compare the results.');}
  catch(e){logExecution('Failed',e.message);$('run-status').textContent='Read stopped: '+e.message+'. No new result was recorded. Retry this read; Guardian scenarios also work without a chain connection.';}
  finally{setBusy(false);render();}
}
if(present)window.addEventListener('keydown',event=>{if(event.key==='Escape'){event.preventDefault();window.parent.postMessage('workshop-demo-close',location.origin);}});
for(const id of ['target','band','scenario','hf'])$(id).addEventListener('input',()=>{if(stage===1&&!busy){runs=runs.filter(record=>record.kind!=='changed');$('run-status').textContent='Setting changed. Run again to record this choice.';render();}});
$('run').onclick=()=>execute(stage===0?'baseline':'changed');$('unknown').onclick=()=>execute('unknown');
$('next').onclick=()=>{if(busy)return;if(stage===3)evidenceReviewed=true;stage=Math.min(4,stage+1);$('run-status').textContent='';render();$('stage-title').scrollIntoView({block:'nearest',behavior:'smooth'});};
$('reset').onclick=()=>{if(!busy){choose(recipe,false);if(present&&window.parent!==window)window.parent.postMessage('workshop-demo-reset',location.origin);}};
document.querySelectorAll('[data-recipe]').forEach(b=>b.onclick=()=>{if(!busy){choose(b.dataset.recipe);$('lesson').scrollIntoView({behavior:'smooth'});}});
window.addEventListener('hashchange',()=>{if(!busy)choose(location.hash==='#guardian'?'guardian':'rebalancer',false);});
$('copy').onclick=async()=>{try{await navigator.clipboard.writeText($('commands').textContent);$('copy').textContent='Copied';}catch{$('copy').textContent='Select and copy the commands above';}};
$('save').onclick=()=>{
  if(!runs.some(r=>r.kind==='baseline')||!runs.some(r=>r.kind==='changed'))return;
  const evidence={lesson:lessons[recipe].name,savedAt:new Date().toISOString(),mode:'read-only workshop decision loop',transactionsSubmitted:0,evidenceReviewedByParticipant:evidenceReviewed,chainEvidence:{lab:new URL('../index.html',import.meta.url).href,previousPoolTransaction:new URL('../index.html?tx=Fvdxzog5tBYp3D4gg85PJxd6j4embkbcKyMKowhYnFV8',import.meta.url).href,recordedGuardianTransaction:'https://suivision.xyz/txblock/4Fpevq1op4CiaQT79ZSvrQE8Jcc8reh8zvp5kjCPgiMG',relationship:'These previous transactions are separate from the workshop decision runs.'},runs};
  const url=URL.createObjectURL(new Blob([JSON.stringify(evidence,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download=recipe+'-workshop-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);finished=true;render();if(present)window.parent.postMessage('workshop-demo-complete',location.origin);
};
for(const [slug,name]of [['dca-accumulator','DCA Accumulator'],['gem-hunter','Gem Hunter'],['farm','Airdrop Farmer'],['claim-watch','Claim Watch'],['security-guard','Security Guard'],['gas-claims-reminder','Gas & Claims'],['privacy-guard','Privacy Guard']]){const li=document.createElement('li'),a=document.createElement('a');a.textContent=name;a.href='https://github.com/holonym-foundation/agent-exchange/tree/95ce4629f060717b6c243ea2acb97a01d3047303/skills/'+slug;li.append(a);$('skills').append(li);}
choose(location.hash==='#guardian'?'guardian':'rebalancer',false);
setBusy(false); // Enable controls only after the module and selected recipe are ready.
