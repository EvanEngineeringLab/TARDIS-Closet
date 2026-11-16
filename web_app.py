
import streamlit as st
import requests
import random
import time
import base64
import sqlite3
import uuid
import streamlit.components.v1 as components

# --- SECRETS SETUP ---
OPENWEATHER_TOKEN = st.secrets["OPENWEATHER_TOKEN"]

# --- DATABASE SETUP (SQLite) ---
def init_db():
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (session_id TEXT PRIMARY KEY, zip_code TEXT, notion_token TEXT, database_id TEXT)''')
    conn.commit()
    conn.close()


def get_user_data(session_id):
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    c.execute(
        "SELECT zip_code, notion_token, database_id FROM users WHERE session_id=?",
        (session_id,)
    )
    row = c.fetchone()
    conn.close()

    if row:
        return {
            "zip_code": row[0],
            "notion_token": row[1],
            "database_id": row[2]
        }
    return None


def save_user_data(session_id, zip_code, notion_token, database_id):
    conn = sqlite3.connect('wardrobe.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (session_id, zip_code, notion_token, database_id) VALUES (?, ?, ?, ?)",
        (session_id, zip_code, notion_token, database_id)
    )
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


# Load background and TARDIS icon
bg_b64 = get_image_base64("Photos/background.png")
tardis_b64 = get_image_base64("Photos/TARDIS_icon.png")

# Set the page title and layout
st.set_page_config(
    page_title="TARDIS Closet",
    page_icon="Photos/TARDIS_icon.png",
    layout="centered"
)

# Force the TARDIS icon for the PWA/Home Screen shortcut
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
    .stApp {{
        background-image: url("data:image/png;base64,{bg_b64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}

    .title-container {{
        text-align: center;
        margin-bottom: 30px;
    }}

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

    .weather-prompt {{
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
        text-shadow: 2px 2px 4px #000;
    }}

    [data-testid="StyledFullScreenButton"],
    button[title="View fullscreen"] {{
        display: none !important;
    }}

    [data-testid="column"]:hover {{
        background-color: transparent !important;
    }}

    [data-testid="stForm"] {{
        background-color: rgba(0, 0, 0, 0.85) !important;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #555;
    }}

    [data-testid="stForm"] * {{
        color: white !important;
    }}

    [data-testid="stForm"] h3 {{
        font-weight: 700 !important;
    }}

    [data-testid="stTextInput"] input {{
        background-color: rgba(50, 50, 50, 0.9) !important;
        color: white !important;
        border: 1px solid #777 !important;
    }}

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
st.markdown(
    f'<div class="title-container" style="display: flex; justify-content: center; align-items: center; gap: 15px;">'
    f'<img src="data:image/png;base64,{tardis_b64}" style="height: 120px;">'
    f'<h1 style="margin: 0; color: white; text-shadow: 2px 2px 4px #000;">TARDIS Closet</h1>'
    f'</div>',
    unsafe_allow_html=True
)

# --- URL SESSION MANAGEMENT ---
query_params = st.query_params
url_session_id = query_params.get("user_id", None)

if "session_id" not in st.session_state:
    if url_session_id:
        st.session_state.session_id = url_session_id
    else:
        new_id = str(uuid.uuid4())
        st.session_state.session_id = new_id
        st.query_params["user_id"] = new_id

if "page" not in st.session_state:
    user_data = get_user_data(st.session_state.session_id)

    if user_data:
        st.session_state.zip_code = user_data["zip_code"]
        st.session_state.notion_token = user_data["notion_token"]
        st.session_state.database_id = user_data["database_id"]
        st.session_state.page = "menu"
    else:
        st.session_state.page = "welcome"
        st.session_state.zip_code = ""
        st.session_state.notion_token = ""
        st.session_state.database_id = ""

if "outfit_data" not in st.session_state:
    st.session_state.outfit_data = {}


# ==========================================
# PAGE 0: WELCOME SCREEN
# ==========================================
if st.session_state.page == "welcome":

    st.markdown(
        '<div style="text-align: center; font-size: 20px; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">Welcome! Please set up your profile to begin.</div>',
        unsafe_allow_html=True
    )

    with st.form("setup_form"):
        st.subheader("Location")
        zip_input = st.text_input("Enter your ZIP code:")

        st.subheader("Notion Integration")
        notion_input = st.text_input("Notion API Token:", type="password")
        db_input = st.text_input("Notion Database ID:")

        submitted = st.form_submit_button(
            "Start",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            if zip_input.strip() and notion_input.strip() and db_input.strip():
                save_user_data(
                    st.session_state.session_id,
                    zip_input.strip(),
                    notion_input.strip(),
                    db_input.strip()
                )

                st.session_state.zip_code = zip_input.strip()
                st.session_state.notion_token = notion_input.strip()
                st.session_state.database_id = db_input.strip()

                st.session_state.page = "menu"
                st.rerun()
            else:
                st.error("Please fill out all fields.")


# ==========================================
# PAGE 1: THE MENU
# ==========================================
elif st.session_state.page == "menu":

    with st.sidebar:
        st.header("Settings")

        new_zip = st.text_input(
            "Update ZIP code:",
            value=st.session_state.zip_code
        )

        if new_zip != st.session_state.zip_code:
            st.session_state.zip_code = new_zip.strip()

            save_user_data(
                st.session_state.session_id,
                st.session_state.zip_code,
                st.session_state.notion_token,
                st.session_state.database_id
            )
            st.rerun()

        st.write("---")

        if st.button("Log Out / Reset Profile", use_container_width=True):
            conn = sqlite3.connect('wardrobe.db')
            c = conn.cursor()
            c.execute(
                "DELETE FROM users WHERE session_id=?",
                (st.session_state.session_id,)
            )
            conn.commit()
            conn.close()

            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    st.markdown(
        '<div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">What is the occasion?</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)
    occasion = None

    img_casual = get_image_base64("Photos/Casual.png")
    img_date = get_image_base64("Photos/Date.png")
    img_school = get_image_base64("Photos/School.png")
    img_interview = get_image_base64("Photos/Interview.png")
    img_work = get_image_base64("Photos/Work.png")
    img_pres = get_image_base64("Photos/Presentation.png")
    img_formal = get_image_base64("Photos/Formal.png")
    img_cosplay = get_image_base64("Photos/Cosplay.png")

    with col1:
        if img_casual:
            st.markdown(
                f'<img src="data:image/png;base64,{img_casual}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Casual", use_container_width=True):
            occasion = "Casual"

        if img_date:
            st.markdown(
                f'<img src="data:image/png;base64,{img_date}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; margin-top:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Date", use_container_width=True):
            occasion = "Date"

    with col2:
        if img_school:
            st.markdown(
                f'<img src="data:image/png;base64,{img_school}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("School", use_container_width=True):
            occasion = "School"

        if img_interview:
            st.markdown(
                f'<img src="data:image/png;base64,{img_interview}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; margin-top:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Interview", use_container_width=True):
            occasion = "Job Interview"

    with col3:
        if img_work:
            st.markdown(
                f'<img src="data:image/png;base64,{img_work}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Work", use_container_width=True):
            occasion = "Work"

        if img_pres:
            st.markdown(
                f'<img src="data:image/png;base64,{img_pres}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; margin-top:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Presentation", use_container_width=True):
            occasion = "Presentation"

    with col4:
        if img_formal:
            st.markdown(
                f'<img src="data:image/png;base64,{img_formal}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Formal", use_container_width=True):
            occasion = "Formal Event"

        if img_cosplay:
            st.markdown(
                f'<img src="data:image/png;base64,{img_cosplay}" style="width:100%; height:130px; object-fit:cover; border-radius:10px; margin-bottom:10px; margin-top:10px; pointer-events:none;">',
                unsafe_allow_html=True
            )
        if st.button("Cosplay", use_container_width=True):
            occasion = "Cosplay"

    if occasion:
        weather_url = (
            f"https://api.openweathermap.org/data/2.5/weather?"
            f"zip={st.session_state.zip_code},US&appid={OPENWEATHER_TOKEN}&units=imperial"
        )

        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        if weather_response.status_code == 200:
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
        else:
            st.error("Could not fetch weather. Check your ZIP code.")


# ==========================================
# PAGE 2: WEATHER AGREEMENT
# ==========================================
elif st.session_state.page == "weather_check":

    data = st.session_state.outfit_data

    st.markdown(
        f'<div class="weather-prompt" style="color: white;">Forecast for {data["city"]}: {data["temp"]}°F<br>Humidity: {data["humidity"]}%</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        f'<div style="text-align: center; font-size: 20px; color: white; text-shadow: 2px 2px 4px #000;">I think you should classify this as <b>{data["bot_guess"]}</b>.<br>Do you agree?</div>',
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    st.markdown("""
    <style>
        div[class*="st-key-btn_yes"] button {
            background-color: #28a745 !important;
            color: white !important;
            border: 1px solid #28a745 !important;
        }
        div[class*="st-key-btn_no"] button {
            background-color: #dc3545 !important;
            color: white !important;
            border: 1px solid #dc3545 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button("Yes", key="btn_yes", use_container_width=True):
            data["final_weather"] = data["bot_guess"]
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
    available_options = [
        opt for opt in all_options if opt != wrong_guess
    ]

    st.markdown(
        '<div style="text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; color: white; text-shadow: 2px 2px 4px #000;">Pick the correct weather:</div>',
        unsafe_allow_html=True
    )

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

    if data["outfit"] is None:

        with st.spinner("Fetching clothes from Notion..."):

            url = (
                f"https://api.notion.com/v1/databases/"
                f"{st.session_state.database_id}/query"
            )

            headers = {
                "Authorization": f"Bearer {st.session_state.notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }

            response = requests.post(url, headers=headers)

            # --- IMPROVED NOTION ERROR REPORTING ---
            if response.status_code != 200:
                st.error(f"Notion Error: {response.status_code}")

                try:
                    error_data = response.json()
                    st.write("Error Code:", error_data.get("code"))
                    st.write("Error Message:", error_data.get("message"))
                except ValueError:
                    st.write(response.text)

                st.stop()

            notion_data = response.json()

            outfit_slots = {
                "Undershirt": [],
                "Overshirt": [],
                "Pants": [],
                "Shoes": [],
                "Mid-Layer": [],
                "Headwear": [],
                "Outerwear": [],
                "Accessory": []
            }

            for item in notion_data.get("results", []):
                try:
                    name = item["properties"]["Name"]["title"][0]["text"]["content"]

                    g_type = item["properties"]["Garment Type"]["select"]["name"]

                    occasions = [
                        opt["name"]
                        for opt in item["properties"]["Occasion"]["multi_select"]
                    ]

                    weathers = [
                        opt["name"]
                        for opt in item["properties"]["Weather"]["multi_select"]
                    ]

                    image_url = None

                    files = item["properties"].get("Image", {}).get("files", [])

                    if files:
                        if files[0].get("type") == "file":
                            image_url = files[0].get("file", {}).get("url")
                        elif files[0].get("type") == "external":
                            image_url = files[0].get("external", {}).get("url")

                    if (
                        data["occasion"] in occasions
                        and data["final_weather"] in weathers
                    ):
                        if g_type in outfit_slots:
                            outfit_slots[g_type].append({
                                "name": name,
                                "image": image_url
                            })

                except (IndexError, KeyError, TypeError):
                    pass

            data["outfit"] = outfit_slots

    st.markdown(
        f'<div style="color: white; text-shadow: 2px 2px 4px #000; font-size: 20px; margin-bottom: 20px;"><b>Occasion:</b> {data["occasion"]} | <b>Weather:</b> {data["final_weather"]} in {data["city"]} ({data["temp"]}°F / {data["humidity"]}%)</div>',
        unsafe_allow_html=True
    )

    col_a, col_b = st.columns([1, 1])

    with col_a:
        if st.button(
            "🔄 Shuffle Outfit",
            use_container_width=True,
            type="primary"
        ):
            with st.spinner("Finding your fashion..."):
                time.sleep(0.8)
            st.rerun()

    with col_b:
        st.button(
            "❌ Start Over",
            use_container_width=True,
            on_click=reset_app
        )

    st.write("---")

    cols = st.columns(3)
    col_index = 0
    outfit = data["outfit"]

    for slot, items in outfit.items():

        if items:

            if slot == "Accessory" and len(items) > 1:
                chosen = random.sample(items, 2)

                for item in chosen:
                    with cols[col_index % 3]:
                        st.markdown(
                            f'<div style="color: white; font-weight: bold; text-shadow: 1px 1px 2px #000;">{slot}: {item["name"]}</div>',
                            unsafe_allow_html=True
                        )

                        if item["image"]:
                            st.image(item["image"], use_container_width=True)

                    col_index += 1

            else:
                chosen = random.choice(items)

                with cols[col_index % 3]:
                    st.markdown(
                        f'<div style="color: white; font-weight: bold; text-shadow: 1px 1px 2px #000;">{slot}: {chosen["name"]}</div>',
                        unsafe_allow_html=True
                    )

                    if chosen["image"]:
                        st.image(chosen["image"], use_container_width=True)

                col_index += 1

        else:
            with cols[col_index % 3]:
                st.markdown(
                    f'<div style="color: white; font-weight: bold; text-shadow: 1px 1px 2px #000;">{slot}: No items found</div>',
                    unsafe_allow_html=True
                )

            col_index += 1
