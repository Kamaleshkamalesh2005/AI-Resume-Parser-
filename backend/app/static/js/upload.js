/**
 * Resume Upload Module
 * Handles file uploads, drag-drop, and resume processing
 */

document.addEventListener('DOMContentLoaded', () => {
    initializeJobDescription();
    initializeSingleUpload();
    initializeBatchUpload();
});

// Global storage for drag-dropped files (since .files is read-only)
let draggedSingleFile = null;
let draggedBatchFiles = null;

function initializeJobDescription() {
    const form = document.getElementById('jobDescriptionForm');
    const status = document.getElementById('jobDescriptionStatus');
    if (!form || !status) return;

    const textInput = document.getElementById('jobDescriptionText');
    const savedText = localStorage.getItem('jobDescriptionText') || '';
    if (textInput && savedText) {
        textInput.value = savedText;
        status.textContent = `Saved (${savedText.length} chars)`;
        status.classList.remove('hidden');
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const text = document.getElementById('jobDescriptionText')?.value || '';
        const fileInput = document.getElementById('jobDescriptionFile');
        const file = fileInput?.files?.[0] || null;

        const formData = new FormData();
        formData.append('text', text);
        if (file) formData.append('file', file);

        try {
            appUtils.toggleLoadingScreen(true);
            const data = await postWithFallback(['/api/upload/job-description'], formData);

            if (!data.success) {
                throw new Error(data.message || data.error || 'Failed to save job description');
            }

            const content = data.data?.content || '';
            localStorage.setItem('jobDescriptionText', content);
            status.textContent = `Saved (${content.length} chars)`;
            status.classList.remove('hidden');
            appUtils.showNotification('Job description saved', 'success');
        } catch (error) {
            appUtils.showNotification(error.message || 'Failed to save job description', 'error');
        } finally {
            appUtils.toggleLoadingScreen(false);
        }
    });
}

function initializeSingleUpload() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadForm = document.getElementById('uploadForm');

    if (!dropZone || !fileInput || !uploadForm) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach((eventName) => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('active');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('active');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        draggedSingleFile = files.length > 0 ? files[0] : null;
        renderSingleFile(files);
    });

    dropZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        draggedSingleFile = e.target.files.length > 0 ? e.target.files[0] : null;
        renderSingleFile(e.target.files);
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await processSingleUpload();
    });
}

function renderSingleFile(files) {
    const dropZone = document.getElementById('dropZone');

    if (!dropZone || !files || files.length === 0) return;

    const file = files[0];
    dropZone.innerHTML = `
        <div class="text-4xl mb-3">✓</div>
        <p class="text-lg font-semibold text-white">${file.name}</p>
        <p class="text-sm text-gray-300 mt-2">${appUtils.formatBytes(file.size)}</p>
        <p class="text-xs text-blue-200 mt-2">Ready for AI parsing</p>
    `;
}

async function processSingleUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const statusDetails = document.getElementById('statusDetails');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    // Check both dragged file and file input
    const selectedFile = draggedSingleFile || (fileInput?.files?.length ? fileInput.files[0] : null);
    
    if (!selectedFile) {
        appUtils.showNotification('Please select a resume file', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    resetProgress('single');
    showProgress('single', true);
    appUtils.toggleLoadingScreen(true);

    const progressTimer = animateProgress('single', 88, 12);

    try {
        const data = await postWithFallback(['/api/upload/resume', '/api/upload/single'], formData);

        clearInterval(progressTimer);
        setProgress('single', 100);

        if (data.success) {
            const payload = data.data || {};
            const featureCount = payload.features ? Object.keys(payload.features).length : 0;
            const skillCount = payload.skills ? payload.skills.length : 0;

            statusDetails.innerHTML = `
                <div class="space-y-1">
                    <p>File: <strong>${payload.filename || selectedFile.name}</strong></p>
                    <p>Skills detected: <strong>${skillCount}</strong></p>
                    <p>Feature signals: <strong>${featureCount}</strong></p>
                </div>
            `;

            uploadStatus.classList.remove('hidden');
            renderSingleResult(resultsContent, payload);
            const scoredCandidates = await persistDashboardCandidates([payload]);
            if (scoredCandidates && scoredCandidates.length > 0) {
                renderScorePreview(resultsContent, scoredCandidates[0]);
            }
            appUtils.transitionToResults('resultsSection');
            appUtils.showNotification('Resume processed successfully', 'success');
            
            // Clear the file after successful upload
            draggedSingleFile = null;
            if (fileInput) fileInput.value = '';
        } else {
            throw new Error(data.message || data.error || 'Upload failed');
        }
    } catch (error) {
        clearInterval(progressTimer);
        setProgress('single', 0);
        appUtils.showNotification(error.message || 'Processing failed', 'error');
    } finally {
        appUtils.toggleLoadingScreen(false);
        setTimeout(() => showProgress('single', false), 500);
    }
}

function initializeBatchUpload() {
    const dropZoneBatch = document.getElementById('dropZoneBatch');
    const fileInputBatch = document.getElementById('fileInputBatch');
    const batchForm = document.getElementById('batchForm');

    if (!dropZoneBatch || !fileInputBatch || !batchForm) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
        dropZoneBatch.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    ['dragenter', 'dragover'].forEach((eventName) => {
        dropZoneBatch.addEventListener(eventName, () => {
            dropZoneBatch.classList.add('active');
        });
    });

    ['dragleave', 'drop'].forEach((eventName) => {
        dropZoneBatch.addEventListener(eventName, () => {
            dropZoneBatch.classList.remove('active');
        });
    });

    dropZoneBatch.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        draggedBatchFiles = Array.from(files);
        renderBatchFiles(files);
    });

    dropZoneBatch.addEventListener('click', () => fileInputBatch.click());

    fileInputBatch.addEventListener('change', (e) => {
        draggedBatchFiles = Array.from(e.target.files);
        renderBatchFiles(e.target.files);
    });

    batchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await processBatchUpload();
    });
}

function renderBatchFiles(files) {
    const fileList = document.getElementById('fileList');

    if (!fileList || !files || files.length === 0) {
        if (fileList) fileList.classList.add('hidden');
        return;
    }

    let html = '<h4 class="font-semibold mb-2 text-neon-purple">Selected Files</h4><ul class="space-y-1">';

    for (const file of files) {
        html += `<li class="text-sm text-gray-200">• ${file.name} (${appUtils.formatBytes(file.size)})</li>`;
    }

    html += '</ul>';
    fileList.innerHTML = html;
    fileList.classList.remove('hidden');
}

async function processBatchUpload() {
    const fileInputBatch = document.getElementById('fileInputBatch');
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');

    // Check both dragged files and file input
    const selectedFiles = draggedBatchFiles?.length ? draggedBatchFiles : (fileInputBatch?.files?.length ? Array.from(fileInputBatch.files) : []);
    
    if (!selectedFiles || selectedFiles.length === 0) {
        appUtils.showNotification('Please select resume files', 'error');
        return;
    }

    const formData = new FormData();
    for (const file of selectedFiles) {
        formData.append('files', file);
    }

    resetProgress('batch');
    showProgress('batch', true);
    appUtils.toggleLoadingScreen(true);
    const progressTimer = animateProgress('batch', 90, 9);

    try {
        const data = await postWithFallback(['/api/upload/batch'], formData);

        clearInterval(progressTimer);
        setProgress('batch', 100);

        if (data.success) {
            appUtils.showNotification(
                `Processed ${data.summary?.successful ?? 0}/${data.summary?.total ?? 0} resumes`,
                'success'
            );
            renderBatchResults(resultsContent, data);
            await persistDashboardCandidates(Array.isArray(data.data) ? data.data : []);
            appUtils.transitionToResults('resultsSection');
            
            // Clear the files after successful upload
            draggedBatchFiles = null;
            if (fileInputBatch) fileInputBatch.value = '';
        } else {
            throw new Error(data.message || data.error || 'Batch upload failed');
        }
    } catch (error) {
        clearInterval(progressTimer);
        setProgress('batch', 0);
        appUtils.showNotification(error.message || 'Batch processing failed', 'error');
    } finally {
        appUtils.toggleLoadingScreen(false);
        setTimeout(() => showProgress('batch', false), 500);
    }
}

async function persistDashboardCandidates(resumes) {
    const jobText = (localStorage.getItem('jobDescriptionText') || '').trim();
    const existing = (() => {
        try {
            const raw = localStorage.getItem('dashboardCandidates');
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (_) {
            return [];
        }
    })();

    const candidates = await Promise.all((resumes || []).map(async (resume, index) => {
        const skills = Array.isArray(resume.skills) ? resume.skills : [];
        let matchResult = null;

        if (jobText) {
            try {
                const resp = await fetch('/api/match/similarity', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        resume_text: (resume.cleaned_text || resume.raw_text || skills.join(' ')).toString(),
                        job_description: jobText
                    })
                });
                const result = await resp.json();
                if (resp.ok && result.success) {
                    matchResult = result;
                }
            } catch (_) {
                matchResult = null;
            }
        }

        const finalScore = matchResult ? Number(matchResult.score || 0) : 0;
        const subscores = matchResult?.subscores || {};
        return {
            id: `R-${Date.now()}-${index}`,
            name: resume.filepath ? String(resume.filepath).split('\\').pop().split('/').pop() : `Candidate ${index + 1}`,
            similarity: subscores.semantic || finalScore,
            probability: subscores.keyword || finalScore,
            finalScore: finalScore,
            grade: matchResult?.grade || 'F',
            matchedSkills: matchResult?.matched_skills || skills.slice(0, 8),
            missingSkills: matchResult?.missing_skills || [],
            subscores: subscores,
            explanation: matchResult?.explanation || '',
            ats_score: matchResult?.ats_score || 0
        };
    }));

    localStorage.setItem('dashboardCandidates', JSON.stringify([...existing, ...candidates]));
    return candidates;
}

function renderBatchResults(resultsContent, batchData) {
    let html = `
        <div class="mb-4 result-panel">
            <h4 class="font-semibold mb-3 text-neon-blue">Batch Summary</h4>
            <div class="grid grid-cols-3 gap-4">
                <div class="mini-tile text-center">
                    <p class="text-2xl font-bold text-blue-300">${batchData.summary?.successful ?? 0}</p>
                    <p class="text-sm text-gray-300">Success</p>
                </div>
                <div class="mini-tile text-center">
                    <p class="text-2xl font-bold text-purple-300">${batchData.summary?.failed ?? 0}</p>
                    <p class="text-sm text-gray-300">Failed</p>
                </div>
                <div class="mini-tile text-center">
                    <p class="text-2xl font-bold text-indigo-300">${batchData.summary?.total ?? 0}</p>
                    <p class="text-sm text-gray-300">Total</p>
                </div>
            </div>
        </div>
    `;

    if (Array.isArray(batchData.failed) && batchData.failed.length > 0) {
        html += `
            <div class="mb-4 result-panel">
                <h4 class="font-semibold mb-2 text-red-300">Failed Files</h4>
                <ul class="space-y-1">
                    ${batchData.failed.map(item => 
                        `<li class="text-sm text-red-300">• ${item.filename}: ${item.error}</li>`
                    ).join('')}
                </ul>
            </div>
        `;
    }

    resultsContent.innerHTML = html;
}

function renderSingleResult(resultsContent, payload) {
    const skills = Array.isArray(payload.skills) ? payload.skills : [];
    const education = Array.isArray(payload.education) ? payload.education : [];
    const experience = Array.isArray(payload.experience) ? payload.experience :
                       (Array.isArray(payload.entities?.experience) ? payload.entities.experience : []);
    const organizations = Array.isArray(payload.organizations) ? payload.organizations :
                          (Array.isArray(payload.entities?.organizations) ? payload.entities.organizations : []);
    const locations = Array.isArray(payload.entities?.locations) ? payload.entities.locations : [];
    const contact = payload.contact_info || {
        name: payload.name || '',
        emails: payload.emails || [],
        phones: payload.phones || []
    };

    // ==================== CONTACT CARD ====================
    const contactHtml = `
        <div class="result-panel">
            <h4 class="font-semibold mb-3 text-neon-blue flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                </svg>
                Contact Information
            </h4>
            ${contact.name ? `<p class="text-sm text-white mb-2"><strong>Name:</strong> ${contact.name}</p>` : ''}
            <p class="text-sm text-gray-200 mb-1">
                <strong class="text-gray-100">Email:</strong> 
                ${Array.isArray(contact.emails) && contact.emails.length ? contact.emails.join(', ') : 'N/A'}
            </p>
            <p class="text-sm text-gray-200">
                <strong class="text-gray-100">Phone:</strong> 
                ${Array.isArray(contact.phones) && contact.phones.length ? contact.phones.join(', ') : 'N/A'}
            </p>
        </div>
    `;

    // ==================== SKILLS CARD ====================
    const skillsHtml = `
        <div class="result-panel">
            <h4 class="font-semibold mb-3 text-neon-purple flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"></path>
                </svg>
                Technical Skills (${skills.length})
            </h4>
            <div class="flex flex-wrap gap-2">
                ${skills.length > 0 ? skills.map((skill) => 
                    `<span class="badge badge-success">${skill}</span>`
                ).join('') : '<p class="text-gray-300 text-sm">No skills detected</p>'}
            </div>
        </div>
    `;

    // ==================== EDUCATION CARD ====================
    const educationHtml = `
        <div class="result-panel">
            <h4 class="font-semibold mb-3 text-neon-blue flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M12 14l9-5-9-5-9 5 9 5z"></path>
                    <path d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l9-5-9-5-9 5 9 5zm0 0l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14zm-4 6v-7.5l4-2.222"></path>
                </svg>
                Education
            </h4>
            ${education.length > 0 ? education.map((edu) => `
                <div class="mb-3 pb-3 border-b border-gray-600 last:border-0 last:pb-0">
                    <p class="text-white font-medium">${edu.degree || 'Degree'}</p>
                    ${edu.institution ? `<p class="text-sm text-gray-300 mt-1">${edu.institution}</p>` : ''}
                    ${edu.years ? `<p class="text-xs text-gray-400 mt-1">${edu.years}</p>` : ''}
                </div>
            `).join('') : '<p class="text-gray-300 text-sm">No education detected</p>'}
        </div>
    `;

    // ==================== EXPERIENCE CARD ====================
    const experienceHtml = `
        <div class="result-panel">
            <h4 class="font-semibold mb-3 text-neon-purple flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                </svg>
                Experience
            </h4>
            ${experience.length > 0 ? experience.map((exp) => `
                <div class="mb-3 pb-3 border-b border-gray-600 last:border-0 last:pb-0">
                    <p class="text-white font-medium">${exp.title || 'Position'}</p>
                    ${exp.company ? `<p class="text-sm text-gray-300 mt-1">${exp.company}</p>` : ''}
                    ${exp.duration ? `<p class="text-xs text-gray-400 mt-1">${exp.duration}</p>` : ''}
                </div>
            `).join('') : '<p class="text-gray-300 text-sm">No experience detected</p>'}
        </div>
    `;

    // ==================== ORGANIZATIONS & LOCATIONS CARD ====================
    const entitiesHtml = `
        <div class="result-panel">
            <h4 class="font-semibold mb-3 text-neon-blue flex items-center">
                <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path>
                </svg>
                Organizations & Locations
            </h4>
            ${organizations.length > 0 ? `
                <div class="mb-3">
                    <p class="text-xs text-gray-400 font-semibold mb-1">ORGANIZATIONS</p>
                    <div class="flex flex-wrap gap-1">
                        ${organizations.map(org => `<span class="badge badge-info text-xs">${org}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
            ${locations.length > 0 ? `
                <div>
                    <p class="text-xs text-gray-400 font-semibold mb-1">LOCATIONS</p>
                    <div class="flex flex-wrap gap-1">
                        ${locations.map(loc => `<span class="badge badge-warning text-xs">${loc}</span>`).join('')}
                    </div>
                </div>
            ` : ''}
            ${organizations.length === 0 && locations.length === 0 ? '<p class="text-gray-300 text-sm">No organizations or locations detected</p>' : ''}
        </div>
    `;

    // ==================== RENDER LAYOUT ====================
    resultsContent.innerHTML = `
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            ${contactHtml}
            ${skillsHtml}
            ${educationHtml}
            ${experienceHtml}
            ${entitiesHtml}
        </div>
    `;
}

function renderScorePreview(container, candidate) {
    if (!container || !candidate || !candidate.finalScore) return;
    const score = Math.round(candidate.finalScore);
    const grade = candidate.grade || 'F';
    const subscores = candidate.subscores || {};
    const matched = candidate.matchedSkills || [];
    const missing = candidate.missingSkills || [];

    const gradeColor = score >= 75 ? 'text-green-400' : score >= 60 ? 'text-yellow-400' : 'text-red-400';
    const barColor = score >= 75 ? 'bg-green-500' : score >= 60 ? 'bg-yellow-500' : 'bg-red-500';

    const scoreHtml = `
        <div class="mt-6 result-panel">
            <h4 class="font-semibold mb-4 text-neon-blue flex items-center text-xl">
                Match Score Analysis
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div class="text-center">
                    <p class="text-5xl font-bold ${gradeColor}">${score}%</p>
                    <p class="text-sm text-gray-400 mt-1">Final Score</p>
                </div>
                <div class="text-center">
                    <p class="text-4xl font-bold ${gradeColor}">${grade}</p>
                    <p class="text-sm text-gray-400 mt-1">Grade</p>
                </div>
                <div class="text-center">
                    <p class="text-4xl font-bold text-blue-300">${candidate.ats_score ? Math.round(candidate.ats_score) : '-'}</p>
                    <p class="text-sm text-gray-400 mt-1">ATS Score</p>
                </div>
            </div>
            <div class="mb-4">
                <div class="flex justify-between text-sm mb-1"><span class="text-gray-300">Overall Match</span><span class="text-white font-semibold">${score}%</span></div>
                <div class="w-full bg-gray-700 rounded-full h-3"><div class="${barColor} h-3 rounded-full transition-all" style="width:${score}%"></div></div>
            </div>
            ${Object.keys(subscores).length > 0 ? `
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                    ${subscores.semantic !== undefined ? `<div class="mini-tile text-center"><p class="text-lg font-bold text-blue-300">${Math.round(subscores.semantic)}%</p><p class="text-xs text-gray-400">Semantic</p></div>` : ''}
                    ${subscores.keyword !== undefined ? `<div class="mini-tile text-center"><p class="text-lg font-bold text-purple-300">${Math.round(subscores.keyword)}%</p><p class="text-xs text-gray-400">Keyword</p></div>` : ''}
                    ${subscores.skills !== undefined ? `<div class="mini-tile text-center"><p class="text-lg font-bold text-indigo-300">${Math.round(subscores.skills)}%</p><p class="text-xs text-gray-400">Skills</p></div>` : ''}
                    ${subscores.experience !== undefined ? `<div class="mini-tile text-center"><p class="text-lg font-bold text-cyan-300">${Math.round(subscores.experience)}%</p><p class="text-xs text-gray-400">Experience</p></div>` : ''}
                </div>
            ` : ''}
            ${matched.length > 0 ? `
                <div class="mb-3">
                    <p class="text-sm font-semibold text-green-400 mb-2">Matched Skills (${matched.length})</p>
                    <div class="flex flex-wrap gap-1">${matched.map(s => `<span class="badge badge-success text-xs">${s}</span>`).join('')}</div>
                </div>
            ` : ''}
            ${missing.length > 0 ? `
                <div class="mb-3">
                    <p class="text-sm font-semibold text-red-400 mb-2">Missing Skills (${missing.length})</p>
                    <div class="flex flex-wrap gap-1">${missing.map(s => `<span class="badge badge-error text-xs">${s}</span>`).join('')}</div>
                </div>
            ` : ''}
            ${candidate.explanation ? `<p class="text-sm text-gray-300 mt-3">${candidate.explanation}</p>` : ''}
        </div>
    `;
    container.insertAdjacentHTML('beforeend', scoreHtml);
}

function resetProgress(type) {
    setProgress(type, 0);
}

function setProgress(type, value) {
    const bar = document.getElementById(`${type}ProgressBar`);
    const text = document.getElementById(`${type}ProgressText`);
    if (!bar || !text) return;
    const safeValue = Math.max(0, Math.min(100, value));
    bar.style.width = `${safeValue}%`;
    text.textContent = `${safeValue}%`;
}

function showProgress(type, visible) {
    const wrap = document.getElementById(`${type}ProgressWrap`);
    if (!wrap) return;
    wrap.classList.toggle('hidden', !visible);
}

function animateProgress(type, target = 90, intervalMs = 10) {
    let value = 0;
    return setInterval(() => {
        if (value < target) {
            value += 1;
            setProgress(type, value);
        }
    }, intervalMs);
}

async function postWithFallback(urls, formData) {
    let lastError;

    for (const url of urls) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || data.error || `Request failed (${response.status})`);
            }

            return data;
        } catch (error) {
            lastError = error;
        }
    }

    throw lastError || new Error('Request failed');
}
