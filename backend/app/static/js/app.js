/**
 * Main Application JavaScript Module
 * Global functions and utilities for the Resume Matcher application
 */

// API Base URL
const API_BASE = '/api';

/**
 * Make API requests with error handling
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise}
 */
async function apiCall(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, finalOptions);
        
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || data.error || `HTTP Error: ${response.status}`);
        }

        return { success: true, data };
    } catch (error) {
        console.error(`API Error: ${error.message}`);
        return { success: false, error: error.message };
    }
}

/**
 * Show notification message
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in milliseconds
 */
function showNotification(message, type = 'info', duration = 3000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} fixed top-4 right-4 max-w-md`;
    notification.textContent = message;
    notification.style.zIndex = '9999';

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.remove();
    }, duration);
}

/**
 * Format bytes to human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string}
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Format date to readable format
 * @param {Date} date - Date object
 * @returns {string}
 */
function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

/**
 * Show loading spinner
 * @param {string} elementId - Element ID
 */
function showLoader(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '<div class="spinner"></div>';
    }
}

/**
 * Clear element content
 * @param {string} elementId - Element ID
 */
function clearElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = '';
    }
}

/**
 * Element visibility toggle
 * @param {string} elementId - Element ID
 * @param {boolean} show - Show or hide
 */
function toggleElement(elementId, show) {
    const element = document.getElementById(elementId);
    if (element) {
        element.classList.toggle('hidden', !show);
    }
}

/**
 * Debounce function for optimizing event handlers
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function}
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function for rate-limiting function calls
 * @param {Function} func - Function to throttle
 * @param {number} limit - Limit in milliseconds
 * @returns {Function}
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('Copied to clipboard!', 'success');
    } catch (error) {
        showNotification('Failed to copy', 'error');
    }
}

/**
 * Parse URL parameters
 * @returns {Object}
 */
function getUrlParams() {
    const params = {};
    const queryString = window.location.search.substring(1);
    const pairs = queryString.split('&');

    pairs.forEach(pair => {
        const [key, value] = pair.split('=');
        params[decodeURIComponent(key)] = decodeURIComponent(value || '');
    });

    return params;
}

function toggleLoadingScreen(show = true) {
    const loadingScreen = document.getElementById('aiLoadingScreen');
    if (!loadingScreen) return;

    loadingScreen.classList.toggle('active', show);
    loadingScreen.setAttribute('aria-hidden', show ? 'false' : 'true');
    document.body.style.overflow = show ? 'hidden' : '';
}

function transitionToResults(resultsId = 'resultsSection') {
    const section = document.getElementById(resultsId);
    if (!section) return;

    section.classList.remove('hidden');
    section.classList.add('fade-in');
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * Initialize app on DOMContentLoaded
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('✓ Resume Matcher Application Loaded');

    // Add smooth scroll behavior
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});

// Export functions for use in other modules
window.appUtils = {
    apiCall,
    showNotification,
    formatBytes,
    formatDate,
    showLoader,
    clearElement,
    toggleElement,
    debounce,
    throttle,
    copyToClipboard,
    getUrlParams,
    toggleLoadingScreen,
    transitionToResults
};
