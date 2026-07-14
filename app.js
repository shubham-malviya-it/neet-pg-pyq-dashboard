const D = window.NEET_DATA;
const SECTIONS = D.sections;
const SUBJECTS = D.subjects;
const ALL_YEARS = D.meta.generated_years;               // every parsed paper
const YEARS = D.meta.stats_years || D.meta.generated_years; // classifiable papers only
const SEC_OF = {}; Object.entries(SECTIONS).forEach(([sec,subs])=>subs.forEach(s=>SEC_OF[s]=sec));
const SEC_KEYS = Object.keys(SECTIONS);
const SEC_VAR = {"Pre-Clinical":"--sec-pre","Para-Clinical":"--sec-para","Clinical":"--sec-clin"};
const cssv = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const secColor = sec => cssv(SEC_VAR[sec]);
const debounce=(fn,wait=180)=>{let timer;return (...args)=>{clearTimeout(timer);timer=setTimeout(()=>fn(...args),wait);};};
const VIEW_NAMES=['overview','subjects','trends','questions','papers','syllabus','predictions'];

// curated high-yield topics (authoritative full list = official bulletin)
const TOPICS = {
 "Anatomy":"Embryology (germ layers, pharyngeal arches, neural crest), gross anatomy of limbs & thorax, cranial nerves & foramina, histology of epithelia and glands.",
 "Physiology":"Membrane & action potentials, cardiac cycle & output, renal clearance/GFR, acid–base and respiratory physiology, endocrine feedback loops.",
 "Biochemistry":"Enzyme kinetics & inhibition, glycolysis/Krebs/HMP shunt, urea cycle, vitamin & cofactor deficiencies, molecular biology (DNA/RNA, mutations).",
 "Pathology":"General pathology (necrosis, inflammation, neoplasia), haematology, tumour markers & staining, systemic organ pathology — consistently high-yield.",
 "Pharmacology":"Mechanisms & receptors, autonomic drugs, antimicrobials, diuretics & cardiovascular drugs, pharmacokinetics, adverse effects & antidotes.",
 "Microbiology":"Bacterial/viral/fungal/parasite identification, Gram stain & culture media, immunology basics, vaccines and the national immunization schedule.",
 "Forensic Medicine":"Thanatology (rigor/livor mortis, PM changes), asphyxial deaths, common poisons, medico-legal reports, relevant sections of law.",
 "PSM":"Epidemiology & study designs, sensitivity/specificity & screening, biostatistics, national health programmes, immunization & nutrition.",
 "Medicine":"Cardiology, endocrinology (diabetes/thyroid), nephrology, neurology, infectious disease and autoimmune conditions — the largest clinical block.",
 "Surgery":"Acute abdomen, hernia, hepatobiliary & GI surgery, trauma & burns, surgical oncology, pre/post-operative management.",
 "Obstetrics & Gynaecology":"Antenatal care, labour & partograph, obstetric emergencies (pre-eclampsia, PPH), contraception, menstrual disorders, gynae-oncology.",
 "Paediatrics":"Neonatology & APGAR, growth & development milestones, immunization, nutrition (kwashiorkor/marasmus), common congenital disorders.",
 "Orthopaedics":"Fracture patterns & management, joint dislocations, avascular necrosis, bone tumours, spine, plaster & orthopaedic implants.",
 "Radiology":"Modalities (X-ray/CT/MRI/USG), contrast studies, classic imaging signs, safety and appropriate first-line imaging.",
 "Anaesthesia":"Neuromuscular blockers & muscle relaxants, airway management & intubation, inhalational agents/MAC, spinal anaesthesia, complications.",
 "Psychiatry":"Mood & psychotic disorders, anxiety & OCD, DSM criteria, psychopharmacology (antidepressants/antipsychotics), suicide risk.",
 "Dermatology":"Papulosquamous disorders (psoriasis, lichen planus), vesiculobullous (pemphigus), infections, leprosy, skin malignancies.",
 "Ophthalmology":"Refractive errors, cataract & glaucoma, retina (diabetic/hypertensive), red eye & uveitis, optic nerve pathways.",
 "ENT":"Otology (otitis media, hearing loss, vertigo), rhinology & sinusitis, laryngology, epistaxis and head-&-neck basics."
};

/* ---------- theme ---------- */
const themeBtn = document.getElementById('theme');
function applyTheme(t){ document.documentElement.setAttribute('data-theme',t); localStorage.setItem('neet-theme',t);
  themeBtn.setAttribute('aria-label',`Switch to ${t==='dark'?'light':'dark'} theme`); renderAll(); }
themeBtn.onclick = ()=>{ const cur=document.documentElement.getAttribute('data-theme')
    || (matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');
  applyTheme(cur==='dark'?'light':'dark'); };
(function(){ const s=localStorage.getItem('neet-theme')||'dark'; document.documentElement.setAttribute('data-theme',s);
  themeBtn.setAttribute('aria-label',`Switch to ${s==='dark'?'light':'dark'} theme`); })();

/* ---------- tabs ---------- */
const tabs=document.getElementById('tabs'), menuBtn=document.getElementById('menu');
const tabButtons=[...tabs.querySelectorAll('button')];
tabButtons.forEach((button,index)=>{const view=button.dataset.v, panel=document.querySelector(`[data-view="${view}"]`);
  button.id=`tab-${view}`; button.setAttribute('role','tab'); button.setAttribute('aria-controls',`panel-${view}`);
  button.tabIndex=index? -1:0; panel.id=`panel-${view}`; panel.setAttribute('role','tabpanel'); panel.setAttribute('aria-labelledby',button.id);
});
document.querySelectorAll('.seg button').forEach(button=>{button.type='button';button.setAttribute('aria-pressed',String(button.classList.contains('on')));});
tabs.addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return;
  navigateTo(b.dataset.v);
});
tabs.addEventListener('keydown',e=>{const current=tabButtons.indexOf(document.activeElement);if(current<0)return;
  let next;if(e.key==='ArrowRight'||e.key==='ArrowDown')next=(current+1)%tabButtons.length;
  if(e.key==='ArrowLeft'||e.key==='ArrowUp')next=(current-1+tabButtons.length)%tabButtons.length;
  if(e.key==='Home')next=0;if(e.key==='End')next=tabButtons.length-1;if(next===undefined)return;
  e.preventDefault();tabButtons[next].focus();navigateTo(tabButtons[next].dataset.v);
});
menuBtn.addEventListener('click',()=>setMenu(!tabs.classList.contains('open')));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&tabs.classList.contains('open')){setMenu(false);menuBtn.focus();}});
document.addEventListener('click',e=>{if(tabs.classList.contains('open')&&!e.target.closest('header'))setMenu(false);});
function setMenu(open){tabs.classList.toggle('open',open);menuBtn.setAttribute('aria-expanded',String(open));
  menuBtn.setAttribute('aria-label',open?'Close navigation':'Open navigation');}
function readRoute(){
  const [view,query='']=location.hash.slice(1).split('?');
  return {view:VIEW_NAMES.includes(view)?view:'overview',params:new URLSearchParams(query)};
}
function navigateTo(v){if(!VIEW_NAMES.includes(v))v='overview';
  if(readRoute().view!==v||location.hash!==`#${v}`)location.hash=v;else showView(v,true);}
function showView(v,scroll=false){if(!VIEW_NAMES.includes(v))v='overview';
  tabButtons.forEach(x=>{const on=x.dataset.v===v;x.classList.toggle('on',on);x.setAttribute('aria-selected',String(on));x.tabIndex=on?0:-1;});
  document.querySelectorAll('.view').forEach(el=>{const on=el.dataset.view===v;el.classList.toggle('on',on);el.hidden=!on;});
  setMenu(false); if(v==='questions')loadQuestions().then(applyQuestionRoute); if(scroll)window.scrollTo({top:0,behavior:'smooth'});
}
function setPressed(selector,active){document.querySelectorAll(selector).forEach(button=>{const on=button===active;button.classList.toggle('on',on);button.setAttribute('aria-pressed',String(on));});}
addEventListener('hashchange',()=>showView(readRoute().view,true));

/* ---------- derived data ---------- */
const RECENT_YEARS = YEARS.slice(-3);           // 3 most recent classifiable papers
const EARLIER_YEARS = YEARS.slice(0,-3);
function totalsFor(years){ // sorted [{s,n,sec}] over the given years
  const o={}; SUBJECTS.forEach(s=>o[s]=0);
  years.forEach(y=>SUBJECTS.forEach(s=>o[s]+=D.years[y].counts[s]));
  return SUBJECTS.map(s=>({s,n:o[s],sec:SEC_OF[s]})).sort((a,b)=>b.n-a.n);
}
const subjTotals = totalsFor(YEARS);            // all-years ranking
const subjRecent = totalsFor(RECENT_YEARS);
const classifiedTotal = subjTotals.reduce((a,b)=>a+b.n,0);
const recentTotal = subjRecent.reduce((a,b)=>a+b.n,0);
const rankOf = {}; subjTotals.forEach((d,i)=>rankOf[d.s]=i+1);
function sectionCountsByYear(){ // {year:{sec:count}}
  const o={}; YEARS.forEach(y=>{ o[y]={}; SEC_KEYS.forEach(s=>o[y][s]=0);
    const c=D.years[y].counts; SUBJECTS.forEach(su=>{ o[y][SEC_OF[su]]+=c[su]; }); });
  return o;
}
function subjectByYear(sub){ return YEARS.map(y=>({y, n:D.years[y].counts[sub]})); }
function subjectStats(sub){
  const arr=subjectByYear(sub);
  const total=D.subject_totals[sub];
  const nz=arr.filter(d=>d.n>0);
  const peak=arr.reduce((a,b)=>b.n>a.n?b:a,arr[0]);
  const avg=total/arr.length;
  // recent-3 avg vs earlier avg -> direction
  const normalised=y=>{const total=SUBJECTS.reduce((sum,s)=>sum+D.years[y].counts[s],0);return total?200*D.years[y].counts[sub]/total:0;};
  const recAvg=RECENT_YEARS.reduce((a,y)=>a+normalised(y),0)/RECENT_YEARS.length;
  const earAvg=EARLIER_YEARS.reduce((a,y)=>a+normalised(y),0)/(EARLIER_YEARS.length||1);
  return {arr,total,appears:nz.length,peak,avg,recAvg,earAvg,
    share:100*total/classifiedTotal, rank:rankOf[sub]};
}

/* ---------- KPI ---------- */
function renderKPI(){
  const exam=new Date(D.meta.exam_date_2026+'T00:00:00');
  const days=Math.max(0,Math.ceil((exam-new Date())/86400000));
  const papers=ALL_YEARS.length;
  const el=document.getElementById('kpis');
  el.innerHTML=`
    <div class="kpi"><div class="n">${D.meta.grand_total_questions.toLocaleString()}</div><div class="l">Questions parsed</div><div class="sub">${classifiedTotal.toLocaleString()} subject-classified</div></div>
    <div class="kpi"><div class="n">${papers}</div><div class="l">Exam years covered</div><div class="sub">2010 – 2025</div></div>
    <div class="kpi"><div class="n">19</div><div class="l">MBBS subjects</div><div class="sub">3 curriculum blocks</div></div>
    <div class="kpi countdown"><div class="n">${days}</div><div class="l">Days to NEET-PG 2026</div><div class="sub">30 Aug 2026</div></div>`;
}

/* ---------- section legend ---------- */
function legendHTML(){ return SEC_KEYS.map(s=>
  `<span class="lg" data-sec="${s}"><span class="sw" style="background:${secColor(s)}"></span>${s}</span>`).join(''); }

/* ---------- bar chart with inline expand ---------- */
let selectedSubject=null;
let weightMode='all';   // 'all' | 'recent'
function currentBarData(){ return weightMode==='recent'?subjRecent:subjTotals; }
function currentDenom(){ return weightMode==='recent'?recentTotal:classifiedTotal; }

function sparklineSVG(sub){
  const st=subjectStats(sub), arr=st.arr, col=secColor(SEC_OF[sub]);
  const W=220,H=64,m={t:8,r:6,b:16,l:6}, iw=W-m.l-m.r, ih=H-m.t-m.b;
  const max=Math.max(2,...arr.map(d=>d.n));
  const xs=i=>m.l+(arr.length<2?iw/2:iw*i/(arr.length-1));
  const ys=v=>m.t+ih-ih*v/max;
  let line='',area='M'+xs(0)+' '+ys(0);
  arr.forEach((d,i)=>{ line+=(i?'L':'M')+xs(i)+' '+ys(d.n)+' '; area+=' L'+xs(i)+' '+ys(d.n); });
  area+=' L'+xs(arr.length-1)+' '+ys(0)+' Z';
  const pk=arr.indexOf(st.peak);
  const dots=arr.map((d,i)=>`<circle cx="${xs(i)}" cy="${ys(d.n)}" r="${i===pk?3.2:2}" fill="${i===pk?col:cssv('--surface')}" stroke="${col}" stroke-width="1.5"/>`).join('');
  const labels=[0,arr.length-1].map(i=>`<text x="${xs(i)}" y="${H-4}" text-anchor="${i?'end':'start'}" font-size="9" fill="${cssv('--muted')}">'${arr[i].y.slice(2)}</text>`).join('');
  return `<svg class="spark" viewBox="0 0 ${W} ${H}"><path d="${area}" fill="${col}" opacity="0.12"/>`+
    `<path d="${line}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round"/>${dots}${labels}</svg>`;
}
function detailHTML(sub){
  const st=subjectStats(sub);
  const dir = st.recAvg>st.earAvg*1.15?'up':(st.recAvg<st.earAvg*0.85?'down':'flat');
  const dirTxt = dir==='up'?'↑ Rising':dir==='down'?'↓ Cooling':'→ Steady';
  const denomPct = weightMode==='recent'
      ? (100*subjRecent.find(d=>d.s===sub).n/recentTotal).toFixed(1)
      : st.share.toFixed(1);
  return `<div class="bar-detail">
    <div>${sparklineSVG(sub)}</div>
    <div class="stat-grid">
      <div class="stat"><span class="v">${st.total}</span><span class="k">Total questions</span></div>
      <div class="stat"><span class="v">${denomPct}%</span><span class="k">Share of paper</span></div>
      <div class="stat"><span class="v">#${st.rank}</span><span class="k">Rank of 19</span></div>
      <div class="stat"><span class="v">${st.avg.toFixed(1)}</span><span class="k">Avg / paper</span></div>
      <div class="stat"><span class="v">${st.peak.n} <small style="font-size:12px;color:var(--muted);font-weight:600">'${st.peak.y.slice(2)}</small></span><span class="k">Peak year</span></div>
      <div class="stat"><span class="v ${dir==='up'?'up':dir==='down'?'down':''}">${dirTxt}</span><span class="k">Recent 3 vs earlier</span></div>
    </div>
    ${topicBreakdownHTML(sub)}</div>`;
}
function topicBreakdownHTML(sub){
  const tt=D.topic_totals[sub]||{}; const col=secColor(SEC_OF[sub]);
  const rows=Object.entries(tt).sort((a,b)=>b[1]-a[1]);
  if(!rows.length) return '';
  const max=rows[0][1];
  const bars=rows.map(([t,n])=>`<div class="trow"><span class="tn" title="${t}">${t}</span>
    <span class="tt2"><span class="tbar"><i style="width:${100*n/max}%;background:${col}"></i></span><span class="tv">${n}</span></span></div>`).join('');
  return `<div class="bd-topics"><div class="th">Topic breakdown
      <a href="#" class="browseTopic" data-sub="${sub}">Browse ${sub} questions →</a></div>
    <div class="tgrid">${bars}</div></div>`;
}
function renderBars(elId){
  const el=document.getElementById(elId); if(!el) return;
  const list=currentBarData(), denom=currentDenom();
  const max=Math.max(1,...list.map(d=>d.n));
  el.innerHTML=list.map(d=>{
    const pct=denom?(100*d.n/denom).toFixed(1):'0.0';
    const w=(100*d.n/max).toFixed(1);
    const sel=d.s===selectedSubject;
    return `<div class="bar ${sel?'sel':''}" data-sub="${d.s}" role="button" tabindex="0" aria-expanded="${sel}" aria-label="${escapeHtml(d.s)}, ${d.n} questions, ${pct} percent">
      <div class="name" title="${d.s}"><span class="caretb">▸</span>${d.s}</div>
      <div class="track"><div class="fill" style="width:${w}%;background:${secColor(d.sec)}"></div></div>
      <div class="val">${d.n}<small>${pct}%</small></div></div>`+
      (sel?detailHTML(d.s):'');
  }).join('');
  el.querySelectorAll('.bar').forEach(b=>{b.onclick=()=>selectSubject(b.dataset.sub);b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectSubject(b.dataset.sub);}};});
}
function selectSubject(sub){
  selectedSubject = (selectedSubject===sub)?null:sub;
  renderBars('bars-ov'); renderBars('bars-sub');
  renderTrend('svg-ov','tt-ov','legend-tr', trendModeOv, 'trend-title','trend-sub');
}
function setWeightMode(m){
  weightMode=m;
  document.querySelectorAll('#wt-mode button,#wt-mode2 button').forEach(x=>{const on=x.dataset.w===m;x.classList.toggle('on',on);x.setAttribute('aria-pressed',String(on));});
  document.getElementById('wt-title').textContent = m==='recent'
    ? 'Subject weightage — recent 3 papers' : `Subject weightage — all ${YEARS.length} classifiable papers`;
  renderBars('bars-ov'); renderBars('bars-sub'); renderCoverage();
}

/* ---------- SVG trend (stacked areas for sections, or a line for one subject) ---------- */
let trendModeOv='count', trendModeTr='count';
function renderTrend(svgId, ttId, legId, mode, titleId, subId){
  const svg=document.getElementById(svgId); if(!svg) return;
  const VB=svg.viewBox.baseVal, W=VB.width, H=VB.height;
  const m={t:16,r:16,b:34,l:44}, iw=W-m.l-m.r, ih=H-m.t-m.b;
  const xs=i=> m.l + (YEARS.length===1?iw/2:iw*i/(YEARS.length-1));
  const NS='http://www.w3.org/2000/svg';
  let out='';
  const gridN=4;

  if(selectedSubject){
    // single subject line
    if(titleId){document.getElementById(titleId).textContent=`${selectedSubject} — ${mode==='pct'?'share by year':'questions per 200'}`;
      document.getElementById(subId).innerHTML=`${mode==='pct'?'Share of classified questions':'Estimated questions normalised to a 200-question paper'} each year. <a href="#" id="clearsel">Clear selection ↩</a>`;}
    const data=subjectByYear(selectedSubject).map(d=>{const total=SUBJECTS.reduce((sum,s)=>sum+D.years[d.y].counts[s],0);
      return {...d,raw:d.n,total,n:total?d.n*(mode==='pct'?100:200)/total:0};});
    const max=Math.max(mode==='pct'?4:8,...data.map(d=>d.n));
    const ys=v=> m.t+ih-(ih*v/max);
    for(let g=0;g<=gridN;g++){ const v=Math.round(max*g/gridN); const y=ys(v);
      out+=`<line x1="${m.l}" y1="${y}" x2="${W-m.r}" y2="${y}" stroke="${cssv('--grid')}" stroke-width="1"/>`;
      out+=`<text x="${m.l-8}" y="${y+4}" text-anchor="end" font-size="11" fill="${cssv('--muted')}">${v}${mode==='pct'?'%':''}</text>`; }
    const col=secColor(SEC_OF[selectedSubject]);
    let dLine='', dArea='';
    data.forEach((d,i)=>{ const x=xs(i),y=ys(d.n); dLine+=(i?'L':'M')+x+' '+y+' '; });
    dArea=`M${xs(0)} ${ys(0)} `+data.map((d,i)=>'L'+xs(i)+' '+ys(d.n)).join(' ')+` L${xs(data.length-1)} ${ys(0)} Z`;
    out+=`<path d="${dArea}" fill="${col}" opacity="0.13"/>`;
    out+=`<path d="${dLine}" fill="none" stroke="${col}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>`;
    data.forEach((d,i)=>{ out+=`<circle cx="${xs(i)}" cy="${ys(d.n)}" r="4" fill="${cssv('--surface')}" stroke="${col}" stroke-width="2.5" data-i="${i}" class="pt"/>`; });
    xlabels(); svg.innerHTML=out;
    document.getElementById(legId).innerHTML='';
    svg.setAttribute('aria-label',`${selectedSubject} trend, ${mode==='pct'?'percentage share':'questions per 200'} by exam year`);
    hoverSubject(svg,ttId,data,max,xs,ys,col,mode);
    const cs=document.getElementById('clearsel'); if(cs) cs.onclick=(e)=>{e.preventDefault(); selectSubject(selectedSubject);};
    return;
  }

  // stacked section areas
  if(titleId){document.getElementById(titleId).textContent='Question mix over time — by section';
    document.getElementById(subId).textContent = mode==='pct'
      ? 'Share of each curriculum block per exam year (normalised to 100%).'
      : 'Estimated questions per block, normalised to a 200-question paper; hover for extraction coverage.';}
  const byY=sectionCountsByYear();
  const totals=YEARS.map(y=>SEC_KEYS.reduce((a,s)=>a+byY[y][s],0));
  const yearMax = mode==='pct'?100:200;
  const ys=v=> m.t+ih-(ih*v/yearMax);
  for(let g=0;g<=gridN;g++){ const v=Math.round(yearMax*g/gridN); const y=ys(v);
    out+=`<line x1="${m.l}" y1="${y}" x2="${W-m.r}" y2="${y}" stroke="${cssv('--grid')}" stroke-width="1"/>`;
    out+=`<text x="${m.l-8}" y="${y+4}" text-anchor="end" font-size="11" fill="${cssv('--muted')}">${v}${mode==='pct'?'':''}</text>`; }
  // build cumulative stacks
  const val=(y,s)=>{const total=totals[YEARS.indexOf(y)];return total?(mode==='pct'?100:200)*byY[y][s]/total:0;};
  let lower=YEARS.map(()=>0);
  SEC_KEYS.forEach(s=>{
    const col=secColor(s);
    const upper=YEARS.map((y,i)=>lower[i]+val(y,s));
    let d='M';
    YEARS.forEach((y,i)=> d+=`${xs(i)} ${ys(upper[i])} `+(i<YEARS.length-1?'L':''));
    for(let i=YEARS.length-1;i>=0;i--) d+=`L${xs(i)} ${ys(lower[i])} `;
    d+='Z';
    out+=`<path d="${d}" fill="${col}" opacity="0.9" stroke="${cssv('--surface')}" stroke-width="1"/>`;
    lower=upper;
  });
  xlabels(); svg.innerHTML=out;
  svg.setAttribute('aria-label',`Curriculum block trend, ${mode==='pct'?'percentage share':'questions per 200'} by exam year`);
  document.getElementById(legId).innerHTML=legendHTML();
  hoverStack(svg,ttId,byY,totals,mode,xs,m,ih);

  function xlabels(){ YEARS.forEach((y,i)=>{ const show = YEARS.length<=10 || i%2===0 || i===YEARS.length-1;
    if(show) out+=`<text x="${xs(i)}" y="${H-12}" text-anchor="middle" font-size="10.5" fill="${cssv('--muted')}">'${y.slice(2)}</text>`; }); }
}

function hoverStack(svg,ttId,byY,totals,mode,xs,m,ih){
  const tt=document.getElementById(ttId);
  const box=svg.parentElement;
  svg.onmousemove=ev=>{
    const r=svg.getBoundingClientRect(), sx=(ev.clientX-r.left)/r.width*svg.viewBox.baseVal.width;
    let i=Math.round((sx-m.l)/((svg.viewBox.baseVal.width-m.l-16)/(YEARS.length-1)));
    i=Math.max(0,Math.min(YEARS.length-1,i)); const y=YEARS[i];
    tt.innerHTML=`<h4>NEET-PG ${y}${y==='2025'?' · recall set':''}</h4>`+
      SEC_KEYS.map(s=>{ const v=byY[y][s]; const pc=totals[i]?(100*v/totals[i]):0;
        return `<div class="r"><span class="sw" style="background:${secColor(s)}"></span><span class="k">${s}</span><span class="v">${mode==='pct'?pc.toFixed(1)+'%':(pc*2).toFixed(1)}</span></div>`;}).join('')+
      `<div class="r" style="border-top:1px solid var(--border);margin-top:5px;padding-top:5px"><span class="k">Extraction coverage</span><span class="v">${totals[i]} / ${D.years[y].total_questions} (${D.years[y].total_questions?Math.round(100*totals[i]/D.years[y].total_questions):0}%)</span></div>`;
    place(tt,box,ev);
  };
  svg.onmouseleave=()=>tt.style.opacity=0;
}
function hoverSubject(svg,ttId,data,max,xs,ys,col,mode){
  const tt=document.getElementById(ttId), box=svg.parentElement;
  svg.onmousemove=ev=>{ const r=svg.getBoundingClientRect(), sx=(ev.clientX-r.left)/r.width*svg.viewBox.baseVal.width;
    let i=Math.round((sx-44)/((svg.viewBox.baseVal.width-60)/(YEARS.length-1)));
    i=Math.max(0,Math.min(YEARS.length-1,i)); const d=data[i];
    tt.innerHTML=`<h4>${selectedSubject} · ${d.y}</h4><div class="r"><span class="sw" style="background:${col}"></span><span class="k">${mode==='pct'?'Share':'Per 200'}</span><span class="v">${d.n.toFixed(1)}${mode==='pct'?'%':''}</span></div><div class="r"><span class="k">Extracted count</span><span class="v">${d.raw} / ${d.total}</span></div>`;
    place(tt,box,ev); };
  svg.onmouseleave=()=>tt.style.opacity=0;
}
function place(tt,box,ev){ const b=box.getBoundingClientRect();
  let x=ev.clientX-b.left+14, y=ev.clientY-b.top+12;
  if(x+180>b.width) x=ev.clientX-b.left-180; tt.style.left=x+'px'; tt.style.top=y+'px'; tt.style.opacity=1; }

/* ---------- volume bars (per-year parsed) ---------- */
function renderVolume(){
  const svg=document.getElementById('svg-vol'); if(!svg) return;
  const VB=svg.viewBox.baseVal,W=VB.width,H=VB.height,m={t:16,r:16,b:34,l:44},iw=W-m.l-m.r,ih=H-m.t-m.b;
  const data=ALL_YEARS.map(y=>({y,n:D.years[y].total_questions}));
  const max=Math.max(...data.map(d=>d.n));
  const bw=iw/data.length*0.6, gap=iw/data.length;
  let out='';
  for(let g=0;g<=4;g++){const v=Math.round(max*g/4),yy=m.t+ih-ih*g/4;
    out+=`<line x1="${m.l}" y1="${yy}" x2="${W-m.r}" y2="${yy}" stroke="${cssv('--grid')}"/>`;
    out+=`<text x="${m.l-8}" y="${yy+4}" text-anchor="end" font-size="11" fill="${cssv('--muted')}">${v}</text>`;}
  data.forEach((d,i)=>{ const x=m.l+gap*i+(gap-bw)/2, h=ih*d.n/max, y=m.t+ih-h;
    const excl=D.years[d.y].stats_excluded;
    const fill=excl?cssv('--axis'):secColor('Pre-Clinical');
    out+=`<rect x="${x}" y="${y}" width="${bw}" height="${h}" rx="4" fill="${fill}" data-i="${i}" class="vb"/>`;
    out+=`<text x="${x+bw/2}" y="${H-12}" text-anchor="middle" font-size="10.5" fill="${cssv('--muted')}">'${d.y.slice(2)}</text>`;
    out+=`<text x="${x+bw/2}" y="${y-5}" text-anchor="middle" font-size="10" fill="${cssv('--ink-2')}" font-weight="700">${d.n}</text>`;});
  svg.innerHTML=out;
  svg.setAttribute('aria-label','Questions extracted per exam year; excluded compilations are shown in grey');
  const tt=document.getElementById('tt-vol'),box=svg.parentElement;
  svg.querySelectorAll('.vb').forEach(rc=>{ rc.onmousemove=ev=>{const d=data[rc.dataset.i]; const yd=D.years[d.y];
    tt.innerHTML=`<h4>NEET-PG ${d.y}</h4><div class="r"><span class="k">Questions parsed</span><span class="v">${d.n}</span></div>`+
      (yd.stats_excluded
        ? `<div class="r"><span class="k">Solved compilation —</span></div><div class="r"><span class="k">excluded from subject stats</span></div>`
        : `<div class="r"><span class="k">Classified</span><span class="v">${yd.classified}</span></div>`);
    place(tt,box,ev);}; rc.onmouseleave=()=>tt.style.opacity=0;});
}

/* ---------- papers ---------- */
function renderPapers(){
  const el=document.getElementById('papers');
  el.innerHTML=ALL_YEARS.slice().reverse().map(y=>{
    const f=D.years[y].files; const yd=D.years[y];
    const link=(arr,label,ic)=> arr.length
      ? arr.map(fn=>`<a class="plink" href="${encodeURI(fn)}" target="_blank" rel="noopener"><span class="ic">${ic}</span>${label}${arr.length>1?' · '+shiftLabel(fn):''}<span class="go">↗</span></a>`).join('')
      : `<span class="plink mut"><span class="ic">${ic}</span>${label} — n/a</span>`;
    const sol = f.sol.length?f.sol:(f.key.length?f.key:[]);
    const solLabel = f.sol.length?'Solutions':(f.key.length?'Answer key':'Solutions');
    const meta = yd.stats_excluded
      ? `<b>${yd.total_questions}</b> questions · solved compilation`
      : yd.recall_source
        ? `<b>${yd.total_questions}</b> recall Qs · <b>${yd.classified}</b> classified`
        : `<b>${yd.total_questions}</b> parsed · <b>${yd.classified}</b> classified`;
    const recallLink = (f.recall&&f.recall.length)
      ? link(f.recall,'Recall questions (200)','🧠') : '';
    return `<div class="pcard">
      <div><div class="yr">${y}</div><div class="qn">${meta}</div></div>
      <div class="links">
        ${recallLink}
        ${link(f.qp,'Question paper','📝')}
        ${sol.length?link(sol,solLabel,'✅'):`<span class="plink mut"><span class="ic">✅</span>Solutions — n/a</span>`}
      </div></div>`;
  }).join('');
}
function shiftLabel(fn){ const m=fn.match(/Shift-(\d)/i); return m?'Shift '+m[1]:''; }

/* ---------- syllabus ---------- */
function renderSyllabus(){
  const el=document.getElementById('syllabus');
  const maxN=Math.max(...SUBJECTS.map(s=>D.subject_totals[s]));
  el.innerHTML=SEC_KEYS.map(sec=>{
    const subs=SECTIONS[sec]; const col=secColor(sec);
    const secTotal=subs.reduce((a,s)=>a+D.subject_totals[s],0);
    const rows=subs.slice().sort((a,b)=>D.subject_totals[b]-D.subject_totals[a]).map(s=>{
      const n=D.subject_totals[s], pct=(100*n/classifiedTotal).toFixed(1), w=(100*n/maxN).toFixed(0);
      return `<details class="sub">
        <summary>
          <span class="chip" style="background:${col}">${n}</span>
          <span class="sname">${s}</span>
          <span class="share"><span class="minibar"><i style="width:${w}%;background:${col}"></i></span>${pct}%</span>
          <span class="caret">▸</span>
        </summary>
        <div class="body"><div class="topics">${TOPICS[s]||''}</div></div>
      </details>`;
    }).join('');
    return `<div class="syl-sec">
      <h3><span class="dot" style="background:${col}"></span>${sec}<span class="cnt">· ${subs.length} subjects · ~${(100*secTotal/classifiedTotal).toFixed(0)}% of PYQs</span></h3>
      ${rows}</div>`;
  }).join('');
}

/* ---------- coverage callout ---------- */
function renderCoverage(){
  const el=document.getElementById('coverage'); if(!el) return;
  const list=currentBarData(), denom=currentDenom();
  let cum=0, n=0; const target=denom*0.6;
  for(const d of list){ cum+=d.n; n++; if(cum>=target) break; }
  const scope = weightMode==='recent'?'recent 3 papers':`all ${YEARS.length} classifiable papers`;
  const segs = list.slice(0,n).map(d=>`<i style="width:${100*d.n/denom}%;background:${secColor(d.sec)}"></i>`).join('')
             + `<i style="flex:1;background:var(--grid)"></i>`;
  el.innerHTML=`<div class="big">${n}</div>
    <div class="ctext">Just the <b>top ${n} subjects</b> account for <b>~60%</b> of all classified questions across the ${scope}.
      Master these first — the remaining ${list.length-n} subjects split the other 40%.
      <div class="covbar">${segs}</div></div>`;
}

/* ---------- movers (rising / cooling) ---------- */
function renderInsights(){
  const el=document.getElementById('insights'); if(!el) return;
  // percentage-point change in share: recent-3 share vs earlier share
  const movers=SUBJECTS.map(s=>{
    const rec=RECENT_YEARS.reduce((a,y)=>a+D.years[y].counts[s],0);
    const ear=EARLIER_YEARS.reduce((a,y)=>a+D.years[y].counts[s],0);
    const recShare=recentTotal?100*rec/recentTotal:0;
    const earTot=EARLIER_YEARS.reduce((a,y)=>a+SUBJECTS.reduce((x,su)=>x+D.years[y].counts[su],0),0);
    const earShare=earTot?100*ear/earTot:0;
    return {s, sec:SEC_OF[s], delta:recShare-earShare, recShare, earShare};
  });
  const rising=movers.slice().sort((a,b)=>b.delta-a.delta).slice(0,4);
  const cooling=movers.slice().sort((a,b)=>a.delta-b.delta).slice(0,4);
  const row=m=>{ const up=m.delta>=0;
    return `<div class="mover"><span class="sw" style="width:10px;height:10px;border-radius:3px;background:${secColor(m.sec)}"></span>
      <span class="mname">${m.s}</span>
      <span class="from">${m.earShare.toFixed(1)}% → ${m.recShare.toFixed(1)}%</span>
      <span class="arrow ${up?'up':'down'}">${up?'▲':'▼'} ${Math.abs(m.delta).toFixed(1)}pt</span></div>`; };
  el.innerHTML=`
    <div class="icard"><h3>📈 Gaining weight</h3><p class="hint">Biggest rise in share — recent 3 papers vs earlier years.</p>${rising.map(row).join('')}</div>
    <div class="icard"><h3>📉 Losing weight</h3><p class="hint">Biggest drop in share over the same window.</p>${cooling.map(row).join('')}</div>`;
}

/* ---------- subject × year heatmap ---------- */
function renderHeatmap(){
  const el=document.getElementById('heatmap'); if(!el) return;
  const rows=subjTotals; // sorted by total
  let gmax=1; YEARS.forEach(y=>SUBJECTS.forEach(s=>gmax=Math.max(gmax,D.years[y].counts[s])));
  const ramp=['#cde2fb','#9ec5f4','#6da7ec','#3987e5','#256abf','#184f95','#0d366b'];
  const cell=v=>{ if(!v) return {bg:'transparent',cls:'z'};
    const t=v/gmax; const i=Math.min(ramp.length-1,Math.round(t*(ramp.length-1)));
    return {bg:ramp[i],cls: i<2?'z':''}; };
  let html='<table class="heat"><caption class="sr-only">Subject question counts by exam year</caption><thead><tr><th class="rowh" scope="col">Subject</th>'+
    YEARS.map(y=>`<th>'${y.slice(2)}</th>`).join('')+'</tr></thead><tbody>';
  rows.forEach(r=>{
    html+=`<tr><th class="rowh" scope="row" title="${r.s}">${r.s}</th>`;
    YEARS.forEach(y=>{ const v=D.years[y].counts[r.s]; const c=cell(v);
      html+=`<td class="${c.cls}" style="background:${c.bg}" title="${r.s} · ${y}: ${v} questions">${v||''}</td>`; });
    html+='</tr>';
  });
  el.innerHTML=html+'</tbody></table>';
}

/* ---------- question browser ---------- */
const Q_PAGE=50; let qShown=Q_PAGE, qReady=false, qLoading=null, QUESTIONS=[], qYearMode='single';
function qYears(){ return [...new Set(QUESTIONS.map(q=>String(q.y)))].sort(); }
function escapeHtml(s){ return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
async function loadQuestions(){
  if(qReady)return QUESTIONS; if(qLoading)return qLoading;
  document.getElementById('q-total').textContent='…';
  document.getElementById('q-meta').textContent='Loading question index…';
  document.getElementById('q-list').innerHTML='<div class="qempty">Loading questions…</div>';
  qLoading=fetch('questions.json').then(response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json();})
    .then(payload=>{QUESTIONS=Array.isArray(payload)?payload:(payload.questions||[]);initQuestions();return QUESTIONS;})
    .catch(error=>{qLoading=null;document.getElementById('q-meta').textContent='Question index could not be loaded.';
      document.getElementById('q-list').innerHTML='<div class="qempty">Could not load questions.json. Serve this folder over HTTP and try again.</div>';
      document.getElementById('q-more').innerHTML='<button class="btn" id="q-retry" type="button">Retry</button>';
      document.getElementById('q-retry').onclick=loadQuestions;console.error(error);return [];});
  return qLoading;
}
function initQuestions(){
  const subj=document.getElementById('q-subject');
  subj.innerHTML='<option value="">All subjects</option>'+
    SUBJECTS.map(s=>`<option>${s}</option>`).join('')+'<option value="Unclassified">Unclassified</option>';
  const years=qYears(), yearOptions=years.map(y=>`<option>${y}</option>`).join('');
  document.getElementById('q-year').innerHTML='<option value="">All years</option>'+yearOptions;
  document.getElementById('q-year-from').innerHTML=yearOptions;
  document.getElementById('q-year-to').innerHTML=yearOptions;
  document.getElementById('q-year-from').value=years[0]||'';
  document.getElementById('q-year-to').value=years.at(-1)||'';
  document.getElementById('q-total').textContent=QUESTIONS.length.toLocaleString();
  updateTopicOptions();
  document.getElementById('q-search').addEventListener('input',debounce(()=>{qShown=Q_PAGE;renderQuestions();updateQuestionRoute();},180));
  document.getElementById('q-subject').addEventListener('change',()=>{updateTopicOptions();qShown=Q_PAGE;renderQuestions();updateQuestionRoute();});
  document.getElementById('q-topic').addEventListener('change',()=>{qShown=Q_PAGE;renderQuestions();updateQuestionRoute();});
  document.getElementById('q-year').addEventListener('change',()=>{qShown=Q_PAGE;renderQuestions();updateQuestionRoute();});
  document.querySelector('.year-mode').addEventListener('click',event=>{
    const button=event.target.closest('[data-year-mode]');if(!button)return;
    const mode=button.dataset.yearMode, single=document.getElementById('q-year').value;
    if(mode==='range'&&qYearMode==='single'&&single){document.getElementById('q-year-from').value=single;document.getElementById('q-year-to').value=single;}
    if(mode==='single'&&qYearMode==='range'){
      const from=document.getElementById('q-year-from').value,to=document.getElementById('q-year-to').value;
      if(from===to)document.getElementById('q-year').value=from;
    }
    setYearMode(mode);qShown=Q_PAGE;renderQuestions();updateQuestionRoute();
  });
  document.getElementById('q-year-from').addEventListener('change',()=>{
    const from=document.getElementById('q-year-from'),to=document.getElementById('q-year-to');if(from.value>to.value)to.value=from.value;
    qShown=Q_PAGE;renderQuestions();updateQuestionRoute();
  });
  document.getElementById('q-year-to').addEventListener('change',()=>{
    const from=document.getElementById('q-year-from'),to=document.getElementById('q-year-to');if(to.value<from.value)from.value=to.value;
    qShown=Q_PAGE;renderQuestions();updateQuestionRoute();
  });
  qReady=true; applyQuestionRoute();
}
function setYearMode(mode){
  qYearMode=mode==='range'?'range':'single';
  document.getElementById('q-year-single').hidden=qYearMode!=='single';
  document.getElementById('q-year-range').hidden=qYearMode!=='range';
  document.querySelectorAll('[data-year-mode]').forEach(button=>{const on=button.dataset.yearMode===qYearMode;button.classList.toggle('on',on);button.setAttribute('aria-pressed',String(on));});
}
function setSelectValue(select,value,fallback=''){
  select.value=[...select.options].some(option=>option.value===value)?value:fallback;
}
function applyQuestionRoute(){
  if(!qReady||readRoute().view!=='questions')return;
  const params=readRoute().params, search=document.getElementById('q-search'), subject=document.getElementById('q-subject');
  search.value=params.get('q')||'';
  subject.value=[...subject.options].some(option=>option.value===params.get('subject'))?(params.get('subject')||''):'';
  updateTopicOptions();
  const topic=document.getElementById('q-topic'), year=document.getElementById('q-year'),
    from=document.getElementById('q-year-from'),to=document.getElementById('q-year-to'),years=qYears();
  setSelectValue(topic,params.get('topic')||'');
  if(params.has('from')||params.has('to')){
    setYearMode('range');setSelectValue(from,params.get('from')||'',years[0]||'');setSelectValue(to,params.get('to')||'',years.at(-1)||'');
    if(from.value>to.value)[from.value,to.value]=[to.value,from.value];
  }else{setYearMode('single');setSelectValue(year,params.get('year')||'');}
  qShown=Q_PAGE; renderQuestions();
}
function updateQuestionRoute(){
  if(readRoute().view!=='questions')return;
  const values={q:document.getElementById('q-search').value.trim(),subject:document.getElementById('q-subject').value,
    topic:document.getElementById('q-topic').value};
  if(qYearMode==='range'){values.from=document.getElementById('q-year-from').value;values.to=document.getElementById('q-year-to').value;}
  else values.year=document.getElementById('q-year').value;
  const params=new URLSearchParams();Object.entries(values).forEach(([key,value])=>{if(value)params.set(key,value);});
  history.replaceState(null,'',`#questions${params.size?`?${params}`:''}`);
}
function updateTopicOptions(){
  const sub=document.getElementById('q-subject').value, tsel=document.getElementById('q-topic');
  if(sub){
    const counts={};QUESTIONS.forEach(r=>{if(r.s===sub&&r.t)counts[r.t]=(counts[r.t]||0)+1;});
    const topics=Object.entries(counts).sort((a,b)=>b[1]-a[1]).map(x=>x[0]);
    tsel.innerHTML='<option value="">All topics</option>'+topics.map(t=>`<option>${t}</option>`).join('');
    tsel.disabled=!topics.length;
  } else { tsel.innerHTML='<option value="">All topics</option>'; tsel.disabled=true; }
}
function filteredQuestions(){
  const sub=document.getElementById('q-subject').value, top=document.getElementById('q-topic').value,
        yr=document.getElementById('q-year').value,from=document.getElementById('q-year-from').value,
        to=document.getElementById('q-year-to').value,q=document.getElementById('q-search').value.trim().toLowerCase();
  return QUESTIONS.filter(r=>{const year=String(r.y);return (!sub||r.s===sub)&&(!top||r.t===top)&&
    (qYearMode==='range'?(year>=from&&year<=to):(!yr||year===yr))&&(!q||String(r.q||'').toLowerCase().includes(q));});
}
function highlightText(text,term){
  let html=escapeHtml(text);
  if(term){const re=new RegExp('('+term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig');html=html.replace(re,'<mark>$1</mark>');}
  return html;
}
function fmtQ(text,term){
  const source=String(text||''), marker=/\(\s*([A-D1-4])\s*\)/gi, matches=[...source.matchAll(marker)];
  if(matches.length<2)return `<div class="qstem">${highlightText(source,term)}</div>`;
  const stem=source.slice(0,matches[0].index).trim();
  const options=matches.map((match,index)=>({label:match[1].toUpperCase(),
    text:source.slice(match.index+match[0].length,index+1<matches.length?matches[index+1].index:source.length).trim()}));
  return `<div class="qstem">${highlightText(stem,term)}</div><div class="qoptions">${options.map(option=>
    `<div class="qoption"><span class="opt-label">${escapeHtml(option.label)}</span><span>${highlightText(option.text,term)}</span></div>`).join('')}</div>`;
}
function confidenceUI(value){if(value===undefined||value===null||value==='')return '';
  const numeric=Number(value), text=Number.isFinite(numeric)?`${numeric<=1?Math.round(numeric*100):Math.round(numeric)}% classifier separation`:String(value);
  const score=Number.isFinite(numeric)?(numeric<=1?numeric:numeric/100):({high:.9,medium:.65,low:.3}[String(value).toLowerCase()]||.5);
  return `<span class="qconfidence ${score>=.8?'high':score>=.55?'medium':'low'}" title="Score separation from the next classifier candidate; not a probability of correctness">${escapeHtml(text)}</span>`;}
function sourceUI(r){if(!r.src&&!r.page&&!r.qnum)return '';
  const label=[r.src&&String(r.src).split(/[\\/]/).pop(),r.page&&`page ${r.page}`,r.qnum&&`Q${r.qnum}`].filter(Boolean).join(' · ');
  const safeSrc=typeof r.src==='string'&&!/^\s*(?:javascript|data):/i.test(r.src);
  const href=safeSrc?`${encodeURI(r.src)}${r.page?`#page=${encodeURIComponent(r.page)}`:''}`:'';
  return href?`<a href="${escapeHtml(href)}" target="_blank" rel="noopener">Source: ${escapeHtml(label)}</a>`:`<span>Source: ${escapeHtml(label)}</span>`;}
function candidatesUI(items){if(!Array.isArray(items)||!items.length)return '';
  const values=items.slice(0,4).map(c=>typeof c==='string'?c:[c.s||c.subject,c.t||c.topic,c.score!==undefined?`(${Number(c.score).toFixed(2)})`:null].filter(Boolean).join(' — '));
  return `<ul class="qcandidates">${values.map(v=>`<li>${escapeHtml(v)}</li>`).join('')}</ul>`;}
function classifierUI(r){
  const candidates=candidatesUI(r.candidates), confidence=confidenceUI(r.confidence);
  if(!candidates&&!confidence)return '';
  return `<details class="qclassifier"><summary>Classification details</summary><div>${confidence}${candidates}</div></details>`;
}
function imageUI(r){
  if(!r.image&&!r.image_asset)return '';
  const asset=typeof r.image_asset==='string'?r.image_asset:(r.image_asset?.path||r.image_asset?.src||'');
  if(asset&&!/^\s*(?:javascript|data):/i.test(asset)){
    const path=escapeHtml(encodeURI(asset));
    return `<figure class="qimage"><a href="${path}" target="_blank" rel="noopener"><img src="${path}" loading="lazy" decoding="async" alt="Source-page crop for question ${escapeHtml(r.qnum||'')}"></a><figcaption>Source-page crop containing the referenced visual · tap to enlarge</figcaption></figure>`;
  }
  return `<div class="qnotice">This question refers to an image, but no recoverable figure is available from its source.${r.page_link?` <a href="${escapeHtml(encodeURI(r.page_link))}" target="_blank" rel="noopener">View source page</a>`:''}</div>`;
}
function renderQuestions(){
  if(!qReady) return;
  const list=filteredQuestions(), term=document.getElementById('q-search').value.trim();
  document.getElementById('q-meta').textContent = list.length
    ? `Showing ${Math.min(qShown,list.length).toLocaleString()} of ${list.length.toLocaleString()} matching questions` : '';
  const el=document.getElementById('q-list');
  if(!list.length){ el.innerHTML='<div class="qempty">No questions match these filters. Try clearing the search or widening the subject.</div>';
    document.getElementById('q-more').innerHTML=''; return; }
  el.innerHTML=list.slice(0,qShown).map((r,index)=>{
    const col=r.s==='Unclassified'?cssv('--muted'):secColor(SEC_OF[r.s]);
    const topicTag=r.t?`<span class="qtag topic">${escapeHtml(r.t)}</span>`:'';
    const ansTag=r.a?`<span class="qtag ans">Ans: ${escapeHtml(r.a)}</span>`:'';
    return `<article class="qcard" aria-label="Question ${escapeHtml(r.qnum||index+1)}, ${escapeHtml(r.y)}"><div class="qtags"><span class="qnumber">Q${escapeHtml(r.qnum||index+1)}</span><span class="qtag year">${escapeHtml(r.y)}</span>
      <span class="qtag" style="background:${col}">${escapeHtml(r.s||'Unclassified')}</span>${topicTag}${ansTag}</div>
      <div class="qtext">${fmtQ(r.q,term)}</div>${imageUI(r)}
      <div class="qdetails">${sourceUI(r)}${classifierUI(r)}</div></article>`;
  }).join('');
  document.getElementById('q-more').innerHTML = list.length>qShown
    ? `<button class="btn" id="q-loadmore">Show more (${(list.length-qShown).toLocaleString()} left)</button>` : '';
  const lm=document.getElementById('q-loadmore'); if(lm) lm.onclick=()=>{qShown+=Q_PAGE;renderQuestions();};
}
// jump from a subject's expand panel into the browser
document.addEventListener('click',async e=>{ const a=e.target.closest('.browseTopic'); if(!a) return;
  e.preventDefault();
  navigateTo('questions'); await loadQuestions(); if(!qReady)return;
  document.getElementById('q-search').value=''; document.getElementById('q-year').value='';
  document.getElementById('q-subject').value=a.dataset.sub; updateTopicOptions();
  qShown=Q_PAGE; renderQuestions(); updateQuestionRoute();
});

/* ---------- 2026 predictions ---------- */
function isDark(){ const t=document.documentElement.getAttribute('data-theme');
  return t?t==='dark':matchMedia('(prefers-color-scheme:dark)').matches; }
const RED=()=>isDark()?'#e66767':'#e34948';
let predExpanded=null, predSearch='';
function renderPredKPIs(){
  const P=D.predictions; if(!P) return; const pc=P.priority_counts;
  document.getElementById('pred-src').innerHTML='Source: <b>'+P.source+'</b>';
  document.getElementById('pred-pdf').href='NEET-PG-2026-Predicted-Topics.pdf';
  document.getElementById('pred-kpis').innerHTML=`
   <div class="pred-kpi"><div class="n">${P.total_topics}</div><div class="l">Predicted high-yield topics</div></div>
   <div class="pred-kpi"><div class="n">${Object.keys(P.subjects).length}</div><div class="l">Subjects covered</div></div>
   <div class="pred-kpi"><div class="n">${P.total_repeats}</div><div class="l">Combined past-paper repeats</div></div>
   <div class="pred-kpi"><div class="n">${pc.High}</div><div class="l">High-priority topics</div>
     <div class="prio"><i style="flex:${pc.High};background:#e34948"></i><i style="flex:${pc.Moderate};background:#eda100"></i><i style="flex:${pc.Low};background:var(--muted)"></i></div></div>`;
}
const _norm=s=>s.toLowerCase().replace(/[^a-z0-9]/g,'');
function lookupNotes(subject,topic){
  const N=window.NEET_NOTES; if(!N||!N[subject]) return [];
  if(N[subject][topic]) return N[subject][topic];
  const nt=_norm(topic);
  for(const k in N[subject]) if(_norm(k)===nt) return N[subject][k];
  return [];
}
function predTopicRow(t,term,subj){
  let name=escapeHtml(t.topic);
  if(term){ const re=new RegExp('('+term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','ig'); name=name.replace(re,'<mark>$1</mark>'); }
  const notes=lookupNotes(subj,t.topic);
  const notesHtml=notes.length
    ? `<div class="subtopics"><div class="st-head">High-yield sub-topics</div><ul>${notes.map(n=>`<li>${escapeHtml(n)}</li>`).join('')}</ul></div>` : '';
  return `<div class="ptopic-wrap">
    <div class="ptopic ${notes.length?'has-notes':''}" ${notes.length?'role="button" tabindex="0" aria-expanded="false"':''}>
      <span class="prio-pill ${t.priority}">${t.priority}</span>
      <span class="pt-name">${name}</span>
      <span class="times-badge">${t.times}×</span>
      ${notes.length?'<span class="pt-caret">▸</span>':'<span class="pt-caret" style="visibility:hidden">▸</span>'}
    </div>${notesHtml}</div>`;
}
function renderPredBars(){
  const P=D.predictions; if(!P) return; const el=document.getElementById('pred-bars');
  const subs=Object.entries(P.subjects).map(([name,v])=>({name,sec:SEC_OF[name],...v}))
      .sort((a,b)=>b.combined-a.combined);
  const max=Math.max(...subs.map(s=>s.combined));
  const term=predSearch.trim().toLowerCase();
  el.innerHTML=subs.map(s=>{
    const matches=term?s.topics.filter(t=>t.topic.toLowerCase().includes(term)):null;
    if(term && matches.length===0) return '';
    const expanded=term?true:(predExpanded===s.name);
    const w=(100*s.combined/max).toFixed(1);
    const bar=`<div class="bar ${expanded?'sel':''}" data-sub="${s.name}" role="button" tabindex="0" aria-expanded="${expanded}">
      <div class="name" title="${s.name}"><span class="caretb">▸</span>${s.name}</div>
      <div class="track"><div class="fill" style="width:${w}%;background:${secColor(s.sec)}"></div></div>
      <div class="val">${s.combined}<small>${s.topics.length} topics</small></div></div>`;
    if(!expanded) return bar;
    const rows=(term?matches:s.topics).slice().sort((a,b)=>b.times-a.times).map(t=>predTopicRow(t,term,s.name)).join('');
    return bar+`<div class="pred-detail">${rows}</div>`;
  }).join('') || '<div class="qempty">No forecast topics match that search.</div>';
  el.querySelectorAll('.bar').forEach(b=>{const activate=()=>{if(predSearch.trim())return;predExpanded=predExpanded===b.dataset.sub?null:b.dataset.sub;renderPredBars();};
    b.onclick=activate;b.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}};});
  el.querySelectorAll('.ptopic.has-notes').forEach(row=>{const activate=e=>{e.stopPropagation();const open=row.closest('.ptopic-wrap').classList.toggle('open');row.setAttribute('aria-expanded',String(open));};
    row.onclick=activate;row.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate(e);}};});
}
function renderTopTopics(){
  const P=D.predictions; if(!P) return;
  const all=[]; Object.entries(P.subjects).forEach(([s,v])=>v.topics.forEach(t=>all.push({...t,subj:s})));
  all.sort((a,b)=>b.times-a.times);
  document.getElementById('pred-top').innerHTML=all.slice(0,18).map((t,i)=>`<div class="toptopic">
    <span class="rank">${i+1}</span>
    <div class="tt-body"><div class="tt-name" title="${t.topic}">${t.topic}</div><div class="tt-sub">${t.subj} · ${t.priority} priority</div></div>
    <span class="tt-times">${t.times}×</span></div>`).join('');
}
function renderPredCompare(){
  const P=D.predictions; const svg=document.getElementById('svg-pred'); if(!P||!svg) return;
  const VB=svg.viewBox.baseVal,W=VB.width,H=VB.height, m={t:28,r:46,b:12,l:158}, iw=W-m.l-m.r, ih=H-m.t-m.b;
  const cx=m.l+iw/2;
  const rows=Object.keys(P.subjects).map(s=>{
    const predShare=100*P.subjects[s].combined/P.total_repeats;
    const histShare=100*(D.subject_totals[s]||0)/classifiedTotal;
    return {s,gap:predShare-histShare,predShare,histShare};
  }).sort((a,b)=>b.gap-a.gap);
  const maxAbs=Math.max(...rows.map(r=>Math.abs(r.gap)))||1, scale=(iw/2-34)/maxAbs, rowH=ih/rows.length;
  let out=`<line x1="${cx}" y1="${m.t-4}" x2="${cx}" y2="${H-m.b}" stroke="${cssv('--axis')}" stroke-width="1"/>`;
  out+=`<text x="${cx+7}" y="${m.t-14}" font-size="10.5" fill="${cssv('--muted')}">forecast heavier →</text>`;
  out+=`<text x="${cx-7}" y="${m.t-14}" text-anchor="end" font-size="10.5" fill="${cssv('--muted')}">← history heavier</text>`;
  rows.forEach((r,i)=>{ const y=m.t+i*rowH+rowH/2, bh=Math.min(15,rowH-6), up=r.gap>=0;
    const col=up?secColor('Pre-Clinical'):RED(), len=Math.max(1,Math.abs(r.gap)*scale), x=up?cx:cx-len;
    out+=`<text x="${m.l-10}" y="${y+4}" text-anchor="end" font-size="11.5" fill="${cssv('--ink-2')}">${r.s}</text>`;
    out+=`<rect x="${x}" y="${y-bh/2}" width="${len}" height="${bh}" rx="3" fill="${col}" data-i="${i}" class="pcb"/>`;
    const lx=up?cx+len+5:cx-len-5;
    out+=`<text x="${lx}" y="${y+4}" text-anchor="${up?'start':'end'}" font-size="10.5" font-weight="700" fill="${cssv('--muted')}">${up?'+':''}${r.gap.toFixed(1)}</text>`;
  });
  svg.innerHTML=out;
  svg.setAttribute('aria-label','Difference between 2026 forecast share and historical question share by subject');
  const tt=document.getElementById('tt-pred'),box=svg.parentElement;
  svg.querySelectorAll('.pcb').forEach(rc=>{ rc.onmousemove=ev=>{const r=rows[rc.dataset.i];
    tt.innerHTML=`<h4>${r.s}</h4><div class="r"><span class="k">Forecast share</span><span class="v">${r.predShare.toFixed(1)}%</span></div>
      <div class="r"><span class="k">Historical share</span><span class="v">${r.histShare.toFixed(1)}%</span></div>
      <div class="r" style="border-top:1px solid var(--border);margin-top:5px;padding-top:5px"><span class="k">Difference</span><span class="v">${r.gap>=0?'+':''}${r.gap.toFixed(1)} pt</span></div>`;
    place(tt,box,ev);}; rc.onmouseleave=()=>tt.style.opacity=0; });
}
function renderPredictions(){ renderPredKPIs(); renderPredBars(); renderTopTopics(); renderPredCompare(); }

/* ---------- footer ---------- */
function renderFoot(){
  const statsParsed = YEARS.reduce((a,y)=>a+D.years[y].total_questions,0);
  document.getElementById('foot').innerHTML=
   `<b>Method.</b> Text extracted from every question-paper PDF (2010–2025); questions split on their numbering and evaluated by a weighted medical-keyword matcher. `+
   `${D.meta.grand_total_questions.toLocaleString()} questions parsed in total; across the ${YEARS.length} classifiable papers, ${classifiedTotal.toLocaleString()} of ${statsParsed.toLocaleString()} (${Math.round(100*classifiedTotal/statsParsed)}%) had at least one keyword match. Top-score ties use canonical subject order and remain flagged for review; zero-score questions remain unclassified. `+
   `Subject percentages are <b>directional estimates</b>, not an official blueprint — NBEMS does not publish a subject-wise count. `+
   `<b>2015</b> was never released publicly; <b>2016</b> is a solved compilation (kept in the library but excluded from subject stats); <b>2025</b> uses a ~200-question student recall set (DigiNerve), the exam being memory-based. `+
   `Regenerate anytime with <b>build_analysis.py</b>. Official syllabus: the NEET-PG 2026 Information Bulletin.`;
}

/* ---------- mode toggles ---------- */
document.getElementById('trend-mode').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  trendModeOv=b.dataset.m; setPressed('#trend-mode button',b);
  renderTrend('svg-ov','tt-ov','legend-tr',trendModeOv,'trend-title','trend-sub');});
document.getElementById('trend2-mode').addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  trendModeTr=b.dataset.m; setPressed('#trend2-mode button',b);
  renderTrend('svg-tr','tt-tr','legend-tr2',trendModeTr,'trend2-title','trend2-sub');});
['wt-mode','wt-mode2'].forEach(id=>document.getElementById(id).addEventListener('click',e=>{
  const b=e.target.closest('button'); if(!b) return; setWeightMode(b.dataset.w);}));
document.getElementById('pred-search').addEventListener('input',debounce(e=>{predSearch=e.target.value; renderPredBars();},180));

/* ---------- render all ---------- */
function renderAll(){
  if(!qReady)document.getElementById('q-total').textContent=D.meta.grand_total_questions.toLocaleString();
  document.getElementById('wt-title').textContent=weightMode==='recent'
    ? 'Subject weightage — recent 3 papers' : `Subject weightage — all ${YEARS.length} classifiable papers`;
  renderKPI();
  document.getElementById('legend-ov').innerHTML=legendHTML();
  document.getElementById('legend-sub').innerHTML=legendHTML();
  renderBars('bars-ov'); renderBars('bars-sub'); renderCoverage(); renderInsights();
  renderTrend('svg-ov','tt-ov','legend-tr',trendModeOv,'trend-title','trend-sub');
  renderTrend('svg-tr','tt-tr','legend-tr2',trendModeTr,'trend2-title','trend2-sub');
  renderVolume(); renderHeatmap(); renderPapers(); renderSyllabus(); renderPredictions(); renderFoot();
  renderQuestions();
}
renderAll();
showView(readRoute().view);
addEventListener('resize',debounce(()=>{ renderTrend('svg-ov','tt-ov','legend-tr',trendModeOv,'trend-title','trend-sub');
  renderTrend('svg-tr','tt-tr','legend-tr2',trendModeTr,'trend2-title','trend2-sub'); renderVolume(); renderPredCompare(); },160));
