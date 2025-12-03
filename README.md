# Kurumi Discord Bot

<img src="assets/emojis/kurumichibi.png" width="200" />

Kurumi is a multi-purpose Discord bot built with Python.  
It focuses on moderation, automation, and useful utilities for server management.  

## Features
- [x] AutoMod (spam and profanity filtering)  
- [x] Information commands  
- [x] Manager tools  
- [x] Miscellaneous utilities  
- [x] Moderator tools  

## Status
- Kurumi has reached its **final version**. 
- The bot is feature-complete with **40 commands**. 
- Focus is on stability and polish. New features may be added occasionally.

---

## License
This project is licensed under the **MIT License** — you are free to use, modify, and distribute it, provided that proper credit is given.  
See the [LICENSE](LICENSE) file for details.  

---

## Disclaimer

- Kurumi is an independent project and is **not affiliated with, supported by, or endorsed by Discord Inc.**  
  All trademarks and copyrights related to Discord are owned by their respective owners.  
- All anime characters and artwork shown are the property of their respective creators.  
- All emoji assets are made by me.  
- Used here for **non-commercial, portfolio purposes only**.  
- ⚠️ GIF files are not included. Place kurumi.gif (and others if needed) in the `assets/` folder before using commands that rely on GIF outputs.  
- Upload the emoji file into Discord Developer Portal and update the IDs in the code to display them correctly.


## Artwork Attribution

The chibi character artwork featured in this project is created by [@pypy_nemui](https://x.com/pypy_nemui/status/1130490628096217088). Used here solely for non-commercial, portfolio purposes.

## Data Source
Anime information and character data is provided via <a href="https://anilist.co/"><img src="https://anilist.co/img/icons/android-chrome-512x512.png" width="16" /></a> AniList API.<br>

## Installation & Requirements

## 1. Clone the repository
```bash
git clone https://github.com/yourusername/kurumi-bot.git
cd kurumi-bot
```

## 2. (Optional) Create and activate a virtual environment
```bash
python -m venv venv
```

**Activate it:**
- **Linux/macOS**
  ```bash
  source venv/bin/activate
  ```
- **Windows**
  ```bash
  venv\Scripts\activate
  ```

## 3. Install dependencies
```bash
pip install -r requirements.txt
```

**Dependencies:**
- discord.py  
- better_profanity  
- aiohttp  
- python-dotenv  

## 4. Create a .env file
Inside the project root (already in .gitignore), add your bot token:

```env
DISCORD_TOKEN=your_token_here
```

(You can also add other API keys if needed.)

## 5. Run the bot
```bash
python main.py
```






