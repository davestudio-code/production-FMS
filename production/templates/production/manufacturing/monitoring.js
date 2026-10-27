function confirmMilestoneSubmit(form, orderId) {
    const select = form.querySelector('select[name="progress"]');
    const val = parseFloat(select ? select.value : 0);
    if (val >= 90) {
        return confirm("Confirm Workshop Assembly:\n\nAre you sure Order #PO-" + orderId + " has finished physical assembly and is ready for Quality Inspection (Feature 8)?");
    }
    return true;
}

function toggleRollbackForm(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'flex' : 'none';
    }
}

window.setMonitoringTab = function(stateVal) {
    const nextVal = stateVal || '';
    const stateInput = document.getElementById('monitoringStateSelect');
    if (stateInput) {
        stateInput.value = nextVal;
    }
    const tabs = document.querySelectorAll('.workspaceFilterTabs .workspaceTabBtn[data-state]');
    tabs.forEach(function(tab) {
        if ((tab.getAttribute('data-state') || '') === nextVal) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
    window.filterMonitoringTable();
};

window.filterMonitoringTable = function() {
    const q = (document.getElementById('globalTabSearchInput')?.value || '').toLowerCase().trim();
    const state = (document.getElementById('monitoringStateSelect')?.value || '').trim();
    const rows = document.querySelectorAll('tr.monitoringRow');
    let visibleCount = 0;
    rows.forEach(function(row) {
        const rowState = row.dataset.state || '';
        const rowSearch = row.dataset.search || '';
        const matchState = !state || rowState === state;
        const matchSearch = !q || rowSearch.includes(q);
        if (matchState && matchSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    const emptyRow = document.getElementById('monitoringEmptyFilterRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.filterMonitoringTable();
    });
} else {
    window.filterMonitoringTable();
}
