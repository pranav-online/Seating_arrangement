document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const uploadBtn = document.getElementById('uploadBtn');
    const generateBtn = document.getElementById('generateBtn');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const departmentSection = document.getElementById('departmentSection');
    
    // Event Listeners
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadFile);
    }
    
    if (generateBtn) {
        generateBtn.addEventListener('click', generateSeating);
    }

    // Functions
    async function uploadFile() {
        const file = fileInput.files[0];
        const originalText = uploadBtn.textContent;
        uploadBtn.disabled = true;
        uploadBtn.textContent = "Uploading...";
        
        try {
            if (!file) {
                throw new Error("Please select a file!");
            }
        
            // Validate file type
            if (!file.name.match(/\.(xlsx|xls)$/i)) {
                throw new Error("Please upload an Excel file (.xlsx or .xls)");
            }
        
            const formData = new FormData();
            formData.append('file', file);
        
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
    
            renderDepartments(data.departments);
            uploadStatus.innerHTML = `<div class="success">${data.message}</div>`;
            departmentSection.classList.remove('hidden');
        } catch (error) {
            uploadStatus.innerHTML = `<div class="error">${error.message}</div>`;
            console.error("Upload error:", error);
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = originalText;
        }
    }

    function renderDepartments(departments) {
        const container = document.getElementById('departmentList');
        container.innerHTML = '';

        departments.forEach(dept => {
            const div = document.createElement('div');
            div.className = 'checkbox-item';
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.id = `dept-${dept.replace(/\s+/g, '-')}`;
            checkbox.value = dept;
            checkbox.checked = true;
            
            const label = document.createElement('label');
            label.htmlFor = checkbox.id;
            label.textContent = dept;
            
            div.appendChild(checkbox);
            div.appendChild(label);
            container.appendChild(div);
        });
    }

    async function generateSeating() {
        const originalText = generateBtn.textContent;
        generateBtn.disabled = true;
        generateBtn.textContent = "Generating...";
        
        try {
            const selectedDepts = Array.from(
                document.querySelectorAll('#departmentList input:checked')
            ).map(el => el.value);

            const classrooms = document.getElementById('classrooms').value;
            const studentsPerClass = document.getElementById('studentsPerClass').value;
            const resultDiv = document.getElementById('result');

            if (selectedDepts.length === 0) {
                throw new Error("Please select at least one department!");
            }

            if (isNaN(classrooms) || classrooms < 1) {
                throw new Error("Please enter a valid number of classrooms (minimum 1)");
            }
            
            if (isNaN(studentsPerClass) || studentsPerClass < 1) {
                throw new Error("Please enter a valid number of students per class (minimum 1)");
            }

            resultDiv.innerHTML = "<p>Generating seating arrangement...</p>";
            
            const response = await fetch('/generate_seating', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    departments: selectedDepts,
                    classrooms: parseInt(classrooms),
                    studentsPerClass: parseInt(studentsPerClass)
                })
            });

            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }

            displayResults(result);
        } catch (error) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = `<div class="error">Error: ${error.message}</div>`;
            console.error("Seating error:", error);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = originalText;
        }
    }

    function displayResults(data) {
        const container = document.getElementById('result');
        container.innerHTML = '';

        if (!data || data.length === 0) {
            container.innerHTML = "<p class='error'>No seating data available.</p>";
            return;
        }

        // Create summary statistics
        const summary = document.createElement('div');
        summary.className = 'summary';
        
        const totalStudents = data.length;
        const rooms = [...new Set(data.map(item => item.room))];
        const departments = [...new Set(data.map(item => item.department))];
        
        summary.innerHTML = `
            <h3>Seating Summary</h3>
            <p>Total Students: ${totalStudents}</p>
            <p>Classrooms Used: ${rooms.length}</p>
            <p>Departments: ${departments.join(', ')}</p>
        `;
        container.appendChild(summary);

        // Group by classroom for better display
        const byRoom = data.reduce((acc, student) => {
            if (!acc[student.room]) acc[student.room] = [];
            acc[student.room].push(student);
            return acc;
        }, {});

        // Create a section for each classroom
        for (const [room, students] of Object.entries(byRoom)) {
            const roomSection = document.createElement('div');
            roomSection.className = 'room-section';
            
            const roomHeader = document.createElement('h3');
            roomHeader.textContent = `${room} (${students.length} students)`;
            roomSection.appendChild(roomHeader);
            
            const table = document.createElement('table');
            
            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            ['Seat', 'Roll Number', 'Name', 'Department'].forEach(text => {
                const th = document.createElement('th');
                th.textContent = text;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);
            
            // Create body
            const tbody = document.createElement('tbody');
            students.forEach(student => {
                const row = document.createElement('tr');
                [student.seat, student.roll_number, student.name, student.department].forEach(value => {
                    const td = document.createElement('td');
                    td.textContent = value;
                    row.appendChild(td);
                });
                tbody.appendChild(row);
            });
            table.appendChild(tbody);
            
            roomSection.appendChild(table);
            container.appendChild(roomSection);
        }
        
        // Add export button
        const exportBtn = document.createElement('button');
        exportBtn.className = 'btn';
        exportBtn.textContent = 'Export to Excel';
        exportBtn.addEventListener('click', () => exportToExcel(data));
        container.appendChild(exportBtn);
    }

    function exportToExcel(data) {
        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.json_to_sheet(data);
        XLSX.utils.book_append_sheet(wb, ws, "Seating Arrangement");
        XLSX.writeFile(wb, "exam_seating_arrangement.xlsx");
    }
});