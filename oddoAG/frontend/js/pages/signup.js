/**
 * Signup Page — Join by Company Code or Create Company
 */
const SignupPage = {
    countries: [],

    async render() {
        // Fetch countries for Admin setup
        try {
            const { countries } = await API.getCountries();
            this.countries = countries;
        } catch { this.countries = []; }

        const countryOptions = this.countries.map(c =>
            `<option value="${c.name}" data-currency="${c.currency_code}">${Utils.escapeHtml(c.name)} (${c.currency_code})</option>`
        ).join('');

        return `
        <div class="auth-container">
            <div class="auth-card">
                <div class="auth-logo">
                    <h1>💸 ExpenseFlow</h1>
                    <p>Sign up for an account</p>
                </div>
                <form class="auth-form" onsubmit="SignupPage.handleSubmit(event)">
                    <div class="form-group">
                        <label class="form-label" for="signup-role">Role</label>
                        <select id="signup-role" class="form-select" required onchange="SignupPage.toggleRoleFields()">
                            <option value="employee" selected>Employee</option>
                            <option value="manager">Manager</option>
                            <option value="admin">Admin (Create Company)</option>
                        </select>
                    </div>

                    <div id="employee-fields">
                        <div class="form-group">
                            <label class="form-label" for="company-code">Company Code</label>
                            <input type="text" id="company-code" class="form-input" placeholder="e.g. ABC123" required>
                            <p class="text-muted text-sm mt-1">Ask your admin for the unique company code.</p>
                        </div>
                    </div>

                    <div id="admin-fields" class="hidden">
                        <div class="form-group">
                            <label class="form-label" for="company-name">Company Name</label>
                            <input type="text" id="company-name" class="form-input" placeholder="Acme Inc.">
                        </div>
                        <div class="form-group">
                            <label class="form-label" for="country">Country</label>
                            <select id="country" class="form-select" onchange="SignupPage.onCountryChange()">
                                <option value="">Select your country...</option>
                                ${countryOptions}
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Base Currency</label>
                            <input type="text" id="currency-display" class="form-input" readonly placeholder="Auto-detected">
                            <input type="hidden" id="currency-code">
                        </div>
                    </div>

                    <div class="divider"></div>
                    
                    <div class="form-group">
                        <label class="form-label" for="user-name">Your Name</label>
                        <input type="text" id="user-name" class="form-input" placeholder="John Doe" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="user-email">Email</label>
                        <input type="email" id="user-email" class="form-input" placeholder="john@example.com" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="user-password">Password</label>
                        <input type="password" id="user-password" class="form-input" placeholder="Min. 8 characters" minlength="8" required>
                    </div>
                    
                    <div id="signup-error" class="form-error hidden"></div>
                    
                    <button type="submit" class="btn btn-primary btn-lg w-full" id="signup-btn">
                        Sign Up
                    </button>
                </form>
                <div class="auth-footer">
                    Already have an account? <a href="#/login">Log in</a>
                </div>
            </div>
        </div>`;
    },

    toggleRoleFields() {
        const role = document.getElementById('signup-role').value;
        const empFields = document.getElementById('employee-fields');
        const adminFields = document.getElementById('admin-fields');
        const codeInput = document.getElementById('company-code');
        const compName = document.getElementById('company-name');
        const country = document.getElementById('country');

        if (role === 'admin') {
            empFields.classList.add('hidden');
            adminFields.classList.remove('hidden');
            codeInput.removeAttribute('required');
            compName.setAttribute('required', 'required');
            country.setAttribute('required', 'required');
        } else {
            adminFields.classList.add('hidden');
            empFields.classList.remove('hidden');
            compName.removeAttribute('required');
            country.removeAttribute('required');
            codeInput.setAttribute('required', 'required');
        }
    },

    onCountryChange() {
        const select = document.getElementById('country');
        const selected = select.options[select.selectedIndex];
        const currency = selected?.dataset?.currency || '';
        document.getElementById('currency-code').value = currency;
        document.getElementById('currency-display').value = currency ? `${currency}` : '';
    },

    async handleSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('signup-btn');
        const errorEl = document.getElementById('signup-error');
        errorEl.classList.add('hidden');

        btn.disabled = true;
        btn.textContent = 'Creating...';

        const role = document.getElementById('signup-role').value;
        const payload = {
            role: role,
            name: document.getElementById('user-name').value,
            email: document.getElementById('user-email').value,
            password: document.getElementById('user-password').value,
        };

        if (role === 'admin') {
            payload.company_name = document.getElementById('company-name').value;
            payload.country = document.getElementById('country').value;
            payload.currency_code = document.getElementById('currency-code').value;
        } else {
            payload.company_code = document.getElementById('company-code').value;
        }

        try {
            const data = await API.signup(payload);
            App.currentUser = data.user;
            App.currentCompany = data.company;
            Utils.toast('Account created successfully!', 'success');
            
            if (role === 'admin') {
                window.location.hash = '#/dashboard';
            } else {
                window.location.hash = '#/expenses';
            }
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Sign Up';
        }
    },
};
