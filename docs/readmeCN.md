<div align="center">
  <p>
    <a href="https://github.com/Dendroculus/kurumi-discord-bot/blob/main/README.md">EN</a> | <strong>CN</strong>
  </p>

  <img src="../assets/emojis/kurumichibi.png" width="220" alt="Kurumi Chibi Logo" />

  <h1>Kurumi — Discord 机器人</h1>

  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.1.0+-blue.svg" alt="Python Version" />
    <img src="https://img.shields.io/badge/discord.py-v2.x-7289DA.svg?logo=discord&logoColor=white" alt="discord.py" />
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT" />
    <img src="https://img.shields.io/badge/status-Active-green.svg" alt="Update Status" />
  </p>

  <p>
    <em>一个专注于审核、自动化和实用工具的多功能 Discord 机器人。</em><br />
    功能完备，运行稳定，随时为您服务。
  </p>
</div>


## ✨ 功能特性

Kurumi 包含 42 个命令，旨在让服务器管理变得更轻松、更有趣。

&nbsp; 🛡️ AutoMod (自动审核) — 高级防护功能，拦截垃圾信息和脏话，保持聊天环境整洁。 <br>
&nbsp; 🔧 Moderation (管理工具) — 用于踢出、封禁和高效管理用户的必要工具。 <br>
&nbsp; ℹ️ Information (信息查询) — 详细的服务器信息、用户信息及实用查询功能。 <br>
&nbsp; 🔨 Manager Tools (管理员工具) — 用于服务器配置的管理实用程序。 <br>
&nbsp; 🎀 Utilities (杂项功能) — 社区所需的各种有趣且实用的命令。

## 🚀 项目状态

注意： Kurumi 已达到最终版本。  
机器人功能已完备，目前的开发重点是稳定性和打磨。偶尔可能会添加新功能，但核心体验已完成。


## 🛠️ 安装与设置

请按照以下步骤在您的设备上运行 Kurumi。

1. 克隆仓库
```bash
git clone https://github.com/Dendroculus/kurumi-discord-bot.git
cd kurumi-discord-bot
```

2. 设置虚拟环境（可选但推荐）
```bash
# 创建环境
python -m venv venv

# 激活环境:
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Windows (cmd)
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

核心库：

- discord.py  
- better_profanity  
- aiohttp  
- python-dotenv  
- asyncpg  
- Pillow

4. 配置环境

在项目根目录下创建一个 `.env` 文件并添加您的凭据：

```env
DISCORD_TOKEN=your_bot_token_here
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost
```

5. 启动

```bash
python main.py
```


## 🎨 致谢与版权声明

艺术作品

本项目中的 Q 版角色插图由 [@pypy_nemui](https://x.com/pypy_nemui/status/1130490628096217088) 创作。  
仅用于非商业及作品集展示目的。

数据来源

动漫信息和角色数据由 AniList API 提供支持
<a href="https://anilist.co/">
  <img src="https://anilist.co/img/icons/android-chrome-512x512.png" width="20" alt="AniList" align="top" />
</a>

## ⚖️ 许可证与免责声明

本项目基于 MIT 许可证开源 — 详见 [LICENSE](LICENSE)。  

免责声明：

- Kurumi 是一个独立项目，不隶属于 Discord Inc.，也不受其认可或支持。  
- 所有动漫角色和艺术作品均归其各自创作者所有。  
- 表情符号资产由开发者制作。如果您分叉（fork）了此仓库，请将表情文件上传到您的 Discord 开发者门户并在代码中更新 ID。

<div align="center">
  <sub>💜 作者：<a href="https://github.com/Dendroculus">Dendroculus</a></sub>
</div>
