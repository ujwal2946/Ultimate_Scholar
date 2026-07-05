from werkzeug.security import generate_password_hash

from utils.db import execute, fetch_one


def seed_default_users():
    # Admin defaults
    admin_username = "Ujwal"
    admin_plain_password = "2006@Ujwal"
    admin_hash = generate_password_hash(admin_plain_password)

    # Attendant defaults
    attendant_username = "Track"
    attendant_plain_password = "attend_2946"
    attendant_hash = generate_password_hash(attendant_plain_password)

    # Upsert-like behavior: check then insert
    existing_admin = fetch_one("SELECT id FROM admins WHERE username=%s", (admin_username,))
    if not existing_admin:
        execute("INSERT INTO admins (username, password) VALUES (%s,%s)", (admin_username, admin_hash))

    existing_attendant = fetch_one(
        "SELECT id FROM attendants WHERE username=%s", (attendant_username,)
    )
    if not existing_attendant:
        execute(
            "INSERT INTO attendants (username, password) VALUES (%s,%s)",
            (attendant_username, attendant_hash),
        )

    print("Seeded default admin & attendant (if missing).")


if __name__ == "__main__":
    seed_default_users()

