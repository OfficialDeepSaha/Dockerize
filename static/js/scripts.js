// Rail Sathi UI Scripts

document.addEventListener('DOMContentLoaded', function() {
    // Initialize date pickers
    const datePickers = document.querySelectorAll('.date-picker');
    if (datePickers) {
        datePickers.forEach(input => {
            input.type = 'date';
        });
    }

    // File upload preview
    const fileInputs = document.querySelectorAll('.file-upload');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const previewContainer = document.getElementById(`${this.id}-preview`);
            if (!previewContainer) return;
            
            previewContainer.innerHTML = '';
            
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                const reader = new FileReader();
                
                const mediaItem = document.createElement('div');
                mediaItem.className = 'media-item';
                
                reader.onload = function(e) {
                    if (file.type.startsWith('image/')) {
                        const img = document.createElement('img');
                        img.src = e.target.result;
                        mediaItem.appendChild(img);
                    } else {
                        const fileIcon = document.createElement('div');
                        fileIcon.className = 'file-icon';
                        fileIcon.textContent = file.name.split('.').pop().toUpperCase();
                        mediaItem.appendChild(fileIcon);
                    }
                    
                    const removeBtn = document.createElement('div');
                    removeBtn.className = 'remove-btn';
                    removeBtn.innerHTML = '&times;';
                    removeBtn.addEventListener('click', function() {
                        mediaItem.remove();
                        // Note: This doesn't actually remove the file from the input
                        // For a complete solution, you'd need to use a more complex approach
                    });
                    
                    mediaItem.appendChild(removeBtn);
                };
                
                reader.readAsDataURL(file);
                previewContainer.appendChild(mediaItem);
            }
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Search complaint by ID
    const searchForm = document.getElementById('search-complaint-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const complaintId = document.getElementById('search-complaint-id').value;
            if (complaintId) {
                window.location.href = `/items/complaint/${complaintId}`;
            }
        });
    }

    // Search complaints by date and mobile
    const searchDateForm = document.getElementById('search-date-form');
    if (searchDateForm) {
        searchDateForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const date = document.getElementById('search-date').value;
            const mobile = document.getElementById('search-mobile').value;
            
            if (date && mobile) {
                window.location.href = `/items/complaints/${date}?mobile_number=${mobile}`;
            } else {
                alert('Please enter both date and mobile number');
            }
        });
    }

    // Delete complaint confirmation
    const deleteButtons = document.querySelectorAll('.delete-complaint-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this complaint?')) {
                event.preventDefault();
            }
        });
    });

    // Delete media confirmation
    const deleteMediaButtons = document.querySelectorAll('.delete-media-btn');
    deleteMediaButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this media file?')) {
                event.preventDefault();
            }
        });
    });

    // Show alert messages
    const showAlert = (message, type = 'info') => {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="close" data-dismiss="alert" aria-label="Close">
                <span aria-hidden="true">&times;</span>
            </button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto dismiss after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => {
                alert.remove();
            }, 150);
        }, 5000);
    };

    // Check for message in URL query params
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    const messageType = urlParams.get('type') || 'info';
    
    if (message) {
        showAlert(decodeURIComponent(message), messageType);
    }
});

// Function to handle complaint form submission
function submitComplaintForm(formId, method, redirectUrl) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        if (!form.checkValidity()) {
            form.classList.add('was-validated');
            return;
        }
        
        const formData = new FormData(form);
        
        try {
            const response = await fetch(form.action, {
                method: method,
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                window.location.href = redirectUrl + '?message=' + encodeURIComponent('Operation completed successfully') + '&type=success';
            } else {
                showAlert('Error: ' + (result.detail || 'Something went wrong'), 'danger');
            }
        } catch (error) {
            showAlert('Error: ' + error.message, 'danger');
        }
    });
}
