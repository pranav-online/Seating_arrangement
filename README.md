# Exam Seating Arrangement System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.3.2-green.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)

A web-based application that automatically generates optimized exam seating arrangements while maintaining roll number sequences and preventing department clustering.

## Features

- **Excel Upload**: Process student data from Excel files
- **Smart Distribution**: Round-robin algorithm for fair seating
- **Department Mixing**: Prevents subject-wise clustering
- **Data Validation**: Cleans and standardizes input data
- **Export Options**: Download seating plans as Excel files
- **Responsive UI**: Works on desktop and mobile devices

## Technology Stack

### Backend
- Python 3.8+
- Flask (Web Framework)
- SQLAlchemy (ORM)
- Pandas (Data Processing)
- MySQL (Database)

### Frontend
- HTML5, CSS3, JavaScript
- XLSX.js (Excel export)

## Installation

### Prerequisites
- Python 3.8+
- MySQL Server 8.0
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/exam-seating-system.git
cd exam-seating-system
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up MySQL:
```sql
CREATE DATABASE seating_system;
CREATE USER 'seating_user'@'localhost' IDENTIFIED BY 'yourpassword';
GRANT ALL PRIVILEGES ON seating_system.* TO 'seating_user'@'localhost';
FLUSH PRIVILEGES;
```

5. Create `.env` file:
```env
DB_USER=seating_user
DB_PASSWORD=yourpassword
DB_NAME=seating_system
SECRET_KEY=your-secret-key-here
```

## Usage

1. Run the application:
```bash
flask run
```

2. Access the web interface at:
```
http://localhost:5000
```

3. Workflow:
   - Upload student data Excel file
   - Select departments to include
   - Set number of classrooms and capacity
   - Generate and view seating arrangement
   - Export to Excel if needed

## File Structure

```
exam-seating-system/
├── app.py                 # Main application
├── requirements.txt       # Dependencies
├── .env.example           # Environment template
├── static/
│   ├── css/               # Stylesheets
│   └── js/                # JavaScript files
└── templates/
    ├── base.html          # Base template
    ├── home.html          # Home page
    └── seating.html       # Seating arrangement page
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/upload` | POST | Handle Excel uploads |
| `/generate_seating` | POST | Generate seating plan |
| `/static/<path>` | GET | Serve static files |

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Your Name - pranav05gedela@gmail.com
linkedin - Gedela Pranav

Project Link: [https://github.com/yourusername/exam-seating-system](https://github.com/yourusername/exam-seating-system)
