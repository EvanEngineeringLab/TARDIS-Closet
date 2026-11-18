# TARDIS Closet

TARDIS Closet is a weather-aware, automated wardrobe randomizer built with Python, Streamlit, and the Notion API. It pulls your wardrobe from a Notion database, checks the current weather for your ZIP code, and generates a randomized outfit based on the occasion and weather conditions.

## 🌐 Live Demo
[Click here to view the live app!](https://tardis-closet.streamlit.app)

## ✨ Features
- **Notion Integration:** Reads clothing items, images, and tags directly from your Notion database.
- **Weather API:** Automatically fetches temperature and humidity to classify the weather as Hot, Cold, or Raining.
- **Interactive UI:** Allows the user to agree or disagree with the bot's weather assessment.
- **Image Display:** Shows the exact photos of the clothes you need to grab from your closet.
- **Multi-User System:** Uses a lightweight SQLite database and URL session IDs to remember user settings without overlapping data.
- **Custom UI:** Includes a Doctor Who-themed background, TARDIS icons, and custom-styled buttons.

## 🚀 How to Use the Live App
To use the live app, you will need to connect your own Notion database. This ensures your personal wardrobe stays private to you. 

### Phase 1: Create Your Notion Account
1. Download the Notion app from the Play Store and create an account.
2. Open a web browser on a **laptop or desktop** (the connection step cannot be done on the mobile app).

### Phase 2: Create Your Database
3. In Notion, press the plus to create a new page.
4. Type `/database` and select **Table View** to create an inline database.
5. Rename the first column to **Name** and make sure it is set to the **Title** property type.
6. Add the following properties and their exact options:
   - **Garment Type** (Select): Add options for `Undershirt`, `Overshirt`, `Pants`, `Shoes`, `Mid-Layer`, `Headwear`, `Outerwear`, and `Accessory`.
   - **Occasion** (Multi-Select): Add options for `Date`, `School`, `Work`, `Job Interview`, `Presentation`, `Casual`, `Formal Event`, and `Cosplay`.
   - **Weather** (Multi-Select): Add options for `Hot`, `Cold`, and `Raining`.
   - **Image** (Files & Media): Leave this blank; you will upload photos here later.

### Phase 3: Create the Connection
7. On your laptop, go to your Notion **Settings**.
8. Scroll down and click **Connections**.
9. Click **Add connection** -> **Developer connection**.
10. Click **New connection**, name it (e.g., "Wardrobe Bot"), and save.
11. Copy the **API Token** shown next to the name.

### Phase 4: Link the Connection to the Database
12. Go back to your Wardrobe database page.
13. Click the **three dots (...)** in the top right corner.
14. Click **+ Add connections** (or just Connections).
15. Search for your connection ("Wardrobe Bot") and click it to add it to the page.

### Phase 5: Get the Database ID
16. Look at the URL in your browser. It will look something like this:
    `app.notion.com/p/`**`1234567890abcdef1234567890abcdef`**`?v=...`
17. The Database ID is the long string of letters and numbers shortly after `/p/` and right before `?v=`. It has **no hyphens**. Copy that string.

### Phase 6: Connect to the App
18. Go to the [Live Demo](https://tardis-closet.streamlit.app).
19. Type in your API Token, Database ID, and ZIP code into the black welcome box.
20. Follow the on-screen prompts. Congratulations, you're connected!

### Phase 7: Fill Your Database
21. Go back to the Notion app on your phone.
22. Open your Wardrobe page and open the database.
23. For each item of clothing, select the `Garment Type`, `Occasion`, and `Weather`.
24. Take a photo, click **Add a file** under the Image property, and select the photo. 
*(Note: Your phone will be filled with pictures of your clothes for a short period of time while you get everything set up. A small price to pay!)*

## 🧑‍💻 How to Run Locally (For Developers)
If you want to run this code on your own machine and host your own version:

### 1. Requirements
1. Clone this repository.
2. Install the requirements: `pip install -r requirements.txt`
3. You will need a free API key from [openweathermap.org](https://openweathermap.org).

### 2. Environment Variables
1. Create a folder named `.streamlit` in the root of this project.
2. Inside that folder, create a file named `secrets.toml`.
3. Add your weather key to the file:
   `OPENWEATHER_TOKEN = "your_api_key_here"`

### 3. Run
Run the app: `python -m streamlit run web_app.py`

## 🧠 How It Works
The app uses a state-machine approach. It prompts the user for an occasion, checks the weather, asks for confirmation, and then queries Notion for items matching both tags. It uses `random.choice()` to build the outfit and displays it in a grid. To handle multiple users without requiring a complex login system, it generates a unique UUID and stores it in the URL and a local SQLite database.

## 👨‍💻 Author
**Evan Brown**
- GitHub: [@EvanEngineeringLab](https://github.com/EvanEngineeringLab)
