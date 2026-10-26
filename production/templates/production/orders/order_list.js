window.openRestockModal = function(furnitureId) {
    const furnSelect = document.getElementById('modalFurnitureSelect');
    if (furnSelect) {
        furnSelect.value = String(furnitureId);
    }
    const restockRadio = document.getElementById('purposeRestock');
    if (restockRadio) {
        restockRadio.checked = true;
    }
    const qtyInput = document.getElementById('modalQuantityInput');
    if (qtyInput && !qtyInput.value) {
        qtyInput.value = '5';
    }
    window.updateLiveMrpCheck();
    openModal('createOrderModal');
};

window.updateLiveMrpCheck = function() {
    const furnSelect = document.getElementById('modalFurnitureSelect');
    const qtyInput = document.getElementById('modalQuantityInput');
    const previewBox = document.getElementById('mrpPreviewBox');
    const badge = document.getElementById('mrpStatusBadge');
    const list = document.getElementById('mrpComponentList');
    const submitBtn = document.getElementById('modalCreateOrderBtn');

    if (!furnSelect || !qtyInput || !previewBox || !badge || !list) return;

    const furnId = furnSelect.value;
    const qty = parseInt(qtyInput.value, 10);

    if (!furnId) {
        previewBox.style.display = 'none';
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
            submitBtn.title = '';
        }
        return;
    }

    const bomMap = window.furnitureBomMap || {};
    const items = bomMap[furnId] || [];

    if (items.length === 0) {
        previewBox.style.display = 'block';
        badge.className = 'statusBadge alert';
        badge.textContent = 'No Recipe Defined';
        list.innerHTML = '<span style="color: #9a4a3a; font-weight: 600;">Product has no configured BOM. Please configure recipe before ordering.</span>';
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.5';
            submitBtn.style.cursor = 'not-allowed';
            submitBtn.title = 'Cannot create order: Selected product has no configured BOM';
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
        submitBtn.title = '';
    }

    if (isNaN(qty) || qty <= 0) {
        previewBox.style.display = 'none';
        return;
    }

    let hasShortage = false;
    let html = '';

    items.forEach(function(item) {
        const required = (item.quantityRequired * qty);
        const onHand = item.currentStock;
        const deficit = Math.max(0, required - onHand);
        const isDeficit = deficit > 0.0001;
        if (isDeficit) hasShortage = true;

        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 3px 0; border-bottom: 1px dashed var(--bd);">
                <span><b>${item.materialName}</b> &middot; ${required.toFixed(2)} ${item.unit}</span>
                <span style="color: ${isDeficit ? '#9a4a3a' : '#357a58'}; font-weight: 600;">
                    ${isDeficit ? `Shortage: -${deficit.toFixed(2)} ${item.unit}` : `In Stock (${onHand.toFixed(1)} ${item.unit})`}
                </span>
            </div>
        `;
    });

    list.innerHTML = html;
    previewBox.style.display = 'block';

    if (hasShortage) {
        badge.className = 'statusBadge alert';
        badge.textContent = 'Material Shortage';
    } else {
        badge.className = 'statusBadge completed';
        badge.textContent = 'Stock Sufficient';
    }
};

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
