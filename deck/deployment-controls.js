(()=>{
const endpoint='http://127.0.0.1:8788/';
const steps={prepare:'Prepare runtime',configure:'Configure',deploy:'Deploy',run:'Start / Run',inspect:'Inspect output',modify:'Modify strategy',stop:'Stop + save'};
const slides={s13:['prepare','configure','deploy','run','inspect','modify','stop'],s15:['prepare','configure','deploy'],s16:['run','inspect'],s17:['inspect'],s18:['modify','run'],s19:['stop']};
for(const [id,keys]of Object.entries(slides)){const slide=document.querySelector('#slide-'+id);if(!slide)continue;const nav=document.createElement('nav');nav.className='workshop-actions';nav.setAttribute('aria-label','Live Rebalancer deployment steps');for(const key of keys){const a=document.createElement('a');a.className='workshop-link';a.href=endpoint+'#'+key;a.target='rebalancer-runtime';a.rel='noopener';a.textContent=steps[key]+' ↗';a.addEventListener('click',e=>e.stopPropagation());a.addEventListener('keydown',e=>e.stopPropagation());nav.append(a);}slide.querySelector('.workshop-actions')?.remove();slide.append(nav);}
const style=document.createElement('style');style.textContent='.workshop-actions{flex-wrap:wrap;max-width:1664px}#slide-s13 .workshop-link{font-size:25px;padding:14px 20px}#slide-s13 .workshop-actions{bottom:140px}';document.head.append(style);
})();
