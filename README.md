# Ultimate Scholar

A role-based student database management system built with Flask and MySQL. Ultimate Scholar provides separate experiences for administrators, attendants, and students, with tools for managing student records, attendance, grades, reports, and school data.

> This project is intended for local development. Review the security notes before using it outside a trusted environment.

## Highlights

- Role-based sign-in for **administrators**, **attendants**, and **students**
- Session-based authentication with protected routes and role checks
- Administrator student-management module:
  - Create, view, edit, search, filter, paginate, and delete student records
  - Automatic generation of student usernames and initial passwords
- Attendance workflows for administrators and attendants
- Student attendance dashboard
- Optional email notifications to parents when a student is marked absent
- Administrator attendance reports with CSV export
- Grade-management and student grade-dashboard routes
- Administrator analytics for attendance and grade distribution
- Password hashing with Werkzeug

## Technology

| Area | Tools |
| --- | --- |
| Backend | Python, Flask |
| Database | MySQL, PyMySQL |
| Authentication | Flask sessions, Werkzeug password hashing |
| Configuration | python-dotenv |
| Front end | Flask templates, Bootstrap |
| Reporting | CSV export |

## Project structure

```text
Ultimate_Scholar/
├── app.py                  # Flask application factory and blueprint registration
├── config.py               # Environment-based configuration
├── requirements.txt        # Python dependencies
├── database/
│   └── schema.sql          # Core MySQL schema
├── routes/                 # Authentication, dashboard, attendance, grades, reports, and admin routes
├── services/
│   └── seed_default_users.py
├── utils/                  # Database, authentication, and email helpers
├── templates/              # Jinja templates
└── static/                 # Static assets
```

## Prerequisites

- Python 3
- MySQL Server
- `pip`

## Local setup

### 1. Clone the repository

```bash
git clone https://github.com/ujwal2946/Ultimate_Scholar.git
cd Ultimate_Scholar
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database and load the schema

Create a MySQL database (the default name is `student_db`):

```sql
CREATE DATABASE student_db;
```

Then load the included schema:

```bash
mysql -u root -p student_db < database/schema.sql
```

### 5. Configure environment variables

Create a `.env` file in the repository root. The application reads the following database and Flask settings:

```env
FLASK_SECRET_KEY=replace-with-a-long-random-value

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=student_db
```

For absence-notification emails, add these optional Gmail SMTP settings:

```env
GMAIL_SMTP_HOST=smtp.gmail.com
GMAIL_SMTP_PORT=587
GMAIL_SMTP_USER=your-email@gmail.com
GMAIL_SMTP_PASSWORD=your-gmail-app-password
GMAIL_FROM_EMAIL=your-email@gmail.com
```

The `.env` file is ignored by Git and must not be committed. A non-empty `MYSQL_PASSWORD` is required by the database helper.

### 6. Seed the default users

```bash
python -m services.seed_default_users
```

This creates the following development accounts when they do not already exist:

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `Ujwal` | `2006@Ujwal` |
| Attendant | `Track` | `attend_2946` |

Change these credentials before any real deployment. Student accounts are created through the administrator's student-management module.

### 7. Run the application

```bash
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser, select a role, and sign in.

## Using the application

1. Sign in as an administrator to manage student records, attendance, grades, reports, analytics, and administrator settings.
2. Sign in as an attendant to access attendant attendance workflows.
3. Students can sign in using the credentials created for their record to view their dashboard, attendance, and grades.

When an administrator creates a student, the app generates the student's username from their name and date of birth, and an initial password from their name. Share those credentials securely and change them as appropriate.

## Database notes

The included `database/schema.sql` creates the core user, student, attendance, and notification tables. The application also includes grade-management, grade-dashboard, and analytics routes that query grade data; ensure the database schema used in your environment includes the required grade tables before using those features.

## Security notes

- Replace the development `FLASK_SECRET_KEY` with a strong, private value.
- Do not use the seeded credentials in production.
- Configure HTTPS and set secure session cookies before deployment.
- Keep database and SMTP credentials in environment variables only.
- The student-delete flow currently relies on same-origin sessions and does not include CSRF protection; add CSRF protection before production use.

## Contributing

Contributions are welcome. Please keep changes focused, test them locally, and describe the purpose of each change clearly in a pull request.

## License

No license file is currently included. All rights remain with the repository owner unless a license is added.
