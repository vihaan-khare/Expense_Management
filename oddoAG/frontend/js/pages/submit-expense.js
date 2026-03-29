/**
 * Submit Expense Page
 */
const SubmitExpensePage = {
    currencies: [],
    receiptUrl: null,
    receiptFilepath: null,
    companyCurrency: '',

    async render() {
        const company = App.currentCompany;
        this.companyCurrency = company?.currency_code || 'USD';

        try {
            const { currencies } = await API.getCurrencies();
            this.currencies = currencies;
        } catch { this.currencies = ['USD', 'EUR', 'GBP', 'INR']; }

        const currencyOptions = this.currencies.map(c =>
            `<option value="${c}" ${c === this.companyCurrency ? 'selected' : ''}>${c}</option>`
        ).join('');

        const categories = ['Travel', 'Meals', 'Accommodation', 'Equipment', 'Software', 'Training', 'Marketing', 'Other'];

        return `
        <div style="max-width: 700px; margin: 0 auto;">
            <h1 class="page-title mb-6">Submit New Expense</h1>

            <form class="card" onsubmit="SubmitExpensePage.handleSubmit(event)" id="expense-form">
                <!-- Receipt Upload -->
                <div class="form-group mb-4">
                    <label class="form-label">Receipt (Optional)</label>
                    <div class="file-upload" id="receipt-drop" onclick="document.getElementById('receipt-input').click()">
                        <input type="file" id="receipt-input" accept=".jpg,.jpeg,.png,.pdf" onchange="SubmitExpensePage.handleFileSelect(event)">
                        <div id="receipt-status">
                            <div style="font-size: 2rem; margin-bottom: 8px;">📎</div>
                            <div class="text-sm font-medium">Click to upload receipt</div>
                            <div class="text-xs text-muted mt-2">JPG, PNG, or PDF • Max 5MB</div>
                        </div>
                    </div>
                    <div class="flex gap-2 mt-2 hidden" id="ocr-actions">
                        <button type="button" class="btn btn-secondary btn-sm" onclick="SubmitExpensePage.scanReceipt()">
                            🔍 Scan Receipt (OCR)
                        </button>
                    </div>
                </div>

                <div class="divider"></div>

                <!-- Amount & Currency -->
                <div class="form-row mb-4">
                    <div class="form-group">
                        <label class="form-label" for="expense-amount">Amount</label>
                        <input type="number" id="expense-amount" class="form-input" step="0.01" min="0.01" 
                               placeholder="0.00" required oninput="SubmitExpensePage.onAmountChange()">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="expense-currency">Currency</label>
                        <select id="expense-currency" class="form-select" required onchange="SubmitExpensePage.onCurrencyChange()">
                            ${currencyOptions}
                        </select>
                    </div>
                </div>

                <!-- Conversion Preview -->
                <div id="conversion-preview" class="hidden mb-4"></div>

                <!-- Category -->
                <div class="form-group mb-4">
                    <label class="form-label" for="expense-category">Category</label>
                    <select id="expense-category" class="form-select" required>
                        ${categories.map(c => `<option value="${c}">${Utils.categoryIcon(c)} ${c}</option>`).join('')}
                    </select>
                </div>

                <!-- Description -->
                <div class="form-group mb-4">
                    <label class="form-label" for="expense-description">Description</label>
                    <textarea id="expense-description" class="form-textarea" placeholder="Describe the expense (min 10 characters)..." required minlength="10"></textarea>
                </div>

                <!-- Date -->
                <div class="form-group mb-4">
                    <label class="form-label" for="expense-date">Expense Date</label>
                    <input type="date" id="expense-date" class="form-input" required max="${new Date().toISOString().split('T')[0]}">
                </div>

                <div id="submit-error" class="form-error hidden"></div>

                <div class="form-actions">
                    <button type="button" class="btn btn-secondary" onclick="window.location.hash='#/expenses'">Cancel</button>
                    <button type="submit" class="btn btn-primary" id="submit-btn">Submit Expense</button>
                </div>
            </form>
        </div>`;
    },

    async handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        document.getElementById('receipt-status').innerHTML = `
            <div style="font-size: 2rem; margin-bottom: 8px;">📄</div>
            <div class="text-sm font-medium">${Utils.escapeHtml(file.name)}</div>
            <div class="text-xs text-muted mt-2">Uploading...</div>
        `;
        document.getElementById('receipt-drop').classList.add('has-file');

        try {
            const result = await API.uploadReceipt(file);
            this.receiptUrl = result.receipt_url;
            this.receiptFilepath = result.filepath;

            document.getElementById('receipt-status').innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 8px;">✅</div>
                <div class="text-sm font-medium">${Utils.escapeHtml(file.name)}</div>
                <div class="text-xs text-muted mt-2">Uploaded successfully</div>
            `;

            // Show OCR button for images
            if (file.type.startsWith('image/')) {
                document.getElementById('ocr-actions').classList.remove('hidden');
            }
        } catch (err) {
            document.getElementById('receipt-status').innerHTML = `
                <div style="font-size: 2rem; margin-bottom: 8px;">❌</div>
                <div class="text-sm" style="color: var(--red);">Upload failed: ${err.message}</div>
            `;
            document.getElementById('receipt-drop').classList.remove('has-file');
        }
    },

    async scanReceipt() {
        if (!this.receiptFilepath) {
            Utils.toast('Upload a receipt first', 'warning');
            return;
        }

        const btn = document.querySelector('#ocr-actions button');
        btn.disabled = true;
        btn.textContent = '🔍 Scanning...';

        try {
            const result = await API.scanReceipt(this.receiptFilepath);
            const data = result.data;

            if (data.amount) {
                document.getElementById('expense-amount').value = data.amount;
                document.getElementById('expense-amount').classList.add('ocr-filled');
            }
            if (data.currency) {
                document.getElementById('expense-currency').value = data.currency;
                document.getElementById('expense-currency').classList.add('ocr-filled');
            }
            if (data.suggested_category) {
                document.getElementById('expense-category').value = data.suggested_category;
                document.getElementById('expense-category').classList.add('ocr-filled');
            }
            if (data.merchant_name) {
                document.getElementById('expense-description').value = `Expense at ${data.merchant_name}`;
                document.getElementById('expense-description').classList.add('ocr-filled');
            }
            if (data.date) {
                document.getElementById('expense-date').value = data.date;
                document.getElementById('expense-date').classList.add('ocr-filled');
            }

            Utils.toast('Receipt scanned! Review the auto-filled fields.', 'success');
            this.onCurrencyChange();
        } catch (err) {
            Utils.toast(`OCR failed: ${err.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = '🔍 Scan Receipt (OCR)';
        }
    },

    _conversionDebounce: null,

    onAmountChange() {
        clearTimeout(this._conversionDebounce);
        this._conversionDebounce = setTimeout(() => this._updateConversion(), 300);
    },

    onCurrencyChange() {
        this._updateConversion();
    },

    async _updateConversion() {
        const amount = parseFloat(document.getElementById('expense-amount').value);
        const currency = document.getElementById('expense-currency').value;
        const preview = document.getElementById('conversion-preview');

        if (!amount || currency === this.companyCurrency) {
            preview.classList.add('hidden');
            return;
        }

        preview.classList.remove('hidden');
        preview.innerHTML = '<div class="conversion-preview"><span class="loading">Converting...</span></div>';

        try {
            const result = await API.convertCurrency(amount, currency, this.companyCurrency);
            preview.innerHTML = `
                <div class="conversion-preview">
                    💱 ${Utils.formatCurrency(amount, currency)} = <strong>${Utils.formatCurrency(result.converted_amount, this.companyCurrency)}</strong>
                </div>`;
        } catch {
            preview.innerHTML = '<div class="conversion-preview" style="color: var(--red);">Conversion failed</div>';
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const btn = document.getElementById('submit-btn');
        const errorEl = document.getElementById('submit-error');
        errorEl.classList.add('hidden');

        btn.disabled = true;
        btn.textContent = 'Submitting...';

        try {
            await API.createExpense({
                amount: parseFloat(document.getElementById('expense-amount').value),
                currency: document.getElementById('expense-currency').value,
                category: document.getElementById('expense-category').value,
                description: document.getElementById('expense-description').value,
                expense_date: document.getElementById('expense-date').value,
                receipt_url: this.receiptUrl,
                ocr_autofilled: document.querySelector('.ocr-filled') !== null,
            });

            Utils.toast('Expense submitted! 🎉', 'success');
            window.location.hash = '#/expenses';
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Submit Expense';
        }
    },
};
