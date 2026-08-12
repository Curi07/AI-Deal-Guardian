// State
let currentDealId = null;
let currentDealData = null;

// Views
const views = {
    newDeal: document.getElementById('view-new-deal'),
    preflight: document.getElementById('view-preflight'),
    dealMemory: document.getElementById('view-deal-memory'),
    scopeGuard: document.getElementById('view-scope-guard')
};

function showView(viewName) {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    views[viewName].classList.remove('hidden');
}

// Elements
const overlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');

function showLoading(text) {
    loadingText.textContent = text;
    overlay.classList.remove('hidden');
}

function hideLoading() {
    overlay.classList.add('hidden');
}

function showError(msg) {
    alert("Error: " + msg);
}

// 1. Analyze Deal
document.getElementById('btn-analyze-deal').addEventListener('click', async () => {
    const brief = document.getElementById('deal-brief').value;
    if (!brief.trim()) return alert("Please enter a brief.");
    
    showLoading("Analyzing Deal...");
    try {
        const res = await fetch('/api/deals/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brief, context: "" })
        });
        
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        currentDealData = data;
        renderPreflight(data);
        showView('preflight');
    } catch (e) {
        showError(e.message);
    } finally {
        hideLoading();
    }
});

function renderPreflight(data) {
    const p = data.preflight;
    document.getElementById('preflight-status').textContent = p.status.toUpperCase();
    
    const riskEl = document.getElementById('risk-score');
    riskEl.textContent = p.risk_score + "/100";
    riskEl.className = 'score-value ' + (p.risk_score > 66 ? 'risk-high' : (p.risk_score > 33 ? 'risk-med' : 'risk-low'));
    
    document.getElementById('confidence-score').textContent = p.confidence_score + "/100";
    
    renderList('list-unknowns', p.unknowns);
    renderList('list-blocking-unknowns', p.blocking_unknowns);
    renderList('list-questions', p.questions_to_ask);
}

function renderList(elementId, items) {
    const ul = document.getElementById(elementId);
    ul.innerHTML = '';
    if (!items || items.length === 0) {
        ul.innerHTML = '<li><em>None</em></li>';
        return;
    }
    items.forEach(item => {
        const li = document.createElement('li');
        li.textContent = item;
        ul.appendChild(li);
    });
}

// 2. Save Deal
document.getElementById('btn-save-deal').addEventListener('click', async () => {
    showLoading("Saving Deal...");
    try {
        const res = await fetch('/api/deals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentDealData)
        });
        
        if (!res.ok) throw new Error(await res.text());
        const saved = await res.json();
        currentDealId = saved.id;
        
        // Fetch to confirm and render memory
        loadDealMemory(currentDealId);
    } catch (e) {
        showError(e.message);
        hideLoading();
    }
});

document.getElementById('btn-back-new').addEventListener('click', () => showView('newDeal'));

// 3. Deal Memory
async function loadDealMemory(id) {
    try {
        const res = await fetch(`/api/deals/${id}`);
        if (!res.ok) throw new Error(await res.text());
        const deal = await res.json();
        
        document.getElementById('memory-deal-id').textContent = deal.id;
        document.getElementById('mem-title').textContent = deal.project.title;
        document.getElementById('mem-budget').textContent = deal.commercial.budget;
        document.getElementById('mem-deadline').textContent = deal.timeline.deadline;
        
        renderList('mem-included', deal.scope.deliverables);
        renderList('mem-excluded', deal.scope.exclusions);
        
        const decs = deal.decisions.map(d => `${d.description} (${d.status})`);
        renderList('mem-decisions', decs.length ? decs : ['None']);
        
        showView('dealMemory');
    } catch(e) {
        showError(e.message);
    } finally {
        hideLoading();
    }
}

// 4. Modal for New Message
const modal = document.getElementById('modal-message');
document.getElementById('btn-open-message').addEventListener('click', () => {
    document.getElementById('msg-content').value = '';
    modal.classList.remove('hidden');
});
document.getElementById('btn-close-modal').addEventListener('click', () => {
    modal.classList.add('hidden');
});

// 5. Analyze Message (Scope Guard & Response)
document.getElementById('btn-analyze-msg').addEventListener('click', async () => {
    const content = document.getElementById('msg-content').value;
    const objective = document.getElementById('msg-objective').value;
    const tone = document.getElementById('msg-tone').value;
    
    if (!content.trim()) return alert("Please enter a message.");
    
    modal.classList.add('hidden');
    showLoading("Analyzing Scope & Preparing Response...");
    
    try {
        const res = await fetch(`/api/deals/${currentDealId}/analyze_message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'client', content, objective, tone })
        });
        
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        
        renderScopeGuardAndResponse(data);
        showView('scopeGuard');
    } catch(e) {
        showError(e.message);
    } finally {
        hideLoading();
    }
});

function renderScopeGuardAndResponse(data) {
    const diff = data.message_analysis.scope_guard;
    
    // Meta
    document.getElementById('diff-classification').textContent = diff.classification.replace(/_/g, ' ');
    const commBadge = document.getElementById('diff-commercial');
    commBadge.textContent = 'COMMERCIAL IMPACT: ' + diff.commercial_impact.level.toUpperCase();
    commBadge.className = 'badge commercial-badge ' + diff.commercial_impact.level.toLowerCase();
    
    // Added
    renderList('diff-added', diff.added);
    document.querySelector('.added-section').style.display = diff.added.length ? 'block' : 'none';
    
    // Conflicting
    renderList('diff-conflicting', diff.conflicting);
    document.querySelector('.conflicting-section').style.display = diff.conflicting.length ? 'block' : 'none';
    
    // Changed
    const changedUl = document.getElementById('diff-changed');
    changedUl.innerHTML = '';
    if (diff.changed && diff.changed.length > 0) {
        document.querySelector('.changed-section').style.display = 'block';
        diff.changed.forEach(c => {
            const li = document.createElement('li');
            li.textContent = `${c.item}: ${c.before} → ${c.after}`;
            changedUl.appendChild(li);
        });
    } else {
        document.querySelector('.changed-section').style.display = 'none';
    }
    
    // Unchanged
    renderList('diff-unchanged', diff.unchanged);
    document.querySelector('.unchanged-section').style.display = diff.unchanged.length ? 'block' : 'none';
    
    // Evidence & Action
    document.getElementById('diff-evidence-text').textContent = diff.evidence.join(' ');
    document.getElementById('diff-recommended').textContent = diff.recommended_action;
    
    // Response Intelligence
    document.getElementById('resp-intent').textContent = data.message_analysis.intent.primary.replace(/_/g, ' ');
    document.getElementById('resp-strategy').textContent = data.strategy.recommended_action;
    document.getElementById('resp-draft').value = data.response.draft;
}

document.getElementById('btn-back-memory').addEventListener('click', () => showView('dealMemory'));

document.getElementById('btn-copy-response').addEventListener('click', () => {
    const text = document.getElementById('resp-draft').value;
    navigator.clipboard.writeText(text).then(() => {
        alert("Copied to clipboard!");
    });
});
