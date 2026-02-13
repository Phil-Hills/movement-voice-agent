"""
Outlook Rate Watcher — Browser Agent
Automatically logs into Movement Outlook via Okta SSO,
navigates to the "Rate Watch" folder, reads the latest rate email,
parses Optimal Blue rates, and pushes them to the live rate tracker API.

Usage:
    python rate_watcher.py                # Interactive first run (saves session)
    python rate_watcher.py --headless     # Headless mode (uses saved session)
    python rate_watcher.py --dry-run      # Parse only, don't push to API

Authentication:
    - Okta credentials loaded from .env (OKTA_EMAIL, OKTA_PASSWORD)
    - MFA via Okta Verify push notification (you approve on your phone)
    - Browser session/cookies saved locally for faster re-auth

Scheduling:
    Add to crontab or Cloud Scheduler to run every morning at 6:45 AM PT
    (15 minutes before the daily trigger at 7 AM PT)
"""

import os
import re
import sys
import json
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / '.env')
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('rate-watcher')

# ---- CONFIGURATION ----
OKTA_EMAIL = os.environ.get('OKTA_EMAIL', 'phil.hills@movement.com')
OKTA_PASSWORD = os.environ.get('OKTA_PASSWORD', '')

OUTLOOK_URL = 'https://outlook.office.com/mail/'
OKTA_APPS_URL = 'https://movement.okta.com/app/UserHome'

RATE_TRACKER_API = os.environ.get(
    'RATE_TRACKER_API',
    'https://rate-tracker-511662304947.us-west1.run.app/api/rates'
)

# Where to store browser session data for re-use
SESSION_DIR = Path(__file__).parent / '.outlook_session'

# Rate Watch folder name in Outlook
RATE_WATCH_FOLDER = 'Rate Watch'


def parse_rates_from_email(email_text: str) -> dict:
    """
    Parse Optimal Blue rate data from email text content.
    Looks for patterns like:
        30-YR. CONFORMING\n6.048
        30-YR. JUMBO\n6.361
        30-YR. FHA\n5.956
        30-YR. VA\n5.690
    """
    rates = {}

    # Pattern: label followed by a rate number (possibly on next line)
    patterns = [
        (r'30-YR\.?\s*CONFORMING\s*[\n\r]*\s*([\d]+\.[\d]+)', 'conventional_30'),
        (r'30-YR\.?\s*JUMBO\s*[\n\r]*\s*([\d]+\.[\d]+)', 'jumbo_30'),
        (r'30-YR\.?\s*FHA\s*[\n\r]*\s*([\d]+\.[\d]+)', 'fha_30'),
        (r'30-YR\.?\s*VA\s*[\n\r]*\s*([\d]+\.[\d]+)', 'va_30'),
    ]

    for pattern, key in patterns:
        match = re.search(pattern, email_text, re.IGNORECASE)
        if match:
            rates[key] = float(match.group(1))
            logger.info(f"  ✅ Parsed {key}: {rates[key]}%")
        else:
            logger.warning(f"  ⚠️  Could not find {key} in email")

    # Also try USDA and 15-yr if available
    usda_match = re.search(r'30-YR\.?\s*USDA\s*[\n\r]*\s*([\d]+\.[\d]+)', email_text, re.IGNORECASE)
    if usda_match:
        rates['usda_30'] = float(usda_match.group(1))
        logger.info(f"  ✅ Parsed usda_30: {rates['usda_30']}%")

    conf15_match = re.search(r'15-YR\.?\s*CONFORMING\s*[\n\r]*\s*([\d]+\.[\d]+)', email_text, re.IGNORECASE)
    if conf15_match:
        rates['conventional_15'] = float(conf15_match.group(1))
        logger.info(f"  ✅ Parsed conventional_15: {rates['conventional_15']}%")

    return rates


def push_rates_to_api(rates: dict) -> bool:
    """Push parsed rates to the live rate tracker API."""
    try:
        import urllib.request

        payload = json.dumps(rates).encode('utf-8')
        req = urllib.request.Request(
            RATE_TRACKER_API,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            logger.info(f"📡 Rates pushed to tracker: {result.get('status')}")
            logger.info(f"   Updated rates: {json.dumps(result.get('rates', {}), indent=2)}")
            return True

    except Exception as e:
        logger.error(f"❌ Failed to push rates: {e}")
        return False


def run_watcher(headless: bool = False, dry_run: bool = False):
    """Main rate watcher execution flow."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    logger.info("📧 Rate Watcher: Initializing...")
    logger.info(f"   Mode: {'Headless' if headless else 'Visible'} | {'DRY RUN' if dry_run else 'LIVE'}")

    # Ensure session directory exists
    SESSION_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        # Launch with persistent context to reuse cookies/sessions
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=headless,
            viewport={'width': 1400, 'height': 900},
            locale='en-US'
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        # ---- STEP 1: Navigate to Outlook ----
        logger.info("🔑 Step 1: Navigating to Outlook...")

        # Try going directly to Outlook first (may work if session is saved)
        page.goto(OUTLOOK_URL, wait_until='domcontentloaded', timeout=30000)
        time.sleep(3)

        current_url = page.url

        # Check if we're redirected to Okta login
        if 'okta.com' in current_url or 'login.microsoftonline' in current_url:
            logger.info("🔐 Okta login required — authenticating...")
            _handle_okta_login(page)
        elif 'outlook.office' in current_url or 'outlook.live' in current_url:
            logger.info("✅ Already authenticated (session reused)")
        else:
            # Try via Okta apps page
            logger.info("🔄 Navigating via Okta apps page...")
            page.goto(OKTA_APPS_URL, wait_until='domcontentloaded', timeout=30000)
            time.sleep(2)

            if 'okta.com/login' in page.url:
                _handle_okta_login(page)

            # Find and click Outlook/Office 365 app tile
            time.sleep(3)
            _click_outlook_tile(page)

        # ---- STEP 2: Wait for Outlook to fully load ----
        logger.info("📬 Step 2: Waiting for Outlook to load...")
        try:
            # Wait for the Outlook mail interface
            page.wait_for_selector(
                '[aria-label="Mail"], [data-app-section="Mail"], div[role="main"]',
                timeout=60000
            )
            logger.info("✅ Outlook loaded")
        except Exception:
            logger.warning("⚠️  Outlook may not have fully loaded. Continuing...")
            time.sleep(5)

        # ---- STEP 3: Navigate to Rate Watch folder ----
        logger.info(f"📁 Step 3: Looking for '{RATE_WATCH_FOLDER}' folder...")

        rate_watch_found = False

        # Try clicking the folder in the left nav
        try:
            # Look for the folder by name in the folder pane
            folder_selectors = [
                f'[title="{RATE_WATCH_FOLDER}"]',
                f'span:text("{RATE_WATCH_FOLDER}")',
                f'[aria-label*="{RATE_WATCH_FOLDER}"]',
                f'div[data-folder-name="{RATE_WATCH_FOLDER}"]',
            ]

            for selector in folder_selectors:
                try:
                    folder_el = page.locator(selector).first
                    if folder_el.is_visible(timeout=3000):
                        folder_el.click()
                        rate_watch_found = True
                        logger.info(f"✅ Found and clicked '{RATE_WATCH_FOLDER}' folder")
                        break
                except Exception:
                    continue

            if not rate_watch_found:
                # Folder might be nested — try expanding "Folders"
                try:
                    folders_toggle = page.locator('span:text("Folders"), [aria-label="Folders"]').first
                    if folders_toggle.is_visible(timeout=3000):
                        folders_toggle.click()
                        time.sleep(1)

                        # Try again after expanding
                        for selector in folder_selectors:
                            try:
                                folder_el = page.locator(selector).first
                                if folder_el.is_visible(timeout=3000):
                                    folder_el.click()
                                    rate_watch_found = True
                                    logger.info(f"✅ Found '{RATE_WATCH_FOLDER}' under Folders")
                                    break
                            except Exception:
                                continue
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"⚠️  Error finding folder: {e}")

        if not rate_watch_found:
            logger.error(f"❌ Could not find '{RATE_WATCH_FOLDER}' folder.")
            logger.info("   Please navigate to the folder manually in the browser.")
            if not headless:
                input("   Press Enter when you're in the Rate Watch folder...")
            else:
                browser.close()
                return None

        time.sleep(3)  # Wait for folder contents to load

        # ---- STEP 4: Open the latest email ----
        logger.info("📩 Step 4: Opening latest rate email...")

        try:
            # Click the first/most recent email in the list
            email_selectors = [
                '[aria-label*="Rate"] >> nth=0',
                '[role="listbox"] [role="option"]:first-child',
                'div[aria-label*="message list"] > div:first-child',
                '[data-convid] >> nth=0',
            ]

            email_clicked = False
            for selector in email_selectors:
                try:
                    email_el = page.locator(selector).first
                    if email_el.is_visible(timeout=3000):
                        email_el.click()
                        email_clicked = True
                        logger.info("✅ Opened latest email")
                        break
                except Exception:
                    continue

            if not email_clicked:
                logger.warning("⚠️  Could not auto-click email. Trying first visible item...")
                page.locator('[role="option"]').first.click()

        except Exception as e:
            logger.error(f"❌ Could not open email: {e}")
            if not headless:
                input("   Please open the latest rate email, then press Enter...")
            else:
                browser.close()
                return None

        time.sleep(3)  # Wait for email to render

        # ---- STEP 5: Extract email text content ----
        logger.info("👀 Step 5: Extracting rate data from email...")

        email_text = ''
        try:
            # Try to get the email body text
            body_selectors = [
                '[aria-label="Message body"]',
                '[role="document"]',
                'div[class*="ReadingPane"] div[class*="Body"]',
                'div.allowTextSelection',
            ]

            for selector in body_selectors:
                try:
                    body_el = page.locator(selector).first
                    if body_el.is_visible(timeout=3000):
                        email_text = body_el.inner_text()
                        if len(email_text) > 50:
                            logger.info(f"✅ Extracted email text ({len(email_text)} chars)")
                            break
                except Exception:
                    continue

            if not email_text:
                # Fallback: get all visible text on the page
                email_text = page.locator('[role="main"]').inner_text()
                logger.info(f"📄 Fallback: extracted {len(email_text)} chars from main content")

        except Exception as e:
            logger.error(f"❌ Could not extract email text: {e}")
            browser.close()
            return None

        # ---- STEP 6: Parse rates ----
        logger.info("🧮 Step 6: Parsing Optimal Blue rates...")
        logger.info(f"   Email preview: {email_text[:200]}...")

        rates = parse_rates_from_email(email_text)

        if not rates:
            logger.error("❌ No rates found in email text. Raw content:")
            logger.error(email_text[:500])
            browser.close()
            return None

        logger.info(f"\n📊 Parsed Rates:")
        for key, value in rates.items():
            logger.info(f"   {key}: {value}%")

        # ---- STEP 7: Push to API ----
        if dry_run:
            logger.info("\n🔸 DRY RUN — rates NOT pushed to API")
            logger.info(f"   Would push: {json.dumps(rates)}")
        else:
            logger.info("\n📡 Step 7: Pushing rates to tracker API...")
            success = push_rates_to_api(rates)
            if success:
                logger.info("🎉 Daily rates updated successfully!")
            else:
                logger.error("❌ Failed to push rates")

        # Save rates locally as backup
        rates_file = Path(__file__).parent / 'latest_rates.json'
        rates_data = {
            'rates': rates,
            'parsed_at': datetime.now().isoformat(),
            'source': 'Outlook Rate Watch folder'
        }
        rates_file.write_text(json.dumps(rates_data, indent=2))
        logger.info(f"💾 Rates saved locally: {rates_file}")

        browser.close()
        return rates


def _handle_okta_login(page):
    """Handle Okta SSO login with stored credentials and push MFA."""

    # Enter email/username
    try:
        username_field = page.locator('input[name="identifier"], input[name="username"], #okta-signin-username')
        if username_field.is_visible(timeout=5000):
            username_field.fill(OKTA_EMAIL)
            logger.info(f"   Entered email: {OKTA_EMAIL}")

            # Click Next
            next_btn = page.locator('input[type="submit"], button[type="submit"], [data-se="o-form-explain"]')
            next_btn.first.click()
            time.sleep(2)
    except Exception:
        logger.info("   Username field not found (may already be filled)")

    # Enter password
    if OKTA_PASSWORD:
        try:
            password_field = page.locator('input[name="credentials.passcode"], input[name="password"], input[type="password"]')
            if password_field.is_visible(timeout=5000):
                password_field.fill(OKTA_PASSWORD)
                logger.info("   Entered password")

                # Submit
                submit_btn = page.locator('input[type="submit"], button[type="submit"]')
                submit_btn.first.click()
                time.sleep(2)
        except Exception:
            logger.info("   Password field not found")
    else:
        logger.warning("   ⚠️  OKTA_PASSWORD not set in .env — waiting for manual entry...")
        if not page.context.browser.is_connected():
            return
        try:
            page.wait_for_selector('input[type="password"]', timeout=5000)
            input("   Enter your password in the browser, then press Enter here...")
        except Exception:
            pass

    # Handle MFA — wait for Okta Verify push
    logger.info("📱 Waiting for Okta Verify push notification...")
    logger.info("   👉 CHECK YOUR PHONE — approve the push notification")

    # Look for push notification option and click it
    try:
        push_selectors = [
            'a:text("Send Push")',
            'button:text("Send Push")',
            '[data-se="okta_verify-push"]',
            'a[data-se="channel-push"]',
            '[aria-label*="push"]',
        ]
        for selector in push_selectors:
            try:
                push_btn = page.locator(selector).first
                if push_btn.is_visible(timeout=3000):
                    push_btn.click()
                    logger.info("   ✅ Push notification sent!")
                    break
            except Exception:
                continue
    except Exception:
        logger.info("   Push may have been sent automatically")

    # Wait for MFA to complete (user approves on phone)
    try:
        page.wait_for_url(
            lambda url: 'okta.com/login' not in url and 'okta.com/signin' not in url,
            timeout=120000  # 2 minute timeout for MFA approval
        )
        logger.info("   ✅ MFA approved! Continuing...")
    except Exception:
        logger.error("   ❌ MFA timeout — please approve faster next time")


def _click_outlook_tile(page):
    """Find and click the Outlook/Office 365 Mail tile on the Okta apps page."""
    try:
        outlook_selectors = [
            'a[aria-label*="Outlook"]',
            'a[aria-label*="Office 365 Mail"]',
            'a[aria-label*="Microsoft Office"]',
            'a[href*="outlook"]',
            'span:text("Outlook")',
            'span:text("Office 365")',
        ]

        for selector in outlook_selectors:
            try:
                tile = page.locator(selector).first
                if tile.is_visible(timeout=3000):
                    tile.click()
                    logger.info("✅ Clicked Outlook app tile")
                    time.sleep(5)
                    return
            except Exception:
                continue

        logger.warning("⚠️  Could not find Outlook tile. Navigating directly...")
        page.goto(OUTLOOK_URL, wait_until='domcontentloaded')

    except Exception as e:
        logger.error(f"❌ Error clicking Outlook tile: {e}")
        page.goto(OUTLOOK_URL, wait_until='domcontentloaded')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Outlook Rate Watcher — Browser Agent')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (uses saved session)')
    parser.add_argument('--dry-run', action='store_true', help='Parse rates without pushing to API')
    args = parser.parse_args()

    rates = run_watcher(headless=args.headless, dry_run=args.dry_run)

    if rates:
        print(f"\n{'='*50}")
        print(f"📊 TODAY'S RATES (Optimal Blue)")
        print(f"{'='*50}")
        for key, value in rates.items():
            label = key.replace('_', ' ').title().replace('30', '30yr')
            print(f"  {label:.<30} {value}%")
        print(f"{'='*50}")
    else:
        print("\n❌ Rate extraction failed. Check logs above.")
        sys.exit(1)
