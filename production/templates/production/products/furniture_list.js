function openEditModal(id, name, type, price, bomCost, hasBOM) {
    const form = document.getElementById('editFurnitureForm');
    form.action = '/production/furniture/edit/' + id;
    document.getElementById('editFurnitureName').value = name;
    document.getElementById('editFurnitureType').value = type;
    document.getElementById('editSellingPrice').value = (price && price !== '0.00' && price !== '0') ? price : '';

    const bomBox = document.getElementById('editBomCostBox');
    const bomDisplay = document.getElementById('editBomCostDisplay');
    const markupSuggestion = document.getElementById('editMarkupSuggestion');
    const applyBtn = document.getElementById('applyMarkupBtn');

    const costNum = parseFloat(bomCost) || 0;
    if (bomBox) {
        bomBox.style.display = 'block';
        if (hasBOM && costNum > 0) {
            bomDisplay.innerHTML = '₱' + costNum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            const suggested = (costNum * 1.40).toFixed(2);
            if (applyBtn) {
                applyBtn.textContent = 'Apply ₱' + parseFloat(suggested).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                applyBtn.onclick = function() {
                    document.getElementById('editSellingPrice').value = suggested;
                };
            }
            if (markupSuggestion) markupSuggestion.style.display = 'flex';
        } else {
            bomDisplay.innerHTML = '<span class="statusBadge draft" style="font-size: 11px;">BOM Not Configured</span>';
            if (markupSuggestion) markupSuggestion.style.display = 'none';
        }
    }
    openModal('editFurnitureModal');
}

let currentFurniturePage = 1;
let furniturePageSize = 10;

window.filterFurnitureTable = function(resetPage = true) {
    if (resetPage) {
        currentFurniturePage = 1;
    }
    const q = (document.getElementById('globalTabSearchInput')?.value || '').toLowerCase().trim();
    const cat = (document.getElementById('furnitureCategorySelect')?.value || '').trim();
    const resetBtn = document.getElementById('furnitureResetBtn');
    if (resetBtn) {
        resetBtn.style.display = cat ? 'inline-block' : 'none';
    }
    const allRows = Array.from(document.querySelectorAll('tr.furnitureRow'));
    const matchingRows = allRows.filter(function(row) {
        const rowCat = row.dataset.category || '';
        const rowSearch = row.dataset.search || '';
        const matchCat = !cat || rowCat === cat;
        const matchSearch = !q || rowSearch.includes(q);
        return matchCat && matchSearch;
    });

    const totalCount = matchingRows.length;
    const totalPages = Math.ceil(totalCount / furniturePageSize) || 1;
    if (currentFurniturePage > totalPages) currentFurniturePage = totalPages;
    if (currentFurniturePage < 1) currentFurniturePage = 1;

    const startIndex = (currentFurniturePage - 1) * furniturePageSize;
    const endIndex = Math.min(startIndex + furniturePageSize, totalCount);

    allRows.forEach(function(row) {
        row.style.display = 'none';
    });

    for (let i = startIndex; i < endIndex; i++) {
        matchingRows[i].style.display = '';
    }

    const emptyRow = document.getElementById('furnitureEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (totalCount === 0 && allRows.length > 0) ? '' : 'none';
    }

    const pageInfo = document.getElementById('furniturePageInfo');
    if (pageInfo) {
        if (totalCount === 0) {
            pageInfo.textContent = 'Showing 0 products';
        } else {
            pageInfo.textContent = `Showing ${startIndex + 1}–${endIndex} of ${totalCount} product${totalCount === 1 ? '' : 's'}`;
        }
    }

    const pageIndicator = document.getElementById('furniturePageIndicator');
    if (pageIndicator) {
        pageIndicator.textContent = `Page ${currentFurniturePage} of ${totalPages}`;
    }

    const prevBtn = document.getElementById('furniturePrevBtn');
    if (prevBtn) {
        prevBtn.disabled = currentFurniturePage <= 1;
        prevBtn.style.opacity = currentFurniturePage <= 1 ? '0.5' : '1';
        prevBtn.style.cursor = currentFurniturePage <= 1 ? 'default' : 'pointer';
    }

    const nextBtn = document.getElementById('furnitureNextBtn');
    if (nextBtn) {
        nextBtn.disabled = currentFurniturePage >= totalPages;
        nextBtn.style.opacity = currentFurniturePage >= totalPages ? '0.5' : '1';
        nextBtn.style.cursor = currentFurniturePage >= totalPages ? 'default' : 'pointer';
    }

    const paginationContainer = document.getElementById('furniturePagination');
    if (paginationContainer) {
        paginationContainer.style.display = allRows.length === 0 ? 'none' : 'flex';
    }
};

window.changeFurniturePage = function(delta) {
    currentFurniturePage += delta;
    window.filterFurnitureTable(false);
};

window.changeFurniturePageSize = function(newSize) {
    const parsed = parseInt(newSize, 10);
    if (!isNaN(parsed) && parsed > 0) {
        furniturePageSize = parsed;
        currentFurniturePage = 1;
        window.filterFurnitureTable(false);
    }
};

window.resetFurnitureFilter = function() {
    const qInput = document.getElementById('globalTabSearchInput');
    const catSelect = document.getElementById('furnitureCategorySelect');
    if (qInput) qInput.value = '';
    if (typeof window.updateGlobalSearchClearBtn === 'function') {
        window.updateGlobalSearchClearBtn();
    }
    if (catSelect) catSelect.value = '';
    currentFurniturePage = 1;
    window.filterFurnitureTable(true);
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.filterFurnitureTable(true);
    });
} else {
    window.filterFurnitureTable(true);
}
window.addEventListener('pageshow', function() {
    window.filterFurnitureTable(false);
});
