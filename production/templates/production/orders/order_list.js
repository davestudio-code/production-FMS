function toggleOrderSource(source) {
    const salesGroup = document.getElementById('salesOrderGroup');
    const salesSelect = document.getElementById('salesOrderSelect');
    const salesHint = document.getElementById('salesOrderHint');
    if (source === 'sales') {
        salesGroup.style.display = 'flex';
    } else {
        salesGroup.style.display = 'none';
        if (salesSelect) salesSelect.value = '';
        if (salesHint) {
            salesHint.style.display = 'none';
            salesHint.textContent = '';
        }
    }
}

function onSalesOrderSelected() {
    const sel = document.getElementById('salesOrderSelect');
    const opt = sel.options[sel.selectedIndex];
    const hint = document.getElementById('salesOrderHint');
    if (opt && opt.value) {
        const qty = opt.dataset.qty;
        const furnId = opt.dataset.furnitureId;
        const customer = opt.dataset.customer;
        const orderDate = opt.dataset.orderDate;
        const qtyInput = document.querySelector('input[name="plannedQuantity"]');
        const furnSelect = document.querySelector('select[name="furnitureID"]');
        if (qty && qtyInput) qtyInput.value = qty;
        if (furnId && furnSelect && furnId !== '') {
            furnSelect.value = furnId;
        }
        if (hint) {
            hint.style.display = 'block';
            hint.textContent = `Customer: ${customer} | Placed on ${orderDate}`;
        }
    } else {
        if (hint) {
            hint.style.display = 'none';
            hint.textContent = '';
        }
    }
}

window.filterOrdersTable = function() {
    const q = (document.getElementById('orderSearchInput')?.value || '').toLowerCase().trim();
    const status = (document.getElementById('orderStatusSelect')?.value || '').trim();
    const resetBtn = document.getElementById('orderResetBtn');
    if (resetBtn) {
        resetBtn.style.display = (q || status) ? 'inline-block' : 'none';
    }
    const rows = document.querySelectorAll('tr.orderRow');
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
    const emptyRow = document.getElementById('ordersEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
};

window.resetOrdersFilter = function() {
    const qInput = document.getElementById('orderSearchInput');
    const statusSelect = document.getElementById('orderStatusSelect');
    if (qInput) qInput.value = '';
    if (statusSelect) statusSelect.value = '';
    window.filterOrdersTable();
};
