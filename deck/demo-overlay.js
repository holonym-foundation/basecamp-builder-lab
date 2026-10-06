// Run the same browser lesson inside the presentation; no shell access or wallet calls.
(()=>{
 const overlay=document.createElement('div');overlay.id='workshop-demo';overlay.hidden=true;
 overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');overlay.setAttribute('aria-labelledby','demo-heading');
 overlay.innerHTML='<header><strong id="demo-heading">Guided build · follow with me</strong><button type="button" id="demo-close">Back to slides</button></header><iframe title="Executable workshop walkthrough" allow="clipboard-write" referrerpolicy="strict-origin-when-cross-origin"></iframe>';
 const style=document.createElement('style');style.textContent='#workshop-demo{position:fixed;inset:0;z-index:10000;background:#080809;display:flex;flex-direction:column;color:#f4f2ef;font:18px system-ui}#workshop-demo[hidden]{display:none}#workshop-demo header{height:68px;flex:none;display:flex;align-items:center;justify-content:space-between;padding:12px 24px;border-bottom:1px solid #353536;gap:16px}#workshop-demo button{background:#132824;color:#f4f2ef;border:1px solid #2ed0bd;border-radius:10px;padding:10px 18px;font:inherit;cursor:pointer}#workshop-demo button:focus-visible{outline:3px solid white;outline-offset:3px}#workshop-demo iframe{width:100%;flex:1;border:0;background:#080809}.workshop-run{cursor:pointer}.workshop-actions{flex-wrap:wrap;max-width:1664px}';
 document.head.append(style);document.body.append(overlay);
 const frame=overlay.querySelector('iframe'),close=overlay.querySelector('button');let previous=null,selected=null,complete=false;
 function hide(){overlay.hidden=true;window.__workshopDemoOpen=false;document.querySelector('#app').inert=false;previous?.focus();if(complete)location.hash='s19';}
 close.onclick=hide;
 document.addEventListener('keydown',e=>{if(!overlay.hidden){if(e.key==='Escape'){hide();e.preventDefault();}e.stopImmediatePropagation();}},false);
 window.addEventListener('message',e=>{if(e.source!==frame.contentWindow||e.origin!==location.origin)return;if(e.data==='workshop-demo-close')hide();if(e.data==='workshop-demo-complete'){complete=true;close.textContent='Continue: your turn';}if(e.data==='workshop-demo-reset'){complete=false;close.textContent='Back to slide '+(Number(previous?.closest('.slide')?.dataset.idx)+1);}});
 for(const id of ['s13','s15','s16','s17','s20']){
  const slide=document.querySelector('#slide-'+id);if(!slide)continue;
  let nav=slide.querySelector('.workshop-actions');if(!nav){nav=document.createElement('nav');nav.className='workshop-actions';slide.append(nav);}
  for(const recipe of ['rebalancer','guardian']){
   const b=document.createElement('button');b.type='button';b.className='workshop-link workshop-run';b.textContent='Run '+(recipe==='rebalancer'?'Rebalancer':'Guardian');
   for(const type of ['click','keydown'])b.addEventListener(type,e=>e.stopPropagation());
   b.addEventListener('click',()=>{previous=b;window.__workshopDemoOpen=true;document.querySelector('#app').inert=true;overlay.hidden=false;if(selected!==recipe)complete=false;close.textContent=complete?'Continue: your turn':'Back to slide '+(Number(slide.dataset.idx)+1);if(selected!==recipe){frame.src=new URL('../build.html?present=1#'+recipe,location.href).href;selected=recipe;}close.focus();});nav.prepend(b);
  }
 }
})();
