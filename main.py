import re
import pandas as pd
import streamlit as st
from time import sleep
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------- MUKILTEO HQ: ARCHITECT CONFIG ----------
APP_VERSION = "v1.1-PITBOSS"
CHROME_DRIVER_PATH = None # Set if local driver is required

def start_browser() -> webdriver.Chrome:
    """Initializes a stealth-optimized Chrome instance."""
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)
    # Stealth settings to bypass basic bot detection
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--start-maximized")
    
    browser = webdriver.Chrome(options=chrome_options)
    # Mask automation signature
    browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    browser.get('https://www.ebay.com/')
    return browser

def login_to_ebay(browser, username, password):
    """Handles the multi-step eBay login process."""
    try:
        wait = WebDriverWait(browser, 10)
        browser.find_element(By.LINK_TEXT, "Sign in").click()
        
        # Username step
        user_field = wait.until(EC.presence_of_element_located((By.ID, "userid")))
        user_field.send_keys(username)
        browser.find_element(By.ID, "signin-continue-btn").click()
        
        # Password step
        pass_field = wait.until(EC.visibility_of_element_located((By.ID, "pass")))
        pass_field.send_keys(password)
        browser.find_element(By.ID, "sgnBt").click()
        
        sleep(3)
        # Check for MFA / Verification
        if "verification" in browser.current_url.lower() or browser.find_elements(By.ID, "send-button"):
            return "verification_needed"

        if "sign in" in browser.current_url.lower():
            return False
        return True
    except Exception as e:
        st.error(f"Login logic failed: {e}")
        return False

def get_auction_data(browser, url):
    """Extracts current price and time left from the listing."""
    try:
        browser.get(url)
        wait = WebDriverWait(browser, 5)
        
        # Check if ended
        page_source = browser.page_source
        if "Item sold" in page_source or "Bidding ended" in page_source:
            return None, None, "Auction Ended"

        # Price extraction (Handling different eBay UI variants)
        try:
            price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.x-price-primary, .prcIsum_bidPrice')))
            price_text = price_element.text
            price_match = re.search(r"[\d,]+\.\d{2}", price_text)
            current_price = float(price_match.group(0).replace(",", "")) if price_match else 0.0
        except:
            return None, None, "Price not found"

        # Time extraction
        try:
            time_element = browser.find_element(By.CSS_SELECTOR, '.ux-timer__text, .vi-tmr-main')
            full_text = time_element.text.lower()
            
            # Simple parser for d/h/m/s
            seconds = 0
            parts = re.findall(r"(\d+)([dhms])", full_text)
            for val, unit in parts:
                if unit == 'd': seconds += int(val) * 86400
                elif unit == 'h': seconds += int(val) * 3600
                elif unit == 'm': seconds += int(val) * 60
                elif unit == 's': seconds += int(val)
            
            return current_price, seconds, "Active"
        except:
            return current_price, 0, "Timer hidden"

    except Exception as e:
        return None, None, f"Audit Error: {str(e)}"

def place_bid(browser, bid_price):
    """The 'Strike' logic: Enters bid and confirms."""
    try:
        wait = WebDriverWait(browser, 10)
        # Click the initial 'Place bid' button
        place_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[text()="Place bid"]/ancestor::button')))
        place_btn.click()

        # Switch to the bidding iframe or modal if necessary
        # Enter numerical value
        input_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="tel"].textbox__control, #maxbid')))
        input_box.clear()
        input_box.send_keys(str(bid_price))
        sleep(0.5)

        # Final Confirmation
        confirm_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="ux-call-to-action"], .place-bid-actions__submit button')))
        confirm_btn.click()
        
        return True, "Strike Successful: Bid Placed."
    except Exception as e:
        return False, f"Strike Failed: {str(e)}"

# ---------- STREAMLIT INTERFACE ----------
st.set_page_content(page_title="Mukilteo HQ: eBay Sniper", page_icon="🎯")

# Session State Initialization
if 'step' not in st.session_state: st.session_state.step = 1
if 'items' not in st.session_state: st.session_state.items = []
if 'results' not in st.session_state: st.session_state.results = []

st.title("🎯 eBay Pit Boss Sniper")
st.caption(f"Mukilteo HQ Systems {APP_VERSION} | Logistical Inventory Acquisition")

if st.session_state.step == 1:
    with st.container():
        st.subheader("🔑 Authenticate Session")
        u = st.text_input("eBay User/Email")
        p = st.text_input("Password", type="password")
        
        if st.button("Initialize Browser & Login"):
            with st.spinner("Bypassing security protocols..."):
                browser = start_browser()
                st.session_state.browser = browser
                res = login_to_ebay(browser, u, p)
                if res == True:
                    st.session_state.step = 2
                    st.rerun()
                elif res == "verification_needed":
                    st.session_state.step = "mfa"
                    st.rerun()
                else:
                    st.error("Authentication Denied. Check credentials.")

if st.session_state.step == "mfa":
    code = st.text_input("Enter 6-Digit Verification Code")
    if st.button("Verify Strike Authority"):
        try:
            code_field = st.session_state.browser.find_element(By.ID, "code")
            code_field.send_keys(code)
            st.session_state.browser.find_element(By.ID, "validate-code-button").click()
            sleep(5)
            st.session_state.step = 2
            st.rerun()
        except:
            st.error("Verification field not found. Check the browser window.")

if st.session_state.step == 2:
    st.subheader("📦 Inventory Target List")
    
    with st.form("add_target"):
        col1, col2 = st.columns([3, 1])
        url = col1.text_input("Item URL")
        max_bid = col2.number_input("Max Bid ($)", min_value=0.15, step=0.01)
        if st.form_submit_button("Add to Target Queue"):
            if url:
                st.session_state.items.append({"url": url, "max": max_bid})
                st.success(f"Target Acquired at ${max_bid}")

    if st.session_state.items:
        st.write("---")
        for i, item in enumerate(st.session_state.items):
            st.text(f"{i+1}. {item['url'][:60]}... -> ${item['max']}")
        
        if st.button("🚀 Commence Sniping Protocol"):
            st.session_state.step = 3
            st.rerun()

if st.session_state.step == 3:
    st.subheader("📡 Live Strike Monitor")
    progress = st.progress(0)
    status = st.empty()
    
    for i, target in enumerate(st.session_state.items):
        status.info(f"Syncing with Target {i+1}...")
        price, time_left, msg = get_auction_data(st.session_state.browser, target['url'])
        
        if price is None:
            st.session_state.results.append({"url": target['url'], "status": f"Error: {msg}"})
            continue

        if price >= target['max']:
            st.session_state.results.append({"url": target['url'], "status": "Outpriced: Floor exceeded"})
            continue

        # Countdown Loop
        while time_left > 15:
            status.warning(f"Waiting for Strike Window... {time_left}s remaining.")
            sleep(10)
            price, time_left, _ = get_auction_data(st.session_state.browser, target['url'])
        
        status.error("🔥 TARGET IN RANGE. PREPARING STRIKE.")
        success, res_msg = place_bid(st.session_state.browser, target['max'])
        st.session_state.results.append({"url": target['url'], "status": res_msg})
    
    st.session_state.step = 4
    st.rerun()

if st.session_state.step == 4:
    st.subheader("📊 Post-Operation Report")
    df = pd.DataFrame(st.session_state.results)
    st.table(df)
    
    if st.button("New Mission"):
        st.session_state.step = 2
        st.session_state.items = []
        st.session_state.results = []
        st.rerun()

st.markdown("---")
st.info("Dedicated to Papa - you will always be the winner ❤️")