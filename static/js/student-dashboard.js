/* ===== STUDENT DASHBOARD LOGIC — v3 ===== */
(async () => {
    const user = requireAuth('student');
    if (!user) return;

    document.getElementById('student-name').textContent = user.name || 'Student';
    document.getElementById('nav-username').textContent = user.name;

    // Track which tests the student already submitted for
    let submittedTestIds = new Set();

    // Load dashboard stats
    try {
        const stats = await API.get('/api/student/dashboard');
        document.getElementById('st-total').textContent = stats.totalSubmissions;
        document.getElementById('st-passed').textContent = stats.passedSubmissions;
        document.getElementById('st-violations').textContent = stats.violations;
    } catch { }

    // Load my submissions first (to know completed tests)
    try {
        const subs = await API.get('/api/student/submissions');
        subs.forEach(s => { if (s.testId) submittedTestIds.add(s.testId); });

        const tbody = document.getElementById('my-submissions');
        if (!subs.length) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-muted);">No submissions yet \u2014 take a test!</td></tr>';
        } else {
            const badge = r => r === 'passed' ? 'badge-success' : r === 'partial' ? 'badge-warn' : 'badge-danger';
            tbody.innerHTML = subs.map(s => `
                <tr>
                  <td><span class="badge badge-info">${s.language}</span></td>
                  <td><span class="badge ${badge(s.result)}">${s.result}</span></td>
                  <td style="font-weight:600;color:var(--neon-blue);">${s.score || '\u2014'}</td>
                  <td>${s.executionTime !== undefined ? s.executionTime + 's' : '\u2014'}</td>
                  <td style="font-size:.78rem;color:var(--text-muted);">${s.submittedAt ? new Date(s.submittedAt).toLocaleString() : '\u2014'}</td>
                </tr>`).join('');
        }
    } catch (e) { showToast('Failed to load submissions: ' + e.message, 'error'); }

    // Load available tests — auto-refresh every 30s to catch scheduled tests going live
    async function loadAvailableTests() {
        try {
            const tests = await API.get('/api/student/tests/available');
            const cardsEl = document.getElementById('test-cards');
            if (!tests.length) {
                cardsEl.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:48px;color:var(--text-muted);">No tests available right now.</div>';
            } else {
                const now = new Date();
                cardsEl.innerHTML = tests.map(t => {
                    const isCompleted = submittedTestIds.has(t.id);
                    // Use simple testId-only link — editor.js auto-fetches problems from test data
                    const examUrl = `/student/exam?testId=${t.id}`;

                    // Determine availability with proper time checking
                    const st = t.startTime ? new Date(t.startTime) : null;
                    const et = t.endTime ? new Date(t.endTime) : null;
                    let isAvailable = t.available;

                    // Double-check timing on client side
                    if (st && now < st) isAvailable = false;
                    if (et && now > et) isAvailable = false;

                    let footerHtml;
                    if (isCompleted) {
                        footerHtml = `
                            <span class="badge badge-info" style="background:rgba(139,92,246,.15);color:#a78bfa;border-color:rgba(139,92,246,.3);">\u2713 Submitted</span>
                            <a href="${examUrl}" class="btn btn-outline btn-sm" style="opacity:.6;">Re-attempt</a>`;
                    } else if (isAvailable) {
                        footerHtml = `
                            <span class="badge badge-success">Available</span>
                            <a href="${examUrl}" class="btn btn-primary btn-sm">Start Exam \u2192</a>`;
                    } else if (st && now < st) {
                        // Test is scheduled but not yet started — show countdown
                        const diffMs = st - now;
                        const diffMin = Math.ceil(diffMs / 60000);
                        const timeStr = diffMin > 60
                            ? `${Math.floor(diffMin / 60)}h ${diffMin % 60}m`
                            : `${diffMin} min`;
                        footerHtml = `
                            <span class="badge badge-warn">Starts in ${timeStr}</span>
                            <button class="btn btn-outline btn-sm" disabled style="opacity:.4;cursor:not-allowed;">Not Active Yet</button>`;
                    } else {
                        footerHtml = `
                            <span class="badge badge-warn">Not Active</span>
                            <button class="btn btn-outline btn-sm" disabled style="opacity:.4;cursor:not-allowed;">Not Active</button>`;
                    }

                    let scheduleInfo;
                    if (st && et) {
                        scheduleInfo = `<span>\ud83d\udcc5 ${st.toLocaleString()} \u2014 ${et.toLocaleString()}</span>`;
                    } else if (st) {
                        scheduleInfo = `<span>\ud83d\udcc5 Starts: ${st.toLocaleString()}</span>`;
                    } else if (et) {
                        scheduleInfo = `<span>\ud83d\udcc5 Ends: ${et.toLocaleString()}</span>`;
                    } else {
                        scheduleInfo = '<span style="color:var(--neon-green);">Always Active</span>';
                    }

                    return `
                        <div class="test-card${isCompleted ? ' completed-card' : ''}">
                            <div class="test-card-title">${t.title}</div>
                            <div class="test-card-meta">
                                <span>\u23f1 ${t.duration} min</span>
                                <span>\ud83d\udcdd ${(t.problems || []).length} problem(s)</span>
                                ${scheduleInfo}
                            </div>
                            <div class="test-card-footer">${footerHtml}</div>
                        </div>`;
                }).join('');
            }
        } catch (e) { showToast('Failed to load tests: ' + e.message, 'error'); }
    }

    await loadAvailableTests();

    // Auto-refresh test availability every 30 seconds to catch scheduled tests going live
    setInterval(loadAvailableTests, 30000);
})();
