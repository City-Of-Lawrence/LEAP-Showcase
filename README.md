# LEAP Web Portal — Setup & Run Guide

## What this is
Flask web app for the City of Lawrence Energy Affordability Program.
Handles resident/landlord registration before directing participants
to official Mass Save enrollment at masssave.com/Lawrence.

## File layout

```
leap_app/
  app.py                  ← Flask routes and logic
  requirements.txt        ← Python dependencies
  templates/
    base.html             ← Shared layout with Lawrence branding
    index.html            ← Landing page
    address_search.html   ← Generic path: address lookup
    confirm_address.html  ← Address confirmation (both paths)
    role.html             ← Role selection
    intent.html           ← Intent selection
    contact.html          ← Optional contact info
    done.html             ← Completion page
    error.html            ← Error page
    admin_login.html      ← Staff login
    admin.html            ← Staff registrations dashboard
```

## Databases expected (place in same folder as app.py)

| File                      | Used for                              |
|---------------------------|---------------------------------------|
| upinmgmt.sqlite           | UPIN validation + registrations table |
| lawrence_master.sqlite    | Property details (Assessment_L_Parcels)|
| LEAPMailings_clean.sqlite | Address/unit lookup (Outreach_Master_Unified) |

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy your databases into the leap_app folder
cp /path/to/upinmgmt.sqlite .
cp /path/to/lawrence_master.sqlite .
cp /path/to/LEAPMailings_clean.sqlite .

# 4. Run
python app.py
```

Open http://localhost:5000 in your browser.

## Admin dashboard

Visit http://localhost:5000/admin
Default password: leapadmin2026  ← change before sharing with anyone

To change: set environment variable before running:
  export ADMIN_PASSWORD=yournewpassword

## QR path testing

A QR code URL looks like:
  http://localhost:5000/register?upin=ABCD1234XY

Where ABCD1234XY is the plaintext UPIN issued by upin_store.py.
To get a test UPIN, run cli.py and use option 4 (random residential parcel)
then note the printed plaintext UPIN.

## Environment variables (all optional)

| Variable        | Default               | Description                    |
|-----------------|-----------------------|--------------------------------|
| DB_UPIN         | upinmgmt.sqlite       | Path to UPIN database          |
| DB_MASTER       | lawrence_master.sqlite| Path to master parcel database |
| DB_OUTREACH     | LEAPMailings_clean.sqlite | Path to outreach/unit DB   |
| ADMIN_PASSWORD  | leapadmin2026         | Staff dashboard password       |
| SECRET_KEY      | dev-secret-...        | Flask session key (change!)    |

## Notes

- Registration with the City is optional per the Municipal Registration Model.
  The app never blocks a user from proceeding to masssave.com/Lawrence.
- UPIN management (issue/revoke/reissue) remains in cli.py — not exposed
  via web UI in this prototype.
- Unit-UPIN generation is deferred to a future iteration.
- Spanish language support is deferred to post-prototype.
