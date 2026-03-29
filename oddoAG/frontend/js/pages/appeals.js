/**
 * Appeals Queue Page (Admin only)
 */
const AppealsPage = {
    async render() {
        let appeals = [];
        try {
            const data = await API.getAppeals();
            appeals = data.appeals;
        } catch (err) {
            return `<div class="form-error">Failed to load appeals: ${err.message}</div>`;
        }

        const company = App.currentCompany;
        const currency = company?.currency_code || 'USD';

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <h1 class="page-title">Appeals Queue</h1>
                <span class="badge badge-appealed"><span class="dot"></span>${appeals.length} pending</span>
            </div>

            ${appeals.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-icon">⚖️</div>
                    <div class="empty-state-title">No pending appeals</div>
                    <div class="empty-state-text">All appeals have been reviewed.</div>
                </div>
            ` : `
                <div class="flex flex-col gap-4">
                    ${appeals.map(appeal => `
                        <div class="card">
                            <div class="flex items-center justify-between mb-3">
                                <div class="flex items-center gap-3">
                                    <div class="user-avatar">${Utils.initials(appeal.submitter_name || '')}</div>
                                    <div>
                                        <div class="font-medium">${Utils.escapeHtml(appeal.submitter_name || 'Unknown')}</div>
                                        <div class="text-xs text-muted">Submitted ${Utils.timeAgo(appeal.created_at)}</div>
                                    </div>
                                </div>
                                ${appeal.expense ? `
                                    <div class="font-semibold">${Utils.formatCurrency(appeal.expense.converted_amount || appeal.expense.amount, currency)}</div>
                                ` : ''}
                            </div>

                            ${appeal.expense ? `
                                <div class="text-sm mb-2">
                                    <span class="text-muted">Category:</span> ${Utils.categoryIcon(appeal.expense.category)} ${Utils.escapeHtml(appeal.expense.category)}
                                    <span class="text-muted ml-3">Date:</span> ${Utils.formatDate(appeal.expense.expense_date)}
                                </div>
                            ` : ''}

                            <div class="card-flat mb-3" style="padding: 12px;">
                                <div class="text-xs text-muted mb-1">Appeal Reason:</div>
                                <div class="text-sm">${Utils.escapeHtml(appeal.reason)}</div>
                            </div>

                            <div class="flex gap-3" style="flex-wrap:wrap;">
                                <button class="btn btn-secondary btn-sm" onclick="App.navigateToExpense('${appeal.expense_id}')">
                                    👁️ View Full Expense
                                </button>
                                <button class="btn btn-approve btn-sm" onclick="AppealsPage.showReviewModal('${appeal.id}', 'approved')">
                                    ✅ Override & Approve
                                </button>
                                <button class="btn btn-reject btn-sm" onclick="AppealsPage.showReviewModal('${appeal.id}', 'rejected')">
                                    ❌ Uphold Rejection
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `}
        </div>
        <div id="appeal-modal-container"></div>`;
    },

    showReviewModal(appealId, decision) {
        const title = decision === 'approved' ? 'Override & Approve' : 'Uphold Rejection';
        const body = `
            <p class="text-sm text-muted mb-3">
                ${decision === 'approved' 
                    ? 'This will override the rejection and approve the expense.' 
                    : 'This will uphold the original rejection. The employee will be notified.'}
            </p>
            <div class="form-group">
                <label class="form-label">Justification (min. 20 characters)</label>
                <textarea id="appeal-justification" class="form-textarea" 
                          placeholder="Explain your decision..." minlength="20"></textarea>
            </div>
            <div id="appeal-review-error" class="form-error hidden"></div>
        `;

        const footer = `
            <button class="btn btn-secondary" onclick="Components.closeModal('appeal-review-modal')">Cancel</button>
            <button class="btn ${decision === 'approved' ? 'btn-approve' : 'btn-reject'}" 
                    onclick="AppealsPage.handleReview('${appealId}', '${decision}')">
                ${decision === 'approved' ? '✅ Approve' : '❌ Reject'}
            </button>
        `;

        document.getElementById('appeal-modal-container').innerHTML =
            Components.modal('appeal-review-modal', title, body, footer);
    },

    async handleReview(appealId, decision) {
        const justification = document.getElementById('appeal-justification').value;
        const errorEl = document.getElementById('appeal-review-error');
        errorEl.classList.add('hidden');

        if (justification.length < 20) {
            errorEl.textContent = 'Justification must be at least 20 characters.';
            errorEl.classList.remove('hidden');
            return;
        }

        try {
            await API.reviewAppeal(appealId, decision, justification);
            Components.closeModal('appeal-review-modal');
            Utils.toast(`Appeal ${decision}!`, decision === 'approved' ? 'success' : 'info');
            App.navigate(window.location.hash);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    },
};
