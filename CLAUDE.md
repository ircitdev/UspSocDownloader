# Claude Code Instructions for UspSocDownloader

This file contains instructions for Claude Code when working with this project.

## Project Overview

**UspSocDownloader** - Telegram bot for downloading media from social networks (Instagram, YouTube, TikTok, Twitter/X, VK) with AI features (translation, rewriting, OCR).

- **Technology Stack**: Python 3.11+, aiogram 3.15, yt-dlp, gallery-dl, OpenAI GPT-4
- **Production Server**: VPS 31.44.7.144 (SSH: root@31.44.7.144)
- **Deployment**: systemd service (`uspsocdowloader`)
- **Bot**: [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)

## Project Structure

```
UspSocDownloader/
├── src/
│   ├── bot.py                  # Bot initialization
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration
│   ├── handlers/               # Message handlers
│   ├── downloaders/            # Media downloaders
│   ├── processors/             # URL processors
│   └── utils/                  # Utilities
├── run_bot.py                  # Production entry point
├── .env                        # Environment variables (not in git)
└── requirements.txt            # Python dependencies
```

## Development Workflow

### 1. Making Changes

- **Always read files before editing** - understand the existing code structure
- **Use dedicated tools**: Read, Edit, Write (not bash cat/sed/awk)
- **Test locally first** before deploying to production
- **Follow existing code style** and patterns in the project

### 2. Error Handling

- **Always escape HTML** in user-facing error messages using `safe_format_error()` from `src/utils/text_helpers.py`
- **Never expose sensitive data** in error messages (tokens, API keys, passwords)
- **Log errors properly** using the logger from `src/utils/logger.py`

### 3. Git Workflow

**Commit Message Format:**
```
<type>: <short description>

- Detailed change 1
- Detailed change 2

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types**: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`

**Before committing:**
1. Check git status: `git status`
2. Review changes: `git diff`
3. Add files: `git add <files>`
4. Commit with proper message
5. Push to GitHub: `git push origin master`

### 4. Deployment to Production

**Steps to deploy:**

```bash
# 1. Commit and push changes to GitHub
git push origin master

# 2. SSH to server
ssh root@31.44.7.144

# 3. Navigate to project directory
cd /opt/uspsocdowloader

# 4. Pull latest changes
git pull origin master

# 5. Restart the bot
systemctl restart uspsocdowloader

# 6. Check status
systemctl status uspsocdowloader

# 7. Monitor logs
journalctl -u uspsocdowloader -f
```

**Important Notes:**
- Always backup local changes on server before pulling
- Check for conflicts before merging
- Verify bot is running after restart
- Monitor logs for errors

### 5. Configuration

**Environment Variables (.env):**
- `BOT_TOKEN` - Telegram bot token
- `OPENAI_API_KEY` - OpenAI API key (if needed)
- `ADMIN_ID` - Telegram user ID of administrator (default: 65876198)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)
- `MAX_FILE_SIZE` - Maximum file size for downloads

**Never commit .env file to git!**

## Code Guidelines

### Python Style

- Use **type hints** for function parameters and return values
- Use **async/await** for all I/O operations
- Use **f-strings** for string formatting
- Keep functions **small and focused** (single responsibility)
- Add **docstrings** to complex functions

### Error Messages

**Always use safe HTML escaping:**

```python
from src.utils.text_helpers import safe_format_error

try:
    # some code
except Exception as e:
    await message.answer(f"❌ Ошибка: {safe_format_error(e)}")
```

**Don't do this:**
```python
await message.answer(f"❌ Ошибка: {str(e)}")  # ❌ Can cause HTML parsing errors
```

### Telegram Messages

- Use **HTML parse mode** for formatted messages: `parse_mode="HTML"`
- Use **inline keyboards** for user interactions
- Keep messages **concise and clear**
- Use **emojis** to improve UX: ✅ ❌ ⏳ 📥 💎 👑

### Admin Features

- Check if user is admin: `if user_id == config.ADMIN_ID:`
- Use admin panel callbacks: `admin_panel`, `admin_stats`, `admin_users`
- Admin commands: `/admin`, `/allstats`, `/users`, `/broadcast`, `/checkinstagram`, `/setcookies`

## Testing

### Local Testing

```bash
# Run locally
python run_bot.py

# Check logs
tail -f logs/bot.log
```

### Production Testing

```bash
# SSH to server
ssh root@31.44.7.144

# Check logs
journalctl -u uspsocdowloader -n 50

# Follow logs in real-time
journalctl -u uspsocdowloader -f
```

## Common Tasks

### Adding a New Platform

1. Add platform to `Platform` enum in `src/processors/url_processor.py`
2. Add URL patterns in `URLProcessor` class
3. Implement download logic in `src/downloaders/media_downloader.py`
4. Update `PLATFORMS` in `src/localization/messages.py`
5. Test thoroughly before deployment

### Adding a New Command

1. Add handler in `src/handlers/commands.py` (user) or create new handler file
2. Register router in `src/bot.py`
3. Add command to bot commands list in `src/bot.py`
4. Update README.md with new command documentation

### Fixing Bugs

1. **Reproduce the bug** - understand what's happening
2. **Check logs** - look for error messages and stack traces
3. **Find the root cause** - don't just fix symptoms
4. **Write a fix** - keep it minimal and focused
5. **Test the fix** - ensure it works and doesn't break anything
6. **Deploy** - commit, push, and restart on server

### Updating Dependencies

```bash
# Update requirements.txt
pip freeze > requirements.txt

# On server, install new dependencies
ssh root@31.44.7.144
cd /opt/uspsocdowloader
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart uspsocdowloader
```

## Important Files

### Core Files
- `src/bot.py` - Bot initialization, routers, commands setup
- `src/handlers/url_handler.py` - Main URL processing and callbacks
- `src/downloaders/media_downloader.py` - Media download logic
- `src/processors/url_processor.py` - URL parsing and platform detection

### Utility Files
- `src/utils/text_helpers.py` - Safe text formatting (HTML escaping)
- `src/utils/logger.py` - Logging setup
- `src/utils/translator.py` - OpenAI integration (translation, rewrite, OCR)
- `src/utils/sheets.py` - Google Sheets integration
- `src/utils/notifications.py` - Telegram notifications

### Configuration Files
- `.env` - Environment variables (secret, not in git)
- `src/config.py` - Configuration loader
- `requirements.txt` - Python dependencies

## Security Notes

- **Never commit secrets** to git (.env, tokens, API keys)
- **Always validate user input** before processing
- **Escape HTML** in all user-facing messages
- **Use proper file permissions** on server (check cookies, credentials)
- **Keep dependencies updated** to avoid security vulnerabilities

## Monitoring

### Health Checks
- Instagram health check runs every 12 hours
- Notifications sent to admin on issues
- Google Sheets logs all requests and errors

### Logs
- Application logs: `logs/bot.log`
- System logs: `journalctl -u uspsocdowloader`
- Error tracking: Check Google Sheets for failed requests

## Resources

- **GitHub**: https://github.com/ircitdev/UspSocDownloader
- **Telegram Bot**: [@UspSocDownloader_bot](https://t.me/UspSocDownloader_bot)
- **Google Sheets**: [Statistics Dashboard](https://docs.google.com/spreadsheets/d/1cQhOc-FyY5uF7cLC2nH0jht2pITrt0bc3swhvfhVUoI/)
- **Notification Group**: https://t.me/c/3307715316/

## Contact

- **Admin Telegram ID**: 65876198
- **Server**: 31.44.7.144 (SSH: root@31.44.7.144)

---

## Quick Reference Commands

```bash
# Local development
python run_bot.py

# Deploy to production
git push origin master
ssh root@31.44.7.144 'cd /opt/uspsocdowloader && git pull && systemctl restart uspsocdowloader'

# Check production logs
ssh root@31.44.7.144 'journalctl -u uspsocdowloader -n 100'

# Monitor production logs
ssh root@31.44.7.144 'journalctl -u uspsocdowloader -f'

# Check bot status
ssh root@31.44.7.144 'systemctl status uspsocdowloader'
```

---

**Remember**: Always test locally, commit properly, and verify production deployment!
