function openScheduleModal(orderID, productName, startDate, dueDate) {
    document.getElementById('scheduleForm').action = "/production/planning/update/" + orderID;
    document.getElementById('scheduleModalTitle').textContent = "Edit Schedule: Order #PO-" + orderID;
    document.getElementById('scheduleOrderProduct').textContent = productName;
    document.getElementById('scheduleStartDate').value = startDate || '';
    document.getElementById('scheduleDueDate').value = dueDate || '';
    openModal('scheduleModal');
}

window.filterPlanningTable = function() {
    const q = (document.getElementById('globalTabSearchInput')?.value || '').toLowerCase().trim();
    const status = (document.getElementById('planningStatusSelect')?.value || '').trim();
    const resetBtn = document.getElementById('planningResetBtn');
    if (resetBtn) {
        resetBtn.style.display = status ? 'inline-block' : 'none';
    }
    const rows = document.querySelectorAll('tr.planningRow');
    let visibleCount = 0;
    rows.forEach(function(row) {
        const rowStatus = row.dataset.status || '';
        const rowSearch = row.dataset.search || '';
        const matchStatus = !status || rowStatus === status;
        const matchSearch = !q || rowSearch.includes(q);
        if (matchStatus && matchSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    const emptyRow = document.getElementById('planningEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
};

window.resetPlanningFilter = function() {
    const qInput = document.getElementById('globalTabSearchInput');
    const statusSelect = document.getElementById('planningStatusSelect');
    if (qInput) qInput.value = '';
    if (typeof window.updateGlobalSearchClearBtn === 'function') {
        window.updateGlobalSearchClearBtn();
    }
    if (statusSelect) statusSelect.value = '';
    window.filterPlanningTable();
};
