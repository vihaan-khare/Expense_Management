/**
 * Expense Detail Page — the most complex screen
 * Shows: full expense info, step visualizer, discussion thread, 3-option action panel
 */
const ExpenseDetailPage = {
    expense: null,
    comments: [],
    pollTimer: null,

    async render(expenseId) {
        if (!expenseId) return '<div class="form-error">No expense ID</div>';

        try {
            const [expenseData, commentData] = await Promise.all([
                API.getExpense(expenseId),
                API.getComments(expenseId),
            ]);
            this.expense = expenseData.expense;
            this.comments = commentData.comments;
        } catch (err) {
            return `<div class="form-error">Failed to load expense: ${err.message}</div>`;
        }

        const e = this.expense;
        const company = App.currentCompany;
        const currency = company?.currency_code || 'USD';
        const user = App.currentUser;

        // Start polling for new comments
        this._startPolling(expenseId);

        const changeReasons = [
            'Receipt unclear/missing',
            'Amount justification needed',
            'Wrong category selected',
            'Policy violation',
            'Requires additional information',
            'Other',
        ];

        return `
        <div style="max-width: 900px; margin: 0 auto;">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
                <div>
                    <button class="btn btn-ghost btn-sm mb-2" onclick="window.history.back()">← Back</button>
                    <h1 class="page-title">${Utils.categoryIcon(e.category)} ${Utils.escapeHtml(e.category)} Expense</h1>
                </div>
                ${Components.statusBadge(e.status)}
            </div>

            <!-- Step Visualizer -->
            <div class="card mb-4">
                <h3 class="section-title mb-2">Approval Progress</h3>
                ${Components.stepVisualizer(
                    e.current_step, e.total_steps, e.chain_steps || [],
                    e.status, e.has_manager_prestep
                )}
                ${e.auto_approved ? `
                    <div class="card-accent mt-2">
                        <span class="text-sm">⚡ Auto-approved: ${Utils.escapeHtml(e.auto_approve_reason || '')}</span>
                    </div>` : ''}
            </div>

            <!-- Expense Details -->
            <div class="card mb-4">
                <h3 class="section-title mb-4">Expense Details</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                    <div>
                        <div class="text-xs text-muted">Amount</div>
                        <div class="font-semibold text-lg">${Utils.formatCurrency(e.converted_amount || e.amount, currency)}</div>
                        ${e.currency !== currency ? `<div class="text-xs text-muted">Original: ${Utils.formatCurrency(e.amount, e.currency)}</div>` : ''}
                    </div>
                    <div>
                        <div class="text-xs text-muted">Category</div>
                        <div class="font-medium">${Utils.categoryIcon(e.category)} ${Utils.escapeHtml(e.category)}</div>
                    </div>
                    <div>
                        <div class="text-xs text-muted">Date</div>
                        <div class="font-medium">${Utils.formatDate(e.expense_date)}</div>
                    </div>
                    <div>
                        <div class="text-xs text-muted">Submitted by</div>
                        <div class="font-medium">${Utils.escapeHtml(e.employee_name || '—')}</div>
                    </div>
                    <div style="grid-column: 1 / -1;">
                        <div class="text-xs text-muted">Description</div>
                        <div class="text-sm mt-1">${Utils.escapeHtml(e.description)}</div>
                    </div>
                    ${e.receipt_url ? `
                    <div style="grid-column: 1 / -1;">
                        <div class="text-xs text-muted">Receipt</div>
                        <a href="${e.receipt_url}" target="_blank" class="btn btn-secondary btn-sm mt-1">📎 View Receipt</a>
                    </div>` : ''}
                </div>
                ${e.ocr_autofilled ? '<div class="text-xs text-muted mt-3">ℹ️ Some fields were auto-filled by OCR</div>' : ''}
            </div>

            <!-- Action Panel (only if user can approve) -->
            ${e.can_approve ? `
            <div class="action-panel mb-4" id="action-panel">
                <h3 class="section-title mb-4">Take Action</h3>
                
                <div class="form-group mb-4">
                    <label class="form-label">Justification (min. 20 characters)</label>
                    <textarea id="action-justification" class="form-textarea" 
                              placeholder="Provide a meaningful explanation for your decision..." minlength="20"></textarea>
                </div>

                <div id="change-reasons-section" class="hidden mb-4">
                    <label class="form-label mb-2">Reasons for Change Request</label>
                    <div class="checkbox-group">
                        ${changeReasons.map(r => `
                            <label class="checkbox-label">
                                <input type="checkbox" class="change-reason-check" value="${Utils.escapeHtml(r)}">
                                ${Utils.escapeHtml(r)}
                            </label>
                        `).join('')}
                    </div>
                </div>

                ${e.revision_count >= e.max_revisions ? `
                    <div class="card-accent mb-3" style="background: var(--orange-light); border-color: var(--orange-border);">
                        <span class="text-sm" style="color: var(--orange);">
                            ⚠️ Maximum revisions (${e.max_revisions}) reached. You can only approve or reject.
                        </span>
                    </div>` : ''}

                <div id="action-error" class="form-error hidden mb-3"></div>

                <div class="action-buttons">
                    <button class="btn btn-approve" onclick="ExpenseDetailPage.takeAction('approved')">
                        ✅ Approve
                    </button>
                    ${e.revision_count < e.max_revisions ? `
                    <button class="btn btn-changes" onclick="ExpenseDetailPage.showChangeReasons()">
                        🔄 Request Changes
                    </button>` : ''}
                    <button class="btn btn-reject" onclick="ExpenseDetailPage.takeAction('rejected')">
                        ❌ Hard Reject
                    </button>
                </div>
            </div>` : ''}

            <!-- Resubmit Panel (for employee when changes requested) -->
            ${e.status === 'changes_requested' && e.employee_id === user.id ? `
            <div class="action-panel mb-4" style="border-color: var(--orange-border);">
                <h3 class="section-title mb-2">Changes Requested</h3>
                <p class="text-sm text-muted mb-4">Review the feedback below and resubmit your expense.</p>
                <div class="text-xs text-muted mb-2">Revisions: ${e.revision_count} / ${e.max_revisions}</div>
                <button class="btn btn-primary" onclick="ExpenseDetailPage.handleResubmit('${e.id}')">
                    📝 Resubmit for Review
                </button>
            </div>` : ''}

            <!-- Appeal Button (for employee when rejected) -->
            ${e.status === 'rejected' && e.employee_id === user.id ? `
            <div class="action-panel mb-4" style="border-color: var(--red-border);">
                <h3 class="section-title mb-2">Expense Rejected</h3>
                <p class="text-sm text-muted mb-4">You can appeal this decision once.</p>
                <div class="form-group mb-3">
                    <label class="form-label">Appeal Reason (min. 50 characters)</label>
                    <textarea id="appeal-reason" class="form-textarea" 
                              placeholder="Explain why you believe the rejection was incorrect..." minlength="50"></textarea>
                </div>
                <button class="btn btn-primary" onclick="ExpenseDetailPage.submitAppeal('${e.id}')">
                    ⚖️ Submit Appeal
                </button>
            </div>` : ''}

            <!-- Discussion Thread -->
            <div class="card">
                <h3 class="section-title mb-4">Discussion Thread</h3>
                <div class="thread-container" id="thread-container">
                    ${this.comments.length === 0 ? 
                        '<p class="text-sm text-muted text-center p-4">No comments yet.</p>' :
                        this.comments.map(c => Components.threadMessage(c)).join('')
                    }
                </div>

                <div class="divider"></div>

                ${Components.threadComposer(e.id)}
            </div>
        </div>`;
    },

    showChangeReasons() {
        document.getElementById('change-reasons-section').classList.toggle('hidden');
    },

    async takeAction(action) {
        const justification = document.getElementById('action-justification').value;
        const errorEl = document.getElementById('action-error');
        errorEl.classList.add('hidden');

        if (justification.length < 20) {
            errorEl.textContent = 'Justification must be at least 20 characters.';
            errorEl.classList.remove('hidden');
            return;
        }

        let changeReasons = [];
        if (action === 'changes_requested') {
            changeReasons = Array.from(document.querySelectorAll('.change-reason-check:checked'))
                .map(cb => cb.value);
            if (changeReasons.length === 0) {
                errorEl.textContent = 'Select at least one reason for the change request.';
                errorEl.classList.remove('hidden');
                return;
            }
            // Show reasons section
            document.getElementById('change-reasons-section').classList.remove('hidden');
        }

        // Confirm rejection
        if (action === 'rejected') {
            if (!confirm('Are you sure you want to permanently reject this expense? This cannot be undone (the employee may appeal).')) {
                return;
            }
        }

        try {
            await API.takeAction(this.expense.id, {
                action,
                justification,
                change_reasons: changeReasons,
            });

            const labels = { approved: 'approved', changes_requested: 'sent back for changes', rejected: 'rejected' };
            Utils.toast(`Expense ${labels[action]}!`, action === 'approved' ? 'success' : 'warning');
            App.navigate(window.location.hash);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    },

    async handleResubmit(expenseId) {
        try {
            await API.resubmitExpense(expenseId, {});
            Utils.toast('Expense resubmitted for review!', 'success');
            App.navigate(window.location.hash);
        } catch (err) {
            Utils.toast(err.message, 'error');
        }
    },

    async submitAppeal(expenseId) {
        const reason = document.getElementById('appeal-reason')?.value || '';
        if (reason.length < 50) {
            Utils.toast('Appeal reason must be at least 50 characters.', 'error');
            return;
        }

        try {
            await API.submitAppeal(expenseId, reason);
            Utils.toast('Appeal submitted! An admin will review it.', 'success');
            App.navigate(window.location.hash);
        } catch (err) {
            Utils.toast(err.message, 'error');
        }
    },

    async postComment(expenseId) {
        const input = document.getElementById('thread-input');
        const typeSelect = document.getElementById('thread-type');
        const content = input.value.trim();

        if (!content) return;

        try {
            const result = await API.addComment(expenseId, content, typeSelect.value);
            input.value = '';

            // Add to thread
            const container = document.getElementById('thread-container');
            const noComments = container.querySelector('p');
            if (noComments) noComments.remove();

            container.insertAdjacentHTML('beforeend', Components.threadMessage(result.comment));
            container.scrollTop = container.scrollHeight;
        } catch (err) {
            Utils.toast(err.message, 'error');
        }
    },

    _startPolling(expenseId) {
        this._stopPolling();
        this.pollTimer = setInterval(async () => {
            try {
                const { comments } = await API.getComments(expenseId);
                if (comments.length > this.comments.length) {
                    this.comments = comments;
                    const container = document.getElementById('thread-container');
                    if (container) {
                        container.innerHTML = comments.map(c => Components.threadMessage(c)).join('');
                        container.scrollTop = container.scrollHeight;
                    }
                }
            } catch { /* ignore polling errors */ }
        }, 10000);
    },

    _stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    },
};
