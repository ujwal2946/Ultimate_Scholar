import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

from utils.db import execute, fetch_one


load_dotenv()


def _get_env(name: str, default=None):
    return os.getenv(name, default)


def send_absence_notification_gmail(payload: dict):
    """Send Gmail SMTP notification.

    payload keys:
      - student_full_name
      - class_name
      - section
      - attendance_date
      - parent_email

    Returns: (success: bool, error_message: str|None)
    """

    student_full_name = payload.get("student_full_name")
    class_name = payload.get("class_name")
    section = payload.get("section")
    attendance_date = payload.get("attendance_date")
    parent_email = payload.get("parent_email")

    # .env expected keys
    smtp_host = _get_env("GMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(_get_env("GMAIL_SMTP_PORT", "587"))
    smtp_user = _get_env("GMAIL_SMTP_USER", "")
    smtp_password = _get_env("GMAIL_SMTP_PASSWORD", "")
    from_email = _get_env("GMAIL_FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_password or not from_email:
        return False, "Gmail SMTP credentials missing in .env"

    # Helpful for troubleshooting in dev. Never log the password.
    # (You can remove this after SMTP works.)
    print("[MAIL] Using Gmail SMTP:", smtp_host, smtp_port, "from=", from_email) 


    subject = "Attendance Alert"
    body = (
        "Dear Parent,\n\n"
        "Your child has been marked ABSENT today.\n\n"
        f"Student Name: {student_full_name}\n"
        f"Class: {class_name}\n"
        f"Section: {section}\n"
        f"Date: {attendance_date}\n\n"
        "Regards\n"
        "Student Database Management System"
    )

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = parent_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    def _send_starttls(port: int):
        with smtplib.SMTP(smtp_host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [parent_email], msg.as_string())

    def _send_ssl(port: int):
        with smtplib.SMTP_SSL(smtp_host, port, timeout=20) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [parent_email], msg.as_string())

    try:
        if smtp_port == 465:
            _send_ssl(smtp_port)
        else:
            _send_starttls(smtp_port)
        return True, None
    except PermissionError as e:
        # Some networks block STARTTLS/587 but permit Gmail's implicit TLS
        # endpoint. Retry that endpoint before reporting a local socket block.
        if smtp_host.lower() == "smtp.gmail.com" and smtp_port != 465:
            try:
                _send_ssl(465)
                return True, None
            except Exception as fallback_error:
                return False, (
                    "SMTP connections on ports 587 and 465 are blocked by this "
                    f"Windows environment: {type(fallback_error).__name__}: {fallback_error}"
                )
        return False, f"SMTP connection blocked by this Windows environment: {e}"
    except Exception as e:
        # Include exception type for easier troubleshooting.
        return False, f"{type(e).__name__}: {e}"



def record_and_send_absence_notification(*, student_id: int, attendance_id: int, attendance_date, status: str):
    """Persist notifications row and attempt sending.

    Must be called after attendance row is saved. Returns ``(sent, message)`` so
    the attendance page can tell the signed-in user what happened.
    """

    # Retrieve parent email and student info
    student = fetch_one(
        """
        SELECT id, full_name, class, section, parent_email
        FROM students
        WHERE id=%s
        """,
        (student_id,),
    )

    if not student:
        # still create notification row with error
        execute(
            """
            INSERT INTO notifications (student_id, parent_email, subject, message, notification_status, sent_at, error_message)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """,
            (student_id, "", "Attendance Alert", "Student not found", "failed", "student record missing"),
        )
        return False, "The student record was not found, so no email was sent."

    parent_email = student.get("parent_email") or ""
    full_name = student.get("full_name") or ""
    class_name = student.get("class") or ""
    section = student.get("section") or ""

    subject = "Attendance Alert"
    message = (
        "Dear Parent,\n\n"
        "Your child has been marked ABSENT today.\n\n"
        f"Student Name: {full_name}\n"
        f"Class: {class_name}\n"
        f"Section: {section}\n"
        f"Date: {attendance_date}\n\n"
        "Regards\n"
        "Thank U from Unified Scholor"
    )

    # Prevent duplicate notification sends for the same student+date when possible.
    # Your current schema doesn't include attendance_date/notification_type in notifications,
    # so de-duplication isn't reliable. We'll skip de-dup checks to ensure emails send.


    # If no parent email, record failure and return
    if not parent_email:
        execute(
            """
            INSERT INTO notifications (student_id, parent_email, subject, message, notification_status, sent_at, error_message)
            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
            """,
            (student_id, "", subject, message, "failed", "parent_email missing"),
        )
        return False, "The parent email address is missing, so no email was sent."

    ok, err = send_absence_notification_gmail(
        {
            "student_full_name": full_name,
            "class_name": class_name,
            "section": section,
            "attendance_date": attendance_date,
            "parent_email": parent_email,
        }
    )

    # A failed delivery must not look like it was sent. Keep the error in the
    # audit row, but leave sent_at empty unless Gmail accepted the message.
    try:
        if ok:
            execute(
                """
                INSERT INTO notifications (
                    student_id, parent_email, subject, message,
                    notification_status, sent_at, error_message
                )
                VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                """,
                (student_id, parent_email, subject, message, "sent", None),
            )
        else:
            execute(
                """
                INSERT INTO notifications (
                    student_id, parent_email, subject, message,
                    notification_status, sent_at, error_message
                )
                VALUES (%s, %s, %s, %s, %s, NULL, %s)
                """,
                (student_id, parent_email, subject, message, "failed", err),
            )
    except Exception as exc:
        # Attendance has already been saved. Do not turn a notification-audit
        # failure into a 500 error on the attendance page.
        return False, f"Email could not be recorded: {type(exc).__name__}"

    if ok:
        return True, f"Absence notification sent to {parent_email}."
    return False, f"Attendance was saved, but the absence email failed: {err}"


