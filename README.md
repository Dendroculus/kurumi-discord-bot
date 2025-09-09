# Kurumi Discord Bot

<img src="assets/kurumichibi.png" width="200" />

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
- The bot is feature-complete with **36 commands**. 
- No new commands will be added, but minor improvements and maintenance may still occur.

---

## License
This project is licensed under the **MIT License** — you are free to use, modify, and distribute it, provided that proper credit is given.  
See the [LICENSE](LICENSE) file for details.  

---

## Disclaimer
Kurumi is an independent project and is **not affiliated with, supported by, or endorsed by Discord Inc.**  
All trademarks and copyrights related to Discord are owned by their respective owners.  

All anime characters and artwork shown are the property of their respective creators.  
Used here for non-commercial, portfolio purposes only.

## Artwork Attribution

The chibi character artwork featured in this project is created by [@pypy_nemui](https://x.com/pypy_nemui/status/1130490628096217088). Used here solely for non-commercial, portfolio purposes.

## Data Source
Anime information is provided via <a href="https://anilist.co/"><img src="https://anilist.co/img/icons/android-chrome-512x512.png" width="16" /></a> AniList API.<br>
Anime character information is provided via <a href="https://jikan.moe/"><img src="https://cdn.myanimelist.net/img/sp/icon/apple-touch-icon-256.png" width="16" /></a> Jikan API.

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






