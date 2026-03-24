/* ===== MONACO EDITOR + EXAM CONTROLLER ===== */
(async () => {
    // Auth guard
    const user = requireAuth('student');
    if (!user) return;

    // Parse query params
    const params = new URLSearchParams(location.search);
    const testId = params.get('testId');
    // problems can come from URL or we auto-fetch from testId
    let problemIds = (params.get('problems') || '').split(',').filter(Boolean);

    if (!testId) {
        document.getElementById('exam-title').textContent = 'Invalid exam link';
        return;
    }

    // State
    let currentProblemIndex = 0;
    let problems = [];
    let monacoEditor = null;
    const codeStore = {}; // { problemId: { lang: code } }

    // Fetch test info first (this also gives us the problem IDs if not in URL)
    let testDuration = 60;
    let testData = null;
    try {
        testData = await API.get(`/api/tests/${testId}`);
        document.getElementById('exam-title').textContent = testData.title || 'Exam';
        testDuration = testData.duration || 60;
        // If problem IDs weren't in URL, get them from the test data
        if (!problemIds.length && testData.problems && testData.problems.length) {
            problemIds = testData.problems;
        }
    } catch (e) {
        document.getElementById('exam-title').textContent = 'Error loading test';
        showToast('Failed to load test: ' + e.message, 'error');
        return;
    }

    if (!problemIds.length) {
        document.getElementById('exam-title').textContent = 'No problems found for this test';
        return;
    }

    // Check if test is currently available
    if (testData) {
        const now = new Date();
        const st = testData.startTime ? new Date(testData.startTime) : null;
        const et = testData.endTime ? new Date(testData.endTime) : null;
        if (st && now < st) {
            document.getElementById('exam-title').textContent = 'This test has not started yet';
            document.getElementById('prob-title').textContent = `Starts at: ${st.toLocaleString()}`;
            document.getElementById('prob-desc').textContent = 'Please come back when the test is active.';
            document.getElementById('start-overlay').style.display = 'none';
            return;
        }
        if (et && now > et) {
            document.getElementById('exam-title').textContent = 'This test has ended';
            document.getElementById('prob-title').textContent = `Ended at: ${et.toLocaleString()}`;
            document.getElementById('prob-desc').textContent = 'This test is no longer available.';
            document.getElementById('start-overlay').style.display = 'none';
            setTimeout(() => { window.location.href = '/student/dashboard'; }, 3000);
            return;
        }

        // If the test has an end time, automatically submit/refresh when it is reached
        if (et && now < et) {
            const msUntilEnd = et.getTime() - now.getTime();
            // Optional: If we want to strictly limit timer duration to not exceed endTime
            const maxAllowedMinutes = Math.floor(msUntilEnd / 60000);
            if (testDuration > maxAllowedMinutes) {
                testDuration = maxAllowedMinutes;
            }

            // Auto-refresh the page at the exact end time
            setTimeout(() => {
                window.location.reload();
            }, msUntilEnd);
        }
    }

    // Fetch all problems
    for (const pid of problemIds) {
        try {
            const p = await API.get(`/api/problems/${pid}`);
            problems.push(p);
        } catch (e) { console.warn('Could not load problem', pid); }
    }

    if (!problems.length) {
        document.getElementById('exam-title').textContent = 'No problems could be loaded';
        return;
    }

    // Render problem selector tabs
    const selEl = document.getElementById('problem-selector');
    problems.forEach((p, i) => {
        const btn = document.createElement('button');
        btn.className = `btn btn-outline btn-sm${i === 0 ? ' active' : ''}`;
        btn.style.minWidth = '90px';
        btn.textContent = `Q${i + 1}`;
        btn.onclick = () => switchProblem(i);
        btn.id = `prob-tab-${i}`;
        selEl.appendChild(btn);
    });

    function switchProblem(idx) {
        currentProblemIndex = idx;
        const p = problems[idx];
        document.getElementById('prob-title').textContent = p.title;
        document.getElementById('prob-desc').textContent = p.description;

        // Render sample cases
        const casesEl = document.getElementById('sample-cases');
        casesEl.innerHTML = '';
        (p.sampleTestCases || []).forEach((tc, i) => {
            casesEl.innerHTML += `
        <div class="test-case-block">
          <label>Case ${i + 1}</label>
          <label>Input</label><pre>${tc.input || ''}</pre>
          <label>Expected Output</label><pre>${tc.output || ''}</pre>
        </div>`;
        });

        // Restore stored code
        const lang = document.getElementById('lang-select').value;
        if (monacoEditor) {
            const stored = (codeStore[p.id] || {})[lang] || getDefaultCode(lang);
            monacoEditor.setValue(stored);
        }

        // Update tab highlight
        problems.forEach((_, i) => {
            const t = document.getElementById(`prob-tab-${i}`);
            if (t) t.className = `btn btn-outline btn-sm${i === idx ? ' active' : ''}`;
        });

        document.getElementById('output-cases').innerHTML =
            '<p style="color:var(--text-muted);font-size:.82rem;">Click \u25b6 Run to execute against sample test cases.</p>';
        document.getElementById('test-summary').textContent = '';
    }

    // Init Monaco
    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
    require(['vs/editor/editor.main'], () => {
        monacoEditor = monaco.editor.create(document.getElementById('monaco-editor'), {
            value: getDefaultCode('python'),
            language: 'python',
            theme: 'vs-dark',
            fontSize: 14,
            fontFamily: "'Fira Code', monospace",
            minimap: { enabled: false },
            wordWrap: 'on',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            tabSize: 4,
        });

        // Expose globally for complexity analyzer
        window.monacoEditor = monacoEditor;

        // Auto-save code on change
        monacoEditor.onDidChangeModelContent(() => {
            const p = problems[currentProblemIndex];
            const lang = document.getElementById('lang-select').value;
            if (!codeStore[p.id]) codeStore[p.id] = {};
            codeStore[p.id][lang] = monacoEditor.getValue();
        });

        // Display first problem
        if (problems.length > 0) switchProblem(0);

        window.startExamFullscreen = () => {
            const el = document.documentElement;
            if (el.requestFullscreen) {
                el.requestFullscreen().catch(() => { });
            } else if (el.webkitRequestFullscreen) {
                el.webkitRequestFullscreen();
            } else if (el.msRequestFullscreen) {
                el.msRequestFullscreen();
            }
            document.getElementById('start-overlay').style.display = 'none';

            // Init anti-cheat and timer only after starting
            AntiCheat.init(testId);

            const storedEnd = sessionStorage.getItem('terv_timer_end');
            if (storedEnd && parseInt(storedEnd) > Date.now()) {
                Timer.resume(autoSubmitAll);
            } else {
                Timer.start(testDuration, autoSubmitAll);
            }
        };
    });

    // Language change
    window.changeLanguage = (lang) => {
        if (!monacoEditor) return;
        const p = problems[currentProblemIndex];
        // Restore stored or default
        const code = (codeStore[p?.id] || {})[lang] || getDefaultCode(lang);
        const model = monacoEditor.getModel();
        monaco.editor.setModelLanguage(model, monacoToLang(lang));
        monacoEditor.setValue(code);
    };

    // Run code
    window.runCode = async () => {
        if (!monacoEditor) return;
        const p = problems[currentProblemIndex];
        const code = monacoEditor.getValue();
        const lang = document.getElementById('lang-select').value;
        const statusEl = document.getElementById('run-status');
        const outputEl = document.getElementById('output-cases');
        const summaryEl = document.getElementById('test-summary');
        statusEl.textContent = '\u23f3 Running\u2026';
        outputEl.innerHTML = '';
        try {
            const res = await API.post('/api/submissions/run', { code, language: lang, problemId: p.id });
            const results = res.results || [];
            let passed = 0;
            const numSampleCases = (p.sampleTestCases || []).length;
            results.forEach(r => {
                if (r.passed) passed++;
                const isHidden = r.isHidden !== undefined ? r.isHidden : r.caseIndex >= numSampleCases;
                const displayName = isHidden ? `Hidden Case ${r.caseIndex - numSampleCases + 1}` : `Sample Case ${r.caseIndex + 1}`;

                let detailsHtml = '';
                if (!isHidden) {
                    detailsHtml = `
                    <div style="margin-top:8px;font-size:0.8rem;background:rgba(0,0,0,0.2);padding:8px;border-radius:4px;border:1px solid var(--border-subtle);width:100%;">
                        <div style="margin-bottom:4px;"><strong style="color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;">Input:</strong><br><pre style="color:var(--text-primary);margin:0;white-space:pre-wrap;font-family:var(--font-code);">${r.input || ''}</pre></div>
                        <div style="margin-bottom:4px;"><strong style="color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;">Expected Output:</strong><br><pre style="color:var(--neon-green);margin:0;white-space:pre-wrap;font-family:var(--font-code);">${r.expected || ''}</pre></div>
                        <div><strong style="color:var(--text-muted);font-size:0.75rem;text-transform:uppercase;">Your Output:</strong><br><pre style="color:${r.passed ? 'var(--neon-green)' : '#f87171'};margin:0;white-space:pre-wrap;font-family:var(--font-code);">${r.actual || ''}</pre></div>
                    </div>`;
                }

                outputEl.innerHTML += `
          <div class="case-result ${r.passed ? 'passed' : 'failed'}" style="flex-direction:column;align-items:stretch;gap:8px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <span class="case-icon">${r.passed ? '✅' : '❌'}</span>
                <span>${displayName}: ${r.passed ? 'Passed' : r.error || 'Wrong Answer'}</span>
                <span style="margin-left:auto;font-size:.75rem;color:var(--text-muted);">${r.time}s</span>
            </div>
            ${detailsHtml}
          </div>`;
                if (!r.passed && r.stderr) {
                    outputEl.innerHTML += `<pre style="font-size:.75rem;color:#f87171;padding:8px 12px;background:rgba(239,68,68,.06);border-radius:6px;white-space:pre-wrap;margin-top:8px;width:100%;box-sizing:border-box;">${r.stderr}</pre>`;
                }
            });
            summaryEl.textContent = `${passed}/${results.length} passed`;
            statusEl.textContent = '';
        } catch (e) {
            statusEl.textContent = '';
            outputEl.innerHTML = `<p style="color:#f87171;font-size:.82rem;">${e.message}</p>`;
        }
    };

    // Submit entire exam manually
    window.submitSolution = async () => {
        if (!monacoEditor) return;
        if (!confirm("Are you sure you want to finish and submit the entire exam? You will not be able to return.")) return;
        await window.autoSubmitAll();
    };

    // Auto-submit all (called by timer or anti-cheat)
    window.autoSubmitAll = async () => {
        Timer.stop();
        if (typeof AntiCheat !== 'undefined' && AntiCheat.clearUnload) {
            AntiCheat.clearUnload();
        }
        const btn = document.getElementById('submit-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Submitting\u2026'; }
        let totalPoints = 0;
        let maxPoints = 0;
        for (const p of problems) {
            const res = await _submitProblem(p, true);
            if (res) {
                totalPoints += (res.points || 0);
                maxPoints += (res.maxScore || 100);
            }
        }
        // Exit fullscreen before showing completion banner
        if (document.fullscreenElement) {
            document.exitFullscreen().catch(() => { });
        }
        showCompletionBanner(totalPoints, maxPoints);
    };

    function showCompletionBanner(points, max) {
        const pct = max > 0 ? Math.round((points / max) * 100) : 0;
        const emoji = pct >= 80 ? '\ud83c\udfc6' : pct >= 50 ? '\u2705' : '\ud83d\udccb';
        const msg = pct >= 80 ? 'Excellent work!' : pct >= 50 ? 'Good effort!' : 'Exam submitted.';
        const banner = document.createElement('div');
        banner.className = 'completion-banner';
        banner.innerHTML = `
            <div class="completion-card">
                <div class="completion-icon">${emoji}</div>
                <div class="completion-title">EXAM COMPLETE</div>
                <div class="completion-score">${points} / ${max}</div>
                <div style="font-size:.75rem;color:var(--text-muted);margin-bottom:8px;">${points} out of ${max} points \u2014 ${pct}%</div>
                <div class="completion-sub">${msg} Returning to dashboard\u2026</div>
                <div style="background:rgba(255,255,255,.06);border-radius:var(--radius-md);height:4px;overflow:hidden;margin-top:8px;">
                    <div id="redirect-bar" style="height:100%;width:100%;background:var(--gradient-primary);border-radius:var(--radius-md);transition:width 4s linear;"></div>
                </div>
            </div>`;
        document.body.appendChild(banner);
        setTimeout(() => {
            const bar = document.getElementById('redirect-bar');
            if (bar) bar.style.width = '0%';
        }, 50);
        setTimeout(() => { window.location.href = '/student/dashboard'; }, 4000);
    }


    async function _submitProblem(p, silent = false) {
        if (!p) return null;
        const lang = document.getElementById('lang-select').value;
        const code = (codeStore[p.id] || {})[lang] || monacoEditor.getValue();
        try {
            const res = await API.post('/api/submissions/submit', {
                code, language: lang, problemId: p.id, testId
            });
            if (!silent) {
                showToast(
                    `Submitted! Score: ${res.score} pts \u2014 ${res.testCases}`,
                    res.points === res.maxScore ? 'success' : 'warn'
                );
            }
            return res;
        } catch (e) {
            if (!silent) showToast(`Submit failed: ${e.message}`, 'error');
            return null;
        }
    }

    function getDefaultCode(lang) {
        const defaults = {
            python: '# Write your solution here\ndef solution():\n    pass\n\nsolution()',
            javascript: '// Write your solution here\nfunction solution() {\n\n}\n\nsolution();',
            java: 'public class Main {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}',
            c: '#include <stdio.h>\n\nint main() {\n    // Write your solution here\n    return 0;\n}',
            cpp: '#include <iostream>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}',
        };
        return defaults[lang] || '// Start coding here';
    }

    function monacoToLang(lang) {
        const map = { python: 'python', javascript: 'javascript', java: 'java', c: 'c', cpp: 'cpp' };
        return map[lang] || 'plaintext';
    }
})();

/* ===== COMPLEXITY ANALYZER ===== */

(function () {
    // Track if server has its own token
    let serverTokenAvailable = false;
    const TOKEN_KEY = 'terv_hf_token';

    function getStoredToken() {
        return sessionStorage.getItem(TOKEN_KEY) || '';
    }

    function saveToken(t) {
        if (t) sessionStorage.setItem(TOKEN_KEY, t);
    }

    // Check server token status and set up UI accordingly
    async function initComplexityPanel() {
        try {
            const res = await API.get('/api/complexity/status');
            serverTokenAvailable = res.serverTokenAvailable === true;
        } catch (e) {
            serverTokenAvailable = false;
        }

        const serverNotice = document.getElementById('complexity-server-notice');
        const manualToken = document.getElementById('complexity-manual-token');
        const statusBadge = document.getElementById('complexity-status-badge');

        if (serverTokenAvailable) {
            // Server has a token — show the "AI Ready" badge, hide manual input
            if (serverNotice) serverNotice.style.display = 'block';
            if (manualToken) manualToken.style.display = 'none';
            if (statusBadge) statusBadge.style.display = 'inline-flex';
        } else {
            // No server token — show manual input
            if (serverNotice) serverNotice.style.display = 'none';
            if (manualToken) manualToken.style.display = 'block';
            if (statusBadge) statusBadge.style.display = 'none';
            // Restore saved token
            const inp = document.getElementById('hf-token-input');
            if (inp) inp.value = getStoredToken();
        }
    }

    // Init on DOM ready
    document.addEventListener('DOMContentLoaded', initComplexityPanel);

    function getComplexityClass(val) {
        if (!val) return '';
        const v = val.toLowerCase();
        if (v.includes('o(1)') || v.includes('o(log')) return 'good';
        if (v.includes('o(n)') || v.includes('o(n log') || v === 'o(n)') return 'ok';
        return 'bad';
    }

    window.toggleComplexityPanel = function () {
        const body = document.getElementById('complexity-panel-body');
        const chevron = document.getElementById('complexity-chevron');
        if (!body) return;
        const isOpen = body.classList.contains('open');
        body.classList.toggle('open', !isOpen);
        if (chevron) chevron.classList.toggle('open', !isOpen);
    };

    window.analyzeComplexity = async function () {
        const tokenInput = document.getElementById('hf-token-input');
        const modelSelect = document.getElementById('hf-model-select');
        const resultsEl = document.getElementById('complexity-results');
        const btn = document.getElementById('complexity-analyze-btn');

        // If server has a token, we send empty (backend will use its own)
        // Otherwise use the manual input
        const token = serverTokenAvailable ? '' : (tokenInput ? tokenInput.value : '').trim();
        const model = modelSelect ? modelSelect.value : 'Qwen/Qwen2.5-Coder-7B-Instruct';

        // Get current code from Monaco editor
        const code = (window.monacoEditor ? window.monacoEditor.getValue() : '').trim();

        if (!code) {
            resultsEl.innerHTML = '<div class="complexity-error">⚠ Write some code first before analyzing.</div>';
            return;
        }
        if (!serverTokenAvailable && !token) {
            resultsEl.innerHTML = '<div class="complexity-error">⚠ Enter your HuggingFace token above.<br><a href="https://huggingface.co/settings/tokens" target="_blank" style="color:var(--neon-cyan);">Get a free token here →</a></div>';
            return;
        }

        if (token) saveToken(token);
        btn.disabled = true;
        btn.textContent = '⏳ Analyzing…';
        resultsEl.innerHTML = `
            <div class="complexity-results">
                <div class="complexity-loading">
                    <div class="complexity-spinner"></div>
                    Analyzing with ${model.split('/')[1]}…
                </div>
            </div>`;

        try {
            const payload = { code, model };
            if (token) payload.hfToken = token;

            const res = await API.post('/api/complexity/analyze', payload);

            if (res.raw) {
                // Model returned non-JSON text
                resultsEl.innerHTML = `
                    <div class="complexity-results">
                        <div class="complexity-raw">${escapeHtml(res.raw)}</div>
                    </div>`;
            } else {
                const algos = Array.isArray(res.algorithm) ? res.algorithm : [res.algorithm].filter(Boolean);
                const tClass = getComplexityClass(res.time_complexity);
                const sClass = getComplexityClass(res.space_complexity);

                resultsEl.innerHTML = `
                    <div class="complexity-results">
                        <div class="complexity-badge">
                            <span class="complexity-badge-label">⏱ Time</span>
                            <span class="complexity-badge-value ${tClass}">${escapeHtml(res.time_complexity || 'N/A')}</span>
                        </div>
                        <div class="complexity-badge">
                            <span class="complexity-badge-label">🗄 Space</span>
                            <span class="complexity-badge-value ${sClass}">${escapeHtml(res.space_complexity || 'N/A')}</span>
                        </div>
                        <div class="complexity-info-block">
                            ${algos.length ? `
                            <div class="complexity-algo-tags">
                                ${algos.map(a => `<span class="complexity-algo-tag">${escapeHtml(a)}</span>`).join('')}
                            </div>` : ''}
                            ${res.explanation ? `<div class="complexity-explanation">${escapeHtml(res.explanation)}</div>` : ''}
                            ${res.optimization ? `<div class="complexity-optimization">${escapeHtml(res.optimization)}</div>` : ''}
                        </div>
                    </div>`;
            }
        } catch (e) {
            resultsEl.innerHTML = `<div class="complexity-results"><div class="complexity-error">❌ ${escapeHtml(e.message)}</div></div>`;
        } finally {
            btn.disabled = false;
            btn.textContent = '⚡ Analyze Complexity';
        }
    };

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
})();
/* ===== END COMPLEXITY ANALYZER ===== */
