// WebSocket connection for real-time notifications
let socket;

function initializeWebSocket() {
    socket = new WebSocket(`ws://${window.location.host}/ws`);

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.type === 'notification') {
            showNotification(data.message, data.notificationType);
            updateNotificationBadge();
        } else if (data.type === 'leave_update') {
            updateLeaveStatus(data.leaveId, data.status);
        }
    };

    socket.onclose = function() {
        setTimeout(initializeWebSocket, 3000);
    };
}

function showNotification(message, type = 'info') {
    const notificationContainer = document.getElementById('notification-container');
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
        </div>
    `;
    notificationContainer.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function updateNotificationBadge() {
    fetch('/api/notifications/unread-count')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notification-badge');
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'block';
            } else {
                badge.style.display = 'none';
            }
        });
}

function markNotificationAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    }).then(() => {
        updateNotificationBadge();
    });
}

function updateLeaveStatus(leaveId, status) {
    const leaveRow = document.querySelector(`[data-leave-id="${leaveId}"]`);
    if (leaveRow) {
        const statusCell = leaveRow.querySelector('.leave-status');
        statusCell.textContent = status;
        statusCell.className = `leave-status status-${status.toLowerCase()}`;
    }
}

// Document upload handling
function handleFileUpload(event, leaveId) {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('document', file);
    formData.append('leave_id', leaveId);

    fetch('/api/leaves/upload-document', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Document uploaded successfully', 'success');
            updateDocumentList(leaveId);
        } else {
            showNotification('Failed to upload document', 'error');
        }
    })
    .catch(() => {
        showNotification('Error uploading document', 'error');
    });
}

function updateDocumentList(leaveId) {
    fetch(`/api/leaves/${leaveId}/documents`)
        .then(response => response.json())
        .then(data => {
            const documentList = document.querySelector(`#documents-${leaveId}`);
            if (documentList) {
                documentList.innerHTML = data.documents.map(doc => `
                    <div class="document-item">
                        <a href="${doc.url}" target="_blank">${doc.filename}</a>
                        <button onclick="deleteDocument('${doc.id}', ${leaveId})" class="btn-delete">&times;</button>
                    </div>
                `).join('');
            }
        });
}

function deleteDocument(documentId, leaveId) {
    if (!confirm('Are you sure you want to delete this document?')) return;

    fetch(`/api/documents/${documentId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Document deleted successfully', 'success');
            updateDocumentList(leaveId);
        } else {
            showNotification('Failed to delete document', 'error');
        }
    })
    .catch(() => {
        showNotification('Error deleting document', 'error');
    });
}

// Initialize WebSocket connection when the page loads
document.addEventListener('DOMContentLoaded', initializeWebSocket);