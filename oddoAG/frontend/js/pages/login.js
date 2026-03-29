/**
 * Login Page
 */
const LoginPage = {
    async render() {
        return `
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-logo">
                    <h1>💸 ExpenseFlow</h1>
                    <p>Welcome back</p>
                </div>
                <form class="auth-form" onsubmit="LoginPage.handleSubmit(event)">
                    <div class="form-group">
                        <label class="form-label" for="login-email">Email</label>
                        <input type="email" id="login-email" class="form-input" placeholder="you@company.com" required>
                    </div>
                    <div class="form-group">
                        <div class="flex-between">
                            <label class="form-label" for="login-password">Password</label>
                            <a href="#" onclick="alert('Please contact your Admin to securely reset your password.'); return false;" class="text-xs text-primary">Forgot password?</a>
                        </div>
                        <input type="password" id="login-password" class="form-input" placeholder="Enter password" required>
                    </div>
                    <div id="login-error" class="form-error hidden"></div>
                    <button type="submit" class="btn btn-primary btn-lg w-full" id="login-btn">
                        Login
                    </button>
                </form>
                <div class="auth-footer">
                    Don't have an account? <a href="#/signup">Sign Up</a>
                </div>
            </div>
        </div>`;
    },

    async handleSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('login-btn');
        const errorEl = document.getElementById('login-error');
        errorEl.classList.add('hidden');

        btn.disabled = true;
        btn.textContent = 'Logging in...';

        try {
            const data = await API.login(
                document.getElementById('login-email').value,
                document.getElementById('login-password').value
            );
            App.currentUser = data.user;
            App.currentCompany = data.company;
            Utils.toast('Welcome back!', 'success');

            // Role-based redirect
            if (data.user.role === 'admin') {
                window.location.hash = '#/dashboard';
            } else if (data.user.role === 'manager') {
                window.location.hash = '#/approver-queue';
            } else {
                window.location.hash = '#/expenses';
            }
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Log In';
        }
    },
};
