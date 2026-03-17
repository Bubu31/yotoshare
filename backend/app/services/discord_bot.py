import logging
import discord
from discord.ext import commands
from typing import Optional, List
import asyncio
import threading
import re
from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(intents=intents)
bot_ready = threading.Event()  # Use threading.Event for cross-thread sync
bot_error: Optional[str] = None
bot_loop: Optional[asyncio.AbstractEventLoop] = None


class DownloadButton(discord.ui.View):
    """View with download button - interactions handled by on_interaction event"""
    def __init__(self, archive_id: int):
        super().__init__(timeout=None)
        # Create button with unique custom_id per archive
        # The actual interaction is handled by the on_interaction event
        button = discord.ui.Button(
            label="Télécharger",
            style=discord.ButtonStyle.primary,
            emoji="📥",
            custom_id=f"download_{archive_id}"
        )
        self.add_item(button)


class PackDownloadButton(discord.ui.View):
    """View with download button for packs - interactions handled by on_interaction event"""
    def __init__(self, pack_id: int):
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="Télécharger le pack",
            style=discord.ButtonStyle.primary,
            emoji="📦",
            custom_id=f"pack_download_{pack_id}"
        )
        self.add_item(button)


@bot.event
async def on_ready():
    global bot_loop
    logger.info("Bot connected as %s", bot.user)
    bot_loop = asyncio.get_event_loop()
    bot_ready.set()


@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle persistent button interactions"""
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "")

    # Handle pack download buttons with format "pack_download_{pack_id}"
    if custom_id.startswith("pack_download_"):
        try:
            pack_id = int(custom_id.split("_")[2])
        except (IndexError, ValueError):
            try:
                await interaction.response.send_message(
                    "❌ Bouton invalide.",
                    ephemeral=True
                )
            except discord.NotFound:
                pass
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Pack download interaction expired before defer (pack %s)", pack_id)
            return

        from app.database import SessionLocal
        from app.models import Pack
        from app.services.token import create_pack_signed_url

        db = None
        try:
            db = SessionLocal()
            pack = db.query(Pack).filter(Pack.id == pack_id).first()
            if not pack:
                await interaction.followup.send(
                    "❌ Pack non trouvé.",
                    ephemeral=True
                )
                return

            download_url, _ = create_pack_signed_url(pack.id)

            embed = discord.Embed(
                title=f"📦 {pack.name}",
                description=f"Voici ton lien de téléchargement :\n\n**[Cliquez ici pour télécharger le pack]({download_url})**\n\n⏰ Ce lien expire dans 2 heures.",
                color=discord.Color.green()
            )

            if pack.image_path:
                image_url = f"{settings.base_url}/api/packs/{pack.id}/image"
                embed.set_thumbnail(url=image_url)

            embed.set_footer(text="Yoto Library")

            await interaction.user.send(embed=embed)
            await interaction.followup.send(
                "📬 Le lien de téléchargement t'a été envoyé en message privé !",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres de confidentialité.",
                ephemeral=True
            )
        except Exception as e:
            logger.error("Pack download error: %s", e)
            await interaction.followup.send(
                f"❌ Une erreur s'est produite: {str(e)}",
                ephemeral=True
            )
        finally:
            if db:
                db.close()
        return

    # Handle download buttons with format "download_{archive_id}"
    if custom_id.startswith("download_"):
        try:
            archive_id = int(custom_id.split("_")[1])
        except (IndexError, ValueError):
            try:
                await interaction.response.send_message(
                    "❌ Bouton invalide.",
                    ephemeral=True
                )
            except discord.NotFound:
                pass
            return

        # CRITICAL: Defer immediately to avoid Discord's 3-second timeout
        # This acknowledges the interaction and shows "thinking..." to the user
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Download interaction expired before defer (archive %s)", archive_id)
            return

        from app.database import SessionLocal
        from app.models import Archive
        from app.services.token import create_download_token, get_download_url

        db = None
        try:
            db = SessionLocal()

            # Get archive info for the DM
            archive = db.query(Archive).filter(Archive.id == archive_id).first()
            if not archive:
                await interaction.followup.send(
                    "❌ Archive non trouvée.",
                    ephemeral=True
                )
                return

            token, expires_at = create_download_token(db, archive_id, str(interaction.user.id), reusable=True)
            download_url = get_download_url(token)

            # Build embed with archive info
            embed = discord.Embed(
                title=f"📚 {archive.title}",
                description=f"Voici ton lien de téléchargement :\n\n**[Cliquez ici pour télécharger]({download_url})**\n\n⏰ Ce lien expire dans 2 heures.",
                color=discord.Color.green()
            )

            # Add cover image if available
            if archive.cover_path:
                cover_url = f"{settings.base_url}/api/archives/cover/{archive.cover_path}"
                embed.set_thumbnail(url=cover_url)

            embed.set_footer(text="Yoto Library")

            await interaction.user.send(embed=embed)
            await interaction.followup.send(
                "📬 Le lien de téléchargement t'a été envoyé en message privé !",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres de confidentialité.",
                ephemeral=True
            )
        except Exception as e:
            logger.error("Download error: %s", e)
            await interaction.followup.send(
                f"❌ Une erreur s'est produite: {str(e)}",
                ephemeral=True
            )
        finally:
            if db:
                db.close()


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    if not seconds:
        return "Inconnu"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    elif minutes > 0:
        return f"{minutes}m {secs:02d}s"
    else:
        return f"{secs}s"


async def _do_publish(
    archive_id: int,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str],
    file_size: int,
    total_duration: Optional[int],
    chapters_count: Optional[int],
    chapters: Optional[List[dict]],
    categories: Optional[List[str]] = None,
) -> str:
    """Internal function that runs in the bot's event loop"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        raise ValueError(f"Guild not found (ID: {settings.discord_guild_id})")

    channel = guild.get_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        raise ValueError(f"Forum channel not found (ID: {settings.discord_forum_channel_id})")

    # Find matching tags from forum's available tags
    applied_tags = []
    if categories:
        available_tags = {tag.name.lower(): tag for tag in channel.available_tags}
        for cat_name in categories:
            tag = available_tags.get(cat_name.lower())
            if tag:
                applied_tags.append(tag)
                logger.debug("Found tag for category '%s'", cat_name)
            else:
                logger.warning("No tag found for category '%s' (available: %s)", cat_name, list(available_tags.keys()))

    size_mb = file_size / (1024 * 1024)
    size_str = f"{size_mb:.1f} MB"

    embed = discord.Embed(
        title=f"📖 {title}",
        description=description or "Pas de description",
        color=discord.Color.blue()
    )
    embed.add_field(name="👤 Auteur", value=author or "Inconnu", inline=True)
    embed.add_field(name="📦 Taille", value=size_str, inline=True)

    if total_duration:
        embed.add_field(name="⏱️ Durée", value=format_duration(total_duration), inline=True)

    if chapters_count:
        embed.add_field(name="📚 Chapitres", value=str(chapters_count), inline=True)

    # Add chapters list if available
    if chapters and len(chapters) > 0:
        chapters_text = ""
        shown = 0
        for i, ch in enumerate(chapters):
            ch_title = ch.get("title") or ch.get("label") or f"Chapitre {i+1}"
            ch_duration = ch.get("duration")
            duration_str = f" ({format_duration(ch_duration)})" if ch_duration else ""
            line = f"• {ch_title}{duration_str}\n"
            remaining_suffix = f"_... et {len(chapters) - shown} autres chapitres_"
            if len(chapters_text) + len(line) + len(remaining_suffix) > 1024:
                chapters_text += remaining_suffix
                break
            chapters_text += line
            shown += 1
        else:
            if shown < len(chapters):
                chapters_text += f"_... et {len(chapters) - shown} autres chapitres_"

        if chapters_text:
            embed.add_field(name="📋 Liste des chapitres", value=chapters_text[:1024], inline=False)

    if cover_url:
        embed.set_thumbnail(url=cover_url)

    embed.set_footer(text="Cliquez sur le bouton ci-dessous pour recevoir le lien de téléchargement")

    view = DownloadButton(archive_id)

    result = await channel.create_thread(
        name=title[:100],
        content="",
        embed=embed,
        view=view,
        applied_tags=applied_tags if applied_tags else None,
    )

    # Handle both ForumThread (has .thread) and Thread objects
    thread_id = result.thread.id if hasattr(result, 'thread') else result.id
    return str(thread_id)


async def publish_archive(
    archive_id: int,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str] = None,
    file_size: int = 0,
    total_duration: Optional[int] = None,
    chapters_count: Optional[int] = None,
    chapters: Optional[List[dict]] = None,
    categories: Optional[List[str]] = None,
) -> Optional[str]:
    global bot_error, bot_loop

    if bot_error:
        raise ValueError(f"Discord bot failed to start: {bot_error}")

    # Wait for bot to be ready (threading.Event works across threads)
    if not bot_ready.wait(timeout=10.0):
        raise ValueError("Discord bot is not ready. Check the bot token configuration.")

    if not bot_loop:
        raise ValueError("Discord bot event loop not available")

    # Run the publish coroutine in the bot's event loop
    future = asyncio.run_coroutine_threadsafe(
        _do_publish(archive_id, title, author, description, cover_url, file_size, total_duration, chapters_count, chapters, categories),
        bot_loop
    )

    # Wait for the result with timeout
    try:
        return future.result(timeout=30.0)
    except Exception as e:
        raise ValueError(f"Failed to publish: {e}")


def format_file_size(size_bytes: int) -> str:
    """Format file size to human readable string"""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


async def _do_publish_pack(
    pack_id: int,
    name: str,
    description: str,
    image_url: Optional[str],
    total_size: int,
    archive_titles: List[str],
) -> str:
    """Internal function that publishes a pack to Discord forum"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        raise ValueError(f"Guild not found (ID: {settings.discord_guild_id})")

    channel = guild.get_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        raise ValueError(f"Forum channel not found (ID: {settings.discord_forum_channel_id})")

    embed = discord.Embed(
        title=f"📦 {name}",
        description=description or "Pas de description",
        color=discord.Color.purple()
    )
    embed.add_field(name="📚 Archives", value=str(len(archive_titles)), inline=True)
    embed.add_field(name="📦 Taille totale", value=format_file_size(total_size), inline=True)

    # Build archive list
    if archive_titles:
        archives_text = ""
        shown = 0
        for title in archive_titles:
            line = f"• {title}\n"
            remaining_suffix = f"_... et {len(archive_titles) - shown} autres_"
            if len(archives_text) + len(line) + len(remaining_suffix) > 1024:
                archives_text += remaining_suffix
                break
            archives_text += line
            shown += 1

        if archives_text:
            embed.add_field(name="📋 Contenu du pack", value=archives_text[:1024], inline=False)

    if image_url:
        embed.set_image(url=image_url)

    embed.set_footer(text="Cliquez sur le bouton ci-dessous pour recevoir le lien de téléchargement")

    view = PackDownloadButton(pack_id)

    result = await channel.create_thread(
        name=name[:100],
        content="",
        embed=embed,
        view=view,
    )

    thread_id = result.thread.id if hasattr(result, 'thread') else result.id
    return str(thread_id)


async def publish_pack(
    pack_id: int,
    name: str,
    description: str,
    image_url: Optional[str] = None,
    total_size: int = 0,
    archive_titles: Optional[List[str]] = None,
) -> Optional[str]:
    global bot_error, bot_loop

    if bot_error:
        raise ValueError(f"Discord bot failed to start: {bot_error}")

    if not bot_ready.wait(timeout=10.0):
        raise ValueError("Discord bot is not ready. Check the bot token configuration.")

    if not bot_loop:
        raise ValueError("Discord bot event loop not available")

    future = asyncio.run_coroutine_threadsafe(
        _do_publish_pack(pack_id, name, description, image_url, total_size, archive_titles or []),
        bot_loop
    )

    try:
        return future.result(timeout=30.0)
    except Exception as e:
        raise ValueError(f"Failed to publish pack: {e}")


async def _do_delete_thread(thread_id: str) -> bool:
    """Delete a Discord forum thread"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        logger.warning("Guild not found for thread deletion")
        return False

    try:
        thread = guild.get_thread(int(thread_id))
        if not thread:
            # Try fetching if not in cache
            try:
                thread = await bot.fetch_channel(int(thread_id))
            except discord.NotFound:
                logger.info("Thread %s not found (already deleted?)", thread_id)
                return True  # Consider success if already gone

        await thread.delete()
        logger.info("Deleted thread %s", thread_id)
        return True
    except Exception as e:
        logger.error("Failed to delete thread %s: %s", thread_id, e)
        return False


async def _do_edit_thread(
    thread_id: str,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str],
    file_size: int,
    total_duration: Optional[int],
    chapters_count: Optional[int],
    chapters: Optional[List[dict]],
    categories: Optional[List[str]] = None,
    archive_id: Optional[int] = None,
) -> bool:
    """Edit a Discord forum thread (name, message, and tags)"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        logger.warning("Guild not found for thread edit")
        return False

    channel = guild.get_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        logger.warning("Forum channel not found for thread edit")
        return False

    try:
        thread = guild.get_thread(int(thread_id))
        if not thread:
            try:
                thread = await bot.fetch_channel(int(thread_id))
            except discord.NotFound:
                logger.warning("Thread %s not found", thread_id)
                return False

        # Find matching tags
        applied_tags = []
        if categories:
            available_tags = {tag.name.lower(): tag for tag in channel.available_tags}
            for cat_name in categories:
                tag = available_tags.get(cat_name.lower())
                if tag:
                    applied_tags.append(tag)

        # Update thread name and tags
        await thread.edit(name=title[:100], applied_tags=applied_tags if applied_tags else None)

        # Build new embed
        size_mb = file_size / (1024 * 1024)
        size_str = f"{size_mb:.1f} MB"

        embed = discord.Embed(
            title=f"📖 {title}",
            description=description or "Pas de description",
            color=discord.Color.blue()
        )
        embed.add_field(name="👤 Auteur", value=author or "Inconnu", inline=True)
        embed.add_field(name="📦 Taille", value=size_str, inline=True)

        if total_duration:
            embed.add_field(name="⏱️ Durée", value=format_duration(total_duration), inline=True)

        if chapters_count:
            embed.add_field(name="📚 Chapitres", value=str(chapters_count), inline=True)

        if chapters and len(chapters) > 0:
            chapters_text = ""
            for i, ch in enumerate(chapters[:15]):
                ch_title = ch.get("title") or ch.get("label") or f"Chapitre {i+1}"
                ch_duration = ch.get("duration")
                duration_str = f" ({format_duration(ch_duration)})" if ch_duration else ""
                chapters_text += f"• {ch_title}{duration_str}\n"

            if len(chapters) > 15:
                chapters_text += f"_... et {len(chapters) - 15} autres chapitres_"

            if chapters_text:
                embed.add_field(name="📋 Liste des chapitres", value=chapters_text, inline=False)

        if cover_url:
            embed.set_thumbnail(url=cover_url)

        embed.set_footer(text="Cliquez sur le bouton ci-dessous pour recevoir le lien de téléchargement")

        # Get and edit the starter message
        starter_message = thread.starter_message
        if not starter_message:
            starter_message = await thread.fetch_message(thread.id)

        # Rebuild the view with download button
        view = DownloadButton(archive_id) if archive_id else None
        await starter_message.edit(embed=embed, view=view)

        logger.info("Edited thread %s", thread_id)
        return True
    except Exception as e:
        logger.error("Failed to edit thread %s: %s", thread_id, e)
        return False


def delete_discord_thread(thread_id: str) -> bool:
    """Delete a Discord thread (thread-safe, synchronous)"""
    global bot_error, bot_loop

    logger.info("Attempting to delete thread '%s'...", thread_id)

    if bot_error:
        logger.error("Bot has error: %s", bot_error)
        return False

    if not bot_ready.is_set():
        logger.warning("Bot not ready, waiting...")
        if not bot_ready.wait(timeout=10.0):
            logger.warning("Bot still not ready after waiting")
            return False

    if not bot_loop:
        logger.warning("Bot loop not available")
        return False

    future = asyncio.run_coroutine_threadsafe(_do_delete_thread(thread_id), bot_loop)
    try:
        result = future.result(timeout=10.0)
        logger.info("Thread deletion result: %s", result)
        return result
    except Exception as e:
        logger.error("Failed to delete thread '%s': %s", thread_id, e)
        return False


def edit_discord_thread(
    thread_id: str,
    title: str,
    author: str,
    description: str,
    cover_url: Optional[str] = None,
    file_size: int = 0,
    total_duration: Optional[int] = None,
    chapters_count: Optional[int] = None,
    chapters: Optional[List[dict]] = None,
    categories: Optional[List[str]] = None,
    archive_id: Optional[int] = None,
) -> bool:
    """Edit a Discord thread (thread-safe, synchronous)"""
    global bot_error, bot_loop

    logger.info("Attempting to edit thread '%s'...", thread_id)

    if bot_error:
        logger.error("Bot has error: %s", bot_error)
        return False

    if not bot_ready.is_set():
        logger.warning("Bot not ready, waiting...")
        if not bot_ready.wait(timeout=10.0):
            logger.warning("Bot still not ready after waiting")
            return False

    if not bot_loop:
        logger.warning("Bot loop not available")
        return False

    future = asyncio.run_coroutine_threadsafe(
        _do_edit_thread(
            thread_id, title, author, description, cover_url,
            file_size, total_duration, chapters_count, chapters,
            categories, archive_id
        ),
        bot_loop
    )
    try:
        result = future.result(timeout=15.0)
        logger.info("Thread edit result: %s", result)
        return result
    except Exception as e:
        logger.error("Failed to edit thread '%s': %s", thread_id, e)
        return False


async def _do_create_forum_tag(tag_name: str, emoji: str = "🗄️") -> bool:
    """Create a tag in the Discord forum channel"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        logger.warning("Guild not found for tag creation")
        return False

    channel = guild.get_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        logger.warning("Forum channel not found for tag creation")
        return False

    # Check if tag already exists
    existing_tags = {tag.name.lower(): tag for tag in channel.available_tags}
    if tag_name.lower() in existing_tags:
        logger.debug("Tag '%s' already exists", tag_name)
        return True

    # Discord limits to 20 tags per forum
    if len(channel.available_tags) >= 20:
        logger.warning("Cannot create tag '%s': forum has reached 20 tags limit", tag_name)
        return False

    # Create new tag with emoji
    new_tag = discord.ForumTag(name=tag_name, emoji=emoji, moderated=False)
    new_tags = list(channel.available_tags) + [new_tag]
    await channel.edit(available_tags=new_tags)
    logger.info("Created forum tag '%s' with emoji %s", tag_name, emoji)
    return True


async def _do_delete_forum_tag(tag_name: str) -> bool:
    """Delete a tag from the Discord forum channel"""
    guild = bot.get_guild(int(settings.discord_guild_id))
    if not guild:
        logger.warning("Guild not found for tag deletion")
        return False

    channel = guild.get_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        logger.warning("Forum channel not found for tag deletion")
        return False

    # Find and remove the tag
    new_tags = [tag for tag in channel.available_tags if tag.name.lower() != tag_name.lower()]
    if len(new_tags) == len(channel.available_tags):
        logger.warning("Tag '%s' not found", tag_name)
        return False

    await channel.edit(available_tags=new_tags)
    logger.info("Deleted forum tag '%s'", tag_name)
    return True


def create_forum_tag(tag_name: str, emoji: str = "🗄️") -> bool:
    """Create a forum tag (thread-safe, synchronous)"""
    global bot_error, bot_loop

    logger.info("Attempting to create tag '%s' with emoji %s...", tag_name, emoji)

    if bot_error:
        logger.error("Bot has error: %s", bot_error)
        return False

    if not bot_ready.is_set():
        logger.warning("Bot not ready, waiting...")
        if not bot_ready.wait(timeout=10.0):
            logger.warning("Bot still not ready after waiting")
            return False

    if not bot_loop:
        logger.warning("Bot loop not available")
        return False

    future = asyncio.run_coroutine_threadsafe(_do_create_forum_tag(tag_name, emoji), bot_loop)
    try:
        result = future.result(timeout=10.0)
        logger.info("Tag creation result: %s", result)
        return result
    except Exception as e:
        logger.error("Failed to create tag '%s': %s", tag_name, e)
        return False


def delete_forum_tag(tag_name: str) -> bool:
    """Delete a forum tag (thread-safe, synchronous)"""
    global bot_error, bot_loop

    logger.info("Attempting to delete tag '%s'...", tag_name)

    if bot_error:
        logger.error("Bot has error: %s", bot_error)
        return False

    if not bot_ready.is_set():
        logger.warning("Bot not ready, waiting...")
        if not bot_ready.wait(timeout=10.0):
            logger.warning("Bot still not ready after waiting")
            return False

    if not bot_loop:
        logger.warning("Bot loop not available")
        return False

    future = asyncio.run_coroutine_threadsafe(_do_delete_forum_tag(tag_name), bot_loop)
    try:
        result = future.result(timeout=10.0)
        logger.info("Tag deletion result: %s", result)
        return result
    except Exception as e:
        logger.error("Failed to delete tag '%s': %s", tag_name, e)
        return False


async def start_bot():
    global bot_error
    if settings.discord_bot_token:
        try:
            await bot.start(settings.discord_bot_token)
        except discord.LoginFailure as e:
            bot_error = f"Invalid Discord token: {e}"
            logger.error(bot_error)
        except Exception as e:
            bot_error = f"Failed to start bot: {e}"
            logger.error(bot_error)


def run_bot_in_background():
    if settings.discord_bot_token:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(start_bot())
        except Exception as e:
            global bot_error
            bot_error = str(e)
            logger.error("Bot error: %s", e)
