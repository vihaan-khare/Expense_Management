/**
 * Approver Queue Page — expenses waiting for current user's approval
 */
const ApproverQueuePage = {
    async render() {
        const company = App.currentCompany;
        const currency = company?.currency_code || 'USD';
        let queue = [];

        try {
            const data = await API.getApprovalQueue();
            queue = data.queue;
        } catch (err) {
            return `<div class="form-error">Failed to load queue: ${err.message}</div>`;
        }

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <h1 class="page-title">Approval Queue</h1>
                <span class="badge badge-in_review">
                    <span class="dot"></span>
                    ${queue.length} pending
                </span>
            </div>

            ${queue.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-icon">✅</div>
                    <div class="empty-state-title">All caught up!</div>
                    <div class="empty-state-text">No expenses waiting for your approval.</div>
                </div>
            ` : `
                ${Components.dataTable([
                    { label: 'Name', render: r => `
                        <div class="flex items-center gap-3">
                            <div class="user-avatar" style="width: 32px; height: 32px; font-size: 14px;">${Utils.initials(r.employee_name)}</div>
                            <div class="font-medium text-gray-900">${Utils.escapeHtml(r.employee_name || 'Unknown')}</div>
                        </div>
                    `},
                    { label: 'Items', render: r => `
                        <div>
                            <div class="font-medium text-gray-900 truncate" style="max-width: 250px;" title="${Utils.escapeHtml(r.description)}">
                                ${Utils.escapeHtml(r.description)}
                            </div>
                            <div class="text-xs text-muted mt-1">${Utils.formatDate(r.expense_date)}</div>
                        </div>
                    `},
                    { label: 'Category', render: r => `
                        <div class="inline-flex items-center gap-2">
                            <span>${Utils.categoryIcon(r.category)}</span>
                            <span class="text-sm font-medium text-gray-700">${Utils.escapeHtml(r.category)}</span>
                        </div>
                    `},
                    { label: 'Total Amount', render: r => `
                        <span class="font-bold text-gray-900">${Utils.formatCurrency(r.converted_amount || r.amount, currency)}</span>
                        ${r.currency !== currency ? `<div class="text-xs text-muted block mt-1">(${Utils.formatCurrency(r.amount, r.currency)})</div>` : ''}
                    `},
                    { label: 'Actions', render: r => `
                        <div class="flex gap-2">
                            <button class="btn btn-ghost btn-sm text-green-700 bg-green-50 hover:bg-green-100" onclick="ApproverQueuePage.quickAction('${r.id}', 'approved')" title="Quick Approve">✅ Approve</button>
                            <button class="btn btn-ghost btn-sm text-red-700 bg-red-50 hover:bg-red-100" onclick="ApproverQueuePage.quickAction('${r.id}', 'rejected')" title="Quick Reject">❌ Reject</button>
                            <a href="#/expense/${r.id}" class="btn btn-secondary btn-sm" title="Review full details">🔍 Review</a>
                        </div>
                    `}
                ], queue, {
                    emptyMessage: 'No expenses yet in your queue.'
                })}
            `}
            <div id="quick-action-modal-container"></div>
        </div>`;
    },

    quickAction(id, action) {
        let title, btnText, btnClass, justificationPlaceholder;

        if (action === 'approved') {
            title = 'Quick Approve';
            btnText = 'Approve';
            btnClass = 'btn-primary';
            justificationPlaceholder = 'Looks correct, approved following policy.';
        } else {
            title = 'Quick Reject';
            btnText = 'Reject';
            btnClass = 'btn-danger';
            justificationPlaceholder = 'Does not align with company travel policy.';
        }

        const body = `
            <div class="form-group">
                <label class="form-label">Justification</label>
                <textarea id="qa-justification" class="form-input" rows="3" placeholder="${justificationPlaceholder}" required minlength="20"></textarea>
                <span class="form-hint">At least 20 characters required.</span>
            </div>
            <div id="qa-error" class="form-error hidden"></div>
        `;

        const footer = `
            <button class="btn btn-secondary" onclick="Components.closeModal('qa-modal')">Cancel</button>
            <button class="btn ${btnClass}" onclick="ApproverQueuePage.submitAction('${id}', '${action}')">${btnText}</button>
        `;

        document.getElementById('quick-action-modal-container').innerHTML = 
            Components.modal('qa-modal', title, body, footer);
    },

    async submitAction(id, action) {
        const just = document.getElementById('qa-justification').value;
        const errEl = document.getElementById('qa-error');
        errEl.classList.add('hidden');

        if (just.length < 20) {
            errEl.textContent = 'Please provide at least 20 characters for your justification.';
            errEl.classList.remove('hidden');
            return;
        }

        try {
            await API.takeAction(id, { action, justification: just });
            Components.closeModal('qa-modal');
            Utils.toast(\`Expense \${action === 'approved' ? 'approved' : 'rejected'} successfully.\`, 'success');
            App.navigate(window.location.hash);
        } catch(err) {
            errEl.textContent = err.message;
            errEl.classList.remove('hidden');
        }
    }
};
