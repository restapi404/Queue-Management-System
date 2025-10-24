# Queue Management System (Django)

Simple web-based queue management system built with Django and SQLite.

Quick setup (Windows PowerShell):

1. Create and activate a virtualenv:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Apply migrations and create a superuser:

```powershell
python manage.py migrate; python manage.py createsuperuser
```

4. Run the development server:

```powershell
python manage.py runserver
```

Visit http://127.0.0.1:8000/ to access the site. Admin is at /admin/.

Notes:
- The project uses SQLite by default (db.sqlite3).
- Admin-only views require staff/superuser access.
- To reset/clear all tokens use the Admin Dashboard "Reset/Clear All Tokens" button.

Planned enhancements (placeholders in templates):
- SMS/Email notification integration
- Analytics/reporting
- Multi-language support
- Offline operation mode
