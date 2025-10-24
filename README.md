# Queue Management System

A Django-based queue management system with SMS notifications for token status updates.

## Features

- Token generation with SMS notifications
- Real-time queue status updates
- Admin dashboard for queue management
- Automatic counter assignment
- SMS notifications for:
  - Token creation
  - Service ready notifications
  - Next-in-line alerts

## Setup

1. Clone the repository:
```bash
git clone https://github.com/restapi404/Queue-Management-System.git
cd Queue-Management-System
```

2. Create and activate a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration:
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
# - TWILIO_MESSAGING_SERVICE_SID
# - TWILIO_PHONE_NUMBER
```

5. Apply migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

## Running the Application

The application requires two components to run:

1. The Django development server:
```bash
python manage.py runserver
```

2. The automatic token assignment process (in a separate terminal):
```bash
python manage.py auto_assign_tokens
```

The auto-assignment process continuously:
- Assigns waiting tokens to available counters
- Maintains queue fairness (configurable threshold)
- Auto-completes tokens that exceed maximum serving time
- Sends SMS notifications for status changes

Important: Both processes need to be running for automatic counter assignment to work.

## Accessing the Application

- Main application: http://127.0.0.1:8000/
- Admin interface: http://127.0.0.1:8000/admin/
- Queue status: http://127.0.0.1:8000/status/<token_number>/
- Admin dashboard: http://127.0.0.1:8000/admin-dashboard/

## Additional Notes

- Uses SQLite database by default (db.sqlite3)
- Admin-only views require staff/superuser access
- Reset/clear all tokens via Admin Dashboard
- SMS notifications require valid Twilio credentials
- Configure fairness settings in environment:
  - FAIRNESS_THRESHOLD (default: 3 tokens)
  - AUTO_ASSIGN_INTERVAL (default: 5 seconds)
  - MAX_SERVING_TIME (default: 10 minutes)
