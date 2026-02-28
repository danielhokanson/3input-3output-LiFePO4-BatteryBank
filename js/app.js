// ===================================================================
// Solar Battery System — Build Spec App
// SPA with localStorage progress + JSON file export/import
// ===================================================================

let specData = null;
let progress = null;
let activeSection = 'overview';
let saveTimeout = null;

const STORAGE_KEY = 'solar-build-progress';

// ===================== INIT =====================
async function init() {
  const res = await fetch('data/spec.json');
  specData = await res.json();
  loadProgress();
  buildSidebar();
  renderSection('overview');
  updateGlobalProgress();
  bindGlobalEvents();
}

// ===================== PROGRESS PERSISTENCE =====================
function loadProgress() {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    try { progress = JSON.parse(stored); return; } catch(e) {}
  }
  // Load defaults from file
  progress = getDefaultProgress();
}

function getDefaultProgress() {
  return {
    version: "3.1",
    lastUpdated: null,
    buildSteps: Object.fromEntries(
      Array.from({length: 12}, (_, i) => [
        String(i+1),
        { completed: false, checkpoints: {} }
      ])
    ),
    notes: {},
    measurements: {}
  };
}

function saveProgress() {
  progress.lastUpdated = new Date().toISOString();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
  showSaveToast();
}

function debounceSave() {
  clearTimeout(saveTimeout);
  saveTimeout = setTimeout(saveProgress, 600);
}

function showSaveToast() {
  const t = document.getElementById('save-toast');
  t.textContent = `✓ Saved ${new Date().toLocaleTimeString()}`;
  t.classList.add('save-toast--visible');
  setTimeout(() => t.classList.remove('save-toast--visible'), 1800);
}

function exportProgress() {
  const blob = new Blob([JSON.stringify(progress, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `solar-build-progress-${new Date().toISOString().split('T')[0]}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function importProgress() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      if (data.buildSteps) {
        progress = data;
        saveProgress();
        renderSection(activeSection);
        updateSidebarBadges();
        updateGlobalProgress();
      }
    } catch(err) {
      alert('Invalid progress file.');
    }
  };
  input.click();
}

function resetProgress() {
  if (confirm('Reset ALL build progress? This cannot be undone.')) {
    progress = getDefaultProgress();
    saveProgress();
    renderSection(activeSection);
    updateSidebarBadges();
    updateGlobalProgress();
  }
}

// ===================== SIDEBAR =====================
function buildSidebar() {
  const nav = document.getElementById('nav');
  let html = '';

  // Overview
  html += `<div class="nav__section-label">System</div>`;
  html += navItem('overview', '📋', 'System Overview');

  // Spec sections
  html += `<div class="nav__section-label">Specification</div>`;
  for (const s of specData.sections) {
    if (s.id === 'build') continue; // build gets its own group
    html += navItem(s.id, s.icon, s.title, s.number);
  }

  // Build
  html += `<div class="nav__section-label">Construction</div>`;
  const buildSection = specData.sections.find(s => s.id === 'build');
  html += navItem('build', buildSection.icon, buildSection.title, buildSection.number);

  // Wiring
  html += navItem('wiring', '🔌', 'Wiring Schematic');

  // Tools
  html += `<div class="nav__section-label">Tools</div>`;
  html += navItem('tools', '🛠️', 'Export / Import');

  nav.innerHTML = html;
  updateSidebarBadges();
}

function navItem(id, icon, text, number) {
  const cls = id === activeSection ? ' nav__item--active' : '';
  return `<a class="nav__item${cls}" data-section="${id}" onclick="navigateTo('${id}')">
    <span class="nav__item-icon">${icon}</span>
    <span class="nav__item-text">${text}</span>
    <span class="nav__item-badge" id="badge-${id}"></span>
  </a>`;
}

function updateSidebarBadges() {
  // Build step badge
  const buildBadge = document.getElementById('badge-build');
  if (buildBadge) {
    const done = Object.values(progress.buildSteps).filter(s => s.completed).length;
    if (done === 12) {
      buildBadge.textContent = '✓';
      buildBadge.className = 'nav__item-badge nav__item-badge--done';
    } else if (done > 0) {
      buildBadge.textContent = `${done}/12`;
      buildBadge.className = 'nav__item-badge';
    } else {
      buildBadge.textContent = '';
    }
  }
}

function navigateTo(id) {
  activeSection = id;
  // Update nav active state
  document.querySelectorAll('.nav__item').forEach(el => {
    el.classList.toggle('nav__item--active', el.dataset.section === id);
  });
  renderSection(id);
  // Close mobile sidebar
  document.getElementById('sidebar').classList.remove('sidebar--open');
  document.getElementById('sidebar-overlay').classList.remove('sidebar-overlay--visible');
  // Scroll to top
  document.querySelector('.main').scrollTop = 0;
}

// ===================== SECTION RENDERING =====================
function renderSection(id) {
  const main = document.getElementById('content');

  if (id === 'overview') {
    main.innerHTML = renderOverview();
  } else if (id === 'build') {
    main.innerHTML = renderBuildSteps();
  } else if (id === 'wiring') {
    main.innerHTML = renderWiringSchematic();
  } else if (id === 'tools') {
    main.innerHTML = renderTools();
  } else {
    const section = specData.sections.find(s => s.id === id);
    if (section) {
      main.innerHTML = renderSpecSection(section);
    }
  }
}

// ===================== OVERVIEW =====================
function renderOverview() {
  const o = specData.overview;
  const cards = Object.entries(o).map(([key, val]) => {
    const label = key.replace(/_/g, ' ');
    const isAccent = ['nominal_capacity', 'solar_inputs', 'autonomy'].includes(key);
    return `<div class="overview-card">
      <div class="overview-card__label">${label}</div>
      <div class="overview-card__value${isAccent ? ' overview-card__value--accent' : ''}">${val}</div>
    </div>`;
  }).join('');

  return `
    <div class="section section--active">
      <div class="section__header">
        <div class="section__number">Section 1</div>
        <h1 class="section__title">System Overview</h1>
      </div>
      <div class="overview-grid">${cards}</div>
      <div class="block">
        <div class="block__text">
          This specification covers the design and construction of a consolidated LiFePO4 battery system built from three salvaged Solariver solar pump units. All three pump controllers accept 12V DC input and are designed to operate directly from solar or battery — no boost converters are required. The system uses 12 Grade B LiFePO4 cells in a 4S3P configuration for 7,680 Wh of capacity, charges from three solar panel inputs (2× 40W, 1× 25W) via individual MPPT controllers, and is housed in a custom 3D-printed enclosure styled as a landscape boulder for outdoor installation in Salt Lake City.
        </div>
      </div>
    </div>`;
}

// ===================== SPEC SECTIONS =====================
function renderSpecSection(section) {
  let blocks = '';
  for (const item of section.content) {
    blocks += renderContentBlock(item);
  }

  return `
    <div class="section section--active">
      <div class="section__header">
        <div class="section__number">Section ${section.number}</div>
        <h1 class="section__title">${section.icon} ${section.title}</h1>
      </div>
      ${blocks}
    </div>`;
}

function renderContentBlock(item) {
  switch (item.type) {
    case 'heading':
      return `<div class="block"><h3 class="block__heading">${item.text}</h3></div>`;

    case 'text':
      return `<div class="block"><p class="block__text">${item.body}</p></div>`;

    case 'list':
      const lis = item.items.map(i => `<li>${i}</li>`).join('');
      return `<div class="block"><ul class="block__list">${lis}</ul></div>`;

    case 'callout':
      return `<div class="callout callout--${item.severity}">${item.body}</div>`;

    case 'table':
      return renderTable(item.headers, item.rows);

    case 'steps':
      return ''; // handled separately in build view

    default:
      return '';
  }
}

function renderTable(headers, rows) {
  const ths = headers.map(h => `<th>${h}</th>`).join('');
  const trs = rows.map(r => {
    const tds = r.map(c => `<td>${c}</td>`).join('');
    return `<tr>${tds}</tr>`;
  }).join('');

  return `<div class="block"><table class="spec-table">
    <thead><tr>${ths}</tr></thead>
    <tbody>${trs}</tbody>
  </table></div>`;
}

// ===================== BUILD STEPS =====================
function renderBuildSteps() {
  const buildSection = specData.sections.find(s => s.id === 'build');
  const stepsData = buildSection.content.find(c => c.type === 'steps').items;

  let html = `
    <div class="section section--active">
      <div class="section__header">
        <div class="section__number">Section 9 — Construction</div>
        <h1 class="section__title">🔨 Build Sequence</h1>
      </div>`;

  for (const step of stepsData) {
    const sp = progress.buildSteps[String(step.step)] || { completed: false, checkpoints: {} };
    const checkedCount = Object.values(sp.checkpoints).filter(Boolean).length;
    const totalChecks = step.checkpoints.length;
    const allChecked = checkedCount === totalChecks;
    const completeClass = allChecked ? ' build-step--complete' : '';
    const progressClass = allChecked ? ' build-step__progress--done' : '';
    const progressText = allChecked ? '✓ Complete' : `${checkedCount}/${totalChecks}`;

    let checkpointsHtml = '';
    step.checkpoints.forEach((cp, idx) => {
      const checked = sp.checkpoints[idx] ? ' checkpoint--checked' : '';
      checkpointsHtml += `
        <label class="checkpoint${checked}" data-step="${step.step}" data-idx="${idx}" onclick="toggleCheckpoint(${step.step}, ${idx})">
          <div class="checkpoint__box"><span class="checkpoint__check">✓</span></div>
          <span class="checkpoint__label">${cp}</span>
        </label>`;
    });

    // Notes for this step
    const noteVal = progress.notes[`step-${step.step}`] || '';

    html += `
      <div class="build-step${completeClass}" id="step-${step.step}">
        <div class="build-step__header" onclick="toggleStep(${step.step})">
          <div class="build-step__number">${step.step}</div>
          <div class="build-step__title">${step.title}</div>
          <div class="build-step__progress${progressClass}">${progressText}</div>
          <div class="build-step__toggle">▾</div>
        </div>
        <div class="build-step__body">
          <div class="build-step__desc">${step.body}</div>
          ${checkpointsHtml}
          <div class="notes-area">
            <div class="notes-area__label">Notes</div>
            <textarea class="notes-area__input" placeholder="Observations, measurements, issues..."
              data-step="${step.step}"
              onchange="saveNote(${step.step}, this.value)"
              oninput="debounceSave()">${noteVal}</textarea>
          </div>
        </div>
      </div>`;
  }

  html += '</div>';
  return html;
}

function toggleStep(step) {
  const el = document.getElementById(`step-${step}`);
  el.classList.toggle('build-step--open');
}

function toggleCheckpoint(step, idx) {
  const sp = progress.buildSteps[String(step)];
  if (!sp.checkpoints) sp.checkpoints = {};
  sp.checkpoints[idx] = !sp.checkpoints[idx];

  // Check if all checkpoints are done
  const buildSection = specData.sections.find(s => s.id === 'build');
  const stepsData = buildSection.content.find(c => c.type === 'steps').items;
  const stepData = stepsData.find(s => s.step === step);
  const total = stepData.checkpoints.length;
  const done = Object.values(sp.checkpoints).filter(Boolean).length;
  sp.completed = (done === total);

  saveProgress();
  renderSection('build');
  updateSidebarBadges();
  updateGlobalProgress();

  // Re-open the step that was just clicked
  const el = document.getElementById(`step-${step}`);
  if (el) el.classList.add('build-step--open');
}

function saveNote(step, value) {
  progress.notes[`step-${step}`] = value;
  debounceSave();
}

// ===================== WIRING SCHEMATIC =====================
function renderWiringSchematic() {
  return `
    <div class="section section--active">
      <div class="section__header">
        <div class="section__number">Reference</div>
        <h1 class="section__title">🔌 Wiring Schematic</h1>
      </div>

      <div class="schematic-embed">
        <div class="schematic-legend">
          <div class="schematic-legend__item"><div class="schematic-legend__swatch" style="background:#e8a735"></div>Solar (18V)</div>
          <div class="schematic-legend__item"><div class="schematic-legend__swatch" style="background:#e85050"></div>Battery +</div>
          <div class="schematic-legend__item"><div class="schematic-legend__swatch" style="background:#4090e0"></div>Battery −</div>
          <div class="schematic-legend__item"><div class="schematic-legend__swatch" style="background:#40c070"></div>Load Output</div>
        </div>

        <svg viewBox="0 0 900 620" style="width:100%;max-width:900px;background:var(--bg-deep);border-radius:6px;">
          <!-- Zones -->
          <rect x="20" y="280" width="340" height="320" rx="8" fill="rgba(60,30,30,0.2)" stroke="#3a2020" stroke-width="1" stroke-dasharray="6 3"/>
          <text x="35" y="300" font-family="DM Mono,monospace" font-size="9" fill="#5a4040" text-transform="uppercase" letter-spacing="1.5">Battery Zone</text>

          <rect x="390" y="20" width="490" height="580" rx="8" fill="rgba(20,35,55,0.15)" stroke="#1a2a40" stroke-width="1" stroke-dasharray="6 3"/>
          <text x="405" y="40" font-family="DM Mono,monospace" font-size="9" fill="#3a5070" letter-spacing="1.5">Electronics Zone</text>

          <!-- PANELS -->
          ${svgBox(420, 60, 120, 44, 'Panel 1 — 40W', '18V / MC4', '#e8a735')}
          ${svgBox(570, 60, 120, 44, 'Panel 2 — 40W', '18V / MC4', '#e8a735')}
          ${svgBox(720, 60, 120, 44, 'Panel 3 — 25W', '18V / MC4', '#e8a735')}

          <!-- Solar wires -->
          <line x1="480" y1="104" x2="480" y2="140" stroke="#e8a735" stroke-width="2"/>
          <line x1="630" y1="104" x2="630" y2="140" stroke="#e8a735" stroke-width="2"/>
          <line x1="780" y1="104" x2="780" y2="140" stroke="#e8a735" stroke-width="2"/>

          <!-- MPPTs -->
          ${svgBox(420, 140, 120, 70, 'MPPT 1', 'Tracer 2210AN', '#5090c0')}
          ${svgBox(570, 140, 120, 70, 'MPPT 2', 'Tracer 2210AN', '#5090c0')}
          ${svgBox(720, 140, 120, 70, 'MPPT 3', 'Tracer 2210AN', '#5090c0')}

          <!-- Bus bars -->
          <rect x="410" y="265" width="340" height="18" rx="3" fill="#1a1212" stroke="#e85050" stroke-width="1.2"/>
          <text x="580" y="278" font-family="DM Mono,monospace" font-size="8" fill="#e88080" text-anchor="middle">+12.8V POSITIVE BUS (8 AWG)</text>

          <rect x="410" y="295" width="340" height="18" rx="3" fill="#0e1520" stroke="#4090e0" stroke-width="1.2"/>
          <text x="580" y="308" font-family="DM Mono,monospace" font-size="8" fill="#80b0e0" text-anchor="middle">NEGATIVE BUS (8 AWG)</text>

          <!-- MPPT to bus (pos + neg) -->
          <line x1="468" y1="210" x2="468" y2="265" stroke="#e85050" stroke-width="2"/>
          <line x1="490" y1="210" x2="490" y2="295" stroke="#4090e0" stroke-width="2"/>
          <line x1="618" y1="210" x2="618" y2="265" stroke="#e85050" stroke-width="2"/>
          <line x1="640" y1="210" x2="640" y2="295" stroke="#4090e0" stroke-width="2"/>
          <line x1="768" y1="210" x2="768" y2="265" stroke="#e85050" stroke-width="2"/>
          <line x1="790" y1="210" x2="790" y2="295" stroke="#4090e0" stroke-width="2"/>

          <!-- ANL Fuse -->
          <rect x="335" y="268" width="50" height="14" rx="2" fill="#1a1a10" stroke="#c0a040" stroke-width="1"/>
          <text x="360" y="279" font-family="DM Mono,monospace" font-size="7" fill="#c0a040" text-anchor="middle">80A</text>

          <!-- Battery pack -->
          ${svgBox(40, 330, 300, 100, '4S3P LiFePO4 Battery Pack', '12×200Ah Grade B — 12.8V / 7,680 Wh', '#e85050')}

          <!-- Cell blocks inside -->
          <rect x="55"  y="370" width="60" height="40" rx="3" fill="#140c0c" stroke="#4a2020" stroke-width="0.8"/>
          <text x="85" y="394" font-family="DM Mono,monospace" font-size="7" fill="#7a4040" text-anchor="middle">S1 3P</text>
          <rect x="125" y="370" width="60" height="40" rx="3" fill="#140c0c" stroke="#4a2020" stroke-width="0.8"/>
          <text x="155" y="394" font-family="DM Mono,monospace" font-size="7" fill="#7a4040" text-anchor="middle">S2 3P</text>
          <rect x="195" y="370" width="60" height="40" rx="3" fill="#140c0c" stroke="#4a2020" stroke-width="0.8"/>
          <text x="225" y="394" font-family="DM Mono,monospace" font-size="7" fill="#7a4040" text-anchor="middle">S3 3P</text>
          <rect x="265" y="370" width="60" height="40" rx="3" fill="#140c0c" stroke="#4a2020" stroke-width="0.8"/>
          <text x="295" y="394" font-family="DM Mono,monospace" font-size="7" fill="#7a4040" text-anchor="middle">S4 3P</text>

          <!-- BMS -->
          ${svgBox(60, 450, 260, 40, 'BMS — JK B2A20S20P', '4S 60A / Balance / Temp Cutoff', '#4090e0')}

          <!-- Battery → ANL → bus -->
          <polyline points="340,370 370,370 370,275 385,275" fill="none" stroke="#e85050" stroke-width="2"/>
          <circle cx="370" cy="275" r="2.5" fill="#e85050"/>
          <text x="345" y="362" font-family="DM Mono,monospace" font-size="7" fill="#c0a040">≤30cm</text>

          <!-- Battery neg through BMS to bus -->
          <polyline points="40,390 30,390 30,510 190,510" fill="none" stroke="#4090e0" stroke-width="2"/>
          <line x1="190" y1="490" x2="190" y2="510" stroke="#4090e0" stroke-width="2"/>
          <polyline points="190,510 400,510 400,304 410,304" fill="none" stroke="#4090e0" stroke-width="2"/>
          <circle cx="190" cy="510" r="2.5" fill="#4090e0"/>

          <!-- Load output wires -->
          <polyline points="480,210 480,245 510,245 510,410" fill="none" stroke="#40c070" stroke-width="1.8"/>
          <polyline points="630,210 630,245 600,245 600,410" fill="none" stroke="#40c070" stroke-width="1.8"/>
          <polyline points="780,210 780,245 700,245 700,410" fill="none" stroke="#40c070" stroke-width="1.8"/>

          <!-- Pump controllers -->
          ${svgBox(440, 415, 130, 50, 'Pump Ctrl 1', '470 GPH / ~25W', '#40c070')}
          ${svgBox(590, 415, 130, 50, 'Pump Ctrl 2', '470 GPH / ~25W', '#40c070')}
          ${svgBox(740, 415, 130, 50, 'Pump Ctrl 3', '235 GPH / ~12W', '#40c070')}

          <!-- Fuse block -->
          ${svgBox(580, 340, 140, 40, 'Fuse Block', '5A / 5A / 3A blade', '#c0a040')}
          <line x1="650" y1="283" x2="650" y2="340" stroke="#e85050" stroke-width="1.5"/>
          <circle cx="650" cy="283" r="2.5" fill="#e85050"/>

          <!-- Fuse to pump backup paths (dashed) -->
          <polyline points="600,380 505,380 505,415" fill="none" stroke="#e8505060" stroke-width="1.2" stroke-dasharray="4 2"/>
          <line x1="650" y1="380" x2="655" y2="415" fill="none" stroke="#e8505060" stroke-width="1.2" stroke-dasharray="4 2"/>
          <polyline points="700,380 805,380 805,415" fill="none" stroke="#e8505060" stroke-width="1.2" stroke-dasharray="4 2"/>

          <!-- Pumps -->
          ${svgBox(440, 490, 130, 35, 'Pump 1 — 470 GPH', '', '#40c070')}
          ${svgBox(590, 490, 130, 35, 'Pump 2 — 470 GPH', '', '#40c070')}
          ${svgBox(740, 490, 130, 35, 'Pump 3 — 235 GPH', '', '#40c070')}

          <line x1="505" y1="465" x2="505" y2="490" stroke="#40c070" stroke-width="1.5"/>
          <line x1="655" y1="465" x2="655" y2="490" stroke="#40c070" stroke-width="1.5"/>
          <line x1="805" y1="465" x2="805" y2="490" stroke="#40c070" stroke-width="1.5"/>

          <!-- Thermal system -->
          ${svgBox(40, 530, 130, 40, 'PTC Heater', '12V / 10–15W', '#c060e0')}
          ${svgBox(200, 530, 130, 40, 'Temp Probe', 'NTC → STC-1000', '#80b0d0')}

          <!-- Thermostat in electronics zone -->
          ${svgBox(420, 550, 150, 40, 'STC-1000 Thermostat', 'Heat + Cool relays', '#c060e0')}

          <!-- Thermal wiring -->
          <polyline points="420,570 170,570 170,530" fill="none" stroke="#c060e0" stroke-width="1.2" stroke-dasharray="5 3"/>
          <polyline points="330,550 380,550 380,575 420,575" fill="none" stroke="#80b0d0" stroke-width="1" stroke-dasharray="3 2"/>

          <!-- Fan -->
          ${svgBox(600, 550, 130, 40, 'Vent Fan', '12V / 3–5W', '#c060e0')}
          <line x1="570" y1="570" x2="600" y2="570" stroke="#c060e0" stroke-width="1.2" stroke-dasharray="5 3"/>

        </svg>
      </div>

      <div class="block">
        <h3 class="block__heading">Power Flow Summary</h3>
        <p class="block__text">
          <strong style="color:#e8a735">Solar path:</strong> Panels → MPPT controllers → Load output terminals → Pump controllers (primary, solar-prioritized)<br><br>
          <strong style="color:#e85050">Battery path:</strong> LiFePO4 bank → BMS (neg bus) → ANL fuse (pos bus) → Distribution bus → Fuse block → Pump controllers (backup)<br><br>
          <strong style="color:#c060e0">Thermal path:</strong> STC-1000 thermostat → PTC heater relay (winter) + Fan relay (summer). Temp probe on cell surface. BMS charge inhibit below 0°C.
        </p>
      </div>
    </div>`;
}

function svgBox(x, y, w, h, label, sub, accentColor) {
  return `
    <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="5"
      fill="#111822" stroke="${accentColor}40" stroke-width="1"/>
    <text x="${x + w/2}" y="${y + (sub ? h/2 - 3 : h/2 + 3)}" 
      font-family="Outfit,sans-serif" font-size="9" font-weight="600" 
      fill="#d0d8e4" text-anchor="middle">${label}</text>
    ${sub ? `<text x="${x + w/2}" y="${y + h/2 + 10}" 
      font-family="DM Mono,monospace" font-size="7" 
      fill="#6a7a90" text-anchor="middle">${sub}</text>` : ''}`;
}

// ===================== TOOLS PAGE =====================
function renderTools() {
  const stepsCompleted = Object.values(progress.buildSteps).filter(s => s.completed).length;
  const totalCheckpoints = getTotalCheckpoints();
  const checkedCheckpoints = getCheckedCheckpoints();
  const lastSaved = progress.lastUpdated
    ? new Date(progress.lastUpdated).toLocaleString()
    : 'Never';

  return `
    <div class="section section--active">
      <div class="section__header">
        <div class="section__number">Tools</div>
        <h1 class="section__title">🛠️ Export / Import Progress</h1>
      </div>

      <div class="overview-grid">
        <div class="overview-card">
          <div class="overview-card__label">Steps Completed</div>
          <div class="overview-card__value overview-card__value--accent">${stepsCompleted} / 12</div>
        </div>
        <div class="overview-card">
          <div class="overview-card__label">Checkpoints</div>
          <div class="overview-card__value">${checkedCheckpoints} / ${totalCheckpoints}</div>
        </div>
        <div class="overview-card">
          <div class="overview-card__label">Last Saved</div>
          <div class="overview-card__value">${lastSaved}</div>
        </div>
      </div>

      <div class="block" style="margin-top:20px">
        <p class="block__text">Progress is stored in your browser's localStorage. Use the buttons below to export a JSON backup or import a previous save. You can also reset all progress.</p>
      </div>

      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:20px">
        <button onclick="exportProgress()" style="
          background:var(--accent-load);color:var(--bg-deep);
          border:none;border-radius:6px;padding:10px 20px;
          font-family:var(--sans);font-weight:600;font-size:0.9rem;cursor:pointer;">
          ⬇ Export Progress JSON
        </button>
        <button onclick="importProgress()" style="
          background:var(--bg-raised);color:var(--text-primary);
          border:1px solid var(--border-mid);border-radius:6px;padding:10px 20px;
          font-family:var(--sans);font-weight:600;font-size:0.9rem;cursor:pointer;">
          ⬆ Import Progress JSON
        </button>
        <button onclick="resetProgress()" style="
          background:transparent;color:var(--accent-danger);
          border:1px solid var(--accent-danger);border-radius:6px;padding:10px 20px;
          font-family:var(--sans);font-weight:500;font-size:0.9rem;cursor:pointer;">
          ✕ Reset All Progress
        </button>
      </div>
    </div>`;
}

// ===================== PROGRESS CALCULATION =====================
function getTotalCheckpoints() {
  const buildSection = specData.sections.find(s => s.id === 'build');
  const stepsData = buildSection.content.find(c => c.type === 'steps').items;
  return stepsData.reduce((sum, s) => sum + s.checkpoints.length, 0);
}

function getCheckedCheckpoints() {
  let count = 0;
  for (const sp of Object.values(progress.buildSteps)) {
    count += Object.values(sp.checkpoints || {}).filter(Boolean).length;
  }
  return count;
}

function updateGlobalProgress() {
  const total = getTotalCheckpoints();
  const done = getCheckedCheckpoints();
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  const fill = document.getElementById('global-progress-fill');
  const text = document.getElementById('global-progress-text');
  if (fill) fill.style.width = pct + '%';
  if (text) text.textContent = pct + '%';
}

// ===================== GLOBAL EVENTS =====================
function bindGlobalEvents() {
  document.getElementById('hamburger').addEventListener('click', () => {
    document.getElementById('sidebar').classList.toggle('sidebar--open');
    document.getElementById('sidebar-overlay').classList.toggle('sidebar-overlay--visible');
  });

  document.getElementById('sidebar-overlay').addEventListener('click', () => {
    document.getElementById('sidebar').classList.remove('sidebar--open');
    document.getElementById('sidebar-overlay').classList.remove('sidebar-overlay--visible');
  });
}

// ===================== START =====================
document.addEventListener('DOMContentLoaded', init);
