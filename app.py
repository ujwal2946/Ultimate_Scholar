import os

from flask import Flask

from dotenv import load_dotenv

from config import Config



from routes.main import bp_main
from routes.auth_admin import bp_auth_admin
from routes.auth_attendant import bp_auth_attendant
from routes.auth_student import bp_auth_student
from routes.admin import bp_admin
from routes.attendant import bp_attendant
from routes.student import bp_student
from routes.student_mgmt import bp_student_mgmt
from routes.attendance_admin import bp_attendance_admin
from routes.attendance_attendant import bp_attendance_attendant
from routes.attendance_student import bp_attendance_student
from routes.grades_admin import bp_grades_admin
from routes.grades_student import bp_grades_student
from routes.reports_admin import bp_reports_admin
from routes.analytics_admin import bp_analytics_admin
from routes.settings_admin import bp_settings_admin

from routes.errors import bp_errors

from routes.logout import bp_logout



def create_app():
    # Ensure .env in project root is loaded (when running from different working directories)
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
    app = Flask(__name__, template_folder="templates", static_folder="static")


    app.config.from_object(Config)

    # Session-based auth
    app.secret_key = app.config["SECRET_KEY"]

    # Register blueprints
    app.register_blueprint(bp_errors)
    app.register_blueprint(bp_main)

    app.register_blueprint(bp_auth_admin, url_prefix="/auth")
    app.register_blueprint(bp_auth_attendant, url_prefix="/auth")
    app.register_blueprint(bp_auth_student, url_prefix="/auth")

    app.register_blueprint(bp_admin, url_prefix="/admin")
    app.register_blueprint(bp_attendant, url_prefix="/attendant")
    app.register_blueprint(bp_student, url_prefix="/student")
    app.register_blueprint(bp_attendance_admin, url_prefix="/admin/attendance")
    app.register_blueprint(bp_attendance_attendant, url_prefix="/attendant/attendance")
    app.register_blueprint(bp_attendance_student, url_prefix="/student/attendance")
    # Student management (admin)
    app.register_blueprint(bp_student_mgmt, url_prefix="/admin/students")

    # Admin reports
    app.register_blueprint(bp_reports_admin, url_prefix="/admin/reports")
    # Admin analytics
    app.register_blueprint(bp_analytics_admin, url_prefix="/admin/analytics")

    app.register_blueprint(bp_settings_admin, url_prefix="/admin/settings")

    # Grades admin
    app.register_blueprint(bp_grades_admin, url_prefix="/admin/grades")

    app.register_blueprint(bp_grades_student, url_prefix="/student/grades")



    app.register_blueprint(bp_logout)

    return app





if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)

