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

var currentOrdersPage = 1;
var ordersPageSize = 10;

window.filterOrdersTable = function(resetPage = true) {
    if (resetPage) {
        currentOrdersPage = 1;
    }
    const qInput = document.getElementById('globalTabSearchInput');
    const q = (qInput?.value || '').toLowerCase().trim();
    const status = (document.getElementById('orderStatusSelect')?.value || '').trim();
    const ordersSection = document.getElementById('ordersWorkspaceSection');
    const stockoutsSection = document.getElementById('stockoutsWorkspaceSection');

    if (status === '__stockouts__') {
        if (ordersSection) ordersSection.style.display = 'none';
        if (stockoutsSection) stockoutsSection.style.display = 'block';
        if (qInput) qInput.placeholder = 'Search out-of-stock products...';
        const stockoutRows = Array.from(document.querySelectorAll('tr.stockoutRow'));
        let visibleStockouts = 0;
        stockoutRows.forEach(function(row) {
            const rowSearch = row.dataset.search || '';
            const match = !q || rowSearch.includes(q);
            row.style.display = match ? '' : 'none';
            if (match) visibleStockouts++;
        });
        const emptyStockoutSearch = document.getElementById('stockoutsEmptySearchRow');
        if (emptyStockoutSearch) {
            emptyStockoutSearch.style.display = (visibleStockouts === 0 && stockoutRows.length > 0) ? '' : 'none';
        }
        return;
    }

    if (ordersSection) ordersSection.style.display = 'block';
    if (stockoutsSection) stockoutsSection.style.display = 'none';
    if (qInput) qInput.placeholder = 'Search production orders, #PO, or products...';

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

window.syncOrderStatusTabs = function(statusValue) {
    const tabs = document.querySelectorAll('.workspaceFilterTabs .workspaceTabBtn');
    tabs.forEach(function(tab) {
        const tabStatus = tab.getAttribute('data-status') || '';
        if (tabStatus === statusValue) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
};

window.setOrderStatusTab = function(statusValue) {
    const nextVal = statusValue || '';
    const statusInput = document.getElementById('orderStatusSelect');
    if (statusInput) {
        statusInput.value = nextVal;
    }
    if (window.history && window.history.replaceState) {
        const targetUrl = nextVal === '__stockouts__' ? '/production/orders?stockouts=1' : '/production/orders';
        window.history.replaceState({ targetUrl: targetUrl }, '', targetUrl);
    }
    window.syncOrderStatusTabs(nextVal);
    window.filterOrdersTable(true);
};

window.resetOrdersFilter = function() {
    const qInput = document.getElementById('globalTabSearchInput');
    const statusSelect = document.getElementById('orderStatusSelect');
    if (qInput) qInput.value = '';
    if (typeof window.updateGlobalSearchClearBtn === 'function') {
        window.updateGlobalSearchClearBtn();
    }
    if (statusSelect && statusSelect.value !== '__stockouts__') {
        statusSelect.value = '';
        window.syncOrderStatusTabs('');
    }
    currentOrdersPage = 1;
    window.filterOrdersTable(true);
};

function initOrdersWorkspace() {
    const params = new URLSearchParams(window.location.search);
    const statusSelect = document.getElementById('orderStatusSelect');
    if (params.get('stockouts') === '1' && statusSelect) {
        statusSelect.value = '__stockouts__';
    }
    if (statusSelect) {
        window.syncOrderStatusTabs(statusSelect.value || '');
    }
    window.filterOrdersTable(true);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOrdersWorkspace);
} else {
    initOrdersWorkspace();
}
window.addEventListener('pageshow', function() {
    window.filterOrdersTable(false);
});
