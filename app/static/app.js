// State
let currentDeal = null;
let currentDealId = null;

// DOM Elements
const views = {
    dashboard: document.getElementById('view-dashboard'),
    newDeal: document.getElementById('view-new-deal'),
    preflight: document.getElementById('view-preflight'),
    dealMemory: document.getElementById('view-deal-memory'),
    scopeGuard: document.getElementById('view-scope-guard'),
    howItWorks: document.getElementById('view-how-it-works')
};

const navLinks = {
    dashboard: document.getElementById('nav-dashboard'),
    newDeal: document.getElementById('nav-new-deal'),
    howItWorks: document.getElementById('nav-how-it-works')
};

// UI Helpers
const showView = (viewName) => {
    Object.values(views).forEach(v => {
        if (v) {
            v.classList.add('hidden');
            v.classList.remove('active');
        }
    });
    Object.values(navLinks).forEach(l => {
        if (l) l.classList.remove('active');
    });
    
    if (views[viewName]) {
        views[viewName].classList.remove('hidden');
        views[viewName].classList.add('active');
    }
    
    if (navLinks[viewName]) {
        navLinks[viewName].classList.add('active');
    }
    
    if (viewName === 'dashboard') {
        loadDashboard();
    }
};

const showLoading = (text = 'Analizando proyecto...') => {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.remove('hidden');
};

const hideLoading = () => {
    document.getElementById('loading-overlay').classList.add('hidden');
};

const showError = (msg) => {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-toast';
    errorDiv.textContent = msg;
    document.body.appendChild(errorDiv);
    setTimeout(() => {
        errorDiv.classList.add('fade-out');
        setTimeout(() => errorDiv.remove(), 300);
    }, 5000);
};

const getBadgeClass = (value) => {
    if (!value) return 'neutral';
    const v = value.toLowerCase();
    if (v.includes('in_scope') || v.includes('low') || v.includes('ready') || v.includes('listo') || v.includes('completed') || v.includes('finalizado')) return 'success';
    if (v.includes('out_of_scope') || v.includes('medium') || v.includes('needs_clarification') || v.includes('aclaracion') || v.includes('in_progress') || v.includes('en_curso')) return 'warning';
    if (v.includes('conflict') || v.includes('high') || v.includes('critical') || v.includes('do_not_quote') || v.includes('no_presupuestar') || v.includes('rejected') || v.includes('rechazado')) return 'danger';
    return 'neutral';
};

const formatStatusLabel = (status) => {
    if (!status) return '';
    const s = status.toLowerCase();
    if (s === 'ready' || s === 'listo') return 'Listo';
    if (s === 'needs_clarification' || s === 'requiere_aclaracion') return 'Requiere aclaración';
    if (s === 'do_not_quote' || s === 'no_presupuestar') return 'No presupuestar';
    return status;
};

const formatProjectStatusLabel = (status) => {
    if (!status) return 'En espera de mensaje';
    const s = status.toLowerCase();
    if (s === 'waiting_message' || s === 'en_espera_de_mensaje') return 'En espera de mensaje';
    if (s === 'in_progress' || s === 'en_curso') return 'En curso';
    if (s === 'rejected' || s === 'rechazado') return 'Rechazado';
    if (s === 'completed' || s === 'finalizado') return 'Finalizado';
    return status;
};

const getProjectStatusBadgeClass = (status) => {
    if (!status) return 'neutral';
    const s = status.toLowerCase();
    if (s === 'waiting_message') return 'neutral';
    if (s === 'in_progress') return 'warning';
    if (s === 'rejected') return 'danger';
    if (s === 'completed') return 'success';
    return 'neutral';
};

const formatPriorityLabel = (priority) => {
    if (!priority) return '';
    const p = priority.toLowerCase();
    if (p === 'high') return 'Alta';
    if (p === 'medium') return 'Media';
    if (p === 'low') return 'Baja';
    if (p === 'critical') return 'Crítica';
    return priority;
};

const populateUnknownsList = (elementId, items) => {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '';
    if (!items || items.length === 0) {
        el.innerHTML = '<li><em>Ninguno</em></li>';
        return;
    }
    items.forEach(item => {
        const li = document.createElement('li');
        li.className = 'unknown-card-item';
        
        let title = 'Aspecto pendiente';
        let desc = '';
        let sev = 'medium';
        
        if (typeof item === 'string') {
            desc = item;
        } else if (item) {
            title = (item.title && item.title.trim()) || 'Aspecto pendiente';
            desc = item.description || item.item || '';
            sev = item.severity || 'medium';
        }
        
        const sevLabel = formatPriorityLabel(sev);
        const badgeClass = getBadgeClass(sev);
        
        li.innerHTML = `
            <div class="unknown-header">
                <span class="unknown-title">${title}</span>
                <span class="badge ${badgeClass}">${sevLabel}</span>
            </div>
            ${desc ? `<p class="unknown-desc">${desc}</p>` : ''}
        `;
        el.appendChild(li);
    });
};

const populateList = (elementId, items) => {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '';
    if (!items || items.length === 0) {
        el.innerHTML = '<li><em>Ninguno</em></li>';
        return;
    }
    items.forEach(item => {
        const li = document.createElement('li');
        if (typeof item === 'string') {
            li.textContent = item;
        } else if (item && item.description) {
            const sev = item.severity ? `[${formatPriorityLabel(item.severity)}] ` : '';
            li.textContent = `${sev}${item.description}`;
        } else if (item && item.item) {
            li.textContent = item.item;
        } else {
            li.textContent = JSON.stringify(item);
        }
        el.appendChild(li);
    });
};

const populateChangedList = (elementId, items) => {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '';
    if (!items || items.length === 0) {
        el.innerHTML = '<li><em>Ninguno</em></li>';
        return;
    }
    items.forEach(c => {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${c.item}</strong>: ${c.before} &rarr; ${c.after}`;
        el.appendChild(li);
    });
};

// Navigation Listeners
if (navLinks.dashboard) navLinks.dashboard.addEventListener('click', (e) => { e.preventDefault(); showView('dashboard'); });
if (navLinks.newDeal) navLinks.newDeal.addEventListener('click', (e) => { e.preventDefault(); showView('newDeal'); });
if (navLinks.howItWorks) navLinks.howItWorks.addEventListener('click', (e) => { e.preventDefault(); showView('howItWorks'); });
document.getElementById('btn-goto-new').addEventListener('click', () => showView('newDeal'));
document.getElementById('btn-back-new').addEventListener('click', () => showView('newDeal'));
document.getElementById('btn-back-memory').addEventListener('click', () => showView('dealMemory'));

// Status change listener
const statusSelector = document.getElementById('mem-status-select');
if (statusSelector) {
    statusSelector.addEventListener('change', async (e) => {
        const newStatus = e.target.value;
        if (!currentDealId) return;
        showLoading('Actualizando estado del proyecto...');
        try {
            const res = await fetch(`/api/deals/${currentDealId}/status`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (!res.ok) throw new Error('Error al actualizar el estado del proyecto');
            if (currentDeal) currentDeal.status = newStatus;
        } catch (err) {
            showError(err.message);
            if (currentDeal && currentDeal.status) {
                statusSelector.value = currentDeal.status;
            }
        } finally {
            hideLoading();
        }
    });
}

// API Calls
async function loadDashboard() {
    try {
        const res = await fetch('/api/deals');
        if (!res.ok) throw new Error('Error al cargar la lista de proyectos');
        const deals = await res.json();
        
        const tbody = document.getElementById('deals-table-body');
        tbody.innerHTML = '';
        
        if (deals.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No se encontraron proyectos. ¡Creá uno!</td></tr>';
            return;
        }
        
        deals.forEach(deal => {
            const tr = document.createElement('tr');
            const dealTitle = (deal.title && deal.title.trim()) || 'Proyecto sin título';
            const clientName = deal.client || 'Desconocido';
            const companySub = deal.company ? `<br><span class="text-small" style="color: var(--text-secondary);">${deal.company}</span>` : '<br><span class="text-small" style="color: var(--text-secondary);">Cliente privado</span>';
            const projectStatusLabel = formatProjectStatusLabel(deal.status);
            const preflightStatusLabel = formatStatusLabel(deal.preflight_status);
            
            tr.innerHTML = `
                <td class="table-link">${dealTitle}</td>
                <td><strong>${clientName}</strong>${companySub}</td>
                <td>${deal.budget} ${deal.currency || 'USD'}</td>
                <td>${deal.deadline || 'A definir'}</td>
                <td><span class="badge ${getProjectStatusBadgeClass(deal.status)}">${projectStatusLabel}</span></td>
                <td><span class="badge ${getBadgeClass(deal.preflight_status)}">${preflightStatusLabel}</span></td>
            `;
            tr.addEventListener('click', () => loadDeal(deal.id));
            tbody.appendChild(tr);
        });
    } catch (err) {
        showError(err.message);
    }
}

async function loadDeal(id) {
    showLoading('Cargando memoria del proyecto...');
    try {
        const res = await fetch(`/api/deals/${id}`);
        if (!res.ok) throw new Error('No se pudo cargar el proyecto');
        currentDeal = await res.json();
        currentDealId = id;
        
        renderDealMemory(currentDeal);
        showView('dealMemory');
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

function renderDealMemory(deal) {
    const memTitle = (deal.project && deal.project.title && deal.project.title.trim()) || 
                     (deal.project && deal.project.description && deal.project.description.trim()) || 
                     'Proyecto sin título';
    document.getElementById('mem-title').textContent = memTitle;
    
    // Client info
    const cName = (deal.client && deal.client.name) ? deal.client.name : 'Desconocido';
    const cComp = (deal.client && deal.client.company) ? deal.client.company : 'Cliente privado';
    document.getElementById('mem-client-info').innerHTML = `<strong>Cliente:</strong> ${cName} &bull; <strong>Organización:</strong> ${cComp}`;
    
    // Project status selector
    const sel = document.getElementById('mem-status-select');
    if (sel) {
        sel.value = deal.status || 'waiting_message';
    }
    
    // Preflight status badge
    document.getElementById('mem-preflight-status').textContent = formatStatusLabel(deal.preflight.status);
    document.getElementById('mem-preflight-status').className = `badge ${getBadgeClass(deal.preflight.status)}`;
    
    document.getElementById('mem-budget').textContent = `${deal.commercial.budget} ${deal.commercial.currency || 'USD'}`;
    document.getElementById('mem-deadline').textContent = deal.timeline.deadline || 'A definir';
    
    document.getElementById('mem-risk').textContent = `${deal.preflight.risk_score}/100`;
    document.getElementById('mem-confidence').textContent = `${Math.round(deal.preflight.confidence * 100)}/100`;
    
    populateList('mem-included', deal.scope.deliverables);
    populateList('mem-excluded', deal.scope.exclusions);
    
    document.getElementById('msg-content').value = '';
}

// Create Deal Flow
document.getElementById('btn-analyze-deal').addEventListener('click', async () => {
    const clientName = document.getElementById('deal-client-name').value.trim();
    const clientCompany = document.getElementById('deal-client-company').value.trim();
    const brief = document.getElementById('deal-brief').value;
    const budget = document.getElementById('deal-budget').value;
    const currency = document.getElementById('deal-currency').value;
    const deadline = document.getElementById('deal-deadline').value;
    
    if (!clientName) return showError('Por favor, ingresá el nombre del cliente (obligatorio)');
    if (!brief) return showError('Por favor, ingresá el brief o mensaje del cliente');
    
    showLoading('Analizando parámetros del proyecto...');
    try {
        const payload = { 
            message: brief,
            client_name: clientName,
            client_company: clientCompany || undefined
        };
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
            throw new Error(err.detail || 'El análisis del proyecto falló');
        }
        
        const data = await res.json();
        currentDeal = data.deal;
        renderPreflight(currentDeal);
        showView('preflight');
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
});

function renderPreflight(deal) {
    document.getElementById('preflight-status').textContent = formatStatusLabel(deal.preflight.status);
    document.getElementById('preflight-status').className = `badge ${getBadgeClass(deal.preflight.status)}`;
    document.getElementById('risk-score').textContent = `${deal.preflight.risk_score}/100`;
    document.getElementById('confidence-score').textContent = `${Math.round(deal.preflight.confidence * 100)}/100`;
    
    populateUnknownsList('list-unknowns', deal.unknowns);
    populateUnknownsList('list-blocking-unknowns', deal.unknowns.filter(u => u.blocks_quote));
    
    const questionList = document.getElementById('list-questions');
    questionList.innerHTML = '';
    if (!deal.questions || deal.questions.length === 0) {
        questionList.innerHTML = '<li><em>Ninguna</em></li>';
    } else {
        deal.questions.forEach(q => {
            const li = document.createElement('li');
            const prio = formatPriorityLabel(q.priority);
            li.innerHTML = `<strong>[${prio}]</strong> ${q.question}`;
            questionList.appendChild(li);
        });
    }
}

document.getElementById('btn-save-deal').addEventListener('click', async () => {
    if (!currentDeal) return;
    
    showLoading('Guardando y registrando proyecto...');
    try {
        const res = await fetch('/api/deals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentDeal)
        });
        
        if (!res.ok) throw new Error('Error al guardar el proyecto');
        const data = await res.json();
        
        // Load the deal to go to memory view
        await loadDeal(data.deal_id);
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
});

// Analyze Message Flow
document.getElementById('btn-analyze-msg').addEventListener('click', async () => {
    const content = document.getElementById('msg-content').value;
    const objective = document.getElementById('msg-objective').value;
    const tone = document.getElementById('msg-tone').value;
    
    if (!content) return showError('Por favor, ingresá el mensaje del cliente');
    
    showLoading('Analizando cambio de alcance y estrategia...');
    try {
        const res = await fetch(`/api/deals/${currentDealId}/analyze_message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sender: 'client', content, objective, tone })
        });
        
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Error al analizar el mensaje');
        }
        
        const intelligence = await res.json();
        renderAnalysis(intelligence);
        showView('scopeGuard');
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
});

function renderAnalysis(intelligence) {
    const guard = intelligence.message_analysis.scope_guard;
    const intent = intelligence.message_analysis.intent;
    const strategy = intelligence.strategy;
    const response = intelligence.response;
    
    const classMap = {
        'in_scope': 'Dentro del alcance',
        'potentially_out_of_scope': 'Cambio de alcance detectado',
        'conflict_with_exclusion': 'Conflicto con exclusión',
        'unclear': 'Requiere aclaración'
    };
    
    const intentMap = {
        'add_feature': 'Agregar funcionalidad',
        'request_excluded_service': 'Solicitud de servicio excluido',
        'price_negotiation': 'Negociación de precio',
        'clarification': 'Pedido de aclaración',
        'general_inquiry': 'Consulta general',
        'accept_terms': 'Aceptar términos'
    };
    
    // Scope Diff
    document.getElementById('diff-classification').textContent = classMap[guard.classification] || guard.classification;
    document.getElementById('diff-classification').className = `badge ${getBadgeClass(guard.classification)}`;
    
    // Commercial Impact
    const impactMap = {
        'low': 'BAJO',
        'medium': 'MEDIO',
        'high': 'ALTO',
        'critical': 'CRÍTICO'
    };
    const lvlKey = (guard.commercial_impact.level || '').toLowerCase();
    document.getElementById('diff-commercial-level').textContent = impactMap[lvlKey] || (guard.commercial_impact.level || '').toUpperCase();
    document.getElementById('diff-commercial-level').className = `badge ${getBadgeClass(guard.commercial_impact.level)}`;
    document.getElementById('diff-commercial-reason').textContent = guard.commercial_impact.reason;
    document.getElementById('diff-commercial-action').textContent = guard.commercial_impact.pricing_action;
    
    const toggleSection = (sectionId, arr) => {
        const el = document.getElementById(sectionId);
        if (!arr || arr.length === 0) el.classList.add('hidden');
        else el.classList.remove('hidden');
    };
    
    populateList('diff-added', guard.added);
    toggleSection('section-added', guard.added);
    
    populateChangedList('diff-changed', guard.changed);
    toggleSection('section-changed', guard.changed);
    
    populateList('diff-conflicting', guard.conflicting);
    toggleSection('section-conflicting', guard.conflicting);
    
    populateList('diff-unchanged', guard.unchanged);
    toggleSection('section-unchanged', guard.unchanged);
    
    // Strategy
    document.getElementById('resp-intent').textContent = intentMap[intent.primary] || intent.primary;
    document.getElementById('resp-strategy').textContent = strategy.recommended_action;
    populateList('resp-reasoning', strategy.reasoning);
    
    // Draft Response
    const draftTextarea = document.getElementById('resp-draft');
    draftTextarea.value = response.draft;
    
    const reviewBadge = document.getElementById('review-badge');
    
    // Reset review UI state
    document.getElementById('review-actions').classList.remove('hidden');
    document.getElementById('review-status-msg').classList.add('hidden');
    draftTextarea.disabled = false;
    
    if (response.requires_review) {
        reviewBadge.classList.remove('hidden');
        draftTextarea.classList.add('requires-review');
    } else {
        reviewBadge.classList.add('hidden');
        draftTextarea.classList.remove('requires-review');
    }
}

async function submitReview(status) {
    const draft = document.getElementById('resp-draft').value;
    showLoading('Registrando aprobación...');
    try {
        const res = await fetch(`/api/deals/${currentDealId}/reviews`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status, draft })
        });
        
        if (!res.ok) throw new Error('Error al registrar la revisión');
        
        document.getElementById('review-actions').classList.add('hidden');
        const statusMsg = document.getElementById('review-status-msg');
        statusMsg.classList.remove('hidden');
        statusMsg.textContent = status === 'approved' ? '✅ Aprobado por humano' : '❌ Rechazado por humano';
        statusMsg.style.backgroundColor = status === 'approved' ? 'var(--success, #10b981)' : 'var(--danger, #ef4444)';
        statusMsg.style.color = 'white';
        document.getElementById('resp-draft').disabled = true;
    } catch (err) {
        showError(err.message);
    } finally {
        hideLoading();
    }
}

document.getElementById('btn-approve-response').addEventListener('click', () => submitReview('approved'));
document.getElementById('btn-reject-response').addEventListener('click', () => submitReview('rejected'));

// Init
showView('dashboard');
