# INFO212 Treningsapp

A Flask web app for planning, generating, and logging workouts with a built-in calendar.

---

## Setup

```bash
git clone https://github.com/Tsarian28/INFO212-GRUPPEPROSJEKT.git
cd INFO212-GRUPPEPROSJEKT
python -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```
## usage
Create a new user (username + password).
Add or generate workouts.
Try Weekly Plan to build a full program.
Open Calendar to view and schedule sessions.
Log out when done.

## structure:
- app.py                 # main Flask app
- models.py              # database helpers
- plan_logic.py          # smart training plan generator
- templates/             # HTML templates
- static/                # CSS and images
- instance/app.db        # auto-created local database

## Notes
The database is created automatically in /instance.
Delete instance/ to reset.
Run locally only; debug mode is on by default.

