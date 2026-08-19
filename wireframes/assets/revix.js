/* Revix wireframe interaction layer.
   The weighting switch is REAL: three precomputed strategies, exactly as the
   pipeline would produce them. Flipping it re-renders every score, interval,
   ordering and the effective sample size.

   All figures are illustrative placeholders. Nothing here is fetched. */

const STRATEGIES = [
  { key: 'equal',  label: 'Every review equally',
    blurb: 'One review, one vote. This is what every review site in India shows you today.' },
  { key: 'source', label: 'By source',
    blurb: 'Expert publications, owner reviews and forum posts carry different fixed weights.' },
  { key: 'cred',   label: 'By how much each can be trusted',
    blurb: 'Each review is weighted by spam risk, detail, corroboration, and by whether that owner is a good witness to this particular topic.' }
];

/* aspect ids follow the fixed nine-aspect taxonomy in proposal.md section 17 */
const CRETA = {
  name: 'Hyundai Creta', variant: 'SX (O) 1.5 Diesel AT',
  price: '₹19.2L – 20.4L', klass: 'car',
  specs: [['Engine','1493 cc diesel'],['Power','114 bhp'],['Transmission','6-speed AT'],['ARAI mileage','21.4 kmpl'],['Seats','5']],
  line: 'Rides beautifully and feels a class above inside. <em>The after-sales experience is what owners hesitate over.</em>',
  overall: { equal:[8.3,7.9,8.7,412], source:[8.0,7.5,8.5,301], cred:[7.8,7.1,8.4,178] },
  media: { equal:8.7, source:8.9, cred:8.9 },
  owners:{ equal:8.1, source:7.6, cred:7.4 },
  gap: 'service, after-sales and parts',
  gapVals: [8.5, 5.9],
  aspects: [
    { id:'engine', name:'Engine and gearbox', split:0.61, n:34,
      equal:[7.4,6.8,8.0], source:[7.1,6.4,7.8], cred:[6.2,5.4,7.1],
      why:{ covariate:'transmission type', pct:71,
            rows:[['Automatic (DCT) owners',6.2,true],['Manual owners',8.8,false]],
            note:'The gearbox is not bad. It is bad <b>in traffic, in the automatic</b>. That is a variant-level answer no star average can give you.' } },
    { id:'service', name:'Service, after-sales and parts', split:0.44, n:96,
      equal:[7.1,6.5,7.6], source:[6.6,6.0,7.2], cred:[5.9,5.1,6.6],
      why:{ covariate:'city', pct:58,
            rows:[['Metro cities',6.8,false],['Smaller cities',5.1,true]],
            note:'Spare-part waiting time is the single most cited reason in the negative reviews.' } },
    { id:'reliability', name:'Long-term reliability', split:0.33, n:71,
      equal:[7.8,7.2,8.3], source:[7.6,7.0,8.1], cred:[7.2,6.6,7.8],
      why:{ covariate:'kilometres driven', pct:49,
            rows:[['Under 20,000 km',8.1,false],['Over 50,000 km',6.6,true]],
            note:'Owners past 50,000 km are the ones the credibility model trusts most on this topic.' } },
    { id:'running', name:'Real-world mileage and running cost', split:0.29, n:118,
      equal:[7.5,7.0,8.0], source:[7.3,6.8,7.8], cred:[7.0,6.5,7.5] },
    { id:'build', name:'Build quality', split:0.21, n:88,
      equal:[8.0,7.5,8.4], source:[8.1,7.6,8.5], cred:[7.9,7.4,8.3] },
    { id:'features', name:'Features and infotainment', split:0.17, n:143,
      equal:[8.3,8.0,8.6], source:[8.4,8.1,8.7], cred:[8.4,8.1,8.7] },
    { id:'interior', name:'Interior space and comfort', split:0.13, n:151,
      equal:[8.6,8.3,8.9], source:[8.7,8.4,9.0], cred:[8.7,8.4,9.0] },
    { id:'ride', name:'Ride quality, handling and NVH', split:0.12, n:139,
      equal:[8.5,8.2,8.8], source:[8.7,8.4,9.0], cred:[8.6,8.3,8.9] },
    { id:'safety', name:'Safety', split:0.08, n:64,
      equal:[8.8,8.5,9.1], source:[8.9,8.6,9.2], cred:[8.9,8.6,9.2] }
  ],
  facts: [
    { k:'Real-world mileage', v:'17.2', unit:'kmpl',
      sub:'Owners report <b>19.6% below</b> the 21.4 kmpl ARAI claim' },
    { k:'Crash safety', stars:5,
      sub:'Bharat NCAP: 5★ adult, 4★ child occupant' },
    { k:'Recalls', v:'1', unit:'notice',
      sub:'2024: high-pressure fuel pump, 8,900 units' }
  ]
};

const CLASSIC = {
  name: 'Royal Enfield Classic 350', variant: 'Dual-channel ABS',
  price: '₹2.25L – 2.32L', klass: 'two_wheeler',
  specs: [['Engine','349 cc petrol'],['Power','20 bhp'],['Kerb weight','195 kg'],['Seat height','805 mm'],['Braking','Dual-channel ABS']],
  line: 'Nothing else feels like it. <em>What you pay for that is vibration, weight and a service queue.</em>',
  overall: { equal:[8.1,7.7,8.5,368], source:[7.9,7.4,8.3,268], cred:[7.5,6.8,8.1,154] },
  media: { equal:8.6, source:8.8, cred:8.8 },
  owners:{ equal:7.9, source:7.4, cred:7.2 },
  gap: 'long-term reliability',
  gapVals: [8.4, 6.4],
  aspects: [
    { id:'reliability', name:'Long-term reliability', split:0.58, n:61,
      equal:[7.2,6.5,7.8], source:[6.9,6.2,7.5], cred:[6.1,5.3,6.9],
      why:{ covariate:'year of manufacture', pct:66,
            rows:[['2021–22 (J-platform, early)',5.4,true],['2024 onwards',7.9,false]],
            note:'The split is almost entirely a <b>model-year</b> story. Averaging every review together hides the fact that the problem was largely fixed.' } },
    { id:'service', name:'Service, after-sales and parts', split:0.47, n:83,
      equal:[7.0,6.4,7.6], source:[6.7,6.1,7.3], cred:[6.2,5.5,6.9],
      why:{ covariate:'city', pct:54,
            rows:[['Metro cities',7.1,false],['Smaller cities',5.6,true]],
            note:'Dealer density drives this far more than the motorcycle does.' } },
    { id:'engine', name:'Engine and gearbox', split:0.31, n:104,
      equal:[8.2,7.7,8.6], source:[8.3,7.9,8.7], cred:[8.1,7.6,8.5] },
    { id:'running', name:'Real-world mileage and running cost', split:0.27, n:97,
      equal:[7.4,6.9,7.9], source:[7.2,6.7,7.7], cred:[7.1,6.6,7.6] },
    { id:'ride', name:'Ergonomics and pillion comfort', split:0.24, n:112,
      equal:[7.6,7.1,8.1], source:[7.8,7.3,8.2], cred:[7.5,7.0,8.0] },
    { id:'build', name:'Build quality', split:0.19, n:126,
      equal:[8.4,8.1,8.7], source:[8.5,8.2,8.8], cred:[8.4,8.1,8.7] },
    { id:'features', name:'Features and instrumentation', split:0.16, n:78,
      equal:[7.3,6.9,7.7], source:[7.2,6.8,7.6], cred:[7.2,6.8,7.6] },
    { id:'interior', name:'Ride quality and NVH', split:0.14, n:118,
      equal:[8.0,7.7,8.3], source:[8.1,7.8,8.4], cred:[8.0,7.7,8.3] },
    { id:'safety', name:'Safety', split:0.11, n:44,
      equal:[7.7,7.3,8.1], source:[7.8,7.4,8.2], cred:[7.8,7.4,8.2] }
  ],
  facts: [
    { k:'Real-world mileage', v:'33.8', unit:'kmpl',
      sub:'Owners report <b>10.1% below</b> the 37.6 kmpl claimed figure' },
    { k:'Crash safety', absent:true, v:'No rating exists',
      sub:'Bharat NCAP does not rate two-wheelers. Anchored on braking spec and ABS instead.' },
    { k:'Recalls', v:'2', unit:'notices',
      sub:'2023 ignition coil · 2022 rear brake caliper' }
  ]
};

/* ---------- helpers ---------- */
const heatOf = s => s >= 0.40 ? 'split' : s >= 0.22 ? 'some' : 'agreed';
const heatWord = s => s >= 0.40 ? 'Sharply split' : s >= 0.22 ? 'Some disagreement' : 'Broad agreement';
const pct = v => (v * 10).toFixed(1);

function trackHTML(v, lo, hi, heat){
  return `<div class="track" data-heat="${heat}" style="--v:${pct(v)};--lo:${pct(lo)};--hi:${pct(hi)}">
      <div class="track-band"></div><div class="track-dot"></div></div>`;
}

function deltaChip(now, base){
  const d = +(now - base).toFixed(1);
  if (Math.abs(d) < 0.05) return `<span class="delta flat">no change</span>`;
  const cls = d < 0 ? 'dn' : 'up';
  return `<span class="delta ${cls}">${d < 0 ? '▼' : '▲'} ${Math.abs(d).toFixed(1)}</span>`;
}

/* ---------- the render ---------- */
function renderVerdict(V, strat){
  const [ov, lo, hi, n] = V.overall[strat];
  const [bov] = V.overall.equal;

  document.getElementById('ovScore').textContent = ov.toFixed(1);
  document.getElementById('ovTrack').innerHTML = trackHTML(ov, lo, hi, 'agreed');
  document.getElementById('ovRange').innerHTML =
    `confident range <b>${lo.toFixed(1)} – ${hi.toFixed(1)}</b>`;
  document.getElementById('ovEff').innerHTML =
    `<b>${V.overall.equal[3]}</b> reviews<s>·</s><b>6</b> sources<s>·</s>` +
    `effective sample <b>${n}</b><s>·</s>updated <b>2 days ago</b>`;

  const s = STRATEGIES.find(x => x.key === strat);
  document.getElementById('stratBlurb').innerHTML = s.blurb;

  /* what changed, always measured against the baseline everyone else uses */
  const box = document.getElementById('changed');
  if (strat === 'equal'){
    box.innerHTML = `<span class="lead">This is the baseline.</span>
      <span class="muted">Every other review site stops here. Flip the switch to see what it hides.</span>`;
  } else {
    const moved = V.aspects
      .map(a => ({ name:a.name, d:+(a[strat][0] - a.equal[0]).toFixed(1) }))
      .filter(x => Math.abs(x.d) >= 0.2)
      .sort((x,y) => Math.abs(y.d) - Math.abs(x.d)).slice(0,3);
    box.innerHTML = `<span class="lead">Compared with counting every review equally:</span>
      <span class="delta ${ov<bov?'dn':'up'}">Overall ${ov<bov?'▼':'▲'} ${Math.abs(ov-bov).toFixed(1)}</span>` +
      moved.map(m => `<span class="delta ${m.d<0?'dn':'up'}">${m.name.split(',')[0]} ${m.d<0?'▼':'▲'} ${Math.abs(m.d).toFixed(1)}</span>`).join('') +
      `<span class="muted">effective sample falls to ${n}, so the range widens, honestly.</span>`;
  }

  /* aspects, ordered by disagreement, never by score */
  const list = [...V.aspects].sort((a,b) => b.split - a.split);
  document.getElementById('aspects').innerHTML = list.map((a,i) => {
    const [v, l, h] = a[strat]; const heat = heatOf(a.split);
    const row = `<a class="aspect" href="evidence.html" title="Opens the reviews behind this number">
        <div class="aspect-name"><span class="aspect-rank">${i+1}</span>${a.name}</div>
        <div class="aspect-score">${v.toFixed(1)}</div>
        <div>${trackHTML(v, l, h, heat)}</div>
        <div><span class="chip" data-heat="${heat}"><span class="tick"></span>${heatWord(a.split)}</span></div>
        <div class="aspect-cta">${a.n} reviews ›</div>
      </a>`;
    if (!a.why) return row;
    const rows = a.why.rows.map(([lab, val, hi2]) =>
      `<div class="split-bar ${hi2 ? 'hi' : ''}">
         <div class="lab">${lab}</div>
         <div class="meter"><i style="width:${val*10}%"></i></div>
         <div class="val">${val.toFixed(1)}</div>
       </div>`).join('');
    const panel = `<div class="split-why">
        <h4>${a.why.pct}% of this disagreement is explained by ${a.why.covariate}</h4>
        <div class="split-bars">${rows}</div>
        <p class="split-foot">${a.why.note} <a href="evidence.html">See the ${a.n} reviews ›</a></p>
      </div>`;
    /* only the single most contested topic is expanded on arrival.
       the rest disclose on demand, so the page stays scannable. */
    return i === 0 ? row + panel
      : row + `<details class="why-wrap"><summary>Why do they disagree?</summary>${panel}</details>`;
  }).join('');

  /* media vs owners */
  const m = V.media[strat], o = V.owners[strat];
  document.getElementById('vsBlock').innerHTML =
    `<div class="vs-row"><div class="lab">Media</div>
       <div class="vs-meter"><i style="width:${m*10}%"></i></div><div class="val">${m.toFixed(1)}</div></div>
     <div class="vs-row owner"><div class="lab">Owners</div>
       <div class="vs-meter"><i style="width:${o*10}%"></i></div><div class="val">${o.toFixed(1)}</div></div>
     <p class="fact-sub mt16">Widest gap is <b>${V.gap}</b>: media ${V.gapVals[0].toFixed(1)}, owners ${V.gapVals[1].toFixed(1)}.
        Media drive it for a weekend. Owners live with the service centre for five years.</p>`;

  document.querySelectorAll('.seg button').forEach(b =>
    b.setAttribute('aria-pressed', String(b.dataset.strat === strat)));
}

function mountVerdict(V){
  document.getElementById('vName').innerHTML = `${V.name} <span>${V.variant}</span>`;
  document.getElementById('vLine').innerHTML = V.line;
  document.getElementById('vPrice').innerHTML = `${V.price}<small>ex-showroom, Mumbai</small>`;
  document.getElementById('vSpecs').innerHTML =
    V.specs.map(([k,val]) => `<div><dt>${k}</dt><dd>${val}</dd></div>`).join('');
  document.getElementById('facts').innerHTML = V.facts.map(f => `
    <div class="fact ${f.absent ? 'absent' : ''}">
      <div class="fact-k">${f.k}</div>
      <div class="fact-v">${f.stars
        ? `<span class="stars">${'★'.repeat(f.stars)}<i>${'★'.repeat(5-f.stars)}</i></span>`
        : `${f.v}${f.unit ? ` <small>${f.unit}</small>` : ''}`}</div>
      <p class="fact-sub">${f.sub}</p>
    </div>`).join('');

  document.getElementById('seg').innerHTML = STRATEGIES.map(s =>
    `<button data-strat="${s.key}" aria-pressed="false">${s.label}</button>`).join('');
  document.getElementById('seg').addEventListener('click', e => {
    const b = e.target.closest('button'); if (b) renderVerdict(V, b.dataset.strat);
  });
  renderVerdict(V, 'cred');
}

/* ================= shared chrome =================
   One nav and one footer for every screen, so they cannot drift apart.
   In the real build these become two React components. */

const NAV = [
  ['browse.html',  'Browse'],
  ['compare.html', 'Compare'],
  ['method.html',  'Method'],
  ['metrics.html', 'Accuracy']
];

function mountChrome(active, opts){
  opts = opts || {};
  document.body.insertAdjacentHTML('afterbegin', `
    <div class="wf-flag">
      <b>PREVIEW</b>: every screen and every interaction here is real. The figures are
      placeholders until our first full run finishes.
    </div>
    <nav class="nav"><div class="nav-in">
      <a class="brand" href="index.html"><span class="mark">revix</span><small>driven by reviews</small></a>
      <div class="nav-search">
        <input id="navq" type="search" autocomplete="off" spellcheck="false"
               placeholder="Search a car or bike, try &quot;Creta&quot;">
        <div class="sdrop" id="navdrop"></div>
      </div>
      <div class="nav-links">
        ${NAV.map(([h,l]) => `<a href="${h}" class="${h === active ? 'on' : ''}">${l}</a>`).join('')}
      </div>
    </div></nav>`);

  document.body.insertAdjacentHTML('beforeend', `
    <footer class="foot"><div class="wrap foot-in">
      <span class="brand"><span class="mark">revix</span></span>
      <span>Milestone 2 wireframe · M.Sc. Data Science, NMIMS Mumbai</span>
      <span style="margin-left:auto">
        <a href="index.html">Home</a> · <a href="sources.html">Sources</a> ·
        <a href="method.html">Method</a> · <a href="preferences.html">Preferences</a> ·
        <a href="suppressed.html">Thin evidence</a>
      </span>
    </div></footer>`);

  wireSearch(document.getElementById('navq'), document.getElementById('navdrop'));
}

/* ================= search =================
   A real client-side search over the seeded catalogue. Type-ahead filters as
   you type, Enter opens the results page. In the real build this becomes
   GET /variants?q= against the serving layer. */

const CATALOGUE = [
  { brand:'Hyundai', model:'Creta', variant:'SX (O) 1.5 Diesel AT', klass:'car', seg:'Midsize SUV',
    price:'₹19.2L', score:7.8, lo:7.1, hi:8.4, n:412, href:'verdict.html' },
  { brand:'Hyundai', model:'Creta', variant:'SX (O) 1.5 Diesel MT', klass:'car', seg:'Midsize SUV',
    price:'₹18.0L', score:8.4, lo:7.9, hi:8.9, n:126, href:'verdict.html' },
  { brand:'Hyundai', model:'Creta', variant:'SX (O) 1.5 Turbo DCT', klass:'car', seg:'Midsize SUV',
    price:'₹20.1L', score:7.3, lo:6.4, hi:8.1, n:97, href:'verdict.html' },
  { brand:'Hyundai', model:'Creta', variant:'SX 1.5 Petrol IVT', klass:'car', seg:'Midsize SUV',
    price:'₹16.4L', score:7.6, lo:6.9, hi:8.3, n:88, href:'verdict.html' },
  { brand:'Hyundai', model:'Creta', variant:'S 1.5 Petrol MT', klass:'car', seg:'Midsize SUV',
    price:'₹13.0L', score:8.1, lo:7.5, hi:8.7, n:71, href:'verdict.html' },
  { brand:'Hyundai', model:'Creta', variant:'E 1.5 Petrol MT', klass:'car', seg:'Midsize SUV',
    price:'₹11.1L', score:8.2, lo:7.6, hi:8.8, n:54, href:'verdict.html' },
  { brand:'Kia', model:'Seltos', variant:'GTX+ 1.5 Turbo DCT', klass:'car', seg:'Midsize SUV',
    price:'₹20.4L', score:7.9, lo:7.3, hi:8.5, n:386, href:'compare.html' },
  { brand:'Maruti Suzuki', model:'Grand Vitara', variant:'Alpha+ Hybrid', klass:'car', seg:'Midsize SUV',
    price:'₹19.8L', score:7.7, lo:7.0, hi:8.3, n:298, href:'model.html' },
  { brand:'Tata', model:'Nexon', variant:'Fearless+ 1.2 Petrol DCA', klass:'car', seg:'Compact SUV',
    price:'₹13.6L', score:7.6, lo:7.0, hi:8.2, n:271, href:'model.html' },
  { brand:'Tata', model:'Curvv', variant:'Accomplished+ A 1.2', klass:'car', seg:'Midsize SUV',
    price:'₹17.7L', score:7.2, lo:6.3, hi:8.0, n:137, href:'model.html' },
  { brand:'Volkswagen', model:'Taigun', variant:'GT Plus 1.5 TSI DSG', klass:'car', seg:'Midsize SUV',
    price:'₹19.4L', score:8.0, lo:7.4, hi:8.6, n:244, href:'model.html' },
  { brand:'Maruti Suzuki', model:'Swift', variant:'ZXi+ 1.2 AMT', klass:'car', seg:'Hatchback',
    price:'₹9.6L', score:7.9, lo:7.4, hi:8.4, n:352, href:'model.html' },
  { brand:'Mahindra', model:'XUV700', variant:'AX7 L Diesel AT', klass:'car', seg:'Full-size SUV',
    price:'₹25.7L', score:8.1, lo:7.5, hi:8.6, n:318, href:'model.html' },
  { brand:'Citroen', model:'C3 Aircross', variant:'Shine 1.2 Turbo MT', klass:'car', seg:'Midsize SUV',
    price:'₹11.6L', score:null, n:19, href:'suppressed.html' },

  { brand:'Royal Enfield', model:'Classic 350', variant:'Dual-channel ABS', klass:'two_wheeler', seg:'Cruiser',
    price:'₹2.32L', score:7.5, lo:6.8, hi:8.1, n:368, href:'verdict-bike.html' },
  { brand:'Royal Enfield', model:'Hunter 350', variant:'Retro', klass:'two_wheeler', seg:'Roadster',
    price:'₹1.75L', score:7.8, lo:7.2, hi:8.3, n:214, href:'model.html' },
  { brand:'Honda', model:'Activa', variant:'6G Standard', klass:'two_wheeler', seg:'Scooter',
    price:'₹0.81L', score:8.3, lo:7.9, hi:8.6, n:496, href:'model.html' },
  { brand:'Hero', model:'Splendor Plus', variant:'i3S Drum', klass:'two_wheeler', seg:'Commuter',
    price:'₹0.79L', score:8.0, lo:7.6, hi:8.4, n:441, href:'model.html' },
  { brand:'Bajaj', model:'Pulsar NS200', variant:'ABS', klass:'two_wheeler', seg:'Sport',
    price:'₹1.62L', score:7.4, lo:6.7, hi:8.0, n:187, href:'model.html' },
  { brand:'TVS', model:'Jupiter', variant:'125 SmartXonnect', klass:'two_wheeler', seg:'Scooter',
    price:'₹0.92L', score:8.1, lo:7.6, hi:8.5, n:263, href:'model.html' },
  { brand:'Yamaha', model:'MT-15', variant:'V2', klass:'two_wheeler', seg:'Sport',
    price:'₹1.71L', score:7.7, lo:7.0, hi:8.3, n:156, href:'model.html' }
];

function searchHits(q, limit){
  q = (q || '').trim().toLowerCase();
  if (!q) return [];
  const toks = q.split(/\s+/);
  return CATALOGUE
    .map(v => ({ v, hay: (v.brand + ' ' + v.model + ' ' + v.variant).toLowerCase() }))
    .filter(x => toks.every(t => x.hay.indexOf(t) !== -1))
    .slice(0, limit || 7)
    .map(x => x.v);
}

function hitHTML(v){
  const score = v.score === null
    ? '<span class="vr">not enough evidence</span>'
    : v.score.toFixed(1) + '<span class="vr"> / 10</span>';
  return `<a class="sitem" href="${v.href}">
      <div>
        <div class="nm">${v.brand} ${v.model}</div>
        <div class="vr">${v.variant} &middot; ${v.seg} &middot; ${v.price}</div>
      </div>
      <div class="sc">${score}</div>
    </a>`;
}

function wireSearch(input, drop){
  if (!input || !drop) return;
  function render(){
    const q = input.value.trim();
    if (!q){ drop.classList.remove('on'); drop.innerHTML = ''; return; }
    const hits = searchHits(q);
    drop.innerHTML = hits.length
      ? hits.map(hitHTML).join('') +
        `<a class="sitem more" href="search.html?q=${encodeURIComponent(q)}">
           <div class="nm">See all results for &ldquo;${q}&rdquo;</div><div class="sc">&rsaquo;</div></a>`
      : `<div class="snone">Nothing in our catalogue matches &ldquo;${q}&rdquo;.
           We cover 142 vehicles chosen for having enough reviews to say something useful.
           <a href="browse.html">Browse them all.</a></div>`;
    drop.classList.add('on');
  }
  input.addEventListener('input', render);
  input.addEventListener('focus', render);
  input.addEventListener('keydown', function(e){
    if (e.key === 'Enter' && input.value.trim())
      location.href = 'search.html?q=' + encodeURIComponent(input.value.trim());
    if (e.key === 'Escape') drop.classList.remove('on');
  });
  document.addEventListener('click', function(e){
    if (!drop.contains(e.target) && e.target !== input) drop.classList.remove('on');
  });
}

/* the results page renders from ?q= */
function mountSearchPage(){
  const q = new URLSearchParams(location.search).get('q') || '';
  const box = document.getElementById('results');
  const head = document.getElementById('resultHead');
  const input = document.getElementById('pageq');
  if (input) input.value = q;

  const hits = searchHits(q, 50);
  const models = [...new Set(hits.map(v => v.brand + '|' + v.model))];

  head.innerHTML = q
    ? `<h1>Results for &ldquo;${q}&rdquo;</h1>
       <p>${hits.length} ${hits.length === 1 ? 'vehicle' : 'vehicles'} matched,
          across ${models.length} ${models.length === 1 ? 'model' : 'models'}.</p>`
    : `<h1>Search</h1><p>Type a make, a model or an exact variant.</p>`;

  if (!q){ box.innerHTML = ''; return; }

  if (!hits.length){
    box.innerHTML = `<div class="card"><div class="empty">
        <div class="icon">&#9906;</div>
        <h2>Nothing matched &ldquo;${q}&rdquo;.</h2>
        <p>We cover 142 vehicles, chosen because they have enough reviews for us to say
           something useful. If yours is not here yet, it is because we could not find
           enough evidence to give you an honest answer.</p>
        <p style="margin-top:18px"><a class="fpill on" href="browse.html">Browse the catalogue &rsaquo;</a></p>
      </div></div>`;
    return;
  }

  box.innerHTML = `<div class="card tbl-wrap"><table class="tbl">
      <thead><tr>
        <th>Vehicle</th><th>Variant</th><th>Type</th>
        <th class="n">Price</th><th class="n">Verdict</th><th class="n">Reviews</th><th></th>
      </tr></thead>
      <tbody>${hits.map(v => `
        <tr onclick="location.href='${v.href}'" style="cursor:pointer">
          <td class="strong">${v.brand} ${v.model}</td>
          <td>${v.variant}</td>
          <td class="muted">${v.seg}</td>
          <td class="n">${v.price}</td>
          <td class="n ${v.score === null ? 'muted' : 'strong'}">${v.score === null ? 'No verdict' : v.score.toFixed(1)}</td>
          <td class="n">${v.n}</td>
          <td class="n muted">&rsaquo;</td>
        </tr>`).join('')}
      </tbody></table></div>`;
}
