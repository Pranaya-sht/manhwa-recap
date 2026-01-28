/**
 * Manhwa Recap Generator - Frontend Application
 * Handles UI interactions and API communication
 */

// API Base URL
const API_BASE = 'http://localhost:8000';

// State
let currentProject = null;
let autoMode = true;

// DOM Elements
const elements = {
    urlInput: null,
    startBtn: null,
    autoModeToggle: null,
    progressSection: null,
    scriptSection: null,
    resultSection: null,
    projectsList: null,
    toastContainer: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initEventListeners();
    loadProjects();
    loadSettings();
});

function initElements() {
    elements.urlInput = document.getElementById('url-input');
    elements.startBtn = document.getElementById('start-btn');
    elements.autoModeToggle = document.getElementById('auto-mode');
    elements.progressSection = document.getElementById('progress-section');
    elements.scriptSection = document.getElementById('script-section');
    elements.resultSection = document.getElementById('result-section');
    elements.projectsList = document.getElementById('projects-list');
    elements.toastContainer = document.getElementById('toast-container');
}

function initEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    // Start processing
    elements.startBtn.addEventListener('click', startProcessing);

    // Auto mode toggle
    elements.autoModeToggle.addEventListener('change', (e) => {
        autoMode = e.target.checked;
    });

    // Enter key on URL input
    elements.urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            startProcessing();
        }
    });

    // Generate voiceover button
    document.getElementById('generate-voice-btn')?.addEventListener('click', () => {
        generateVoiceover();
    });

    // Download button
    document.getElementById('download-btn')?.addEventListener('click', downloadVideo);

    // New project button
    document.getElementById('new-project-btn')?.addEventListener('click', resetUI);

    // Refresh projects
    document.getElementById('refresh-projects-btn')?.addEventListener('click', loadProjects);

    // Save settings
    document.getElementById('save-settings-btn')?.addEventListener('click', saveSettings);

    // Speech rate slider
    const speechRateSlider = document.getElementById('speech-rate');
    if (speechRateSlider) {
        speechRateSlider.addEventListener('input', (e) => {
            document.getElementById('speech-rate-value').textContent = e.target.value + 'x';
        });
    }

    // Script editor word count
    const scriptEditor = document.getElementById('script-editor');
    if (scriptEditor) {
        scriptEditor.addEventListener('input', updateWordCount);
    }
}

// View switching
function switchView(viewName) {
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewName}-view`).classList.add('active');
}

// Toast notifications
function showToast(title, message, type = 'info') {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;

    elements.toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// Update step status
function updateStep(stepId, status, message = '') {
    const step = document.getElementById(`step-${stepId}`);
    if (!step) return;

    // Remove all status classes
    step.classList.remove('active', 'completed', 'error');

    // Add new status
    step.classList.add(status);

    // Update badge
    const badge = step.querySelector('.status-badge');
    badge.className = `status-badge ${status}`;

    const statusText = {
        waiting: 'Waiting',
        active: 'In Progress...',
        completed: 'Completed ✓',
        error: 'Failed ✗'
    };

    badge.textContent = message || statusText[status];

    // Add Retry Button if error
    if (status === 'error') {
        const retryBtn = document.createElement('button');
        retryBtn.className = 'btn-retry';
        retryBtn.innerHTML = '🔄 Retry Step';
        retryBtn.onclick = (e) => {
            e.stopPropagation();
            retryStep(stepId);
        };
        badge.appendChild(retryBtn);
    }
}

// Retry a specific step
async function retryStep(stepId) {
    if (!currentProject?.project_id) return;

    showToast('Retry', `Retrying ${stepId}...`, 'info');

    if (stepId === 'scrape') {
        startProcessing(); // Restart from URL
    } else if (stepId === 'script') {
        processStepByStep(currentProject.url, true); // Force script gen
    } else if (stepId === 'voice') {
        generateVoiceover();
    } else if (stepId === 'video') {
        createVideo();
    }
}

// Update progress bar
function updateProgress(percent) {
    document.getElementById('progress-fill').style.width = `${percent}%`;
    document.getElementById('progress-text').textContent = `${Math.round(percent)}%`;
}

// Main processing function
async function startProcessing() {
    const url = elements.urlInput.value.trim();

    if (!url) {
        showToast('Error', 'Please enter a manhwa chapter URL', 'error');
        return;
    }

    // Validate URL
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        showToast('Error', 'Please enter a valid URL starting with http:// or https://', 'error');
        return;
    }

    // Show progress section
    elements.progressSection.classList.remove('hidden');
    elements.scriptSection.classList.add('hidden');
    elements.resultSection.classList.add('hidden');

    // Disable start button
    elements.startBtn.disabled = true;
    elements.startBtn.innerHTML = '<span class="btn-icon loading-spinner">⏳</span> Processing...';

    // Reset steps
    ['scrape', 'script', 'voice', 'video'].forEach(step => {
        updateStep(step, 'waiting');
    });
    updateProgress(0);

    try {
        if (autoMode) {
            // Full automation mode
            await processFullAuto(url);
        } else {
            // Step-by-step mode
            await processStepByStep(url);
        }
    } catch (error) {
        showToast('Error', error.message, 'error');
        console.error('Processing error:', error);
    } finally {
        elements.startBtn.disabled = false;
        elements.startBtn.innerHTML = '<span class="btn-icon">🚀</span> Start Processing';
    }
}

// Full automation processing
async function processFullAuto(url) {
    updateStep('scrape', 'active');
    updateProgress(5);

    try {
        const response = await fetch(`${API_BASE}/api/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url: url,
                voice: document.getElementById('voice-select')?.value || 'en-US-GuyNeural',
                rate: 1.0,
                ken_burns: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Processing failed');
        }

        // Simulate progress updates
        const progressSteps = [
            { step: 'scrape', progress: 25, delay: 1000 },
            { step: 'script', progress: 50, delay: 2000 },
            { step: 'voice', progress: 75, delay: 1500 },
            { step: 'video', progress: 100, delay: 2000 }
        ];

        let stepIndex = 0;
        const simulateProgress = () => {
            if (stepIndex > 0) {
                updateStep(progressSteps[stepIndex - 1].step, 'completed');
            }
            if (stepIndex < progressSteps.length) {
                updateStep(progressSteps[stepIndex].step, 'active');
                updateProgress(progressSteps[stepIndex].progress);
                stepIndex++;
            }
        };

        // Start progress simulation
        const progressInterval = setInterval(simulateProgress, 3000);
        simulateProgress();

        const result = await response.json();
        clearInterval(progressInterval);

        // Mark all steps complete
        ['scrape', 'script', 'voice', 'video'].forEach(step => {
            updateStep(step, 'completed');
        });
        updateProgress(100);

        currentProject = result;
        document.getElementById('project-title').textContent =
            `${result.manga_name} - Chapter ${result.chapter}`;

        showToast('Success', 'Video created successfully!', 'success');
        showResult(result);
        loadProjects();

    } catch (error) {
        updateStep('scrape', 'error', 'Failed');
        throw error;
    }
}

// Step-by-step processing
async function processStepByStep(url, skipScrape = false) {
    let projectId = currentProject?.project_id;

    // Step 1: Scrape (unless skipped)
    if (!skipScrape) {
        updateStep('scrape', 'active');
        updateProgress(10);

        const scrapeResponse = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!scrapeResponse.ok) {
            const error = await scrapeResponse.json();
            updateStep('scrape', 'error');
            throw new Error(error.detail || 'Scraping failed');
        }

        const scrapeResult = await scrapeResponse.json();
        projectId = scrapeResult.project_id;
        currentProject = { ...scrapeResult };
        updateStep('scrape', 'completed');
        updateProgress(25);

        document.getElementById('project-title').textContent =
            `${scrapeResult.manga_name} - Chapter ${scrapeResult.chapter}`;
    }

    // Step 2: Generate Script
    updateStep('script', 'active');

    const scriptResponse = await fetch(`${API_BASE}/api/generate-script`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
    });

    if (!scriptResponse.ok) {
        const error = await scriptResponse.json();
        updateStep('script', 'error');
        throw new Error(error.detail || 'Script generation failed');
    }

    const scriptResult = await scriptResponse.json();
    currentProject = { ...currentProject, ...scriptResult };
    updateStep('script', 'completed');
    updateProgress(50);

    // Show script for review
    showScriptReview(scriptResult);
}

// Show script review section
function showScriptReview(result) {
    elements.scriptSection.classList.remove('hidden');

    const editor = document.getElementById('script-editor');
    editor.value = result.script;

    document.getElementById('word-count').textContent = `${result.word_count} words`;
    document.getElementById('duration-estimate').textContent =
        `~${Math.round(result.estimated_duration)} min`;

    showToast('Script Ready', 'Review the script and generate voiceover', 'info');
}

// Update word count in editor
function updateWordCount() {
    const editor = document.getElementById('script-editor');
    const wordCount = editor.value.trim().split(/\s+/).filter(w => w).length;
    document.getElementById('word-count').textContent = `${wordCount} words`;
    document.getElementById('duration-estimate').textContent =
        `~${Math.round(wordCount / 150)} min`;
}

// Generate voiceover
async function generateVoiceover() {
    if (!currentProject?.project_id) {
        showToast('Error', 'No active project', 'error');
        return;
    }

    const btn = document.getElementById('generate-voice-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-icon loading-spinner">⏳</span> Generating...';

    try {
        // Update script if modified
        const script = document.getElementById('script-editor').value;
        await fetch(`${API_BASE}/api/update-script`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProject.project_id,
                script: script
            })
        });

        updateStep('voice', 'active');

        // Generate voiceover
        const voice = document.getElementById('voice-select').value;
        const response = await fetch(`${API_BASE}/api/generate-voice`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProject.project_id,
                voice: voice,
                rate: 1.0
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Voiceover generation failed');
        }

        const voiceResult = await response.json();
        currentProject = { ...currentProject, ...voiceResult };
        updateStep('voice', 'completed');
        updateProgress(75);

        showToast('Success', 'Voiceover generated!', 'success');

        // Create video
        await createVideo();

    } catch (error) {
        updateStep('voice', 'error');
        showToast('Error', error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🎙️</span> Generate Voiceover';
    }
}

// Create video
async function createVideo() {
    if (!currentProject?.project_id) {
        showToast('Error', 'No active project', 'error');
        return;
    }

    updateStep('video', 'active');

    try {
        const response = await fetch(`${API_BASE}/api/create-video`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: currentProject.project_id,
                ken_burns: true,
                transition_duration: 0.5
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Video creation failed');
        }

        const videoResult = await response.json();
        currentProject = { ...currentProject, ...videoResult };
        updateStep('video', 'completed');
        updateProgress(100);

        showToast('Success', 'Video created successfully!', 'success');
        showResult(videoResult);
        loadProjects();

    } catch (error) {
        updateStep('video', 'error');
        showToast('Error', error.message, 'error');
    }
}

// Show result section
function showResult(result) {
    elements.scriptSection.classList.add('hidden');
    elements.resultSection.classList.remove('hidden');

    // Update result info
    document.getElementById('result-title').textContent =
        `${currentProject.manga_name} - Chapter ${currentProject.chapter}`;
    document.getElementById('result-duration').textContent =
        formatDuration(result.duration);
    document.getElementById('result-size').textContent =
        formatFileSize(result.file_size);

    // Video preview (if available locally)
    const videoPreview = document.getElementById('video-preview');
    if (result.video_path) {
        videoPreview.src = `file://${result.video_path}`;
    }
}

// Format duration
function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Format file size
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

// Download video
function downloadVideo() {
    if (currentProject?.video_path) {
        // Create download link
        const link = document.createElement('a');
        link.href = `file://${currentProject.video_path}`;
        link.download = `${currentProject.manga_name}_Chapter_${currentProject.chapter}.mp4`;
        link.click();

        showToast('Download', 'Video download started', 'info');
    }
}

// Reset UI for new project
function resetUI() {
    elements.urlInput.value = '';
    elements.progressSection.classList.add('hidden');
    elements.scriptSection.classList.add('hidden');
    elements.resultSection.classList.add('hidden');
    currentProject = null;

    ['scrape', 'script', 'voice', 'video'].forEach(step => {
        updateStep(step, 'waiting');
    });
    updateProgress(0);
}

// Load projects list
async function loadProjects() {
    try {
        const response = await fetch(`${API_BASE}/api/projects`);
        if (!response.ok) throw new Error('Failed to load projects');

        const projects = await response.json();

        if (projects.length === 0) {
            elements.projectsList.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p>No projects yet. Create one above!</p>
                </div>
            `;
            return;
        }

        elements.projectsList.innerHTML = projects.map(project => `
            <div class="project-item" data-id="${project.id}" onclick="resumeProject('${project.id}')">
                <div class="project-thumb">📖</div>
                <div class="project-info">
                    <h4>${project.manga_name} - Ch. ${project.chapter}</h4>
                    <p>${project.image_count || 0} images • ${formatDate(project.created_at)}</p>
                </div>
                <span class="project-status ${project.status}">${project.status}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Failed to load projects:', error);
    }
}

// Resume an existing project
async function resumeProject(projectId) {
    try {
        const response = await fetch(`${API_BASE}/api/projects/${projectId}`);
        if (!response.ok) throw new Error('Project not found');

        const project = await response.json();
        currentProject = project;

        // Setup UI
        elements.progressSection.classList.remove('hidden');
        elements.scriptSection.classList.add('hidden');
        elements.resultSection.classList.add('hidden');
        document.getElementById('project-title').textContent =
            `${project.manga_name} - Chapter ${project.chapter}`;

        // Restore steps
        const steps = ['scrape', 'script', 'voiceover', 'video'];
        const stepMapping = {
            'scrape': 'scrape',
            'script': 'script',
            'voiceover': 'voice',
            'video': 'video'
        };

        // Reset all
        steps.forEach(s => updateStep(stepMapping[s], 'waiting'));

        // Mark completed
        let lastCompletedIdx = -1;
        project.steps_completed.forEach(stepName => {
            const stepId = stepMapping[stepName];
            if (stepId) {
                updateStep(stepId, 'completed');
                const idx = steps.indexOf(stepName);
                if (idx > lastCompletedIdx) lastCompletedIdx = idx;
            }
        });

        // Update progress bar
        const progressPerStep = 25;
        updateProgress((lastCompletedIdx + 1) * progressPerStep);

        // Show next action
        if (project.status === 'completed') {
            showResult(project);
        } else if (project.status === 'script_generated') {
            showScriptReview(project);
        } else if (project.status === 'voiceover_generated') {
            updateStep('video', 'waiting');
            // If it was voiceover generated, maybe it failed at video? 
            // Or just show result if it has video path
            if (project.video_path) {
                showResult(project);
            } else {
                updateStep('video', 'active', 'Ready to render');
            }
        }

        showToast('Resumed', `Loaded project: ${project.manga_name}`, 'info');

    } catch (error) {
        showToast('Error', 'Failed to resume project', 'error');
    }
}

// Format date
function formatDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Load settings
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        if (!response.ok) return;

        const config = await response.json();

        // Populate settings form
        if (config.default_voice) {
            const voiceSelect = document.getElementById('default-voice');
            if (voiceSelect) voiceSelect.value = config.default_voice;
        }

        if (config.speech_rate) {
            const rateSlider = document.getElementById('speech-rate');
            if (rateSlider) {
                rateSlider.value = config.speech_rate;
                document.getElementById('speech-rate-value').textContent = config.speech_rate + 'x';
            }
        }

        if (config.channel_name) {
            const channelInput = document.getElementById('channel-name');
            if (channelInput) channelInput.value = config.channel_name;
        }

        if (config.ken_burns_enabled !== undefined) {
            const kenBurns = document.getElementById('ken-burns');
            if (kenBurns) kenBurns.checked = config.ken_burns_enabled;
        }

        if (config.auto_crop_enabled !== undefined) {
            const autoCrop = document.getElementById('auto-crop');
            if (autoCrop) autoCrop.checked = config.auto_crop_enabled;
        }

    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

// Save settings
async function saveSettings() {
    const config = {
        gemini_api_key: document.getElementById('gemini-key')?.value || undefined,
        default_voice: document.getElementById('default-voice')?.value,
        speech_rate: parseFloat(document.getElementById('speech-rate')?.value || 1.0),
        channel_name: document.getElementById('channel-name')?.value,
        ken_burns_enabled: document.getElementById('ken-burns')?.checked,
        auto_crop_enabled: document.getElementById('auto-crop')?.checked
    };

    // Remove undefined values
    Object.keys(config).forEach(key => {
        if (config[key] === undefined || config[key] === '') {
            delete config[key];
        }
    });

    try {
        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!response.ok) throw new Error('Failed to save settings');

        showToast('Success', 'Settings saved successfully', 'success');

    } catch (error) {
        showToast('Error', 'Failed to save settings', 'error');
        console.error('Save settings error:', error);
    }
}
