"""
app.py  –  LEAP City of Lawrence Registration Portal
Flask prototype  |  March 2026

Entry point. Configures the app, registers blueprints, wires up
DB teardown and schema startup. All routes live in:
  routes/public.py  — resident-facing flows  (Blueprint "public")
  routes/admin.py   — admin panel            (Blueprint "admin", prefix /admin)

Shared helpers in helpers.py, DB/schema management in schema.py.
"""

import os
from datetime import datetime, timezone
from flask import Flask, g, session, send_file
from translations import t

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
MASSSAVE_URL                  = "https://www.masssave.com/community-first/lawrence"
UNIT_COUNT_CONFIRM_MULTIPLIER = 2

# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

app.config["ADMIN_PASSWORD"]                = os.environ.get("ADMIN_PASSWORD", "leapadmin2026")
app.config["MASSSAVE_URL"]                  = MASSSAVE_URL
app.config["UNIT_COUNT_CONFIRM_MULTIPLIER"] = UNIT_COUNT_CONFIRM_MULTIPLIER

# ------------------------------------------------------------------
# DB teardown
# ------------------------------------------------------------------
@app.teardown_appcontext
def close_dbs(exc):
    for attr in list(vars(g)):
        if attr.startswith("_db_"):
            getattr(g, attr).close()

# ------------------------------------------------------------------
# Schema — run once at startup (safe, never drops data)
# ------------------------------------------------------------------
from schema import ensure_schema
_schema_ready = False

@app.before_request
def startup_schema():
    global _schema_ready
    if not _schema_ready:
        ensure_schema()
        _schema_ready = True

# ------------------------------------------------------------------
# Template globals
# ------------------------------------------------------------------
from helpers import get_lang

@app.context_processor
def inject_globals():
    lang = get_lang()
    return {
        "t":    lambda key: t(key, lang),
        "lang": lang,
        "now":  datetime.now(timezone.utc),
    }

# ------------------------------------------------------------------
# Register blueprints
# ------------------------------------------------------------------
from routes.public import public
from routes.admin  import admin

app.register_blueprint(public)
app.register_blueprint(admin)

# ------------------------------------------------------------------
# TEMPORARY — DB dump download route
# PURPOSE: One-time download of hosted upinmgmt.sqlite as SQL dump
#          so local machine can be reseeded from Render (master).
# REMOVE THIS ROUTE AND THE send_file IMPORT after download is done.
# ------------------------------------------------------------------
@app.route('/admin/download-db-dump')
def download_db_dump():
    dump_path = '/data/upin_dump.sql'
    if not os.path.exists(dump_path):
        return "Dump file not found. Run the dump script in Render shell first.", 404
    return send_file(dump_path,
                     as_attachment=True,
                     download_name='upin_dump.sql',
                     mimetype='text/plain')

# ------------------------------------------------------------------
# Dev entrypoint
# ------------------------------------------------------------------
if __name__ == "__main__":
    from schema import init_schema
    init_schema()
    app.run(debug=True, port=5000)
