/* ===== ANTI-CHEAT SYSTEM ===== */
const AntiCheat = (() => {
    let violations = 0;
    const MAX_VIOLATIONS = 3;
    let testId = null;
    let warningVisible = false;
    let autoSubmitFired = false;

    function init(tid) {
        testId = tid;
        _enforceFullscreen();
        _bindTabSwitch();
        _bindVisibilityChange();
        _disableRightClick();
        _disableCopyPaste();
        _detectDevTools();
        _preventContextMenu();
        _preventUnload();
    }

    function _preventUnload() {
        window.addEventListener('beforeunload', (e) => {
            if (autoSubmitFired) return; // Allow programmatic redirects/reloads
            e.preventDefault();
            e.returnValue = "Are you sure you want to leave? Your exam is in progress.";
            return e.returnValue;
        });
    }

    function _enforceFullscreen() {
        // Request fullscreen on exam start
        const el = document.documentElement;
        if (el.requestFullscreen) el.requestFullscreen().catch(() => { });
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement && !warningVisible) {
                _recordViolation('fullscreen_exit', 'Exited fullscreen mode');
            }
        });
    }

    function _bindTabSwitch() {
        window.addEventListener('blur', () => {
            if (!warningVisible) _recordViolation('tab_switch', 'Window focus lost');
        });
    }

    function _bindVisibilityChange() {
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && !warningVisible) {
                _recordViolation('tab_switch', 'Tab became hidden');
            }
        });
    }

    function _disableRightClick() {
        document.addEventListener('contextmenu', e => e.preventDefault());
    }

    function _disableCopyPaste() {
        document.addEventListener('copy', e => { e.preventDefault(); _recordViolation('copy_attempt', 'Copy attempted', false); });
        document.addEventListener('paste', e => { e.preventDefault(); });
        document.addEventListener('cut', e => { e.preventDefault(); });
        // Also block via keydown
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'x', 'u'].includes(e.key.toLowerCase())) {
                if (e.key.toLowerCase() !== 'c') return; // allow Ctrl+C inside editor
                // only block outside the monaco editor
                if (!e.target.closest('#monaco-editor')) e.preventDefault();
            }
            // Block F12, Ctrl+Shift+I/J/C
            if (e.key === 'F12' ||
                (e.ctrlKey && e.shiftKey && ['i', 'j', 'c'].includes(e.key.toLowerCase()))) {
                e.preventDefault();
                _recordViolation('devtools', 'DevTools shortcut blocked');
            }
        });
    }

    function _preventContextMenu() {
        document.addEventListener('contextmenu', e => e.preventDefault());
    }

    function _detectDevTools() {
        // Dimension-based detection
        const threshold = 120;
        setInterval(() => {
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            if (widthDiff > threshold || heightDiff > threshold) {
                _recordViolation('devtools', 'DevTools panel detected', false);
            }
        }, 3000);
        // debugger-based detection (runs only once per interval)
        setInterval(() => {
            const start = performance.now();
            // eslint-disable-next-line no-debugger
            debugger;
            if (performance.now() - start > 100) {
                _recordViolation('devtools', 'Debugger breakpoint detected', false);
            }
        }, 5000);
    }

    async function _recordViolation(eventType, reason, showWarning = true) {
        if (autoSubmitFired) return; // Prevent logging if submission is in progress or completed
        violations++;
        try {
            const res = await API.post('/api/activity/log', { testId, eventType, details: { reason } });
            if (res.autoSubmit && !autoSubmitFired) {
                autoSubmitFired = true;
                _triggerAutoSubmit();
                return;
            }
        } catch (e) { /* offline — still enforce locally */ }

        if (violations >= MAX_VIOLATIONS && !autoSubmitFired) {
            autoSubmitFired = true;
            _triggerAutoSubmit();
            return;
        }
        if (showWarning) _showWarning(reason);
    }

    function _showWarning(reason) {
        warningVisible = true;
        const overlay = document.getElementById('anticheat-overlay');
        const msgEl = document.getElementById('ac-msg');
        if (overlay) overlay.style.display = 'flex';
        if (msgEl) msgEl.textContent = reason || 'Suspicious activity detected.';
        _updateDots();
    }

    function _updateDots() {
        for (let i = 1; i <= 3; i++) {
            const dot = document.getElementById(`vd-${i}`);
            if (dot) dot.classList.toggle('filled', i <= violations);
        }
    }

    function _triggerAutoSubmit() {
        const overlay = document.getElementById('anticheat-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            const msgEl = document.getElementById('ac-msg');
            if (msgEl) msgEl.textContent = '⚠️ Maximum violations reached. Your exam has been auto-submitted.';
            const btn = overlay.querySelector('button');
            if (btn) btn.style.display = 'none';
        }
        _updateDots();
        setTimeout(() => {
            if (typeof autoSubmitAll === 'function') autoSubmitAll();
        }, 2000);
    }

    function dismiss() {
        warningVisible = false;
        const overlay = document.getElementById('anticheat-overlay');
        if (overlay) overlay.style.display = 'none';
        // Re-enforce fullscreen
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => { });
        }
    }

    function clearUnload() {
        autoSubmitFired = true;
    }

    return { init, dismiss, clearUnload };
})();

function dismissWarning() { AntiCheat.dismiss(); }
