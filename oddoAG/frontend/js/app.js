/**
 * ExpenseFlow — SPA Router & Application Controller
 */

const App = {
    currentUser: null,
    currentCompany: null,
    notifPollTimer: null,

    /**
     * Initialize the application.
     */
    async init() {
        // Try to restore session
        try {
            const data = await API.getMe();
            this.currentUser = data.user;
            this.currentCompany = data.company;
        } catch {
            this.currentUser = null;
            this.currentCompany = null;
        }

        // Listen for hash changes
        window.addEventListener('hashchange', () => this.navigate(window.location.hash));

        // Initial route
        this.navigate(window.location.hash || '#/');
    },

    /**
     * Route to a page based on hash.
     */
    async navigate(hash) {
        const app = document.getElementById('app');
        const [route, ...params] = hash.replace('#/', '').split('/');

        // Stop any existing polling
        if (typeof ExpenseDetailPage !== 'undefined') ExpenseDetailPage._stopPolling();

        // Public routes (no auth needed)
        if (['signup', 'login'].includes(route)) {
            app.innerHTML = Components.loading(true);
            let html;
            if (route === 'signup') html = await SignupPage.render();
            else html = await LoginPage.render();
            app.innerHTML = html;
            this._stopNotifPolling();
            return;
        }

        // Invite route
        if (route === 'invite') {
            app.innerHTML = Components.loading(true);
            app.innerHTML = await InvitePage.render(params[0]);
            return;
        }

        // All other routes require auth
        if (!this.currentUser) {
            window.location.hash = '#/login';
            return;
        }

        // Render page inside app shell
        app.innerHTML = Components.loading(true);

        let pageContent;
        try {
            pageContent = await this._getPageContent(route, params);
        } catch (err) {
            pageContent = `<div class="form-error">Error loading page: ${err.message}</div>`;
        }

        app.innerHTML = Components.appShell(
            this.currentUser,
            this.currentCompany,
            `#/${route || 'dashboard'}`,
            pageContent
        );

        // Start notification polling
        this._startNotifPolling();

        // Scroll to top
        window.scrollTo(0, 0);
    },

    /**
     * Get page content based on route.
     */
    async _getPageContent(route, params) {
        const role = this.currentUser?.role;

        switch (route) {
            case '':
            case 'dashboard':
                if (role === 'admin') return DashboardPage.render();
                if (role === 'manager') return ApproverQueuePage.render();
                return MyExpensesPage.render();

            case 'users':
                if (role !== 'admin') return '<div class="form-error">Access denied</div>';
                return UsersPage.render();

            case 'approval-config':
                if (role !== 'admin') return '<div class="form-error">Access denied</div>';
                return ApprovalConfigPage.render();

            case 'appeals':
                if (role !== 'admin') return '<div class="form-error">Access denied</div>';
                return AppealsPage.render();

            case 'expenses':
                return MyExpensesPage.render();

            case 'submit-expense':
                return SubmitExpensePage.render();

            case 'approver-queue':
                if (role === 'employee') return '<div class="form-error">Access denied</div>';
                return ApproverQueuePage.render();

            case 'expense':
                return ExpenseDetailPage.render(params[0]);

            default:
                return `
                    <div class="empty-state">
                        <div class="empty-state-icon">🔍</div>
                        <div class="empty-state-title">Page not found</div>
                        <div class="empty-state-text">The page you're looking for doesn't exist.</div>
                    </div>`;
        }
    },

    /**
     * Navigate to expense detail.
     */
    navigateToExpense(expenseId) {
        window.location.hash = `#/expense/${expenseId}`;
    },

    /**
     * Handle logout.
     */
    async handleLogout() {
        try {
            await API.logout();
        } catch { /* ignore */ }
        this.currentUser = null;
        this.currentCompany = null;
        this._stopNotifPolling();
        window.location.hash = '#/login';
    },

    /**
     * Toggle sidebar (mobile).
     */
    toggleSidebar(force) {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebar-overlay');
        if (!sidebar) return;

        if (typeof force === 'boolean') {
            sidebar.classList.toggle('open', force);
            overlay?.classList.toggle('visible', force);
        } else {
            sidebar.classList.toggle('open');
            overlay?.classList.toggle('visible');
        }
    },

    /**
     * Toggle notifications panel.
     */
    async toggleNotifications() {
        const panel = document.getElementById('notifications-panel');
        if (!panel) return;

        const isHidden = panel.classList.contains('hidden');
        panel.classList.toggle('hidden');

        if (isHidden) {
            // Load notifications
            const list = document.getElementById('notifications-list');
            list.innerHTML = Components.loading();

            try {
                const { notifications } = await API.getNotifications();
                if (notifications.length === 0) {
                    list.innerHTML = `
                        <div class="p-4 text-center text-sm text-muted">
                            No notifications yet
                        </div>`;
                } else {
                    list.innerHTML = notifications.map(n => `
                        <div class="notification-item ${n.is_read ? '' : 'unread'}" 
                             onclick="${n.expense_id ? `App.navigateToExpense('${n.expense_id}')` : ''}">
                            <div class="flex items-center gap-3">
                                <span>${Utils.notifIcon(n.type)}</span>
                                <div class="flex-1">
                                    <div class="text-sm">${Utils.escapeHtml(n.message)}</div>
                                    <div class="text-xs text-muted mt-1">${Utils.timeAgo(n.created_at)}</div>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }
            } catch {
                list.innerHTML = '<div class="p-4 text-center text-sm text-muted">Failed to load</div>';
            }
        }
    },

    /**
     * Mark all notifications as read.
     */
    async markAllRead() {
        try {
            await API.markNotificationsRead();
            const badge = document.getElementById('notif-badge');
            if (badge) {
                badge.textContent = '0';
                badge.classList.add('hidden');
            }
            // Refresh list
            const items = document.querySelectorAll('.notification-item.unread');
            items.forEach(item => item.classList.remove('unread'));
            Utils.toast('All notifications marked as read', 'info');
        } catch { /* ignore */ }
    },

    /**
     * Start polling for notification count.
     */
    _startNotifPolling() {
        this._stopNotifPolling();
        this._updateNotifCount();
        this.notifPollTimer = setInterval(() => this._updateNotifCount(), 15000);
    },

    _stopNotifPolling() {
        if (this.notifPollTimer) {
            clearInterval(this.notifPollTimer);
            this.notifPollTimer = null;
        }
    },

    async _updateNotifCount() {
        try {
            const { unread_count } = await API.getUnreadCount();
            const badge = document.getElementById('notif-badge');
            if (badge) {
                badge.textContent = unread_count;
                badge.classList.toggle('hidden', unread_count === 0);
            }
        } catch { /* ignore */ }
    },
};

// ─── Boot ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());
