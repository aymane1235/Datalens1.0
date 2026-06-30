// Auto-hide flash messages
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('primaryNav');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            const open = navMenu.classList.toggle('is-open');
            navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            navToggle.setAttribute('aria-label', open ? 'Fermer le menu' : 'Ouvrir le menu');
        });
        document.addEventListener('click', function(e) {
            if (!navMenu.classList.contains('is-open')) return;
            if (navToggle.contains(e.target) || navMenu.contains(e.target)) return;
            navMenu.classList.remove('is-open');
            navToggle.setAttribute('aria-expanded', 'false');
            navToggle.setAttribute('aria-label', 'Ouvrir le menu');
        });
    }

    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease';
            
            setTimeout(function() {
                message.remove();
            }, 500);
        }, 5000);
    });
});

// Form validation helpers
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;
    
    inputs.forEach(function(input) {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');
            
            // Remove error class on input
            input.addEventListener('input', function() {
                if (input.value.trim()) {
                    input.classList.remove('error');
                }
            });
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

// Password confirmation validation
function validatePasswordConfirmation() {
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    
    if (!password || !confirmPassword) return;
    
    function checkPasswords() {
        if (password.value !== confirmPassword.value) {
            confirmPassword.setCustomValidity('Les mots de passe ne correspondent pas');
        } else {
            confirmPassword.setCustomValidity('');
        }
    }
    
    password.addEventListener('input', checkPasswords);
    confirmPassword.addEventListener('input', checkPasswords);
}

// File upload validation
function validateFileUpload(inputId, maxSizeMB = 16, allowedTypes = ['csv', 'xlsx', 'xls']) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Check file size
        const maxSizeBytes = maxSizeMB * 1024 * 1024;
        if (file.size > maxSizeBytes) {
            alert(`File size must be less than ${maxSizeMB}MB`);
            input.value = '';
            return;
        }
        
        // Check file type
        const fileExtension = file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileExtension)) {
            alert(`File type must be one of: ${allowedTypes.join(', ')}`);
            input.value = '';
            return;
        }
    });
}

// Table sorting functionality
function makeTableSortable(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const headers = table.querySelectorAll('th');
    
    headers.forEach(function(header, index) {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            sortTable(table, index);
        });
    });
}

function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    const isAscending = table.getAttribute('data-sort-order') !== 'asc';
    table.setAttribute('data-sort-order', isAscending ? 'asc' : 'desc');
    
    rows.sort(function(a, b) {
        const aValue = a.cells[columnIndex].textContent.trim();
        const bValue = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aValue);
        const bNum = parseFloat(bValue);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // String comparison
        return isAscending ? 
            aValue.localeCompare(bValue) : 
            bValue.localeCompare(aValue);
    });
    
    // Clear and re-append sorted rows
    tbody.innerHTML = '';
    rows.forEach(function(row) {
        tbody.appendChild(row);
    });
}

// Copy to clipboard functionality
function copyToClipboard(text, buttonElement) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            showCopyFeedback(buttonElement, true);
        }).catch(function() {
            showCopyFeedback(buttonElement, false);
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            showCopyFeedback(buttonElement, true);
        } catch (err) {
            showCopyFeedback(buttonElement, false);
        }
        
        document.body.removeChild(textArea);
    }
}

function showCopyFeedback(button, success) {
    const originalText = button.textContent;
    button.textContent = success ? 'Copied!' : 'Failed';
    button.style.backgroundColor = success ? '#10b981' : '#ef4444';
    
    setTimeout(function() {
        button.textContent = originalText;
        button.style.backgroundColor = '';
    }, 2000);
}

// Export functionality
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    rows.forEach(function(row) {
        const rowData = [];
        const cells = row.querySelectorAll('td, th');
        
        cells.forEach(function(cell) {
            let cellText = cell.textContent.trim();
            // Escape quotes and wrap in quotes if contains comma
            if (cellText.includes(',') || cellText.includes('"')) {
                cellText = '"' + cellText.replace(/"/g, '""') + '"';
            }
            rowData.push(cellText);
        });
        
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', filename || 'export.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    window.URL.revokeObjectURL(url);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize password confirmation validation
    validatePasswordConfirmation();
    
    // Initialize file upload validation
    validateFileUpload('file');
    
    // Add form validation to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form.id)) {
                e.preventDefault();
                alert('Veuillez remplir tous les champs obligatoires');
            }
        });
    });
    
    // Make tables sortable
    const tables = document.querySelectorAll('.data-table');
    tables.forEach(function(table) {
        if (table.id) {
            makeTableSortable(table.id);
        }
    });
});

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Search functionality for datasets
function searchDatasets(searchTerm, datasetContainer) {
    const datasets = datasetContainer.querySelectorAll('.dataset-card');
    const term = searchTerm.toLowerCase();
    
    datasets.forEach(function(dataset) {
        const title = dataset.querySelector('h3').textContent.toLowerCase();
        const filename = dataset.querySelector('.info-value').textContent.toLowerCase();
        
        if (title.includes(term) || filename.includes(term)) {
            dataset.style.display = 'block';
        } else {
            dataset.style.display = 'none';
        }
    });
}

// Initialize search if search box exists
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('dataset-search');
    const datasetContainer = document.querySelector('.datasets-grid');
    
    if (searchInput && datasetContainer) {
        const debouncedSearch = debounce(function() {
            searchDatasets(searchInput.value, datasetContainer);
        }, 300);
        
        searchInput.addEventListener('input', debouncedSearch);
    }
});
