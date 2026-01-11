// Socket.IO client for JAR - Natural Language Observability
const socket = io();

// DOM elements
const queryForm = document.getElementById('query-form');
const queryInput = document.getElementById('query-input');
const submitBtn = document.getElementById('submit-btn');
const voiceBtn = document.getElementById('voice-btn');
const reasoningLog = document.getElementById('reasoning-log');
const resultsDisplay = document.getElementById('results-display');
const connectionStatus = document.getElementById('connection-status');

// Database indicators
const indicators = {
    oracle: document.getElementById('oracle-indicator'),
    prometheus: document.getElementById('prometheus-indicator'),
    elasticsearch: document.getElementById('elasticsearch-indicator'),
    analytics: document.getElementById('analytics-indicator')
};

// Data action buttons
const precomputeBtn = document.getElementById('precompute-btn');
const populateBtn = document.getElementById('populate-btn');

// State
let isProcessing = false;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

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

// Accumulator for streaming response
let streamingResponse = '';
let streamingActive = false;

socket.on('progress', (data) => {
    console.log('Progress:', data);

    // Handle streaming response chunks
    if (data.step === 'streaming') {
        if (!streamingActive) {
            streamingActive = true;
            // Initialize streaming display
            displayStreamingStart();
        }
        // Accumulate and display chunk
        streamingResponse += data.message;
        updateStreamingResponse(streamingResponse);
        return;
    }

    // Update database indicators
    if (data.source) {
        updateDatabaseIndicator(data.source, data.step);
    }

    // Add to reasoning log
    addReasoningEntry(data.source, data.message, data.reasoning, data.data);
});

socket.on('result', (data) => {
    console.log('Result:', data);

    // Reset streaming state
    streamingActive = false;
    streamingResponse = '';

    // Reset all indicators to complete
    Object.keys(indicators).forEach(key => {
        if (indicators[key].classList.contains('active')) {
            indicators[key].classList.remove('active');
            indicators[key].classList.add('complete');
            updateIndicatorStatus(key, 'Complete');
        }
    });

    // Display result (will show the complete response if not already streaming)
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

    // Reset streaming state
    streamingResponse = '';
    streamingActive = false;

    // Disable form
    isProcessing = true;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    // Send query to server
    socket.emit('query', { query });
});

// Voice input functionality
voiceBtn.addEventListener('click', async () => {
    if (isRecording) {
        // Stop recording
        stopRecording();
    } else {
        // Start recording
        startRecording();
    }
});

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.addEventListener('dataavailable', (event) => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener('stop', async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            await transcribeAudio(audioBlob);

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        });

        mediaRecorder.start();
        isRecording = true;

        // Update button UI
        voiceBtn.classList.add('recording');
        voiceBtn.title = 'Click to stop recording';

        addReasoningEntry('system', 'Recording audio...', 'Listening for voice input');

    } catch (error) {
        console.error('Error accessing microphone:', error);
        showNotification('Could not access microphone. Please check permissions.', 'error');
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;

        // Update button UI
        voiceBtn.classList.remove('recording');
        voiceBtn.title = 'Click to speak';

        addReasoningEntry('system', 'Processing audio...', 'Transcribing speech to text');
    }
}

async function transcribeAudio(audioBlob) {
    try {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.webm');

        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Transcription failed');
        }

        const data = await response.json();

        if (data.text) {
            // Populate input with transcribed text
            queryInput.value = data.text;
            queryInput.focus();

            addReasoningEntry('system', 'Transcription complete', `Recognized: "${data.text}"`);
            showNotification('Voice input transcribed successfully', 'success');
        } else {
            throw new Error('No text received from transcription');
        }

    } catch (error) {
        console.error('Transcription error:', error);
        addReasoningEntry('error', 'Transcription failed', error.message);
        showNotification(`Transcription error: ${error.message}`, 'error');
    }
}

// Streaming helper functions
function displayStreamingStart() {
    resultsDisplay.innerHTML = '';

    const card = document.createElement('div');
    card.className = 'result-card healthy streaming';
    card.id = 'streaming-card';

    card.innerHTML = `
        <div class="result-header">✍️ Generating Response...</div>
        <div class="result-response">
            <div id="streaming-content"></div>
            <span class="streaming-cursor">▋</span>
        </div>
    `;

    resultsDisplay.appendChild(card);
}

function updateStreamingResponse(content) {
    const streamingContent = document.getElementById('streaming-content');
    if (streamingContent) {
        streamingContent.innerHTML = formatResponse(content);
        // Auto-scroll to bottom
        resultsDisplay.scrollTop = resultsDisplay.scrollHeight;
    }
}

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
    // Comprehensive HTML escaping for XSS protection
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '`': '&#x60;',
    };
    return String(text).replace(/[&<>"'/`]/g, (s) => map[s]);
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

// Data action button handlers
if (precomputeBtn) {
    precomputeBtn.addEventListener('click', async () => {
        if (precomputeBtn.disabled) return;

        precomputeBtn.disabled = true;
        precomputeBtn.querySelector('span').textContent = 'Computing...';

        addReasoningEntry('system', 'Starting baseline precomputation...', 'Regenerating historical baselines and patterns');

        try {
            const response = await fetch('/api/precompute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ days: 120 })
            });

            const data = await response.json();

            if (data.status === 'success') {
                addReasoningEntry('system', 'Baseline precomputation complete!', 'All baselines and patterns updated');
                showNotification('Baselines refreshed successfully', 'success');
            } else {
                addReasoningEntry('error', 'Precomputation failed', data.message || 'Unknown error');
                showNotification('Failed to refresh baselines', 'error');
            }
        } catch (error) {
            console.error('Precompute error:', error);
            addReasoningEntry('error', 'Precomputation failed', error.message);
            showNotification('Failed to refresh baselines', 'error');
        } finally {
            precomputeBtn.disabled = false;
            precomputeBtn.querySelector('span').textContent = 'Refresh Baselines';
        }
    });
}

if (populateBtn) {
    populateBtn.addEventListener('click', async () => {
        if (populateBtn.disabled) return;

        // Confirm action since it regenerates all data
        if (!confirm('This will regenerate all dummy data (Oracle, Prometheus, Elasticsearch, and baselines). Continue?')) {
            return;
        }

        populateBtn.disabled = true;
        populateBtn.querySelector('span').textContent = 'Populating...';

        addReasoningEntry('system', 'Starting full data population...', 'Regenerating all test data across data sources');

        try {
            const response = await fetch('/api/populate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const data = await response.json();

            if (data.status === 'success') {
                addReasoningEntry('system', 'Data population complete!', 'All data sources refreshed');
                showNotification('All data populated successfully', 'success');
            } else {
                addReasoningEntry('error', 'Data population failed', data.message || 'Unknown error');
                showNotification('Failed to populate data', 'error');
            }
        } catch (error) {
            console.error('Populate error:', error);
            addReasoningEntry('error', 'Data population failed', error.message);
            showNotification('Failed to populate data', 'error');
        } finally {
            populateBtn.disabled = false;
            populateBtn.querySelector('span').textContent = 'Populate All Data';
        }
    });
}

// Initialize JAR Natural Language Observability Client
// Components: Socket.IO connection, event handlers, UI state management
console.log('JAR Client initialized - WebSocket connection and event listeners configured');
