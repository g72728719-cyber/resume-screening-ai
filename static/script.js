// State management
let uploadedFiles = [];

// DOM elements
const jobDescription = document.getElementById('jobDescription');
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const fileList = document.getElementById('fileList');
const analyzeBtn = document.getElementById('analyzeBtn');
const emptyState = document.getElementById('emptyState');
const loadingState = document.getElementById('loadingState');
const resultsContainer = document.getElementById('resultsContainer');
const resultsGrid = document.getElementById('resultsGrid');
const clearResults = document.getElementById('clearResults');
const loadingText = document.getElementById('loadingText');

// Initialize event listeners
function init() {
    // Upload zone click
    uploadZone.addEventListener('click', () => {
        fileInput.click();
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Drag and drop events
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    // Job description input
    jobDescription.addEventListener('input', updateAnalyzeButton);

    // Analyze button
    analyzeBtn.addEventListener('click', analyzeResumes);

    // Clear results button
    clearResults.addEventListener('click', () => {
        showEmptyState();
        resultsGrid.innerHTML = '';
    });
}

// Handle uploaded files
function handleFiles(files) {
    const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');

    pdfFiles.forEach(file => {
        // Check if file already uploaded
        if (!uploadedFiles.some(f => f.name === file.name)) {
            uploadedFiles.push(file);
        }
    });

    renderFileList();
    updateAnalyzeButton();
}

// Render file list
function renderFileList() {
    if (uploadedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
    }

    fileList.innerHTML = uploadedFiles.map((file, index) => `
        <div class="file-item">
            <div class="file-info">
                <svg class="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                </svg>
                <span class="file-name">${file.name}</span>
            </div>
            <button class="remove-file" onclick="removeFile(${index})">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `).join('');
}

// Remove file
function removeFile(index) {
    uploadedFiles.splice(index, 1);
    renderFileList();
    updateAnalyzeButton();
}

// Update analyze button state
function updateAnalyzeButton() {
    const hasJobDescription = jobDescription.value.trim().length > 0;
    const hasFiles = uploadedFiles.length > 0;

    analyzeBtn.disabled = !(hasJobDescription && hasFiles);
}

// Show/hide states
function showEmptyState() {
    emptyState.style.display = 'flex';
    loadingState.style.display = 'none';
    resultsContainer.style.display = 'none';
}

function showLoadingState() {
    emptyState.style.display = 'none';
    loadingState.style.display = 'flex';
    resultsContainer.style.display = 'none';
}

function showResultsState() {
    emptyState.style.display = 'none';
    loadingState.style.display = 'none';
    resultsContainer.style.display = 'block';
}

// Analyze resumes
async function analyzeResumes() {
    if (uploadedFiles.length === 0 || !jobDescription.value.trim()) {
        return;
    }

    showLoadingState();
    analyzeBtn.disabled = true;

    const formData = new FormData();
    formData.append('job_description', jobDescription.value);

    uploadedFiles.forEach(file => {
        formData.append('resumes', file);
    });

    try {
        // Simulate loading text updates
        const loadingMessages = [
            'Processing resumes with AI...',
            'Extracting text from PDFs...',
            'Analyzing candidate qualifications...',
            'Comparing skills and experience...',
            'Generating insights...'
        ];

        let messageIndex = 0;
        const loadingInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % loadingMessages.length;
            loadingText.textContent = loadingMessages[messageIndex];
        }, 2000);

        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        clearInterval(loadingInterval);

        if (!response.ok) {
            throw new Error('Analysis failed');
        }

        const results = await response.json();
        displayResults(results);
        showResultsState();

    } catch (error) {
        console.error('Error analyzing resumes:', error);
        alert('Failed to analyze resumes. Please try again.');
        showEmptyState();
    } finally {
        analyzeBtn.disabled = false;
    }
}

// Display results
function displayResults(results) {
    resultsGrid.innerHTML = '';
    currentAnalysisData = {};

    results.forEach((result, index) => {
        // Store the analysis data for later use when generating resume
        currentAnalysisData[result.resume_name] = result.analysis;
        
        const card = createResultCard(result, index);
        resultsGrid.appendChild(card);
    });
}

// Create result card
function createResultCard(result, index) {
    const card = document.createElement('div');
    card.className = 'result-card';

    // Parse the analysis text
    const parsed = parseAnalysis(result.analysis);

    // Determine score class
    const scoreClass = parsed.score >= 70 ? 'score-high' :
                       parsed.score >= 50 ? 'score-medium' : 'score-low';

    card.classList.add(scoreClass);
    card.style.animationDelay = `${index * 0.1}s`;

    // Check if there are missing skills to enable the generate button
    const hasMissingSkills = parsed.missingSkills.length > 0;
    const buttonClass = hasMissingSkills ? 'generate-btn enabled' : 'generate-btn disabled';
    const buttonDisabled = hasMissingSkills ? '' : 'disabled';

    card.innerHTML = `
        <div class="result-header">
            <div class="result-title">
                <h3>${result.resume_name}</h3>
                <p class="result-subtitle">Candidate Analysis</p>
            </div>
            <div class="score-badge">
                <span class="score-value">${parsed.score}</span>
                <span class="score-label">Score</span>
            </div>
        </div>

        ${parsed.matchedSkills.length > 0 ? `
            <div class="skills-section">
                <div class="skills-header">Matched Skills</div>
                <div class="skills-list">
                    ${parsed.matchedSkills.map(skill => `
                        <span class="skill-tag matched">${skill}</span>
                    `).join('')}
                </div>
            </div>
        ` : ''}

        ${parsed.missingSkills.length > 0 ? `
            <div class="skills-section">
                <div class="skills-header">Missing Skills</div>
                <div class="skills-list">
                    ${parsed.missingSkills.map(skill => `
                        <span class="skill-tag missing">${skill}</span>
                    `).join('')}
                </div>
            </div>
        ` : ''}

        ${parsed.summary ? `
            <div class="summary-section">
                <div class="summary-header">Summary</div>
                <p class="summary-text">${parsed.summary}</p>
            </div>
        ` : ''}

        <button class="${buttonClass}" onclick="generateOptimizedResume(this, '${result.resume_name}', ${index})" ${buttonDisabled}>
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span class="btn-text">Generate Optimized Resume</span>
        </button>
    `;

    return card;
}

// Parse analysis text
function parseAnalysis(text) {
    const result = {
        score: 0,
        matchedSkills: [],
        missingSkills: [],
        summary: ''
    };

    // Extract score
    const scoreMatch = text.match(/Score:\s*(\d+)/i);
    if (scoreMatch) {
        result.score = parseInt(scoreMatch[1]);
    }

    // Extract matched skills
    const matchedMatch = text.match(/Matched Skills:\s*([^\n]+)/i);
    if (matchedMatch) {
        result.matchedSkills = matchedMatch[1]
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0 && s.toLowerCase() !== 'none');
    }

    // Extract missing skills
    const missingMatch = text.match(/Missing Skills:\s*([^\n]+)/i);
    if (missingMatch) {
        result.missingSkills = missingMatch[1]
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0 && s.toLowerCase() !== 'none');
    }

    // Extract summary
    const summaryMatch = text.match(/Summary:\s*(.+)/is);
    if (summaryMatch) {
        result.summary = summaryMatch[1].trim();
    }

    return result;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', init);

// Store current analysis results for resume generation
let currentAnalysisData = {};

// Generate optimized resume
async function generateOptimizedResume(button, resumeName, resultIndex) {
    const originalButton = button;
    const originalHTML = button.innerHTML;
    
    try {
        // Disable button and show loading state
        button.disabled = true;
        button.innerHTML = `
            <svg class="btn-icon spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
            </svg>
            <span class="btn-text">Generating...</span>
        `;
        
        // Get the resume text from the uploaded file
        const resumeIndex = Array.from(uploadedFiles).findIndex(f => f.name === resumeName);
        if (resumeIndex === -1) {
            throw new Error('Resume file not found');
        }
        
        const resumeFile = uploadedFiles[resumeIndex];
        
        // Read the PDF file as text (we need to extract it)
        // Since we can't directly extract text from browser, we'll send the file to be processed
        const formData = new FormData();
        formData.append('resume_file', resumeFile);
        formData.append('job_description', jobDescription.value);
        
        // For now, we'll use a different approach: send the same file and let backend handle it
        const generateFormData = new FormData();
        generateFormData.append('resume_file', resumeFile);
        generateFormData.append('job_description', jobDescription.value);
        
        // First, extract the text from the resume
        const extractResponse = await fetch('/extract-resume-text', {
            method: 'POST',
            body: generateFormData
        });
        
        if (!extractResponse.ok) {
            throw new Error('Failed to extract resume text');
        }
        
        const extractData = await extractResponse.json();
        const resumeText = extractData.resume_text;
        
        // Get the analysis from the results
        const analysisText = currentAnalysisData[resumeName];
        if (!analysisText) {
            throw new Error('Analysis not found for this resume');
        }
        
        // Create the generate request payload
        const generatePayload = {
            resume_text: resumeText,
            job_description: jobDescription.value,
            analysis: analysisText,
            resume_filename: resumeName
        };
        
        // Send the generate-resume request
        const generateResponse = await fetch('/generate-resume', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(generatePayload)
        });
        
        if (!generateResponse.ok) {
            throw new Error('Failed to generate optimized resume');
        }
        
        // Get the file blob
        const blob = await generateResponse.blob();
        
        // Create a download link
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `optimized_resume_${Date.now()}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        // Show success message
        button.innerHTML = `
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <span class="btn-text">Downloaded!</span>
        `;
        
        // Reset after 3 seconds
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.disabled = false;
        }, 3000);
        
    } catch (error) {
        console.error('Error generating resume:', error);
        button.innerHTML = `
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="15" y1="9" x2="9" y2="15"></line>
                <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
            <span class="btn-text">Error!</span>
        `;
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.disabled = false;
        }, 3000);
        
        alert(`Failed to generate resume: ${error.message}`);
    }
}
