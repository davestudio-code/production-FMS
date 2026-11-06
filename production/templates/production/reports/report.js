const reportState = {
    activeTab: 'orders',
    pages: { orders: 1, materials: 1, dispatches: 1 },
    pageSizes: { orders: 10, materials: 10, dispatches: 10 }
};

window.setReportWorkspaceTab = function (tabKey) {
    const validTabs = ['orders', 'materials', 'dispatches'];
    const targetTab = validTabs.includes(tabKey) ? tabKey : 'orders';
    reportState.activeTab = targetTab;

    const tabInput = document.getElementById('reportActiveTabInput');
    if (tabInput) tabInput.value = targetTab;

    document.querySelectorAll('.workspaceFilterTabs .workspaceTabBtn[data-reporttab]').forEach(function (btn) {
        btn.classList.toggle('active', btn.getAttribute('data-reporttab') === targetTab);
    });

    const secOrders = document.getElementById('reportSectionOrders');
    const secMaterials = document.getElementById('reportSectionMaterials');
    const secDispatches = document.getElementById('reportSectionDispatches');
    if (secOrders) secOrders.style.display = targetTab === 'orders' ? 'block' : 'none';
    if (secMaterials) secMaterials.style.display = targetTab === 'materials' ? 'block' : 'none';
    if (secDispatches) secDispatches.style.display = targetTab === 'dispatches' ? 'block' : 'none';

    const tbOrders = document.getElementById('reportToolbarOrders');
    const tbMaterials = document.getElementById('reportToolbarMaterials');
    const tbDispatches = document.getElementById('reportToolbarDispatches');
    if (tbOrders) tbOrders.style.display = targetTab === 'orders' ? 'flex' : 'none';
    if (tbMaterials) tbMaterials.style.display = targetTab === 'materials' ? 'flex' : 'none';
    if (tbDispatches) tbDispatches.style.display = targetTab === 'dispatches' ? 'flex' : 'none';

    window.applyReportFilters();
};

function paginateAndRenderSection(sectionKey, allRows, matchedRows, emptyRowId) {
    const pageSize = reportState.pageSizes[sectionKey] || 10;
    const totalRecords = matchedRows.length;
    const totalPages = Math.ceil(totalRecords / pageSize) || 1;
    if (reportState.pages[sectionKey] > totalPages) {
        reportState.pages[sectionKey] = totalPages;
    }
    if (reportState.pages[sectionKey] < 1) {
        reportState.pages[sectionKey] = 1;
    }
    const currentPage = reportState.pages[sectionKey];
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = startIdx + pageSize;

    allRows.forEach(function (r) {
        r.style.display = 'none';
    });

    matchedRows.forEach(function (r, idx) {
        r.style.display = (idx >= startIdx && idx < endIdx) ? '' : 'none';
    });

    const emptyRow = document.getElementById(emptyRowId);
    if (emptyRow) {
        emptyRow.style.display = (totalRecords === 0 && allRows.length > 0) ? '' : 'none';
    }

    const infoEl = document.getElementById(sectionKey + 'PageInfo');
    const indicatorEl = document.getElementById(sectionKey + 'PageIndicator');
    const prevBtn = document.getElementById(sectionKey + 'PrevBtn');
    const nextBtn = document.getElementById(sectionKey + 'NextBtn');

    if (totalRecords === 0) {
        if (infoEl) infoEl.textContent = allRows.length === 0 ? '0 records' : 'No matching records';
        if (indicatorEl) indicatorEl.textContent = 'Page 0 of 0';
        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = true;
    } else {
        const startDisplay = startIdx + 1;
        const endDisplay = Math.min(endIdx, totalRecords);
        if (infoEl) infoEl.textContent = `Showing ${startDisplay}–${endDisplay} of ${totalRecords}`;
        if (indicatorEl) indicatorEl.textContent = `Page ${currentPage} of ${totalPages}`;
        if (prevBtn) prevBtn.disabled = currentPage <= 1;
        if (nextBtn) nextBtn.disabled = currentPage >= totalPages;
    }
}

window.applyReportFilters = function () {
    const q = (document.getElementById('globalTabSearchInput')?.value || '').trim().toLowerCase();

    const orderRows = Array.from(document.querySelectorAll('tr.reportOrderRow'));
    const matchedOrderRows = orderRows.filter(function (row) {
        const searchBlob = row.dataset.search || '';
        return !q || searchBlob.includes(q);
    });
    paginateAndRenderSection('orders', orderRows, matchedOrderRows, 'ordersEmptyFilterRow');

    const materialRows = Array.from(document.querySelectorAll('tr.reportMaterialRow'));
    const matchedMaterialRows = materialRows.filter(function (row) {
        const searchBlob = row.dataset.search || '';
        return !q || searchBlob.includes(q);
    });
    paginateAndRenderSection('materials', materialRows, matchedMaterialRows, 'materialsEmptyFilterRow');

    const auditOrder = (document.getElementById('auditOrderSelect')?.value || '').trim();
    const dateFrom = document.getElementById('auditDateFrom')?.value || '';
    const dateTo = document.getElementById('auditDateTo')?.value || '';

    const dispatchRows = Array.from(document.querySelectorAll('tr.dispatchRow'));
    const matchedDispatchRows = dispatchRows.filter(function (row) {
        const searchBlob = row.dataset.search || '';
        const rowOrder = row.dataset.order || '';
        const rowDate = row.dataset.date || '';
        if (q && !searchBlob.includes(q)) return false;
        if (auditOrder && rowOrder !== auditOrder) return false;
        if (dateFrom && rowDate && rowDate < dateFrom) return false;
        if (dateTo && rowDate && rowDate > dateTo) return false;
        return true;
    });
    paginateAndRenderSection('dispatches', dispatchRows, matchedDispatchRows, 'dispatchesEmptyFilterRow');
};

window.applyAuditFilters = window.applyReportFilters;

window.changeReportPage = function (sectionKey, delta) {
    if (!reportState.pages[sectionKey]) reportState.pages[sectionKey] = 1;
    reportState.pages[sectionKey] += delta;
    window.applyReportFilters();
};

window.changeReportPageSize = function (sectionKey, newSize) {
    const parsed = parseInt(newSize, 10);
    reportState.pageSizes[sectionKey] = (!isNaN(parsed) && parsed > 0) ? parsed : 10;
    reportState.pages[sectionKey] = 1;
    window.applyReportFilters();
};

window.resetAuditFilters = function () {
    const orderSel = document.getElementById('auditOrderSelect');
    const fromEl = document.getElementById('auditDateFrom');
    const toEl = document.getElementById('auditDateTo');
    if (orderSel) orderSel.value = '';
    if (fromEl) fromEl.value = '';
    if (toEl) toEl.value = '';
    reportState.pages.dispatches = 1;
    window.applyReportFilters();
};

function initReportWorkspace() {
    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = (urlParams.get('tab') || '').toLowerCase();
    if (tabParam === 'audit' || tabParam === 'dispatches') {
        window.setReportWorkspaceTab('dispatches');
    } else if (tabParam === 'materials') {
        window.setReportWorkspaceTab('materials');
    } else {
        window.setReportWorkspaceTab('orders');
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReportWorkspace);
} else {
    initReportWorkspace();
}
