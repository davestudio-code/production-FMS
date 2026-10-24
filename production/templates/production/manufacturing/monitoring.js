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
