/**
 * ExpenseFlow — Utility functions
 */

const Utils = {
    /**
     * Format a date string to a readable format.
     */
    formatDate(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    },

    /**
     * Format a date with time.
     */
    formatDateTime(dateStr) {
        if (!dateStr) return '—';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },

    /**
     * Relative time (e.g., "2 hours ago").
     */
    timeAgo(dateStr) {
        if (!dateStr) return '';
        const now = new Date();
        const d = new Date(dateStr);
        const seconds = Math.floor((now - d) / 1000);

        if (seconds < 60) return 'just now';
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
        if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
        return Utils.formatDate(dateStr);
    },

    /**
     * Format currency amount.
     */
    formatCurrency(amount, currency = 'USD') {
        if (amount == null) return '—';
        try {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2,
            }).format(amount);
        } catch {
            return `${currency} ${parseFloat(amount).toFixed(2)}`;
        }
    },

    /**
     * Status display labels.
     */
    statusLabel(status) {
        const labels = {
            'draft': 'Draft',
            'submitted': 'Submitted',
            'pending_manager': 'Pending Manager',
            'in_review': 'In Review',
            'changes_requested': 'Changes Requested',
            'approved': 'Approved',
            'rejected': 'Rejected',
            'appealed': 'Appealed',
        };
        return labels[status] || status;
    },

    /**
     * Thread type emoji icons.
     */
    threadIcon(type) {
        const icons = {
            'submission': '📋',
            'approval': '✅',
            'rejection': '❌',
            'changes_requested': '🔄',
            'query': '💬',
            'reply': '↩️',
            'revision_submitted': '📝',
            'admin_override': '⚡',
        };
        return icons[type] || '💬';
    },

    /**
     * Thread type labels.
     */
    threadLabel(type) {
        const labels = {
            'submission': 'Submitted',
            'approval': 'Approved',
            'rejection': 'Rejected',
            'changes_requested': 'Changes Requested',
            'query': 'Question',
            'reply': 'Reply',
            'revision_submitted': 'Resubmitted',
            'admin_override': 'Admin Override',
        };
        return labels[type] || type;
    },

    /**
     * Get user initials for avatar.
     */
    initials(name) {
        if (!name) return '?';
        return name.split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase();
    },

    /**
     * Debounce function.
     */
    debounce(fn, ms = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), ms);
        };
    },

    /**
     * Escape HTML to prevent XSS.
     */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    },

    /**
     * Show a toast notification.
     */
    toast(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(30px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Notification type icons.
     */
    notifIcon(type) {
        const icons = {
            'approval_required': '📥',
            'approved': '✅',
            'rejected': '❌',
            'changes_requested': '🔄',
            'appeal_submitted': '⚖️',
            'appeal_decided': '⚡',
            'revision_submitted': '📝',
        };
        return icons[type] || '🔔';
    },

    /**
     * Category icons.
     */
    categoryIcon(category) {
        const icons = {
            'Travel': '✈️',
            'Meals': '🍽️',
            'Accommodation': '🏨',
            'Equipment': '🖥️',
            'Software': '💿',
            'Training': '📚',
            'Marketing': '📢',
            'Other': '📦',
        };
        return icons[category] || '📦';
    },
};
