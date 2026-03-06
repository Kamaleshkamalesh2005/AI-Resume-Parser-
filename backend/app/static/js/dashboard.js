/**
 * Premium Results Dashboard UI
 * - Ranked table with fade-in row animation
 * - Score bars with progressive fill
 * - Skill match vs missing section
 * - Pie chart using Chart.js
 * - Responsive and modular rendering
 */

let skillChart = null;
let rankingData = [];

function byScoreDesc(a, b) {
    return (b.finalScore || 0) - (a.finalScore || 0);
}

function toPercentString(value) {
    if (value === null || value === undefined) return '0%';
    if (typeof value !== 'number') return '0%';
    return `${Math.round(value)}%`;
}

function toPercentNumber(value) {
    if (value === null || value === undefined) return 0;
    if (typeof value !== 'number') return 0;
    return Math.round(value);
}

function statusBadge(score) {
    if (score >= 85) return '<span class="badge badge-success">Top Fit</span>';
    if (score >= 75) return '<span class="badge badge-warning">Strong Fit</span>';
    return '<span class="badge badge-error">Needs Review</span>';
}

function renderRankingTable(data) {
    const tbody = document.getElementById('rankingTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-gray-400 py-6">No real candidate data yet. Upload resumes to see rankings.</td></tr>';
        return;
    }

    data.forEach((candidate, index) => {
        const row = document.createElement('tr');
        row.className = 'ranking-row fade-sequence';
        row.style.animationDelay = `${index * 90}ms`;
        row.dataset.candidateId = candidate.id;

        row.innerHTML = `
            <td>${index + 1}</td>
            <td>
                <div class="font-semibold text-white">${candidate.name}</div>
                <div class="text-xs text-gray-400">${candidate.id}</div>
            </td>
            <td>${toPercentString(candidate.similarity)}</td>
            <td>${toPercentString(candidate.probability)}</td>
            <td><span class="text-neon-blue font-semibold">${toPercentString(candidate.finalScore)}</span></td>
            <td>${statusBadge(candidate.finalScore)}</td>
        `;

        row.addEventListener('click', () => {
            setActiveRow(candidate.id);
            renderSkillSection(candidate);
            updatePieChart(candidate);
        });

        tbody.appendChild(row);
    });
}

function setActiveRow(candidateId) {
    document.querySelectorAll('.ranking-row').forEach((row) => {
        row.classList.toggle('active', row.dataset.candidateId === candidateId);
    });
}

function renderScoreBars(data) {
    const container = document.getElementById('scoreBars');
    if (!container) return;

    container.innerHTML = '';

    if (!data.length) {
        container.innerHTML = '<p class="text-sm text-gray-400">No scores available.</p>';
        return;
    }

    data.forEach((candidate, index) => {
        const block = document.createElement('div');
        block.className = 'score-bar-row';

        block.innerHTML = `
            <div class="flex items-center justify-between mb-1 text-sm">
                <span class="text-gray-200">${candidate.name}</span>
                <span class="text-neon-purple font-semibold">${toPercentString(candidate.finalScore)}</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill progress-fill-purple" data-score-fill style="width:0%"></div>
            </div>
        `;

        container.appendChild(block);

        const fill = block.querySelector('[data-score-fill]');
        setTimeout(() => {
            fill.style.width = toPercentString(candidate.finalScore);
        }, 120 + (index * 100));
    });
}

function renderSkillTags(targetId, skills, type = 'match') {
    const target = document.getElementById(targetId);
    if (!target) return;

    if (!skills || skills.length === 0) {
        target.innerHTML = '<p class="text-sm text-gray-400">No data available.</p>';
        return;
    }

    const badgeClass = type === 'match' ? 'badge-success' : 'badge-error';
    target.innerHTML = skills.map((skill) => `<span class="badge ${badgeClass}">${skill}</span>`).join(' ');
}

function renderSkillSection(candidate) {
    const selected = document.getElementById('selectedCandidate');
    if (selected) {
        selected.innerHTML = `<strong class="text-white">${candidate.name}</strong> · Final score ${toPercentString(candidate.finalScore)}`;
    }

    renderSkillTags('matchedSkills', candidate.matchedSkills, 'match');
    renderSkillTags('missingSkills', candidate.missingSkills, 'missing');
}

function initPieChart() {
    const canvas = document.getElementById('skillsPieChart');
    if (!canvas || typeof Chart === 'undefined') return;

    skillChart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: ['Matched Skills', 'Missing Skills'],
            datasets: [{
                data: [1, 1],
                backgroundColor: ['rgba(59, 130, 246, 0.85)', 'rgba(168, 85, 247, 0.85)'],
                borderColor: ['rgba(147, 197, 253, 1)', 'rgba(216, 180, 254, 1)'],
                borderWidth: 1.5,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: '#dbeafe'
                    }
                }
            }
        }
    });
}

function updatePieChart(candidate) {
    if (!skillChart) return;

    const matchedCount = candidate.matchedSkills.length;
    const missingCount = candidate.missingSkills.length;

    skillChart.data.datasets[0].data = [matchedCount, missingCount];
    skillChart.update();
}

function renderTopStats(data) {
    const total = data.length;
    const avg = total ? data.reduce((sum, item) => sum + item.finalScore, 0) / total : 0;

    const totalEl = document.getElementById('totalCandidates');
    const avgEl = document.getElementById('avgScore');

    if (totalEl) totalEl.textContent = String(total);
    if (avgEl) avgEl.textContent = toPercentString(avg);
}

function renderHealthSummary(healthData) {
    const target = document.getElementById('healthSummary');
    if (!target) return;

    if (!healthData || !healthData.success) {
        target.innerHTML = '<p class="text-gray-400">Live health data unavailable.</p>';
        return;
    }

    const rows = Object.entries(healthData.components || {}).map(([name, status]) => {
        const ok = Boolean(status.ok);
        return `
            <div class="flex items-center justify-between result-panel">
                <span>${name}</span>
                <span class="${ok ? 'text-blue-300' : 'text-red-300'}">${ok ? 'Online' : 'Issue'}</span>
            </div>
        `;
    }).join('');

    target.innerHTML = rows || '<p class="text-gray-400">No component data.</p>';
}

function renderModelSnapshot(modelData) {
    const target = document.getElementById('modelSnapshot');
    if (!target) return;

    if (!modelData || !modelData.success) {
        target.innerHTML = '<p class="text-gray-400">Model snapshot unavailable.</p>';
        return;
    }

    const model = modelData.model || {};
    const components = model.components || {};
    const isReady = components.all_ready || model.status === 'MLService ready';
    target.innerHTML = `
        <div class="result-panel flex items-center justify-between"><span>Model Type</span><strong>${model.type || '-'}</strong></div>
        <div class="result-panel flex items-center justify-between"><span>SBERT</span><strong class="${components.sbert_ready ? 'text-green-400' : 'text-red-400'}">${components.sbert_ready ? 'Loaded' : 'Not Loaded'}</strong></div>
        <div class="result-panel flex items-center justify-between"><span>TF-IDF</span><strong class="${components.tfidf_ready ? 'text-green-400' : 'text-yellow-400'}">${components.tfidf_ready ? 'Ready' : 'Fit-on-demand'}</strong></div>
        <div class="result-panel flex items-center justify-between"><span>Status</span><strong class="${isReady ? 'text-green-400' : 'text-red-400'}">${isReady ? 'Operational' : 'Not Ready'}</strong></div>
    `;
}

async function fetchJson(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) return null;
        return await response.json();
    } catch (error) {
        return null;
    }
}

async function loadDashboardData() {
    let parsed = [];
    try {
        const persisted = localStorage.getItem('dashboardCandidates');
        parsed = persisted ? JSON.parse(persisted) : [];
    } catch (error) {
        parsed = [];
    }
    rankingData = (Array.isArray(parsed) ? parsed : []).sort(byScoreDesc);

    renderTopStats(rankingData);
    renderRankingTable(rankingData);
    renderScoreBars(rankingData);

    initPieChart();
    const first = rankingData[0];
    if (first) {
        setActiveRow(first.id);
        renderSkillSection(first);
        updatePieChart(first);
    } else {
        renderSkillTags('matchedSkills', [], 'match');
        renderSkillTags('missingSkills', [], 'missing');
        const selected = document.getElementById('selectedCandidate');
        if (selected) selected.innerHTML = '<span class="text-gray-400">No candidate selected.</span>';
    }

    const [healthData, modelData] = await Promise.all([
        fetchJson('/api/dashboard/health'),
        fetchJson('/api/match/model-info')
    ]);

    renderHealthSummary(healthData);
    renderModelSnapshot(modelData);
}

document.addEventListener('DOMContentLoaded', loadDashboardData);
