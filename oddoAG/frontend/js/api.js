/**
 * ExpenseFlow — API Client
 */

const API = {
    /**
     * Base fetch wrapper with error handling.
     */
    async request(url, options = {}) {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
            },
        };

        // Don't set Content-Type for FormData
        if (options.body instanceof FormData) {
            delete defaultOptions.headers['Content-Type'];
        }

        const response = await fetch(url, { ...defaultOptions, ...options });

        let data;
        try {
            data = await response.json();
        } catch {
            data = { error: 'Invalid server response' };
        }

        if (!response.ok) {
            const errorMsg = data.error || `Request failed (${response.status})`;
            throw new Error(errorMsg);
        }

        return data;
    },

    // ─── Auth ────────────────────────────────────────────────────────
    async signup(formData) {
        return this.request('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify(formData),
        });
    },

    async login(email, password) {
        return this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },

    async logout() {
        return this.request('/api/auth/logout', { method: 'POST' });
    },

    async getMe() {
        return this.request('/api/auth/me');
    },

    async getInviteInfo(token) {
        return this.request(`/api/auth/accept-invite/${token}`);
    },

    async acceptInvite(token, password) {
        return this.request(`/api/auth/accept-invite/${token}`, {
            method: 'POST',
            body: JSON.stringify({ password }),
        });
    },

    // ─── Users ───────────────────────────────────────────────────────
    async getUsers() {
        return this.request('/api/users');
    },

    async createUser(userData) {
        return this.request('/api/users', {
            method: 'POST',
            body: JSON.stringify(userData),
        });
    },

    async updateUser(userId, userData) {
        return this.request(`/api/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(userData),
        });
    },

    async resetPassword(userId) {
        return this.request(`/api/users/${userId}/reset-password`, { method: 'POST' });
    },

    async getManagers() {
        return this.request('/api/users/managers');
    },

    // ─── Expenses ────────────────────────────────────────────────────
    async createExpense(expenseData) {
        return this.request('/api/expenses', {
            method: 'POST',
            body: JSON.stringify(expenseData),
        });
    },

    async getExpenses() {
        return this.request('/api/expenses');
    },

    async getExpense(id) {
        return this.request(`/api/expenses/${id}`);
    },

    async deleteExpense(id) {
        return this.request(`/api/expenses/${id}`, { method: 'DELETE' });
    },

    async resubmitExpense(id, data) {
        return this.request(`/api/expenses/${id}/resubmit`, {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },

    async uploadReceipt(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/api/expenses/upload-receipt', {
            method: 'POST',
            body: formData,
            headers: {}, // Let browser set content-type for FormData
        });
    },

    async scanReceipt(filepath) {
        return this.request('/api/expenses/ocr-scan', {
            method: 'POST',
            body: JSON.stringify({ filepath }),
        });
    },

    async getCurrencies() {
        return this.request('/api/expenses/currencies');
    },

    async convertCurrency(amount, from, to) {
        return this.request(`/api/expenses/convert?amount=${amount}&from=${from}&to=${to}`);
    },

    async getCountries() {
        return this.request('/api/expenses/countries');
    },

    async getStats() {
        return this.request('/api/expenses/stats');
    },

    // ─── Approvals ───────────────────────────────────────────────────
    async getChains() {
        return this.request('/api/approvals/chains');
    },

    async saveChain(chainData) {
        return this.request('/api/approvals/chains', {
            method: 'POST',
            body: JSON.stringify(chainData),
        });
    },

    async deleteChain(chainId) {
        return this.request(`/api/approvals/chains/${chainId}`, { method: 'DELETE' });
    },

    async getApprovalQueue() {
        return this.request('/api/approvals/queue');
    },

    async takeAction(expenseId, actionData) {
        return this.request(`/api/approvals/${expenseId}/action`, {
            method: 'POST',
            body: JSON.stringify(actionData),
        });
    },

    // ─── Comments ────────────────────────────────────────────────────
    async getComments(expenseId) {
        return this.request(`/api/expenses/${expenseId}/comments`);
    },

    async addComment(expenseId, content, commentType = 'query') {
        return this.request(`/api/expenses/${expenseId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ content, comment_type: commentType }),
        });
    },

    // ─── Appeals ─────────────────────────────────────────────────────
    async submitAppeal(expenseId, reason, evidenceUrl) {
        return this.request(`/api/expenses/${expenseId}/appeal`, {
            method: 'POST',
            body: JSON.stringify({ reason, evidence_url: evidenceUrl }),
        });
    },

    async getAppeals() {
        return this.request('/api/appeals');
    },

    async reviewAppeal(appealId, decision, justification) {
        return this.request(`/api/appeals/${appealId}/review`, {
            method: 'POST',
            body: JSON.stringify({ decision, justification }),
        });
    },

    // ─── Notifications ───────────────────────────────────────────────
    async getNotifications() {
        return this.request('/api/notifications');
    },

    async markNotificationsRead() {
        return this.request('/api/notifications/mark-read', { method: 'POST' });
    },

    async getUnreadCount() {
        return this.request('/api/notifications/unread-count');
    },
};
