/**
 * User Management Page (Admin view users list)
 */
const UsersPage = {
    users: [],
    managers: [],

    async render() {
        try {
            const [userData, managerData] = await Promise.all([
                API.getUsers(),
                API.getManagers(),
            ]);
            this.users = userData.users;
            this.managers = managerData.managers;
        } catch (err) {
            return `<div class="form-error">Failed to load users: ${err.message}</div>`;
        }

        const companyName = App.currentCompany?.name || 'Company';

        return `
        <div>
            <div class="flex items-center justify-between mb-6">
                <h1 class="page-title">User Management</h1>
                <button class="btn btn-primary" onclick="UsersPage.showAddModal()">
                    ➕ Add Member
                </button>
            </div>

            ${Components.dataTable([
                { label: 'Name', render: r => `
                    <div class="flex items-center gap-3">
                        <div class="user-avatar">${Utils.initials(r.name)}</div>
                        <div>
                            <div class="font-medium">${Utils.escapeHtml(r.name)}</div>
                            <div class="text-xs text-muted">${Utils.escapeHtml(r.email)}</div>
                        </div>
                    </div>` },
                { label: 'Role', render: r => Components.rolePill(r.role) },
                { label: 'Company', render: () => Utils.escapeHtml(companyName) },
                { label: 'Status', render: r => `<span class="invite-active pb-1 pt-1 pl-2 pr-2 text-xs font-bold rounded-full bg-green-100 text-green-800">Active</span>` },
                { label: 'Actions', render: r => `
                    <div class="flex gap-2">
                        <button class="btn btn-ghost btn-sm" onclick="UsersPage.showEditModal('${r.id}')">Edit</button>
                        <button class="btn btn-ghost btn-sm text-primary" onclick="UsersPage.resetPassword('${r.id}')">Reset password</button>
                    </div>` },
            ], this.users, { emptyMessage: 'No users yet. Add your first team member!' })}
        </div>
        <div id="user-modal-container"></div>`;
    },

    showAddModal() {
        const managerOptions = this.managers.map(m =>
            `<option value="${m.id}">${Utils.escapeHtml(m.name)} (${m.role})</option>`
        ).join('');

        const body = `
            <div class="form-group">
                <label class="form-label">Name</label>
                <input type="text" id="new-user-name" class="form-input" placeholder="Jane Smith" required>
            </div>
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" id="new-user-email" class="form-input" placeholder="jane@company.com" required>
            </div>
            <div class="form-group">
                <label class="form-label">Role</label>
                <select id="new-user-role" class="form-select">
                    <option value="employee">Employee</option>
                    <option value="manager">Manager</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Direct Manager (Optional)</label>
                <select id="new-user-manager" class="form-select">
                    <option value="">None</option>
                    ${managerOptions}
                </select>
            </div>
            <div id="add-user-error" class="form-error hidden"></div>
        `;

        const footer = `
            <button class="btn btn-secondary" onclick="Components.closeModal('add-user-modal')">Cancel</button>
            <button class="btn btn-primary" onclick="UsersPage.handleAdd()">Create Account</button>
        `;

        document.getElementById('user-modal-container').innerHTML =
            Components.modal('add-user-modal', 'Add Team Member', body, footer);
    },

    async handleAdd() {
        const errorEl = document.getElementById('add-user-error');
        errorEl.classList.add('hidden');

        try {
            const result = await API.createUser({
                name: document.getElementById('new-user-name').value,
                email: document.getElementById('new-user-email').value,
                role: document.getElementById('new-user-role').value,
                direct_manager_id: document.getElementById('new-user-manager').value || null,
            });

            Components.closeModal('add-user-modal');
            Utils.toast('User created successfully!', 'success');

            if (result.temp_password) {
                alert("Account Created! Temporary Password: " + result.temp_password + "\n\nPlease copy this and send it to the user.");
            }

            App.navigate(window.location.hash);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    },

    showEditModal(userId) {
        const user = this.users.find(u => u.id === userId);
        if (!user) return;

        const managerOptions = this.managers.map(m =>
            `<option value="${m.id}" ${m.id === user.direct_manager_id ? 'selected' : ''}>${Utils.escapeHtml(m.name)} (${m.role})</option>`
        ).join('');

        const body = `
            <div class="form-group">
                <label class="form-label">Name</label>
                <input type="text" id="edit-user-name" class="form-input" value="${Utils.escapeHtml(user.name)}">
            </div>
            <div class="form-group">
                <label class="form-label">Role</label>
                <select id="edit-user-role" class="form-select">
                    <option value="employee" ${user.role === 'employee' ? 'selected' : ''}>Employee</option>
                    <option value="manager" ${user.role === 'manager' ? 'selected' : ''}>Manager</option>
                    <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Admin</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Direct Manager</label>
                <select id="edit-user-manager" class="form-select">
                    <option value="">None</option>
                    ${managerOptions}
                </select>
            </div>
            <div id="edit-user-error" class="form-error hidden"></div>
        `;

        const footer = `
            <button class="btn btn-secondary" onclick="Components.closeModal('edit-user-modal')">Cancel</button>
            <button class="btn btn-primary" onclick="UsersPage.handleEdit('${userId}')">Save Changes</button>
        `;

        document.getElementById('user-modal-container').innerHTML =
            Components.modal('edit-user-modal', `Edit ${user.name}`, body, footer);
    },

    async handleEdit(userId) {
        const errorEl = document.getElementById('edit-user-error');
        errorEl.classList.add('hidden');

        try {
            await API.updateUser(userId, {
                name: document.getElementById('edit-user-name').value,
                role: document.getElementById('edit-user-role').value,
                direct_manager_id: document.getElementById('edit-user-manager').value || null,
            });

            Components.closeModal('edit-user-modal');
            Utils.toast('User updated!', 'success');
            App.navigate(window.location.hash);
        } catch (err) {
            errorEl.textContent = err.message;
            errorEl.classList.remove('hidden');
        }
    },

    async resetPassword(userId) {
        if (!confirm("Are you sure you want to reset this user's password?")) return;
        
        try {
            const result = await API.resetPassword(userId);
            let msg = "Temporary Password:\n\n" + result.temp_password + "\n\nPlease share this securely.";
            alert(msg);
            Utils.toast('Password reset successfully.', 'success');
        } catch (err) {
            Utils.toast(err.message, 'error');
        }
    },
};
