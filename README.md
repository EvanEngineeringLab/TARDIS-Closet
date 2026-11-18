# TARDIS Closet

TARDIS Closet is a weather-aware, automated wardrobe manager built with Python, Streamlit, and the Notion API. It pulls your wardrobe directly from a Notion database, provides live `Clean`/`Dirty` inventory tracking, and generates coordinated outfits using a deterministic round-robin priority layout.

## 🌐 Live Demo
[Click here to view the live app!](https://tardis-closet.streamlit.app)

## ✨ Features
- **Notion Integration:** Reads clothing items, images, and attributes directly from your Notion database with zero manual hardcoding.
- **Live Inventory & Laundry Tracking:** Instantly toggle any clothing item between `Clean` and `Dirty` status right from the closet catalog or drill-down editor.
- **Deterministic Priority Sorting:** Cycles through your wear-order preferences in a clean, predictable round-robin sequence without chaotic random shuffling.
- **Image Display:** Pulls exact photos of your wardrobe for visual outfit previews.
- **Emergency Laundry Trap:** Triggers a locked alert view if every item in your closet is marked as dirty.
- **Custom UI:** Designed with high-contrast container geometry, custom drop shadows, and a clean dark theme.

## 🚀 How to Use the Live App
To use the live app, you will need to connect your own Notion database. This ensures your personal wardrobe stays private to you. 

### Phase 1: Create Your Notion Account
1. Download the Notion app or open a web browser to create an account.
2. Open a web browser on a **laptop or desktop** for the initial setup.

### Phase 2: Create Your Database
3. In Notion, press the plus to create a new page.
4. Type `/database` and select **Table View** to create an inline database.
5. Rename the first column to **Name** and make sure it is set to the **Title** property type.
6. Add the following required properties to your database:
   - **Laundry** (Select): Create options for `Clean` and `Dirty`.
   - **Image** (Files & Media): For your clothing photos.
   *(Note: Occasion and Garment Type properties can be automatically mapped or created dynamically during app setup!)*

### Phase 3: Create the Connection
7. Go to your Notion **Settings**.
8. Scroll down and click **Connections**.
9. Click **Add connection** -> **Developer connection**.
10. Click **New connection**, name it (e.g., "Wardrobe Bot"), and save.
11. Copy the **API Token** shown next to the name.

### Phase 4: Link the Connection to the Database
12. Go back to your Wardrobe database page.
13. Click the **three dots (...)** in the top right corner.
14. Click **+ Add connections** (or just Connections).
15. Search for your connection ("Wardrobe Bot") and click it to add it to the page.

### Phase 5: Get the Database ID and Form URL
16. Look at the URL in your browser. It will look something like this:
    `app.notion.com/p/`**`1234567890abcdef1234567890abcdef`**`?v=...`
17. The Database ID is the long string of letters and numbers shortly after `/p/` and right before `?v=`. It has **no hyphens**. Copy that string.
18. Create a Notion web/quick-add form for your closet and copy the form's link URL.

### Phase 6: Set Up Your Credential File
19. Create a text file and format your credentials like this:
    ```text
    NOTION_TOKEN = "your_api_code_here"
    DATABASE_ID = "your_database_id_here"
    FORM = "your_form_link_url_here"
    ```
20. Save the file.

### Phase 7: Connect and Configure in the App
21. Go to the [Live Demo](https://tardis-closet.streamlit.app).
22. Upload your credential text file when prompted to authenticate.
23. Select your preferred **Persona**.
24. Choose your **latitude and longitude** directly off the interactive map.
25. Configure and map your Notion database properties for your **occasions** and **garment types** right inside the app interface. Once configured, you're good to go!

## 🧑‍💻 How to Run Locally (For Developers)
If you want to run this code on your own machine and host your own version:

### 1. Requirements
1. Clone this repository.
2. Install the requirements: `pip install -r requirements.txt`

### 2. Environment Variables
1. Create a folder named `.streamlit` in the root of this project.
2. Inside that folder, create a file named `secrets.toml`.
3. Add your keys to the file:
   ```toml
   NOTION_TOKEN = "your_notion_token_here"
   DATABASE_ID = "your_database_id_here"
   FORM = "your_form_link_url_here"
   ```

### 3. Run
Run the app locally: `python -m streamlit run web_app.py`

## 🧠 How It Works
The app uses a state-machine architecture to guide you from credential text-file authentication through persona selection, map coordinate picking, dynamic schema auto-hydration, round-robin catalog filtering, live database patching (`Clean`/`Dirty` status updates), and outfit generation. It dynamically queries your Notion schema on load so that your custom tags and categories automatically map to the interface.

## 👨‍💻 Author
**Evan Brown**
- GitHub: [@EvanEngineeringLab](https://github.com/EvanEngineeringLab)
