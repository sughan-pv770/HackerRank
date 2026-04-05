/* ===== ADMIN DASHBOARD LOGIC — v3 ===== */
(async () => {
    const user = requireAuth('master');
    if (!user) return;
    document.getElementById('admin-name').textContent = user.name || 'Admin';

    // Live clock
    const clockEl = document.getElementById('overview-time');
    const updateClock = () => {
        if (clockEl) clockEl.textContent = new Date().toLocaleString();
    };
    updateClock();
    setInterval(updateClock, 1000);

    // ── Globals ──
    let allProblems = [];
    let allTests = [];
    let allStudents = [];
    let currentEditProblemId = null;
    let _rescheduleTestId = null;
    let _passFailChart = null;
    let _langChart = null;
    let _testPfChart = null;
    let _testLangChart = null;

    // ── Mobile Sidebar ──
    window.openSidebar = () => {
        document.getElementById('sidebar').classList.add('open');
        document.getElementById('sidebar-overlay').classList.add('visible');
        document.body.style.overflow = 'hidden';
    };
    window.closeSidebar = () => {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebar-overlay').classList.remove('visible');
        document.body.style.overflow = '';
    };

    // ── Section Switching ──
    window.showSection = (name, el) => {
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.getElementById(`section-${name}`)?.classList.add('active');
        if (el) el.classList.add('active');
        closeSidebar();
        loadSection(name);
    };

    async function loadSection(name) {
        switch (name) {
            case 'overview': await loadStats(); await loadRecentTests(); break;
            case 'problems': await loadProblems(); break;
            case 'tests': await loadTests(); break;
            case 'students': await loadStudents(); break;
            case 'submissions': await loadSubmissions(); break;
            case 'activity': await loadActivity(); break;
            case 'analytics': await loadAnalytics(); break;
        }
    }

    // ══════════════════════════════════════════════════
    // OVERVIEW — Stats
    // ══════════════════════════════════════════════════
    async function loadStats() {
        try {
            const data = await API.get('/api/admin/stats');
            document.getElementById('s-students').textContent = data.totalStudents;
            document.getElementById('s-tests').textContent = data.totalTests;
            document.getElementById('s-submissions').textContent = data.totalSubmissions;
            document.getElementById('s-suspicious').textContent = data.suspiciousEvents;
        } catch (e) { showToast('Failed to load stats: ' + e.message, 'error'); }
    }

    // OVERVIEW — Recent Tests
    async function loadRecentTests() {
        try {
            const tests = await API.get('/api/tests/');
            allTests = tests;
            const el = document.getElementById('recent-tests-list');
            if (!tests.length) {
                el.innerHTML = '<div style="color:var(--text-muted);font-size:.85rem;text-align:center;padding:20px;">No tests created yet. <a href="/admin/create-test" style="color:var(--neon-blue);">Create one \u2192</a></div>';
                return;
            }
            const now = new Date();
            const recent = [...tests].reverse().slice(0, 5);
            el.innerHTML = recent.map(t => {
                const st = t.startTime ? new Date(t.startTime) : null;
                const et = t.endTime ? new Date(t.endTime) : null;
                let status, statusColor;
                if (!st && !et) { status = 'Always Active'; statusColor = 'var(--neon-green)'; }
                else if (st && now < st) { status = 'Scheduled'; statusColor = '#f59e0b'; }
                else if (et && now > et) { status = 'Ended'; statusColor = '#ef4444'; }
                else { status = 'Active'; statusColor = 'var(--neon-green)'; }

                return `<div class="recent-test-row">
                    <div class="recent-test-title">${t.title}</div>
                    <div class="recent-test-meta">
                        <span>\u23f1 ${t.duration}m</span>
                        <span>\ud83d\udcdd ${(t.problems || []).length} problems</span>
                        ${st ? `<span>\ud83d\udd50 ${st.toLocaleDateString()}</span>` : ''}
                    </div>
                    <span style="background:rgba(0,0,0,.3);border:1px solid ${statusColor};color:${statusColor};border-radius:20px;padding:3px 12px;font-size:.72rem;font-weight:600;white-space:nowrap;">${status}</span>
                    <button class="btn btn-outline btn-sm" onclick='openCodeViewer(${JSON.stringify(t)})' style="flex-shrink:0;">\ud83d\udc41 View Code</button>
                    <button class="btn btn-outline btn-sm" onclick='openRescheduleModal(${JSON.stringify(t)})' style="flex-shrink:0;">\ud83d\udcc5 Reschedule</button>
                </div>`;
            }).join('');
        } catch (e) { showToast('Failed to load recent tests: ' + e.message, 'error'); }
    }

    // ══════════════════════════════════════════════════
    // PROBLEMS
    // ══════════════════════════════════════════════════
    async function loadProblems() {
        try {
            allProblems = await API.get('/api/problems/');
            const tbody = document.getElementById('problems-table-body');
            if (!allProblems.length) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:32px;color:var(--text-muted);">No problems yet. <button class="btn btn-primary btn-sm" onclick="openProblemModal()" style="margin-left:12px;">+ Add Problem</button></td></tr>';
                return;
            }
            tbody.innerHTML = allProblems.map(p => `
                <tr>
                  <td><strong>${p.title}</strong></td>
                  <td>${(p.sampleTestCases || []).length}</td>
                  <td>${(p.hiddenTestCases || []).length}</td>
                  <td style="font-size:.78rem;color:var(--text-muted);">${p.createdAt ? new Date(p.createdAt).toLocaleDateString() : '\u2014'}</td>
                  <td style="white-space:nowrap;">
                    <button class="btn btn-outline btn-sm" onclick='editProblem(${JSON.stringify(p)})'>Edit</button>
                    <button class="btn btn-danger btn-sm" style="margin-left:6px;" onclick="deleteProblem('${p.id}')">Delete</button>
                  </td>
                </tr>`).join('');
        } catch (e) { showToast(e.message, 'error'); }
    }

    window.openProblemModal = () => {
        currentEditProblemId = null;
        document.getElementById('problem-modal-title').textContent = 'ADD PROBLEM';
        ['pm-title', 'pm-desc', 'pm-sample', 'pm-hidden'].forEach(id => { document.getElementById(id).value = ''; });
        document.getElementById('problem-modal').style.display = 'flex';
    };
    window.closeProblemModal = () => { document.getElementById('problem-modal').style.display = 'none'; };

    window.editProblem = (p) => {
        currentEditProblemId = p.id;
        document.getElementById('problem-modal-title').textContent = 'EDIT PROBLEM';
        document.getElementById('pm-title').value = p.title || '';
        document.getElementById('pm-desc').value = p.description || '';
        document.getElementById('pm-sample').value = JSON.stringify(p.sampleTestCases || []);
        document.getElementById('pm-hidden').value = JSON.stringify(p.hiddenTestCases || []);
        document.getElementById('problem-modal').style.display = 'flex';
    };

    window.saveProblem = async () => {
        let sample, hidden;
        try { sample = JSON.parse(document.getElementById('pm-sample').value || '[]'); } catch { return showToast('Invalid sample JSON', 'error'); }
        try { hidden = JSON.parse(document.getElementById('pm-hidden').value || '[]'); } catch { return showToast('Invalid hidden JSON', 'error'); }
        const payload = {
            title: document.getElementById('pm-title').value,
            description: document.getElementById('pm-desc').value,
            sampleTestCases: sample, hiddenTestCases: hidden
        };
        try {
            if (currentEditProblemId) {
                await API.put(`/api/problems/${currentEditProblemId}`, payload);
                showToast('Problem updated', 'success');
            } else {
                await API.post('/api/problems/', payload);
                showToast('Problem created', 'success');
            }
            closeProblemModal(); await loadProblems();
        } catch (e) { showToast(e.message, 'error'); }
    };

    window.deleteProblem = async (id) => {
        if (!confirm('Delete this problem?')) return;
        try { await API.del(`/api/problems/${id}`); showToast('Deleted', 'success'); await loadProblems(); }
        catch (e) { showToast(e.message, 'error'); }
    };

    // ══════════════════════════════════════════════════
    // TESTS MANAGEMENT
    // ══════════════════════════════════════════════════
    async function loadTests() {
        try {
            allTests = await API.get('/api/tests/');
            renderTestsTable(allTests);
        } catch (e) { showToast(e.message, 'error'); }
    }

    function renderTestsTable(tests) {
        const tbody = document.getElementById('tests-table-body');
        if (!tests.length) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-muted);">No tests yet.</td></tr>';
            return;
        }
        const now = new Date();
        tbody.innerHTML = tests.map(t => {
            const st = t.startTime ? new Date(t.startTime) : null;
            const et = t.endTime ? new Date(t.endTime) : null;
            let statusBadge;
            if (!st && !et) statusBadge = '<span class="badge badge-success">Always Active</span>';
            else if (st && now < st) statusBadge = '<span class="badge badge-warn">Scheduled</span>';
            else if (et && now > et) statusBadge = '<span class="badge badge-danger">Ended</span>';
            else statusBadge = '<span class="badge badge-success">Active</span>';

            const depts = (t.departments || []);
            const deptDisplay = depts.length
                ? depts.map(d => `<span class="badge badge-info" style="font-size:.65rem;margin:1px;">${d}</span>`).join(' ')
                : '<span style="color:var(--text-muted);font-size:.78rem;">All</span>';

            return `
            <tr>
              <td><strong>${t.title}</strong></td>
              <td>${deptDisplay}</td>
              <td>${(t.problems || []).length}</td>
              <td>${t.duration} min</td>
              <td style="font-size:.75rem;">${st ? st.toLocaleString() : '<span style="color:var(--text-muted);">\u2014</span>'}</td>
              <td style="font-size:.75rem;">${et ? et.toLocaleString() : '<span style="color:var(--text-muted);">\u2014</span>'}</td>
              <td>${statusBadge}</td>
              <td>
                <button class="btn btn-outline btn-sm" onclick='openCodeViewer(${JSON.stringify(t)})' title="View student code">\ud83d\udc41 Code</button>
                <button class="btn btn-outline btn-sm" style="margin-left:4px;" onclick='openTestAnalytics("${t.id}", ${JSON.stringify(t.title)})' title="View analytics">\ud83d\udcca Analytics</button>
              </td>
              <td style="white-space:nowrap;">
                <button class="btn btn-outline btn-sm" onclick='openRescheduleModal(${JSON.stringify(t)})' title="Reschedule">\ud83d\udcc5</button>
                <button class="btn btn-outline btn-sm" style="margin-left:4px;" onclick='copyExamLink("${t.id}")' title="Copy student exam link">\ud83d\udd17</button>
                <button class="btn btn-danger btn-sm" style="margin-left:4px;" onclick="deleteTest('${t.id}')" title="Delete">\ud83d\uddd1</button>
              </td>
            </tr>`;
        }).join('');
    }

    window.filterTests = (q) => {
        const filtered = allTests.filter(t => t.title.toLowerCase().includes(q.toLowerCase()));
        renderTestsTable(filtered);
    };

    // Create Test Modal
    const DEPARTMENTS = ['AI&DS', 'CSE', 'CYBER', 'CSBS', 'IT', 'AI&ML'];
    let _tmAllStudents = [];

    window.openTestModal = async () => {
        if (!allProblems.length) {
            try { allProblems = await API.get('/api/problems/'); } catch { }
        }
        const listEl = document.getElementById('tm-problem-list');
        if (!allProblems.length) {
            listEl.innerHTML = '<div style="color:var(--text-muted);font-size:.82rem;">No problems found. <a href="#" onclick="closeProblemModal();openProblemModal();" style="color:var(--neon-blue);">Add problems first.</a></div>';
        } else {
            listEl.innerHTML = allProblems.map(p => `
                <label style="display:flex;align-items:center;gap:10px;padding:8px;cursor:pointer;border-radius:6px;transition:.15s;" onmouseover="this.style.background='rgba(0,212,255,.06)'" onmouseout="this.style.background=''">
                    <input type="checkbox" class="prob-check" value="${p.id}" style="accent-color:var(--neon-blue);width:15px;height:15px;">
                    <span style="font-size:.875rem;">${p.title}</span>
                    <span style="font-size:.72rem;color:var(--text-muted);margin-left:auto;">${(p.sampleTestCases || []).length} sample cases</span>
                </label>`).join('');
        }

        const deptListEl = document.getElementById('tm-dept-list');
        deptListEl.innerHTML = DEPARTMENTS.map(d => `
            <label style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:rgba(0,212,255,.07);border:1px solid rgba(0,212,255,.2);border-radius:20px;cursor:pointer;font-size:.78rem;transition:.15s;" onmouseover="this.style.background='rgba(0,212,255,.18)'" onmouseout="this.style.background='rgba(0,212,255,.07)'">
                <input type="checkbox" class="dept-check" value="${d}" style="accent-color:var(--neon-blue);">
                ${d}
            </label>`).join('');

        try {
            _tmAllStudents = await API.get('/api/admin/students');
        } catch { _tmAllStudents = []; }
        const filterEl = document.getElementById('tm-dept-filter');
        filterEl.innerHTML = '<option value="">-- All Departments --</option>' +
            DEPARTMENTS.map(d => `<option value="${d}">${d}</option>`).join('');
        renderTmStudents(_tmAllStudents);

        document.getElementById('test-modal').style.display = 'flex';
    };
    window.closeTestModal = () => { document.getElementById('test-modal').style.display = 'none'; };

    function renderTmStudents(students) {
        const el = document.getElementById('tm-student-list');
        if (!students.length) {
            el.innerHTML = '<div style="color:var(--text-muted);font-size:.82rem;">No students found for this filter.</div>';
            return;
        }
        el.innerHTML = students.map(s => `
            <label style="display:flex;align-items:center;gap:8px;padding:6px;cursor:pointer;border-radius:6px;transition:.15s;" onmouseover="this.style.background='rgba(0,212,255,.06)'" onmouseout="this.style.background=''">
                <input type="checkbox" class="student-check" value="${s.id}" style="accent-color:var(--neon-blue);">
                <span style="font-size:.82rem;">${s.name}</span>
                <span class="badge badge-info" style="font-size:.62rem;margin-left:auto;">${s.department || '\u2014'}</span>
            </label>`).join('');
    }

    window.filterTmStudents = (dept) => {
        const filtered = dept ? _tmAllStudents.filter(s => s.department === dept) : _tmAllStudents;
        renderTmStudents(filtered);
    };

    window.saveTest = async () => {
        const checked = [...document.querySelectorAll('.prob-check:checked')].map(c => c.value);
        const title = document.getElementById('tm-title').value.trim();
        if (!title) return showToast('Test title is required', 'error');
        if (!checked.length) return showToast('Select at least one problem', 'error');
        const departments = [...document.querySelectorAll('.dept-check:checked')].map(c => c.value);
        const assignedStudents = [...document.querySelectorAll('.student-check:checked')].map(c => c.value);

        // Convert local datetime-local values to ISO UTC strings
        const startRaw = document.getElementById('tm-start').value;
        const endRaw = document.getElementById('tm-end').value;
        const startTime = startRaw ? new Date(startRaw).toISOString() : null;
        const endTime = endRaw ? new Date(endRaw).toISOString() : null;

        try {
            await API.post('/api/tests/', {
                title,
                problems: checked,
                duration: parseInt(document.getElementById('tm-duration').value),
                startTime,
                endTime,
                departments,
                assignedStudents
            });
            showToast('Test created!', 'success');
            closeTestModal();
            await loadTests();
        } catch (e) { showToast(e.message, 'error'); }
    };

    window.deleteTest = async (id) => {
        if (!confirm('Delete this test?')) return;
        try { await API.del(`/api/tests/${id}`); showToast('Deleted', 'success'); await loadTests(); }
        catch (e) { showToast(e.message, 'error'); }
    };

    // ── Copy Exam Link (for STUDENTS) ──
    window.copyExamLink = (testId) => {
        // The link points to /student/exam which requires student auth.
        // Students opening this link will go directly to the exam.
        const url = `${location.origin}/student/exam?testId=${testId}`;
        navigator.clipboard.writeText(url).then(() => showToast('Student exam link copied! Share with students.', 'success'));
    };

    // ── Reschedule ──
    window.openRescheduleModal = (t) => {
        _rescheduleTestId = t.id;
        document.getElementById('rs-test-name').textContent = `"${t.title}"`;
        const now = new Date();
        const toLocal = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
        const defaultStart = new Date(now.getTime() + 5 * 60000);
        const defaultEnd = new Date(now.getTime() + 2 * 3600000);
        document.getElementById('rs-start').value = t.startTime ? toLocal(new Date(t.startTime)) : toLocal(defaultStart);
        document.getElementById('rs-end').value = t.endTime ? toLocal(new Date(t.endTime)) : toLocal(defaultEnd);
        updateRsPreview();
        document.getElementById('reschedule-modal').style.display = 'flex';
    };

    function updateRsPreview() {
        const startVal = document.getElementById('rs-start').value;
        const endVal = document.getElementById('rs-end').value;
        const previewEl = document.getElementById('rs-preview');
        if (startVal && endVal) {
            const diff = (new Date(endVal) - new Date(startVal)) / 3600000;
            const color = diff > 24 ? '#ef4444' : diff > 0 ? 'var(--neon-green)' : '#ef4444';
            previewEl.innerHTML = diff > 0
                ? `<span style="color:${color};">Duration: ${diff.toFixed(1)}h ${diff > 24 ? '\u2014 \u26a0 Exceeds 24h limit' : '\u2713'}</span>`
                : '<span style="color:#ef4444;">End must be after start</span>';
        } else {
            previewEl.innerHTML = '';
        }
    }
    document.getElementById('rs-start').addEventListener('input', updateRsPreview);
    document.getElementById('rs-end').addEventListener('input', updateRsPreview);

    window.closeRescheduleModal = () => {
        document.getElementById('reschedule-modal').style.display = 'none';
        _rescheduleTestId = null;
    };

    window.saveReschedule = async () => {
        const startVal = document.getElementById('rs-start').value;
        const endVal = document.getElementById('rs-end').value;
        if (!startVal || !endVal) { showToast('Both start and end times required', 'error'); return; }
        const start = new Date(startVal);
        const end = new Date(endVal);
        const now = new Date();
        if (start < now) { showToast('Start time cannot be in the past', 'error'); return; }
        if (end <= start) { showToast('End time must be after start time', 'error'); return; }
        const diffHours = (end - start) / 3600000;
        if (diffHours > 24) { showToast('Exam window cannot exceed 24 hours', 'error'); return; }
        try {
            await API.put(`/api/tests/${_rescheduleTestId}`, {
                startTime: start.toISOString(),
                endTime: end.toISOString()
            });
            showToast(`\u2705 Rescheduled! Window: ${diffHours.toFixed(1)}h`, 'success');
            closeRescheduleModal();
            await loadTests();
            await loadRecentTests();
        } catch (e) { showToast(e.message, 'error'); }
    };

    window.clearSchedule = async () => {
        if (!_rescheduleTestId) return;
        if (!confirm('Remove schedule? Test will become always active.')) return;
        try {
            await API.put(`/api/tests/${_rescheduleTestId}`, { startTime: null, endTime: null });
            showToast('Schedule cleared \u2014 test is now always active', 'success');
            closeRescheduleModal();
            await loadTests();
            await loadRecentTests();
        } catch (e) { showToast(e.message, 'error'); }
    };

    // ══════════════════════════════════════════════════
    // PER-TEST ANALYTICS MODAL
    // ══════════════════════════════════════════════════
    window.openTestAnalytics = async (testId, testTitle) => {
        const modal = document.getElementById('test-analytics-modal');
        if (!modal) return;
        document.getElementById('ta-test-title').textContent = testTitle || 'Test Analytics';
        // Reset content
        document.getElementById('ta-stats-row').innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">Loading...</div>';
        document.getElementById('ta-student-tbody').innerHTML = '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted);">Loading...</td></tr>';
        document.getElementById('ta-attended-tbody').innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted);">Loading...</td></tr>';
        document.getElementById('ta-not-attended-tbody').innerHTML = '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted);">Loading...</td></tr>';
        modal.style.display = 'flex';

        try {
            const data = await API.get(`/api/admin/tests/${testId}/analytics`);

            // Stats row
            document.getElementById('ta-stats-row').innerHTML = `
                <div class="glass-card stat-card" style="padding:16px;">
                    <div class="stat-value">${data.totalSubmissions}</div>
                    <div class="stat-label">Submissions</div>
                </div>
                <div class="glass-card stat-card" style="padding:16px;">
                    <div class="stat-value" style="color:var(--neon-green);">${data.passed}</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div class="glass-card stat-card" style="padding:16px;">
                    <div class="stat-value" style="color:#ef4444;">${data.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="glass-card stat-card" style="padding:16px;">
                    <div class="stat-value" style="color:var(--neon-blue);">${data.passRate}%</div>
                    <div class="stat-label">Pass Rate</div>
                </div>
                <div class="glass-card stat-card" style="padding:16px;">
                    <div class="stat-value">${data.eligibleCount || 0}</div>
                    <div class="stat-label">Eligible</div>
                </div>`;

            // Charts
            const pfCtx = document.getElementById('ta-pf-chart');
            if (_testPfChart) _testPfChart.destroy();
            _testPfChart = new Chart(pfCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Passed', 'Failed', 'Other'],
                    datasets: [{ data: [data.passed, data.failed, data.totalSubmissions - data.passed - data.failed], backgroundColor: ['#10b981', '#ef4444', '#f59e0b'], borderWidth: 0 }]
                },
                options: { responsive: true, maintainAspectRatio: false, cutout: '65%', plugins: { legend: { display: false } } }
            });

            const langCtx = document.getElementById('ta-lang-chart');
            if (_testLangChart) _testLangChart.destroy();
            const langs = Object.keys(data.byLanguage || {});
            const counts = langs.map(l => data.byLanguage[l]);
            const colors = { python: '#3b82f6', javascript: '#f59e0b', java: '#8b5cf6', c: '#10b981', cpp: '#06b6d4' };
            _testLangChart = new Chart(langCtx, {
                type: 'bar',
                data: {
                    labels: langs,
                    datasets: [{ label: 'Submissions', data: counts, backgroundColor: langs.map(l => colors[l] || '#94a3b8'), borderRadius: 6, borderSkipped: false }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,.04)' } },
                        y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: 'rgba(255,255,255,.06)' }, beginAtZero: true }
                    }
                }
            });

            // Student performance table
            const statEntries = Object.entries(data.studentStats || {});
            document.getElementById('ta-student-tbody').innerHTML = statEntries.length
                ? statEntries.map(([name, s]) => {
                    const pct = s.total > 0 ? Math.round(s.passed / s.total * 100) : 0;
                    return `<tr>
                        <td><strong>${name}</strong></td>
                        <td style="text-align:center;">${s.total}</td>
                        <td style="text-align:center;color:var(--neon-green);">${s.passed}</td>
                        <td style="text-align:center;color:#f87171;">${s.failed}</td>
                        <td style="text-align:center;">
                            <span style="color:${pct >= 50 ? 'var(--neon-green)' : '#f87171'};font-weight:700;">${pct}%</span>
                        </td>
                    </tr>`;
                }).join('')
                : '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted);">No submissions yet</td></tr>';

            // Attendance
            const att = data.attendance || {};
            const attList = att.attended || [];
            const notList = att.notAttended || [];
            document.getElementById('ta-attended-count').textContent = `(${attList.length})`;
            document.getElementById('ta-not-attended-count').textContent = `(${notList.length})`;

            const renderRow = s => `<tr>
                <td><strong>${s.name}</strong></td>
                <td style="font-size:.8rem;">${s.email}</td>
                <td><span class="badge badge-info" style="font-size:.62rem;">${s.department || '\u2014'}</span></td>
                <td><span class="badge ${s.status === 'active' ? 'badge-success' : 'badge-danger'}">${s.status}</span></td>
            </tr>`;

            document.getElementById('ta-attended-tbody').innerHTML = attList.length
                ? attList.map(renderRow).join('')
                : '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--text-muted);">None yet</td></tr>';
            document.getElementById('ta-not-attended-tbody').innerHTML = notList.length
                ? notList.map(renderRow).join('')
                : '<tr><td colspan="4" style="text-align:center;padding:16px;color:var(--neon-green);">\ud83c\udf89 All students attended!</td></tr>';

        } catch (e) { showToast('Failed to load test analytics: ' + e.message, 'error'); }
    };

    window.closeTestAnalytics = () => {
        document.getElementById('test-analytics-modal').style.display = 'none';
    };

    // ══════════════════════════════════════════════════
    // CODE VIEWER
    // ══════════════════════════════════════════════════
    let _cvSubs = [];
    let _activeSubIdx = null;

    window.openCodeViewer = async (test) => {
        document.getElementById('cv-test-title').textContent = test.title;
        document.getElementById('cv-student-name').textContent = 'Loading\u2026';
        document.getElementById('cv-list').innerHTML = '<div style="color:var(--text-muted);font-size:.82rem;padding:20px;text-align:center;">Loading submissions\u2026</div>';
        document.getElementById('cv-code-area').innerHTML = '<div class="code-empty"><div style="font-size:2rem;">\u23f3</div><div>Loading\u2026</div></div>';
        document.getElementById('code-viewer').style.display = 'flex';
        document.body.style.overflow = 'hidden';

        try {
            _cvSubs = await API.get(`/api/admin/tests/${test.id}/submissions`);
            if (!_cvSubs.length) {
                document.getElementById('cv-list').innerHTML = '<div style="color:var(--text-muted);font-size:.82rem;padding:20px;text-align:center;">No submissions for this test yet.</div>';
                document.getElementById('cv-student-name').textContent = 'No submissions';
                document.getElementById('cv-code-area').innerHTML = '<div class="code-empty"><div style="font-size:2.5rem;">\ud83d\udced</div><div>No student has submitted yet</div></div>';
                return;
            }
            renderCvList();
            selectSubmission(0);
        } catch (e) {
            showToast('Failed to load submissions: ' + e.message, 'error');
            closeCodeViewer();
        }
    };

    function renderCvList() {
        const resultClass = r => r === 'passed' ? 'badge-success' : r === 'partial' ? 'badge-warn' : 'badge-danger';
        document.getElementById('cv-list').innerHTML = _cvSubs.map((s, i) => `
            <div class="code-viewer-list-item${i === _activeSubIdx ? ' active' : ''}" onclick="selectSubmission(${i})" id="cvitem-${i}">
                <div class="cv-name">${s.studentName || s.studentId || '\u2014'}</div>
                <div class="cv-meta">
                    <span class="badge ${resultClass(s.result)}" style="font-size:.62rem;padding:2px 7px;">${s.result}</span>
                    <span style="color:var(--neon-blue);font-weight:700;margin-left:6px;">${s.score}</span>
                    &nbsp;&nbsp;<span style="color:var(--text-muted);">${s.language}</span>
                </div>
            </div>`).join('');
    }

    window.selectSubmission = (idx) => {
        _activeSubIdx = idx;
        const s = _cvSubs[idx];
        if (!s) return;

        document.querySelectorAll('.code-viewer-list-item').forEach((el, i) => {
            el.classList.toggle('active', i === idx);
        });

        document.getElementById('cv-student-name').textContent = s.studentName || s.studentId || '\u2014';
        document.getElementById('cv-lang').textContent = s.language || '';
        const resultBadgeClass = s.result === 'passed' ? 'badge-success' : s.result === 'partial' ? 'badge-warn' : 'badge-danger';
        document.getElementById('cv-result').className = `badge ${resultBadgeClass}`;
        document.getElementById('cv-result').textContent = s.result;
        document.getElementById('cv-score').textContent = s.score ? `${s.score} pts` : '';

        const codeArea = document.getElementById('cv-code-area');
        const escapedCode = (s.code || '// No code submitted').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const timeStr = s.submittedAt ? new Date(s.submittedAt).toLocaleString() : '';
        codeArea.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 0 16px;border-bottom:1px solid var(--border-subtle);margin-bottom:16px;flex-wrap:wrap;gap:8px;">
                <span style="font-size:.75rem;color:var(--text-muted);">\ud83d\udd50 Submitted: ${timeStr}</span>
                <span style="font-size:.75rem;color:var(--text-muted);">\u26a1 Exec time: ${s.executionTime !== undefined ? s.executionTime + 's' : '\u2014'}</span>
                <button onclick="copyCode(${idx})" class="btn btn-outline btn-sm">\ud83d\udccb Copy Code</button>
            </div>
            <pre id="code-pre-${idx}">${escapedCode}</pre>`;
    };

    window.copyCode = (idx) => {
        const s = _cvSubs[idx];
        if (!s) return;
        navigator.clipboard.writeText(s.code || '').then(() => showToast('Code copied!', 'success'));
    };

    window.closeCodeViewer = () => {
        document.getElementById('code-viewer').style.display = 'none';
        document.body.style.overflow = '';
        _cvSubs = [];
        _activeSubIdx = null;
    };

    // ESC key closes modals/viewer
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeCodeViewer();
            closeRescheduleModal();
            closeProblemModal();
            closeTestModal();
            const em = document.getElementById('export-modal');
            if (em) em.style.display = 'none';
            const tam = document.getElementById('test-analytics-modal');
            if (tam) tam.style.display = 'none';
            if (_aiChatOpen) toggleAiChat();
            closeSidebar();
        }
    });

    // ══════════════════════════════════════════════════
    // STUDENTS
    // ══════════════════════════════════════════════════
    async function loadStudents() {
        try {
            allStudents = await API.get('/api/admin/students');
            renderStudentsTable(allStudents);
        } catch (e) { showToast(e.message, 'error'); }
    }

    function renderStudentsTable(students) {
        const tbody = document.getElementById('students-table-body');
        if (!students.length) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);">No students registered</td></tr>';
            return;
        }
        tbody.innerHTML = students.map(s => `
            <tr>
              <td><strong>${s.name}</strong></td>
              <td><span class="badge badge-info" style="font-size:.7rem;">${s.department || '\u2014'}</span></td>
              <td style="font-size:.82rem;">${s.email}</td>
              <td><span class="badge ${s.status === 'active' ? 'badge-success' : 'badge-danger'}">${s.status}</span></td>
              <td style="font-size:.78rem;color:var(--text-muted);">${s.createdAt ? new Date(s.createdAt).toLocaleDateString() : '\u2014'}</td>
              <td>
                ${s.status === 'active'
                ? `<button class="btn btn-danger btn-sm" onclick="disqualify('${s.id}')">Disqualify</button>`
                : '<span style="color:#ef4444;font-size:.78rem;">Disqualified</span>'}
              </td>
            </tr>`).join('');
    }

    window.filterStudents = (q) => {
        const filtered = allStudents.filter(s =>
            s.name.toLowerCase().includes(q.toLowerCase()) ||
            s.email.toLowerCase().includes(q.toLowerCase())
        );
        renderStudentsTable(filtered);
    };

    window.disqualify = async (id) => {
        if (!confirm('Disqualify this student? They will not be able to log in.')) return;
        try {
            await API.post(`/api/admin/students/${id}/disqualify`, {});
            showToast('Student disqualified', 'warn');
            await loadStudents();
        } catch (e) { showToast(e.message, 'error'); }
    };

    // ══════════════════════════════════════════════════
    // SUBMISSIONS
    // ══════════════════════════════════════════════════
    async function loadSubmissions() {
        try {
            const subs = await API.get('/api/submissions/');
            const tbody = document.getElementById('submissions-table-body');
            if (!subs.length) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);">No submissions yet</td></tr>';
                return;
            }
            const badge = r => r === 'passed' ? 'badge-success' : r === 'partial' ? 'badge-warn' : 'badge-danger';
            tbody.innerHTML = subs.map(s => `
                <tr>
                  <td><strong>${s.studentName || s.studentId || '\u2014'}</strong></td>
                  <td><span class="badge badge-info">${s.language}</span></td>
                  <td><span class="badge ${badge(s.result)}">${s.result}</span></td>
                  <td style="font-weight:700;color:var(--neon-blue);">${s.score || '\u2014'} pts</td>
                  <td>${s.executionTime !== undefined ? s.executionTime + 's' : '\u2014'}</td>
                  <td style="font-size:.78rem;color:var(--text-muted);">${s.submittedAt ? new Date(s.submittedAt).toLocaleString() : '\u2014'}</td>
                </tr>`).join('');
        } catch (e) { showToast(e.message, 'error'); }
    }

    // ── Export Modal (now with test dropdown) ──
    window.openExportModal = async () => {
        // Populate test name dropdown from actual test list
        if (!allTests.length) {
            try { allTests = await API.get('/api/tests/'); } catch { }
        }
        const sel = document.getElementById('exp-test-name');
        sel.innerHTML = '<option value="">-- All Tests --</option>' +
            allTests.map(t => `<option value="${t.title}">${t.title}</option>`).join('');
        document.getElementById('exp-department').value = '';
        document.getElementById('export-modal').style.display = 'flex';
    };

    window.doExportCSV = async () => {
        const testName = document.getElementById('exp-test-name').value.trim();
        const dept = document.getElementById('exp-department').value;
        let url = '/api/admin/export/submissions?';
        const params = new URLSearchParams();
        if (testName) params.set('testName', testName);
        if (dept) params.set('department', dept);
        url += params.toString();
        document.getElementById('export-modal').style.display = 'none';
        try {
            const blob = await API.download(url);
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            let filename = 'submissions';
            if (testName) filename += '_' + testName.replace(/\s+/g, '_');
            if (dept) filename += '_' + dept;
            filename += '.csv';
            a.download = filename;
            a.click();
            showToast('CSV download started!', 'success');
        } catch (e) { showToast('Export failed: ' + e.message, 'error'); }
    };

    // ══════════════════════════════════════════════════
    // ACTIVITY LOGS
    // ══════════════════════════════════════════════════
    async function loadActivity() {
        try {
            const logs = await API.get('/api/admin/activity-logs');
            const tbody = document.getElementById('activity-table-body');
            if (!logs.length) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:32px;color:var(--text-muted);">No activity logs</td></tr>';
                return;
            }
            const colorMap = { tab_switch: 'badge-warn', devtools: 'badge-danger', auto_submit: 'badge-danger', disqualified: 'badge-danger', fullscreen_exit: 'badge-warn', copy_attempt: 'badge-warn' };
            tbody.innerHTML = logs.map(l => `
                <tr>
                  <td><strong>${l.studentName || l.studentId || '\u2014'}</strong></td>
                  <td><span class="badge ${colorMap[l.eventType] || 'badge-info'}">${l.eventType}</span></td>
                  <td style="font-size:.78rem;color:var(--text-muted);">${JSON.stringify(l.details)}</td>
                  <td style="font-size:.78rem;color:var(--text-muted);">${l.timestamp ? new Date(l.timestamp).toLocaleString() : '\u2014'}</td>
                </tr>`).join('');
        } catch (e) { showToast(e.message, 'error'); }
    }

    // ══════════════════════════════════════════════════
    // GLOBAL ANALYTICS
    // ══════════════════════════════════════════════════
    async function loadAnalytics() {
        try {
            const data = await API.get('/api/admin/analytics');

            // Pass/Fail Chart
            const pfCtx = document.getElementById('passFailChart');
            if (_passFailChart) { _passFailChart.destroy(); }
            _passFailChart = new Chart(pfCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Passed', 'Failed', 'Partial'],
                    datasets: [{ data: [data.passed, data.failed, data.totalSubmissions - data.passed - data.failed], backgroundColor: ['#10b981', '#ef4444', '#f59e0b'], borderWidth: 0, hoverOffset: 6 }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}` } } },
                    cutout: '68%'
                }
            });
            document.getElementById('pass-fail-legend').innerHTML =
                `<span style="color:#10b981;">\u25cf Passed: ${data.passed}</span>
                 <span style="color:#ef4444;">\u25cf Failed: ${data.failed}</span>
                 <span style="color:var(--text-muted);">Rate: <strong style="color:var(--neon-green);">${data.passRate}%</strong></span>`;

            // Language Bar Chart
            const langCtx = document.getElementById('langChart');
            if (_langChart) { _langChart.destroy(); }
            const langs = Object.keys(data.byLanguage || {});
            const counts = langs.map(l => data.byLanguage[l]);
            const colors = { python: '#3b82f6', javascript: '#f59e0b', java: '#8b5cf6', c: '#10b981', cpp: '#06b6d4' };
            _langChart = new Chart(langCtx, {
                type: 'bar',
                data: {
                    labels: langs,
                    datasets: [{ label: 'Submissions', data: counts, backgroundColor: langs.map(l => colors[l] || '#94a3b8'), borderRadius: 6, borderSkipped: false }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,.04)' } },
                        y: { ticks: { color: '#94a3b8', stepSize: 1 }, grid: { color: 'rgba(255,255,255,.06)' }, beginAtZero: true }
                    }
                }
            });

            // Student performance table
            const statsTbody = document.getElementById('student-stats-tbody');
            const statEntries = Object.entries(data.studentStats || {});
            statsTbody.innerHTML = statEntries.length
                ? statEntries.map(([name, s]) => {
                    const pct = s.total > 0 ? Math.round(s.passed / s.total * 100) : 0;
                    return `<tr>
                        <td><strong>${name}</strong></td>
                        <td style="text-align:center;">${s.total}</td>
                        <td style="text-align:center;color:var(--neon-green);">${s.passed}</td>
                        <td style="text-align:center;color:#f87171;">${s.failed}</td>
                        <td style="text-align:center;">
                            <span style="color:${pct >= 50 ? 'var(--neon-green)' : '#f87171'};font-weight:700;">${pct}%</span>
                        </td>
                    </tr>`;
                }).join('')
                : '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted);">No submissions yet</td></tr>';

            // Attendance
            const att = data.attendance || {};
            const attList = att.attended || [];
            const notList = att.notAttended || [];
            document.getElementById('attended-count').textContent = `(${attList.length})`;
            document.getElementById('not-attended-count').textContent = `(${notList.length})`;

            const renderRow = s => `<tr>
                <td><strong>${s.name}</strong></td>
                <td style="font-size:.8rem;">${s.email}</td>
                <td><span class="badge ${s.status === 'active' ? 'badge-success' : 'badge-danger'}">${s.status}</span></td>
            </tr>`;

            document.getElementById('attended-tbody').innerHTML = attList.length
                ? attList.map(renderRow).join('')
                : '<tr><td colspan="3" style="text-align:center;padding:16px;color:var(--text-muted);">None yet</td></tr>';
            document.getElementById('not-attended-tbody').innerHTML = notList.length
                ? notList.map(renderRow).join('')
                : '<tr><td colspan="3" style="text-align:center;padding:16px;color:var(--neon-green);">\ud83c\udf89 All students attended!</td></tr>';

        } catch (e) { showToast(e.message, 'error'); }
    }

    // ══════════════════════════════════════════════════
    // AI CHATBOT
    // ══════════════════════════════════════════════════
    let _aiChatOpen = false;
    let _aiGenerating = false;
    let _lastGeneratedProblem = null;

    window.toggleAiChat = () => {
        _aiChatOpen = !_aiChatOpen;
        const panel = document.getElementById('ai-chat-panel');
        const fab = document.getElementById('ai-chat-fab');
        if (_aiChatOpen) {
            panel.style.display = 'flex';
            fab.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
                <span class="ai-fab-pulse"></span>`;
            document.getElementById('ai-chat-input').focus();
        } else {
            panel.style.display = 'none';
            fab.innerHTML = `
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
                    <path d="M6 10a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2"/>
                    <path d="M18 10a2 2 0 0 1 2 2v1a2 2 0 0 1-2 2"/>
                    <path d="M9 18h6"/>
                    <path d="M10 22h4"/>
                    <path d="M12 18v4"/>
                </svg>
                <span class="ai-fab-pulse"></span>`;
        }
    };

    window.sendAiSuggestion = (btn) => {
        const text = btn.textContent.trim();
        document.getElementById('ai-chat-input').value = text;
        sendAiMessage();
    };

    function appendAiMessage(role, html) {
        const container = document.getElementById('ai-chat-messages');
        const avatar = role === 'bot' ? '🤖' : '👤';
        const msgDiv = document.createElement('div');
        msgDiv.className = `ai-msg ai-msg-${role}`;
        msgDiv.innerHTML = `
            <div class="ai-msg-avatar">${avatar}</div>
            <div class="ai-msg-bubble">${html}</div>`;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
    }

    function showTypingIndicator() {
        const container = document.getElementById('ai-chat-messages');
        const typing = document.createElement('div');
        typing.className = 'ai-msg ai-msg-bot';
        typing.id = 'ai-typing-msg';
        typing.innerHTML = `
            <div class="ai-msg-avatar">🤖</div>
            <div class="ai-msg-bubble">
                <div class="ai-typing">
                    <div class="ai-typing-dot"></div>
                    <div class="ai-typing-dot"></div>
                    <div class="ai-typing-dot"></div>
                </div>
                <div style="font-size:.72rem;color:var(--text-muted);margin-top:4px;">Generating problem with AI…</div>
            </div>`;
        container.appendChild(typing);
        container.scrollTop = container.scrollHeight;
    }

    function removeTypingIndicator() {
        const el = document.getElementById('ai-typing-msg');
        if (el) el.remove();
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderProblemCard(problem) {
        const desc = (problem.description || '').substring(0, 300);
        const sampleCount = (problem.sampleTestCases || []).length;
        const hiddenCount = (problem.hiddenTestCases || []).length;

        // Build sample test cases preview
        let samplesHtml = '';
        (problem.sampleTestCases || []).forEach((tc, i) => {
            samplesHtml += `
                <div style="background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:.74rem;">
                    <div style="color:var(--neon-blue);font-weight:600;margin-bottom:3px;">Sample ${i + 1}</div>
                    <div style="display:flex;gap:12px;">
                        <div style="flex:1;"><span style="color:var(--text-muted);">Input:</span> <code style="color:var(--neon-green);font-family:var(--font-code);">${escapeHtml(tc.input || '')}</code></div>
                        <div style="flex:1;"><span style="color:var(--text-muted);">Output:</span> <code style="color:#f59e0b;font-family:var(--font-code);">${escapeHtml(tc.output || '')}</code></div>
                    </div>
                </div>`;
        });

        return `
            <div class="ai-problem-card">
                <div class="ai-problem-card-title">📝 ${escapeHtml(problem.title || 'Untitled')}</div>
                <div class="ai-problem-card-desc">${escapeHtml(desc)}${desc.length < (problem.description || '').length ? '…' : ''}</div>
                <div class="ai-problem-card-meta">
                    <span class="badge badge-info" style="font-size:.65rem;">✓ ${sampleCount} sample cases</span>
                    <span class="badge badge-warn" style="font-size:.65rem;">🔒 ${hiddenCount} hidden cases</span>
                </div>
                ${samplesHtml}
                <div class="ai-problem-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="useAiProblem()" style="font-size:.7rem;">✅ Use This Problem</button>
                    <button class="btn btn-outline btn-sm" onclick="regenerateAiProblem()" style="font-size:.7rem;">🔄 Generate Another</button>
                </div>
            </div>`;
    }

    window.sendAiMessage = async () => {
        if (_aiGenerating) return;
        const input = document.getElementById('ai-chat-input');
        const text = input.value.trim();
        if (!text) return;

        input.value = '';
        appendAiMessage('user', `<p>${escapeHtml(text)}</p>`);

        _aiGenerating = true;
        document.getElementById('ai-send-btn').disabled = true;
        showTypingIndicator();

        try {
            const resp = await API.post('/api/ai/generate-problem', { prompt: text });
            removeTypingIndicator();

            if (resp.success && resp.problem) {
                _lastGeneratedProblem = resp.problem;
                const cardHtml = renderProblemCard(resp.problem);
                appendAiMessage('bot', `<p style="margin-bottom:8px;">Here's a problem based on your request:</p>${cardHtml}`);
            } else {
                appendAiMessage('bot', `<p style="color:#f87171;">⚠️ ${escapeHtml(resp.error || 'Failed to generate problem. Please try again.')}</p>
                    ${resp.raw ? `<details style="margin-top:8px;font-size:.75rem;color:var(--text-muted);"><summary>Raw response</summary><pre style="white-space:pre-wrap;max-height:150px;overflow:auto;margin-top:6px;font-family:var(--font-code);font-size:.72rem;">${escapeHtml(resp.raw || '')}</pre></details>` : ''}`);
            }
        } catch (err) {
            removeTypingIndicator();
            appendAiMessage('bot', `<p style="color:#f87171;">❌ Error: ${escapeHtml(err.message || 'Connection failed')}</p>
                <p style="font-size:.78rem;color:var(--text-muted);margin-top:6px;">Please check your connection and try again.</p>`);
        } finally {
            _aiGenerating = false;
            document.getElementById('ai-send-btn').disabled = false;
        }
    };

    window.useAiProblem = () => {
        if (!_lastGeneratedProblem) return;
        const p = _lastGeneratedProblem;

        // Switch to Problems section
        showSection('problems', document.querySelector('[data-section=problems]'));

        // Open problem modal and fill fields
        currentEditProblemId = null;
        document.getElementById('problem-modal-title').textContent = 'ADD PROBLEM';
        document.getElementById('pm-title').value = p.title || '';
        document.getElementById('pm-desc').value = p.description || '';
        document.getElementById('pm-sample').value = JSON.stringify(p.sampleTestCases || [], null, 2);
        document.getElementById('pm-hidden').value = JSON.stringify(p.hiddenTestCases || [], null, 2);
        document.getElementById('problem-modal').style.display = 'flex';

        // Close chat panel
        toggleAiChat();

        showToast('Problem loaded into form! Review and save.', 'success');
    };

    window.regenerateAiProblem = () => {
        const input = document.getElementById('ai-chat-input');
        input.focus();
        appendAiMessage('bot', `<p style="font-size:.82rem;color:var(--text-secondary);">Sure! Describe the problem you'd like, or try one of these:</p>
            <div class="ai-suggestions">
                <button class="ai-suggestion-chip" onclick="sendAiSuggestion(this)">Easy string manipulation</button>
                <button class="ai-suggestion-chip" onclick="sendAiSuggestion(this)">Medium graph problem</button>
                <button class="ai-suggestion-chip" onclick="sendAiSuggestion(this)">Hard tree traversal</button>
            </div>`);
    };

    // ────────────────────────────────────────────────
    // Initial load
    await loadStats();
    await loadRecentTests();
})();
