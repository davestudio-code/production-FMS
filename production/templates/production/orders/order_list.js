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

let currentOrdersPage = 1;
let ordersPageSize = 10;

window.filterOrdersTable = function(resetPage = true) {
    if (resetPage) {
        currentOrdersPage = 1;
    }
    const q = (document.getElementById('orderSearchInput')?.value || '').toLowerCase().trim();
    const status = (document.getElementById('orderStatusSelect')?.value || '').trim();
    const resetBtn = document.getElementById('orderResetBtn');
    if (resetBtn) {
        resetBtn.style.display = (q || status) ? 'inline-block' : 'none';
    }
    const allRows = Array.from(document.querySelectorAll('tr.orderRow'));
    const matchingRows = allRows.filter(function(row) {
        const rowStatus = row.dataset.status || '';
        const rowSearch = row.dataset.search || '';
        const matchStatus = !status || rowStatus === status;
        const matchSearch = !q || rowSearch.includes(q);
        return matchStatus && matchSearch;
    });

    const totalCount = matchingRows.length;
    const totalPages = Math.ceil(totalCount / ordersPageSize) || 1;
    if (currentOrdersPage > totalPages) currentOrdersPage = totalPages;
    if (currentOrdersPage < 1) currentOrdersPage = 1;

    const startIndex = (currentOrdersPage - 1) * ordersPageSize;
    const endIndex = Math.min(startIndex + ordersPageSize, totalCount);

    allRows.forEach(function(row) {
        row.style.display = 'none';
    });

    for (let i = startIndex; i < endIndex; i++) {
        matchingRows[i].style.display = '';
    }

    const emptyRow = document.getElementById('ordersEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (totalCount === 0 && allRows.length > 0) ? '' : 'none';
    }

    const pageInfo = document.getElementById('ordersPageInfo');
    if (pageInfo) {
        if (totalCount === 0) {
            pageInfo.textContent = 'Showing 0 orders';
        } else {
            pageInfo.textContent = `Showing ${startIndex + 1}–${endIndex} of ${totalCount} order${totalCount === 1 ? '' : 's'}`;
        }
    }

    const pageIndicator = document.getElementById('ordersPageIndicator');
    if (pageIndicator) {
        pageIndicator.textContent = `Page ${currentOrdersPage} of ${totalPages}`;
    }

    const prevBtn = document.getElementById('ordersPrevBtn');
    if (prevBtn) {
        prevBtn.disabled = currentOrdersPage <= 1;
        prevBtn.style.opacity = currentOrdersPage <= 1 ? '0.5' : '1';
        prevBtn.style.cursor = currentOrdersPage <= 1 ? 'default' : 'pointer';
    }

    const nextBtn = document.getElementById('ordersNextBtn');
    if (nextBtn) {
        nextBtn.disabled = currentOrdersPage >= totalPages;
        nextBtn.style.opacity = currentOrdersPage >= totalPages ? '0.5' : '1';
        nextBtn.style.cursor = currentOrdersPage >= totalPages ? 'default' : 'pointer';
    }

    const paginationContainer = document.getElementById('ordersPagination');
    if (paginationContainer) {
        paginationContainer.style.display = allRows.length === 0 ? 'none' : 'flex';
    }
};

window.changeOrdersPage = function(delta) {
    currentOrdersPage += delta;
    window.filterOrdersTable(false);
};

window.changeOrdersPageSize = function(newSize) {
    const parsed = parseInt(newSize, 10);
    if (!isNaN(parsed) && parsed > 0) {
        ordersPageSize = parsed;
        currentOrdersPage = 1;
        window.filterOrdersTable(false);
    }
};

window.resetOrdersFilter = function() {
    const qInput = document.getElementById('orderSearchInput');
    const statusSelect = document.getElementById('orderStatusSelect');
    if (qInput) qInput.value = '';
    if (statusSelect) statusSelect.value = '';
    currentOrdersPage = 1;
    window.filterOrdersTable(true);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.filterOrdersTable(true);
    });
} else {
    window.filterOrdersTable(true);
}
window.addEventListener('pageshow', function() {
    window.filterOrdersTable(false);
});
