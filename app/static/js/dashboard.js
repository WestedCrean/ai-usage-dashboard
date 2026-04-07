/* ── AI Usage Dashboard — Frontend ──────────────────────────────────────── */
'use strict';

// ── Helpers ───────────────────────────────────────────────────────────────────

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function fmt(value, type = 'number') {
  if (value === null || value === undefined) return '—';
  if (type === 'tokens') return Number(value).toLocaleString();
  if (type === 'requests') return Number(value).toLocaleString();
  if (type === 'ms') return Number(value).toFixed(0) + ' ms';
  return String(value);
}

function fmtMoney(value, unit = 'USD') {
  if (value === null || value === undefined) return '—';
  const currency = (unit || 'USD').toUpperCase();
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: 4,
    }).format(Number(value));
  } catch {
    return `${Number(value).toFixed(4)} ${currency}`;
  }
}

function parseIso(iso) {
  if (!iso) return null;
  if (iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso)) return new Date(iso);
  return new Date(iso + 'Z');
}

function relTime(iso) {
  if (!iso) return '—';
  const d = parseIso(iso);
  if (!d || Number.isNaN(d.getTime())) return '—';
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 5) return 'just now';
  if (diff < 60) return diff + 's ago';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function absTime(iso) {
  if (!iso) return '—';
  const d = parseIso(iso);
  if (!d || Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
}

function resetChartBody(bodySelector, canvasId) {
  const body = $(bodySelector);
  if (!body) return null;
  body.innerHTML = `<canvas id="${canvasId}"></canvas>`;
  return $(`#${canvasId}`);
}

function showToast(msg, type = 'info', duration = 3500) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  const container = $('#toast-container');
  container.appendChild(el);
  setTimeout(() => el.remove(), duration);
}

// Source badge HTML
function sourceBadge(source) {
  const labels = { official: 'Official', inferred: 'Inferred', experimental: 'Experimental', unavailable: 'N/A' };
  const label = labels[source] || source;
  return `<span class="source-tag ${source}">${label}</span>`;
}

// ── Chart defaults ────────────────────────────────────────────────────────────

Chart.defaults.color = '#8b95a9';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.borderColor = 'rgba(255,255,255,0.07)';

const PROVIDER_COLORS = {
  openai:     '#10a37f',
  anthropic:  '#d97757',
  gemini:     '#4285f4',
  mistral:    '#ff7000',
  openrouter: '#9b59b6',
  codex:      '#10a37f',
  claude_code:'#d97757',
  gemini_cli: '#4285f4',
  mistral_vibe:'#ff7000',
};

function providerColor(id) {
  return PROVIDER_COLORS[id] || '#4f8eff';
}

// ── Navigation ────────────────────────────────────────────────────────────────

const sectionTitles = {
  overview:       'Overview',
  providers:      'Providers',
  models:         'Model Breakdown',
  timeseries:     'Usage History',
  subscriptions:  'Subscriptions',
  windows:        'Usage Windows',
  tests:          'Endpoint Tests',
};

function activateSection(name) {
  $$('.nav-item').forEach(el => el.classList.remove('active'));
  $$('.section').forEach(el => el.classList.remove('active'));
  const navEl = $(`.nav-item[data-section="${name}"]`);
  const sectionEl = $(`#section-${name}`);
  if (navEl) navEl.classList.add('active');
  if (sectionEl) sectionEl.classList.add('active');
  const titleEl = $('#page-title');
  if (titleEl) titleEl.textContent = sectionTitles[name] || name;
}

document.addEventListener('DOMContentLoaded', () => {
  $$('.nav-item').forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      activateSection(el.dataset.section);
    });
  });
});

// ── State ────────────────────────────────────────────────────────────────────

let chartSpendProvider = null;
let chartTokensProvider = null;
let chartTimeseries = null;
let isRefreshing = false;

// ── API ──────────────────────────────────────────────────────────────────────

async function api(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json();
}

async function post(path) {
  const resp = await fetch(path, { method: 'POST' });
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json();
}

// ── Load & render ─────────────────────────────────────────────────────────────

async function loadAll() {
  const [overview, providers, models, windows, timeseries, tests, status, subscriptions] = await Promise.allSettled([
    api('/api/overview'),
    api('/api/providers'),
    api('/api/models'),
    api('/api/windows'),
    api('/api/timeseries'),
    api('/api/tests'),
    api('/api/refresh/status'),
    api('/api/subscriptions'),
  ]);

  if (overview.status === 'fulfilled') renderOverview(overview.value, providers.value);
  if (providers.status === 'fulfilled') renderProviders(providers.value);
  if (models.status === 'fulfilled') renderModels(models.value);
  if (timeseries.status === 'fulfilled') renderTimeseries(timeseries.value);
  if (windows.status === 'fulfilled') renderWindows(windows.value);
  if (tests.status === 'fulfilled') renderTests(tests.value);
  if (status.status === 'fulfilled') renderStatus(status.value);
  if (subscriptions.status === 'fulfilled') renderSubscriptions(subscriptions.value);
}

// ── Overview ─────────────────────────────────────────────────────────────────

function renderOverview(overview, providers) {
  const grid = $('#kpi-grid');
  grid.innerHTML = '';

  const cards = [
    {
      label: 'Total Spend (MTD)',
      value: fmtMoney(overview.total_cost_usd, 'USD'),
      sub: 'Month-to-date',
      source: dominantSource(overview.data_sources, 'cost'),
    },
    {
      label: 'Total Tokens (MTD)',
      value: overview.total_tokens !== null ? fmtTokens(overview.total_tokens) : '—',
      sub: 'Input + Output',
      source: dominantSource(overview.data_sources, 'tokens'),
    },
    {
      label: 'Total Requests (MTD)',
      value: fmt(overview.total_requests, 'requests'),
      sub: 'API calls',
      source: dominantSource(overview.data_sources, 'requests'),
    },
    {
      label: 'Providers Active',
      value: `${overview.configured_providers} / 5`,
      sub: 'API providers configured',
      source: null,
    },
  ];

  cards.forEach(c => {
    const card = document.createElement('div');
    card.className = 'kpi-card';
    card.innerHTML = `
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value">${c.value}</div>
      <div class="kpi-sub">
        ${c.sub}
        ${c.source ? sourceBadge(c.source) : ''}
      </div>
    `;
    grid.appendChild(card);
  });

  // Update data freshness badge
  if (overview.last_refresh) {
    $('#data-freshness').textContent = 'Updated ' + relTime(overview.last_refresh);
  }

  // Charts
  if (providers) renderSpendByProvider(providers);
  renderTokensByProvider(providers || []);
}

function dominantSource(sources, key) {
  if (!sources) return 'unavailable';
  const vals = Object.entries(sources)
    .filter(([k]) => k === key || k.endsWith(`.${key}`))
    .map(([, v]) => v);
  if (vals.length === 0) return 'unavailable';
  if (vals.includes('official')) return 'official';
  if (vals.includes('inferred')) return 'inferred';
  if (vals.includes('experimental')) return 'experimental';
  return 'unavailable';
}

function fmtTokens(n) {
  if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toLocaleString();
}

function renderSpendByProvider(providers) {
  const data = providers
    .map(p => {
      const costMetric = (p.metrics || []).find(m => m.kind === 'cost_usd' && !m.model);
      return {
        id: p.status.id,
        name: p.status.display_name,
        cost: costMetric && costMetric.unit === 'USD' ? costMetric.value : 0,
      };
    })
    .filter(p => p.cost > 0);

  if (chartSpendProvider) {
    chartSpendProvider.destroy();
    chartSpendProvider = null;
  }

  if (data.length === 0) {
    const body = $('#chart-spend-provider-body');
    if (body) body.innerHTML = '<p class="provider-empty">No USD-denominated spend data available. Configure API keys to see cost data.</p>';
    return;
  }

  const canvas = resetChartBody('#chart-spend-provider-body', 'chart-spend-provider');
  if (!canvas) return;

  chartSpendProvider = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        label: 'Cost (USD)',
        data: data.map(d => d.cost),
        backgroundColor: data.map(d => providerColor(d.id) + 'cc'),
        borderColor: data.map(d => providerColor(d.id)),
        borderWidth: 1,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { ticks: { callback: v => '$' + v.toFixed(2) }, grid: { color: 'rgba(255,255,255,0.04)' } },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderTokensByProvider(providers) {
  const data = providers
    .map(p => {
      const inMetric  = (p.metrics || []).find(m => m.kind === 'tokens_input' && !m.model);
      const outMetric = (p.metrics || []).find(m => m.kind === 'tokens_output' && !m.model);
      const tokens = (inMetric ? inMetric.value : 0) + (outMetric ? outMetric.value : 0);
      return { id: p.status.id, name: p.status.display_name, tokens };
    })
    .filter(p => p.tokens > 0);

  if (chartTokensProvider) {
    chartTokensProvider.destroy();
    chartTokensProvider = null;
  }

  if (data.length === 0) {
    const body = $('#chart-tokens-provider-body');
    if (body) body.innerHTML = '<p class="provider-empty">No token data available.</p>';
    return;
  }

  const canvas = resetChartBody('#chart-tokens-provider-body', 'chart-tokens-provider');
  if (!canvas) return;

  chartTokensProvider = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        data: data.map(d => d.tokens),
        backgroundColor: data.map(d => providerColor(d.id) + 'bb'),
        borderColor: data.map(d => providerColor(d.id)),
        borderWidth: 2,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '65%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { padding: 12, boxWidth: 10, font: { size: 11 } },
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.label}: ${fmtTokens(ctx.raw)} tokens` },
        },
      },
    },
  });
}

// ── Providers ─────────────────────────────────────────────────────────────────

function renderProviders(providers) {
  const grid = $('#provider-grid');
  grid.innerHTML = '';

  providers.forEach(p => {
    const { status, metrics } = p;
    const isConfigured = status.configured;
    const kindLabel = status.kind === 'api' ? 'API' : 'Tool';
    const dotClass = isConfigured ? 'ok' : 'missing';

    const card = document.createElement('div');
    card.className = 'provider-card';

    // Gather key metrics
    const cost   = metrics.find(m => m.kind === 'cost_usd' && !m.model);
    const tokIn  = metrics.find(m => m.kind === 'tokens_input' && !m.model);
    const tokOut = metrics.find(m => m.kind === 'tokens_output' && !m.model);
    const reqs   = metrics.find(m => m.kind === 'requests' && !m.model);
    const credits = metrics.find(m => m.kind === 'credits_remaining');

    const rows = [];
    if (cost && cost.source !== 'unavailable') {
      rows.push({ label: 'Cost', value: fmtMoney(cost.value, cost.unit), source: cost.source });
    }
    if (tokIn && tokIn.source !== 'unavailable') {
      rows.push({ label: 'Input tokens', value: fmtTokens(tokIn.value), source: tokIn.source });
    }
    if (tokOut && tokOut.source !== 'unavailable') {
      rows.push({ label: 'Output tokens', value: fmtTokens(tokOut.value), source: tokOut.source });
    }
    if (reqs && reqs.source !== 'unavailable') {
      rows.push({ label: 'Requests', value: fmt(reqs.value, 'requests'), source: reqs.source });
    }
    if (credits) {
      rows.push({ label: 'Credits remaining', value: fmtMoney(credits.value, credits.unit), source: credits.source });
    }

    let metricsHtml = '';
    if (rows.length === 0) {
      const note = metrics[0]?.notes || (isConfigured ? 'No data yet.' : 'API key not configured.');
      metricsHtml = `<p class="provider-empty">${note}</p>`;
    } else {
      metricsHtml = rows.map(r => `
        <div class="provider-metric-row">
          <span class="provider-metric-label">${r.label}</span>
          <span class="provider-metric-value">${r.value} ${sourceBadge(r.source)}</span>
        </div>
      `).join('');
    }

    card.innerHTML = `
      <div class="provider-header">
        <div class="provider-name">
          <div class="provider-status-dot ${dotClass}"></div>
          ${status.display_name}
        </div>
        <span class="provider-kind-badge ${status.kind}">${kindLabel}</span>
      </div>
      <div class="provider-metrics">${metricsHtml}</div>
    `;

    grid.appendChild(card);
  });
}

// ── Models ────────────────────────────────────────────────────────────────────

function renderModels(models) {
  const tbody = $('#models-tbody');
  const count = $('#model-count');
  if (count) count.textContent = `${models.length} model${models.length !== 1 ? 's' : ''}`;

  if (models.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-row">No model-level data yet. Run a refresh after configuring API keys.</td></tr>';
    return;
  }

  tbody.innerHTML = models.map(m => `
    <tr>
      <td><code style="font-family:var(--font-mono);font-size:11px;color:var(--text-secondary)">${m.model}</code></td>
      <td><span style="text-transform:capitalize;color:var(--text-secondary)">${m.provider}</span></td>
      <td class="num">${m.cost_usd !== null ? fmt(m.cost_usd, 'usd') : '—'}</td>
      <td class="num">${m.tokens_input !== null ? fmtTokens(m.tokens_input) : '—'}</td>
      <td class="num">${m.tokens_output !== null ? fmtTokens(m.tokens_output) : '—'}</td>
      <td class="num">${m.requests !== null ? fmt(m.requests, 'requests') : '—'}</td>
    </tr>
  `).join('');
}

// ── Timeseries ────────────────────────────────────────────────────────────────

function renderTimeseries(points) {
  const filter = $('#ts-provider-filter');
  if (!filter) return;

  const currentValue = filter.value || '';
  const providers = [...new Set(points.map(p => p.provider))].sort();
  filter.innerHTML = '<option value="">All providers</option>';
  providers.forEach(pid => {
    const opt = document.createElement('option');
    opt.value = pid;
    opt.textContent = pid.replace('_', ' ');
    filter.appendChild(opt);
  });
  filter.value = providers.includes(currentValue) ? currentValue : '';

  drawTimeseries(points, filter.value);
}

function drawTimeseries(points, providerFilter) {
  const filtered = providerFilter ? points.filter(p => p.provider === providerFilter) : points;

  // Group by provider, show input+output tokens over time
  const byProvider = {};
  filtered
    .filter(p => p.kind === 'tokens_input' || p.kind === 'tokens_output')
    .forEach(p => {
      const pid = p.provider;
      if (!byProvider[pid]) byProvider[pid] = [];
      byProvider[pid].push({ x: parseIso(p.timestamp), y: p.value });
    });

  if (chartTimeseries) {
    chartTimeseries.destroy();
    chartTimeseries = null;
  }

  if (filtered.length === 0 || Object.keys(byProvider).length === 0) {
    const body = $('#chart-timeseries-body');
    if (body) body.innerHTML = '<p class="provider-empty" style="padding:40px 0">No timeseries data yet. Data accumulates over multiple refreshes.</p>';
    return;
  }

  const canvas = resetChartBody('#chart-timeseries-body', 'chart-timeseries');
  if (!canvas) return;

  const datasets = Object.entries(byProvider).map(([pid, pts]) => ({
    label: pid.replace('_', ' '),
    data: pts.sort((a, b) => a.x - b.x),
    borderColor: providerColor(pid),
    backgroundColor: providerColor(pid) + '22',
    borderWidth: 2,
    pointRadius: 3,
    tension: 0.3,
    fill: false,
  }));

  chartTimeseries = new Chart(canvas, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      parsing: false,
      scales: {
        x: {
          type: 'time',
          time: { unit: 'hour', tooltipFormat: 'MMM d, HH:mm' },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
        y: {
          ticks: { callback: v => fmtTokens(v) },
          grid: { color: 'rgba(255,255,255,0.04)' },
        },
      },
      plugins: {
        legend: { position: 'top', labels: { boxWidth: 10, padding: 14 } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ${fmtTokens(ctx.parsed.y)} tokens`,
          },
        },
      },
      interaction: { mode: 'nearest', intersect: false },
    },
  });
}

// ── Windows ───────────────────────────────────────────────────────────────────

function renderWindows(windows) {
  const grid = $('#windows-grid');
  grid.innerHTML = '';

  if (windows.length === 0) {
    grid.innerHTML = '<p class="provider-empty" style="grid-column:1/-1;padding:40px 0">No usage window data available. Configure API keys to see billing windows.</p>';
    return;
  }

  windows.forEach(w => {
    const pct = w.percent_used;
    const barClass = pct >= 90 ? 'danger' : pct >= 70 ? 'warning' : '';
    const barWidth = pct !== null ? Math.min(pct, 100) : 0;

    const card = document.createElement('div');
    card.className = 'window-card';
    card.innerHTML = `
      <div>
        <div class="window-label">${w.window_label}</div>
        <div class="window-provider">${w.provider.replace('_', ' ')} · ${sourceBadge(w.source)}</div>
      </div>
      ${w.used !== null ? `
        <div class="window-bar-wrap">
          <div class="window-bar ${barClass}" style="width:${barWidth}%"></div>
        </div>
        <div class="window-nums">
          <span>${fmtMoney(w.used, w.unit)} used</span>
          ${w.limit !== null ? `<span>${fmtMoney(w.limit, w.unit)} limit</span>` : ''}
        </div>
      ` : `<p class="window-empty">No usage data available</p>`}
      ${w.reset_at ? `<div class="window-reset">Resets ${absTime(w.reset_at)}</div>` : ''}
    `;
    grid.appendChild(card);
  });
}

// ── Subscriptions ─────────────────────────────────────────────────────────────

function renderSubscriptions(data) {
  // KPI row
  const kpiRow = $('#sub-kpi-row');
  kpiRow.innerHTML = '';

  const kpis = [
    {
      label: 'Total Subscription Cost',
      value: data.total_subscription_cost !== null ? fmtMoney(data.total_subscription_cost) : '—',
      sub: 'Monthly combined',
    },
    {
      label: 'API Equivalent Cost',
      value: data.total_api_equivalent !== null ? fmtMoney(data.total_api_equivalent) : '—',
      sub: 'If using direct API',
    },
    {
      label: 'Estimated Savings',
      value: data.total_estimated_savings !== null ? fmtMoney(data.total_estimated_savings) : '—',
      sub: 'This billing period',
    },
  ];

  kpis.forEach(k => {
    const card = document.createElement('div');
    card.className = 'kpi-card';
    const isSavings = k.label === 'Estimated Savings';
    const savingsClass = isSavings && data.total_estimated_savings > 0 ? ' style="color:var(--green)"' : '';
    card.innerHTML = `
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value"${savingsClass}>${k.value}</div>
      <div class="kpi-sub">${k.sub}</div>
    `;
    kpiRow.appendChild(card);
  });

  // Tool cards
  const grid = $('#sub-tools-grid');
  grid.innerHTML = '';

  if (!data.tools || data.tools.length === 0) {
    grid.innerHTML = '<p class="provider-empty" style="grid-column:1/-1;padding:40px 0">No subscription tool data available.</p>';
  } else {
    data.tools.forEach(t => {
      const pct = t.percent_used;
      const barClass = pct !== null ? (pct >= 90 ? 'danger' : pct >= 70 ? 'warning' : '') : '';
      const barWidth = pct !== null ? Math.min(pct, 100) : 0;

      const card = document.createElement('div');
      card.className = 'sub-tool-card';

      // Header
      let headerHtml = `<div class="sub-tool-header">
        <span class="sub-tool-name">${t.display_name}</span>
        ${t.plan_name ? `<span class="sub-tool-plan">${t.plan_name}</span>` : ''}
      </div>`;

      // Usage bar
      let usageHtml = '';
      if (t.used !== null) {
        usageHtml = `
          <div class="sub-tool-usage">
            <div class="sub-usage-bar-wrap">
              <div class="sub-usage-bar ${barClass}" style="width:${barWidth}%"></div>
            </div>
            <div class="sub-usage-label">
              <span>${fmtMoney(t.used, t.unit)} used</span>
              ${t.limit !== null ? `<span>${fmtMoney(t.limit, t.unit)} limit</span>` : '<span>No limit data</span>'}
            </div>
          </div>`;
      } else {
        usageHtml = '<p class="provider-empty">No usage data available</p>';
      }

      // Savings block
      let savingsHtml = '<div class="sub-savings-block">';
      if (t.subscription_price !== null) {
        savingsHtml += `<div class="sub-savings-row">
          <span>Subscription</span>
          <span class="value">${fmtMoney(t.subscription_price)}/mo</span>
        </div>`;
      }
      if (t.api_equivalent_cost !== null) {
        savingsHtml += `<div class="sub-savings-row">
          <span>API equivalent</span>
          <span class="value">${fmtMoney(t.api_equivalent_cost)}</span>
        </div>`;
      }
      if (t.estimated_savings !== null) {
        const savingsPositive = t.estimated_savings > 0;
        savingsHtml += `<div class="sub-savings-row ${savingsPositive ? 'positive' : ''}">
          <span>Savings</span>
          <span class="value">${savingsPositive ? '+' : ''}${fmtMoney(t.estimated_savings)}</span>
        </div>`;
      }
      savingsHtml += '</div>';

      // Notes
      let notesHtml = t.notes
        ? `<div class="sub-tool-notes">${t.notes}</div>`
        : '';

      // Meta row
      let metaHtml = `<div class="sub-tool-meta">
        <span>${t.window_label}</span>
        ${sourceBadge(t.source)}
      </div>`;

      card.innerHTML = headerHtml + usageHtml + savingsHtml + notesHtml + metaHtml;
      grid.appendChild(card);
    });
  }

  // Caveats
  const caveatsEl = $('#sub-caveats');
  caveatsEl.innerHTML = '';
  if (data.caveats && data.caveats.length > 0) {
    data.caveats.forEach(c => {
      const item = document.createElement('div');
      item.className = 'sub-caveat-item';
      item.textContent = c;
      caveatsEl.appendChild(item);
    });
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

function renderTests(tests) {
  const tbody = $('#tests-tbody');

  if (tests.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-row">No test results yet. Click "Run Tests" to test endpoints.</td></tr>';
    return;
  }

  tbody.innerHTML = tests.map(t => {
    const ts = t.test_status || (t.ok ? 'pass' : 'fail');
    let statusClass, statusLabel;
    if (ts === 'skipped') {
      statusClass = 'status-skip';
      statusLabel = 'SKIP';
    } else if (ts === 'pass') {
      statusClass = 'status-ok';
      statusLabel = 'PASS';
    } else {
      statusClass = 'status-err';
      statusLabel = 'FAIL';
    }
    return `
    <tr>
      <td>${t.provider}</td>
      <td><code style="font-size:11px;font-family:var(--font-mono)">${t.endpoint}</code></td>
      <td><code style="font-size:10px;color:var(--text-dim)">${t.method}</code></td>
      <td class="num ${statusClass}">${t.status_code || '—'} <small>${statusLabel}</small></td>
      <td class="num">${t.latency_ms !== null ? fmt(t.latency_ms, 'ms') : '—'}</td>
      <td style="max-width:220px;font-size:11px;color:var(--text-secondary)">${t.notes || '—'}</td>
      <td>${t.is_experimental ? '<span class="source-tag experimental">Experimental</span>' : '<span class="source-tag official">Official</span>'}</td>
      <td style="font-size:11px;color:var(--text-dim)">${relTime(t.tested_at)}</td>
    </tr>`;
  }).join('');
}

// ── Refresh status ────────────────────────────────────────────────────────────

function renderStatus(status) {
  const dot = $('#refresh-dot');
  const label = $('#last-refresh-label');
  const nextLabel = $('#next-refresh-label');

  if (status.last_run) {
    const finishedAt = parseIso(status.last_run.finished_at);
    const isRecent = finishedAt && (Date.now() - finishedAt.getTime()) < 5000;
    dot.className = 'refresh-dot ' + (isRecent ? 'active' : '');
    label.textContent = 'Updated ' + relTime(status.last_run.finished_at || status.last_run.started_at);
  }

  if (status.next_run_at) {
    const next = parseIso(status.next_run_at);
    const mins = next ? Math.max(0, Math.round((next.getTime() - Date.now()) / 60000)) : 0;
    nextLabel.textContent = `Auto-refresh in ${mins}m`;
  }
}

// ── Manual refresh ────────────────────────────────────────────────────────────

async function triggerRefresh(triggeredBy = 'manual') {
  if (isRefreshing) return;
  isRefreshing = true;

  const btn = $('#btn-refresh');
  const icon = $('#refresh-icon');
  const dot = $('#refresh-dot');

  btn.disabled = true;
  icon.style.animation = 'spin 0.7s linear infinite';
  dot.className = 'refresh-dot loading';

  showToast('Refreshing all providers…', 'info');

  try {
    const run = await post('/api/refresh');
    const ok = run.providers_succeeded?.length || 0;
    const total = run.providers_attempted?.length || 0;
    showToast(`Refresh complete — ${ok}/${total} providers`, ok === total ? 'success' : 'info');
    await loadAll();
  } catch (err) {
    showToast('Refresh failed: ' + err.message, 'error');
  } finally {
    isRefreshing = false;
    btn.disabled = false;
    icon.style.animation = '';
    dot.className = 'refresh-dot active';
    setTimeout(() => { dot.className = 'refresh-dot'; }, 3000);
  }
}

// ── Run endpoint tests ────────────────────────────────────────────────────────

async function runEndpointTests() {
  showToast('Running endpoint tests…', 'info');
  try {
    await post('/api/tests/run');
    const tests = await api('/api/tests');
    renderTests(tests);
    showToast('Tests complete', 'success');
  } catch (err) {
    showToast('Tests failed: ' + err.message, 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  activateSection('overview');
  loadAll();

  $('#btn-refresh').addEventListener('click', () => triggerRefresh('manual'));

  const filter = $('#ts-provider-filter');
  if (filter) {
    filter.addEventListener('change', async () => {
      try {
        const points = await api('/api/timeseries');
        drawTimeseries(points, filter.value);
      } catch (_) {}
    });
  }

  const testBtn = $('#btn-run-tests');
  if (testBtn) testBtn.addEventListener('click', runEndpointTests);

  // Refresh status label every 30 seconds
  setInterval(async () => {
    try {
      const status = await api('/api/refresh/status');
      renderStatus(status);
    } catch (_) {}
  }, 30_000);
});
