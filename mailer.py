"""mailer.py -- outbound email for the LEAP portal.

Wraps the SendGrid v3 /mail/send API over urllib (no SDK dep). Used to
fire automated First Touch confirmation emails after a successful
registration so the resident isn't left feeling the City received
nothing back from them. Per UX Roadmap Area 2 (Engagement & Retention).

If MAILER_API_KEY is unset, send_email() runs in *print mode* -- the
email body is written to stdout instead of sent. That keeps local dev,
CI, and any environment without configured credentials free of real
mail traffic. Render adds the secret via env, so production sends and
local dev doesn't.

Env vars:
  MAILER_API_KEY        SendGrid API key, "SG.xxx..." format. Empty = print mode.
  MAILER_FROM_ADDRESS   Verified-sender email, e.g. "leap@cityoflawrence.com".
  MAILER_FROM_NAME      Optional display name, defaults to "City of Lawrence".

The async wrapper spawns a daemon thread so the response isn't blocked
on send. Failed sends invoke an optional callback the caller can use to
log the failure (typically into outreach_log so the Advocate sees the
miss and can follow up manually).
"""

import json
import os
import sys
import threading
import urllib.error
import urllib.request


SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
DEFAULT_TIMEOUT = 5  # seconds


class MailerResult:
    """ok=True on success, otherwise reason carries a short failure tag."""
    __slots__ = ("ok", "reason")

    def __init__(self, ok: bool, reason: str = ""):
        self.ok = ok
        self.reason = reason

    def __repr__(self) -> str:
        return f"MailerResult(ok={self.ok}, reason={self.reason!r})"


def send_email(to_addr: str, subject: str, body_text: str,
               body_html=None, timeout: float = DEFAULT_TIMEOUT) -> MailerResult:
    """Synchronously send a transactional email.

    Returns MailerResult(ok=True) on a 2xx response or in print mode.
    For non-blocking use, prefer send_email_async().
    """
    api_key   = (os.environ.get("MAILER_API_KEY") or "").strip()
    from_addr = (os.environ.get("MAILER_FROM_ADDRESS") or "").strip()
    from_name = (os.environ.get("MAILER_FROM_NAME") or "City of Lawrence").strip()

    if not to_addr or not subject or not body_text:
        return MailerResult(False, "missing required field")

    # Print mode -- credentials not set, so dump the email to stdout
    # instead of sending. Lets the funnel work end-to-end without
    # real SendGrid traffic during local dev or in test environments.
    if not api_key or not from_addr:
        print("[mailer:print-mode] -------- begin email --------", flush=True)
        print(f"[mailer:print-mode] To:      {to_addr}", flush=True)
        print(f"[mailer:print-mode] Subject: {subject}", flush=True)
        print("[mailer:print-mode] Body:", flush=True)
        for line in body_text.splitlines():
            print(f"[mailer:print-mode]   {line}", flush=True)
        print("[mailer:print-mode] -------- end email --------", flush=True)
        return MailerResult(True, "print-mode")

    payload = {
        "personalizations": [{"to": [{"email": to_addr}]}],
        "from":    {"email": from_addr, "name": from_name},
        "subject": subject,
        "content": [{"type": "text/plain", "value": body_text}],
    }
    if body_html:
        payload["content"].append({"type": "text/html", "value": body_html})

    req = urllib.request.Request(
        SENDGRID_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # SendGrid returns 202 Accepted on success.
            if 200 <= resp.status < 300:
                return MailerResult(True, "")
            return MailerResult(False, f"http {resp.status}")
    except urllib.error.HTTPError as e:
        # 4xx/5xx come through here with .code and .reason populated.
        return MailerResult(False, f"http {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return MailerResult(False, f"network: {e.reason}")
    except Exception as e:
        return MailerResult(False, f"unexpected: {type(e).__name__}: {e}")


def send_email_async(to_addr: str, subject: str, body_text: str,
                     body_html=None, on_failure=None,
                     timeout: float = DEFAULT_TIMEOUT) -> None:
    """Fire-and-forget wrapper around send_email().

    Returns immediately; the actual send runs in a daemon thread so the
    HTTP response from the route isn't blocked. on_failure is called
    from inside the thread with the MailerResult on non-success, so the
    caller can log the miss (typically by writing an outreach_log row).
    The callback runs outside any Flask request context, so it must
    open its own DB connection -- it cannot use g.upin_db().
    """
    def _run():
        result = send_email(to_addr, subject, body_text, body_html, timeout)
        if not result.ok:
            print(f"[mailer:async] send failed for {to_addr}: {result.reason}",
                  file=sys.stderr, flush=True)
            if on_failure is not None:
                try:
                    on_failure(result)
                except Exception as e:
                    # Never let a failure-callback bug crash the worker thread.
                    print(f"[mailer:async] on_failure callback raised: {e}",
                          file=sys.stderr, flush=True)

    threading.Thread(target=_run, daemon=True).start()
