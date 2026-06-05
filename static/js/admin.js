/* =============================================
   Smart AI Assistant — Admin Dashboard Scripts
   ============================================= */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh stats every 60 seconds
    setInterval(refreshStats, 60000);
});

async function refreshStats() {
    try {
        const response = await fetch('/api/admin/stats');
        if (!response.ok) return;

        const data = await response.json();

        // Update stat values if elements exist
        const statValues = document.querySelectorAll('.stat-value');
        if (statValues.length >= 4) {
            statValues[0].textContent = data.total_users;
            statValues[1].textContent = data.total_chats;
            statValues[2].textContent = data.total_messages;
            statValues[3].textContent = data.total_tokens.toLocaleString();
        }
    } catch (error) {
        console.error('Stats refresh error:', error);
    }
}

async function changeUserRole(userId, newRole) {
    const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || '';

    try {
        const response = await fetch(`/admin/users/${userId}/role`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ role: newRole }),
        });

        const data = await response.json();
        if (data.success) {
            showToast(`User role changed to ${data.role}.`, 'success');
            location.reload();
        } else {
            showToast(data.error || 'Failed to change role.', 'danger');
        }
    } catch (error) {
        showToast('Failed to change role.', 'danger');
    }
}
