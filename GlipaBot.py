import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import logging
import random
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
MEDIA_LINKS_FILE = "media_links.txt"
MEDIA_METADATA_FILE = "media_metadata.json"
WORD_BASE_FILE = "word_base.json"
SETTINGS_FILE = "settings.json"

# Intents configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# Bot configuration
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables for media caching
media_cache = {
    'links': [],
    'metadata': {},
    'last_loaded': None
}

# Settings cache
settings_cache = {
    'language': 'en',
    'target_channels': [],
    'posting_enabled': True,
    'posting_probability': 0.6,
    'posting_interval_hours': 1
}

# Background scan tasks
scan_tasks = {}

# Translations
TRANSLATIONS = {
    'en': {
        'no_media': "No media stored yet. Use `/scan` to start collecting.",
        'media_story': "📚 Media Story - {count} items found",
        'need_admin': "❌ You need administrator permissions to use this command.",
        'scan_complete': "✅ Scan complete, found {count} files, took {time}ms",
        'no_media_random': "No media in storage. Use `/scan` to collect some!",
        'cleaned': "🧹 Cleaned {count} media.tenor.com links from storage",
        'no_tenor': "No media.tenor.com links found in storage",
        'error': "Error: {error}",
        'language_set': "✅ Language set to English",
        'channels_set': "✅ Target channels updated: {channels}",
        'no_channels': "❌ You must select at least one channel",
        'scanning': "Scanning channel history...",
        'scan_started': "🔍 Scan started! This may take a while. I'll send results here when done.",
        'scan_finished': "✅ Scan finished! Found {count} new files in {time}ms",
    },
    'ru': {
        'no_media': "Медиа не найдено. Используйте `/scan` чтобы начать сбор.",
        'media_story': "📚 История медиа - {count} элементов найдено",
        'need_admin': "❌ Вам нужны права администратора для использования этой команды.",
        'scan_complete': "✅ Сканирование завершено, найдено {count} файлов, затрачено {time}мс",
        'no_media_random': "Нет медиа в хранилище. Используйте `/scan` чтобы собрать медиа!",
        'cleaned': "🧹 Удалено {count} ссылок media.tenor.com из хранилища",
        'no_tenor': "Ссылки media.tenor.com не найдены в хранилище",
        'error': "Ошибка: {error}",
        'language_set': "✅ Язык установлен на Русский",
        'channels_set': "✅ Целевые каналы обновлены: {channels}",
        'no_channels': "❌ Вы должны выбрать хотя бы один канал",
        'scanning': "Сканирование истории канала...",
        'scan_started': "🔍 Сканирование началось! Это может занять некоторое время. Я отправлю результаты сюда, когда закончу.",
        'scan_finished': "✅ Сканирование завершено! Найдено {count} новых файлов за {time}мс",
    }
}

def get_text(key, **kwargs):
    """Get translated text based on current language."""
    lang = settings_cache.get('language', 'en')
    text = TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS['en'].get(key, key))
    return text.format(**kwargs) if kwargs else text

def load_settings():
    """Load settings from JSON file."""
    global settings_cache
    try:
        if Path(SETTINGS_FILE).exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                settings_cache.update(data)
        else:
            save_settings()
        logger.info("Settings loaded successfully")
        return True
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return False

def save_settings():
    """Save settings to JSON file."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_cache, f, indent=2, ensure_ascii=False)
        logger.info("Settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False

def load_word_base():
    """Load word generation templates from JSON file."""
    try:
        with open(WORD_BASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {WORD_BASE_FILE}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {WORD_BASE_FILE}")
        return None


def load_media_data():
    """Load media links and metadata from files."""
    try:
        # Load links
        links = []
        if Path(MEDIA_LINKS_FILE).exists():
            with open(MEDIA_LINKS_FILE, 'r', encoding='utf-8') as f:
                links = [line.strip() for line in f if line.strip()]
        
        # Load metadata
        metadata = {}
        if Path(MEDIA_METADATA_FILE).exists():
            with open(MEDIA_METADATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                metadata = {item['url']: item for item in data.get('media', [])}
        
        media_cache['links'] = links
        media_cache['metadata'] = metadata
        media_cache['last_loaded'] = time.time()
        
        logger.info(f"Loaded {len(links)} media items from storage")
        return True
    except Exception as e:
        logger.error(f"Error loading media data: {e}")
        return False


def save_media_data():
    """Save media links and metadata to files."""
    try:
        # Save links
        with open(MEDIA_LINKS_FILE, 'w', encoding='utf-8') as f:
            for link in media_cache['links']:
                f.write(link + '\n')
        
        # Save metadata
        metadata_list = list(media_cache['metadata'].values())
        with open(MEDIA_METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'media': metadata_list}, f, indent=2, ensure_ascii=False)
        
        logger.info("Media data saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving media data: {e}")
        return False


def add_media(url, media_type, generated_text=""):
    """Add new media to storage if not duplicate."""
    # Skip invalid URLs
    if not url or not isinstance(url, str) or len(url) < 10:
        return False
    
    if url in media_cache['links']:
        logger.info(f"Media already exists: {url}")
        return False
    
    # Validate URL format
    if not (url.startswith('http://') or url.startswith('https://')):
        logger.warning(f"Invalid URL format: {url}")
        return False
    
    # Skip ONLY media.tenor.com direct links (keep tenor.com/view/ links)
    if 'media.tenor.com' in url:
        logger.info(f"Skipped media.tenor.com direct link: {url}")
        return False
    
    media_cache['links'].append(url)
    media_cache['metadata'][url] = {
        'url': url,
        'date_added': datetime.now().isoformat(),
        'type': media_type,
        'generated_text': generated_text
    }
    
    logger.info(f"Added new media: {url} (Type: {media_type})")
    return True


def get_random_media():
    """Get a random media URL from storage."""
    if not media_cache['links']:
        return None
    return random.choice(media_cache['links'])


def clean_tenor_media_from_storage():
    """Remove all media.tenor.com links from storage."""
    initial_count = len(media_cache['links'])
    
    # Filter out all media.tenor.com URLs (keep tenor.com/view/ links)
    media_cache['links'] = [
        url for url in media_cache['links']
        if 'media.tenor.com' not in url
    ]
    
    # Also clean metadata
    tenor_urls = [
        url for url in media_cache['metadata'].keys()
        if 'media.tenor.com' in url
    ]
    
    for url in tenor_urls:
        del media_cache['metadata'][url]
    
    removed_count = initial_count - len(media_cache['links'])
    
    if removed_count > 0:
        save_media_data()
        logger.info(f"Cleaned {removed_count} media.tenor.com links from storage")
    
    return removed_count


def generate_message():
    """Generate a random message using word_base templates."""
    word_base = load_word_base()
    if not word_base:
        return "Check out this awesome content!"
    
    try:
        template = random.choice(word_base.get('templates', []))
        greeting = random.choice(word_base.get('greetings', ['Check this out!']))
        adjective = random.choice(word_base.get('descriptive_words', ['amazing']))
        
        message = template.format(greeting=greeting, adjective=adjective)
        return message
    except (KeyError, IndexError):
        return "Check out this awesome content!"


def should_post_media():
    """Determine if media should be posted based on configured probability."""
    return random.random() < settings_cache.get('posting_probability', 0.6)


@bot.event
async def on_ready():
    """Event triggered when bot is ready."""
    logger.info(f'Bot logged in as {bot.user}')
    logger.info(f'Bot ID: {bot.user.id}')
    
    # Load media data on startup
    load_media_data()
    load_settings()
    
    # Sync commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")
    
    # Start background tasks
    if not media_posting_loop.is_running():
        media_posting_loop.start()


@bot.tree.command(name="story", description="Send a file with all stored media URLs")
async def story(interaction: discord.Interaction):
    """Send a file containing the full list of all stored media URLs."""
    try:
        load_media_data()
        
        if not media_cache['links']:
            await interaction.response.send_message(get_text('no_media'), ephemeral=True)
            return
        
        # Create content for the file
        content = '\n'.join(media_cache['links'])
        
        # Create a temporary file and send it
        file_path = Path('media_story.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        await interaction.response.send_message(
            get_text('media_story', count=len(media_cache['links'])),
            file=discord.File(file_path)
        )
        
        # Clean up temporary file
        file_path.unlink()
        logger.info(f"Sent media story with {len(media_cache['links'])} items")
        
    except Exception as e:
        logger.error(f"Error in story command: {e}")
        await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


@bot.tree.command(name="scan", description="Scan channel history for images and GIFs")
async def scan(interaction: discord.Interaction):
    """Scan channel history for images, GIFs, and Tenor links."""
    try:
        # Respond immediately
        await interaction.response.send_message(get_text('scan_started'))
        
        # Start background task
        task = asyncio.create_task(perform_scan(interaction.channel))
        scan_tasks[interaction.channel.id] = task
        
        logger.info(f"Scan task started for channel {interaction.channel.id}")
        
    except Exception as e:
        logger.error(f"Error starting scan: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


async def perform_scan(channel: discord.TextChannel):
    """Perform actual scanning in background."""
    try:
        start_time = time.time()
        found_count = 0
        
        # Scan channel history
        async for message in channel.history(limit=None):
            # 1. Check attachments (uploaded files) - Discord uploads
            for attachment in message.attachments:
                if attachment.content_type and (
                    attachment.content_type.startswith('image/') or
                    attachment.content_type == 'image/gif'
                ):
                    media_type = 'gif' if 'gif' in attachment.content_type else 'image'
                    if add_media(attachment.url, media_type):
                        found_count += 1
            
            # 2. ONLY extract links from message.content (original URLs before Discord conversion)
            if message.content:
                # Look for Tenor URLs (tenor.com/view/...)
                tenor_urls = re.findall(
                    r'https?://(?:www\.)?tenor\.com/(?:ru/)?view/[^\s>]*',
                    message.content
                )
                for url in tenor_urls:
                    if add_media(url, 'gif'):
                        found_count += 1
                
                # Look for other image URLs (skip media.tenor.com)
                image_urls = re.findall(
                    r'https?://[^\s]*\.(?:gif|jpg|jpeg|png|webp)[^\s>]*',
                    message.content,
                    re.IGNORECASE
                )
                for url in image_urls:
                    # Skip if already found as Tenor or media.tenor.com
                    if not any(tenor in url for tenor in ['tenor.com', 'media.tenor.com']):
                        media_type = 'gif' if url.lower().endswith('.gif') else 'image'
                        if add_media(url, media_type):
                            found_count += 1
        
        # Save collected media
        save_media_data()
        
        # Calculate elapsed time
        elapsed_time = int((time.time() - start_time) * 1000)
        
        # Send results to channel (not via interaction)
        await channel.send(get_text('scan_finished', count=found_count, time=elapsed_time))
        
        logger.info(f"Scan completed: found {found_count} new files in {elapsed_time}ms")
        
    except Exception as e:
        logger.error(f"Error in background scan: {e}")
        await channel.send(get_text('error', error=str(e)))
    finally:
        # Clean up task
        if channel.id in scan_tasks:
            del scan_tasks[channel.id]


@bot.tree.command(name="random", description="Send a random media from storage")
async def random_media(interaction: discord.Interaction):
    """Send a random image/GIF from storage."""
    try:
        load_media_data()
        
        media_url = get_random_media()
        if not media_url:
            await interaction.response.send_message(get_text('no_media_random'), ephemeral=True)
            return
        
        # Generate message
        message_text = generate_message()
        
        # Send just text with image (no embed border)
        await interaction.response.send_message(message_text)
        await interaction.followup.send(media_url)
        logger.info(f"Sent random media: {media_url}")
        
    except Exception as e:
        logger.error(f"Error in random command: {e}")
        await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


@bot.tree.command(name="clean", description="Remove all media.tenor.com links from storage")
async def clean(interaction: discord.Interaction):
    """Remove all media.tenor.com links from storage."""
    try:
        removed_count = clean_tenor_media_from_storage()
        
        if removed_count > 0:
            await interaction.response.send_message(get_text('cleaned', count=removed_count))
        else:
            await interaction.response.send_message(get_text('no_tenor'), ephemeral=True)
    
    except Exception as e:
        logger.error(f"Error in clean command: {e}")
        await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


@bot.tree.command(name="settings", description="Configure bot settings")
@app_commands.describe(language="Choose language / Выберите язык")
@app_commands.choices(language=[
    app_commands.Choice(name="English", value="en"),
    app_commands.Choice(name="Русский", value="ru")
])
async def settings(interaction: discord.Interaction, language: app_commands.Choice[str]):
    """Change bot language."""
    try:
        settings_cache['language'] = language.value
        save_settings()
        
        await interaction.response.send_message(get_text('language_set'), ephemeral=True)
        logger.info(f"Language changed to: {language.value}")
        
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


@bot.tree.command(name="channels", description="Set target channels for posting")
@app_commands.describe(channel1="Target channel 1", channel2="Target channel 2 (optional)", 
                       channel3="Target channel 3 (optional)")
async def channels(interaction: discord.Interaction, channel1: discord.TextChannel, 
                   channel2: discord.TextChannel = None, channel3: discord.TextChannel = None):
    """Set target channels for automatic media posting."""
    try:
        target_channels = [channel1.id]
        if channel2:
            target_channels.append(channel2.id)
        if channel3:
            target_channels.append(channel3.id)
        
        if not target_channels:
            await interaction.response.send_message(get_text('no_channels'), ephemeral=True)
            return
        
        settings_cache['target_channels'] = target_channels
        save_settings()
        
        channel_names = ", ".join([bot.get_channel(cid).mention for cid in target_channels if bot.get_channel(cid)])
        await interaction.response.send_message(get_text('channels_set', channels=channel_names), ephemeral=True)
        logger.info(f"Target channels updated: {target_channels}")
        
    except Exception as e:
        logger.error(f"Error in channels command: {e}")
        await interaction.response.send_message(get_text('error', error=str(e)), ephemeral=True)


@tasks.loop(hours=1)
async def media_posting_loop():
    """Background task: post media hourly with configured probability and +/- 10 minute offset."""
    try:
        # Check if posting is enabled
        if not settings_cache.get('posting_enabled', True):
            logger.info("Media posting disabled")
            return
        
        # Add random offset (±10 minutes = ±600 seconds)
        offset = random.randint(-600, 600)
        await asyncio.sleep(offset)
        
        # Check probability
        if not should_post_media():
            logger.info("Media posting skipped (probability check failed)")
            return
        
        # Load media
        load_media_data()
        media_url = get_random_media()
        
        if not media_url:
            logger.warning("No media available for posting")
            return
        
        # Get target channels
        target_channels = settings_cache.get('target_channels', [])
        if not target_channels:
            logger.warning("No target channels configured")
            return
        
        # Post to each target channel
        for channel_id in target_channels:
            channel = bot.get_channel(channel_id)
            
            if not channel:
                logger.error(f"Target channel {channel_id} not found")
                continue
            
            # Check if bot has permission to send messages in target channel
            if not channel.permissions_for(channel.guild.me).send_messages:
                logger.error(f"No permission to send messages in channel {channel_id}")
                continue
            
            try:
                # Generate message
                message_text = generate_message()
                
                # Send media without embed (no colored border)
                await channel.send(message_text)
                await channel.send(media_url)
                logger.info(f"Posted media to {channel.guild.name}#{channel.name}")
                
            except Exception as e:
                logger.error(f"Error posting to channel {channel.name}: {e}")
        
    except Exception as e:
        logger.error(f"Error in media posting loop: {e}")


@media_posting_loop.before_loop
async def before_media_posting_loop():
    """Wait for bot to be ready before starting the loop."""
    await bot.wait_until_ready()


@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for app commands."""
    logger.error(f"App command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(get_text('error', error=str(error)), ephemeral=True)
    else:
        await interaction.followup.send(get_text('error', error=str(error)), ephemeral=True)


def main():
    """Main entry point for the bot."""
    try:
        # Load initial data
        load_media_data()
        load_settings()
        
        # Get token from environment or input
        import os
        token = os.getenv('DISCORD_BOT_TOKEN')
        
        if not token:
            logger.error("DISCORD_BOT_TOKEN not found in environment variables")
            raise ValueError("Please set DISCORD_BOT_TOKEN environment variable")
        
        logger.info("Starting GlipaBot...")
        bot.run(token)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
