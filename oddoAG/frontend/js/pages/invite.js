/**
 * Invite Acceptance Page
 */
const InvitePage = {
    async render(token) {
        if (!token) {
            return `<div class="auth-container"><div class="auth-card">
                <div class="auth-logo"><h1>💸 ExpenseFlow</h1></div>
                <p class="text-center text-muted">Invalid invite link.</p>
                <div class="auth-footer"><a href="#/login">Go to login</a></div>
            </div></div>`;
        }

        let inviteInfo;
        try {
            inviteInfo = await API.getInviteInfo(token);
        } catch (err) {
            return `<div class="auth-container"><div class="auth-card">
                <div class="auth-logo"><h1>💸 ExpenseFlow</h1></div>
                <div class="form-error">${Utils.escapeHtml(err.message)}</div>
                <div class="auth-footer"><a href="#/login">Go to login</a></div>
            </div></div>`;
        }

        return `
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-logo">
                    <h1>💸 ExpenseFlow</h1>
                    <p>You've been invited to join <strong>${Utils.escapeHtml(inviteInfo.company_name)}</strong></p>
                </div>
                <form class="auth-form" onsubmit="InvitePage.handleSubmit(event, '${token}')">
                    <div class="form-group">
                        <label class="form-label">Name</label>
                        <input type="text" class="form-input" value="${Utils.escapeHtml(inviteInfo.name)}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Email</label>
                        <input type="email" class="form-input" value="${Utils.escapeHtml(inviteInfo.email)}" readonly>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="invite-password">Set Password</label>
                        <input type="password" id="invite-password" class="form-input" placeholder="Min. 8 characters" minlength="8" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="invite-confirm">Confirm Password</label>
                        <input type="password" id="invite-confirm" class="form-input" placeholder="Repeat password" required>
                    </div>
                    <div id="invite-error" class="form-error hidden"></div>
                    <button type="submit" class="btn btn-primary btn-lg w-full" id="invite-btn">
                        Activate Account
                    </button>
                </form>
            </div>
        </div>`;
    },

    async handleSubmit(e, token) {
        e.preventDefault();
        const password = document.getElementById('invite-password').value;
        const confirm = document.getElementById('invite-confirm').value;
        const errorEl = document.getElementById('invite-error');
        const btn = document.getElementById('invite-btn');

        if (password !== confirm) {
            errorEl.textContent = 'Passwords do not match';
            errorEl.classList.remove('hidden');
            return;
        }

        btn.disabled = true;
        btn.textContent = 'Activating...';
        errorEl.classList.add('hidden');

        try {
            const data = await API.acceptInvite(token, password);
            App.currentUser = data.user;
            Utils.toast('Account activated! Welcome to ExpenseFlow.', 'success');
            window.location.hash = '#/expenses';
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Activate Account';
        }
    },
};
