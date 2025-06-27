// Delete Subject
document.querySelectorAll('.delete-subject').forEach(btn => {
    btn.addEventListener('click', function() {
        const subjectId = this.dataset.id;
        if (confirm('Are you sure you want to permanently delete this subject?')) {
            fetch(`/subjects/${subjectId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                }
            })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Error deleting subject');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Failed to delete subject');
            });
        }
    });
});

// Edit Subject Redirect
document.querySelectorAll('.edit-subject').forEach(btn => {
    btn.addEventListener('click', function() {
        const subjectId = this.dataset.id;
        window.location.href = `/subjects/${subjectId}/edit`;
    });
});

// Flash Message Auto-Close
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        });
    }, 5000);
});

// Progress Bar Animation
document.querySelectorAll('.progress-bar').forEach(bar => {
    const width = bar.style.width;
    bar.style.width = '0';
    setTimeout(() => bar.style.width = width, 100);
});

// Start Study Button Notification
document.addEventListener('DOMContentLoaded', () => {
    const startStudyBtn = document.getElementById('start-study-btn');

    if (startStudyBtn) {
        startStudyBtn.addEventListener('click', () => {
            // Create notification div
            const notification = document.createElement('div');
            notification.className = 'alert alert-success start-study-notification';
            notification.textContent = 'Study session started!';

            // Style notification (you can customize this)
            notification.style.position = 'fixed';
            notification.style.top = '20px';
            notification.style.right = '20px';
            notification.style.zIndex = '1050';
            notification.style.minWidth = '200px';
            notification.style.textAlign = 'center';
            notification.style.opacity = '1';
            notification.style.transition = 'opacity 0.5s ease';

            // Add notification to body
            document.body.appendChild(notification);

            // Remove notification after 1 second
            setTimeout(() => {
                notification.style.opacity = '0';
                setTimeout(() => notification.remove(), 500);
            }, 1000);
        });
    }
});
