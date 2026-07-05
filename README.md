# Student Database Management System (Foundation)

Foundation for a Student Database Management System built with **Flask**, **MySQL**, **Bootstrap**, and **session-based auth**.

## Features implemented in this step
- Welcome page + role selection (glassmorphism)
- Role-based login pages (Admin / Attendant / Student)
- Session-based authentication + route protection
- Separate dashboards (UI only; no attendance/grades/report logic)
- MySQL schema scripts for required tables
- Password hashing via Werkzeug
- Admin-only Student Management module (CRUD, search, filters, pagination)


## Project structure
- `app.py` - app entrypoint
- `config.py` - configuration via environment variables
- `routes/` - Flask blueprints
- `utils/` - shared helpers (auth decorators)
- `database/` - MySQL SQL scripts

## Local setup
### 1) Create database
Create a MySQL database named `student_db` (or change `MYSQL_DATABASE` in `.env`).

### 2) Run schema
```bash
mysql -u root -p student_db < database/schema.sql
```

### 3) Configure environment
Copy `.env.example` to `.env` and update values.

### 4) Install dependencies
```bash
pip install -r requirements.txt
```

### 5) Seed default users
Run:
```bash
python -c "from services.seed_default_users import seed_default_users; seed_default_users()"
```

Default credentials:
- Admin: Ujwal / 2006@Ujwal
- Attendant: Track / attend_2946

Student credentials depend on rows inserted into `students` table.

### 6) Start server
```bash
python app.py
```
Open: http://127.0.0.1:5000

## Deploy later
Project is structured to be deployable on platforms like Render/Railway by using environment variables and a production-ready WSGI server.

"# Ultimate_Scholar" 
