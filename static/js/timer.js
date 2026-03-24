/* ===== TIMER SYSTEM ===== */
const Timer = (() => {
    let endTimestamp = null;
    let intervalId = null;
    let onExpire = null;

    function start(durationMinutes, submitCallback) {
        onExpire = submitCallback;
        const now = Date.now();
        endTimestamp = now + durationMinutes * 60 * 1000;
        // Store in session to survive page refresh
        sessionStorage.setItem('terv_timer_end', endTimestamp);
        _tick();
        intervalId = setInterval(_tick, 1000);
    }

    function resume(submitCallback) {
        onExpire = submitCallback;
        const stored = sessionStorage.getItem('terv_timer_end');
        if (stored) {
            endTimestamp = parseInt(stored);
            if (endTimestamp <= Date.now()) { _expire(); return; }
            _tick();
            intervalId = setInterval(_tick, 1000);
        }
    }

    function _tick() {
        const remaining = endTimestamp - Date.now();
        if (remaining <= 0) { _expire(); return; }
        _render(remaining);
    }

    function _render(ms) {
        const timerEl = document.getElementById('exam-timer');
        if (!timerEl) return;
        const totalSec = Math.ceil(ms / 1000);
        const m = Math.floor(totalSec / 60).toString().padStart(2, '0');
        const s = (totalSec % 60).toString().padStart(2, '0');
        timerEl.textContent = `${m}:${s}`;
        timerEl.classList.remove('warn', 'danger');
        if (totalSec <= 300) timerEl.classList.add('warn');
        if (totalSec <= 60) timerEl.classList.add('danger');
    }

    function _expire() {
        clearInterval(intervalId);
        const timerEl = document.getElementById('exam-timer');
        if (timerEl) timerEl.textContent = '00:00';
        sessionStorage.removeItem('terv_timer_end');
        if (typeof onExpire === 'function') onExpire();
    }

    function stop() { clearInterval(intervalId); }

    return { start, resume, stop };
})();
