#!/usr/bin/env python3
# browserless_auto_harvester.py - Harvester automatico per Render

import asyncio
import re
import random
import time
import requests
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import nodriver as uc

# ==================== CONFIGURAZIONE ====================
EMAIL_BASE = "inspector"
DOMAIN = "spaces0.com"

MAIL_TM_EMAIL = "zenadazurli@sharebot.net"
MAIL_TM_PASSWORD = "UV45$!dame"
MAIL_TM_BASE_URL = "https://api.mail.tm"

FULL_NAME = "Auto Account"
COMPANY = "AutoScript"

# Limiti e orari
MAX_ACCOUNTS_PER_DAY = int(os.environ.get('MAX_ACCOUNTS_PER_DAY', '5'))
START_HOUR = int(os.environ.get('START_HOUR', '23'))  # 23 = 11 PM
END_HOUR = int(os.environ.get('END_HOUR', '0'))       # 0 = midnight

# File di output
OUTPUT_DIR = "/tmp/browserless_keys"
KEYS_FILE = f"{OUTPUT_DIR}/all_keys.txt"
ACCOUNTS_FILE = f"{OUTPUT_DIR}/accounts.json"
LOG_FILE = f"{OUTPUT_DIR}/harvester.log"

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}", flush=True)
    
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")

def generate_alias():
    prefixes = ["test", "key", "api", "token", "auto", "bot", "script", "harvest"]
    return f"{random.choice(prefixes)}_{random.randint(1000, 9999)}"

def generate_email():
    alias = generate_alias()
    return f"{EMAIL_BASE}+{alias}@{DOMAIN}"

async def type_like_human(element, text, delay_min=0.08, delay_max=0.15):
    for char in text:
        await element.send_keys(char)
        await asyncio.sleep(random.uniform(delay_min, delay_max))

# ==================== MAIL.TM ====================
class MailTM:
    def __init__(self):
        self.session = requests.Session()
        self.last_processed_id = None
        
    def login(self):
        try:
            res = self.session.post(
                f"{MAIL_TM_BASE_URL}/token",
                json={"address": MAIL_TM_EMAIL, "password": MAIL_TM_PASSWORD}
            )
            if res.status_code != 200:
                return False
            token = res.json()["token"]
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            return True
        except:
            return False
    
    def get_all_messages(self):
        try:
            res = self.session.get(f"{MAIL_TM_BASE_URL}/messages")
            if res.status_code == 200:
                return res.json().get("hydra:member", [])
        except:
            return []
    
    def get_latest_code(self, target_email, timeout_minuti=3):
        start = time.time()
        while time.time() - start < timeout_minuti * 60:
            try:
                messages = self.get_all_messages()
                for msg in messages:
                    to_emails = []
                    for recipient in msg.get("to", []):
                        if isinstance(recipient, dict):
                            to_emails.append(recipient.get("address", "").lower())
                    
                    if target_email.lower() not in str(to_emails):
                        continue
                    
                    if "verify" in msg.get("subject", "").lower():
                        msg_id = msg["id"]
                        if msg_id == self.last_processed_id:
                            continue
                        
                        res = self.session.get(f"{MAIL_TM_BASE_URL}/messages/{msg_id}")
                        msg_data = res.json()
                        body = msg_data.get("text") or msg_data.get("html", "")
                        match = re.search(r'\b(\d{6})\b', body)
                        if match:
                            code = match.group(1)
                            self.last_processed_id = msg_id
                            return code
                time.sleep(5)
            except:
                time.sleep(5)
        return None

# ==================== SELEZIONE DROPDOWN ====================
async def select_use_cases(page):
    try:
        await page.evaluate("""
            const container = document.querySelector('#use-cases-select');
            if (container) {
                container.scrollIntoView({behavior: 'smooth', block: 'center'});
                const btn = container.querySelector('button');
                if (btn) btn.click();
            }
        """)
        await asyncio.sleep(2)
        
        result = await page.evaluate("""
            (function() {
                const dialogs = document.querySelectorAll('[role="dialog"]');
                for (const d of dialogs) {
                    if (d.style.display !== 'none') {
                        const options = d.querySelectorAll('*');
                        for (const opt of options) {
                            if (opt.innerText && opt.innerText.trim() === 'Scraping') {
                                opt.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            })();
        """)
        
        await page.evaluate("""
            document.body.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27, bubbles: true}));
        """)
        await asyncio.sleep(0.5)
        return result
    except:
        return False

# ==================== CREAZIONE ACCOUNT ====================
async def create_account():
    email = generate_email()
    log(f"📧 Tentativo con email: {email}")
    
    mail = MailTM()
    if not mail.login():
        log("❌ Login Mail.tm fallito")
        return None, None
    
    browser = await uc.start(
        headless=True,
        browser_args=[
            '--disable-blink-features=AutomationControlled',
            '--window-size=1280,1024',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu'
        ]
    )
    
    try:
        page = await browser.get("https://www.browserless.io")
        await asyncio.sleep(2)
        
        signup_btn = await page.find(text="Sign Up")
        if signup_btn:
            await signup_btn.click()
        else:
            await page.get("https://www.browserless.io/signup/email")
        await asyncio.sleep(2)
        
        email_field = await page.select('input[placeholder="Your Email"]')
        if email_field:
            await email_field.send_keys(email)
        
        verify_btn = await page.find(text="Verify")
        if verify_btn:
            await verify_btn.click()
        
        code = mail.get_latest_code(email, timeout_minuti=3)
        if not code:
            log("❌ Codice non ricevuto")
            return None, None
        
        code_field = await page.select('input[placeholder="000 000"]')
        if code_field:
            await code_field.send_keys(code)
        
        submit_btn = await page.find(text="Submit code")
        if submit_btn:
            await submit_btn.click()
        
        await asyncio.sleep(5)
        
        # Full Name
        name_field = await page.select('input[placeholder="John Doe"]')
        if name_field:
            await name_field.click()
            await asyncio.sleep(0.3)
            await type_like_human(name_field, FULL_NAME)
        
        # Company
        await page.evaluate("""
            const companyInput = document.querySelector('input[placeholder="ACME Inc"]');
            if (companyInput) {
                companyInput.value = 'AutoScript';
                companyInput.dispatchEvent(new Event('input', { bubbles: true }));
            }
        """)
        
        # Use Cases
        await select_use_cases(page)
        
        # How Heard
        howheard_btn = await page.select('#attribution-select button')
        if howheard_btn:
            await howheard_btn.click()
            await asyncio.sleep(1)
            search_option = await page.find(text="Search Engine")
            if search_option:
                await search_option.click()
        
        # Project Type
        await page.evaluate("""
            const newProject = document.querySelector('#new-project');
            if (newProject) newProject.click();
        """)
        
        # Terms - deseleziona
        checkbox = await page.select('input[type="checkbox"]')
        if checkbox:
            is_checked = await page.evaluate("""
                const cb = document.querySelector('input[type="checkbox"]');
                return cb ? cb.checked : false;
            """)
            if is_checked:
                await checkbox.click()
        
        await asyncio.sleep(1)
        
        # Submit
        await page.evaluate("""
            const btn = document.querySelector('button[data-testid="complete-signup-button"]');
            if (btn) {
                btn.disabled = false;
                btn.removeAttribute('disabled');
                btn.click();
            }
        """)
        
        await asyncio.sleep(8)
        
        # Cerca API key
        show_btn = await page.find(text="Show")
        if show_btn:
            await show_btn.click()
            await asyncio.sleep(1)
        
        api_key = await page.evaluate("""
            (function() {
                const inputs = document.querySelectorAll('input[readonly]');
                for (const input of inputs) {
                    if (input.value && input.value.match(/2U[D|B][a-zA-Z0-9]{40,}/)) {
                        return input.value;
                    }
                }
                const text = document.body.innerText;
                const match = text.match(/2U[D|B][a-zA-Z0-9]{40,}/);
                return match ? match[0] : null;
            })();
        """)
        
        if api_key:
            log(f"✅ API Key ottenuta: {api_key[:20]}...")
            return email, api_key
        else:
            log("❌ API key non trovata")
            return None, None
            
    except Exception as e:
        log(f"❌ Errore: {e}")
        return None, None
        
    finally:
        await browser.stop()

def save_key(email, api_key):
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    with open(KEYS_FILE, "a") as f:
        f.write(f"{api_key}\n")
    
    accounts = []
    if Path(ACCOUNTS_FILE).exists():
        with open(ACCOUNTS_FILE, "r") as f:
            try:
                accounts = json.load(f)
            except:
                accounts = []
    
    accounts.append({
        "email": email,
        "api_key": api_key,
        "timestamp": datetime.now().isoformat()
    })
    
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)
    
    log(f"💾 Chiave salvata. Totale: {len(accounts)}")

def is_harvesting_time():
    now = datetime.now()
    current_hour = now.hour
    
    if START_HOUR == 23 and END_HOUR == 0:
        return current_hour == 23
    
    if START_HOUR <= END_HOUR:
        return START_HOUR <= current_hour < END_HOUR
    else:
        return current_hour >= START_HOUR or current_hour < END_HOUR

def get_today_keys_count():
    if not Path(ACCOUNTS_FILE).exists():
        return 0
    
    today = datetime.now().date()
    with open(ACCOUNTS_FILE, "r") as f:
        try:
            accounts = json.load(f)
            today_accounts = [
                a for a in accounts 
                if datetime.fromisoformat(a["timestamp"]).date() == today
            ]
            return len(today_accounts)
        except:
            return 0

async def main():
    log("=" * 60)
    log("🚀 BROWSERLESS AUTO HARVESTER")
    log("=" * 60)
    log(f"📅 Data: {datetime.now().strftime('%Y-%m-%d')}")
    log(f"⏰ Ora: {datetime.now().strftime('%H:%M:%S')}")
    log(f"🎯 Massimo account/giorno: {MAX_ACCOUNTS_PER_DAY}")
    log(f"⏱️  Orario harvesting: {START_HOUR}:00 - {END_HOUR}:00")
    log("=" * 60)
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    if not is_harvesting_time():
        log("⏸️ Non in orario di harvesting. Uscita.")
        return
    
    today_count = get_today_keys_count()
    remaining = MAX_ACCOUNTS_PER_DAY - today_count
    
    if remaining <= 0:
        log(f"🏁 Limite giornaliero raggiunto ({MAX_ACCOUNTS_PER_DAY}). Uscita.")
        return
    
    log(f"📊 Oggi già creati: {today_count}")
    log(f"📊 Ancora disponibili: {remaining}")
    log("=" * 60)
    
    success_count = 0
    
    for i in range(remaining):
        if not is_harvesting_time():
            log("⏸️ Fine orario harvesting. Interrompo.")
            break
        
        log(f"\n{'='*60}")
        log(f"📝 TENTATIVO {i+1}/{remaining}")
        log(f"{'='*60}")
        
        email, api_key = await create_account()
        
        if api_key:
            save_key(email, api_key)
            success_count += 1
            pause = random.randint(30, 60)
            log(f"⏸️ Pausa di {pause} secondi...")
            await asyncio.sleep(pause)
        else:
            log("❌ Tentativo fallito, pausa più lunga...")
            await asyncio.sleep(120)
    
    log("\n" + "=" * 60)
    log(f"🏁 HARVESTING COMPLETATO!")
    log(f"✅ Nuove chiavi ottenute: {success_count}")
    log(f"💾 File salvati in: {OUTPUT_DIR}")
    log("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())