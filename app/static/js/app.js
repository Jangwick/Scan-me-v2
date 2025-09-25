/**
 * ScanMe Attendance System - Main JavaScript
 * Handles interactive features, AJAX requests, and real-time updates
 */

// Global configuration
const ScanMe = {
    config: {
        refreshInterval: 30000, // 30 seconds
        animationDuration: 300,
        autoHideAlerts: true,
        alertHideDelay: 5000
    },
    
    // Utility functions
    utils: {
        // Format datetime for display
        formatDateTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleString();
        },
        
        // Format time only
        formatTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleTimeString();
        },
        
        // Show loading state
        showLoading(element) {
            element.classList.add('loading');
        },
        
        // Hide loading state
        hideLoading(element) {
            element.classList.remove('loading');
        },
        
        // Show notification
        showNotification(message, type = 'info') {
            const alertHTML = `
                <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                    <i class="fas fa-${this.getIconForType(type)} me-2"></i>
                    ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            
            // Add to page
            const container = document.querySelector('.container') || document.querySelector('.container-fluid');
            if (container) {
                container.insertAdjacentHTML('afterbegin', alertHTML);
                
                // Auto-hide after delay
                if (ScanMe.config.autoHideAlerts) {
                    setTimeout(() => {
                        const alerts = container.querySelectorAll('.alert');
                        if (alerts.length > 0) {
                            alerts[0].querySelector('.btn-close')?.click();
                        }
                    }, ScanMe.config.alertHideDelay);
                }
            }
        },
        
        // Get icon for notification type
        getIconForType(type) {
            const icons = {
                'success': 'check-circle',
                'danger': 'exclamation-triangle',
                'warning': 'exclamation-circle',
                'info': 'info-circle'
            };
            return icons[type] || 'info-circle';
        },
        
        // Debounce function calls
        debounce(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        
        // Copy text to clipboard
        copyToClipboard(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    ScanMe.utils.showNotification('Copied to clipboard!', 'success');
                });
            } else {
                // Fallback for older browsers
                const textArea = document.createElement('textarea');
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                ScanMe.utils.showNotification('Copied to clipboard!', 'success');
            }
        }
    },
    
    // Scanner functionality
    scanner: {
        isScanning: false,
        currentRoom: null,
        
        // Initialize scanner
        init() {
            this.bindEvents();
            this.setupQRScanner();
        },
        
        // Bind event listeners
        bindEvents() {
            // Room selection change
            const roomSelect = document.getElementById('room-select');
            if (roomSelect) {
                roomSelect.addEventListener('change', (e) => {
                    this.currentRoom = e.target.value;
                    this.updateRoomInfo();
                });
            }
            
            // Manual QR input
            const qrInput = document.getElementById('qr-input');
            if (qrInput) {
                qrInput.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.processQRCode(qrInput.value);
                        qrInput.value = '';
                    }
                });
            }
            
            // Scan button
            const scanBtn = document.getElementById('scan-btn');
            if (scanBtn) {
                scanBtn.addEventListener('click', () => {
                    const qrInput = document.getElementById('qr-input');
                    if (qrInput && qrInput.value) {
                        this.processQRCode(qrInput.value);
                        qrInput.value = '';
                    }
                });
            }
            
            // File upload for QR image scanning
            const qrFileInput = document.getElementById('qr-file');
            if (qrFileInput) {
                qrFileInput.addEventListener('change', (e) => {
                    if (e.target.files.length > 0) {
                        this.scanQRFromImage(e.target.files[0]);
                    }
                });
            }
        },
        
        // Setup QR code scanner (if using camera)
        setupQRScanner() {
            // This would initialize camera-based QR scanning
            // Implementation would depend on chosen QR scanning library
            console.log('QR Scanner initialized');
        },
        
        // Process QR code data
        async processQRCode(qrData) {
            if (!qrData || !this.currentRoom) {
                ScanMe.utils.showNotification('Please select a room and scan a QR code', 'warning');
                return;
            }
            
            this.isScanning = true;
            const scanBtn = document.getElementById('scan-btn');
            if (scanBtn) ScanMe.utils.showLoading(scanBtn);
            
            try {
                const response = await fetch('/scanner/api/scan-qr', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        qr_data: qrData,
                        room_id: this.currentRoom,
                        session_id: document.getElementById('session-select')?.value || null
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.displayScanResult(result);
                    ScanMe.utils.showNotification(result.message, 'success');
                    this.updateScanStats();
                } else {
                    ScanMe.utils.showNotification(result.error, 'danger');
                }
            } catch (error) {
                console.error('Scan error:', error);
                ScanMe.utils.showNotification('Scan failed. Please try again.', 'danger');
            } finally {
                this.isScanning = false;
                if (scanBtn) ScanMe.utils.hideLoading(scanBtn);
            }
        },
        
        // Scan QR from uploaded image
        async scanQRFromImage(file) {
            if (!this.currentRoom) {
                ScanMe.utils.showNotification('Please select a room first', 'warning');
                return;
            }
            
            const formData = new FormData();
            formData.append('image', file);
            formData.append('room_id', this.currentRoom);
            formData.append('session_id', document.getElementById('session-select')?.value || '');
            
            try {
                const response = await fetch('/scanner/api/scan-image', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.displayScanResult(result);
                    ScanMe.utils.showNotification(result.message, 'success');
                } else {
                    ScanMe.utils.showNotification(result.error, 'danger');
                }
            } catch (error) {
                console.error('Image scan error:', error);
                ScanMe.utils.showNotification('Image scan failed', 'danger');
            }
        },
        
        // Display scan result
        displayScanResult(result) {
            const resultContainer = document.getElementById('scan-result');
            if (!resultContainer) return;
            
            const student = result.student;
            const scanInfo = result.scan_info;
            
            const statusClass = scanInfo.is_late ? 'warning' : scanInfo.is_duplicate ? 'info' : 'success';
            const statusIcon = scanInfo.is_late ? 'clock' : scanInfo.is_duplicate ? 'copy' : 'check-circle';
            
            resultContainer.innerHTML = `
                <div class="card border-${statusClass}">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="student-avatar">
                                ${student.name.charAt(0)}
                            </div>
                            <div>
                                <h5 class="mb-1">${student.name}</h5>
                                <div class="text-muted">${student.student_no} • ${student.department}</div>
                            </div>
                        </div>
                        
                        <div class="row text-center">
                            <div class="col-md-3">
                                <div class="text-muted small">Section</div>
                                <div class="fw-bold">${student.section}</div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-muted small">Year Level</div>
                                <div class="fw-bold">${student.year_level}</div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-muted small">Scan Time</div>
                                <div class="fw-bold">${ScanMe.utils.formatTime(scanInfo.scan_time)}</div>
                            </div>
                            <div class="col-md-3">
                                <div class="text-muted small">Status</div>
                                <div>
                                    <span class="badge bg-${statusClass}">
                                        <i class="fas fa-${statusIcon} me-1"></i>
                                        ${scanInfo.is_late ? 'Late' : scanInfo.is_duplicate ? 'Duplicate' : 'On Time'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Scroll to result
            resultContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });
        },
        
        // Update room information
        async updateRoomInfo() {
            if (!this.currentRoom) return;
            
            try {
                const response = await fetch(`/scanner/room-info/${this.currentRoom}`);
                const roomInfo = await response.json();
                
                if (!roomInfo.error) {
                    this.displayRoomInfo(roomInfo);
                }
            } catch (error) {
                console.error('Error fetching room info:', error);
            }
        },
        
        // Display room information
        displayRoomInfo(roomInfo) {
            const infoContainer = document.getElementById('room-info');
            if (!infoContainer) return;
            
            const occupancyPercentage = roomInfo.occupancy_percentage || 0;
            const statusClass = occupancyPercentage >= 80 ? 'danger' : occupancyPercentage >= 50 ? 'warning' : 'success';
            
            infoContainer.innerHTML = `
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-title">${roomInfo.name}</h6>
                        <div class="mb-2">
                            <small class="text-muted">${roomInfo.building} • Capacity: ${roomInfo.capacity}</small>
                        </div>
                        
                        <div class="mb-3">
                            <div class="d-flex justify-content-between mb-1">
                                <small>Current Occupancy</small>
                                <small>${roomInfo.current_occupancy}/${roomInfo.capacity} (${occupancyPercentage}%)</small>
                            </div>
                            <div class="progress" style="height: 6px;">
                                <div class="progress-bar bg-${statusClass}" style="width: ${occupancyPercentage}%"></div>
                            </div>
                        </div>
                        
                        ${roomInfo.recent_visitors?.length ? `
                            <div>
                                <small class="text-muted fw-bold">Recent Visitors:</small>
                                <div class="mt-1">
                                    ${roomInfo.recent_visitors.map(visitor => `
                                        <div class="d-flex justify-content-between align-items-center py-1">
                                            <small>${visitor.student_name}</small>
                                            <small class="text-muted">${visitor.scan_time}</small>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        },
        
        // Update scan statistics
        async updateScanStats() {
            try {
                const response = await fetch('/scanner/api/recent-scans?limit=5');
                const result = await response.json();
                
                if (result.success) {
                    this.displayRecentScans(result.scans);
                }
            } catch (error) {
                console.error('Error updating scan stats:', error);
            }
        },
        
        // Display recent scans
        displayRecentScans(scans) {
            const container = document.getElementById('recent-scans');
            if (!container || !scans.length) return;
            
            container.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">Recent Scans</h6>
                    </div>
                    <div class="card-body p-0">
                        ${scans.map(scan => `
                            <div class="d-flex align-items-center p-3 border-bottom">
                                <div class="student-avatar" style="width: 40px; height: 40px; font-size: 1rem;">
                                    ${scan.student.name.charAt(0)}
                                </div>
                                <div class="ms-3 flex-grow-1">
                                    <div class="fw-bold">${scan.student.name}</div>
                                    <small class="text-muted">
                                        ${scan.room.name} • ${ScanMe.utils.formatTime(scan.scan_time)}
                                        ${scan.is_late ? '<span class="badge bg-warning ms-1">Late</span>' : ''}
                                    </small>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
    },
    
    // Forms functionality
    forms: {
        // Initialize form enhancements
        init() {
            this.setupValidation();
            this.setupAsyncValidation();
            this.setupFileUploads();
        },
        
        // Setup real-time form validation
        setupValidation() {
            const forms = document.querySelectorAll('form[data-validate]');
            forms.forEach(form => {
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    input.addEventListener('blur', () => this.validateField(input));
                    input.addEventListener('input', ScanMe.utils.debounce(() => this.validateField(input), 500));
                });
            });
        },
        
        // Setup async validation (username/email checking)
        setupAsyncValidation() {
            const usernameInput = document.getElementById('username');
            if (usernameInput) {
                usernameInput.addEventListener('blur', ScanMe.utils.debounce(() => {
                    this.checkUsernameAvailability(usernameInput.value);
                }, 500));
            }
            
            const emailInput = document.getElementById('email');
            if (emailInput) {
                emailInput.addEventListener('blur', ScanMe.utils.debounce(() => {
                    this.checkEmailAvailability(emailInput.value);
                }, 500));
            }
        },
        
        // Validate individual field
        validateField(field) {
            const value = field.value.trim();
            let isValid = true;
            let message = '';
            
            // Required validation
            if (field.hasAttribute('required') && !value) {
                isValid = false;
                message = 'This field is required';
            }
            
            // Email validation
            if (field.type === 'email' && value) {
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) {
                    isValid = false;
                    message = 'Please enter a valid email address';
                }
            }
            
            // Password validation
            if (field.type === 'password' && value) {
                if (value.length < 8) {
                    isValid = false;
                    message = 'Password must be at least 8 characters';
                }
            }
            
            this.updateFieldValidation(field, isValid, message);
        },
        
        // Update field validation state
        updateFieldValidation(field, isValid, message) {
            field.classList.remove('is-valid', 'is-invalid');
            
            const feedback = field.parentNode.querySelector('.invalid-feedback, .valid-feedback');
            if (feedback) feedback.remove();
            
            if (message) {
                field.classList.add(isValid ? 'is-valid' : 'is-invalid');
                
                const feedbackDiv = document.createElement('div');
                feedbackDiv.className = isValid ? 'valid-feedback' : 'invalid-feedback';
                feedbackDiv.textContent = message;
                field.parentNode.appendChild(feedbackDiv);
            }
        },
        
        // Check username availability
        async checkUsernameAvailability(username) {
            if (!username || username.length < 3) return;
            
            try {
                const response = await fetch(`/auth/check-username?username=${encodeURIComponent(username)}`);
                const result = await response.json();
                
                const usernameField = document.getElementById('username');
                this.updateFieldValidation(usernameField, result.available, result.message);
            } catch (error) {
                console.error('Username check error:', error);
            }
        },
        
        // Check email availability
        async checkEmailAvailability(email) {
            if (!email || !email.includes('@')) return;
            
            try {
                const response = await fetch(`/auth/check-email?email=${encodeURIComponent(email)}`);
                const result = await response.json();
                
                const emailField = document.getElementById('email');
                this.updateFieldValidation(emailField, result.available, result.message);
            } catch (error) {
                console.error('Email check error:', error);
            }
        },
        
        // Setup file upload enhancements
        setupFileUploads() {
            const fileInputs = document.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                input.addEventListener('change', (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        this.displayFileInfo(input, file);
                    }
                });
            });
        },
        
        // Display file information
        displayFileInfo(input, file) {
            const info = document.createElement('small');
            info.className = 'text-muted mt-1 d-block';
            info.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            
            const existing = input.parentNode.querySelector('small');
            if (existing) existing.remove();
            
            input.parentNode.appendChild(info);
        }
    },
    
    // Tables functionality
    tables: {
        // Initialize table enhancements
        init() {
            this.setupSorting();
            this.setupFiltering();
            this.setupPagination();
        },
        
        // Setup table sorting
        setupSorting() {
            const sortableTables = document.querySelectorAll('table[data-sortable]');
            sortableTables.forEach(table => {
                const headers = table.querySelectorAll('th[data-sort]');
                headers.forEach(header => {
                    header.style.cursor = 'pointer';
                    header.addEventListener('click', () => this.sortTable(table, header));
                });
            });
        },
        
        // Sort table by column
        sortTable(table, header) {
            const column = header.getAttribute('data-sort');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            const isAscending = !header.classList.contains('sort-asc');
            
            // Clear previous sort classes
            table.querySelectorAll('th').forEach(th => th.classList.remove('sort-asc', 'sort-desc'));
            header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
            
            rows.sort((a, b) => {
                const aVal = a.cells[header.cellIndex].textContent.trim();
                const bVal = b.cells[header.cellIndex].textContent.trim();
                
                const comparison = aVal.localeCompare(bVal, undefined, { numeric: true });
                return isAscending ? comparison : -comparison;
            });
            
            rows.forEach(row => tbody.appendChild(row));
        },
        
        // Setup table filtering
        setupFiltering() {
            const filterInputs = document.querySelectorAll('[data-table-filter]');
            filterInputs.forEach(input => {
                input.addEventListener('input', ScanMe.utils.debounce(() => {
                    this.filterTable(input);
                }, 300));
            });
        },
        
        // Filter table rows
        filterTable(input) {
            const tableId = input.getAttribute('data-table-filter');
            const table = document.getElementById(tableId);
            if (!table) return;
            
            const filter = input.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        },
        
        // Setup pagination
        setupPagination() {
            const paginatedTables = document.querySelectorAll('[data-paginate]');
            paginatedTables.forEach(table => {
                this.createPagination(table);
            });
        },
        
        // Create pagination controls
        createPagination(table) {
            const perPage = parseInt(table.getAttribute('data-paginate')) || 10;
            const rows = table.querySelectorAll('tbody tr');
            const totalPages = Math.ceil(rows.length / perPage);
            
            if (totalPages <= 1) return;
            
            const paginationContainer = document.createElement('nav');
            paginationContainer.className = 'mt-3';
            
            const pagination = document.createElement('ul');
            pagination.className = 'pagination justify-content-center';
            
            for (let i = 1; i <= totalPages; i++) {
                const li = document.createElement('li');
                li.className = 'page-item';
                
                const a = document.createElement('a');
                a.className = 'page-link';
                a.href = '#';
                a.textContent = i;
                
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.showPage(table, i, perPage);
                    pagination.querySelector('.active')?.classList.remove('active');
                    li.classList.add('active');
                });
                
                li.appendChild(a);
                pagination.appendChild(li);
            }
            
            paginationContainer.appendChild(pagination);
            table.parentNode.appendChild(paginationContainer);
            
            // Show first page
            this.showPage(table, 1, perPage);
            pagination.firstChild.classList.add('active');
        },
        
        // Show specific page
        showPage(table, page, perPage) {
            const rows = table.querySelectorAll('tbody tr');
            const start = (page - 1) * perPage;
            const end = start + perPage;
            
            rows.forEach((row, index) => {
                row.style.display = (index >= start && index < end) ? '' : 'none';
            });
        }
    }
};

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ScanMe.scanner.init();
    ScanMe.forms.init();
    ScanMe.tables.init();
    
    console.log('ScanMe system initialized');
});

// Export for global access
window.ScanMe = ScanMe;