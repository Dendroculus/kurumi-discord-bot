[EN](https://github.com/Dendroculus/kurumi-discord-bot/blob/main/README.md) | CN 

# Kurumi — Discord 机器人

Kurumi 是一个用 Python 编写的多功能 Discord 机器人，专注于服务器管理所需的审核、自动化和实用工具。

<img src="https://github.com/Dendroculus/kurumi-discord-bot/blob/main/assets/emojis/kurumichibi.png" width="200" />


## 🌟 功能
- [x] 自动审核（垃圾信息和脏话过滤）  
- [x] 信息命令  
- [x] 管理员工具  
- [x] 杂项实用工具  
- [x] 版主工具  

Kurumi 已实现约 40 个命令，覆盖常见的管理与实用场景。



## 🚀 状态
Kurumi 已达到最终版本。  
当前重点是稳定性和完善；将以稳定为主，可能会偶尔添加新功能或修复 bug。



## 📜 许可证
本项目采用 MIT 许可证授权 — 您可以自由使用、修改和分发，但须保留原作者署名与许可文件。详见仓库中的 `LICENSE` 文件。



## ⚠️ 免责声明
- Kurumi 是独立项目，与 Discord Inc. 无关，亦不受其支持或认可。  
- 所有与 Discord 相关的商标和版权归其各自所有者所有。  
- 展示的动漫角色与艺术作品归各自创作者所有。  
- 所有表情符号资产由作者制作，仅用于非商业、个人作品集用途。



## ⚠️ 资源与注意事项
- 仓库不包含 GIF 文件。若命令依赖 GIF 输出，请将 `kurumi.gif`（及其他所需文件）放入 `assets/` 文件夹。  
- 请将自定义表情文件上传到 Discord 开发者门户，并在代码中更新表情 ID，以正确显示表情。



## 🎨 艺术作品署名
本项目中使用的 Q 版角色艺术作品由原作者创作，仅用于非商业、个人作品集目的。请在使用或再发布时尊重原作者权利并注明出处。



## ⚙️ 数据来源
- 动漫信息：AniList API  
- 动漫角色信息：Jikan API



## 🛠️ 安装与要求

1. 克隆仓库
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

2. （可选）创建并激活虚拟环境

   Linux / macOS:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   Windows (PowerShell):
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. 安装依赖项

   - 依赖包：
     - discord.py
     - better_profanity
     - aiohttp
     - python-dotenv

   使用 pip 安装：
   ```bash
   pip install -r requirements.txt
   ```
   或者单独安装：
   ```bash
   pip install discord.py better_profanity aiohttp python-dotenv
   ```

4. 创建 `.env` 文件  
   在项目根目录内（已在 `.gitignore` 中），创建 `.env` 并添加您的机器人令牌。例如：
   ```env
   DISCORD_TOKEN=your_bot_token_here
   # 如果需要其他 API Key，可在此继续添加：
   # ANILIST_CLIENT_ID=...
   # ANILIST_CLIENT_SECRET=...
   ```

5. 运行机器人  
   运行主脚本（根据仓库实际入口文件，可为 `bot.py`、`main.py` 等）：
   ```bash
   python bot.py
   ```
   或
   ```bash
   python main.py
   ```



## ✅ 进一步帮助
您还需要我为该项目翻译其他文件（例如 `LICENSE`、代码注释、命令说明等）吗？我可以：
- 将 README 转为多语言版本；
- 翻译或注释关键代码文件；
- 为每个命令生成使用文档或示例配置。

如需我继续翻译或生成文档，请告诉我想要处理的文件或目录路径。
