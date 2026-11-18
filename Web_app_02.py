import streamlit as st
import requests
import random
import time
import base64
import sqlite3
import uuid
import json
import io
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium

# --- SECRETS SETUP ---
OPENWEATHER_TOKEN = st.secrets["OPENWEATHER_TOKEN"]

# --- DATABASE SETUP (SQLite with Auto-Migration) ---
def init_db():
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (session_id TEXT PRIMARY KEY, zip_code TEXT, notion_token TEXT, database_id TEXT, persona TEXT)''')
    
    # Auto-migration checks for newly added columns
    c.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in c.fetchall()]
    if "occasions" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN occasions TEXT")
    if "occasion_photos" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN occasion_photos TEXT")
    if "form_url" not in columns:
        c.execute("ALTER TABLE users ADD COLUMN form_url TEXT")
        
    conn.commit()
    conn.close()

def get_user_data(session_id):
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    c.execute("SELECT zip_code, notion_token, database_id, persona, occasions, occasion_photos, form_url FROM users WHERE session_id=?", (session_id,))
    row = c.fetchone()
    conn.close()
    if row:
        occasions_list = json.loads(row[4]) if row[4] else []
        photos_dict = json.loads(row[5]) if row[5] else {}
        form_url = row[6] if row[6] else ""
        return {
            "zip_code": row[0], 
            "notion_token": row[1], 
            "database_id": row[2], 
            "persona": row[3],
            "occasions": occasions_list,
            "occasion_photos": photos_dict,
            "form_url": form_url
        }
    return None

def save_user_data(session_id, zip_code, notion_token, database_id, persona=None, occasions=None, occasion_photos=None, form_url=None):
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    occasions_json = json.dumps(occasions) if occasions else json.dumps([])
    
    # Convert uploaded files into base64 strings for persistent storage in SQLite text column
    photos_serializable = {}
    if occasion_photos:
        for occ, file_obj in occasion_photos.items():
            if file_obj is not None:
                try:
                    file_obj.seek(0)
                    b64_str = base64.b64encode(file_obj.read()).decode("utf-8")
                    photos_serializable[occ] = b64_str
                except Exception:
                    pass
    photos_json = json.dumps(photos_serializable)
    
    c.execute("""INSERT OR REPLACE INTO users 
                 (session_id, zip_code, notion_token, database_id, persona, occasions, occasion_photos, form_url) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
              (session_id, zip_code, notion_token, database_id, persona, occasions_json, photos_json, form_url))
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def get_image_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""

def reset_app():
    st.session_state.page = "menu"
    st.session_state.outfit_data = {}

def parse_credentials_file(file_bytes):
    """Parses text file formatted as KEY = "value" """
    config = {}
    try:
        content = file_bytes.decode("utf-8")
        for line in content.splitlines():
            if "=" in line:
                parts = line.split("=", 1)
                key = parts[0].strip().upper()
                val = parts[1].strip().strip('"').strip("'")
                config[key] = val
    except Exception:
        pass
    return config

def verify_notion_credentials(token, db_id):
    """Sends a ping to Notion and returns (is_valid, specific_error_message)."""
    url = f"https://api.notion.com/v1/databases/{db_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return True, ""
        elif response.status_code == 401:
            return False, "Invalid Notion API Token. Please check your Notion token."
        elif response.status_code in (400, 404):
            return False, "Invalid Database ID. Please check your database ID."
        else:
            return False, f"Notion connection failed with error code {response.status_code}."
    except Exception as e:
        return False, f"Could not connect to Notion: {e}"

# Load background and TARDIS icon
bg_b64 = get_image_base64("Photos/background.png")
tardis_b64 = get_image_base64("Photos/TARDIS_icon.png")

# Set the page title and layout
st.set_page_config(page_title="TARDIS Closet", page_icon="Photos/TARDIS_icon.png", layout="centered", initial_sidebar_state="collapsed")

# Force the TARDIS icon for the PWA/Home Screen shortcut using a direct GitHub URL
components.html(
    """
    <script>
        const manifest = {
            "name": "TARDIS Closet",
            "short_name": "TARDIS Closet",
            "icons": [{
                "src": "https://raw.githubusercontent.com/EvanEngineeringLab/TARDIS-Closet/main/Photos/TARDIS_icon.png",
                "sizes": "512x512",
                "type": "image/png"
            }],
            "start_url": ".",
            "display": "standalone"
        };
        
        const stringManifest = JSON.stringify(manifest);
        const blob = new Blob([stringManifest], {type: 'application/json'});
        const manifestURL = URL.createObjectURL(blob);
        
        let link = document.querySelector('link[rel="manifest"]');
        if (!link) {
            link = document.createElement('link');
            link.rel = 'manifest';
            document.head.appendChild(link);
        }
        link.href = manifestURL;
    </script>
    """,
    height=0,
    width=0
)

# --- CUSTOM CSS ---
st.markdown(f"""
<style>
    /* Doctor Who Background */
    .stApp {{
        background-image: url("data:image/png;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    .title-container {{ text-align: center; margin-bottom: 30px; }}
    
    /* Make buttons solid dark gray so they don't blend into the background */
    .stButton>button {{ 
        height: 60px; 
        font-size: 18px !important; 
        border-radius: 10px;
        background-color: rgba(30, 30, 30, 0.9) !important;
        color: white !important;
        border: 1px solid #555 !important;
    }}
    
    .stButton>button:hover {{
        border: 1px solid #4da8da !important;
        color: #4da8da !important;
    }}
    
    .weather-prompt {{ font-size: 24px; font-weight: bold; text-align: center; margin-top: 20px; margin-bottom: 20px; text-shadow: 2px 2px 4px #000; }}
    
    [data-testid="StyledFullScreenButton"], 
    button[title="View fullscreen"] {{ display: none !important; }}
    [data-testid="column"]:hover {{ background-color: transparent !important; }}

    /* Style the welcome/persona forms to look like solid cards */
    [data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.85) !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #555;
    }}

    /* Force ALL text inside forms to be pure white */
    [data-testid="stForm"] * {{
        color: white !important;
    }}
    [data-testid="stForm"] h3 {{
        font-weight: 700 !important;
    }}
    
    /* Force the input boxes to be dark grey so white text is always visible */
    [data-testid="stTextInput"] input {{
        background-color: rgba(50, 50, 50, 0.9) !important; 
        color: white !important; 
        border: 1px solid #777 !important;
    }}

    /* Make the columns responsive for mobile */
    @media (max-width: 768px) {{
        [data-testid="column"] {{
            width: 50% !important;
            flex: 1 1 calc(50% - 1rem) !important;
            min-width: 50% !important;
        }}
        .title-container h1 {{
            font-size: 2rem !important;
        }}
        .title-container img {{
            height: 80px !important;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# Render header with TARDIS image
st.markdown(f'<div class="title-container" style="display: flex; justify-content: center; align-items: center; gap: 15px;"><img src="data:image/png;base64,{tardis_b64}" style="height: 120px;"><h1 style="margin: 0; color: white; text-shadow: 2px 2px 4px #000;">TARDIS Closet</h1></div>', unsafe_allow_html=True)

# --- BULLETPROOF LOGOUT HANDLER (QUERY PARAMS) ---
if st.query_params.get("action") == "logout":
    if "session_id" in st.session_state:
        try:
            conn = sqlite3.connect('wardrobe.db')
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE session_id=?", (st.session_state.session_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
            
    for key in list(st.session_state.keys()):
        del st.session_state[key]
        
    st.query_params.clear()
    st.rerun()

# --- URL SESSION MANAGEMENT & PAGE PERSISTENCE ---
query_params = st.query_params
url_session_id = query_params.get("user_id", None)
url_page = query_params.get("p", None)

if "session_id" not in st.session_state:
    if url_session_id:
        st.session_state.session_id = url_session_id
    else:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.query_params["user_id"] = new_id

# Safe Initialization & Strict Startup Routing
user_data = get_user_data(st.session_state.session_id)

if "notion_token" not in st.session_state:
    st.session_state.notion_token = user_data["notion_token"] if user_data else ""

if "database_id" not in st.session_state:
    st.session_state.database_id = user_data["database_id"] if user_data else ""

if "form_url" not in st.session_state:
    st.session_state.form_url = user_data["form_url"] if (user_data and "form_url" in user_data) else ""

if "zip_code" not in st.session_state:
    st.session_state.zip_code = user_data["zip_code"] if (user_data and user_data["zip_code"]) else None

if "persona" not in st.session_state:
    st.session_state.persona = user_data["persona"] if user_data else None

# Restore cached occasions from SQLite on startup
if "occasions" not in st.session_state:
    st.session_state.occasions = user_data.get("occasions", []) if user_data else []

# Restore cached occasion photos from SQLite on startup (converts base64 back into streamable buffers)
if "occasion_photos" not in st.session_state:
    st.session_state.occasion_photos = {}
    if user_data and user_data.get("occasion_photos"):
        for occ, b64_str in user_data["occasion_photos"].items():
            try:
                file_bytes = base64.b64decode(b64_str)
                st.session_state.occasion_photos[occ] = io.BytesIO(file_bytes)
            except Exception:
                pass

# --- STRICT GATEKEEPER ROUTING ---
if not st.session_state.notion_token or not st.session_state.database_id:
    st.session_state.page = "welcome"
elif "page" not in st.session_state:
    if url_page and user_data and user_data["notion_token"] and user_data["database_id"]:
        st.session_state.page = url_page
    elif not st.session_state.persona:
        st.session_state.page = "persona_select"
    elif not st.session_state.zip_code:
        st.session_state.page = "zip_map"
    else:
        st.session_state.page = "menu"

st.query_params["p"] = st.session_state.page

if "outfit_data" not in st.session_state:
    st.session_state.outfit_data = {}

# ==========================================
# PAGE 0: WELCOME SCREEN (Credentials)
# ==========================================
if st.session_state.page == "welcome":
    st.markdown('<div style="text-align: center; font-size: 20px; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">Welcome! Please upload your credentials file to begin.</div>', unsafe_allow_html=True)
    
    with st.form("setup_form"):
        st.subheader("Notion Integration")
        uploaded_file = st.file_uploader("Upload your credentials file (.txt):", type=["txt"])
        
        submitted = st.form_submit_button("Start", use_container_width=True, type="primary")
        
        if submitted:
            notion_token = ""
            database_id = ""
            form_url = ""
            
            if uploaded_file is not None:
                config_data = parse_credentials_file(uploaded_file.getvalue())
                notion_token = config_data.get("NOTION_TOKEN", "").strip('"\'')
                database_id = config_data.get("DATABASE_ID", "").strip('"\'')
                form_url = config_data.get("FORM", "").strip('"\'')
            
            # Validate token, database ID, and Notion form URL format
            is_valid_url = form_url.startswith("http") and "notion" in form_url
            
            if notion_token and database_id and form_url and is_valid_url:
                with st.spinner("Verifying Notion credentials..."):
                    is_valid, error_msg = verify_notion_credentials(notion_token, database_id)
                
                if is_valid:
                    save_user_data(
                        session_id=st.session_state.session_id, 
                        zip_code=st.session_state.zip_code, 
                        notion_token=notion_token, 
                        database_id=database_id,
                        persona=st.session_state.persona,
                        occasions=st.session_state.get("occasions", []),
                        occasion_photos=st.session_state.get("occasion_photos", {}),
                        form_url=form_url
                    )
                    
                    st.session_state.notion_token = notion_token
                    st.session_state.database_id = database_id
                    st.session_state.form_url = form_url
                    
                    # Gatekeeper routing step
                    if not st.session_state.persona:
                        st.session_state.page = "persona_select"
                    elif not st.session_state.zip_code:
                        st.session_state.page = "zip_map"
                    else:
                        st.session_state.page = "menu"
                    st.rerun()
                else:
                    st.error(error_msg)
            elif not notion_token or not database_id:
                st.error("Please provide a valid credentials file containing both NOTION_TOKEN and DATABASE_ID.")
            elif not form_url:
                st.error("Missing FORM = \"url\" in your credentials file.")
            else:
                st.error(f"Invalid Form URL format: '{form_url}'. It must be a valid Notion link containing 'notion'.")

# ==========================================
# PAGE 0.5A: STYLE PERSONA SELECTOR
# ==========================================
if st.session_state.page == "persona_select":
    st.markdown("""
    <style>
        .persona-subtitle {
            color: white !important;
            font-size: 18px !important;
            font-weight: bold !important;
            text-align: center;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px #000 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div style="text-align: center; font-size: 26px; font-weight: bold; margin-bottom: 10px; color: white; text-shadow: 2px 2px 4px #000;">Select Your Style Persona</div>', unsafe_allow_html=True)
    st.markdown('<div class="persona-subtitle">Choose your wardrobe styling category:</div>', unsafe_allow_html=True)

    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        body {
            background: transparent;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 10px;
        }
        .container {
            display: flex;
            gap: 20px;
            width: 100%;
            max-width: 800px;
        }
        .card {
            flex: 1;
            height: 210px;
            background-color: rgba(0, 0, 0, 0.85);
            border: 1px solid #555;
            border-radius: 12px;
            box-shadow: 0px 6px 14px rgba(0, 0, 0, 0.7);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
            user-select: none;
        }
        .card:hover {
            border-color: #4da8da;
            box-shadow: 0px 8px 18px rgba(77, 168, 218, 0.45);
            transform: translateY(-2px);
        }
        .card:hover .label {
            color: #4da8da;
        }
        .emoji {
            font-size: 54px;
            line-height: 1;
            margin-bottom: 14px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .label {
            font-size: 28px;
            font-weight: bold;
            color: white;
            text-align: center;
            transition: color 0.2s ease-in-out;
        }
    </style>
    </head>
    <body>
        <div class="container">
            <div class="card" onclick="selectPersona('Masculine')">
                <div class="emoji">👔</div>
                <div class="label">Masculine</div>
            </div>
            <div class="card" onclick="selectPersona('Feminine')">
                <div class="emoji">👗</div>
                <div class="label">Feminine</div>
            </div>
        </div>

        <script>
            // Hide the trigger buttons directly via DOM traversal as soon as they appear
            function hideTriggerButtons() {
                const buttons = window.parent.document.querySelectorAll('button');
                buttons.forEach(btn => {
                    const txt = btn.innerText.trim();
                    if (txt === 'TRIGGER_MASCULINE' || txt === 'TRIGGER_FEMININE') {
                        const wrapper = btn.closest('div[data-testid="stHorizontalBlock"]') || btn.closest('.element-container');
                        if (wrapper) {
                            wrapper.style.display = 'none';
                        } else {
                            btn.style.display = 'none';
                        }
                    }
                });
            }

            // Run immediately and watch for Streamlit DOM re-renders
            hideTriggerButtons();
            const observer = new MutationObserver(hideTriggerButtons);
            observer.observe(window.parent.document.body, { childList: true, subtree: true });

            function selectPersona(choice) {
                const buttons = window.parent.document.querySelectorAll('button');
                for (let btn of buttons) {
                    if (btn.innerText.trim() === 'TRIGGER_' + choice.toUpperCase()) {
                        btn.click();
                        break;
                    }
                }
            }
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=240)

    # Hidden Streamlit trigger buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("TRIGGER_MASCULINE", key="hidden_masc"):
            st.session_state.persona = "Masculine"
            save_user_data(
                st.session_state.session_id,
                st.session_state.zip_code,
                st.session_state.notion_token,
                st.session_state.database_id,
                persona="Masculine"
            )
            # Route to zip_map if zip is missing, else menu
            if not st.session_state.zip_code:
                st.session_state.page = "zip_map"
            else:
                st.session_state.page = "menu"
            st.rerun()

    with col2:
        if st.button("TRIGGER_FEMININE", key="hidden_fem"):
            st.session_state.persona = "Feminine"
            save_user_data(
                st.session_state.session_id,
                st.session_state.zip_code,
                st.session_state.notion_token,
                st.session_state.database_id,
                persona="Feminine"
            )
            # Route to zip_map if zip is missing, else menu
            if not st.session_state.zip_code:
                st.session_state.page = "zip_map"
            else:
                st.session_state.page = "menu"
            st.rerun()


# ==========================================
# PAGE: ZIP MAP (0.5b)
# ==========================================
elif st.session_state.page == "zip_map":
    st.markdown('<div style="text-align: center; color: white; font-size: 24px; font-weight: bold; margin-bottom: 20px; text-shadow: 2px 2px 4px #000;">Select Your Location</div>', unsafe_allow_html=True)

    # Initialize map pin and location state securely
    if "map_pin" not in st.session_state:
        st.session_state.map_pin = None
    if "detected_location" not in st.session_state:
        st.session_state.detected_location = None

    # Continental US center and fixed default zoom (Level 4) - no state magnification loops
    map_center = [39.8283, -98.5795]
    
    # Create base map using OpenStreetMap (No paid API keys required)
    m = folium.Map(
        location=map_center, 
        zoom_start=4, 
        tiles="OpenStreetMap"
    )

    # Draw marker if pin exists in session
    if st.session_state.map_pin:
        folium.Marker(
            location=st.session_state.map_pin,
            popup="Selected Location",
            icon=folium.Icon(color="red", icon="map-pin", prefix="fa")
        ).add_to(m)

    # Render map and capture user interaction data
    map_data = st_folium(m, width=700, height=400, key="zip_selection_map")

    # Capture click instantly and run reverse geocoding for town/state/county name
    if map_data and map_data.get("last_clicked"):
        lat = map_data["last_clicked"]["lat"]
        lng = map_data["last_clicked"]["lng"]
        
        if st.session_state.map_pin != (lat, lng):
            st.session_state.map_pin = (lat, lng)
            
            # Reverse geocode via OpenWeather geo API using exact coordinates
            geo_url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lng}&limit=1&appid={OPENWEATHER_TOKEN}"
            try:
                geo_resp = requests.get(geo_url)
                if geo_resp.status_code == 200 and geo_resp.json():
                    loc_data = geo_resp.json()[0]
                    place = loc_data.get('name') or loc_data.get('state') or loc_data.get('county') or "Selected Area"
                    state = loc_data.get('state', '')
                    
                    # Format clean location string with full state name (e.g., "Center, Colorado")
                    if state and place != state:
                        st.session_state.detected_location = f"{place}, {state}"
                    else:
                        st.session_state.detected_location = place
                else:
                    st.session_state.detected_location = "Selected Area"
            except Exception:
                st.session_state.detected_location = "Selected Area"
                
            st.rerun()

    # Confirmation prompt and original colored buttons (Column 1 = Yes, Column 2 = No)
    if st.session_state.map_pin:
        location_name = st.session_state.detected_location or "this area"
        
        st.markdown(f"""
            <div style="text-align: center; color: white; font-size: 18px; margin-top: 20px; text-shadow: 1px 1px 2px #000;">
                Is <b>{location_name}</b> the correct location?
            </div>
        """, unsafe_allow_html=True)

        # Custom CSS for Green ("Yes, Correct") and Red ("No, Pick Again") buttons
        st.markdown("""
            <style>
            div.stButton > button:has-text("Yes, Correct") {
                background-color: #2E7D32 !important;
                color: white !important;
                border: 1px solid #1B5E20 !important;
            }
            div.stButton > button:has-text("Yes, Correct"):hover {
                background-color: #1B5E20 !important;
            }
            div.stButton > button:has-text("No, Pick Again") {
                background-color: #C62828 !important;
                color: white !important;
                border: 1px solid #8E0000 !important;
            }
            div.stButton > button:has-text("No, Pick Again"):hover {
                background-color: #8E0000 !important;
            }
            </style>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Correct", use_container_width=True, key="btn_yes_town"):
                if st.session_state.map_pin:
                    lat, lng = st.session_state.map_pin
                    # Save exact coordinates string to session state (replacing zip dependency)
                    st.session_state.zip_code = f"{lat},{lng}"
                    
                    save_user_data(
                        st.session_state.session_id, 
                        st.session_state.zip_code, 
                        st.session_state.notion_token, 
                        st.session_state.database_id, 
                        st.session_state.get("persona")
                    )
                    st.session_state.page = "config"
                    st.rerun()
                else:
                    st.error("Error: Please drop a pin on the map first.")
        with col2:
            if st.button("No, Pick Again", use_container_width=True, key="btn_no_town"):
                st.session_state.map_pin = None
                st.session_state.detected_location = None
                st.rerun()

# ==========================================
# PAGE: 0.75 WARDROBE CONFIGURATION
# ==========================================
elif st.session_state.page == "config":
    
    # 1. AUTOMATIC SCREEN WIDTH DETECTION VIA QUERY PARAMS
    st.markdown("""
        <script>
            (function() {
                const width = window.innerWidth;
                const urlParams = new URLSearchParams(window.parent.location.search);
                const currentWidthParam = urlParams.get('sw');
                if (!currentWidthParam || Math.abs(parseInt(currentWidthParam) - width) > 50) {
                    urlParams.set('sw', width);
                    window.parent.location.search = urlParams.toString();
                }
            })();
        </script>
    """, unsafe_allow_html=True)

    try:
        screen_width = int(st.query_params.get("sw", 1024))
    except Exception:
        screen_width = 1024

    # 2. MOBILE BLOCKER (< 500 pixels) WITH RETURN TO MENU BUTTON
    if screen_width < 500:
        st.markdown("""
            <div style="background-color: #1e1e1e; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 30px; margin: 40px auto; max-width: 600px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); text-align: center;">
                <h3 style="color: #ff9800; margin-top: 0;">PC Setup Required</h3>
                <p style="color: #ffffff; font-size: 16px; line-height: 1.5;">
                    Your screen width is detected at <b>{}px</b>. Please complete your wardrobe and database configuration using a PC or laptop.
                </p>
            </div>
        """.format(screen_width), unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("Return to Menu", use_container_width=True, key="btn_return_menu"):
                st.session_state.page = "menu"
                st.rerun()

    # 3. FULL PC CONFIGURATION WORKSTATION (>= 500 pixels)
    else:
        # Scoped CSS to widen layout, match uploader height, and hide uploader helper text
        st.markdown("""
            <style>
            .block-container {
                max-width: 90% !important;
                padding-top: 2rem !important;
            }
            .custom-desc-box {
                background-color: #1e1e1e !important;
                border: 1px solid rgba(255,255,255,0.2) !important;
                border-radius: 12px !important;
                padding: 16px !important;
                margin-bottom: 20px !important;
                box-shadow: 0 4px 6px rgba(0,0,0,0.5) !important;
                text-align: center !important;
            }
            .custom-desc-text {
                color: #ffffff !important;
                font-size: 18px !important;
                font-weight: normal !important;
                line-height: 1.4 !important;
            }
            /* Perfectly match file uploader height to text inputs */
            [data-testid="stFileUploader"] section {
                padding: 0px 4px !important;
                min-height: 34px !important;
                height: 36px !important;
            }
            [data-testid="stFileUploader"] section div {
                gap: 0px !important;
                padding: 0px !important;
            }
            [data-testid="stFileUploader"] button {
                padding: 0px 10px !important;
                min-height: 28px !important;
                font-size: 13px !important;
            }
            /* Hide file uploader subtext/instructions completely */
            [data-testid="stFileUploader"] small, 
            [data-testid="stFileUploader"] section div[data-testid="stMarkdownContainer"] {
                display: none !important;
            }
            </style>
            <div class="custom-desc-box">
                <div class="custom-desc-text">Customize your dynamic Notion database options, rename items, set priority position, and assign default PNG photos per occasion.</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="color: white; font-size: 28px; font-weight: bold; text-align: center; margin-bottom: 20px; text-shadow: 2px 2px 3px #000;">Wardrobe Configuration</div>', unsafe_allow_html=True)

        # Initialize occasion photo reserves in session state if missing
        if "occasion_photos" not in st.session_state:
            st.session_state.occasion_photos = {}

        # Fetch live schema from Notion once per entry
        if "notion_schema" not in st.session_state:
            with st.spinner("Fetching database schema from Notion..."):
                url = f"https://api.notion.com/v1/databases/{st.session_state.database_id}"
                headers = {
                    "Authorization": f"Bearer {st.session_state.notion_token}",
                    "Notion-Version": "2022-06-28"
                }
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    st.session_state.notion_schema = True
                    schema = response.json()
                    properties = schema.get("properties", {})
                    
                    g_type_prop = properties.get("Garment Type", {})
                    g_prop_type = g_type_prop.get("type", "select")
                    g_options = [opt["name"] for opt in g_type_prop.get(g_prop_type, {}).get("options", [])]
                    
                    occasion_prop = properties.get("Occasion", {})
                    o_prop_type = occasion_prop.get("type", "multi_select")
                    o_options = [opt["name"] for opt in occasion_prop.get(o_prop_type, {}).get("options", [])]
                    
                    st.session_state.g_prop_type = g_prop_type
                    st.session_state.o_prop_type = o_prop_type
                    st.session_state.editable_garment_types = g_options
                    st.session_state.editable_occasions = o_options
                else:
                    st.error(f"Failed to fetch Notion schema: {response.status_code}")
                    st.session_state.editable_garment_types = []
                    st.session_state.editable_occasions = []

        if "editable_garment_types" not in st.session_state:
            st.session_state.editable_garment_types = []
        if "editable_occasions" not in st.session_state:
            st.session_state.editable_occasions = []

        # Deletion, Addition, & Clear Callbacks
        def remove_garment(index):
            st.session_state.editable_garment_types.pop(index)

        def remove_occasion(index):
            removed_item = st.session_state.editable_occasions.pop(index)
            if removed_item in st.session_state.occasion_photos:
                del st.session_state.occasion_photos[removed_item]

        def clear_occasion_photo(occ_name):
            if occ_name in st.session_state.occasion_photos:
                del st.session_state.occasion_photos[occ_name]

        def add_garment_callback():
            val = st.session_state.get("new_garment_input", "").strip()
            if val and val not in st.session_state.editable_garment_types:
                st.session_state.editable_garment_types.append(val)
                st.session_state.new_garment_input = ""

        def add_occasion_callback():
            val = st.session_state.get("new_occasion_input", "").strip()
            if val and val not in st.session_state.editable_occasions:
                st.session_state.editable_occasions.append(val)
                st.session_state.new_occasion_input = ""

        col_cfg1, col_cfg2 = st.columns(2, gap="large")

        # --- GARMENT TYPES COLUMN ---
        with col_cfg1:
            st.markdown('<div style="color: white; font-size: 18px; font-weight: bold; text-shadow: 1px 1px 2px #000; text-align: center; margin-bottom: 15px;">Garment Types</div>', unsafe_allow_html=True)
            
            g_list = st.session_state.editable_garment_types

            if not g_list:
                st.markdown('<div style="color: white; font-size: 15px; font-weight: bold; text-align: center; margin-bottom: 15px;">No garment types in Notion yet. Add one below.</div>', unsafe_allow_html=True)

            for idx, item in enumerate(g_list):
                cols = st.columns([1.0, 3.5, 0.8])
                with cols[0]:
                    positions = list(range(1, len(g_list) + 1))
                    new_pos = st.selectbox("Pos", options=positions, index=idx, key=f"pos_g_{idx}_{item}", label_visibility="collapsed")
                    if new_pos - 1 != idx:
                        item_to_move = g_list.pop(idx)
                        g_list.insert(new_pos - 1, item_to_move)
                        st.session_state.editable_garment_types = g_list
                        st.rerun()
                with cols[1]:
                    val = st.text_input(f"g_{idx}", value=item, key=f"txt_g_{idx}_{item}", label_visibility="collapsed")
                    if val.strip() and val.strip() != item:
                        st.session_state.editable_garment_types[idx] = val.strip()
                with cols[2]:
                    st.button("❌", key=f"del_g_{idx}", on_click=remove_garment, args=(idx,))

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.text_input("Add new garment type", placeholder="Type & press Enter...", key="new_garment_input", on_change=add_garment_callback, label_visibility="collapsed")
            
            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("CLEAR GARMENTS", key="btn_clear_garments", use_container_width=True):
                st.session_state.editable_garment_types = []
                st.rerun()

        # --- OCCASIONS COLUMN ---
        with col_cfg2:
            st.markdown('<div style="color: white; font-size: 18px; font-weight: bold; text-shadow: 1px 1px 2px #000; text-align: center; margin-bottom: 15px;">Occasions & Photos</div>', unsafe_allow_html=True)
            
            o_list = st.session_state.editable_occasions

            if not o_list:
                st.markdown('<div style="color: white; font-size: 15px; font-weight: bold; text-align: center; margin-bottom: 15px;">No occasions in Notion yet. Add one below.</div>', unsafe_allow_html=True)

            for idx, item in enumerate(o_list):
                has_photo = item in st.session_state.occasion_photos
                
                if has_photo:
                    cols = st.columns([1.0, 2.5, 3.0, 0.8, 0.8])
                else:
                    cols = st.columns([1.0, 2.5, 3.8, 0.8])

                with cols[0]:
                    positions = list(range(1, len(o_list) + 1))
                    new_pos = st.selectbox("Pos", options=positions, index=idx, key=f"pos_o_{idx}_{item}", label_visibility="collapsed")
                    if new_pos - 1 != idx:
                        item_to_move = o_list.pop(idx)
                        o_list.insert(new_pos - 1, item_to_move)
                        st.session_state.editable_occasions = o_list
                        st.rerun()
                with cols[1]:
                    val = st.text_input(f"o_{idx}", value=item, key=f"txt_o_{idx}_{item}", label_visibility="collapsed")
                    if val.strip() and val.strip() != item:
                        old_name = item
                        new_name = val.strip()
                        st.session_state.editable_occasions[idx] = new_name
                        if old_name in st.session_state.occasion_photos:
                            st.session_state.occasion_photos[new_name] = st.session_state.occasion_photos.pop(old_name)
                with cols[2]:
                    uploaded_png = st.file_uploader(f"PNG for {item}", type=["png"], key=f"png_o_{idx}_{item}", label_visibility="collapsed")
                    if uploaded_png is not None:
                        st.session_state.occasion_photos[item] = uploaded_png
                
                if has_photo:
                    with cols[3]:
                        st.button("🗑️", key=f"clear_photo_{idx}_{item}", on_click=clear_occasion_photo, args=(item,), help="Remove uploaded photo and revert to default asset")
                    with cols[4]:
                        st.button("❌", key=f"del_o_{idx}", on_click=remove_occasion, args=(idx,))
                else:
                    with cols[3]:
                        st.button("❌", key=f"del_o_{idx}", on_click=remove_occasion, args=(idx,))

            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            st.text_input("Add new occasion", placeholder="Type & press Enter...", key="new_occasion_input", on_change=add_occasion_callback, label_visibility="collapsed")

            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
            if st.button("CLEAR OCCASIONS", key="btn_clear_occasions", use_container_width=True):
                st.session_state.editable_occasions = []
                st.session_state.occasion_photos = {}
                st.rerun()

        st.write("---")

        # Save & Commit to Notion & SQLite
        if st.button("💾 Save & Continue to Main Menu", type="primary", use_container_width=True):
            with st.spinner("Updating Notion database schema and saving persistent state..."):
                url = f"https://api.notion.com/v1/databases/{st.session_state.database_id}"
                headers = {
                    "Authorization": f"Bearer {st.session_state.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                
                g_type_key = st.session_state.get("g_prop_type", "select")
                o_type_key = st.session_state.get("o_prop_type", "multi_select")

                payload = {
                    "properties": {
                        "Garment Type": {
                            g_type_key: {
                                "options": [{"name": name} for name in st.session_state.editable_garment_types]
                            }
                        },
                        "Occasion": {
                            o_type_key: {
                                "options": [{"name": name} for name in st.session_state.editable_occasions]
                            }
                        }
                    }
                }
                
                response = requests.patch(url, json=payload, headers=headers)
                if response.status_code == 200:
                    st.session_state.occasions = st.session_state.editable_occasions
                    save_user_data(
                        session_id=st.session_state.session_id,
                        zip_code=st.session_state.zip_code,
                        notion_token=st.session_state.notion_token,
                        database_id=st.session_state.database_id,
                        persona=st.session_state.persona,
                        occasions=st.session_state.editable_occasions,
                        occasion_photos=st.session_state.occasion_photos
                    )
                    
                    st.success("Notion schema and photo storage updated successfully!")
                    if "notion_schema" in st.session_state:
                        del st.session_state.notion_schema
                    time.sleep(1)
                    st.session_state.page = "menu"
                    st.rerun()
                else:
                    st.error(f"Failed to update Notion schema: {response.status_code} - {response.text}")
        
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        if st.button("← Back to Menu", use_container_width=True):
            st.session_state.page = "menu"
            st.rerun()

# ==========================================
# PAGE 1: THE MENU
# ==========================================
elif st.session_state.page == "menu":
    with st.sidebar:
        st.header("Navigation")

        # Jump directly to My Closet (Page 1.5)
        if st.button("My Closet", use_container_width=True):
            st.session_state.page = "my_closet"
            st.rerun()

        # Jump directly to Add Clothing (Page 1.75)
        if st.button("Add Clothing", use_container_width=True):
            st.session_state.page = "add_clothing"
            st.rerun()
        
        st.header("Settings")
        st.write(f"**Persona:** {st.session_state.get('persona', 'Not Set')}")
        
        # Button to jump directly to Wardrobe Configuration
        if st.button("Wardrobe Configuration", use_container_width=True):
            st.session_state.page = "config"
            st.rerun()
            
        # Button to return to the interactive map to change location (anchored at the bottom)
        if st.button("Change Location", use_container_width=True):
            st.session_state.page = "zip_map"
            st.rerun()

    # --- LOGOUT HANDLER VIA QUERY PARAMS ---
    if st.query_params.get("action") == "logout":
        conn = sqlite3.connect('wardrobe.db')
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE session_id=?", (st.session_state.session_id,))
        conn.commit()
        conn.close()
        
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

    components.html("""
        <script>
            (function() {
                function injectHeaderButton() {
                    try {
                        const doc = window.parent.document;
                        const header = doc.querySelector('header[data-testid="stHeader"]');
                        if (header && !doc.getElementById('custom-header-logout')) {
                            const btn = document.createElement('a');
                            btn.id = 'custom-header-logout';
                            btn.innerText = 'Log Out';
                            btn.href = '?action=logout';
                            btn.style.backgroundColor = '#D32F2F';
                            btn.style.color = 'white';
                            btn.style.textDecoration = 'none';
                            btn.style.borderRadius = '4px';
                            btn.style.padding = '6px 14px';
                            btn.style.fontWeight = 'bold';
                            btn.style.cursor = 'pointer';
                            btn.style.fontSize = '13px';
                            btn.style.marginLeft = '15px';
                            btn.style.whiteSpace = 'nowrap';
                            btn.style.display = 'inline-flex';
                            btn.style.alignItems = 'center';
                            btn.style.justifyContent = 'center';
                            btn.style.zIndex = '999999';
                            
                            btn.onmouseover = function() { btn.style.backgroundColor = '#B71C1C'; };
                            btn.onmouseout = function() { btn.style.backgroundColor = '#D32F2F'; };
                            
                            header.appendChild(btn);
                        }
                    } catch (e) {}
                }
                setTimeout(injectHeaderButton, 200);
                setTimeout(injectHeaderButton, 600);
            })();
        </script>
    """, height=0, width=0)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f'<div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">What is the occasion?</div>', unsafe_allow_html=True)
    
    # Retrieve dynamic occasions from global persistent session state (backed by SQLite), falling back to editable list
    occasions_list = st.session_state.get("occasions", []) or st.session_state.get("editable_occasions", [])

    occasion = None

    if not occasions_list:
        st.markdown("""
            <div style="background-color: #1e1e1e; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 20px; margin: 40px auto; max-width: 600px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); text-align: center;">
                <div style="color: #ffffff; font-size: 18px; font-weight: normal; line-height: 1.4; text-shadow: 1px 1px 2px #000;">No occasions exist in Notion yet. Please configure them in Wardrobe Configuration.</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # Dynamically determine column count (max 4 per row, but fewer if total items < 4 to keep it centered)
        num_items = len(occasions_list)
        col_count = min(num_items, 4)
        cols = st.columns(col_count)
        
        for idx, occ in enumerate(occasions_list):
            col_target = cols[idx % col_count]
            with col_target:
                img_base64 = None
                
                # 1. Check if user uploaded a reserve PNG for this occasion in Page 0.75
                uploaded_file = st.session_state.get("occasion_photos", {}).get(occ)
                if uploaded_file is not None:
                    try:
                        uploaded_file.seek(0)
                        img_bytes = uploaded_file.read()
                        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
                    except Exception:
                        img_base64 = None
                
                # 2. Fall back to local file paths if no session upload exists
                if not img_base64:
                    img_filename = occ.split()[0].lower() 
                    img_base64 = get_image_base64(f"Photos/{occ}.png") or get_image_base64(f"Photos/{img_filename}.png")
                
                if img_base64:
                    st.markdown(f'<img src="data:image/png;base64,{img_base64}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; pointer-events:none;">', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="width:100%; height:130px; background-color: #1e1e1e; border: 1px dashed rgba(255,255,255,0.2); border-radius:10px; margin-bottom:10px; display:flex; align-items:center; justify-content:center; color: #888; font-size: 12px; text-align: center; padding: 5px;">No Photo Uploaded</div>', unsafe_allow_html=True)
                
                if st.button(occ, use_container_width=True, key=f"occ_btn_{idx}"):
                    occasion = occ
                
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

    if occasion:
        loc_str = st.session_state.get("zip_code")
        lat, lng = loc_str.split(",")
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={OPENWEATHER_TOKEN}&units=imperial"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()
        
        temp = weather_data['main']['temp']
        humidity = weather_data['main']['humidity']
        feels_like = weather_data['main']['feels_like']
        condition = weather_data['weather'][0]['main']
        city_name = weather_data.get('name', 'your area')
        
        if condition == "Rain":
            guess = "Raining"
        elif feels_like < 60:
            guess = "Cold"
        else:
            guess = "Hot"
        
        st.session_state.outfit_data = {
            "occasion": occasion,
            "city": city_name,
            "temp": temp,
            "humidity": humidity,
            "bot_guess": guess,
            "final_weather": None,
            "outfit": None
        }
        st.session_state.page = "weather_check"
        st.rerun()

# ==========================================
# PAGE 1.5: MY CLOSET (Inventory Catalog & Drill-Down Editor)
# ==========================================
elif st.session_state.page == "my_closet":
    with st.sidebar:
        st.header("Navigation")
        if st.button("Back to Main Menu", use_container_width=True):
            st.session_state.page = "menu"
            st.rerun()
            
        st.header("Settings")
        st.write(f"**Persona:** {st.session_state.get('persona', 'Not Set')}")
        
        if st.button("Wardrobe Configuration", use_container_width=True):
            st.session_state.page = "config"
            st.rerun()
            
        if st.button("Change Location", use_container_width=True):
            st.session_state.page = "zip_map"
            st.rerun()

    # Scoped CSS for catalog grid, centered headers, and layout styling
    st.markdown("""
        <style>
        .block-container {
            max-width: 90% !important;
            padding-top: 2rem !important;
        }
        .closet-title {
            color: white;
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 5px;
            text-shadow: 2px 2px 3px #000;
        }
        .closet-subtitle {
            color: #ffffff !important;
            font-size: 17px !important;
            font-weight: bold !important;
            text-align: center !important;
            margin-bottom: 25px !important;
            text-shadow: 2px 2px 4px #000000 !important;
        }
        div[data-testid="stSelectbox"] label p, div[data-testid="stMultiSelect"] label p, div[data-testid="stTextInput"] label p {
            color: #ffffff !important;
            font-size: 16px !important;
            font-weight: bold !important;
            text-shadow: 2px 2px 4px #000000 !important;
        }
        .item-name-box {
            background-color: #111111 !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
            border-radius: 8px !important;
            padding: 8px 12px !important;
            margin-bottom: 10px !important;
            text-align: center !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.4);
        }
        .item-name-text {
            color: #ffffff !important;
            font-size: 16px !important;
            font-weight: bold !important;
            text-shadow: 1px 1px 2px #000;
            margin: 0 !important;
        }
        .catalog-img {
            width: 100% !important;
            height: 160px !important;
            object-fit: cover !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
            margin-bottom: 12px !important;
        }
        .detail-card {
            background-color: #161616;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.6);
            margin-top: 10px;
            margin-bottom: 30px;
        }
        span[data-baseweb="tag"] {
            background-color: #555555 !important;
            color: #ffffff !important;
        }
        span[data-baseweb="tag"] span {
            color: #ffffff !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Hard-refresh guard & Auto-hydrate: Check if session state configuration exists
    if not st.session_state.get("notion_token") or not st.session_state.get("database_id"):
        st.markdown('<div class="closet-title">My Closet Catalog</div>', unsafe_allow_html=True)
        st.markdown("""
            <div style="background-color: #1e1e1e; border: 1px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 30px; margin: 40px auto; max-width: 600px; text-align: center;">
                <div style="color: #ffffff; font-size: 18px; margin-bottom: 15px;">Session configuration missing after refresh. Please run through Wardrobe Configuration or re-enter credentials!</div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("Go to Wardrobe Configuration", use_container_width=True):
            st.session_state.page = "config"
            st.rerun()
    else:
        # Automatically re-hydrate options on hard refresh if session state options were wiped
        if "occasions" not in st.session_state or not st.session_state.get("occasions"):
            try:
                schema_res = requests.get(
                    f"https://api.notion.com/v1/databases/{st.session_state.database_id}",
                    headers={"Authorization": f"Bearer {st.session_state.notion_token}", "Notion-Version": "2022-06-28"}
                )
                if schema_res.status_code == 200:
                    db_props = schema_res.json().get("properties", {})
                    for prop_name, prop_data in db_props.items():
                        if "occasion" in prop_name.lower():
                            ptype = prop_data.get("type")
                            if ptype in ["select", "multi_select"]:
                                st.session_state.occasions = [opt["name"] for opt in prop_data.get(ptype, {}).get("options", [])]
                            break
            except Exception:
                pass

        # ----------------------------------------------------
        # DRILL-DOWN VIEW (When an item is selected for View/Edit)
        # ----------------------------------------------------
        if st.session_state.get("editing_item_id"):
            item_id = st.session_state.editing_item_id
            
            with st.spinner("Fetching item details and Notion schema..."):
                headers = {
                    "Authorization": f"Bearer {st.session_state.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                page_res = requests.get(f"https://api.notion.com/v1/pages/{item_id}", headers=headers)
                db_res = requests.get(f"https://api.notion.com/v1/databases/{st.session_state.database_id}", headers=headers)
                
            if page_res.status_code == 200 and db_res.status_code == 200:
                page_data = page_res.json()
                db_data = db_res.json()
                
                props = page_data.get("properties", {})
                db_properties = db_data.get("properties", {})
                
                # Extract Name
                item_name = "Unnamed Item"
                title_prop_key = None
                for p_name, p_val in props.items():
                    if p_val.get("type") == "title":
                        title_prop_key = p_name
                        arr = p_val.get("title", [])
                        if arr:
                            item_name = arr[0].get("plain_text", "Unnamed Item")
                        break
                
                # Extract Image URL
                img_url = None
                cover = page_data.get("cover")
                if cover:
                    if cover.get("type") == "external":
                        img_url = cover.get("external", {}).get("url")
                    elif cover.get("type") == "file":
                        img_url = cover.get("file", {}).get("url")
                if not img_url:
                    for p_name, p_val in props.items():
                        if p_val.get("type") == "files":
                            f_arr = p_val.get("files", [])
                            if f_arr:
                                f_obj = f_arr[0]
                                if f_obj.get("type") == "file":
                                    img_url = f_obj.get("file", {}).get("url")
                                elif f_obj.get("type") == "external":
                                    img_url = f_obj.get("external", {}).get("url")
                                break

                # Identify property keys
                type_key = next((k for k in props.keys() if 'type' in k.lower() or 'garment' in k.lower() or 'category' in k.lower()), None)
                occasion_key = next((k for k in props.keys() if 'occasion' in k.lower()), None)
                weather_key = next((k for k in props.keys() if 'weather' in k.lower()), None)

                # Extract current values from the page as lists
                def get_property_values(prop_key):
                    if prop_key not in props:
                        return []
                    p = props[prop_key]
                    ptype = p.get("type")
                    if ptype == "select":
                        sel = p.get("select")
                        return [sel.get("name")] if sel else []
                    elif ptype == "multi_select":
                        return [m.get("name") for m in p.get("multi_select", [])]
                    elif ptype == "rich_text":
                        rt = p.get("rich_text", [])
                        val = rt[0].get("plain_text") if rt else ""
                        return [v.strip().replace("'", "").replace('"', "") for v in val.replace("[", "").replace("]", "").split(",") if v.strip()]
                    return []

                current_type_list = get_property_values(type_key) if type_key else []
                current_type = current_type_list[0] if current_type_list else None
                
                current_occasions = get_property_values(occasion_key) if occasion_key else []
                current_weather = get_property_values(weather_key) if weather_key else []

                # Extract strict options from Notion DB Schema
                def extract_schema_options(schema_obj):
                    if not schema_obj:
                        return []
                    stype = schema_obj.get("type")
                    if stype == "select":
                        return [opt["name"] for opt in schema_obj.get("select", {}).get("options", [])]
                    elif stype == "multi_select":
                        return [opt["name"] for opt in schema_obj.get("multi_select", {}).get("options", [])]
                    return []

                notion_type_options = extract_schema_options(db_properties.get(type_key)) if type_key else []
                notion_occasion_options = extract_schema_options(db_properties.get(occasion_key)) if occasion_key else []
                notion_weather_options = extract_schema_options(db_properties.get(weather_key)) if weather_key else []

                # Perfectly centered header layout with the close button
                col_head_space1, col_head_main, col_head_close = st.columns([1, 8, 1])
                with col_head_main:
                    st.markdown(f'<div class="closet-title">Item Editor: {item_name}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="closet-subtitle">View and update wardrobe attributes directly synced with Notion.</div>', unsafe_allow_html=True)
                with col_head_close:
                    st.write("") 
                    if st.button("❌ Close", key="close_editor_red_x_btn", help="Close editor", use_container_width=True):
                        st.session_state.editing_item_id = None
                        st.rerun()

                # Two-column layout for the detail view
                detail_col1, detail_col2 = st.columns([1, 1.5], gap="large")
                
                with detail_col1:
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    if img_url:
                        st.markdown(f'<img src="{img_url}" style="width:100%; height:280px; object-fit:cover; border-radius:10px; border:1px solid rgba(255,255,255,0.2);">', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="width:100%; height:280px; background:#111; display:flex; align-items:center; justify-content:center; color:#888; border-radius:10px;">No Image Available</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                with detail_col2:
                    st.markdown('<div class="detail-card">', unsafe_allow_html=True)
                    
                    with st.form(key=f"edit_form_{item_id}"):
                        st.markdown("### **Edit Attributes**")
                        
                        new_name = st.text_input("Item Name", value=item_name)
                        
                        # Garment Type Dropdown (Single Select)
                        if notion_type_options:
                            if current_type not in notion_type_options and current_type:
                                notion_type_options.append(current_type)
                            type_idx = notion_type_options.index(current_type) if current_type in notion_type_options else 0
                            new_type = st.selectbox("Garment Type", notion_type_options, index=type_idx)
                        else:
                            new_type = st.selectbox("Garment Type", [current_type] if current_type else ["Uncategorized"])

                        # Occasion Multi-select
                        if notion_occasion_options:
                            valid_occ_defaults = [o for o in current_occasions if o in notion_occasion_options]
                            new_occasions = st.multiselect("Occasion", notion_occasion_options, default=valid_occ_defaults)
                        else:
                            new_occasions = st.multiselect("Occasion", current_occasions, default=current_occasions)

                        # Weather Suitability Multi-select
                        if notion_weather_options:
                            valid_wea_defaults = [w for w in current_weather if w in notion_weather_options]
                            new_weather = st.multiselect("Weather Suitability", notion_weather_options, default=valid_wea_defaults)
                        else:
                            new_weather = st.multiselect("Weather Suitability", current_weather, default=current_weather)

                        st.write("")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            submit_button = st.form_submit_button("Save Changes", use_container_width=True)
                        with col_cancel:
                            cancel_button = st.form_submit_button("Cancel", use_container_width=True)

                        if submit_button:
                            patch_properties = {}
                            if title_prop_key:
                                patch_properties[title_prop_key] = {"title": [{"text": {"content": new_name}}]}
                            if type_key:
                                patch_properties[type_key] = {"select": {"name": new_type}}
                            if occasion_key:
                                occ_schema_type = db_properties.get(occasion_key, {}).get("type")
                                if occ_schema_type == "select":
                                    patch_properties[occasion_key] = {"select": {"name": new_occasions[0] if new_occasions else None}}
                                else:
                                    patch_properties[occasion_key] = {"multi_select": [{"name": o} for o in new_occasions]}
                            if weather_key:
                                wea_schema_type = db_properties.get(weather_key, {}).get("type")
                                if wea_schema_type == "select":
                                    patch_properties[weather_key] = {"select": {"name": new_weather[0] if new_weather else None}}
                                else:
                                    patch_properties[weather_key] = {"multi_select": [{"name": w} for w in new_weather]}

                            patch_url = f"https://api.notion.com/v1/pages/{item_id}"
                            patch_headers = {
                                "Authorization": f"Bearer {st.session_state.notion_token}",
                                "Notion-Version": "2022-06-28",
                                "Content-Type": "application/json"
                            }
                            update_res = requests.patch(patch_url, json={"properties": patch_properties}, headers=patch_headers)
                            
                            if update_res.status_code == 200:
                                st.success("Successfully updated item in Notion!")
                                st.session_state.editing_item_id = None
                                st.rerun()
                            else:
                                st.error(f"Failed to update Notion: {update_res.status_code} - {update_res.text}")

                        if cancel_button:
                            st.session_state.editing_item_id = None
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.error("Failed to load item details or schema from Notion.")
                if st.button("Back to Catalog"):
                    st.session_state.editing_item_id = None
                    st.rerun()

        # ----------------------------------------------------
        # MAIN CATALOG GRID VIEW
        # ----------------------------------------------------
        else:
            st.markdown('<div class="closet-title">My Closet Catalog</div>', unsafe_allow_html=True)
            st.markdown('<div class="closet-subtitle">Proof-of-concept database query: pulling all wardrobe items directly from Notion.</div>', unsafe_allow_html=True)

            with st.spinner("Fetching entire wardrobe database from Notion..."):
                url = f"https://api.notion.com/v1/databases/{st.session_state.database_id}/query"
                headers = {
                    "Authorization": f"Bearer {st.session_state.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                response = requests.post(url, json={}, headers=headers)
                
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    
                    if not results:
                        st.markdown("""
                            <div style="background-color: #1e1e1e; border: 1px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 20px; margin: 40px auto; max-width: 600px; text-align: center;">
                                <div style="color: #ffffff; font-size: 18px;">Your Notion database is currently empty. Add some items to see them here!</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        processed_items = []
                        available_types = set()
                        
                        for page in results:
                            props = page.get("properties", {})
                            
                            item_name = "Unnamed Item"
                            for prop_name, prop_val in props.items():
                                if prop_val.get("type") == "title":
                                    title_arr = prop_val.get("title", [])
                                    if title_arr:
                                        item_name = title_arr[0].get("plain_text", "Unnamed Item")
                                    break
                            
                            img_url = None
                            cover = page.get("cover")
                            if cover:
                                if cover.get("type") == "external":
                                    img_url = cover.get("external", {}).get("url")
                                elif cover.get("type") == "file":
                                    img_url = cover.get("file", {}).get("url")
                            
                            if not img_url:
                                for prop_name, prop_val in props.items():
                                    if prop_val.get("type") == "files":
                                        files_arr = prop_val.get("files", [])
                                        if files_arr:
                                            file_obj = files_arr[0]
                                            if file_obj.get("type") == "file":
                                                img_url = file_obj.get("file", {}).get("url")
                                            elif file_obj.get("type") == "external":
                                                img_url = file_obj.get("external", {}).get("url")
                                            break

                            item_type = "Uncategorized"
                            target_prop_key = None
                            for prop_name in props.keys():
                                p_lower = prop_name.lower()
                                if ('type' in p_lower or 'garment' in p_lower or 'category' in p_lower) and 'weather' not in p_lower:
                                    target_prop_key = prop_name
                                    break
                            
                            if not target_prop_key:
                                for prop_name, prop_val in props.items():
                                    ptype = prop_val.get("type")
                                    if ptype in ["select", "multi_select"] and 'weather' not in prop_name.lower():
                                        target_prop_key = prop_name
                                        break
                            
                            if target_prop_key:
                                prop_val = props[target_prop_key]
                                ptype = prop_val.get("type")
                                if ptype == "select":
                                    sel = prop_val.get("select")
                                    if sel and sel.get("name"):
                                        item_type = sel.get("name")
                                        available_types.add(item_type)
                                elif ptype == "multi_select":
                                    m_arr = prop_val.get("multi_select", [])
                                    if m_arr:
                                        item_type = m_arr[0].get("name", "Uncategorized")
                                        for m in m_arr:
                                            available_types.add(m.get("name"))

                            processed_items.append({
                                "id": page.get("id"),
                                "name": item_name,
                                "img_url": img_url,
                                "type": item_type
                            })

                        priority_order = ["Top", "Shirt", "Pants", "Shoes", "Underwear"]
                        
                        def get_priority_rank(item_type):
                            for idx, p in enumerate(priority_order):
                                if p.lower() in item_type.lower():
                                    return idx
                            return 999

                        sorted_types = sorted(list(available_types), key=get_priority_rank)
                        filter_options = ["All Types"] + sorted_types
                        
                        col_filter, col_spacer = st.columns([2, 2])
                        with col_filter:
                            selected_type = st.selectbox("Filter by Garment Type", filter_options)

                        if selected_type != "All Types":
                            filtered_items = [item for item in processed_items if item["type"] == selected_type or selected_type in item["type"]]
                        else:
                            if "catalog_shuffled_items" not in st.session_state or st.session_state.get("last_filter") != selected_type:
                                shuffled = list(processed_items)
                                random.shuffle(shuffled)
                                st.session_state.catalog_shuffled_items = shuffled
                                st.session_state.last_filter = selected_type
                            filtered_items = st.session_state.catalog_shuffled_items

                        st.write("")

                        if not filtered_items:
                            st.info(f"No items found for garment type: '{selected_type}'")
                        else:
                            # ALWAYS use 4 columns per row to maintain fixed card width and grid alignment
                            cols_per_row = 4
                            rows = [filtered_items[i:i + cols_per_row] for i in range(0, len(filtered_items), cols_per_row)]
                            
                            for row_items in rows:
                                cols = st.columns(cols_per_row)
                                for idx in range(cols_per_row):
                                    with cols[idx]:
                                        if idx < len(row_items):
                                            item = row_items[idx]
                                            st.markdown(f'''
                                                <div class="item-name-box">
                                                    <div class="item-name-text">{item["name"]}</div>
                                                </div>
                                            ''', unsafe_allow_html=True)
                                            
                                            if item["img_url"]:
                                                st.markdown(f'<img src="{item["img_url"]}" class="catalog-img">', unsafe_allow_html=True)
                                            else:
                                                st.markdown('<div style="width:100%; height:160px; background-color: #111; border: 1px dashed rgba(255,255,255,0.3); border-radius:8px; display:flex; align-items:center; justify-content:center; color: #888; font-size: 13px; margin-bottom:12px;">No Image Found</div>', unsafe_allow_html=True)
                                            
                                            if st.button("View / Edit", key=f"view_item_{item['id']}", use_container_width=True):
                                                st.session_state.editing_item_id = item['id']
                                                st.rerun()
                                        else:
                                            # Empty placeholder column to preserve 4-wide grid spacing for trailing rows
                                            st.write("")
                else:
                    st.error(f"Failed to fetch Notion database items: {response.status_code} - {response.text}")

# ==========================================
# PAGE 1.75: ADD CLOTHING (Notion Form Link)
# ==========================================
elif st.session_state.page == "add_clothing":
    # High-contrast title
    st.markdown('<div style="text-align: center; font-size: 28px; font-weight: bold; margin-bottom: 25px; color: white; text-shadow: 2px 2px 6px #000;">Add New Clothing Item</div>', unsafe_allow_html=True)
    
    # Ensure form_url is pulled from session or database if missing
    if not st.session_state.get("form_url") and st.session_state.get("session_id"):
        conn = sqlite3.connect('wardrobe.db')
        c = conn.cursor()
        c.execute("SELECT form_url FROM users WHERE session_id=?", (st.session_state.session_id,))
        row = c.fetchone()
        conn.close()
        if row and row[0]:
            st.session_state.form_url = row[0]

    form_url = st.session_state.get("form_url", "")
    
    if form_url:
        # Layer 1: Widest (Top) - Instruction Box (~650px)
        st.markdown(f"""
            <div style="max-width: 650px; margin: 0 auto 15px auto;">
                <div style="background-color: #000000; border: 1px solid rgba(255,255,255,0.25); border-radius: 12px; padding: 25px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.8);">
                    <span style="color: #ffffff; font-size: 17px; font-weight: bold; line-height: 1.5;">
                        Click below to open your Notion form in a new tab. Once submitted, your items will sync directly to your database.
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Layer 2: Medium (Middle) - Notion Form Button (~450px width)
        st.markdown(f"""
            <div style="max-width: 450px; margin: 0 auto 12px auto;">
                <a href="{form_url}" target="_blank" style="
                    background-color: #1a1a1a;
                    color: #ffffff;
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 18px;
                    padding: 16px 20px;
                    width: 100%;
                    display: block;
                    text-align: center;
                    text-decoration: none;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.5);
                    transition: background-color 0.2s ease;
                " onmouseover="this.style.backgroundColor='#333333'" onmouseout="this.style.backgroundColor='#1a1a1a'">
                    🌐 Open Notion Add-Clothing Form
                </a>
            </div>
        """, unsafe_allow_html=True)
        
        # Layer 3: Narrowest (Bottom) - Back to Menu Button (~250px width)
        st.markdown("""
            <style>
                /* Target only the back button container for a narrow stepped width */
                div.stButton {
                    max-width: 250px;
                    margin: 0 auto;
                }
                div.stButton > button {
                    background-color: #1a1a1a !important;
                    color: #ffffff !important;
                    border: 1px solid rgba(255, 255, 255, 0.3) !important;
                    border-radius: 8px !important;
                    font-weight: 600 !important;
                    font-size: 14px !important;
                    padding: 0.6rem 1rem !important;
                    width: 100% !important;
                    opacity: 1 !important;
                }
                div.stButton > button:hover {
                    background-color: #333333 !important;
                    border-color: rgba(255, 255, 255, 0.7) !important;
                    color: #ffffff !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        if st.button("⬅️ Back to Menu", use_container_width=True):
            st.session_state.page = "menu"
            st.rerun()
                
    else:
        st.error("No Notion Form URL was found in your session. Please re-upload your credentials file.")
        if st.button("Go to Setup / Upload Credentials", use_container_width=True):
            st.session_state.page = "welcome"
            st.rerun()

# ==========================================
# PAGE 2: WEATHER AGREEMENT
# ==========================================
elif st.session_state.page == "weather_check":
    # Gracefully redirect to menu if the session payload was wiped by a page refresh
    if "outfit_data" not in st.session_state or not st.session_state.outfit_data:
        st.warning("Weather session expired or reset. Returning to menu...")
        st.session_state.page = "menu"
        st.rerun()

    data = st.session_state.outfit_data
    
    city_display = data.get("city", "Unknown")
    state_display = data.get("state", "")
    
    # Format cleanly as "City, ST" (e.g., "Center, CO")
    location_str = f"{city_display}, {state_display}" if state_display else city_display
    
    st.markdown(f'<div class="weather-prompt" style="color: white;">Forecast for {location_str}: {data.get("temp", "--")}°F<br>Humidity: {data.get("humidity", "--")}%</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align: center; font-size: 20px; color: white; text-shadow: 2px 2px 4px #000;">I think you should classify this as <b>{data.get("bot_guess", "Normal")}</b>.<br>Do you agree?</div>', unsafe_allow_html=True)
    st.write("")
    st.write("")
    
    st.markdown("""
    <style>
        div[class*="st-key-btn_yes"] button { background-color: #28a745 !important; color: white !important; border: 1px solid #28a745 !important; }
        div[class*="st-key-btn_no"] button { background-color: #dc3545 !important; color: white !important; border: 1px solid #dc3545 !important; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Yes", key="btn_yes", use_container_width=True):
            data["final_weather"] = data.get("bot_guess", "")
            st.session_state.page = "fetch_outfit"
            st.rerun()
        st.write("")
        if st.button("No", key="btn_no", use_container_width=True):
            st.session_state.page = "manual_weather"
            st.rerun()

# ==========================================
# PAGE 3: MANUAL WEATHER
# ==========================================
elif st.session_state.page == "manual_weather":
    data = st.session_state.outfit_data
    wrong_guess = data["bot_guess"]
    all_options = ["Hot", "Cold", "Raining"]
    available_options = [opt for opt in all_options if opt != wrong_guess]
    
    st.markdown('<div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">Pick the correct weather:</div>', unsafe_allow_html=True)
    
    cols = st.columns(len(available_options))
    for i, option in enumerate(available_options):
        with cols[i]:
            if st.button(option, use_container_width=True): 
                data["final_weather"] = option
                st.session_state.page = "fetch_outfit"
                st.rerun()

# ==========================================
# PAGE 4: FETCH AND DISPLAY OUTFIT
# ==========================================
elif st.session_state.page == "fetch_outfit":
    data = st.session_state.outfit_data
    
    # --- PULL STRICTLY FROM 0.75 CONFIG STATE (NO FALLBACK) ---
    wear_order = st.session_state.get("editable_garment_types", [])

    if not wear_order:
        st.markdown("""
            <div style="background-color: #1e1e1e; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 20px; margin: 40px auto; max-width: 600px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); text-align: center;">
                <div style="color: #ffffff; font-size: 18px; font-weight: normal; line-height: 1.4; text-shadow: 1px 1px 2px #000; margin-bottom: 20px;">No garment types exist in Notion yet. Please configure them in Wardrobe Configuration.</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Escape hatch button to break the soft lock
        col_center1, col_center2, col_center3 = st.columns([1, 2, 1])
        with col_center2:
            if st.button("Wardrobe Configuration", use_container_width=True, type="primary"):
                st.session_state.page = "config"
                st.rerun()
    else:
        if data["outfit"] is None:
            with st.spinner("Fetching clothes from Notion..."):
                url = f"https://api.notion.com/v1/databases/{st.session_state.database_id}/query"
                headers = {
                    "Authorization": f"Bearer {st.session_state.notion_token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(url, headers=headers)
                notion_data = response.json()
                
                # Initialize outfit slots in the exact priority order defined in 0.75
                outfit_slots = {slot: [] for slot in wear_order}

                if response.status_code == 200:
                    for item in notion_data.get("results", []):
                        try:
                            name = item["properties"]["Name"]["title"][0]["text"]["content"]
                            g_type = item["properties"]["Garment Type"]["select"]["name"]
                            occasions = [opt["name"] for opt in item["properties"]["Occasion"]["multi_select"]]
                            weathers = [opt["name"] for opt in item["properties"]["Weather"]["multi_select"]]
                            
                            image_url = None
                            files = item["properties"].get("Image", {}).get("files", [])
                            if files:
                                if files[0].get("type") == "file":
                                    image_url = files[0].get("file", {}).get("url")
                                elif files[0].get("type") == "external":
                                    image_url = files[0].get("external", {}).get("url")

                            if data["occasion"] in occasions and data["final_weather"] in weathers:
                                if g_type in outfit_slots:
                                    outfit_slots[g_type].append({"name": name, "image": image_url})
                        except (IndexError, KeyError, TypeError):
                            pass
                    data["outfit"] = outfit_slots
                    st.session_state.current_outfit = None
                    st.session_state.carousel_idx = 0
                else:
                    st.error(f"Error connecting to Notion: {response.status_code}")

        st.markdown(f'<div style="color: white; text-shadow: 2px 2px 4px #000; font-size: 20px; margin-bottom: 20px;"><b>Occasion:</b> {data["occasion"]} | <b>Weather:</b> {data["final_weather"]} in {data["city"]} ({data["temp"]}°F / {data["humidity"]}%)</div>', unsafe_allow_html=True)
        
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🔄 Shuffle Outfit", use_container_width=True, type="primary"):
                placeholder = st.empty()
                placeholder.markdown(
                    """
                    <div style="display: flex; justify-content: center; align-items: center; gap: 10px; color: white; font-size: 20px; font-weight: bold; margin-top: 20px;">
                        <div style="border: 4px solid rgba(255,255,255,0.3); border-top: 4px solid white; border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite;"></div>
                        Finding your fashion...
                    </div>
                    <style>
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    </style>
                    """,
                    unsafe_allow_html=True
                )
                time.sleep(1.5)
                placeholder.empty()
                st.session_state.current_outfit = None
                st.session_state.carousel_idx = 0
                st.rerun()
        with col_b:
            if st.button("❌ Start Over", use_container_width=True):
                st.session_state.current_outfit = None
                st.session_state.carousel_idx = 0
                reset_app()

        st.write("---")

        # --- LOCK CHOSEN ITEMS IN SESSION STATE USING PRIORITY ORDER ---
        if "current_outfit" not in st.session_state or st.session_state.current_outfit is None:
            outfit = data["outfit"]
            resolved = {}
            for slot in wear_order:
                items = outfit.get(slot, [])
                if items:
                    if slot.lower() == "accessory" and len(items) > 1:
                        resolved[slot] = random.sample(items, min(2, len(items)))
                    else:
                        resolved[slot] = [random.choice(items)]
                else:
                    resolved[slot] = []
            st.session_state.current_outfit = resolved

        if "carousel_idx" not in st.session_state:
            st.session_state.carousel_idx = 0

        resolved_outfit = st.session_state.current_outfit

        # --- CUSTOM CSS: SOLID OPAQUE CARDS + MOBILE STACKING ---
        st.markdown("""
            <style>
            div.stButton > button {
                background-color: #1a1a1a !important;
                color: white !important;
                border: 1px solid rgba(255, 255, 255, 0.3) !important;
                font-weight: bold !important;
                border-radius: 8px !important;
                height: 42px !important;
            }
            div.stButton > button:hover {
                background-color: #333333 !important;
                border-color: #8ab4f8 !important;
                color: white !important;
            }

            @media screen and (max-width: 600px) {
                div[data-testid="stHorizontalBlock"]:has(.mobile-preview-marker) {
                    flex-direction: column-reverse !important;
                }
            }
            </style>
        """, unsafe_allow_html=True)

        col_text, col_carousel = st.columns([1, 1], gap="large")

        with col_text:
            st.markdown('<div style="color: white; font-size: 22px; font-weight: bold; margin-bottom: 10px; text-shadow: 1px 1px 2px #000;">Clothing Breakdown</div>', unsafe_allow_html=True)
            
            with st.container():
                box_html = '<div style="background: #121212; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); min-height: 533px;">'
                for slot in wear_order:
                    item_list = resolved_outfit.get(slot, [])
                    box_html += f'<div style="margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">'
                    box_html += f'<span style="color: #8ab4f8; font-size: 13px; font-weight: bold; text-transform: uppercase;">{slot}:</span><br>'
                    if item_list:
                        for item in item_list:
                            box_html += f'<span style="color: white; font-size: 14px; margin-left: 10px;">• {item["name"]}</span><br>'
                    else:
                        box_html += f'<span style="color: #888; font-size: 13px; margin-left: 10px; font-style: italic;">No items found</span>'
                    box_html += '</div>'
                box_html += '</div>'
                st.markdown(box_html, unsafe_allow_html=True)

        with col_carousel:
            ordered_slides = []
            for slot in wear_order:
                for item in resolved_outfit.get(slot, []):
                    if item.get("image"):
                        ordered_slides.append((slot, item["name"], item["image"]))

            if ordered_slides:
                total_slides = len(ordered_slides)
                st.session_state.carousel_idx = st.session_state.carousel_idx % total_slides
                curr_slot, curr_name, curr_img = ordered_slides[st.session_state.carousel_idx]
                
                header_html = f"""
                    <div class="mobile-preview-marker" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div style="color: white; font-size: 22px; font-weight: bold; text-shadow: 1px 1px 2px #000;">Outfit Preview</div>
                        <div style="color: white; font-weight: bold; font-size: 15px; text-shadow: 1px 1px 2px #000;">{st.session_state.carousel_idx + 1} / {total_slides}</div>
                    </div>
                """
                st.markdown(header_html, unsafe_allow_html=True)
                
                carousel_card = f"""
                    <div style="background: #121212; border: 1px solid rgba(255,255,255,0.2); border-radius: 12px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.5); text-align: center; min-height: 533px; display: flex; flex-direction: column; justify-content: space-between;">
                        <div>
                            <div style="color: #8ab4f8; font-size: 15px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; text-shadow: 1px 1px 2px #000;">{curr_slot}</div>
                            <img src="{curr_img}" style="width: 100%; height: 420px; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);">
                            <div style="color: white; font-size: 13px; font-weight: 500; margin-top: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{curr_name}</div>
                        </div>
                    </div>
                """
                st.markdown(carousel_card, unsafe_allow_html=True)
                
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                
                nav_prev, nav_spacer, nav_next = st.columns([1, 0.4, 1])
                with nav_prev:
                    if st.button("← Previous", use_container_width=True, key="btn_prev_img"):
                        st.session_state.carousel_idx = (st.session_state.carousel_idx - 1) % total_slides
                        st.rerun()
                with nav_next:
                    if st.button("Next →", use_container_width=True, key="btn_next_img"):
                        st.session_state.carousel_idx = (st.session_state.carousel_idx + 1) % total_slides
                        st.rerun()
                        
                components.html("""
                    <script>
                    (function() {
                        const doc = window.parent.document;
                        let touchstartX = 0;
                        let touchstartY = 0;
                        let touchendX = 0;
                        let touchendY = 0;

                        doc.addEventListener('touchstart', e => {
                            touchstartX = e.changedTouches[0].screenX;
                            touchstartY = e.changedTouches[0].screenY;
                        }, {passive: true});

                        doc.addEventListener('touchend', e => {
                            touchendX = e.changedTouches[0].screenX;
                            touchendY = e.changedTouches[0].screenY;
                            
                            let diffX = touchendX - touchstartX;
                            let diffY = touchendY - touchstartY;

                            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                                const buttons = Array.from(doc.querySelectorAll('button'));
                                if (diffX < 0) {
                                    const nextBtn = buttons.find(b => b.innerText.includes('Next') || b.innerText.includes('→'));
                                    if (nextBtn) nextBtn.click();
                                } else {
                                    const prevBtn = buttons.find(b => b.innerText.includes('Previous') || b.innerText.includes('←'));
                                    if (prevBtn) prevBtn.click();
                                }
                            }
                        }, {passive: true});
                    })();
                    </script>
                """, height=0, width=0)
            else:
                st.info("No item photos available for this generated outfit combination.")






































































































































































