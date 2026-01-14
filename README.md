# GlipaBot

A Discord bot that automatically collects, manages, and shares media (images, GIFs, and Tenor links) from your Discord channels.

## Features

✨ **Automatic Media Collection**
- Scans channel history for images, GIFs, and Tenor links
- Filters out `media.tenor.com` direct links automatically
- Stores media URLs and metadata for later use

📢 **Automatic Posting**
- Posts random media to configured channels hourly
- Configurable posting probability (0-100%)
- ±10 minute random offset to avoid predictability
- Generates unique messages using templates

🌍 **Multi-Language Support**
- English and Russian
- Easy to add more languages
- Language preference saved automatically

⚙️ **Fully Configurable**
- Set target channels with `/channels` command
- Change language with `/settings` command
- Configure posting probability and interval
- Enable/disable automatic posting

## Quick Start

### Prerequisites
- Python 3.9+
- Discord Bot Token

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/sartyfay/GlipaBot.git
cd GlipaBot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Create Discord Bot & Get Token**
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create New Application
   - Go to "Bot" section and click "Add Bot"
   - Copy the token

4. **Set environment variable**

**Windows (PowerShell):**
```powershell
$env:DISCORD_BOT_TOKEN = "your_token_here"
```

**Linux/Mac:**
```bash
export DISCORD_BOT_TOKEN="your_token_here"
```

5. **Invite bot to your server**
   - Go to OAuth2 > URL Generator
   - Select scopes: `bot`, `applications.commands`
   - Select permissions: `Send Messages`, `Read Message History`, `Read Messages/View Channels`, `Embed Links`
   - Copy and open generated URL

6. **Run the bot**
```bash
python GlipaBot.py
```

## Commands

All commands are slash commands (`/`) and accessible to everyone:

### Media Management
- `/scan` - Scan current channel for media (asynchronous, no timeout)
- `/random` - Send random media from storage
- `/story` - Get file with all stored media URLs
- `/clean` - Remove media.tenor.com direct links

### Configuration
- `/settings` - Change language (English/Русский)
- `/channels` - Set 1-3 target channels for automatic posting

## Configuration

Bot settings are stored in `settings.json`:

```json
{
  "language": "en",
  "target_channels": [],
  "posting_enabled": true,
  "posting_probability": 0.6,
  "posting_interval_hours": 1
}
```

### Configuration Options
- `language` - `"en"` or `"ru"`
- `target_channels` - Array of Discord channel IDs
- `posting_enabled` - Enable/disable automatic posting
- `posting_probability` - Probability of posting (0.0 - 1.0)
- `posting_interval_hours` - Post every N hours

## Media Filtering

### What Gets Saved ✅
- Uploaded images (PNG, JPG, JPEG, WebP)
- Uploaded GIFs (.gif files)
- Tenor share links (tenor.com/view/...)
- Direct image URLs

### What Gets Filtered ❌
- media.tenor.com direct links (automatically excluded)
- Embed-only content without extractable links

## File Structure

```
GlipaBot/
├── GlipaBot.py              # Main bot code
├── word_base.json           # Message templates
├── README.md                # This file
├── QUICKSTART.txt           # Detailed setup guide
├── requirements.txt         # Python dependencies
├── .gitignore               # Git ignore rules
├── .env.example             # Environment template
├── settings.json            # Configuration (auto-generated)
├── media_links.txt          # Stored media URLs (auto-generated)
└── media_metadata.json      # Media metadata (auto-generated)
```

## Features in Detail

### Asynchronous Scanning
The `/scan` command runs asynchronously in the background:
1. Responds immediately: "🔍 Scan started!"
2. Scans without blocking the bot
3. Posts results when complete

### Multi-Language Support
- Command responses are translated
- Status messages in your language
- Error messages localized
- Add new languages easily by editing `GlipaBot.py`

### Background Posting
- Posts every hour with configurable probability
- ±10 minute random offset
- Generates unique messages each time
- Posts to all configured channels

## Troubleshooting

**Slash commands not showing?**
- Ensure bot has `applications.commands` scope
- Restart the bot after inviting

**Bot not posting?**
- Set target channels with `/channels` command
- Check bot has "Send Messages" permission
- Verify `posting_enabled` is `true` in `settings.json`

**Scan taking too long?**
- Scans run asynchronously - normal for large channels
- Bot will post results when complete

**Need help?**
- Check logs - all operations are logged with timestamps
- Enable DEBUG logging by editing `GlipaBot.py`

## License

No license - free to use and modify for any purpose.

## Author

Made with ❤️ by **sartyfay**

---

**Contributing**: Feel free to fork and submit pull requests!