// Socket.IO client for JAR - Natural Language Observability
const socket = io();

// DOM elements
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const reasoningLog = document.getElementById('reasoning-log');
const resultsDisplay = document.getElementById('results-display');
const connectionStatus = document.getElementById('connection-status');

// Database indicators
const indicators = {
    oracle: document.getElementById('oracle-indicator'),
    prometheus: document.getElementById('prometheus-indicator'),
    elasticsearch: document.getElementById('elasticsearch-indicator')
};

// State
let isProcessing = false;

// Socket event handlers
socket.on('connect', () => {
    console.log('Connected to server');
    updateConnectionStatus(true);
    addReasoningEntry('system', 'Connected to server', 'Establishing connection with backend agent');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    updateConnectionStatus(false);
    addReasoningEntry('system', 'Disconnected from server', 'Connection lost');
});

socket.on('status', (data) => {
    console.log('Status:', data);
    addReasoningEntry('system', data.message, data.reasoning || '');
    
    if (data.type === 'error' || data.type === 'warning') {
        showNotification(data.message, data.type);
    }
});

socket.on('progress', (data) => {
    console.log('Progress:', data);
    
    // Update database indicators
    if (data.source) {
        updateDatabaseIndicator(data.source, data.step);
    }
    
    // Add to reasoning log
    addReasoningEntry(data.source, data.message, data.reasoning, data.data);
});

socket.on('result', (data) => {
    console.log('Result:', data);
    
    // Reset all indicators to complete
    Object.keys(indicators).forEach(key => {
        if (indicators[key].classList.contains('active')) {
            indicators[key].classList.remove('active');
            indicators[key].classList.add('complete');
            updateIndicatorStatus(key, 'Complete');
        }
    });
    
    // Display result
    displayResult(data);
    
    // Re-enable form
    isProcessing = false;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Send Query';
    queryInput.value = '';
});

socket.on('error', (data) => {
    console.error('Error:', data);
    
    // Add error to reasoning log
    addReasoningEntry('error', data.message, data.reasoning || 'An error occurred');
    
    // Display error in results
    displayError(data);
    
    // Reset indicators
    resetDatabaseIndicators();
    
    // Re-enable form
    isProcessing = false;
    submitBtn.disabled = false;
    submitBtn.textContent = 'Send Query';
    
    showNotification(data.message, 'error');
});

// Form submission
queryForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    if (isProcessing) return;
    
    const query = queryInput.value.trim();
    if (!query) return;
    
    // Clear previous results and reset
    clearResults();
    clearReasoningLog();
    resetDatabaseIndicators();
    
    // Disable form
    isProcessing = true;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    // Send query to server
    socket.emit('query', { query });
});

// Helper functions
function updateConnectionStatus(connected) {
    if (connected) {
        connectionStatus.textContent = 'Connected';
        connectionStatus.classList.remove('disconnected');
        connectionStatus.classList.add('connected');
    } else {
        connectionStatus.textContent = 'Disconnected';
        connectionStatus.classList.remove('connected');
        connectionStatus.classList.add('disconnected');
    }
}

function updateDatabaseIndicator(source, step) {
    const indicator = indicators[source];
    if (!indicator) return;
    
    if (step.includes('start')) {
        indicator.classList.remove('complete', 'error');
        indicator.classList.add('active');
        updateIndicatorStatus(source, 'Querying...');
    } else if (step.includes('complete')) {
        indicator.classList.remove('active');
        indicator.classList.add('complete');
        updateIndicatorStatus(source, 'Complete');
    } else if (step.includes('error')) {
        indicator.classList.remove('active', 'complete');
        indicator.classList.add('error');
        updateIndicatorStatus(source, 'Error');
    }
}

function updateIndicatorStatus(source, status) {
    const indicator = indicators[source];
    if (!indicator) return;
    
    const statusEl = indicator.querySelector('.indicator-status');
    if (statusEl) {
        statusEl.textContent = status;
    }
}

function resetDatabaseIndicators() {
    Object.keys(indicators).forEach(key => {
        const indicator = indicators[key];
        indicator.classList.remove('active', 'complete', 'error');
        updateIndicatorStatus(key, 'Idle');
    });
}

function addReasoningEntry(source, message, reasoning, data = null) {
    const entry = document.createElement('div');
    entry.className = `reasoning-entry ${source || ''}`;
    
    const timestamp = new Date().toLocaleTimeString();
    
    let html = `
        <div class="reasoning-timestamp">${timestamp}</div>
        <div class="reasoning-message">${escapeHtml(message)}</div>
    `;
    
    if (reasoning) {
        html += `<div class="reasoning-text">${escapeHtml(reasoning)}</div>`;
    }
    
    if (data) {
        html += `<div class="reasoning-data">${JSON.stringify(data, null, 2)}</div>`;
    }
    
    entry.innerHTML = html;
    reasoningLog.appendChild(entry);
    reasoningLog.scrollTop = reasoningLog.scrollHeight;
}

function clearReasoningLog() {
    reasoningLog.innerHTML = '';
}

function displayResult(data) {
    resultsDisplay.innerHTML = '';
    
    const card = document.createElement('div');
    card.className = 'result-card healthy';
    
    let html = `
        <div class="result-header">✓ Query Complete</div>
        <div class="result-query">Query: "${escapeHtml(data.query || '')}"</div>
        <div class="result-response">
            <h3>Response:</h3>
            <p>${formatResponse(data.response)}</p>
        </div>
    `;
    
    card.innerHTML = html;
    resultsDisplay.appendChild(card);
}

function displayError(data) {
    resultsDisplay.innerHTML = '';
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <strong>Error:</strong> ${escapeHtml(data.message)}
        ${data.details ? `<pre>${escapeHtml(data.details)}</pre>` : ''}
    `;
    
    resultsDisplay.appendChild(errorDiv);
}

function clearResults() {
    resultsDisplay.innerHTML = '<div class="empty-state"><p>🔍 Processing query...</p></div>';
}

function formatResponse(response) {
    if (!response) return '';
    
    // Convert newlines to <br> and preserve formatting
    return escapeHtml(response)
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
}

function escapeHtml(text) {
    // More robust HTML escaping for security
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    };
    return String(text).replace(/[&<>"'/]/g, (s) => map[s]);
}

function showNotification(message, type) {
    // Simple notification (could be enhanced with a toast library)
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        queryInput.focus();
    }
    
    // Escape to clear input
    if (e.key === 'Escape' && document.activeElement === queryInput) {
        queryInput.value = '';
    }
});

// Initialize
console.log('JAR Client initialized');
