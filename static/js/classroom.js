// Google Classroom Management Logic

// Global State
let selectedCourseId = null;
let selectedCourseName = null;
let selectedStudentIds = [];
let assigneeMode = 'ALL_STUDENTS';

// UI Helpers
function showMessage(message, type = 'info') {
    // Log to Global Console
    if (window.synapseConsole) {
        window.synapseConsole.log(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    // No more alerts or legacy status box
}

// State Helpers
function setMaterialState(val, label) {
    document.getElementById('materialState').value = val;
    document.getElementById('materialStateLabel').innerText = label;
}

function setAssignmentState(val, label) {
    document.getElementById('assignmentState').value = val;
    document.getElementById('assignmentStateLabel').innerText = label;
}

function showLoading(show = true) {
    // Overlay removed to prevent flicker.
    // We rely on console logs for status updates.
    if (window.synapseConsole) {
        if (show) window.synapseConsole.log("⏳ 處理中...", 'info');
    }
}

// Authentication
async function authenticate() {
    try {
        showLoading(true);
        const resp = await fetch('/api/classroom/auth/start');
        const data = await resp.json();
        if (data.status === 'success' && data.authorization_url) {
            showMessage('👉 正在開啟 Google 授權頁面...', 'info');
            window.location.href = data.authorization_url;
        } else {
            showMessage('❌ ' + (data.message || '取得授權網址失敗'), 'error');
        }
    } catch (e) {
        showMessage('❌ 認證錯誤: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Course Management
// Course Management
function renderCourseList(courses) {
    const courseList = document.getElementById('courseList');
    courseList.innerHTML = '';

    if (!courses || courses.length === 0) {
        courseList.innerHTML = `
            <div class="col-12 text-center py-5">
                <h5 class="text-muted">No Courses Found</h5>
                <p class="small text-muted">You don't have any active courses as a Teacher.</p>
            </div>
            `;
        return;
    }

    courses.forEach(course => {
        const item = document.createElement('div');
        item.className = 'course-card card h-100 border-0 shadow-sm flex-shrink-0';
        item.style.minWidth = '240px';
        item.style.maxWidth = '240px';
        item.style.scrollSnapAlign = 'start';
        item.setAttribute('onclick', `selectCourse('${course.id}', '${course.name}', this)`);

        item.innerHTML = `
            <div class="card-body p-3">
                <h6 class="card-title text-dark fw-bold mb-1 text-truncate" title="${course.name}">${course.name}</h6>
                <p class="card-text text-muted small mb-0 text-truncate">${course.section || 'General'}</p>
            </div>
        `;
        courseList.appendChild(item);
    });
}

async function loadCourses(force = false) {
    const CACHE_KEY = 'synapse_classroom_courses';

    // 1. Try Cache
    if (!force) {
        const cached = sessionStorage.getItem(CACHE_KEY);
        if (cached) {
            try {
                const courses = JSON.parse(cached);
                if (window.synapseConsole) window.synapseConsole.log("Rendering from cache", "info");
                renderCourseList(courses);
                return; // Skip fetch
            } catch (e) {
                console.warn('Cache corrupted', e);
                sessionStorage.removeItem(CACHE_KEY);
            }
        }
    }

    // 2. Fetch if no cache or forced
    showLoading(true);
    try {
        const url = '/api/classroom/courses?role=teacher';
        const response = await fetch(url);
        if (response.status === 401) {
            // Need Auth
            showMessage('請先連接 Google Classroom', 'warning');
            const courseList = document.getElementById('courseList');
            courseList.innerHTML = `
                <div class="col-12 text-center py-5">
                    <div class="bg-white bg-opacity-50 rounded-4 p-5 d-inline-block shadow-sm border border-light">
                        <i class="fa-brands fa-google fa-3x text-danger opacity-50 mb-3"></i>
                        <h5 class="fw-bold text-muted">Authentication Required</h5>
                        <p class="small text-muted mb-4 opacity-75">Connect your Google account to manage courses.</p>
                        <button class="btn btn-warning text-white px-4 py-2 shadow-lg rounded-pill" onclick="authenticate()">
                            <i class="fa-solid fa-link me-2"></i> Connect Google Account
                        </button>
                    </div>
                </div>
            `;
            return;
        }

        const data = await response.json();

        if (data.status === 'success') {
            sessionStorage.setItem(CACHE_KEY, JSON.stringify(data.courses));
            renderCourseList(data.courses);
            showMessage(`已載入 ${data.count} 個課程`, 'success');
        } else {
            showMessage(data.message, 'error');
        }
    } catch (error) {
        showMessage('載入課程失敗: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

function selectCourse(courseId, courseName, element) {
    // Remove selected class from all cards
    document.querySelectorAll('.course-card').forEach(card => card.classList.remove('border-primary', 'shadow'));

    // Add to clicked (element is the card-body wrapper or card itself)
    const card = element.classList.contains('card') ? element : element.closest('.card');
    card.classList.add('border-primary', 'shadow');

    selectedCourseId = courseId;
    selectedCourseName = courseName;

    // Show sections
    ['studentSection', 'topicSection', 'materialSection', 'submissionSection', 'assignmentSection'].forEach(id => {
        document.getElementById(id).style.display = 'block';
    });

    // Actions
    showMessage(`Loading data for ${courseName}...`, 'info');
    showLoading(true);

    fetch(`/api/classroom/dashboard/${courseId}`)
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                const d = data.data;
                renderStudents(d.students);
                renderTopics(d.topics);
                renderCategories(d.gradeCategories);
                renderStats(d.coursework, d.stats);

                showMessage(`Dashboard loaded for ${courseName}`, 'success');
            } else {
                showMessage('Failed to load dashboard data', 'error');
            }
        })
        .catch(e => {
            showMessage('Error loading course data: ' + e.message, 'error');
        })
        .finally(() => {
            showLoading(false);
            // Smooth scroll to first section
            document.getElementById('studentSection').scrollIntoView({ behavior: 'smooth' });
        });
}

function renderStudents(students) {
    const studentList = document.getElementById('studentList');
    studentList.innerHTML = '';

    if (!students || students.length === 0) {
        studentList.innerHTML = `
            <div class="d-flex align-items-center justify-content-center" style="min-height: 200px;">
                <p class="text-muted small mb-0">No students found.</p>
            </div>
        `;
        return;
    }

    const listGroup = document.createElement('div');
    listGroup.className = 'list-group';

    students.forEach(student => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-center';
        item.innerHTML = `
            <div>
                <div class="fw-bold">${student.profile.name}</div>
                <small class="text-muted">${student.profile.emailAddress}</small>
            </div>
            <span class="badge bg-secondary rounded-pill">${student.userId.substr(-4)}</span>
        `;
        listGroup.appendChild(item);
    });
    studentList.appendChild(listGroup);
}

function renderTopics(topics) {
    const options = '<option value="">無主題</option>' +
        topics.map(t => `<option value="${t.topicId}">${t.name}</option>`).join('');
    document.getElementById('materialTopic').innerHTML = options;
    document.getElementById('assignmentTopic').innerHTML = options;
}

function renderCategories(cats) {
    const select = document.getElementById('assignmentGradeCategory');
    if (cats && cats.length > 0) {
        select.innerHTML = '<option value="">No Category</option>' +
            cats.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    } else {
        select.innerHTML = '<option value="">Default Grading</option>';
    }
}

function renderStats(coursework, statsMap) {
    const statsDiv = document.getElementById('submissionStats');
    if (!coursework || coursework.length === 0) {
        statsDiv.innerHTML = '<div class="text-muted p-3">No assignments found for tracking.</div>';
        return;
    }

    let html = `
    <div class="table-responsive">
        <table class="table table-hover align-middle table-sm small">
            <thead class="table-light">
                <tr>
                    <th>Assignment</th>
                    <th class="text-center">Turned In</th>
                    <th class="text-center">Missing</th>
                    <th class="text-center">Graded</th>
                    <th class="text-center">Rate</th>
                </tr>
            </thead>
            <tbody>
    `;

    coursework.forEach(w => {
        // statsMap keys are coursework IDs
        const s = statsMap[w.id] || { turned_in: 0, new: 0, created: 0, reclaimed_by_student: 0, returned: 0, turned_in_percentage: 0 };
        const missing = (s.created || 0) + (s.new || 0) + (s.reclaimed_by_student || 0);

        html += `
        <tr>
            <td class="fw-medium text-truncate" style="max-width: 200px;" title="${w.title}">${w.title}</td>
            <td class="text-center text-success fw-bold">${s.turned_in || 0}</td>
            <td class="text-center text-warning">${missing}</td>
            <td class="text-center text-primary">${s.returned || 0}</td>
            <td class="text-center">
                <div class="progress" style="height: 6px; width: 60px; margin: 0 auto;">
                    <div class="progress-bar bg-success" role="progressbar" style="width: ${s.turned_in_percentage}%"></div>
                </div>
                <span class="text-muted" style="font-size: 0.7em;">${s.turned_in_percentage}%</span>
            </td>
        </tr>
        `;
    });

    html += `</tbody></table></div>`;
    statsDiv.innerHTML = html;
}

// Old Loader Functions (Kept empty or redirects if needed, but mostly replaced)
// Student Management
async function viewStudents() { /* Replaced by renderStudents */ }
// Topic Management
async function loadTopics(id) { /* Replaced */ }
async function loadGradeCategories(id) { /* Replaced */ }
async function loadAllTracking() { /* Replaced */ }

// Deprecated separate loaders
async function loadTopics(courseId) { }
async function loadGradeCategories(courseId) { }
async function viewStudents() { }
async function loadAllTracking() { }

async function createTopics() {
    if (!selectedCourseId) return showMessage('請先選擇課程', 'warning');

    const numWeeks = document.getElementById('numWeeks').value;
    const prefix = document.getElementById('topicPrefix').value;

    showLoading(true);
    try {
        const response = await fetch('/api/classroom/topics/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                course_id: selectedCourseId,
                num_weeks: parseInt(numWeeks),
                prefix: prefix
            })
        });
        const data = await response.json();
        showMessage(data.message, data.status);
        if (data.status === 'success') loadTopics(selectedCourseId);
    } catch (error) {
        showMessage('建立主題失敗: ' + error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Assignments
function setAssigneeMode(mode) {
    assigneeMode = mode;
    const btnAll = document.getElementById('assignAll');
    const btnSome = document.getElementById('assignSome');

    if (mode === 'ALL_STUDENTS') {
        btnAll.classList.add('bg-primary', 'text-white');
        btnAll.classList.remove('btn-outline-primary');
        btnSome.classList.remove('bg-primary', 'text-white');
        btnSome.classList.add('btn-outline-primary');
        document.getElementById('studentPicker').style.display = 'none';
    } else {
        btnSome.classList.add('bg-primary', 'text-white');
        btnSome.classList.remove('btn-outline-primary');
        btnAll.classList.remove('bg-primary', 'text-white');
        btnAll.classList.add('btn-outline-primary');
        document.getElementById('studentPicker').style.display = 'block';
        loadStudentsForPicker();
    }
}

async function loadStudentsForPicker() {
    if (!selectedCourseId) return;
    const picker = document.getElementById('studentPicker');
    picker.innerHTML = '<div class="spinner-border spinner-border-sm"></div> 載入中...';

    try {
        const res = await fetch(`/api/classroom/students/${selectedCourseId}`);
        const data = await res.json();

        if (data.status === 'success') {
            picker.innerHTML = '';
            data.students.forEach(s => {
                const div = document.createElement('div');
                div.className = 'form-check';
                div.innerHTML = `
                <input class="form-check-input student-checkbox" type="checkbox" value="${s.userId}" id="stu_${s.userId}">
                <label class="form-check-label" for="stu_${s.userId}">
                    ${s.profile.name} <small class="text-muted">(${s.profile.emailAddress || ''})</small>
                </label>
            `;
                div.querySelector('input').onchange = (e) => {
                    if (e.target.checked) selectedStudentIds.push(s.userId);
                    else selectedStudentIds = selectedStudentIds.filter(id => id !== s.userId);
                };
                picker.appendChild(div);
            });
        }
    } catch (e) {
        picker.innerHTML = '<span class="text-danger">載入失敗</span>';
    }
}

async function publishAssignment() {
    if (!selectedCourseId) return showMessage('請先選擇課程', 'warning');

    const formData = new FormData();
    formData.append('course_id', selectedCourseId);
    formData.append('course_name', selectedCourseName);
    formData.append('title', document.getElementById('assignmentTitle').value);
    formData.append('description', document.getElementById('assignmentDescription').value);
    formData.append('max_points', document.getElementById('assignmentMaxPoints').value);
    formData.append('topic_id', document.getElementById('assignmentTopic').value);
    formData.append('assignee_mode', assigneeMode);
    formData.append('grade_category_id', document.getElementById('assignmentGradeCategory').value);

    // Handle Student IDs (Must append individually for list)
    if (selectedStudentIds.length > 0) {
        selectedStudentIds.forEach(id => formData.append('student_ids', id));
    }

    // Handle Dates
    const dtValue = document.getElementById('assignmentDueDate').value;
    if (dtValue) {
        const dt = new Date(dtValue);
        const dueDate = {
            year: dt.getFullYear(),
            month: dt.getMonth() + 1,
            day: dt.getDate()
        };
        const dueTime = {
            hours: dt.getHours(),
            minutes: dt.getMinutes(),
            seconds: 0
        };
        formData.append('due_date', JSON.stringify(dueDate));
        formData.append('due_time', JSON.stringify(dueTime));
    }

    // Handle File
    const fileInput = document.getElementById('assignmentFile');
    if (fileInput && fileInput.files[0]) {
        formData.append('file', fileInput.files[0]);
    }

    showLoading(true);
    try {
        const response = await fetch('/api/classroom/assignment/create', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        showMessage(data.message, data.status);
    } catch (e) {
        showMessage('發布失敗: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Material Publishing
async function publishMaterial() {
    if (!selectedCourseId) return showMessage('請先選擇課程', 'warning');

    const formData = new FormData();
    formData.append('course_id', selectedCourseId);
    formData.append('course_name', selectedCourseName);
    formData.append('title', document.getElementById('materialTitle').value);
    formData.append('description', document.getElementById('materialDescription').value);
    formData.append('topic_id', document.getElementById('materialTopic').value);
    formData.append('link', document.getElementById('materialLink').value);

    // Handle File
    const fileInput = document.getElementById('materialFile');
    if (fileInput && fileInput.files[0]) {
        formData.append('file', fileInput.files[0]);
    }

    showLoading(true);
    try {
        const response = await fetch('/api/classroom/material/create', {
            method: 'POST',
            body: formData // Content-Type auto-set
        });
        const data = await response.json();
        showMessage(data.message, data.status);
    } catch (e) {
        showMessage('發布失敗: ' + e.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Load Coursework Helper
async function loadCoursework(courseId) {
    const select = document.getElementById('courseworkSelect');
    if (!select) return;

    try {
        const res = await fetch(`/api/classroom/coursework/${courseId}`);
        const data = await res.json();
        if (data.status === 'success') {
            select.innerHTML = '<option value="">請先選擇作業</option>' +
                data.coursework.map(w => `<option value="${w.id}">${w.title}</option>`).join('');
        }
    } catch (e) {
        console.error('Coursework load fail', e);
    }
}

// Deprecated Load Tracking
// async function loadAllTracking() {}

// Init
document.addEventListener('DOMContentLoaded', () => {
    // Initial setup
    loadCourses();
});
