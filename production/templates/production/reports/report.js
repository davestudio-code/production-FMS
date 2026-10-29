function switchReportMainTab(tabKey) {
    const isExecutive = (tabKey === 'executive');
    document.getElementById('mainTabExecutive').classList.toggle('active', isExecutive);
    document.getElementById('mainTabAudit').classList.toggle('active', !isExecutive);
    document.getElementById('paneExecutiveReport').style.display = isExecutive ? 'block' : 'none';
    document.getElementById('paneAuditReport').style.display = isExecutive ? 'none' : 'block';
    const actionGroup = document.getElementById('reportActionBtnGroup');
    if (actionGroup) actionGroup.style.display = isExecutive ? 'block' : 'none';
    if (!isExecutive) {
        applyAuditFilters();
    }
}

let activeAuditTab = 'dispatches';
const auditPages = { dispatches: 1, quality: 1 };
const pageSize = 25;

function switchAuditTab(tabKey) {
    activeAuditTab = tabKey;
    document.getElementById('tabBtnDispatches').classList.toggle('active', tabKey === 'dispatches');
    document.getElementById('tabBtnQuality').classList.toggle('active', tabKey === 'quality');
    document.getElementById('paneDispatches').classList.toggle('active', tabKey === 'dispatches');
    document.getElementById('paneQuality').classList.toggle('active', tabKey === 'quality');
    applyAuditFilters();
}

function applyAuditFilters() {
    const q = (document.getElementById('auditSearchInput').value || '').trim().toLowerCase();
    const orderFilter = (document.getElementById('auditOrderSelect').value || '').trim();
    const dateFrom = document.getElementById('auditDateFrom').value;
    const dateTo = document.getElementById('auditDateTo').value;

    const rowClass = activeAuditTab === 'dispatches' ? '.dispatchRow' : '.qualityRow';
    const rows = Array.from(document.querySelectorAll(rowClass));

    const matchedRows = [];
    rows.forEach(row => {
        const searchBlob = row.dataset.search || '';
        const rowOrder = row.dataset.order || '';
        const rowDate = row.dataset.date || '';

        let matches = true;
        if (q && !searchBlob.includes(q)) matches = false;
        if (orderFilter && rowOrder !== orderFilter) matches = false;
        if (dateFrom && rowDate && rowDate < dateFrom) matches = false;
        if (dateTo && rowDate && rowDate > dateTo) matches = false;

        if (matches) {
            matchedRows.push(row);
        } else {
            row.style.display = 'none';
        }
    });

    const currentPage = auditPages[activeAuditTab];
    const totalRecords = matchedRows.length;
    const totalPages = Math.ceil(totalRecords / pageSize) || 1;
    if (currentPage > totalPages) auditPages[activeAuditTab] = totalPages;
    const effectivePage = auditPages[activeAuditTab];

    const startIndex = (effectivePage - 1) * pageSize;
    const endIndex = startIndex + pageSize;

    matchedRows.forEach((row, idx) => {
        row.style.display = (idx >= startIndex && idx < endIndex) ? '' : 'none';
    });

    const infoEl = document.getElementById(activeAuditTab + 'PageInfo');
    const indicatorEl = document.getElementById(activeAuditTab + 'PageIndicator');
    const prevBtn = document.getElementById(activeAuditTab + 'PrevBtn');
    const nextBtn = document.getElementById(activeAuditTab + 'NextBtn');

    if (totalRecords === 0) {
        if (infoEl) infoEl.textContent = 'No records match filter';
        if (indicatorEl) indicatorEl.textContent = '0 of 0';
        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = true;
    } else {
        const startDisplay = startIndex + 1;
        const endDisplay = Math.min(endIndex, totalRecords);
        if (infoEl) infoEl.textContent = `Showing ${startDisplay}-${endDisplay} of ${totalRecords}`;
        if (indicatorEl) indicatorEl.textContent = `Page ${effectivePage} of ${totalPages}`;
        if (prevBtn) prevBtn.disabled = effectivePage <= 1;
        if (nextBtn) nextBtn.disabled = effectivePage >= totalPages;
    }
}

function changeAuditPage(tabKey, delta) {
    auditPages[tabKey] += delta;
    if (auditPages[tabKey] < 1) auditPages[tabKey] = 1;
    applyAuditFilters();
}

function resetAuditFilters() {
    document.getElementById('auditSearchInput').value = '';
    document.getElementById('auditOrderSelect').value = '';
    document.getElementById('auditDateFrom').value = '';
    document.getElementById('auditDateTo').value = '';
    auditPages.dispatches = 1;
    auditPages.quality = 1;
    applyAuditFilters();
}

window.filterReportOrders = function() {
    const status = (document.getElementById('reportStatusSelect')?.value || '').trim();
    const resetBtn = document.getElementById('reportResetBtn');
    if (resetBtn) {
        resetBtn.style.display = status ? 'inline-block' : 'none';
    }
    const rows = document.querySelectorAll('tr.reportOrderRow');
    let visibleCount = 0;
    rows.forEach(function(row) {
        const rowStatus = row.dataset.status || '';
        const match = !status || rowStatus === status;
        row.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    const emptyRow = document.getElementById('reportEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
    const badge = document.getElementById('reportBatchBadge');
    if (badge) {
        badge.textContent = `${visibleCount} ${visibleCount === 1 ? 'Batch' : 'Batches'}`;
        badge.className = 'statusBadge ' + (status === 'Completed' ? 'completed' : 'inProgress');
    }
};

window.resetReportFilter = function() {
    const statusSelect = document.getElementById('reportStatusSelect');
    if (statusSelect) statusSelect.value = '';
    window.filterReportOrders();
};

function initReportWorkspace() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('tab') === 'audit') {
        switchReportMainTab('audit');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReportWorkspace);
} else {
    initReportWorkspace();
}
