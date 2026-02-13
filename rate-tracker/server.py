"""
Movement Rate Tracker — Cloud Run Backend
Serves the dashboard, provides rate API, handles daily scheduled updates,
reads Outlook Rate Watch emails via Microsoft Graph API,
and sends email notifications to Brad Overlin.
"""

import os
import re
import json
import smtplib
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, send_from_directory, request, redirect

app = Flask(__name__, static_folder='static')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('rate-tracker')

# ---- CONFIGURATION ----
PORT = int(os.environ.get('PORT', 8080))

# Brad's notification email (set via environment variable)
BRAD_EMAIL = os.environ.get('BRAD_EMAIL', 'brad.overlin@movement.com')
NOTIFY_FROM = os.environ.get('NOTIFY_FROM', 'clair@movement-rate-tracker.com')

# SMTP config (Gmail app password or SendGrid)
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

# Phil gets a copy
PHIL_EMAIL = os.environ.get('PHIL_EMAIL', 'phil.hills@movement.com')

# ---- OUTLOOK RATE WATCH CONFIG (GCP-only: Playwright + GCS) ----
# Browser session cookies stored in GCS for persistence across cold starts
# One-time Okta login with push MFA, then fully autonomous
SERVICE_URL = os.environ.get('SERVICE_URL', 'https://rate-tracker-511662304947.us-west1.run.app')
GCS_BUCKET = os.environ.get('GCS_SESSION_BUCKET', 'rate-tracker-sessions')
OKTA_EMAIL = os.environ.get('OKTA_EMAIL', '')
OKTA_PASSWORD = os.environ.get('OKTA_PASSWORD', '')  # stored securely via Secret Manager
RATE_WATCH_FOLDER = os.environ.get('RATE_WATCH_FOLDER', 'Rate Watch')
OUTLOOK_URL = 'https://outlook.office.com/mail/'
MOVEMENT_OKTA_URL = 'https://movement.okta.com/app/UserHome?session_hint=AUTHENTICATED'
SALESFORCE_URL = 'https://movement.lightning.force.com/'
SESSION_DIR = '/tmp/outlook_session'
SESSION_READY = False  # Set to True after successful login

# ---- PIPELINE DATA (from MORE CRM audit 2/12/2026) ----
PIPELINE = [
    {"name": "Megan Carter", "stage": "Funded", "loanNum": "4342859", "property": "9213 Ash Ave SE, Snoqualmie WA", "loanAmount": 1114750, "rate": 6.500, "program": "Jumbo", "closingDate": "6/20/2025", "creditScore": 808, "buyerAgent": "Barb Pexa"},
    {"name": "Chelsey Milton", "stage": "Application", "loanNum": "3010572614", "property": "TBD", "loanAmount": 546025, "rate": 6.750, "program": "Conventional", "closingDate": "3/9/2026", "creditScore": 796, "buyerAgent": ""},
    {"name": "Anuj Mittal", "stage": "Funded", "loanNum": "3010526", "property": "3493 NE Harrison St", "loanAmount": 850000, "rate": 6.875, "program": "Jumbo", "closingDate": "11/12/2025", "creditScore": None, "buyerAgent": "Manu Vij"},
    {"name": "JIYEON PARK", "stage": "Funded", "loanNum": "3010542", "property": "13910 123rd Ave NE", "loanAmount": 720000, "rate": 6.625, "program": "Jumbo", "closingDate": "12/1/2025", "creditScore": None, "buyerAgent": "Emma Park"},
    {"name": "Cooper White", "stage": "Application", "loanNum": "3010554", "property": "TBD", "loanAmount": 480000, "rate": 6.500, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": "Derek Sarr"},
    {"name": "john thang", "stage": "Application", "loanNum": "4214710", "property": "TBD", "loanAmount": 350000, "rate": 6.875, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": "lisa nguyen"},
    {"name": "Jared Larsen", "stage": "Funded", "loanNum": "4073624", "property": "18501 SE Newport Wy", "loanAmount": 600000, "rate": 7.125, "program": "Conventional", "closingDate": "9/26/2023", "creditScore": None, "buyerAgent": "Karen Cor"},
    {"name": "Matthew Simon", "stage": "Application", "loanNum": "", "property": "1156 NW 58th St", "loanAmount": 425000, "rate": 6.750, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": ""},
    {"name": "Chris Candelario", "stage": "Application", "loanNum": "4379189", "property": "TBD", "loanAmount": 390000, "rate": 6.625, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": "Barb Pexa"},
    {"name": "Faezeh Amjadi", "stage": "Application", "loanNum": "4421329", "property": "TBD", "loanAmount": 375000, "rate": 6.500, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": ""},
    {"name": "Stanley Gene", "stage": "Funded", "loanNum": "30105361", "property": "1352 Brewster Dr", "loanAmount": 550000, "rate": 6.750, "program": "Conventional", "closingDate": "2/11/2026", "creditScore": None, "buyerAgent": "Kelly O'Go"},
    {"name": "Samantha Sim", "stage": "Funded", "loanNum": "3010535", "property": "206 1st Ave E", "loanAmount": 415200, "rate": 6.875, "program": "Conventional", "closingDate": "12/4/2025", "creditScore": None, "buyerAgent": "Makenna K"},
    {"name": "Michael Lentz", "stage": "Funded", "loanNum": "3010536", "property": "10605 SE 30th St", "loanAmount": 520000, "rate": 6.625, "program": "Conventional", "closingDate": "12/12/2025", "creditScore": None, "buyerAgent": "Barb Pexa"},
    {"name": "catherine Jin", "stage": "Funded", "loanNum": "4124925", "property": "3633 Beach Dr", "loanAmount": 750000, "rate": 7.250, "program": "Jumbo", "closingDate": "1/22/2024", "creditScore": None, "buyerAgent": "Yao Lu"},
    {"name": "Catherine Jin", "stage": "Lost", "loanNum": "", "property": "3633 Beach Dr", "loanAmount": 0, "rate": None, "program": "Conventional", "closingDate": None, "creditScore": None, "buyerAgent": ""},
]

# ---- CURRENT RATES (Optimal Blue national avg — updated daily by scheduler) ----
CURRENT_RATES = {
    "conventional_30": 6.048,
    "jumbo_30": 6.361,
    "fha_30": 5.956,
    "va_30": 5.690,
    "last_updated": datetime.now(timezone.utc).isoformat()
}


# ---- STATIC FILE SERVING ----
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'rate-tracker.html')


@app.route('/src/<path:filename>')
def serve_src(filename):
    return send_from_directory(os.path.join(app.static_folder, 'src'), filename)


# ---- API ENDPOINTS ----
@app.route('/api/rates', methods=['GET'])
def get_rates():
    """Return current market rates."""
    return jsonify(CURRENT_RATES)


@app.route('/api/rates', methods=['POST'])
def update_rates():
    """Manually update rates (admin endpoint)."""
    data = request.get_json()
    if data:
        for key in ['conventional_30', 'jumbo_30', 'fha_30', 'va_30']:
            if key in data:
                CURRENT_RATES[key] = float(data[key])
        CURRENT_RATES['last_updated'] = datetime.now(timezone.utc).isoformat()
    return jsonify({"status": "ok", "rates": CURRENT_RATES})


@app.route('/api/pipeline', methods=['GET'])
def get_pipeline():
    """Return the full pipeline with refi analysis."""
    analysis = analyze_pipeline(CURRENT_RATES)
    return jsonify(analysis)


@app.route('/api/trigger-daily', methods=['POST'])
def trigger_daily():
    """
    Called by Cloud Scheduler every morning at 7 AM PT.
    1. Fetches latest rates from Outlook Rate Watch folder (via Graph API)
    2. Analyzes pipeline for refi opportunities
    3. Sends email notification to Brad
    4. Auto-creates campaign from refi-ready pipeline
    5. Advances active campaign cadences
    """
    logger.info("🔔 Daily trigger fired at %s", datetime.now(timezone.utc).isoformat())

    # Step 1: Try to fetch rates from Outlook via headless browser
    outlook_result = None
    try:
        _load_session_from_gcs()
        email_data = _run_outlook_browser()
        if email_data:
            rates = _parse_rates_from_text(email_data['text'])
            if rates:
                for key, value in rates.items():
                    CURRENT_RATES[key] = value
                CURRENT_RATES['source'] = 'outlook_rate_watch'
                CURRENT_RATES['source_email'] = email_data.get('subject', '')
                outlook_result = {"status": "updated", "rates_found": len(rates)}
                logger.info("✅ Rates updated from Outlook: %s", json.dumps(rates))
            else:
                outlook_result = {"status": "parse_error"}
        else:
            outlook_result = {"status": "no_session"}
            logger.info("📧 Outlook session not available — using existing rates")
    except Exception as e:
        outlook_result = {"status": "error", "message": str(e)}
        logger.error("❌ Outlook rate fetch failed: %s", e)

    CURRENT_RATES['last_updated'] = datetime.now(timezone.utc).isoformat()

    # Step 2: Analyze pipeline
    analysis = analyze_pipeline(CURRENT_RATES)

    # Step 3: Send notification to Brad
    notification_sent = send_daily_notification(analysis)

    # Step 4: Auto-create campaign if refi opportunities exist
    campaign_created = None
    if analysis['refi_ready_count'] > 0:
        with app.test_request_context(json={"min_score": 50, "include_watch": True}):
            resp = create_campaign_from_pipeline()
            if hasattr(resp, 'get_json'):
                campaign_created = resp.get_json()
            else:
                campaign_created = resp[0].get_json() if isinstance(resp, tuple) else None

    # Step 5: Advance cadences on all active campaigns
    cadence_results = []
    for cid, campaign in ACTIVE_CAMPAIGNS.items():
        if campaign["status"] == "active":
            with app.test_request_context():
                resp = execute_cadence_step(cid)
                if hasattr(resp, 'get_json'):
                    cadence_results.append(resp.get_json())

    return jsonify({
        "status": "ok",
        "timestamp": CURRENT_RATES['last_updated'],
        "outlook_rates": outlook_result,
        "refi_ready_count": analysis['refi_ready_count'],
        "total_monthly_savings": analysis['total_monthly_savings'],
        "notification_sent": notification_sent,
        "campaign_created": campaign_created,
        "cadences_advanced": len(cadence_results)
    })


@app.route('/api/health', methods=['GET'])
def health():
    session_exists = os.path.exists(SESSION_DIR) and bool(os.listdir(SESSION_DIR)) if os.path.exists(SESSION_DIR) else False
    return jsonify({
        "status": "healthy",
        "service": "rate-tracker",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "outlook_integration": "session_saved" if session_exists else "needs_setup",
        "setup_url": f"{SERVICE_URL}/auth/setup" if not session_exists else None
    })


# ============================================================
# OUTLOOK RATE WATCH — PLAYWRIGHT BROWSER AGENT (GCP-ONLY)
# ============================================================
# Flow:
#   1. Set OKTA_EMAIL + OKTA_PASSWORD as Cloud Run env vars (via Secret Manager)
#   2. Visit /auth/connect once → Playwright opens Outlook → Okta login
#      → push MFA approved on phone → session saved to GCS
#   3. Every morning: Cloud Scheduler calls /api/fetch-outlook-rates
#      → loads session from GCS → headless browser opens Outlook
#      → reads Rate Watch folder → parses Optimal Blue rates
#      → updates CURRENT_RATES → pipeline analysis runs
# ============================================================

import shutil
import tarfile
import io


def _save_session_to_gcs():
    """Save browser session directory to GCS for persistence across cold starts."""
    try:
        from google.cloud import storage as gcs
        client = gcs.Client()
        bucket = client.bucket(GCS_BUCKET)

        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode='w:gz') as tar:
            tar.add(SESSION_DIR, arcname='session')
        buf.seek(0)

        blob = bucket.blob('outlook_session.tar.gz')
        blob.upload_from_file(buf, content_type='application/gzip')
        logger.info("💾 Session saved to GCS: gs://%s/outlook_session.tar.gz", GCS_BUCKET)
        return True
    except Exception as e:
        logger.error("❌ Failed to save session to GCS: %s", e)
        return False


def _load_session_from_gcs():
    """Load browser session from GCS bucket."""
    try:
        from google.cloud import storage as gcs
        client = gcs.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob('outlook_session.tar.gz')

        if not blob.exists():
            logger.info("📦 No saved session in GCS")
            return False

        buf = io.BytesIO()
        blob.download_to_file(buf)
        buf.seek(0)

        if os.path.exists(SESSION_DIR):
            shutil.rmtree(SESSION_DIR)

        with tarfile.open(fileobj=buf, mode='r:gz') as tar:
            tar.extractall('/tmp')

        extracted = '/tmp/session'
        if os.path.exists(extracted) and extracted != SESSION_DIR:
            if os.path.exists(SESSION_DIR):
                shutil.rmtree(SESSION_DIR)
            shutil.move(extracted, SESSION_DIR)

        logger.info("📥 Session loaded from GCS")
        return True
    except Exception as e:
        logger.error("❌ Failed to load session from GCS: %s", e)
        return False


def _parse_rates_from_text(text):
    """Parse Optimal Blue rate data from email text."""
    rates = {}
    patterns = [
        (r'30-YR\.?\s*CONFORMING\s*[\n\r\s]*([\d]+\.[\d]+)', 'conventional_30'),
        (r'30-YR\.?\s*JUMBO\s*[\n\r\s]*([\d]+\.[\d]+)', 'jumbo_30'),
        (r'30-YR\.?\s*FHA\s*[\n\r\s]*([\d]+\.[\d]+)', 'fha_30'),
        (r'30-YR\.?\s*VA\s*[\n\r\s]*([\d]+\.[\d]+)', 'va_30'),
    ]
    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            rates[key] = float(match.group(1))
            logger.info("  ✅ %s: %s%%", key, rates[key])
    return rates


def _run_outlook_browser():
    """
    Headless Chromium → Outlook → Rate Watch folder → extract latest email.
    Uses saved session cookies. Handles Okta login if needed.
    Returns dict with email text or None.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("❌ Playwright not installed")
        return None

    import time
    logger.info("🌐 Launching headless browser...")
    os.makedirs(SESSION_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            viewport={'width': 1400, 'height': 900},
            locale='en-US',
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            # Navigate to Outlook
            page.goto(OUTLOOK_URL, wait_until='domcontentloaded', timeout=45000)
            time.sleep(3)
            current_url = page.url

            # Handle Okta login if redirected
            if 'okta.com' in current_url or 'login.microsoftonline' in current_url:
                logger.info("🔐 Okta login required...")
                if not OKTA_EMAIL or not OKTA_PASSWORD:
                    logger.error("❌ OKTA_EMAIL / OKTA_PASSWORD not set")
                    browser.close()
                    return None

                # Enter email
                try:
                    ef = page.locator('input[name="identifier"], input[name="username"], input[type="email"]')
                    if ef.first.is_visible(timeout=5000):
                        ef.first.fill(OKTA_EMAIL)
                        page.locator('input[type="submit"], button[type="submit"]').first.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Enter password
                try:
                    pf = page.locator('input[type="password"]')
                    if pf.first.is_visible(timeout=5000):
                        pf.first.fill(OKTA_PASSWORD)
                        page.locator('input[type="submit"], button[type="submit"]').first.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Handle MFA push
                logger.info("📱 Sending Okta Verify push...")
                for sel in ['a:text("Send Push")', 'button:text("Send Push")', '[data-se="okta_verify-push"]']:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            logger.info("   ✅ Push sent — approve on phone!")
                            break
                    except Exception:
                        continue

                # Wait for MFA approval (2 min)
                try:
                    page.wait_for_url(
                        lambda u: 'okta.com/login' not in u and 'okta.com/signin' not in u,
                        timeout=120000
                    )
                    logger.info("   ✅ MFA approved!")
                except Exception:
                    logger.error("   ❌ MFA timeout")
                    browser.close()
                    return None

                time.sleep(5)

            # Verify we're in Outlook
            if 'outlook.office' not in page.url and 'outlook.live' not in page.url:
                logger.error("❌ Not in Outlook. URL: %s", page.url)
                browser.close()
                return None

            logger.info("✅ In Outlook — finding Rate Watch folder...")
            time.sleep(2)

            # Find Rate Watch folder
            folder_found = False
            for sel in [f'[title="{RATE_WATCH_FOLDER}"]', f'[aria-label*="{RATE_WATCH_FOLDER}"]',
                        f'span:text("{RATE_WATCH_FOLDER}")']:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        folder_found = True
                        logger.info("📁 Clicked '%s'", RATE_WATCH_FOLDER)
                        break
                except Exception:
                    continue

            if not folder_found:
                # Try expanding Folders section
                try:
                    page.locator('span:text("Folders"), [aria-label="Folders"]').first.click()
                    time.sleep(1)
                    for sel in [f'[title="{RATE_WATCH_FOLDER}"]', f'span:text("{RATE_WATCH_FOLDER}")']:
                        try:
                            el = page.locator(sel).first
                            if el.is_visible(timeout=3000):
                                el.click()
                                folder_found = True
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            if not folder_found:
                logger.error("❌ '%s' folder not found", RATE_WATCH_FOLDER)
                browser.close()
                return None

            time.sleep(3)

            # Click first email
            subject_text = 'Rate Watch'
            for sel in ['[role="option"]:first-child', '[role="listbox"] [role="option"] >> nth=0']:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        subject_text = el.inner_text()[:100]
                        el.click()
                        logger.info("📩 Opened: %s...", subject_text[:60])
                        break
                except Exception:
                    continue

            time.sleep(3)

            # Extract email body
            for sel in ['[aria-label="Message body"]', '[role="document"]', 'div.allowTextSelection']:
                try:
                    body = page.locator(sel).first
                    if body.is_visible(timeout=3000):
                        text = body.inner_text()
                        if len(text) > 50:
                            logger.info("✅ Extracted %d chars", len(text))
                            browser.close()
                            _save_session_to_gcs()
                            return {'subject': subject_text, 'text': text,
                                    'received': datetime.now(timezone.utc).isoformat(),
                                    'from': 'rate-watch'}
                except Exception:
                    continue

            # Fallback
            text = page.locator('[role="main"]').inner_text()
            browser.close()
            _save_session_to_gcs()
            return {'subject': subject_text, 'text': text,
                    'received': datetime.now(timezone.utc).isoformat(), 'from': 'rate-watch'}

        except Exception as e:
            logger.error("❌ Browser error: %s", e)
            try:
                browser.close()
            except Exception:
                pass
            return None


@app.route('/auth/setup')
def auth_setup():
    """Setup page with instructions for connecting Outlook."""
    return f"""
    <html>
    <body style="font-family:sans-serif;padding:40px;background:#1a1a2e;color:#e0e0e0;max-width:700px;margin:0 auto">
        <h1 style="color:#8b0000">📧 Outlook Rate Watch Setup</h1>
        <p>Connect your Outlook to auto-read <strong>{RATE_WATCH_FOLDER}</strong> every morning.</p>
        <div style="background:#0d1117;padding:20px;border-radius:8px;margin:20px 0;border:1px solid #333">
            <h3 style="color:#00c853">How It Works (GCP Only)</h3>
            <ol style="line-height:2">
                <li>Set OKTA_EMAIL + OKTA_PASSWORD as Cloud Run env vars</li>
                <li>Click "Connect" → headless browser logs into Outlook via Okta</li>
                <li>Approve the <strong>push notification</strong> on your phone (one time)</li>
                <li>Session cookies saved to GCS bucket — agent runs autonomously</li>
            </ol>
        </div>
        <div style="background:#0d1117;padding:20px;border-radius:8px;margin:20px 0;border:1px solid #333">
            <h3 style="color:#ffd700">Environment Variables</h3>
            <code style="color:#8b8b8b;display:block;padding:10px;background:#000;border-radius:4px">
OKTA_EMAIL={OKTA_EMAIL or 'your.email@movement.com'}<br>
OKTA_PASSWORD=**** (use Secret Manager)<br>
GCS_SESSION_BUCKET={GCS_BUCKET}
            </code>
        </div>
        <a href="/auth/connect" style="display:inline-block;padding:12px 32px;background:#8b0000;color:white;
            text-decoration:none;border-radius:6px;font-weight:bold;font-size:16px">
            🔐 Connect Outlook
        </a>
    </body></html>
    """


@app.route('/auth/connect')
def auth_connect():
    """Trigger headless browser login to Outlook."""
    if not OKTA_EMAIL:
        return jsonify({"error": "Set OKTA_EMAIL env var first"}), 400

    _load_session_from_gcs()
    email_data = _run_outlook_browser()

    if email_data:
        return f"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:#e0e0e0">
            <h1 style="color:#00c853">✅ Outlook Connected!</h1>
            <p>Rate Watch folder will be read every morning at 7 AM PT.</p>
            <p><a href="/" style="color:#8b0000;font-weight:bold">← Dashboard</a></p>
        </body></html>
        """
    else:
        return f"""
        <html><body style="font-family:sans-serif;text-align:center;padding:60px;background:#1a1a2e;color:#e0e0e0">
            <h1 style="color:#ff5252">⚠️ Connection Failed</h1>
            <p>Check OKTA_EMAIL/PASSWORD and approve push within 2 minutes.</p>
            <p><a href="/auth/connect" style="color:#8b0000">Try Again</a></p>
        </body></html>
        """, 200


@app.route('/auth/status')
def auth_status():
    """Auth status for Outlook integration."""
    session_exists = os.path.exists(SESSION_DIR) and bool(os.listdir(SESSION_DIR)) if os.path.exists(SESSION_DIR) else False
    return jsonify({
        "outlook_connected": session_exists,
        "okta_email": OKTA_EMAIL or None,
        "gcs_bucket": GCS_BUCKET,
        "rate_watch_folder": RATE_WATCH_FOLDER,
        "setup_url": f"{SERVICE_URL}/auth/setup" if not session_exists else None
    })


@app.route('/api/fetch-outlook-rates', methods=['POST'])
def fetch_outlook_rates():
    """
    Cloud Scheduler endpoint: headless browser → Outlook → Rate Watch →
    parse Optimal Blue rates → update CURRENT_RATES. Fully autonomous.
    """
    logger.info("📧 Fetching rates from Outlook Rate Watch folder...")

    _load_session_from_gcs()
    email_data = _run_outlook_browser()

    if not email_data:
        return jsonify({
            "status": "session_expired",
            "message": "Could not access Outlook. Visit /auth/setup to reconnect."
        }), 200

    rates = _parse_rates_from_text(email_data['text'])
    if not rates:
        return jsonify({
            "status": "parse_error",
            "email_subject": email_data.get('subject', ''),
            "email_text_preview": email_data['text'][:500]
        }), 200

    for key, value in rates.items():
        CURRENT_RATES[key] = value
    CURRENT_RATES['last_updated'] = datetime.now(timezone.utc).isoformat()
    CURRENT_RATES['source'] = 'outlook_rate_watch'
    CURRENT_RATES['source_email'] = email_data.get('subject', '')
    logger.info("🎉 Rates updated from Outlook: %s", json.dumps(rates))

    return jsonify({
        "status": "updated",
        "rates": CURRENT_RATES,
        "source": {"email_subject": email_data.get('subject', ''),
                    "received": email_data.get('received', '')}
    })




# ============================================================
# CRM BROWSER AGENT — SEND SMS VIA SALESFORCE VONAGE WIDGET
# ============================================================
# Uses same Okta session saved to GCS. Navigates Salesforce Lightning,
# searches for a contact by name, and sends SMS via the built-in
# Vonage SMS widget on the contact record.
# ============================================================

def _run_crm_send_sms(contact_name, message):
    """
    Headless Chromium → Salesforce → search contact → send SMS via Vonage widget.
    Uses saved Okta session cookies from GCS.
    Returns dict with status or None on failure.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("❌ Playwright not installed")
        return None

    import time
    logger.info("🌐 Launching browser for CRM SMS to '%s'...", contact_name)
    os.makedirs(SESSION_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True,
            viewport={'width': 1400, 'height': 900},
            locale='en-US',
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            # Navigate to Salesforce
            logger.info("📊 Navigating to Salesforce...")
            page.goto(SALESFORCE_URL, wait_until='domcontentloaded', timeout=45000)
            time.sleep(3)

            # Handle Okta login if redirected
            if 'okta.com' in page.url or 'login.microsoftonline' in page.url:
                logger.info("🔐 Okta login required...")
                if not OKTA_EMAIL or not OKTA_PASSWORD:
                    logger.error("❌ OKTA_EMAIL / OKTA_PASSWORD not set")
                    browser.close()
                    return {'status': 'error', 'message': 'Okta credentials not configured'}

                # Enter email
                try:
                    ef = page.locator('input[name="identifier"], input[name="username"], input[type="email"]')
                    if ef.first.is_visible(timeout=5000):
                        ef.first.fill(OKTA_EMAIL)
                        page.locator('input[type="submit"], button[type="submit"]').first.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Enter password
                try:
                    pf = page.locator('input[type="password"]')
                    if pf.first.is_visible(timeout=5000):
                        pf.first.fill(OKTA_PASSWORD)
                        page.locator('input[type="submit"], button[type="submit"]').first.click()
                        time.sleep(2)
                except Exception:
                    pass

                # Handle MFA push
                logger.info("📱 Sending Okta Verify push...")
                for sel in ['a:text("Send Push")', 'button:text("Send Push")', '[data-se="okta_verify-push"]']:
                    try:
                        btn = page.locator(sel).first
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            logger.info("   ✅ Push sent — approve on phone!")
                            break
                    except Exception:
                        continue

                # Wait for MFA approval
                try:
                    page.wait_for_url(
                        lambda u: 'okta.com/login' not in u and 'okta.com/signin' not in u,
                        timeout=120000
                    )
                    logger.info("   ✅ MFA approved!")
                except Exception:
                    logger.error("   ❌ MFA timeout")
                    browser.close()
                    return {'status': 'error', 'message': 'MFA approval timeout'}

                time.sleep(5)

            # Wait for Salesforce to load
            try:
                page.wait_for_selector('div.slds-global-header, one-app-nav-bar', timeout=30000)
                logger.info("✅ Salesforce loaded")
            except Exception:
                logger.warning("⚠️  Salesforce header not detected, continuing anyway...")

            time.sleep(2)

            # Use Global Search to find contact
            logger.info("🔍 Searching for contact: %s", contact_name)

            # Click the global search box
            search_selectors = [
                'button[aria-label="Search"]',
                'input[placeholder*="Search"]',
                'div.slds-global-header input',
                '[data-aura-class="forceSearchDesktopHeader"] input',
                'button.slds-button:has-text("Search")',
            ]

            search_clicked = False
            for sel in search_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        search_clicked = True
                        logger.info("   Clicked search")
                        break
                except Exception:
                    continue

            if not search_clicked:
                logger.error("❌ Could not find search bar")
                browser.close()
                return {'status': 'error', 'message': 'Search bar not found'}

            time.sleep(1)

            # Type the contact name
            search_input_selectors = [
                'input[placeholder*="Search"]',
                'input[type="search"]',
                'input.slds-input[role="combobox"]',
                'input[aria-label*="Search"]',
            ]

            for sel in search_input_selectors:
                try:
                    inp = page.locator(sel).first
                    if inp.is_visible(timeout=3000):
                        inp.fill(contact_name)
                        time.sleep(1)
                        inp.press('Enter')
                        logger.info("   Searching: %s", contact_name)
                        break
                except Exception:
                    continue

            time.sleep(4)

            # Click the contact from search results
            contact_selectors = [
                f'a:text("{contact_name}")',
                f'a[title*="{contact_name}"]',
                f'span:text("{contact_name}")',
                'table.slds-table tbody tr:first-child a',
            ]

            contact_clicked = False
            for sel in contact_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=5000):
                        el.click()
                        contact_clicked = True
                        logger.info("   ✅ Opened contact: %s", contact_name)
                        break
                except Exception:
                    continue

            if not contact_clicked:
                logger.error("❌ Contact '%s' not found in search results", contact_name)
                browser.close()
                return {'status': 'error', 'message': f'Contact {contact_name} not found'}

            time.sleep(4)

            # Find and click the SMS/Vonage button on the contact record
            logger.info("📱 Looking for SMS/Vonage widget...")

            sms_selectors = [
                'button:text("Send SMS")',
                'button:text("SMS")',
                'button:text("Text")',
                'button:text("Send Text")',
                'a:text("Send SMS")',
                'a:text("SMS")',
                '[title*="SMS"]',
                '[title*="Text Message"]',
                'button:text("Vonage")',
                # Salesforce Quick Actions
                'a[title="SendSMS"]',
                'a[title="Send_SMS"]',
                'a[title="Text"]',
                'runtime_platform_actions-action-renderer:has-text("SMS")',
                'runtime_platform_actions-action-renderer:has-text("Text")',
            ]

            sms_clicked = False
            for sel in sms_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        sms_clicked = True
                        logger.info("   ✅ Clicked SMS action")
                        break
                except Exception:
                    continue

            if not sms_clicked:
                # Try the "More Actions" dropdown
                logger.info("   Trying 'More Actions' dropdown...")
                try:
                    more_btn = page.locator('button:text("More Actions"), a:text("more actions"), [title="More Actions"]').first
                    if more_btn.is_visible(timeout=3000):
                        more_btn.click()
                        time.sleep(1)
                        for sel in ['a:text("Send SMS")', 'a:text("SMS")', 'a:text("Text")', 'li:text("SMS")', 'li:text("Text")']:
                            try:
                                el = page.locator(sel).first
                                if el.is_visible(timeout=2000):
                                    el.click()
                                    sms_clicked = True
                                    logger.info("   ✅ Found SMS in More Actions")
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass

            if not sms_clicked:
                # Screenshot for debugging
                logger.error("❌ Could not find SMS/Vonage button on contact record")
                page_text = page.locator('body').inner_text()[:500]
                browser.close()
                _save_session_to_gcs()
                return {'status': 'error', 'message': 'SMS button not found on contact',
                        'page_preview': page_text}

            time.sleep(3)

            # Type the message in the SMS dialog
            logger.info("✍️ Typing message...")
            msg_selectors = [
                'textarea[placeholder*="message"]',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="text"]',
                'textarea',
                'div[contenteditable="true"]',
                'input[placeholder*="message"]',
            ]

            msg_typed = False
            for sel in msg_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=5000):
                        el.fill(message)
                        msg_typed = True
                        logger.info("   ✅ Message typed")
                        break
                except Exception:
                    continue

            if not msg_typed:
                logger.error("❌ Could not find message input")
                browser.close()
                _save_session_to_gcs()
                return {'status': 'error', 'message': 'Message input field not found'}

            time.sleep(1)

            # Click Send
            send_selectors = [
                'button:text("Send")',
                'button[title="Send"]',
                'input[value="Send"]',
                'button:text("Send SMS")',
                'button:text("Send Message")',
            ]

            sent = False
            for sel in send_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=3000):
                        el.click()
                        sent = True
                        logger.info("   ✅ Message sent!")
                        break
                except Exception:
                    continue

            time.sleep(2)
            browser.close()
            _save_session_to_gcs()

            if sent:
                logger.info("🎉 SMS sent to %s via CRM Vonage", contact_name)
                return {'status': 'sent', 'contact': contact_name, 'message': message}
            else:
                return {'status': 'error', 'message': 'Could not click Send button'}

        except Exception as e:
            logger.error("❌ CRM SMS error: %s", e)
            try:
                browser.close()
            except Exception:
                pass
            return {'status': 'error', 'message': str(e)}


@app.route('/api/send-sms', methods=['POST'])
def send_sms_via_crm():
    """
    Send SMS through Salesforce CRM's built-in Vonage integration.
    Body: {"contact": "Phil Hills", "message": "Your rates are ready!"}
    Uses Playwright browser agent with saved Okta session.
    """
    data = request.get_json() or {}
    contact_name = data.get('contact', 'Phil Hills')
    message = data.get('message', f"📊 Rate Tracker Update: Today's rates — Conv {CURRENT_RATES.get('conventional_30', 'N/A')}%, Jumbo {CURRENT_RATES.get('jumbo_30', 'N/A')}%, FHA {CURRENT_RATES.get('fha_30', 'N/A')}%, VA {CURRENT_RATES.get('va_30', 'N/A')}%")

    logger.info("📱 SMS request: to=%s msg=%s", contact_name, message[:60])

    # Load session
    _load_session_from_gcs()

    result = _run_crm_send_sms(contact_name, message)

    if result and result.get('status') == 'sent':
        return jsonify(result)
    else:
        return jsonify(result or {'status': 'error', 'message': 'Unknown error'}), 200


# ---- VONAGE / SMS MAGIC / EMAIL CONFIG ----
VONAGE_API_KEY = os.environ.get('VONAGE_API_KEY', '')
VONAGE_API_SECRET = os.environ.get('VONAGE_API_SECRET', '')
VONAGE_APP_ID = os.environ.get('VONAGE_APP_ID', '')
VONAGE_FROM_NUMBER = os.environ.get('VONAGE_FROM_NUMBER', '')

SMSMAGIC_API_KEY = os.environ.get('SMSMAGIC_API_KEY', '')
SMSMAGIC_SENDER_ID = os.environ.get('SMSMAGIC_SENDER_ID', 'MovementMtg')

BRAD_PHONE = os.environ.get('BRAD_PHONE', '')
BRAD_FULL_NAME = 'Brad Overlin'
BRAD_NMLS = '987905'

# ---- ACTIVE CAMPAIGNS STORE ----
ACTIVE_CAMPAIGNS = {}

# ---- CADENCE DEFINITIONS ----
# Multi-channel outreach cadence for refi-ready borrowers
REFI_CADENCE = [
    {
        "day": 0,
        "channel": "email",
        "subject": "Great News About Your Mortgage Rate, {name}!",
        "body": (
            "Hi {name},\n\n"
            "I'm reaching out because market rates have dropped to {market_rate}% — "
            "that's {rate_delta}% below your current rate of {current_rate}%. "
            "On your ${loan_amount} loan, that could save you ${monthly_savings}/month.\n\n"
            "I'd love to walk you through your refinance options. "
            "Are you available for a quick 10-minute call this week?\n\n"
            "Best,\nBrad Overlin\nNMLS #{nmls}\nMovement Mortgage"
        )
    },
    {
        "day": 1,
        "channel": "sms",
        "message": (
            "Hi {name}, this is Brad from Movement Mortgage. "
            "Rates just dropped to {market_rate}% — you could save ${monthly_savings}/mo "
            "on your loan. Want me to run the numbers? Reply YES or call me anytime."
        )
    },
    {
        "day": 3,
        "channel": "vonage_call",
        "greeting": (
            "Hello {name}, this is a courtesy call from Brad Overlin at Movement Mortgage. "
            "I'm reaching out because current mortgage rates have dropped significantly below your existing rate. "
            "Based on your loan, you could be saving over ${monthly_savings} per month. "
            "I'd love to schedule a brief call to discuss your refinance options. "
            "Press 1 to connect with Brad now, or we'll follow up by email."
        )
    },
    {
        "day": 5,
        "channel": "sms",
        "message": (
            "Hi {name} — just following up. Rates are still favorable at {market_rate}%. "
            "Your potential savings: ${monthly_savings}/mo. "
            "I can send you a personalized rate quote — just reply GO. —Brad, Movement Mortgage"
        )
    },
    {
        "day": 7,
        "channel": "email",
        "subject": "Your Personalized Rate Analysis — {name}",
        "body": (
            "Hi {name},\n\n"
            "I wanted to follow up one more time with your personalized refinance analysis:\n\n"
            "  Current Rate: {current_rate}%\n"
            "  Today's Rate: {market_rate}%\n"
            "  Monthly Savings: ${monthly_savings}\n"
            "  Loan Amount: ${loan_amount}\n\n"
            "If you're interested, I can have everything prepped for a no-obligation consultation. "
            "Just reply to this email or call me directly.\n\n"
            "Brad Overlin | NMLS #{nmls}\n"
            "Movement Mortgage | Market Leader"
        )
    },
    {
        "day": 10,
        "channel": "vonage_call",
        "greeting": (
            "Hi {name}, this is a follow-up from Brad Overlin at Movement Mortgage. "
            "I wanted to check in one last time about the rate improvement opportunity on your mortgage. "
            "Rates have been moving and I want to make sure you don't miss this window. "
            "Press 1 to speak with Brad directly."
        )
    },
]


# ---- CAMPAIGN API ENDPOINTS ----
@app.route('/api/campaigns', methods=['GET'])
def list_campaigns():
    """List all active campaigns."""
    return jsonify({
        "campaigns": [
            {
                "id": cid,
                "name": c["name"],
                "created": c["created"],
                "status": c["status"],
                "total_leads": len(c["leads"]),
                "channels": list(set(step["channel"] for step in c.get("cadence", []))),
                "cadence_steps": len(c.get("cadence", []))
            }
            for cid, c in ACTIVE_CAMPAIGNS.items()
        ]
    })


@app.route('/api/campaigns/create-from-pipeline', methods=['POST'])
def create_campaign_from_pipeline():
    """
    Auto-create a campaign from current refi-ready pipeline.
    Filters funded loans with refi score >= threshold and enrolls them in the cadence.
    """
    data = request.get_json() or {}
    min_score = data.get('min_score', 50)  # Lower threshold to catch more prospects
    include_watch = data.get('include_watch', True)

    # Analyze current pipeline
    analysis = analyze_pipeline(CURRENT_RATES)

    # Filter eligible loans
    eligible = []
    for loan in analysis['loans']:
        if loan['stage'] != 'Funded':
            continue
        if loan['refiScore'] >= min_score or (include_watch and loan['refiScore'] >= 30):
            eligible.append(loan)

    if not eligible:
        return jsonify({"status": "no_eligible", "message": "No loans meet the refi threshold at current rates."}), 200

    # Create campaign
    campaign_id = f"refi-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    campaign = {
        "id": campaign_id,
        "name": f"Refi Campaign — {datetime.now().strftime('%b %d, %Y')}",
        "created": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "originator": BRAD_FULL_NAME,
        "leads": [],
        "cadence": REFI_CADENCE,
        "execution_log": []
    }

    for loan in sorted(eligible, key=lambda x: -x['refiScore']):
        lead = {
            "name": loan['name'],
            "loan_num": loan.get('loanNum', ''),
            "loan_amount": loan['loanAmount'],
            "current_rate": loan['rate'],
            "market_rate": loan['marketRate'],
            "rate_delta": round(loan['rate'] - loan['marketRate'], 3) if loan['rate'] else 0,
            "monthly_savings": loan['monthlySavings'],
            "refi_score": loan['refiScore'],
            "property": loan.get('property', ''),
            "program": loan.get('program', ''),
            "cadence_day": 0,
            "cadence_status": "enrolled",
            "last_touch": None,
            "responses": []
        }
        campaign["leads"].append(lead)

    ACTIVE_CAMPAIGNS[campaign_id] = campaign

    # Log creation
    logger.info("🎯 Campaign created: %s with %d leads", campaign_id, len(eligible))

    return jsonify({
        "status": "created",
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "total_leads": len(eligible),
        "leads": [
            {"name": l["name"], "score": l["refi_score"], "savings": l["monthly_savings"]}
            for l in campaign["leads"]
        ],
        "cadence_schedule": [
            {"day": s["day"], "channel": s["channel"]}
            for s in REFI_CADENCE
        ]
    })


@app.route('/api/campaigns/<campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get details of a specific campaign."""
    campaign = ACTIVE_CAMPAIGNS.get(campaign_id)
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404
    return jsonify(campaign)


@app.route('/api/campaigns/<campaign_id>/execute-step', methods=['POST'])
def execute_cadence_step(campaign_id):
    """
    Execute the next cadence step for all leads in a campaign.
    This is called by the daily scheduler or manually.
    """
    campaign = ACTIVE_CAMPAIGNS.get(campaign_id)
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404

    results = []
    for lead in campaign["leads"]:
        if lead["cadence_status"] in ("opted_out", "completed", "converted"):
            continue

        # Find the current cadence step
        current_day = lead["cadence_day"]
        step = None
        for s in campaign["cadence"]:
            if s["day"] == current_day:
                step = s
                break

        if not step:
            # No step for today, advance to next
            next_steps = [s for s in campaign["cadence"] if s["day"] > current_day]
            if next_steps:
                lead["cadence_day"] = next_steps[0]["day"]
            else:
                lead["cadence_status"] = "completed"
            continue

        # Template variables
        template_vars = {
            "name": lead["name"].split()[0],  # First name only
            "current_rate": lead["current_rate"],
            "market_rate": lead["market_rate"],
            "rate_delta": abs(lead["rate_delta"]),
            "monthly_savings": f"{lead['monthly_savings']:,.0f}",
            "loan_amount": f"{lead['loan_amount']:,.0f}",
            "nmls": BRAD_NMLS
        }

        # Execute based on channel
        result = {"lead": lead["name"], "channel": step["channel"], "day": current_day}

        if step["channel"] == "email":
            result["action"] = "send_email"
            result["subject"] = step["subject"].format(**template_vars)
            result["body_preview"] = step["body"].format(**template_vars)[:200] + "..."
            result["status"] = _send_cadence_email(
                lead["name"], lead.get("email", BRAD_EMAIL),
                step["subject"].format(**template_vars),
                step["body"].format(**template_vars)
            )

        elif step["channel"] == "sms":
            message = step["message"].format(**template_vars)
            result["action"] = "send_sms"
            result["message"] = message
            result["status"] = _send_sms_magic(lead.get("phone", ""), message)

        elif step["channel"] == "vonage_call":
            greeting = step["greeting"].format(**template_vars)
            result["action"] = "vonage_call"
            result["greeting_preview"] = greeting[:150] + "..."
            result["status"] = _initiate_vonage_call(lead.get("phone", ""), greeting)

        # Update lead state
        lead["last_touch"] = datetime.now(timezone.utc).isoformat()
        lead["responses"].append({
            "timestamp": lead["last_touch"],
            "channel": step["channel"],
            "day": current_day,
            "status": result["status"]
        })

        # Advance to next step
        next_steps = [s for s in campaign["cadence"] if s["day"] > current_day]
        if next_steps:
            lead["cadence_day"] = next_steps[0]["day"]
        else:
            lead["cadence_status"] = "completed"

        results.append(result)

    # Log execution
    campaign["execution_log"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results_count": len(results),
        "results": results
    })

    return jsonify({
        "status": "executed",
        "campaign_id": campaign_id,
        "steps_executed": len(results),
        "results": results
    })


@app.route('/api/campaigns/<campaign_id>/status', methods=['GET'])
def campaign_status(campaign_id):
    """Get campaign execution status and lead progress."""
    campaign = ACTIVE_CAMPAIGNS.get(campaign_id)
    if not campaign:
        return jsonify({"error": "Campaign not found"}), 404

    summary = {
        "enrolled": 0, "in_progress": 0, "completed": 0,
        "converted": 0, "opted_out": 0
    }
    for lead in campaign["leads"]:
        status = lead["cadence_status"]
        if status in summary:
            summary[status] += 1
        else:
            summary["in_progress"] += 1

    return jsonify({
        "campaign_id": campaign_id,
        "name": campaign["name"],
        "status": campaign["status"],
        "summary": summary,
        "leads": [
            {
                "name": l["name"],
                "score": l["refi_score"],
                "cadence_day": l["cadence_day"],
                "cadence_status": l["cadence_status"],
                "last_touch": l["last_touch"],
                "touches": len(l["responses"])
            }
            for l in campaign["leads"]
        ]
    })


# ---- CHANNEL EXECUTION FUNCTIONS ----
def _send_cadence_email(name, email, subject, body):
    """Send a cadence email to a borrower."""
    if not SMTP_USER or not SMTP_PASS:
        logger.info("📧 [DRY RUN] Email to %s <%s>: %s", name, email, subject)
        return "dry_run"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = NOTIFY_FROM
        msg['To'] = email
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(NOTIFY_FROM, [email], msg.as_string())

        logger.info("📧 Email sent to %s <%s>", name, email)
        return "sent"
    except Exception as e:
        logger.error("📧 Failed to email %s: %s", name, e)
        return f"error: {e}"


def _send_sms_magic(phone, message):
    """Send SMS via SMS Magic API."""
    if not SMSMAGIC_API_KEY or not phone:
        logger.info("💬 [DRY RUN] SMS to %s: %s", phone or "NO_PHONE", message[:80])
        return "dry_run"

    try:
        import urllib.request
        import urllib.parse

        payload = json.dumps({
            "senderid": SMSMAGIC_SENDER_ID,
            "to": phone,
            "message": message
        }).encode('utf-8')

        req = urllib.request.Request(
            "https://api.smsmagic.com/v1/messages",
            data=payload,
            headers={
                "Authorization": f"Bearer {SMSMAGIC_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info("💬 SMS sent to %s: %d", phone, resp.status)
            return "sent"

    except Exception as e:
        logger.error("💬 SMS failed to %s: %s", phone, e)
        return f"error: {e}"


def _initiate_vonage_call(phone, greeting_text):
    """Initiate an outbound call via Vonage Voice API."""
    if not VONAGE_APP_ID or not phone:
        logger.info("📞 [DRY RUN] Vonage call to %s: %s", phone or "NO_PHONE", greeting_text[:80])
        return "dry_run"

    try:
        import urllib.request

        ncco = [{"action": "talk", "text": greeting_text, "voiceName": "Matthew"}]

        payload = json.dumps({
            "to": [{"type": "phone", "number": phone}],
            "from": {"type": "phone", "number": VONAGE_FROM_NUMBER},
            "ncco": ncco
        }).encode('utf-8')

        req = urllib.request.Request(
            "https://api.nexmo.com/v1/calls",
            data=payload,
            headers={
                "Authorization": f"Bearer {VONAGE_APP_ID}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            logger.info("📞 Vonage call initiated to %s: %s", phone, result.get('uuid', 'ok'))
            return "initiated"

    except Exception as e:
        logger.error("📞 Vonage call failed to %s: %s", phone, e)
        return f"error: {e}"




# ---- RATE ANALYSIS ENGINE ----
def calculate_monthly_payment(principal, annual_rate, years=30):
    if principal <= 0 or annual_rate <= 0:
        return 0
    r = annual_rate / 100 / 12
    n = years * 12
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)


def get_market_rate_for_program(program, rates):
    mapping = {
        'Jumbo': 'jumbo_30',
        'Conventional': 'conventional_30',
        'FHA': 'fha_30',
        'VA': 'va_30'
    }
    key = mapping.get(program, 'conventional_30')
    return rates.get(key, 6.625)


def analyze_pipeline(rates):
    results = []
    total_pipeline = 0
    refi_ready_count = 0
    total_monthly_savings = 0
    funded_count = 0

    for loan in PIPELINE:
        if loan['loanAmount'] > 0:
            total_pipeline += loan['loanAmount']
        if loan['stage'] == 'Funded':
            funded_count += 1

        market_rate = get_market_rate_for_program(loan['program'], rates)
        rate_delta = None
        monthly_savings = 0
        refi_score = 0

        if loan['rate'] is not None and market_rate > 0:
            rate_delta = loan['rate'] - market_rate
            if rate_delta > 0:
                current_payment = calculate_monthly_payment(loan['loanAmount'], loan['rate'])
                new_payment = calculate_monthly_payment(loan['loanAmount'], market_rate)
                monthly_savings = max(0, current_payment - new_payment)

                # Score: rate delta weight + loan size weight
                if rate_delta >= 0.75:
                    refi_score += 60
                elif rate_delta >= 0.50:
                    refi_score += 40
                elif rate_delta >= 0.25:
                    refi_score += 20
                else:
                    refi_score += 5

                if loan['loanAmount'] >= 800000:
                    refi_score += 30
                elif loan['loanAmount'] >= 500000:
                    refi_score += 20
                elif loan['loanAmount'] >= 300000:
                    refi_score += 10

                refi_score = min(refi_score, 99)

        if refi_score >= 70 and loan['stage'] == 'Funded':
            refi_ready_count += 1
            total_monthly_savings += monthly_savings

        results.append({
            **loan,
            'marketRate': market_rate,
            'rateDelta': rate_delta,
            'monthlySavings': round(monthly_savings, 2),
            'refiScore': refi_score
        })

    return {
        'loans': results,
        'total_pipeline': total_pipeline,
        'refi_ready_count': refi_ready_count,
        'total_monthly_savings': round(total_monthly_savings, 2),
        'funded_count': funded_count,
        'rates': rates
    }


# ---- EMAIL NOTIFICATIONS ----
def send_daily_notification(analysis):
    """Send Brad a morning email summary."""

    if not SMTP_USER or not SMTP_PASS:
        logger.warning("⚠️  SMTP not configured — skipping email notification")
        logger.info("Would have sent email to: %s", BRAD_EMAIL)
        # Log what would have been sent
        summary = build_email_body(analysis)
        logger.info("Email body:\n%s", summary[:500])
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🏠 Daily Rate Intel — {analysis['refi_ready_count']} Refi Ready | {datetime.now().strftime('%b %d, %Y')}"
        msg['From'] = NOTIFY_FROM
        msg['To'] = BRAD_EMAIL

        body = build_email_body(analysis)
        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            recipients = [BRAD_EMAIL]
            if PHIL_EMAIL:
                msg['Cc'] = PHIL_EMAIL
                recipients.append(PHIL_EMAIL)
            server.sendmail(NOTIFY_FROM, recipients, msg.as_string())

        logger.info("✅ Notification sent to %s", BRAD_EMAIL)
        return True

    except Exception as e:
        logger.error("❌ Failed to send notification: %s", e)
        return False


def build_email_body(analysis):
    """Build a clean HTML email body for Brad's morning briefing."""
    refi_loans = [l for l in analysis['loans'] if l['refiScore'] >= 70 and l['stage'] == 'Funded']
    watch_loans = [l for l in analysis['loans'] if 30 <= l['refiScore'] < 70 and l['stage'] == 'Funded']

    service_url = os.environ.get('SERVICE_URL', 'https://rate-tracker.run.app')

    # Refi rows
    refi_rows = ''
    for l in sorted(refi_loans, key=lambda x: -x['refiScore']):
        refi_rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:600">{l['name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">${l['loanAmount']:,.0f}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">{l['rate']}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">{l['marketRate']}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee;color:#00c853;font-weight:600">${l['monthlySavings']:,.0f}/mo</td>
        </tr>"""

    watch_rows = ''
    for l in sorted(watch_loans, key=lambda x: -x['refiScore']):
        watch_rows += f"""
        <tr>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">{l['name']}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">${l['loanAmount']:,.0f}</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">{l['rate']}%</td>
            <td style="padding:8px 12px;border-bottom:1px solid #eee">{l['rateDelta']:.3f}%</td>
        </tr>"""

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:640px;margin:0 auto;padding:20px">
        <div style="background:#8b0000;color:white;padding:20px;border-radius:12px 12px 0 0;text-align:center">
            <h1 style="margin:0;font-size:22px">🏠 Daily Rate Intelligence</h1>
            <p style="margin:5px 0 0;opacity:0.9;font-size:14px">{datetime.now().strftime('%A, %B %d, %Y')}</p>
        </div>

        <div style="background:#f8f8f8;padding:20px;border:1px solid #e0e0e0">
            <div style="display:flex;text-align:center;gap:10px">
                <div style="flex:1;background:white;padding:16px;border-radius:8px;border:1px solid #e8e8e8">
                    <div style="font-size:28px;font-weight:800;color:#8b0000">{analysis['refi_ready_count']}</div>
                    <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Refi Ready</div>
                </div>
                <div style="flex:1;background:white;padding:16px;border-radius:8px;border:1px solid #e8e8e8">
                    <div style="font-size:28px;font-weight:800">${analysis['total_monthly_savings']:,.0f}</div>
                    <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Monthly Savings</div>
                </div>
                <div style="flex:1;background:white;padding:16px;border-radius:8px;border:1px solid #e8e8e8">
                    <div style="font-size:28px;font-weight:800">{analysis['funded_count']}</div>
                    <div style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px">Funded Loans</div>
                </div>
            </div>
        </div>

        {'<div style="padding:20px;background:white;border:1px solid #e0e0e0;border-top:none"><h3 style="color:#8b0000;margin:0 0 12px">🔥 Refi Opportunities — Call Today</h3><table style="width:100%;border-collapse:collapse;font-size:14px"><thead><tr style="background:#f5f5f5"><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Borrower</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Loan</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Current</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Market</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Savings</th></tr></thead><tbody>' + refi_rows + '</tbody></table></div>' if refi_rows else ''}

        {'<div style="padding:20px;background:white;border:1px solid #e0e0e0;border-top:none"><h3 style="color:#e6a700;margin:0 0 12px">👀 Watch List</h3><table style="width:100%;border-collapse:collapse;font-size:14px"><thead><tr style="background:#f5f5f5"><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Borrower</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Loan</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Rate</th><th style="padding:8px 12px;text-align:left;font-size:12px;color:#666">Δ to Market</th></tr></thead><tbody>' + watch_rows + '</tbody></table></div>' if watch_rows else ''}

        <div style="padding:20px;background:white;border:1px solid #e0e0e0;border-top:none;border-radius:0 0 12px 12px;text-align:center">
            <a href="{service_url}" style="display:inline-block;background:#8b0000;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">View Full Dashboard →</a>
            <p style="margin:12px 0 0;font-size:11px;color:#999">Movement Mortgage — Clair Intelligence System v1.0</p>
        </div>
    </div>
    """


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)
