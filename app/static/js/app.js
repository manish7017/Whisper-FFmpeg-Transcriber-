/**
 * Whisper Speech-to-Text & FFmpeg Media Transcriber
 * Frontend Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Elements ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const fileSelectedBadge = document.getElementById('file-selected-badge');
    const selectedFileName = document.getElementById('selected-file-name');
    const selectedFileSize = document.getElementById('selected-file-size');
    const clearFileBtn = document.getElementById('clear-file-btn');
    const startTranscribeBtn = document.getElementById('start-transcribe-btn');
    const quickTranscribeBtn = document.getElementById('quick-transcribe-btn');

    // Controls
    const modelSelect = document.getElementById('model-select');
    const languageSelect = document.getElementById('language-select');
    const taskSelect = document.getElementById('task-select');
    const normalizeCheck = document.getElementById('normalize-check');

    // Demo Sample Buttons
    const demoAudioBtn = document.getElementById('demo-audio-btn');
    const demoVideoBtn = document.getElementById('demo-video-btn');

    // Recording Controls
    const recordBtn = document.getElementById('record-btn');
    const recordingModal = document.getElementById('recording-modal');
    const recordTimer = document.getElementById('record-timer');
    const stopRecordBtn = document.getElementById('stop-record-btn');
    const cancelRecordBtn = document.getElementById('cancel-record-btn');
    const recordedAudioPreview = document.getElementById('recorded-audio-preview');
    const useRecordingBtn = document.getElementById('use-recording-btn');

    // Progress Section
    const progressSection = document.getElementById('progress-section');
    const progressBar = document.getElementById('progress-bar');
    const progressPercent = document.getElementById('progress-percent');
    const currentStepText = document.getElementById('current-step-text');
    const stepsList = document.getElementById('steps-list');
    const ffmpegNotice = document.getElementById('ffmpeg-notice');

    // Results Section
    const resultsSection = document.getElementById('results-section');
    const mediaContainer = document.getElementById('media-container');
    const mediaTypeBadge = document.getElementById('media-type-badge');
    const mediaTitle = document.getElementById('media-title');
    const mediaDurationBadge = document.getElementById('media-duration-badge');
    const languageBadge = document.getElementById('language-badge');
    const speedBadge = document.getElementById('speed-badge');

    // Audio Track Switcher (when video)
    const audioTrackSwitcher = document.getElementById('audio-track-switcher');
    const trackOriginalBtn = document.getElementById('track-original-btn');
    const trackExtractedBtn = document.getElementById('track-extracted-btn');

    // Search and Tabs
    const searchInput = document.getElementById('search-input');
    const tabSegments = document.getElementById('tab-segments');
    const tabFullText = document.getElementById('tab-fulltext');
    const tabSubtitles = document.getElementById('tab-subtitles');
    const tabSpecs = document.getElementById('tab-specs');
    const viewSegments = document.getElementById('view-segments');
    const viewFullText = document.getElementById('view-fulltext');
    const viewSubtitles = document.getElementById('view-subtitles');
    const viewSpecs = document.getElementById('view-specs');

    // Content containers
    const segmentsContainer = document.getElementById('segments-container');
    const fullTextContainer = document.getElementById('full-text-content');
    const fullTextStats = document.getElementById('full-text-stats');
    const srtContent = document.getElementById('srt-content');
    const specsContainer = document.getElementById('specs-container');

    // Action buttons
    const copyTranscriptBtn = document.getElementById('copy-transcript-btn');
    const exportTxtBtn = document.getElementById('export-txt-btn');
    const exportSrtBtn = document.getElementById('export-srt-btn');
    const exportVttBtn = document.getElementById('export-vtt-btn');
    const exportJsonBtn = document.getElementById('export-json-btn');
    const exportAudioBtn = document.getElementById('export-audio-btn');

    // Recent Tasks
    const recentTasksContainer = document.getElementById('recent-tasks-container');

    // --- State Variables ---
    let selectedFile = null;
    let currentTask = null;
    let activeMediaElement = null;
    let eventSource = null;
    let isVideoMedia = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let recordInterval = null;
    let recordSeconds = 0;
    let recordedBlob = null;
    let activeSegmentIndex = -1;

    // --- Toast Helper ---
    function showToast(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastText = document.getElementById('toast-text');
        const toastIcon = document.getElementById('toast-icon');

        toastText.textContent = message;
        if (type === 'success') {
            toastIcon.innerHTML = `<svg class="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`;
        } else if (type === 'error') {
            toastIcon.innerHTML = `<svg class="w-5 h-5 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>`;
        } else {
            toastIcon.innerHTML = `<svg class="w-5 h-5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;
        }

        toast.classList.remove('hide');
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
            toast.classList.add('hide');
        }, 3500);
    }

    // --- Format Helper ---
    function formatBytes(bytes, decimals = 1) {
        if (!bytes) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    // --- Prevent browser from opening dropped files outside dropzone ---
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        window.addEventListener(eventName, (e) => {
            e.preventDefault();
        }, false);
    });

    // --- File Selection & Drag-and-Drop ---
    function handleFile(file) {
        if (!file) return;
        selectedFile = file;
        selectedFileName.textContent = file.name;
        selectedFileSize.textContent = formatBytes(file.size);
        fileSelectedBadge.classList.remove('hidden');
        startTranscribeBtn.disabled = false;
        startTranscribeBtn.classList.remove('opacity-50', 'cursor-not-allowed');

        // Check if video
        const isVideo = file.type.startsWith('video/') || /\.(mp4|mkv|mov|avi|webm|flv|wmv|m4v|ts|3gp|ogv)$/i.test(file.name);
        const iconContainer = fileSelectedBadge.querySelector('.file-icon');
        if (iconContainer) {
            iconContainer.textContent = isVideo ? '🎬' : '🎵';
        }

        showToast(`Selected: ${file.name}`, 'info');
    }

    // Trigger file chooser when clicking anywhere on dropzone or browse button
    dropzone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });

    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            fileInput.click();
        });
    }

    if (quickTranscribeBtn) {
        quickTranscribeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            startTranscribeBtn.click();
        });
    }

    clearFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        fileSelectedBadge.classList.add('hidden');
        startTranscribeBtn.disabled = true;
        startTranscribeBtn.classList.add('opacity-50', 'cursor-not-allowed');
    });

    fileInput.addEventListener('click', () => {
        fileInput.value = '';
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    // --- Audio Recording in Browser ---
    recordBtn.addEventListener('click', async () => {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            showToast('Microphone recording not supported in this browser.', 'error');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                recordedBlob = new Blob(audioChunks, { type: 'audio/wav' });
                const audioUrl = URL.createObjectURL(recordedBlob);
                recordedAudioPreview.src = audioUrl;
                recordedAudioPreview.classList.remove('hidden');
                useRecordingBtn.classList.remove('hidden');
                stopRecordBtn.classList.add('hidden');
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            recordingModal.classList.remove('hidden');
            recordSeconds = 0;
            recordTimer.textContent = '00:00';
            stopRecordBtn.classList.remove('hidden');
            useRecordingBtn.classList.add('hidden');
            recordedAudioPreview.classList.add('hidden');

            recordInterval = setInterval(() => {
                recordSeconds++;
                recordTimer.textContent = formatTime(recordSeconds);
            }, 1000);

        } catch (err) {
            console.error('Mic access error:', err);
            showToast('Microphone access denied or unavailable.', 'error');
        }
    });

    stopRecordBtn.addEventListener('click', () => {
        clearInterval(recordInterval);
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
    });

    cancelRecordBtn.addEventListener('click', () => {
        clearInterval(recordInterval);
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        recordingModal.classList.add('hidden');
    });

    useRecordingBtn.addEventListener('click', () => {
        if (!recordedBlob) return;
        const file = new File([recordedBlob], `voice_recording_${Date.now()}.wav`, { type: 'audio/wav' });
        handleFile(file);
        recordingModal.classList.add('hidden');
        showToast('Voice recording ready for transcription!', 'success');
    });

    // --- Instant Demo Triggers ---
    demoAudioBtn.addEventListener('click', () => triggerSampleTranscription('sample_audio'));
    demoVideoBtn.addEventListener('click', () => triggerSampleTranscription('sample_video'));

    async function triggerSampleTranscription(sampleId) {
        resetWorkspace();
        showProgressView();

        const formData = new FormData();
        formData.append('sample_id', sampleId);
        formData.append('model_name', modelSelect.value);
        formData.append('language', languageSelect.value);
        formData.append('task', taskSelect.value);
        formData.append('normalize', normalizeCheck.checked);

        try {
            const resp = await fetch('/api/transcribe-sample', {
                method: 'POST',
                body: formData,
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || 'Failed to start demo transcription');
            }

            const data = await resp.json();
            listenToTaskProgress(data.task_id);
        } catch (error) {
            handlePipelineError(error.message);
        }
    }

    // --- Start Transcription Upload with Upload Progress ---
    startTranscribeBtn.addEventListener('click', () => {
        if (!selectedFile) {
            showToast('Please select or record a media file first.', 'error');
            return;
        }

        resetWorkspace();
        showProgressView();

        const isVideo = selectedFile.type.startsWith('video/') || /\.(mp4|mkv|mov|avi|webm|flv|wmv|m4v|ts|3gp|ogv)$/i.test(selectedFile.name);
        if (isVideo) {
            ffmpegNotice.classList.remove('hidden');
        }

        currentStepText.textContent = `Uploading ${selectedFile.name} (${formatBytes(selectedFile.size)})...`;
        progressBar.style.width = '5%';
        progressPercent.textContent = '5%';

        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('model_name', modelSelect.value);
        formData.append('language', languageSelect.value);
        formData.append('task', taskSelect.value);
        formData.append('normalize', normalizeCheck.checked);

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/transcribe', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable && e.total > 0) {
                const percent = Math.min(Math.round((e.loaded / e.total) * 30), 30);
                progressBar.style.width = `${percent}%`;
                progressPercent.textContent = `${percent}%`;
                currentStepText.textContent = `Uploading: ${formatBytes(e.loaded)} / ${formatBytes(e.total)} (${Math.round((e.loaded / e.total) * 100)}%)`;
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const data = JSON.parse(xhr.responseText);
                    progressBar.style.width = '30%';
                    progressPercent.textContent = '30%';
                    currentStepText.textContent = 'Upload complete! Starting pipeline...';
                    listenToTaskProgress(data.task_id);
                } catch (e) {
                    handlePipelineError('Failed to parse server response.');
                }
            } else {
                let err = 'Upload failed';
                try {
                    const res = JSON.parse(xhr.responseText);
                    err = res.detail || err;
                } catch (e) {}
                handlePipelineError(err);
            }
        };

        xhr.onerror = () => {
            handlePipelineError('Network connection error during file upload.');
        };

        xhr.send(formData);
    });

    // --- Task Progress via SSE & Polling ---
    function listenToTaskProgress(taskId) {
        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(`/api/tasks/${taskId}/events`);

        eventSource.onmessage = (event) => {
            try {
                const task = JSON.parse(event.data);
                updateProgressUI(task);

                if (task.status === 'completed') {
                    eventSource.close();
                    currentTask = task;
                    setTimeout(() => renderCompletedResults(task), 400);
                } else if (task.status === 'failed') {
                    eventSource.close();
                    handlePipelineError(task.error || 'Transcription failed.');
                }
            } catch (err) {
                console.error('SSE parsing error:', err);
            }
        };

        eventSource.onerror = () => {
            // Fallback to polling if SSE has network interruption
            console.warn('SSE disconnected. Switching to polling fallback.');
            eventSource.close();
            startPollingFallback(taskId);
        };
    }

    function startPollingFallback(taskId) {
        const interval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/tasks/${taskId}`);
                if (!resp.ok) return;
                const task = await resp.json();
                updateProgressUI(task);

                if (task.status === 'completed') {
                    clearInterval(interval);
                    currentTask = task;
                    renderCompletedResults(task);
                } else if (task.status === 'failed') {
                    clearInterval(interval);
                    handlePipelineError(task.error || 'Transcription failed');
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
        }, 1200);
    }

    function updateProgressUI(task) {
        progressBar.style.width = `${task.progress}%`;
        progressPercent.textContent = `${task.progress}%`;
        currentStepText.textContent = task.current_step;

        // Video + FFmpeg Badge
        if (task.is_video) {
            ffmpegNotice.classList.remove('hidden');
        }

        // Render steps
        stepsList.innerHTML = '';
        (task.steps || []).forEach((s, idx) => {
            const stepEl = document.createElement('div');
            stepEl.className = 'flex items-start space-x-3 text-sm animate-fade-in';
            const isLast = idx === task.steps.length - 1;
            const iconHtml = isLast && task.status !== 'completed'
                ? `<div class="w-5 h-5 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin flex-shrink-0 mt-0.5"></div>`
                : `<div class="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0 mt-0.5 text-xs">✓</div>`;

            stepEl.innerHTML = `
                ${iconHtml}
                <div class="flex-1">
                    <p class="font-medium text-slate-200">${s.title}</p>
                    ${s.detail ? `<p class="text-xs text-slate-400 font-mono mt-0.5 break-all">${s.detail}</p>` : ''}
                </div>
                <span class="text-xs text-slate-500 font-mono">${s.timestamp}s</span>
            `;
            stepsList.appendChild(stepEl);
        });
    }

    function handlePipelineError(message) {
        progressBar.classList.remove('bg-indigo-600');
        progressBar.classList.add('bg-rose-600');
        currentStepText.textContent = `Error: ${message}`;
        showToast(message, 'error');
    }

    function showProgressView() {
        progressSection.classList.remove('hidden');
        resultsSection.classList.add('hidden');
        progressBar.style.width = '5%';
        progressPercent.textContent = '5%';
        currentStepText.textContent = 'Uploading and probing media...';
        stepsList.innerHTML = '';
        ffmpegNotice.classList.add('hidden');
        progressSection.scrollIntoView({ behavior: 'smooth' });
    }

    function resetWorkspace() {
        if (eventSource) eventSource.close();
        if (activeMediaElement) {
            activeMediaElement.pause();
            activeMediaElement.src = '';
        }
    }

    // --- Render Completed Results ---
    function renderCompletedResults(task) {
        progressSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        resultsSection.scrollIntoView({ behavior: 'smooth' });

        const result = task.result || {};
        isVideoMedia = task.is_video;

        // Badges
        mediaTitle.textContent = task.original_filename;
        mediaTypeBadge.innerHTML = isVideoMedia
            ? `<span class="bg-purple-900/50 text-purple-300 border border-purple-700/50 px-2.5 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5">🎬 Video Transcribed via FFmpeg</span>`
            : `<span class="bg-sky-900/50 text-sky-300 border border-sky-700/50 px-2.5 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5">🎵 Audio Transcribed</span>`;

        mediaDurationBadge.textContent = `Duration: ${result.audio_duration_fmt || '00:00'}`;
        languageBadge.textContent = `Lang: ${(result.language || 'en').toUpperCase()}`;
        speedBadge.textContent = `Speed: ${result.speed_factor || 1}x Realtime`;

        // Render Media Player
        setupMediaPlayer(task);

        // Render Transcript Views
        renderSegments(result.segments || []);
        renderFullText(result.text || '', result);
        renderSubtitles(result.srt || '');
        renderSpecs(task);

        // Setup Export links
        setupExportButtons(task.task_id);

        showToast('Transcription completed successfully!', 'success');
        loadRecentTasks();
    }

    // --- Media Player Setup ---
    function setupMediaPlayer(task) {
        mediaContainer.innerHTML = '';

        if (task.is_video) {
            // Render HTML5 Video Player
            const videoEl = document.createElement('video');
            videoEl.id = 'active-media-player';
            videoEl.controls = true;
            videoEl.className = 'w-full rounded-xl max-h-[420px] bg-black shadow-2xl';
            videoEl.src = `/api/media/${task.task_id}/original`;
            mediaContainer.appendChild(videoEl);
            activeMediaElement = videoEl;

            // Show audio track switcher (allows listening to FFmpeg extracted WAV)
            audioTrackSwitcher.classList.remove('hidden');
            trackOriginalBtn.onclick = () => {
                videoEl.src = `/api/media/${task.task_id}/original`;
                videoEl.play();
                trackOriginalBtn.classList.add('bg-indigo-600', 'text-white');
                trackOriginalBtn.classList.remove('bg-slate-800', 'text-slate-300');
                trackExtractedBtn.classList.remove('bg-indigo-600', 'text-white');
                trackExtractedBtn.classList.add('bg-slate-800', 'text-slate-300');
            };
            trackExtractedBtn.onclick = () => {
                videoEl.src = `/api/media/${task.task_id}/audio`;
                videoEl.play();
                trackExtractedBtn.classList.add('bg-indigo-600', 'text-white');
                trackExtractedBtn.classList.remove('bg-slate-800', 'text-slate-300');
                trackOriginalBtn.classList.remove('bg-indigo-600', 'text-white');
                trackOriginalBtn.classList.add('bg-slate-800', 'text-slate-300');
            };
        } else {
            // Render HTML5 Audio Player
            const audioWrapper = document.createElement('div');
            audioWrapper.className = 'p-6 bg-slate-900/80 rounded-xl border border-slate-700/50 flex flex-col items-center justify-center space-y-4';
            audioWrapper.innerHTML = `
                <div class="w-16 h-16 rounded-full bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-3xl">
                    🎵
                </div>
                <audio id="active-media-player" controls class="w-full max-w-md" src="/api/media/${task.task_id}/original"></audio>
            `;
            mediaContainer.appendChild(audioWrapper);
            activeMediaElement = audioWrapper.querySelector('audio');
            audioTrackSwitcher.classList.add('hidden');
        }

        // Synchronize Media Player with Transcript Segments!
        if (activeMediaElement) {
            activeMediaElement.addEventListener('timeupdate', () => {
                syncPlaybackWithTranscript(activeMediaElement.currentTime);
            });
        }
    }

    // --- Synchronize Playback with Segments ---
    function syncPlaybackWithTranscript(currentTime) {
        if (!currentTask || !currentTask.result || !currentTask.result.segments) return;
        const segments = currentTask.result.segments;

        const currentIdx = segments.findIndex(s => currentTime >= s.start && currentTime <= s.end);

        if (currentIdx !== activeSegmentIndex) {
            // Remove previous active
            if (activeSegmentIndex !== -1) {
                const prevEl = document.getElementById(`seg-card-${activeSegmentIndex}`);
                if (prevEl) prevEl.classList.remove('active-segment');
            }

            activeSegmentIndex = currentIdx;

            // Highlight new active
            if (currentIdx !== -1) {
                const activeEl = document.getElementById(`seg-card-${currentIdx}`);
                if (activeEl) {
                    activeEl.classList.add('active-segment');
                    // Smoothly scroll active segment into view if inside container
                    activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
        }
    }

    // --- Render Segments ---
    function renderSegments(segments) {
        segmentsContainer.innerHTML = '';
        if (!segments || segments.length === 0) {
            segmentsContainer.innerHTML = `<div class="p-8 text-center text-slate-400">No speech detected or transcript empty.</div>`;
            return;
        }

        segments.forEach((seg, idx) => {
            const card = document.createElement('div');
            card.id = `seg-card-${idx}`;
            card.className = 'segment-card p-3 rounded-lg bg-slate-800/40 border border-slate-700/40 flex items-start space-x-3 cursor-pointer select-text';
            
            card.innerHTML = `
                <button class="timestamp-btn px-2 py-1 rounded bg-indigo-950/80 text-indigo-300 hover:bg-indigo-600 hover:text-white border border-indigo-700/50 text-xs font-mono font-medium transition flex-shrink-0"
                    title="Click to seek media player to this timestamp">
                    ▶ ${seg.start_fmt}
                </button>
                <div class="flex-1">
                    <p class="segment-text text-sm text-slate-200 leading-relaxed">${escapeHtml(seg.text)}</p>
                </div>
                <button class="copy-seg-btn text-slate-500 hover:text-slate-300 p-1 rounded" title="Copy segment text">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                </button>
            `;

            // Click timestamp to seek media
            const btn = card.querySelector('.timestamp-btn');
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                seekMediaTo(seg.start);
            });

            // Click card body to seek
            card.addEventListener('click', () => {
                seekMediaTo(seg.start);
            });

            // Copy segment
            const copyBtn = card.querySelector('.copy-seg-btn');
            copyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(seg.text);
                showToast('Segment copied!', 'success');
            });

            segmentsContainer.appendChild(card);
        });
    }

    function seekMediaTo(seconds) {
        if (activeMediaElement) {
            activeMediaElement.currentTime = seconds;
            activeMediaElement.play();
        }
    }

    // --- Render Full Text ---
    function renderFullText(text, result) {
        fullTextContainer.textContent = text || 'No transcript text available.';
        const words = (result.word_count || (text ? text.split(/\s+/).length : 0));
        const readTime = Math.ceil(words / 150);
        fullTextStats.textContent = `${words} words • ~${readTime} min read time`;
    }

    // --- Render Subtitles ---
    function renderSubtitles(srt) {
        srtContent.textContent = srt || 'No subtitles available.';
    }

    // --- Render Specs View ---
    function renderSpecs(task) {
        const info = task.media_info || {};
        const ffmpeg = task.ffmpeg_result || {};
        const res = task.result || {};

        specsContainer.innerHTML = `
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <!-- Media Source Specs -->
                <div class="p-4 rounded-xl bg-slate-900/60 border border-slate-700/50 space-y-2">
                    <h4 class="text-sm font-semibold text-indigo-300 flex items-center gap-2">
                        <span>📁</span> Uploaded Media Metadata
                    </h4>
                    <ul class="text-xs space-y-1 text-slate-300 font-mono">
                        <li><strong class="text-slate-400">File Name:</strong> ${task.original_filename}</li>
                        <li><strong class="text-slate-400">Media Type:</strong> ${task.is_video ? 'Video with Audio Stream' : 'Audio File'}</li>
                        <li><strong class="text-slate-400">Duration:</strong> ${info.duration_formatted || info.duration || '0'}s</li>
                        <li><strong class="text-slate-400">File Size:</strong> ${info.size_mb || 0} MB</li>
                        <li><strong class="text-slate-400">Audio Codec:</strong> ${info.audio_codec || 'N/A'}</li>
                        ${info.video_codec ? `<li><strong class="text-slate-400">Video Codec:</strong> ${info.video_codec} (${info.video_resolution})</li>` : ''}
                    </ul>
                </div>

                <!-- FFmpeg Processing Specs -->
                <div class="p-4 rounded-xl bg-slate-900/60 border border-slate-700/50 space-y-2">
                    <h4 class="text-sm font-semibold text-purple-300 flex items-center gap-2">
                        <span>⚡</span> FFmpeg Audio Extraction Pipeline
                    </h4>
                    <ul class="text-xs space-y-1 text-slate-300 font-mono">
                        <li><strong class="text-slate-400">Status:</strong> ${ffmpeg.success ? 'Extracted & Normalized' : 'N/A'}</li>
                        <li><strong class="text-slate-400">Target Sample Rate:</strong> 16,000 Hz Mono PCM</li>
                        <li><strong class="text-slate-400">Extraction Time:</strong> ${ffmpeg.elapsed_seconds || 0} seconds</li>
                        <li><strong class="text-slate-400">Audio Stream Size:</strong> ${ffmpeg.output_size_mb || 0} MB</li>
                    </ul>
                </div>
            </div>

            <!-- FFmpeg Command Execution Log -->
            ${ffmpeg.command ? `
                <div class="mt-4 p-4 rounded-xl bg-black/60 border border-slate-800">
                    <p class="text-xs font-semibold text-slate-400 mb-1">Executed FFmpeg Command:</p>
                    <code class="text-xs text-emerald-400 font-mono break-all">${escapeHtml(ffmpeg.command)}</code>
                </div>
            ` : ''}

            <!-- Whisper AI Model Specs -->
            <div class="mt-4 p-4 rounded-xl bg-slate-900/60 border border-slate-700/50">
                <h4 class="text-sm font-semibold text-sky-300 mb-2 flex items-center gap-2">
                    <span>🧠</span> Whisper Speech-to-Text Model Metrics
                </h4>
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                    <div class="p-3 bg-slate-800/50 rounded-lg">
                        <div class="text-xs text-slate-400">Model Used</div>
                        <div class="text-base font-bold text-white uppercase">${res.model || 'base'}</div>
                    </div>
                    <div class="p-3 bg-slate-800/50 rounded-lg">
                        <div class="text-xs text-slate-400">Compute Device</div>
                        <div class="text-base font-bold text-emerald-400 uppercase">${res.device || 'CPU'}</div>
                    </div>
                    <div class="p-3 bg-slate-800/50 rounded-lg">
                        <div class="text-xs text-slate-400">Inference Time</div>
                        <div class="text-base font-bold text-white">${res.transcription_seconds || 0}s</div>
                    </div>
                    <div class="p-3 bg-slate-800/50 rounded-lg">
                        <div class="text-xs text-slate-400">Speed Ratio</div>
                        <div class="text-base font-bold text-sky-400">${res.speed_factor || 1}x</div>
                    </div>
                </div>
            </div>
        `;
    }

    // --- Search / Filter in Segments ---
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        const cards = segmentsContainer.querySelectorAll('.segment-card');

        cards.forEach(card => {
            const textEl = card.querySelector('.segment-text');
            const text = textEl.textContent.toLowerCase();
            if (!query || text.includes(query)) {
                card.style.display = 'flex';
                if (query) {
                    highlightText(textEl, query);
                } else {
                    textEl.innerHTML = escapeHtml(textEl.textContent);
                }
            } else {
                card.style.display = 'none';
            }
        });
    });

    function highlightText(element, query) {
        const raw = element.textContent;
        const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
        element.innerHTML = raw.replace(regex, '<mark class="bg-amber-400/40 text-amber-200 px-0.5 rounded">$1</mark>');
    }

    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    // --- Tab Switching ---
    function setupTabs() {
        const tabs = [
            { btn: tabSegments, view: viewSegments },
            { btn: tabFullText, view: viewFullText },
            { btn: tabSubtitles, view: viewSubtitles },
            { btn: tabSpecs, view: viewSpecs },
        ];

        tabs.forEach(({ btn, view }) => {
            btn.addEventListener('click', () => {
                tabs.forEach(t => {
                    t.btn.classList.remove('active-tab', 'border-indigo-500', 'text-indigo-400');
                    t.btn.classList.add('border-transparent', 'text-slate-400');
                    t.view.classList.add('hidden');
                });
                btn.classList.add('active-tab', 'border-indigo-500', 'text-indigo-400');
                btn.classList.remove('border-transparent', 'text-slate-400');
                view.classList.remove('hidden');
            });
        });
    }
    setupTabs();

    // --- Export & Download Triggers ---
    function setupExportButtons(taskId) {
        copyTranscriptBtn.onclick = () => {
            if (currentTask && currentTask.result) {
                navigator.clipboard.writeText(currentTask.result.text);
                showToast('Full transcript copied to clipboard!', 'success');
            }
        };

        exportTxtBtn.onclick = () => window.open(`/api/export/${taskId}/txt`, '_blank');
        exportSrtBtn.onclick = () => window.open(`/api/export/${taskId}/srt`, '_blank');
        exportVttBtn.onclick = () => window.open(`/api/export/${taskId}/vtt`, '_blank');
        exportJsonBtn.onclick = () => window.open(`/api/export/${taskId}/json`, '_blank');

        if (isVideoMedia) {
            exportAudioBtn.classList.remove('hidden');
            exportAudioBtn.onclick = () => window.open(`/api/export/${taskId}/audio`, '_blank');
        } else {
            exportAudioBtn.classList.add('hidden');
        }
    }

    // --- Recent Tasks ---
    async function loadRecentTasks() {
        try {
            const resp = await fetch('/api/tasks');
            if (!resp.ok) return;
            const data = await resp.json();
            const tasks = data.tasks || [];

            if (tasks.length === 0) {
                recentTasksContainer.innerHTML = `<p class="text-xs text-slate-500">No previous transcriptions in this session.</p>`;
                return;
            }

            recentTasksContainer.innerHTML = '';
            tasks.forEach(t => {
                const item = document.createElement('div');
                item.className = 'p-2.5 rounded-lg bg-slate-800/40 hover:bg-slate-700/50 border border-slate-700/40 cursor-pointer flex items-center justify-between text-xs transition';
                item.innerHTML = `
                    <div class="flex items-center space-x-2 truncate">
                        <span>${t.is_video ? '🎬' : '🎵'}</span>
                        <span class="truncate font-medium text-slate-300">${t.original_filename}</span>
                    </div>
                    <span class="text-slate-500 font-mono ml-2">${t.result ? t.result.audio_duration_fmt || '' : t.status}</span>
                `;
                item.onclick = () => {
                    if (t.status === 'completed') {
                        currentTask = t;
                        renderCompletedResults(t);
                    }
                };
                recentTasksContainer.appendChild(item);
            });
        } catch (e) {
            console.warn('Could not load recent tasks:', e);
        }
    }
    loadRecentTasks();
});
