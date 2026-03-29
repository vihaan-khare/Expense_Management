/**
 * ExpenseFlow — Reusable UI Components
 */

const Components = {
    /**
     * Status badge pill.
     */
    statusBadge(status) {
        const label = Utils.statusLabel(status);
        return `<span class="badge badge-${status}"><span class="dot"></span>${Utils.escapeHtml(label)}</span>`;
    },

    /**
     * Role pill.
     */
    rolePill(role) {
        return `<span class="role-pill ${role}">${Utils.escapeHtml(role)}</span>`;
    },

    /**
     * KPI stat card.
     */
    kpiCard(icon, value, label, colorClass = 'blue') {
        return `
        <div class="kpi-card">
            <div class="kpi-header">
                <div class="kpi-icon ${colorClass}">${icon}</div>
            </div>
            <div>
                <div class="kpi-value">${Utils.escapeHtml(String(value))}</div>
                <div class="kpi-label">${Utils.escapeHtml(label)}</div>
            </div>
        </div>`;
    },

    /**
     * Approval step visualizer.
     */
    stepVisualizer(currentStep, totalSteps, steps = [], status = '', hasManagerPrestep = false) {
        if (totalSteps === 0 && !hasManagerPrestep) {
            return '<div class="text-sm text-muted">No approval steps configured</div>';
        }

        let html = '<div class="step-visualizer">';
        const allSteps = [];

        // Manager pre-step
        if (hasManagerPrestep) {
            allSteps.push({ number: 0, label: 'Manager', role_label: 'Manager' });
        }

        // Chain steps
        steps.forEach(s => {
            allSteps.push({ number: s.step_number, label: s.role_label, ...s });
        });

        allSteps.forEach((step, idx) => {
            let dotClass = 'pending';
            let dotContent = step.number;

            if (status === 'rejected') {
                if (step.number < currentStep) dotClass = 'completed';
                else if (step.number === currentStep) dotClass = 'rejected';
            } else if (status === 'approved') {
                dotClass = 'completed';
                dotContent = '✓';
            } else {
                if (step.number < currentStep) {
                    dotClass = 'completed';
                    dotContent = '✓';
                } else if (step.number === currentStep) {
                    dotClass = 'active';
                }
            }

            html += `
            <div class="step-group">
                <div class="step-dot ${dotClass}">${dotContent}</div>
                <div class="step-label">${Utils.escapeHtml(step.label || step.role_label)}</div>
            </div>`;

            if (idx < allSteps.length - 1) {
                let connClass = 'pending';
                if (step.number < currentStep) connClass = 'completed';
                else if (step.number === currentStep) connClass = 'active';
                html += `<div class="step-connector ${connClass}"></div>`;
            }
        });

        html += '</div>';
        return html;
    },

    /**
     * Discussion thread message.
     */
    threadMessage(comment) {
        const changeItems = comment.content?.includes('Reasons:')
            ? comment.content.split('Reasons: ')[1]?.split(', ').map(r =>
                `<div class="thread-change-item">⚠️ ${Utils.escapeHtml(r)}</div>`
            ).join('') : '';

        const mainContent = comment.content?.includes('\n\nReasons:')
            ? comment.content.split('\n\nReasons:')[0]
            : comment.content;

        return `
        <div class="thread-message thread-${comment.comment_type}">
            <div class="thread-header">
                <div class="thread-author">
                    <span>${Utils.threadIcon(comment.comment_type)}</span>
                    <span class="thread-author-name">${Utils.escapeHtml(comment.user_name || 'System')}</span>
                    <span class="thread-author-role">${Utils.escapeHtml(comment.user_role || '')}</span>
                    <span class="thread-action-label">${Utils.threadLabel(comment.comment_type)}</span>
                </div>
                <span class="thread-timestamp">${Utils.timeAgo(comment.created_at)}</span>
            </div>
            <div class="thread-body">${Utils.escapeHtml(mainContent)}</div>
            ${changeItems ? `<div class="thread-change-items">${changeItems}</div>` : ''}
        </div>`;
    },

    /**
     * Thread composer.
     */
    threadComposer(expenseId) {
        return `
        <div class="thread-composer">
            <textarea id="thread-input" placeholder="Write a comment or question..." rows="2"></textarea>
            <div class="thread-composer-actions">
                <div></div>
                <div class="flex gap-2">
                    <select id="thread-type" class="form-select" style="width: auto; padding: 4px 8px; font-size: 0.8rem;">
                        <option value="query">Question</option>
                        <option value="reply">Reply</option>
                    </select>
                    <button class="btn btn-primary btn-sm" onclick="ExpenseDetailPage.postComment('${expenseId}')">
                        Send
                    </button>
                </div>
            </div>
        </div>`;
    },

    /**
     * Data table.
     */
    dataTable(columns, rows, options = {}) {
        const { emptyMessage = 'No data found', onRowClick } = options;

        if (rows.length === 0) {
            return `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div class="empty-state-title">${Utils.escapeHtml(emptyMessage)}</div>
            </div>`;
        }

        let html = '<div class="table-container"><table><thead><tr>';
        columns.forEach(col => {
            html += `<th>${Utils.escapeHtml(col.label)}</th>`;
        });
        html += '</tr></thead><tbody>';

        rows.forEach(row => {
            const clickAttr = onRowClick ? `onclick="${onRowClick}('${row.id}')" class="clickable"` : '';
            html += `<tr ${clickAttr}>`;
            columns.forEach(col => {
                const value = col.render ? col.render(row) : (row[col.key] || '—');
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        return html;
    },

    /**
     * Modal dialog.
     */
    modal(id, title, bodyHtml, footerHtml = '') {
        return `
        <div id="${id}" class="modal-overlay" onclick="if(event.target===this)Components.closeModal('${id}')">
            <div class="modal">
                <div class="modal-header">
                    <h3 class="modal-title">${Utils.escapeHtml(title)}</h3>
                    <button class="modal-close" onclick="Components.closeModal('${id}')">&times;</button>
                </div>
                <div class="modal-body">
                    ${bodyHtml}
                </div>
                ${footerHtml ? `<div class="modal-footer">${footerHtml}</div>` : ''}
            </div>
        </div>`;
    },

    closeModal(id) {
        const modal = document.getElementById(id);
        if (modal) modal.remove();
    },

    /**
     * Loading spinner.
     */
    loading(large = false) {
        return `<div class="page-loading"><div class="spinner ${large ? 'spinner-lg' : ''}"></div></div>`;
    },

    /**
     * App shell with sidebar.
     */
    appShell(user, company, activeRoute, pageContent) {
        const navItems = this._getNavItems(user.role);

        return `
        <div class="app-shell">
            <!-- Sidebar Overlay (mobile) -->
            <div class="sidebar-overlay" id="sidebar-overlay" onclick="App.toggleSidebar()"></div>

            <!-- Sidebar -->
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-logo">
                    <h1>
                        <span class="logo-icon">💸</span>
                        ExpenseFlow
                    </h1>
                </div>

                <nav class="sidebar-nav">
                    ${navItems.map(item => {
                        if (item.section) {
                            return `<div class="nav-section-label">${item.section}</div>`;
                        }
                        const isActive = activeRoute === item.route || 
                            (item.route === '#/dashboard' && activeRoute === '#/');
                        return `
                        <a href="${item.route}" class="nav-link ${isActive ? 'active' : ''}" 
                           onclick="App.toggleSidebar(false)">
                            <span class="nav-icon">${item.icon}</span>
                            ${item.label}
                        </a>`;
                    }).join('')}
                </nav>

                <div class="sidebar-footer">
                    <div class="user-info">
                        <div class="user-avatar">${Utils.initials(user.name)}</div>
                        <div class="user-details">
                            <div class="user-name">${Utils.escapeHtml(user.name)}</div>
                            ${this.rolePill(user.role)}
                        </div>
                    </div>
                </div>
            </aside>

            <!-- Main Content -->
            <div class="main-content">
                <div class="topbar">
                    <div class="topbar-left">
                        <button class="hamburger" onclick="App.toggleSidebar()">☰</button>
                        <span class="text-sm text-muted">${Utils.escapeHtml(company?.name || '')}</span>
                    </div>
                    <div class="topbar-right">
                        <button class="notification-btn" id="notifications-btn" onclick="App.toggleNotifications()">
                            🔔
                            <span class="notification-badge hidden" id="notif-badge">0</span>
                        </button>
                        <button class="btn btn-ghost btn-sm" onclick="App.handleLogout()">Logout</button>
                    </div>
                </div>

                <div class="page-content" id="page-content">
                    ${pageContent}
                </div>
            </div>

            <!-- Notifications Panel -->
            <div class="notifications-panel hidden" id="notifications-panel">
                <div class="notifications-header">
                    <span class="font-semibold">Notifications</span>
                    <button class="btn btn-ghost btn-sm" onclick="App.markAllRead()">Mark all read</button>
                </div>
                <div class="notifications-list" id="notifications-list">
                    <div class="page-loading"><div class="spinner"></div></div>
                </div>
            </div>
        </div>`;
    },

    /**
     * Get navigation items based on role.
     */
    _getNavItems(role) {
        const items = [];

        if (role === 'admin') {
            items.push({ section: 'Overview' });
            items.push({ icon: '📊', label: 'Dashboard', route: '#/dashboard' });
            items.push({ section: 'Management' });
            items.push({ icon: '👥', label: 'Users', route: '#/users' });
            items.push({ icon: '⚙️', label: 'Approval Config', route: '#/approval-config' });
            items.push({ icon: '⚖️', label: 'Appeals', route: '#/appeals' });
            items.push({ section: 'Expenses' });
            items.push({ icon: '📋', label: 'All Expenses', route: '#/expenses' });
            items.push({ icon: '📥', label: 'Approval Queue', route: '#/approver-queue' });
            items.push({ icon: '➕', label: 'Submit Expense', route: '#/submit-expense' });
        } else if (role === 'manager') {
            items.push({ section: 'Overview' });
            items.push({ icon: '📥', label: 'Approval Queue', route: '#/approver-queue' });
            items.push({ section: 'Expenses' });
            items.push({ icon: '📋', label: 'My Expenses', route: '#/expenses' });
            items.push({ icon: '➕', label: 'Submit Expense', route: '#/submit-expense' });
        } else {
            items.push({ section: 'Expenses' });
            items.push({ icon: '📋', label: 'My Expenses', route: '#/expenses' });
            items.push({ icon: '➕', label: 'Submit Expense', route: '#/submit-expense' });
        }

        return items;
    },
};
