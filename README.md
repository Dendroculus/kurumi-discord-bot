<div align="center">
  <p>
    <strong>EN</strong> | <a href="https://github.com/Dendroculus/kurumi-discord-bot/blob/main/docs/readmeCN.md">CN</a>
  </p>

  <img src="assets/emojis/kurumichibi.png" width="220" alt="Kurumi Chibi Logo" />

  <h1>Kurumi — Discord Bot</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.1.0+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/discord.py-v2.x-7289DA.svg?logo=discord&logoColor=white" alt="discord.py">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT">
  <img src="https://img.shields.io/badge/status-Active-green.svg" alt="Update Status">
</p>

  <p>
    <em>A multi-purpose Discord bot focused on moderation, automation, and useful utilities.</em><br />
    Feature-complete, stable, and ready to serve.
  </p>
</div>


## ✨ Features
Kurumi comes packed with 42 commands designed to make server management easier and more fun.

&nbsp; 🛡️ **AutoMod** — Advanced protection against spam and profanity to keep your chat clean.  
&nbsp; 🔧 **Moderation** — Essential tools for kicking, banning, and managing users efficiently.  
&nbsp; ℹ️ **Information** — Detailed server info, user info, and utility lookups.  
&nbsp; 🔨 **Manager Tools** — Administration utilities for server configuration.  
&nbsp; 🎀 **Utilities** — Miscellaneous fun and useful commands for your community.

---

## 🚀 Project Status
**Note:** Kurumi has reached its final version.  
The bot is feature-complete and the development focus is now on stability and polish. New features may be added occasionally, but the core experience is finished.


## 🛠️ Installation & Setup
Follow these steps to get Kurumi running on your machine.

1. Clone the repository
```bash
git clone https://github.com/Dendroculus/kurumi-discord-bot.git
cd kurumi-discord-bot
```

2. Set up a Virtual Environment (optional but recommended)
```bash
# Create the environment
python -m venv venv

# Activate it:
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (cmd)
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

Core libraries:
- discord.py
- better_profanity
- aiohttp
- python-dotenv
- asyncpg
- Pillow

4. Configure environment
Create a `.env` file in the project root and add your credentials:
```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost
```

5. Launch
```bash
python main.py
```

## 🎨 Credits & Attribution

### Artwork
The chibi character artwork featured in this project is created by [@pypy_nemui](https://x.com/pypy_nemui/status/1130490628096217088).  
Used here solely for non-commercial, portfolio purposes.

### Data sources

Anime information and character data is powered by the AniList API
<a href="https://anilist.co/">
  <img
    src="https://anilist.co/img/icons/android-chrome-512x512.png"
    width="20"
    alt="AniList"
    align="top"
  />
</a>




## ⚖️ License & Disclaimer
This project is open-sourced under the MIT License — see [LICENSE](LICENSE).  

Disclaimer:
- Kurumi is an independent project and is not affiliated with, endorsed by, or supported by Discord Inc.
- All anime characters and artwork belong to their respective creators.
- Emoji assets are custom-made by the developer. If you fork this repo, please upload the emoji files to your Discord Developer Portal and update the IDs in the code.


<div align="center">
  <sub>Made with 💜 by <a href="https://github.com/Dendroculus">Dendroculus</a></sub>
</div>