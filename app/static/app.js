// State
let currentDeal = null;
let currentDealId = null;

// DOM Elements
const views = {
    dashboard: document.getElementById('view-dashboard'),
    newDeal: document.getElementById('view-new-deal'),
    preflight: document.getElementById('view-preflight'),
    dealMemory: document.getElementById('view-deal-memory'),
    scopeGuard: document.getElementById('view-scope-guard')
};

const navLinks = {
    dashboard: document.getElementById('nav-dashboard'),
    newDeal: document.getElementById('nav-new-deal')
};

// UI Helpers
const showView = (viewName) => {
    Object.values(views).forEach(v => v.classList.add('hidden'));
    Object.values(navLinks).forEach(l => l.classList.remove('active'));
    
    views[viewName].classList.remove('hidden');
    views[viewName].classList.add('active');
    
    if (navLinks[viewName]) {
        navLinks[viewName].classList.add('active');
    }
    
    if (viewName === 'dashboard') {
        loadDashboard();
    }
};

const showLoading = (text = 'Analyzing...') => {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
};

const hideLoading = () => {
    document.getElementById('loading-overlay').classList.add('hidden');
};

const getBadgeClass = (value) => {
    if (!value) return 'neutral';
    const v = value.toLowerCase();
    if (v.includes('in_scope') || v.includes('low')) return 'success';
    if (v.includes('out_of_scope') || v.includes('medium')) return 'warning';
    if (v.includes('conflict') || v.includes('high')) return 'danger';
    return 'neutral';
};

const populateList = (elementId, items) => {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    if (!items || items.length === 0) {
        el.innerHTML = '<li><em>None</em></li>';
        return;
    }
    items.forEach(item => {
        const li = document.createElement('li');
        li.textContent = typeof item === 'string' ? item : item.item;
        el.appendChild(li);
    });
};

const populateChangedList = (elementId, items) => {
    const el = document.getElementById(elementId);
    el.innerHTML = '';
    if (!items || items.length === 0) {
        el.innerHTML = '<li><em>None</em></li>';
        return;
    }
    items.forEach(c => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${c.item}</strong>: ${c.before} &rarr; ${c.after}`;
        el.appendChild(li);
    });
};

// Navigation Listeners
navLinks.dashboard.addEventListener('click', (e) => { e.preventDefault(); showView('dashboard'); });
navLinks.newDeal.addEventListener('click', (e) => { e.preventDefault(); showView('newDeal'); });
document.getElementById('btn-goto-new').addEventListener('click', () => showView('newDeal'));
document.getElementById('btn-back-new').addEventListener('click', () => showView('newDeal'));
document.getElementById('btn-back-memory').addEventListener('click', () => showView('dealMemory'));

// API Calls
async function loadDashboard() {
    try {
        const res = await fetch('/api/deals');
        if (!res.ok) throw new Error('Failed to fetch deals');
        const deals = await res.json();
        
        const tbody = document.getElementById('deals-table-body');
        tbody.innerHTML = '';
        
        if (deals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No deals found. Create one!</td></tr>';
            return;
        }
        
        deals.forEach(deal => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td class="table-link">${deal.title}</td>
                <td>${deal.client}</td>
                <td>${deal.budget} ${deal.currency}</td>
                <td>${deal.deadline}</td>
                <td><span class="badge ${getBadgeClass(deal.status)}">${deal.status}</span></td>
            `;
            tr.addEventListener('click', () => loadDeal(deal.id));
            tbody.appendChild(tr);
        });
    } catch (err) {
        alert(err.message);
    }
}

async function loadDeal(id) {
    showLoading('Loading Deal...');
    try {
        const res = await fetch(`/api/deals/${id}`);
        if (!res.ok) throw new Error('Failed to load deal');
        currentDeal = await res.json();
        currentDealId = id;
        
        renderDealMemory(currentDeal);
        showView('dealMemory');
    } catch (err) {
        alert(err.message);
    } finally {
        hideLoading();
    }
}

function renderDealMemory(deal) {
    document.getElementById('mem-title').textContent = deal.project.title;
    document.getElementById('mem-status').textContent = deal.preflight.status;
    document.getElementById('mem-status').className = `badge ${getBadgeClass(deal.preflight.status)}`;
    
    document.getElementById('mem-budget').textContent = `${deal.commercial.budget} ${deal.commercial.currency}`;
    document.getElementById('mem-deadline').textContent = deal.timeline.deadline;
    
    document.getElementById('mem-risk').textContent = `${deal.preflight.risk_score}/100`;
    document.getElementById('mem-confidence').textContent = `${deal.preflight.confidence}/100`;
    
    populateList('mem-included', deal.scope.deliverables);
    populateList('mem-excluded', deal.scope.exclusions);
    
    document.getElementById('msg-content').value = '';
}

// Create Deal Flow
document.getElementById('btn-analyze-deal').addEventListener('click', async () => {
    const brief = document.getElementById('deal-brief').value;
    const budget = document.getElementById('deal-budget').value;
    const currency = document.getElementById('deal-currency').value;
    const deadline = document.getElementById('deal-deadline').value;
    
    if (!brief) return alert('Please enter a brief');
    
    showLoading('Analyzing Deal Parameters...');
    try {
        const payload = { message: brief };
        if (budget) payload.budget = parseFloat(budget);
        if (currency) payload.currency = currency;
        if (deadline) payload.deadline = deadline;
        
        const res = await fetch('/api/deals/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Analysis failed');
        }
        
        const data = await res.json();
        currentDeal = data.deal;
        renderPreflight(currentDeal);
        showView('preflight');
    } catch (err) {
        alert(err.message);
    } finally {
        hideLoading();
    }
});

function renderPreflight(deal) {
    document.getElementById('preflight-status').textContent = deal.preflight.status;
    document.getElementById('preflight-status').className = `badge ${getBadgeClass(deal.preflight.status)}`;
    document.getElementById('risk-score').textContent = `${deal.preflight.risk_score}/100`;
    document.getElementById('confidence-score').textContent = `${deal.preflight.confidence}/100`;
    
    populateList('list-unknowns', deal.unknowns);
    populateList('list-blocking-unknowns', deal.unknowns.filter(u => u.blocks_quote));
    
    const questionList = document.getElementById('list-questions');
    questionList.innerHTML = '';
    deal.questions.forEach(q => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${q.category}:</strong> ${q.question}`;
        questionList.appendChild(li);
    });
}

document.getElementById('btn-save-deal').addEventListener('click', async () => {
    if (!currentDeal) return;
    
    showLoading('Saving Deal...');
    try {
        const res = await fetch('/api/deals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentDeal)
        });
        
        if (!res.ok) throw new Error('Failed to save deal');
        const data = await res.json();
        
        // Load the deal to go to memory view
        await loadDeal(data.deal_id);
    } catch (err) {
        alert(err.message);
    } finally {
        hideLoading();
    }
});

// Analyze Message Flow
document.getElementById('btn-analyze-msg').addEventListener('click', async () => {
    const content = document.getElementById('msg-content').value;
    const objective = document.getElementById('msg-objective').value;
    const tone = document.getElementById('msg-tone').value;
    
    if (!content) return alert('Enter a client message');
    
    showLoading('Analyzing Scope & Strategy...');
    try {
        const res = await fetch(`/api/deals/${currentDealId}/analyze_message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'client', content, objective, tone })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Message analysis failed');
        }
        
        const intelligence = await res.json();
        renderAnalysis(intelligence);
        showView('scopeGuard');
    } catch (err) {
        alert(err.message);
    } finally {
        hideLoading();
    }
});

function renderAnalysis(intelligence) {
    const guard = intelligence.message_analysis.scope_guard;
    const intent = intelligence.message_analysis.intent;
    const strategy = intelligence.strategy;
    const response = intelligence.response;
    
    // Scope Diff
    document.getElementById('diff-classification').textContent = guard.classification;
    document.getElementById('diff-classification').className = `badge ${getBadgeClass(guard.classification)}`;
    
    document.getElementById('diff-commercial').textContent = `COMMERCIAL IMPACT: ${guard.commercial_impact.level}`;
    document.getElementById('diff-commercial').className = `badge ${getBadgeClass(guard.commercial_impact.level)}`;
    
    populateList('diff-added', guard.added);
    populateChangedList('diff-changed', guard.changed);
    populateList('diff-conflicting', guard.conflicting);
    populateList('diff-unchanged', guard.unchanged);
    
    // Strategy
    document.getElementById('resp-intent').textContent = intent.primary;
    document.getElementById('resp-strategy').textContent = strategy.recommended_action;
    populateList('resp-reasoning', strategy.reasoning);
    document.getElementById('resp-pricing-action').textContent = guard.commercial_impact.pricing_action;
    
    // Draft Response
    const draftTextarea = document.getElementById('resp-draft');
    draftTextarea.value = response.draft;
    
    const reviewBadge = document.getElementById('review-badge');
    const approveBtn = document.getElementById('btn-approve-response');
    
    if (response.requires_review) {
        reviewBadge.classList.remove('hidden');
        draftTextarea.classList.add('requires-review');
        approveBtn.textContent = 'Approve (Review Required)';
    } else {
        reviewBadge.classList.add('hidden');
        draftTextarea.classList.remove('requires-review');
        approveBtn.textContent = 'Approve & Send';
    }
}

document.getElementById('btn-approve-response').addEventListener('click', () => {
    alert("Message Approved! (Sending is not implemented in this MVP)");
});

// Init
showView('dashboard');
