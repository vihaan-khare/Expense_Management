/**
 * My Expenses Page — list of employee's own expenses
 */
const MyExpensesPage = {
    async render() {
        const company = App.currentCompany;
        const currency = company?.currency_code || 'USD';
        let expenses = [];

        try {
            const data = await API.getExpenses();
            expenses = data.expenses;
        } catch (err) {
            return `<div class="form-error">Failed to load expenses: ${err.message}</div>`;
        }

        const role = App.currentUser?.role;
        const title = role === 'admin' ? 'Company Expenses' : 'My Expenses';

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <h1 class="page-title">${title}</h1>
                <a href="#/submit-expense" class="btn btn-primary">➕ New Request</a>
            </div>

            ${Components.dataTable([
                { label: 'Items', render: r => `
                    <div>
                        <div class="font-medium text-gray-900 truncate" style="max-width: 250px;" title="${Utils.escapeHtml(r.description)}">
                            ${Utils.escapeHtml(r.description)}
                        </div>
                        <div class="text-xs text-muted mt-1">${Utils.formatDate(r.expense_date)} ${role === 'admin' ? `— ${Utils.escapeHtml(r.employee_name)}` : ''}</div>
                    </div>
                `},
                { label: 'Category', render: r => `
                    <div class="inline-flex items-center gap-2">
                        <span>${Utils.categoryIcon(r.category)}</span>
                        <span class="text-sm font-medium text-gray-700">${Utils.escapeHtml(r.category)}</span>
                    </div>
                `},
                { label: 'Cost', render: r => {
                    let str = `<span class="font-bold text-gray-900">${Utils.formatCurrency(r.converted_amount || r.amount, currency)}</span>`;
                    if (r.currency !== currency) {
                        str += `<br><span class="text-xs text-muted">(${Utils.formatCurrency(r.amount, r.currency)})</span>`;
                    }
                    return str;
                }},
                { label: 'Status', render: r => Components.statusBadge(r.status) },
                { label: 'Actions', render: r => `
                    <div class="flex items-center gap-2">
                        <a href="#/expense/${r.id}" class="btn btn-ghost btn-sm text-primary" title="View Details">Edit</a>
                        <button onclick="MyExpensesPage.deleteExpense('${r.id}', event)" class="btn btn-ghost btn-sm text-red-600 hover:bg-red-50" title="Delete record">Delete</button>
                    </div>
                `}
            ], expenses, {
                emptyMessage: 'No expenses yet. Submit your first one!',
                // Not using generic row click because of inline actions
            })}
        </div>`;
    },

    async deleteExpense(id, event) {
        event.stopPropagation();
        if (!confirm('Are you sure you want to permanently delete this expense record?')) return;

        try {
            await API.deleteExpense(id);
            Utils.toast('Expense deleted successfully.', 'success');
            App.navigate(window.location.hash);
        } catch (err) {
            Utils.toast(err.message, 'error');
        }
    }
};
