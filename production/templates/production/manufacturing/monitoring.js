var stagePreviewObjectUrl = null;

function toggleRollbackForm(elementId) {
    var el = document.getElementById(elementId);
    if (el) {
        el.style.display = (el.style.display === 'none' || el.style.display === '') ? 'flex' : 'none';
    }
}

window.syncStageProofRequirement = function() {
    var selectEl = document.getElementById('stageModalProgress');
    var photoInput = document.getElementById('stageModalPhoto');
    var photoLabel = document.getElementById('stagePhotoLabel');
    var reqBadge = document.getElementById('stagePhotoReqBadge');
    var submitBtn = document.getElementById('stageModalSubmitBtn');
    if (!selectEl || !photoInput) return;

    var isStage4 = (selectEl.value === '90');
    photoInput.required = isStage4;

    if (photoLabel) {
        photoLabel.textContent = isStage4 ? 'Stage 4 Photo Proof *' : 'Workshop Photo Proof';
    }
    if (reqBadge) {
        reqBadge.textContent = isStage4 ? 'Required for QA Sign-Off' : 'Optional on Stages 1–3';
        reqBadge.style.color = isStage4 ? 'var(--rd)' : 'var(--mt)';
    }
    if (submitBtn && submitBtn.textContent !== 'Optimizing photo...') {
        submitBtn.textContent = isStage4 ? 'Submit for QA' : 'Save Milestone';
    }
};

window.openStageUpdateModal = function(btn) {
    if (!btn) return;
    var monId = btn.getAttribute('data-monitoring-id') || '';
    var orderId = btn.getAttribute('data-order-id') || '';
    var productName = btn.getAttribute('data-product-name') || '';
    var defaultStage = btn.getAttribute('data-default-stage') || '25';

    var form = document.getElementById('stageUpdateForm');
    if (form) {
        form.action = '/production/monitoring/update/' + encodeURIComponent(monId);
        form.dataset.submitting = 'false';
    }
    var titleEl = document.getElementById('stageModalTitle');
    if (titleEl) {
        titleEl.textContent = 'Log Stage: Order #PO-' + orderId;
    }
    var subEl = document.getElementById('stageModalSubtitle');
    if (subEl) {
        subEl.textContent = productName;
    }
    var selectEl = document.getElementById('stageModalProgress');
    if (selectEl) {
        selectEl.value = defaultStage;
    }
    var photoInput = document.getElementById('stageModalPhoto');
    if (photoInput) {
        photoInput.value = '';
    }
    var noteInput = document.getElementById('stageModalNote');
    if (noteInput) {
        noteInput.value = '';
    }
    var previewWrap = document.getElementById('stagePhotoPreviewWrap');
    if (previewWrap) {
        previewWrap.style.display = 'none';
    }
    var submitBtn = document.getElementById('stageModalSubmitBtn');
    if (submitBtn) {
        submitBtn.disabled = false;
    }

    window.syncStageProofRequirement();
    if (typeof openModal === 'function') {
        openModal('stageUpdateModal');
    }
};

window.handleStagePhotoChange = function(input) {
    var previewWrap = document.getElementById('stagePhotoPreviewWrap');
    var previewImg = document.getElementById('stagePhotoPreviewImg');
    var previewMeta = document.getElementById('stagePhotoPreviewMeta');
    var submitBtn = document.getElementById('stageModalSubmitBtn');

    if (stagePreviewObjectUrl) {
        try { URL.revokeObjectURL(stagePreviewObjectUrl); } catch (e) {}
        stagePreviewObjectUrl = null;
    }

    if (!input || !input.files || !input.files[0]) {
        if (previewWrap) previewWrap.style.display = 'none';
        window.syncStageProofRequirement();
        return;
    }

    var file = input.files[0];
    var mime = (file.type || '').toLowerCase();
    if (mime !== 'image/jpeg' && mime !== 'image/jpg' && mime !== 'image/png' && mime !== 'image/webp') {
        input.value = '';
        if (previewWrap) previewWrap.style.display = 'none';
        if (typeof showToast === 'function') {
            showToast('Please select a JPG, PNG, or WebP photo.', 'warning');
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Optimizing photo...';
    }

    var rawUrl = URL.createObjectURL(file);
    var img = new Image();

    function finishPrep(finalFile, displayUrl) {
        if (previewImg && displayUrl) {
            previewImg.src = displayUrl;
        }
        if (previewMeta && finalFile) {
            var kb = Math.max(1, Math.round(finalFile.size / 1024));
            previewMeta.textContent = finalFile.name + ' · ' + kb + ' KB';
        }
        if (previewWrap) {
            previewWrap.style.display = 'flex';
        }
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = '';
        }
        window.syncStageProofRequirement();
    }

    img.onload = function() {
        try {
            var maxDim = 1100;
            var w = img.naturalWidth || img.width;
            var h = img.naturalHeight || img.height;
            if (w > maxDim || h > maxDim) {
                if (w >= h) {
                    h = Math.max(1, Math.round((h * maxDim) / w));
                    w = maxDim;
                } else {
                    w = Math.max(1, Math.round((w * maxDim) / h));
                    h = maxDim;
                }
            }
            var canvas = document.createElement('canvas');
            canvas.width = w;
            canvas.height = h;
            var ctx = canvas.getContext('2d');
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);

            canvas.toBlob(function(blob) {
                try { URL.revokeObjectURL(rawUrl); } catch (e) {}
                if (blob && typeof DataTransfer !== 'undefined') {
                    var baseName = (file.name || 'stage_proof').replace(/\.[^/.]+$/, '');
                    var compFile = new File([blob], baseName + '.jpg', {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    if (compFile.size < file.size || file.size > 900 * 1024) {
                        try {
                            var dt = new DataTransfer();
                            dt.items.add(compFile);
                            input.files = dt.files;
                            stagePreviewObjectUrl = URL.createObjectURL(compFile);
                            finishPrep(compFile, stagePreviewObjectUrl);
                            return;
                        } catch (dtErr) {}
                    }
                }
                stagePreviewObjectUrl = URL.createObjectURL(file);
                finishPrep(file, stagePreviewObjectUrl);
            }, 'image/jpeg', 0.80);
        } catch (err) {
            stagePreviewObjectUrl = rawUrl;
            finishPrep(file, stagePreviewObjectUrl);
        }
    };

    img.onerror = function() {
        try { URL.revokeObjectURL(rawUrl); } catch (e) {}
        stagePreviewObjectUrl = URL.createObjectURL(file);
        finishPrep(file, stagePreviewObjectUrl);
    };

    img.src = rawUrl;
};

window.setMonitoringTab = function(stateVal) {
    var nextVal = stateVal || '';
    var stateInput = document.getElementById('monitoringStateSelect');
    if (stateInput) {
        stateInput.value = nextVal;
    }
    var tabs = document.querySelectorAll('.workspaceFilterTabs .workspaceTabBtn[data-state]');
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
    var searchEl = document.getElementById('globalTabSearchInput');
    var q = (searchEl ? searchEl.value : '').toLowerCase().trim();
    var stateEl = document.getElementById('monitoringStateSelect');
    var state = (stateEl ? stateEl.value : '').trim();
    var rows = document.querySelectorAll('tr.monitoringRow');
    var visibleCount = 0;
    rows.forEach(function(row) {
        var rowState = row.dataset.state || '';
        var rowMine = row.dataset.mine || '0';
        var rowSearch = row.dataset.search || '';
        var matchState = true;
        if (state === 'mine') {
            matchState = (rowMine === '1');
        } else if (state) {
            matchState = (rowState === state);
        }
        var matchSearch = !q || rowSearch.includes(q);
        if (matchState && matchSearch) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    var emptyRow = document.getElementById('monitoringEmptyFilterRow');
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
