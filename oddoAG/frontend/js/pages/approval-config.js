/**
 * Approval Chain Configuration Page (Admin only)
 */
const ApprovalConfigPage = {
    chains: [],

    async render() {
        try {
            const chainData = await API.getChains();
            this.chains = chainData.chains;
        } catch (err) {
            return `<div class="form-error">Failed to load: ${err.message}</div>`;
        }

        const activeChain = this.chains.find(c => c.is_active);
        
        // Find if there is an amount threshold rule
        let amountThreshold = 5000;
        let adminRole = 'admin';
        
        if (activeChain && activeChain.rules && activeChain.rules.length > 0) {
            const rule = activeChain.rules.find(r => r.rule_type === 'amount');
            if (rule && rule.amount_threshold) {
                amountThreshold = rule.amount_threshold;
            }
        }

        const currency = App.currentCompany?.currency_code || 'USD';

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <h1 class="page-title">Approval Workflow Configuration</h1>
            </div>

            <div class="card mb-6">
                <h2 class="section-title mb-4">Approval rules based on total amount / Employee Role</h2>
                <p class="text-sm text-muted mb-6">Define the thresholds and routing logic for who approves what based on expense amount.</p>

                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Range</th>
                            <th>Description</th>
                            <th>Approver Role</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>
                                <div class="font-medium text-gray-700">&lt; <span id="display-threshold">${amountThreshold}</span> ${currency}</div>
                            </td>
                            <td class="text-sm text-muted">Standard expenses within designated limits.</td>
                            <td>
                                <span class="invite-active pb-1 pt-1 pl-2 pr-2 text-xs font-bold rounded-full bg-blue-100 text-blue-800">Role: Manager</span>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div class="flex items-center gap-2">
                                    <span class="font-medium text-gray-700">&gt;</span>
                                    <input type="number" id="threshold-amount" class="form-input" style="width: 120px;" 
                                           value="${amountThreshold}" min="1" step="1" oninput="ApprovalConfigPage.updateDisplay()">
                                    <span class="font-medium text-gray-700">${currency}</span>
                                </div>
                            </td>
                            <td class="text-sm text-muted">High value expenses requiring higher authority approval.</td>
                            <td>
                                <span class="invite-active pb-1 pt-1 pl-2 pr-2 text-xs font-bold rounded-full bg-purple-100 text-purple-800">Role: Admin</span>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <div class="mt-4 form-hint">
                    Dynamic Approval Rules: Admin defines the threshold amount. 
                    Expenses exceeding this threshold will go directly to the designated higher authority.
                </div>
            </div>

            <div id="config-error" class="form-error hidden mb-4"></div>

            <div class="flex gap-3" style="justify-content: flex-end;">
                <button class="btn btn-primary btn-lg" onclick="ApprovalConfigPage.saveConfig()">
                    💾 Save Rules
                </button>
            </div>
        </div>`;
    },

    updateDisplay() {
        const val = document.getElementById('threshold-amount').value || 0;
        document.getElementById('display-threshold').textContent = val;
    },

    async saveConfig() {
        const errorEl = document.getElementById('config-error');
        errorEl.classList.add('hidden');

        const amountThreshold = parseFloat(document.getElementById('threshold-amount').value) || 5000;

        // We map this visual config to our backend chain format.
        // Mode = 'hybrid'
        // Step 1 = Manager (just generic manager step)
        // Rule 1 = Amount threshold (rule_type: 'amount', amount_threshold: amountThreshold)
        
        try {
            await API.saveChain({
                name: 'Standard Amount-based Rules',
                mode: 'hybrid',
                steps: [
                    { role_label: 'Manager', assigned_user_id: null }
                ],
                rules: [
                    { rule_type: 'amount', amount_threshold: amountThreshold }
                ],
            });
            Utils.toast('Approval workflow saved!', 'success');
            App.navigate(window.location.hash);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    },
};
