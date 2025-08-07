/**
 * Common JavaScript functions for Log Analyzer Frontend
 */

// Global utilities and common functions
const LogAnalyzer = {
    // Configuration
    config: {
        apiBaseUrl: '/api',
        alertTimeout: 5000,
        maxFileSize: 16 * 1024 * 1024, // 16MB
        allowedExtensions: ['.log', '.txt']
    },

    // Utility functions
    utils: {
        /**
         * Format file size in human readable format
         */
        formatFileSize: function(bytes) {
            if (typeof bytes === 'string') return bytes;
            if (bytes === 0) return '0 Bytes';
            
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        },

        /**
         * Format timestamp for display
         */
        formatTimestamp: function(timestamp) {
            if (!timestamp) return 'Unknown';
            return new Date(timestamp).toLocaleString();
        },

        /**
         * Escape HTML to prevent XSS
         */
        escapeHtml: function(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        /**
         * Generate unique ID
         */
        generateId: function() {
            return 'id-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        },

        /**
         * Validate file extension
         */
        isValidFileType: function(filename) {
            const ext = filename.toLowerCase().substr(filename.lastIndexOf('.'));
            return LogAnalyzer.config.allowedExtensions.includes(ext);
        },

        /**
         * Copy text to clipboard
         */
        copyToClipboard: function(text) {
            if (navigator.clipboard && window.isSecureContext) {
                return navigator.clipboard.writeText(text);
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                return new Promise((resolve, reject) => {
                    if (document.execCommand('copy')) {
                        resolve();
                    } else {
                        reject();
                    }
                    document.body.removeChild(textArea);
                });
            }
        }
    },

    // API functions
    api: {
        /**
         * Make API request with error handling
         */
        request: async function(endpoint, options = {}) {
            const url = LogAnalyzer.config.apiBaseUrl + endpoint;
            
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                },
                ...options
            };

            try {
                const response = await fetch(url, defaultOptions);
                const data = await response.json();
                
                if (!response.ok) {
                    throw new Error(data.error || `HTTP ${response.status}`);
                }
                
                return data;
            } catch (error) {
                console.error('API Request failed:', error);
                throw error;
            }
        },

        /**
         * Upload file with progress tracking
         */
        uploadFile: function(file, endpoint, onProgress = null) {
            return new Promise((resolve, reject) => {
                const formData = new FormData();
                formData.append('file', file);

                const xhr = new XMLHttpRequest();

                if (onProgress) {
                    xhr.upload.addEventListener('progress', (e) => {
                        if (e.lengthComputable) {
                            const percentComplete = (e.loaded / e.total) * 100;
                            onProgress(percentComplete);
                        }
                    });
                }

                xhr.addEventListener('load', () => {
                    if (xhr.status === 200) {
                        try {
                            const response = JSON.parse(xhr.responseText);
                            resolve(response);
                        } catch (error) {
                            reject(new Error('Invalid JSON response'));
                        }
                    } else {
                        try {
                            const error = JSON.parse(xhr.responseText);
                            reject(new Error(error.error || `HTTP ${xhr.status}`));
                        } catch {
                            reject(new Error(`HTTP ${xhr.status}`));
                        }
                    }
                });

                xhr.addEventListener('error', () => {
                    reject(new Error('Network error'));
                });

                xhr.open('POST', LogAnalyzer.config.apiBaseUrl + endpoint);
                xhr.send(formData);
            });
        }
    },

    // UI functions
    ui: {
        /**
         * Show alert message
         */
        showAlert: function(message, type = 'info', container = 'alert-container', autoHide = true) {
            const alertContainer = document.getElementById(container);
            if (!alertContainer) {
                console.warn('Alert container not found:', container);
                return;
            }

            const alertId = LogAnalyzer.utils.generateId();
            const alertHtml = `
                <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                    ${LogAnalyzer.utils.escapeHtml(message)}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                </div>
            `;
            
            alertContainer.insertAdjacentHTML('beforeend', alertHtml);
            
            if (autoHide) {
                setTimeout(() => {
                    const alert = document.getElementById(alertId);
                    if (alert) {
                        const bsAlert = new bootstrap.Alert(alert);
                        bsAlert.close();
                    }
                }, LogAnalyzer.config.alertTimeout);
            }

            return alertId;
        },

        /**
         * Show loading state for button
         */
        setButtonLoading: function(buttonElement, loading = true, originalText = null) {
            if (loading) {
                buttonElement.dataset.originalText = buttonElement.innerHTML;
                buttonElement.disabled = true;
                buttonElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            } else {
                buttonElement.disabled = false;
                buttonElement.innerHTML = originalText || buttonElement.dataset.originalText || 'Submit';
                delete buttonElement.dataset.originalText;
            }
        },

        /**
         * Show/hide element with optional animation
         */
        toggleElement: function(elementId, show = null, animate = true) {
            const element = document.getElementById(elementId);
            if (!element) return;

            const isCurrentlyVisible = element.style.display !== 'none';
            const shouldShow = show !== null ? show : !isCurrentlyVisible;

            if (animate) {
                if (shouldShow) {
                    element.style.display = 'block';
                    element.style.opacity = '0';
                    element.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        element.style.opacity = '1';
                        element.style.transform = 'translateY(0)';
                    }, 10);
                } else {
                    element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    element.style.opacity = '0';
                    element.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        element.style.display = 'none';
                        element.style.transition = '';
                    }, 300);
                }
            } else {
                element.style.display = shouldShow ? 'block' : 'none';
            }
        },

        /**
         * Create progress bar
         */
        createProgressBar: function(container, percentage = 0) {
            const progressHtml = `
                <div class="progress">
                    <div class="progress-bar" role="progressbar" 
                         style="width: ${percentage}%" 
                         aria-valuenow="${percentage}" 
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${percentage}%
                    </div>
                </div>
            `;
            
            if (typeof container === 'string') {
                container = document.getElementById(container);
            }
            
            container.innerHTML = progressHtml;
            return container.querySelector('.progress-bar');
        },

        /**
         * Update progress bar
         */
        updateProgressBar: function(progressBar, percentage) {
            if (typeof progressBar === 'string') {
                progressBar = document.querySelector(progressBar);
            }
            
            if (progressBar) {
                progressBar.style.width = percentage + '%';
                progressBar.setAttribute('aria-valuenow', percentage);
                progressBar.textContent = Math.round(percentage) + '%';
            }
        },

        /**
         * Create modal programmatically
         */
        createModal: function(title, content, options = {}) {
            const modalId = LogAnalyzer.utils.generateId();
            const modalHtml = `
                <div class="modal fade" id="${modalId}" tabindex="-1">
                    <div class="modal-dialog ${options.size || ''}">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">${LogAnalyzer.utils.escapeHtml(title)}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
                                ${content}
                            </div>
                            ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHtml);
            
            const modal = new bootstrap.Modal(document.getElementById(modalId));
            
            // Auto-remove modal from DOM when hidden
            document.getElementById(modalId).addEventListener('hidden.bs.modal', () => {
                document.getElementById(modalId).remove();
            });
            
            return modal;
        }
    },

    // Validation functions
    validation: {
        /**
         * Validate required fields
         */
        validateRequired: function(fields) {
            const errors = [];
            
            for (const [name, value] of Object.entries(fields)) {
                if (!value || (typeof value === 'string' && value.trim() === '')) {
                    errors.push(`${name} is required`);
                }
            }
            
            return errors;
        },

        /**
         * Validate file
         */
        validateFile: function(file) {
            const errors = [];
            
            if (!file) {
                errors.push('No file selected');
                return errors;
            }
            
            if (!LogAnalyzer.utils.isValidFileType(file.name)) {
                errors.push(`Invalid file type. Allowed: ${LogAnalyzer.config.allowedExtensions.join(', ')}`);
            }
            
            if (file.size > LogAnalyzer.config.maxFileSize) {
                errors.push(`File size exceeds ${LogAnalyzer.utils.formatFileSize(LogAnalyzer.config.maxFileSize)} limit`);
            }
            
            return errors;
        }
    }
};

// Initialize common functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Add global error handler for unhandled promise rejections
    window.addEventListener('unhandledrejection', function(event) {
        console.error('Unhandled promise rejection:', event.reason);
        LogAnalyzer.ui.showAlert(
            'An unexpected error occurred. Please check the console for details.',
            'danger'
        );
    });

    // Add global error handler for JavaScript errors
    window.addEventListener('error', function(event) {
        console.error('JavaScript error:', event.error);
        LogAnalyzer.ui.showAlert(
            'A JavaScript error occurred. Please refresh the page and try again.',
            'danger'
        );
    });

    // Check system health periodically
    if (document.getElementById('health-status')) {
        checkSystemHealth();
        setInterval(checkSystemHealth, 30000); // Check every 30 seconds
    }
});

/**
 * Check system health and update status indicator
 */
function checkSystemHealth() {
    LogAnalyzer.api.request('/health')
        .then(data => {
            const statusElement = document.getElementById('health-status');
            if (statusElement) {
                const isHealthy = data.status === 'healthy';
                statusElement.innerHTML = `
                    <i class="fas fa-circle ${isHealthy ? 'text-success' : 'text-danger'}"></i> 
                    ${isHealthy ? 'Online' : 'Offline'}
                `;
            }
        })
        .catch(error => {
            console.warn('Health check failed:', error);
            const statusElement = document.getElementById('health-status');
            if (statusElement) {
                statusElement.innerHTML = '<i class="fas fa-circle text-danger"></i> Offline';
            }
        });
}

// Export for use in other scripts
window.LogAnalyzer = LogAnalyzer;