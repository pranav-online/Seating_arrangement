from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import pymysql

# Load environment variables
load_dotenv()

app = Flask(__name__)

# ===== Configuration =====
app.config.update(
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev'),
    UPLOAD_FOLDER=Path(__file__).parent/'uploads',
    DATABASE_URI=f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@localhost/{os.getenv('DB_NAME')}?charset=utf8mb4",
    TEMPLATES_AUTO_RELOAD=True,
    ALLOWED_EXTENSIONS={'xls', 'xlsx'},
    MAX_CONTENT_LENGTH=5 * 1024 * 1024  # 5MB file size limit
)

# Ensure upload directory exists
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# ===== Database Connection =====
def get_db_engine():
    """Create and return a database engine"""
    try:
        engine = create_engine(
            app.config['DATABASE_URI'],
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        return engine
    except Exception as e:
        app.logger.error(f"Failed to create database engine: {str(e)}")
        raise

# ===== Database Initialization =====
def init_db():
    """Initialize database tables"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # Test connection first
            conn.execute(text("SELECT 1"))
            app.logger.info("Database connection successful")
            
            # Create students table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    roll_number VARCHAR(50) UNIQUE NOT NULL,
                    department VARCHAR(50) NOT NULL,
                    year VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            app.logger.info("Students table created")
            
            # Create index
            try:
                conn.execute(text("""
                    CREATE INDEX idx_dept_year ON students (department, year)
                """))
                app.logger.info("Index created")
            except Exception as e:
                app.logger.info(f"Index already exists: {str(e)}")
                
        return True
    except Exception as e:
        app.logger.error(f"Database initialization failed: {str(e)}")
        return False

# ===== Helper Functions =====
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def configure_logging():
    """Configure application logging"""
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

# ===== Routes =====
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/seating')
def seating():
    return render_template('seating.html')

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if not allowed_file(file.filename):
        return jsonify({"error": "Only .xls and .xlsx files allowed"}), 400

    try:
        # Read and validate Excel file
        df = pd.read_excel(file, engine='openpyxl', dtype=str)
        if df.empty:
            return jsonify({"error": "The file is empty"}), 400

        # Standardize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        column_mapping = {
            'name': ['name', 'student_name', 'student'],
            'roll_number': ['roll_number', 'roll', 'id', 'student_id'],
            'department': ['department', 'dept', 'branch', 'program'],
            'year': ['year', 'class', 'semester', 'current_year']
        }
        
        # Apply column mapping
        for standard_name, alternatives in column_mapping.items():
            for alt in alternatives:
                if alt in df.columns:
                    df = df.rename(columns={alt: standard_name})
                    break
            else:
                return jsonify({
                    "error": f"Required column '{standard_name}' not found",
                    "available_columns": list(df.columns),
                    "expected_names": alternatives
                }), 400

        # Data cleaning
        df = df.dropna(subset=['roll_number', 'name'])
        df = df[df['roll_number'].str.strip() != '']
        
        # Check for duplicates
        duplicates = df[df.duplicated('roll_number', keep=False)]
        if not duplicates.empty:
            return jsonify({
                "error": "Duplicate roll numbers found",
                "count": len(duplicates),
                "examples": duplicates.head(3).to_dict('records')
            }), 400

        # Clean data
        df['roll_number'] = df['roll_number'].astype(str).str.strip()
        df['name'] = df['name'].astype(str).str.strip()
        df['department'] = df['department'].astype(str).str.strip().str.lower()
        df['year'] = df['year'].astype(str).str.strip()
        df['dept_year'] = df['department'] + " - " + df['year']

        # Database operations
        engine = get_db_engine()
        with engine.begin() as conn:
            # Clear existing data
            conn.execute(text("TRUNCATE TABLE students"))
            
            # Insert data
            df[['name', 'roll_number', 'department', 'year']].to_sql(
                'students',
                conn,
                if_exists='append',
                index=False,
                chunksize=50
            )
            
        return jsonify({
            "success": True,
            "message": f"Uploaded {len(df)} student records",
            "departments": sorted(df['dept_year'].unique().tolist())
        })
        
    except Exception as e:
        app.logger.error(f"Upload failed: {str(e)}")
        return jsonify({
            "error": "Upload failed",
            "details": str(e),
            "solution": "Check your file format and try again"
        }), 500

@app.route('/generate_seating', methods=['POST'])
def generate_seating():
    try:
        # 1. Validate and parse input
        if not request.is_json:
            return jsonify({
                "error": "Request must be JSON",
                "solution": "Set Content-Type: application/json"
            }), 400

        data = request.get_json()
        
        # 2. Validate departments
        departments = []
        if isinstance(data.get('departments'), str):
            departments = [data['departments'].strip()]
        elif isinstance(data.get('departments'), list):
            departments = [str(d).strip() for d in data['departments'] if d and str(d).strip()]
        
        if not departments:
            return jsonify({
                "error": "No valid departments provided",
                "solution": "Provide at least one department"
            }), 400

        # 3. Get classroom parameters
        try:
            num_classrooms = max(1, int(data.get('classrooms', 3)))
            students_per_class = max(1, int(data.get('studentsPerClass', 30)))
        except (ValueError, TypeError) as e:
            return jsonify({
                "error": "Invalid numeric parameters",
                "solution": "Provide valid integers for classrooms and studentsPerClass"
            }), 400

        # 4. Database operations
        engine = get_db_engine()
        with engine.connect() as conn:
            # Get available departments
            available_depts = pd.read_sql(
                "SELECT DISTINCT CONCAT(department, ' - ', year) AS dept FROM students", 
                conn
            )['dept'].tolist()

            # Validate departments
            valid_depts = [d for d in departments if d in available_depts]
            if not valid_depts:
                return jsonify({
                    "error": "No matching departments found",
                    "requested": departments,
                    "available": available_depts
                }), 400

            # Get students sorted by department and roll number
            students = pd.read_sql(
                text("""
                    SELECT name, roll_number, department, year 
                    FROM students 
                    WHERE CONCAT(department, ' - ', year) IN :depts
                    ORDER BY department, roll_number
                """),
                conn,
                params={'depts': tuple(valid_depts)}
            )

            if students.empty:
                return jsonify({
                    "error": "No students found",
                    "departments": valid_depts
                }), 404

        # 5. Implement Round Robin seating algorithm
        seating_plan = []
        
        # Sort all students by roll number first (to maintain sequence)
        students = students.sort_values('roll_number').to_dict('records')
        
        # Initialize classrooms
        num_classrooms = max(1, int(data.get('classrooms', 3)))
        classrooms = [[] for _ in range(num_classrooms)]
        
        # Separate students by department
        dept_groups = {}
        for student in students:
            dept = student['department']
            if dept not in dept_groups:
                dept_groups[dept] = []
            dept_groups[dept].append(student)
        
        # Calculate maximum group size
        max_group_size = max(len(group) for group in dept_groups.values()) if dept_groups else 0
        
        # Distribute students with perfect interleaving
        for i in range(max_group_size):
            for dept, group in dept_groups.items():
                if i < len(group):
                    # Determine target classroom using modulo for even distribution
                    target_class = (i + list(dept_groups.keys()).index(dept)) % num_classrooms
                    classrooms[target_class].append({
                        **group[i],
                        'room': f"Room {target_class + 1}",
                        'seat': len(classrooms[target_class]) + 1
                    })
        
        # Flatten the seating plan
        seating_plan = [student for room in classrooms for student in room]
        
        return jsonify(seating_plan)
    except Exception as e:
        app.logger.error(f"Seating generation failed: {str(e)}")
        return jsonify({
            "error": "Unexpected error",
            "details": str(e),
            "solution": "Check server logs for more information"
        }), 500

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/check_data')
def check_data():
    """Endpoint to verify database contents"""
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            students = pd.read_sql("SELECT * FROM students LIMIT 50", conn)
            depts = pd.read_sql(
                "SELECT DISTINCT CONCAT(department, ' - ', year) AS dept FROM students", 
                conn
            )['dept'].tolist()
            return jsonify({
                "student_count": len(students),
                "sample_students": students.to_dict('records'),
                "available_departments": depts
            })
    except Exception as e:
        app.logger.error(f"Data check failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Configure logging
    configure_logging()
    
    # Verify MySQL connection first
    try:
        conn = pymysql.connect(
            host='localhost',
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        conn.close()
    except pymysql.Error as e:
        app.logger.error(f"MySQL connection failed: {e}")
        print("Verify your MySQL server is running and credentials are correct")
        exit(1)
    
    # Initialize database
    if init_db():
        app.logger.info("Application starting...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        app.logger.error("Failed to initialize database")
        print("❌ Failed to initialize database")