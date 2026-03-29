/**
 * Admin Dashboard — KPI cards, recent expenses, quick links
 */
const DashboardPage = {
    async render() {
        let stats = {};
        let recentExpenses = [];

        try {
            stats = await API.getStats();
        } catch { stats = {}; }

        try {
            const { expenses } = await API.getExpenses();
            recentExpenses = expenses.slice(0, 10);
        } catch { recentExpenses = []; }

        const company = App.currentCompany;
        const currency = company?.currency_code || 'USD';

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <div>
                    <h1 class="page-title">Dashboard</h1>
                    ${App.currentUser?.role === 'admin' && company?.company_code ? 
                      `<div class="mt-2 p-3 bg-gray-50 rounded border border-gray-200 inline-flex items-center gap-3">
                         <span class="text-sm font-medium text-gray-700">Company Code:</span>
                         <code class="text-lg font-bold text-primary tracking-wide">${company.company_code}</code>
                         <button onclick="navigator.clipboard.writeText('${company.company_code}'); Utils.toast('Company Code copied!', 'success');" class="text-muted hover:text-primary transition-colors cursor-pointer" title="Copy code">
                           📋
                         </button>
                       </div>` : ''}
                </div>
                <span class="text-sm text-muted">${Utils.formatDate(new Date().toISOString())}</span>
            </div>

            <!-- KPI Cards -->
            <div class="kpi-grid mb-6">
                ${Components.kpiCard('📊', stats.total_this_month || 0, 'Expenses This Month', 'blue')}
                ${Components.kpiCard('⏳', stats.pending_approvals || 0, 'Pending Approvals', 'orange')}
                ${Components.kpiCard('✅', stats.approved_this_month || 0, 'Approved This Month', 'green')}
                ${Components.kpiCard('❌', stats.rejected_this_month || 0, 'Rejected This Month', 'red')}
                ${Components.kpiCard('💰', Utils.formatCurrency(stats.total_approved_amount || 0, currency), 'Total Approved Amount', 'purple')}
            </div>

            <!-- Quick Actions -->
            <div class="card mb-6">
                <h2 class="section-title mb-4">Quick Actions</h2>
                <div class="flex gap-3" style="flex-wrap: wrap;">
                    <a href="#/users" class="btn btn-secondary">👥 Manage Users</a>
                    <a href="#/approval-config" class="btn btn-secondary">⚙️ Configure Approvals</a>
                    <a href="#/submit-expense" class="btn btn-primary">➕ Submit Expense</a>
                    <a href="#/appeals" class="btn btn-secondary">⚖️ Review Appeals</a>
                </div>
            </div>

            <!-- Recent Expenses -->
            <div>
                <h2 class="section-title mb-4">Recent Expenses</h2>
                ${Components.dataTable([
                    { label: 'Employee', render: r => Utils.escapeHtml(r.employee_name || '—') },
                    { label: 'Amount', render: r => Utils.formatCurrency(r.converted_amount || r.amount, currency) },
                    { label: 'Category', render: r => `${Utils.categoryIcon(r.category)} ${Utils.escapeHtml(r.category)}` },
                    { label: 'Date', render: r => Utils.formatDate(r.expense_date) },
                    { label: 'Status', render: r => Components.statusBadge(r.status) },
                ], recentExpenses, {
                    emptyMessage: 'No expenses yet',
                    onRowClick: 'App.navigateToExpense',
                })}
            </div>
        </div>`;
    },
};
