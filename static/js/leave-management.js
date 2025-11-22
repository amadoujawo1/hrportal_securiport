document.addEventListener('DOMContentLoaded', function() {
    initializeCalendar();
    initializeDocumentUpload();
    updateLeaveBalance();
});

function initializeCalendar() {
    const calendar = document.getElementById('leave-calendar');
    const today = new Date();
    let currentMonth = today.getMonth();
    let currentYear = today.getFullYear();
    
    function renderCalendar() {
        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        const startDate = document.getElementById('start_date');
        const endDate = document.getElementById('end_date');
        
        let calendarHTML = `
            <div class="calendar-header">
                <button onclick="previousMonth()" class="btn btn-link">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
                </button>
                <h3>${new Date(currentYear, currentMonth).toLocaleString('default', { month: 'long', year: 'numeric' })}</h3>
                <button onclick="nextMonth()" class="btn btn-link">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
                </button>
            </div>
            <div class="calendar-grid">
                ${['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => 
                    `<div class="calendar-day day-name">${day}</div>`
                ).join('')}
        `;
        
        for (let i = 0; i < firstDay.getDay(); i++) {
            calendarHTML += '<div class="calendar-day disabled"></div>';
        }
        
        for (let day = 1; day <= lastDay.getDate(); day++) {
            const date = new Date(currentYear, currentMonth, day);
            const isToday = date.toDateString() === today.toDateString();
            const isSelected = (startDate.value && date.toISOString().split('T')[0] === startDate.value) ||
                             (endDate.value && date.toISOString().split('T')[0] === endDate.value);
            
            calendarHTML += `
                <div class="calendar-day ${isToday ? 'today' : ''} ${isSelected ? 'selected' : ''}"
                     onclick="selectDate('${date.toISOString().split('T')[0]}')">
                    ${day}
                </div>`;
        }
        
        calendar.innerHTML = calendarHTML;
    }
    
    window.previousMonth = function() {
        currentMonth--;
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        }
        renderCalendar();
    };
    
    window.nextMonth = function() {
        currentMonth++;
        if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        renderCalendar();
    };
    
    window.selectDate = function(dateStr) {
        const startDate = document.getElementById('start_date');
        const endDate = document.getElementById('end_date');
        
        if (!startDate.value || (startDate.value && endDate.value)) {
            startDate.value = dateStr;
            endDate.value = '';
        } else {
            const start = new Date(startDate.value);
            const selected = new Date(dateStr);
            
            if (selected >= start) {
                endDate.value = dateStr;
            } else {
                endDate.value = startDate.value;
                startDate.value = dateStr;
            }
        }
        
        renderCalendar();
        calculateLeaveDuration();
    };
    
    renderCalendar();
}

function initializeDocumentUpload() {
    const dropZone = document.getElementById('document-upload');
    const fileList = document.getElementById('document-preview');
    const fileInput = document.getElementById('file-input');
    
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    function handleFiles(files) {
        Array.from(files).forEach(file => {
            const reader = new FileReader();
            reader.onload = () => {
                const fileItem = document.createElement('div');
                fileItem.className = 'document-item';
                fileItem.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                    </svg>
                    ${file.name}
                    <span class="remove-doc" onclick="this.parentElement.remove()">&times;</span>
                `;
                fileList.appendChild(fileItem);
            };
            reader.readAsDataURL(file);
        });
    }
}

function updateLeaveBalance() {
    // This function would typically fetch the leave balance from the server
    // For now, we'll use placeholder data
    const balanceData = {
        annual: 20,
        sick: 10,
        remaining: 15
    };
    
    const balanceContainer = document.getElementById('leave-balance');
    balanceContainer.innerHTML = `
        <div class="balance-item">
            <div class="balance-value">${balanceData.annual}</div>
            <div class="balance-label">Annual Leave</div>
        </div>
        <div class="balance-item">
            <div class="balance-value">${balanceData.sick}</div>
            <div class="balance-label">Sick Leave</div>
        </div>
        <div class="balance-item">
            <div class="balance-value">${balanceData.remaining}</div>
            <div class="balance-label">Remaining Days</div>
        </div>
    `;
}

function calculateLeaveDuration() {
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    
    if (startDate && endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const duration = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
        
        document.getElementById('leave-duration').textContent = 
            `Duration: ${duration} day${duration !== 1 ? 's' : ''}`;
    }
}