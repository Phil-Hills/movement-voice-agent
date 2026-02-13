/* ======================================
   Rate Tracker — Core Logic
   Rate Tracker | Intelligence System
   ====================================== */

// Originator's Pipeline (extracted from CRM audit)
const PIPELINE = [
    { name: "Megan Carter", stage: "Funded", loanNum: "4342859", property: "9213 Ash Ave SE, Snoqualmie WA", loanAmount: 1114750, rate: 6.500, program: "Jumbo", closingDate: "6/20/2025", creditScore: 808, ltv: 65.0, dti: 41.68, piti: 8376.57, buyerAgent: "Barb Pexa" },
    { name: "Chelsey Milton", stage: "Application", loanNum: "3010572614", property: "TBD", loanAmount: 546025, rate: 6.750, program: "Conventional", closingDate: "3/9/2026", creditScore: 796, ltv: 73.2, dti: 26.32, piti: 3541.51, buyerAgent: "" },
    { name: "Anuj Mittal", stage: "Funded", loanNum: "3010526", property: "3493 NE Harrison St", loanAmount: 850000, rate: 6.875, program: "Jumbo", closingDate: "11/12/2025", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Manu Vij" },
    { name: "JIYEON PARK", stage: "Funded", loanNum: "3010542", property: "13910 123rd Ave NE", loanAmount: 720000, rate: 6.625, program: "Jumbo", closingDate: "12/1/2025", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Emma Park" },
    { name: "Cooper White", stage: "Application", loanNum: "3010554", property: "TBD", loanAmount: 480000, rate: 6.500, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Derek Sarr" },
    { name: "john thang", stage: "Application", loanNum: "4214710", property: "TBD", loanAmount: 350000, rate: 6.875, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "lisa nguyen" },
    { name: "Jared Larsen", stage: "Funded", loanNum: "4073624", property: "18501 SE Newport Wy", loanAmount: 600000, rate: 7.125, program: "Conventional", closingDate: "9/26/2023", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Karen Cor" },
    { name: "Matthew Simon", stage: "Application", loanNum: "", property: "1156 NW 58th St", loanAmount: 425000, rate: 6.750, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "" },
    { name: "Chris Candelario", stage: "Application", loanNum: "4379189", property: "TBD", loanAmount: 390000, rate: 6.625, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Barb Pexa" },
    { name: "Faezeh Amjadi", stage: "Application", loanNum: "4421329", property: "TBD", loanAmount: 375000, rate: 6.500, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "" },
    { name: "Stanley Gene", stage: "Funded", loanNum: "30105361", property: "1352 Brewster Dr", loanAmount: 550000, rate: 6.750, program: "Conventional", closingDate: "2/11/2026", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Kelly O'Go" },
    { name: "Samantha Sim", stage: "Funded", loanNum: "3010535", property: "206 1st Ave E", loanAmount: 415200, rate: 6.875, program: "Conventional", closingDate: "12/4/2025", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Makenna K" },
    { name: "Michael Lentz", stage: "Funded", loanNum: "3010536", property: "10605 SE 30th St", loanAmount: 520000, rate: 6.625, program: "Conventional", closingDate: "12/12/2025", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Barb Pexa" },
    { name: "catherine Jin", stage: "Funded", loanNum: "4124925", property: "3633 Beach Dr", loanAmount: 750000, rate: 7.250, program: "Jumbo", closingDate: "1/22/2024", creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "Yao Lu" },
    { name: "Catherine Jin", stage: "Lost", loanNum: "", property: "3633 Beach Dr", loanAmount: 0, rate: null, program: "Conventional", closingDate: null, creditScore: null, ltv: null, dti: null, piti: null, buyerAgent: "" }
];

// ---- INITIALIZATION ----
document.addEventListener('DOMContentLoaded', () => {
    setCurrentDate();
    attachRateListeners();
    attachFilterListeners();
    recalculateAll();
});

function setCurrentDate() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('currentDate').textContent = now.toLocaleDateString('en-US', options);
}

// ---- RATE INPUT LISTENERS ----
function attachRateListeners() {
    const inputs = document.querySelectorAll('.rate-input');
    inputs.forEach(input => {
        input.addEventListener('input', () => recalculateAll());
        input.addEventListener('change', () => recalculateAll());
    });
}

// ---- FILTER LISTENERS ----
let currentFilter = 'all';

function attachFilterListeners() {
    const btns = document.querySelectorAll('.filter-btn');
    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            recalculateAll();
        });
    });
}

// ---- CORE CALCULATIONS ----
function getMarketRate(program) {
    if (program === 'Jumbo') return parseFloat(document.getElementById('rate-jumbo30').value) || 0;
    if (program === 'FHA') return parseFloat(document.getElementById('rate-fha30').value) || 0;
    if (program === 'VA') return parseFloat(document.getElementById('rate-va30').value) || 0;
    return parseFloat(document.getElementById('rate-conv30').value) || 0;
}

function calculateMonthlySavings(loanAmount, currentRate, marketRate) {
    if (!loanAmount || !currentRate || !marketRate || currentRate <= marketRate) return 0;
    const currentMonthly = (loanAmount * (currentRate / 100 / 12)) / (1 - Math.pow(1 + currentRate / 100 / 12, -360));
    const newMonthly = (loanAmount * (marketRate / 100 / 12)) / (1 - Math.pow(1 + marketRate / 100 / 12, -360));
    return Math.max(0, currentMonthly - newMonthly);
}

function getRefiScore(rateDelta, loanAmount) {
    if (rateDelta === null || rateDelta <= 0) return { score: 0, label: '—', cls: 'score-na' };
    // Score = weighted by rate delta + loan size
    let score = 0;
    if (rateDelta >= 0.75) score += 60;
    else if (rateDelta >= 0.50) score += 40;
    else if (rateDelta >= 0.25) score += 20;
    else score += 5;

    if (loanAmount >= 800000) score += 30;
    else if (loanAmount >= 500000) score += 20;
    else if (loanAmount >= 300000) score += 10;

    score = Math.min(score, 99);

    if (score >= 70) return { score, label: String(score), cls: 'score-high' };
    if (score >= 30) return { score, label: String(score), cls: 'score-med' };
    return { score, label: String(score), cls: 'score-low' };
}

// ---- RENDER ALL ----
function recalculateAll() {
    let totalPipeline = 0;
    let refiReadyCount = 0;
    let totalMonthlySavings = 0;
    let rateSum = 0;
    let rateCount = 0;
    let fundedCount = 0;

    const enriched = PIPELINE.map(loan => {
        const marketRate = getMarketRate(loan.program);
        const rateDelta = (loan.rate !== null && marketRate > 0) ? loan.rate - marketRate : null;
        const monthlySavings = calculateMonthlySavings(loan.loanAmount, loan.rate, marketRate);
        const refiScore = getRefiScore(rateDelta, loan.loanAmount);

        // Accumulators
        if (loan.loanAmount > 0) totalPipeline += loan.loanAmount;
        if (loan.stage === 'Funded') fundedCount++;
        if (loan.rate) { rateSum += loan.rate; rateCount++; }
        if (refiScore.score >= 70 && loan.stage === 'Funded') { refiReadyCount++; totalMonthlySavings += monthlySavings; }

        return { ...loan, marketRate, rateDelta, monthlySavings, refiScore };
    });

    // Update summary stats
    document.getElementById('totalPipeline').textContent = '$' + (totalPipeline / 1000000).toFixed(2) + 'M';
    document.getElementById('refiReady').textContent = refiReadyCount;
    document.getElementById('totalSavings').textContent = '$' + Math.round(totalMonthlySavings).toLocaleString();
    document.getElementById('avgRate').textContent = rateCount > 0 ? (rateSum / rateCount).toFixed(3) + '%' : '—';
    document.getElementById('fundedCount').textContent = fundedCount;

    // Filter
    let filtered = enriched;
    if (currentFilter === 'refi') filtered = enriched.filter(l => l.refiScore.score >= 70 && l.stage === 'Funded');
    else if (currentFilter === 'watch') filtered = enriched.filter(l => l.refiScore.score >= 30 && l.refiScore.score < 70);
    else if (currentFilter === 'funded') filtered = enriched.filter(l => l.stage === 'Funded');
    else if (currentFilter === 'active') filtered = enriched.filter(l => l.stage === 'Application');

    // Sort by refi score descending
    filtered.sort((a, b) => b.refiScore.score - a.refiScore.score);

    renderTable(filtered);
    renderActions(enriched);
}

// ---- RENDER TABLE ----
function renderTable(loans) {
    const tbody = document.getElementById('pipelineBody');
    tbody.innerHTML = '';

    loans.forEach(loan => {
        const tr = document.createElement('tr');

        // Row highlighting
        if (loan.refiScore.score >= 70 && loan.stage === 'Funded') tr.classList.add('refi-ready');
        else if (loan.refiScore.score >= 30 && loan.refiScore.score < 70) tr.classList.add('watch-item');

        // Stage class
        const stageClass = loan.stage === 'Funded' ? 'stage-funded' : loan.stage === 'Lost' ? 'stage-lost' : 'stage-application';

        // Delta display
        let deltaHtml = '<span class="delta-neutral">—</span>';
        if (loan.rateDelta !== null) {
            if (loan.rateDelta > 0) deltaHtml = `<span class="delta-positive">-${loan.rateDelta.toFixed(3)}%</span>`;
            else if (loan.rateDelta < 0) deltaHtml = `<span class="delta-negative">+${Math.abs(loan.rateDelta).toFixed(3)}%</span>`;
            else deltaHtml = `<span class="delta-neutral">0.000%</span>`;
        }

        // Savings display
        let savingsHtml = '<span class="muted">—</span>';
        if (loan.monthlySavings > 0) {
            savingsHtml = `<span class="savings-value savings-positive">$${Math.round(loan.monthlySavings).toLocaleString()}</span>`;
        }

        tr.innerHTML = `
      <td><span class="score-badge ${loan.refiScore.cls}">${loan.refiScore.label}</span></td>
      <td><span class="borrower-name">${loan.name}</span></td>
      <td><span class="stage-pill ${stageClass}">${loan.stage}</span></td>
      <td class="mono muted">${loan.loanNum || '—'}</td>
      <td>${loan.property}</td>
      <td class="mono">${loan.loanAmount > 0 ? '$' + loan.loanAmount.toLocaleString() : '—'}</td>
      <td class="mono">${loan.rate ? loan.rate.toFixed(3) + '%' : '—'}</td>
      <td class="mono muted">${loan.marketRate ? loan.marketRate.toFixed(3) + '%' : '—'}</td>
      <td>${deltaHtml}</td>
      <td>${savingsHtml}</td>
      <td class="muted">${loan.buyerAgent || '—'}</td>
    `;

        tbody.appendChild(tr);
    });
}

// ---- RENDER ACTION ITEMS ----
function renderActions(enriched) {
    const container = document.getElementById('actionItems');
    container.innerHTML = '';

    const actions = [];

    // Find refi-ready funded loans
    const refiReady = enriched.filter(l => l.refiScore.score >= 70 && l.stage === 'Funded');
    refiReady.forEach(loan => {
        actions.push({
            icon: '🔥',
            title: `Call ${loan.name} — Refi Opportunity`,
            desc: `Current rate ${loan.rate}% → Market ${loan.marketRate.toFixed(3)}%. Potential savings: $${Math.round(loan.monthlySavings).toLocaleString()}/mo on $${loan.loanAmount.toLocaleString()} loan.`,
            tag: 'Call', tagCls: 'tag-call'
        });
    });

    // Watch items
    const watchItems = enriched.filter(l => l.refiScore.score >= 30 && l.refiScore.score < 70 && l.stage === 'Funded');
    watchItems.forEach(loan => {
        actions.push({
            icon: '👀',
            title: `Monitor ${loan.name} — Rate Watch`,
            desc: `Only ${loan.rateDelta?.toFixed(3)}% above market. Queue for automated review when rates drop another 0.125%.`,
            tag: 'Review', tagCls: 'tag-review'
        });
    });

    // Stale applications
    const staleApps = enriched.filter(l => l.stage === 'Application' && !l.closingDate);
    if (staleApps.length > 0) {
        actions.push({
            icon: '📧',
            title: `Follow up on ${staleApps.length} open applications`,
            desc: `${staleApps.map(l => l.name).join(', ')} — no closing date set. Send status check email.`,
            tag: 'Email', tagCls: 'tag-email'
        });
    }

    // Lost re-engagement
    const lostLoans = enriched.filter(l => l.stage === 'Lost');
    lostLoans.forEach(loan => {
        actions.push({
            icon: '🔄',
            title: `Re-engage ${loan.name} — Lost Deal`,
            desc: `Previous opportunity at ${loan.property}. Current rates may offer a better deal than when they left.`,
            tag: 'Call', tagCls: 'tag-call'
        });
    });

    if (actions.length === 0) {
        actions.push({
            icon: '✅',
            title: 'All Clear',
            desc: 'No urgent action items today. Pipeline is healthy.',
            tag: '', tagCls: ''
        });
    }

    actions.forEach(action => {
        const card = document.createElement('div');
        card.className = 'action-card';
        card.innerHTML = `
      <div class="action-icon">${action.icon}</div>
      <div class="action-content">
        <h4>${action.title}</h4>
        <p>${action.desc}</p>
        ${action.tag ? `<span class="action-tag ${action.tagCls}">${action.tag}</span>` : ''}
      </div>
    `;
        container.appendChild(card);
    });
}
