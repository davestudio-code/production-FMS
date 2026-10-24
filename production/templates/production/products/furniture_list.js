function openEditModal(id, name, type, price) {
    const form = document.getElementById('editFurnitureForm');
    form.action = '/production/furniture/edit/' + id;
    document.getElementById('editFurnitureName').value = name;
    document.getElementById('editFurnitureType').value = type;
    document.getElementById('editSellingPrice').value = price;
    openModal('editFurnitureModal');
}

window.filterFurnitureTable = function() {
    const q = (document.getElementById('furnitureSearchInput')?.value || '').toLowerCase().trim();
    const cat = (document.getElementById('furnitureCategorySelect')?.value || '').trim();
    const resetBtn = document.getElementById('furnitureResetBtn');
    if (resetBtn) {
        resetBtn.style.display = (q || cat) ? 'inline-block' : 'none';
    }
    const rows = document.querySelectorAll('tr.furnitureRow');
    let visibleCount = 0;
    rows.forEach(function(row) {
        const rowCat = row.dataset.category || '';
        const rowSearch = row.dataset.search || '';
        const matchCat = !cat || rowCat === cat;
        const matchSearch = !q || rowSearch.includes(q);
        if (matchCat && matchSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    const emptyRow = document.getElementById('furnitureEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
};

window.resetFurnitureFilter = function() {
    const qInput = document.getElementById('furnitureSearchInput');
    const catSelect = document.getElementById('furnitureCategorySelect');
    if (qInput) qInput.value = '';
    if (catSelect) catSelect.value = '';
    window.filterFurnitureTable();
};
