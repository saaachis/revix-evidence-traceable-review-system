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
  ['metrics.html', 'Metrics'],
  ['admin.html',   'Admin']
];

function mountChrome(active, opts){
  opts = opts || {};
  document.body.insertAdjacentHTML('afterbegin', `
    <div class="wf-flag">
      <b>WIREFRAME</b>: Milestone 2. Layout and interaction are real; every figure is a
      placeholder until the pipeline runs.
      ${opts.home === false ? '<a href="index.html">Back to the flow</a>' : ''}
    </div>
    <nav class="nav"><div class="nav-in">
      <a class="brand" href="index.html"><span class="mark">revix</span><small>driven by reviews</small></a>
      <a class="nav-search" href="search.html">Search a car or bike, try &ldquo;Creta&rdquo;</a>
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
}
