import streamlit as st
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Architectural Configuration ---
st.set_page_config(page_title="Saqr Grade Monitor", page_icon="🛡️", layout="wide")

# Engineering UI Styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 4px; height: 3em; background-color: #004a99; color: white; font-weight: bold; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border-left: 5px solid #004a99; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Automated Portal Monitor (PSAU)")
st.info("System Status: Ready for cloud execution. Monitoring academic portal state changes via XPath mapping.")

# --- System Inputs (Sidebar) ---
with st.sidebar:
    st.header("⚙️ System Parameters")
    
    st.subheader("🔑 Authentication")
    portal_user = st.text_input("Portal ID", value="443052289")
    portal_pass = st.text_input("Portal Password", value="2202503658", type="password")
    
    st.divider()
    
    st.subheader("📢 Notification Service")
    tg_token = st.text_input("Telegram Bot Token", placeholder="Enter Bot API Token")
    chat_id = st.text_input("Telegram Chat ID", placeholder="Enter your ID")
    
    st.divider()
    
    st.subheader("🎯 Target Definition")
    grade_xpath = st.text_input("Data XPath", value="/html/body/section/div/div/form/div[2]/div/table[3]/tbody/tr/td/table/tbody/tr[2]/td[3]")
    check_interval = st.slider("Polling Frequency (Min)", 5, 60, 30)

# --- Core Engineering Functions ---

def notify(msg):
    """Sends encoded message via Telegram API."""
    if tg_token and chat_id:
        url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": msg})
        except Exception as e:
            st.error(f"Notification failure: {e}")

def initialize_headless_driver():
    """Configures a headless Chrome instance for server-side scraping."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def run_extraction_cycle():
    """Executes authentication, navigation, and data extraction sequence."""
    driver = initialize_headless_driver()
    wait = WebDriverWait(driver, 25)
    
    try:
        # Step 1: Portal Authentication
        driver.get("https://login.psau.edu.sa/login")
        
        user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#username")))
        pass_field = driver.find_element(By.CSS_SELECTOR, "#password")
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        
        user_field.send_keys(portal_user)
        pass_field.send_keys(portal_pass)
        login_btn.click()
        
        # Step 2: Navigate to Target Sub-page
        time.sleep(4) # Buffer for session establishment
        driver.get("https://eserve.psau.edu.sa/ku/ui/student/homeIndex.faces")
        
        # Step 3: XPath Value Extraction
        target_element = wait.until(EC.presence_of_element_located((By.XPATH, grade_xpath)))
        extracted_value = target_element.text.strip()
        
        return extracted_value

    except Exception as e:
        return f"Operational Failure: {str(e)}"
    finally:
        driver.quit()

# --- Dashboard Layout ---

view_col, monitor_col = st.columns([2, 1])

with monitor_col:
    st.subheader("📊 Engine Status")
    status_box = st.empty()
    metric_box = st.empty()
    timer_box = st.empty()

with view_col:
    st.subheader("📜 Event Logs")
    log_container = st.container()

# --- Execution Controller ---
if st.sidebar.button("🚀 Initialize Monitoring"):
    if not (tg_token and chat_id):
        st.error("Error: Missing Telegram configuration. System cannot notify.")
    else:
        st.session_state.is_running = True
        status_box.success("System: RUNNING")
        notify("Grade Monitor Engine: ACTIVE and watching PSAU portal.")
        
        previous_state = None
        
        while st.session_state.is_running:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with log_container:
                st.info(f"[{timestamp}] Checking portal state...")
            
            current_state = run_extraction_cycle()
            
            if "Failure" in str(current_state):
                with log_container:
                    st.error(f"[{timestamp}] Cycle Error: {current_state}")
            else:
                timer_box.metric("Last Check", time.strftime('%H:%M:%S'))
                metric_box.metric("Current Value", current_state)
                
                # Delta Detection Logic
                if previous_state is not None and current_state != previous_state:
                    with log_container:
                        st.warning(f"[{timestamp}] Delta Detected: State Updated.")
                    notify(f"🚨 PORTAL UPDATE DETECTED!\nNew Value: {current_state}")
                
                previous_state = current_state
                with log_container:
                    st.write(f"[{timestamp}] State Verified: Stable.")

            time.sleep(check_interval * 60)
