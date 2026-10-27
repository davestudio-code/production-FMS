var planningTimelineOffsetDays = 0;

function escPlanningHtml(val) {
    return String(val || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function parseLocalIsoDate(isoStr) {
    if (!isoStr) return null;
    const parts = isoStr.split('-');
    if (parts.length !== 3) return null;
    const y = parseInt(parts[0], 10);
    const m = parseInt(parts[1], 10) - 1;
    const d = parseInt(parts[2], 10);
    if (isNaN(y) || isNaN(m) || isNaN(d)) return null;
    return new Date(y, m, d);
}

function addLocalDays(baseDate, days) {
    return new Date(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate() + days);
}

function diffLocalDays(a, b) {
    const utcA = Date.UTC(a.getFullYear(), a.getMonth(), a.getDate());
    const utcB = Date.UTC(b.getFullYear(), b.getMonth(), b.getDate());
    return Math.round((utcA - utcB) / 86400000);
}

function formatShortMonthDay(d) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    return months[d.getMonth()] + ' ' + d.getDate();
}

function openScheduleModal(orderID, productName, startDate, dueDate, assignedTo) {
    const formEl = document.getElementById('scheduleForm');
    if (formEl) {
        formEl.action = "/production/planning/update/" + orderID;
        formEl.dataset.submitting = 'false';
        const submitBtn = formEl.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerText = 'Save Plan & Assignment';
        }
    }
    document.getElementById('scheduleModalTitle').textContent = "Plan & Assign: Order #PO-" + orderID;
    document.getElementById('scheduleOrderProduct').textContent = productName;
    document.getElementById('scheduleStartDate').value = startDate || '';
    document.getElementById('scheduleDueDate').value = dueDate || '';
    const staffSelect = document.getElementById('scheduleAssignedTo');
    if (staffSelect) {
        staffSelect.value = assignedTo || '';
    }
    const viewInput = document.getElementById('planningViewSelect');
    const nextUrlInput = document.getElementById('scheduleNextUrlInput');
    if (nextUrlInput) {
        nextUrlInput.value = (viewInput && viewInput.value === 'timeline') ? '/production/planning?view=timeline' : '/production/planning';
    }
    openModal('scheduleModal');
}

window.openScheduleFromDataset = function(btn) {
    if (!btn) return;
    openScheduleModal(
        btn.getAttribute('data-oid') || '',
        btn.getAttribute('data-prod') || '',
        btn.getAttribute('data-start') || '',
        btn.getAttribute('data-due') || '',
        btn.getAttribute('data-staff') || ''
    );
};

window.setPlanningView = function(viewMode) {
    const mode = viewMode === 'timeline' ? 'timeline' : 'list';
    const viewInput = document.getElementById('planningViewSelect');
    const listSec = document.getElementById('planningListSection');
    const timeSec = document.getElementById('planningTimelineSection');
    if (viewInput) viewInput.value = mode;

    const viewBtns = document.querySelectorAll('.viewModeBtn[data-planview]');
    viewBtns.forEach(function(btn) {
        if ((btn.getAttribute('data-planview') || '') === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    if (window.history && window.history.replaceState) {
        const nextUrl = mode === 'timeline' ? '/production/planning?view=timeline' : '/production/planning';
        window.history.replaceState({ targetUrl: nextUrl }, '', nextUrl);
    }

    if (mode === 'timeline') {
        if (listSec) listSec.style.display = 'none';
        if (timeSec) timeSec.style.display = 'block';
        window.renderPlanningTimeline();
    } else {
        if (listSec) listSec.style.display = 'block';
        if (timeSec) timeSec.style.display = 'none';
    }
};

window.shiftPlanningTimeline = function(deltaDays) {
    if (deltaDays === 0) {
        planningTimelineOffsetDays = 0;
    } else {
        planningTimelineOffsetDays += deltaDays;
    }
    window.renderPlanningTimeline();
};

window.renderPlanningTimeline = function() {
    const gridContainer = document.getElementById('ganttGridContainer');
    const rangeLabel = document.getElementById('ganttRangeLabel');
    const todayLoadPill = document.getElementById('ganttTodayLoadPill');
    if (!gridContainer) return;

    const canEdit = (document.getElementById('planningCanEdit')?.value === '1');
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const windowDays = 14;
    const windowStart = addLocalDays(today, -3 + planningTimelineOffsetDays);
    const windowEnd = addLocalDays(windowStart, windowDays - 1);

    if (rangeLabel) {
        rangeLabel.textContent = formatShortMonthDay(windowStart) + ' – ' + formatShortMonthDay(windowEnd) + ', ' + windowEnd.getFullYear();
    }

    const allRows = Array.from(document.querySelectorAll('tr.planningRow'));
    const matchingRows = allRows.filter(function(r) {
        return r.dataset.filteredOut !== '1';
    });

    const items = [];
    let toProduceCount = 0;
    let toProduceUnits = 0;

    matchingRows.forEach(function(row) {
        const item = {
            orderId: row.dataset.orderId || '',
            product: row.dataset.product || '',
            qty: parseInt(row.dataset.qty || '0', 10) || 0,
            status: row.dataset.status || 'Draft',
            health: row.dataset.health || '',
            assignedId: row.dataset.assignedId || '',
            assignedName: row.dataset.assignedName || '',
            startIso: row.dataset.start || '',
            dueIso: row.dataset.due || '',
            dateLabel: row.dataset.dateLabel || ''
        };
        const sDate = parseLocalIsoDate(item.startIso);
        const dDate = parseLocalIsoDate(item.dueIso);
        if (!sDate && !dDate) {
            item.hasDates = false;
        } else {
            item.hasDates = true;
            item.effStart = sDate || dDate;
            item.effEnd = dDate || sDate;
            if (item.effEnd < item.effStart) {
                item.effEnd = item.effStart;
            }
            if (item.status !== 'Completed' && item.effStart <= today && item.effEnd >= today) {
                toProduceCount++;
                toProduceUnits += item.qty;
            }
        }
        items.push(item);
    });

    if (todayLoadPill) {
        if (toProduceCount === 0) {
            todayLoadPill.className = 'workspaceMetaPill';
            todayLoadPill.innerHTML = 'To Produce Today: <b>0 orders</b>';
        } else {
            todayLoadPill.className = 'workspaceMetaPill success';
            todayLoadPill.innerHTML = '<span class="tabStatusDot completed"></span><span>To Produce Today: <b>' +
                toProduceCount + ' ' + (toProduceCount === 1 ? 'order' : 'orders') + ' &middot; ' +
                toProduceUnits + ' ' + (toProduceUnits === 1 ? 'unit' : 'units') + '</b></span>';
        }
    }

    const dowNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const days = [];
    for (let i = 0; i < windowDays; i++) {
        const d = addLocalDays(windowStart, i);
        const dow = d.getDay();
        days.push({
            date: d,
            dowLabel: dowNames[dow],
            dayNum: d.getDate(),
            isWeekend: (dow === 0 || dow === 6),
            isToday: diffLocalDays(d, today) === 0
        });
    }

    let html = '<div class="ganttGrid">';
    html += '<div class="ganttCornerHead">Production Order</div>';
    days.forEach(function(day) {
        const cls = 'ganttDayHead' + (day.isWeekend ? ' isWeekend' : '') + (day.isToday ? ' isToday' : '');
        html += '<div class="' + cls + '">' +
            '<span class="ganttDayDow">' + day.dowLabel + '</span>' +
            '<span class="ganttDayNum">' + day.dayNum + '</span>' +
            '</div>';
    });

    if (items.length === 0) {
        html += '<div style="grid-column: 1 / -1; padding: 34px 20px; text-align: center; color: var(--mt); font-size: 13.5px;">' +
            (allRows.length === 0 ? 'No production orders created yet.' : 'No planned orders match your current search or filter.') +
            '</div>';
    } else {
        items.forEach(function(item) {
            const unitWord = item.qty === 1 ? 'unit' : 'units';
            const dotCls = item.health === 'Overdue' ? 'overdue' : (item.status === 'Completed' ? 'completed' : (item.status === 'In Progress' ? 'inProgress' : (item.status === 'Released' ? 'released' : 'draft')));
            const staffLineHtml = item.assignedName
                ? '<div style="font-size: 11px; color: var(--p); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Staff: ' + escPlanningHtml(item.assignedName) + '</div>'
                : '<div style="font-size: 11px; color: #8e622a; font-weight: 600;">Staff: Unassigned</div>';

            html += '<div class="ganttOrderCell">' +
                '<div style="display: flex; align-items: center; justify-content: space-between; gap: 6px;">' +
                '<a href="/production/orders/' + escPlanningHtml(item.orderId) + '" style="color: var(--p); font-weight: 700; font-size: 13px; text-decoration: none;">#PO-' + escPlanningHtml(item.orderId) + '</a>' +
                '<span style="display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--mt); font-weight: 600;"><span class="tabStatusDot ' + dotCls + '"></span>' + escPlanningHtml(item.status) + '</span>' +
                '</div>' +
                '<div style="font-size: 12px; color: var(--tx); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"><b>' + escPlanningHtml(item.product) + '</b> &middot; ' + item.qty + ' ' + unitWord + '</div>' +
                staffLineHtml +
                '</div>';

            html += '<div class="ganttTrackRow">';
            days.forEach(function(day) {
                const bgCls = 'ganttBgCell' + (day.isWeekend ? ' isWeekend' : '') + (day.isToday ? ' isToday' : '');
                html += '<div class="' + bgCls + '"></div>';
            });

            html += '<div class="ganttBarLayer">';
            if (!item.hasDates) {
                const gapHint = item.assignedName ? 'Needs timeline dates' : 'Needs timeline & staff';
                html += '<div class="ganttUnscheduledInline">' +
                    '<span style="font-size: 12px; color: var(--mt);">' + gapHint + '</span>';
                if (canEdit && item.status !== 'Completed') {
                    html += '<button type="button" class="actionButton secondary" style="padding: 3px 10px; font-size: 11.5px;" ' +
                        'data-oid="' + escPlanningHtml(item.orderId) + '" data-prod="' + escPlanningHtml(item.product) + '" data-start="" data-due="" data-staff="' + escPlanningHtml(item.assignedId) + '" ' +
                        'onclick="openScheduleFromDataset(this)">+ Plan &amp; Assign</button>';
                }
                html += '</div>';
            } else {
                const startOffset = diffLocalDays(item.effStart, windowStart);
                const endOffset = diffLocalDays(item.effEnd, windowStart);
                const overlapsWindow = (endOffset >= 0 && startOffset < windowDays);

                if (overlapsWindow) {
                    const clampedStart = Math.max(0, startOffset) + 1;
                    const clampedEnd = Math.min(windowDays - 1, endOffset) + 2;
                    const clippedLeft = startOffset < 0;
                    const clippedRight = endOffset >= windowDays;

                    let barCls = 'barDraft';
                    if (item.health === 'Overdue') barCls = 'barOverdue';
                    else if (item.status === 'Completed') barCls = 'barCompleted';
                    else if (item.status === 'In Progress') barCls = 'barInProgress';
                    else if (item.status === 'Released') barCls = 'barReleased';

                    const staffShort = item.assignedName ? (' · ' + item.assignedName.split(' ')[0]) : ' · Unassigned';
                    const labelLeft = (clippedLeft ? '← ' : '') + item.product + ' (' + item.qty + ' ' + unitWord + ')' + staffShort;
                    const labelRight = (item.health === 'Overdue' ? '! Overdue' : ('Due ' + formatShortMonthDay(item.effEnd))) + (clippedRight ? ' →' : '');

                    html += '<button type="button" class="ganttBar ' + barCls + '" style="grid-column: ' + clampedStart + ' / ' + clampedEnd + ';" ' +
                        'title="#PO-' + escPlanningHtml(item.orderId) + ' • ' + escPlanningHtml(item.product) + ' (' + escPlanningHtml(item.dateLabel) + ') • Staff: ' + escPlanningHtml(item.assignedName || 'Unassigned') + '" ' +
                        'data-oid="' + escPlanningHtml(item.orderId) + '" data-prod="' + escPlanningHtml(item.product) + '" ' +
                        'data-start="' + escPlanningHtml(item.startIso) + '" data-due="' + escPlanningHtml(item.dueIso) + '" data-staff="' + escPlanningHtml(item.assignedId) + '" ' +
                        ((canEdit && item.status !== 'Completed') ? 'onclick="openScheduleFromDataset(this)"' : '') + '>' +
                        '<span style="overflow: hidden; text-overflow: ellipsis;">' + escPlanningHtml(labelLeft) + '</span>' +
                        '<span style="font-size: 10.5px; opacity: 0.88; flex-shrink: 0;">' + escPlanningHtml(labelRight) + '</span>' +
                        '</button>';
                } else {
                    const dirHint = endOffset < 0 ? ('← Scheduled ' + formatShortMonthDay(item.effStart)) : ('Scheduled ' + formatShortMonthDay(item.effStart) + ' →');
                    const targetShift = diffLocalDays(item.effStart, today);
                    html += '<div class="ganttUnscheduledInline">' +
                        '<span style="font-size: 12px; color: var(--mt);">' + escPlanningHtml(dirHint) + '</span>' +
                        '<button type="button" class="actionButton secondary" style="padding: 3px 10px; font-size: 11.5px;" onclick="planningTimelineOffsetDays = ' + targetShift + '; renderPlanningTimeline();">' +
                        'View Week' +
                        '</button></div>';
                }
            }
            html += '</div></div>';
        });
    }

    html += '</div>';
    gridContainer.innerHTML = html;
};

window.syncPlanningHealthTabs = function(healthVal) {
    const tabs = document.querySelectorAll('.workspaceFilterTabs .workspaceTabBtn[data-health]');
    tabs.forEach(function(tab) {
        if ((tab.getAttribute('data-health') || '') === healthVal) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });
};

window.setPlanningHealthTab = function(healthVal) {
    const nextVal = healthVal || '';
    const healthInput = document.getElementById('planningHealthSelect');
    if (healthInput) {
        healthInput.value = nextVal;
    }
    window.syncPlanningHealthTabs(nextVal);
    window.filterPlanningTable();
};

window.filterPlanningTable = function() {
    const q = (document.getElementById('globalTabSearchInput')?.value || '').toLowerCase().trim();
    const status = (document.getElementById('planningStatusSelect')?.value || '').trim();
    const health = (document.getElementById('planningHealthSelect')?.value || '').trim();
    const rows = document.querySelectorAll('tr.planningRow');
    let visibleCount = 0;
    rows.forEach(function(row) {
        const rowStatus = row.dataset.status || '';
        const rowHealth = row.dataset.health || '';
        const rowSearch = row.dataset.search || '';
        const matchStatus = !status || rowStatus === status;
        const matchHealth = !health || rowHealth === health;
        const matchSearch = !q || rowSearch.includes(q);
        if (matchStatus && matchHealth && matchSearch) {
            row.style.display = '';
            row.dataset.filteredOut = '0';
            visibleCount++;
        } else {
            row.style.display = 'none';
            row.dataset.filteredOut = '1';
        }
    });
    const emptyRow = document.getElementById('planningEmptyRow');
    if (emptyRow) {
        emptyRow.style.display = (visibleCount === 0 && rows.length > 0) ? '' : 'none';
    }
    if (document.getElementById('planningViewSelect')?.value === 'timeline') {
        window.renderPlanningTimeline();
    }
};

window.resetPlanningFilter = function() {
    const qInput = document.getElementById('globalTabSearchInput');
    const statusSelect = document.getElementById('planningStatusSelect');
    const healthInput = document.getElementById('planningHealthSelect');
    if (qInput) qInput.value = '';
    if (typeof window.updateGlobalSearchClearBtn === 'function') {
        window.updateGlobalSearchClearBtn();
    }
    if (statusSelect) statusSelect.value = '';
    if (healthInput) healthInput.value = '';
    window.syncPlanningHealthTabs('');
    window.filterPlanningTable();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.filterPlanningTable();
    });
} else {
    window.filterPlanningTable();
}
