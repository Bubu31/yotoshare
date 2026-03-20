import asyncio
import logging
from typing import Optional, List

import discord
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

intents = discord.Intents.none()

bot = discord.Client(
    intents=intents,
    chunk_guilds_at_startup=False,
    member_cache_flags=discord.MemberCacheFlags.none(),
)
bot_ready = asyncio.Event()
bot_error: Optional[str] = None


class DownloadButton(discord.ui.View):
    def __init__(self, archive_id: int):
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="Télécharger",
            style=discord.ButtonStyle.primary,
            emoji="📥",
            custom_id=f"download_{archive_id}",
        )
        self.add_item(button)


class PackDownloadButton(discord.ui.View):
    def __init__(self, pack_id: int):
        super().__init__(timeout=None)
        button = discord.ui.Button(
            label="Télécharger le pack",
            style=discord.ButtonStyle.primary,
            emoji="📦",
            custom_id=f"pack_download_{pack_id}",
        )
        self.add_item(button)


@bot.event
async def on_ready():
    logger.info("Bot connected as %s", bot.user)
    bot_ready.set()


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "")

    # --- Pack download ---
    if custom_id.startswith("pack_download_"):
        try:
            pack_id = int(custom_id.split("_")[2])
        except (IndexError, ValueError):
            try:
                await interaction.response.send_message("❌ Bouton invalide.", ephemeral=True)
            except discord.NotFound:
                pass
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Pack download interaction expired before defer (pack %s)", pack_id)
            return

        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{settings.yotoshare_api_url}/api/service/pack-download",
                    json={"pack_id": pack_id},
                    headers={"X-Service-Key": settings.service_api_key},
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()

            embed = discord.Embed(
                title=f"📦 {data['name']}",
                description=(
                    f"Voici ton lien de téléchargement :\n\n"
                    f"**[Cliquez ici pour télécharger le pack]({data['download_url']})**\n\n"
                    f"⏰ Ce lien expire dans 2 heures."
                ),
                color=discord.Color.green(),
            )
            if data.get("image_url"):
                embed.set_thumbnail(url=data["image_url"])
            embed.set_footer(text="Yoto Library")

            await interaction.user.send(embed=embed)
            await interaction.followup.send(
                "📬 Le lien de téléchargement t'a été envoyé en message privé !",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres de confidentialité.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error("Pack download error: %s", e)
            await interaction.followup.send(f"❌ Une erreur s'est produite: {str(e)}", ephemeral=True)
        return

    # --- Archive download ---
    if custom_id.startswith("download_"):
        try:
            archive_id = int(custom_id.split("_")[1])
        except (IndexError, ValueError):
            try:
                await interaction.response.send_message("❌ Bouton invalide.", ephemeral=True)
            except discord.NotFound:
                pass
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except discord.NotFound:
            logger.warning("Download interaction expired before defer (archive %s)", archive_id)
            return

        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"{settings.yotoshare_api_url}/api/service/download",
                    json={"archive_id": archive_id, "discord_user_id": str(interaction.user.id)},
                    headers={"X-Service-Key": settings.service_api_key},
                    timeout=10.0,
                )
                r.raise_for_status()
                data = r.json()

            embed = discord.Embed(
                title=f"📚 {data['title']}",
                description=(
                    f"Voici ton lien de téléchargement :\n\n"
                    f"**[Cliquez ici pour télécharger]({data['download_url']})**\n\n"
                    f"⏰ Ce lien expire dans 2 heures."
                ),
                color=discord.Color.green(),
            )
            if data.get("cover_url"):
                embed.set_thumbnail(url=data["cover_url"])
            embed.set_footer(text="Yoto Library")

            await interaction.user.send(embed=embed)
            await interaction.followup.send(
                "📬 Le lien de téléchargement t'a été envoyé en message privé !",
                ephemeral=True,
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je ne peux pas t'envoyer de message privé. Vérifie tes paramètres de confidentialité.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error("Download error: %s", e)
            await interaction.followup.send(f"❌ Une erreur s'est produite: {str(e)}", ephemeral=True)


# ─── Helpers ────────────────────────────────────────────────────────────────

def format_duration(ms: int) -> str:
    if not ms:
        return "Inconnu"
    seconds = round(ms / 1000)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    elif minutes > 0:
        return f"{minutes}m {secs:02d}s"
    else:
        return f"{secs}s"


def format_file_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


# ─── Discord actions (called from HTTP endpoints) ────────────────────────────

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
    channel = await bot.fetch_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        raise ValueError(f"Forum channel not found (ID: {settings.discord_forum_channel_id})")

    applied_tags = []
    if categories:
        available_tags = {tag.name.lower(): tag for tag in channel.available_tags}
        for cat_name in categories:
            tag = available_tags.get(cat_name.lower())
            if tag:
                applied_tags.append(tag)

    size_str = f"{file_size / (1024 * 1024):.1f} MB"
    embed = discord.Embed(
        title=f"📖 {title}",
        description=description or "Pas de description",
        color=discord.Color.blue(),
    )
    embed.add_field(name="👤 Auteur", value=author or "Inconnu", inline=True)
    embed.add_field(name="📦 Taille", value=size_str, inline=True)
    if total_duration:
        embed.add_field(name="⏱️ Durée", value=format_duration(total_duration), inline=True)
    if chapters_count:
        embed.add_field(name="📚 Chapitres", value=str(chapters_count), inline=True)

    if chapters:
        chapters_text = ""
        shown = 0
        for i, ch in enumerate(chapters):
            ch_title = ch.get("title") or ch.get("label") or f"Chapitre {i + 1}"
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
    thread_id = result.thread.id if hasattr(result, "thread") else result.id
    return str(thread_id)


async def _do_publish_pack(
    pack_id: int,
    name: str,
    description: str,
    image_url: Optional[str],
    total_size: int,
    archive_titles: List[str],
) -> str:
    channel = await bot.fetch_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        raise ValueError(f"Forum channel not found (ID: {settings.discord_forum_channel_id})")

    embed = discord.Embed(
        title=f"📦 {name}",
        description=description or "Pas de description",
        color=discord.Color.purple(),
    )
    embed.add_field(name="📚 Archives", value=str(len(archive_titles)), inline=True)
    embed.add_field(name="📦 Taille totale", value=format_file_size(total_size), inline=True)

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
    thread_id = result.thread.id if hasattr(result, "thread") else result.id
    return str(thread_id)


async def _do_delete_thread(thread_id: str) -> bool:
    try:
        thread = await bot.fetch_channel(int(thread_id))
        await thread.delete()
        return True
    except discord.NotFound:
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
    try:
        channel = await bot.fetch_channel(int(settings.discord_forum_channel_id))
        if not channel or not isinstance(channel, discord.ForumChannel):
            return False

        thread = await bot.fetch_channel(int(thread_id))

        applied_tags = []
        if categories:
            available_tags = {tag.name.lower(): tag for tag in channel.available_tags}
            for cat_name in categories:
                tag = available_tags.get(cat_name.lower())
                if tag:
                    applied_tags.append(tag)

        await thread.edit(name=title[:100], applied_tags=applied_tags if applied_tags else None)

        size_str = f"{file_size / (1024 * 1024):.1f} MB"
        embed = discord.Embed(
            title=f"📖 {title}",
            description=description or "Pas de description",
            color=discord.Color.blue(),
        )
        embed.add_field(name="👤 Auteur", value=author or "Inconnu", inline=True)
        embed.add_field(name="📦 Taille", value=size_str, inline=True)
        if total_duration:
            embed.add_field(name="⏱️ Durée", value=format_duration(total_duration), inline=True)
        if chapters_count:
            embed.add_field(name="📚 Chapitres", value=str(chapters_count), inline=True)

        if chapters:
            chapters_text = ""
            for i, ch in enumerate(chapters[:15]):
                ch_title = ch.get("title") or ch.get("label") or f"Chapitre {i + 1}"
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

        starter_message = thread.starter_message
        if not starter_message:
            starter_message = await thread.fetch_message(thread.id)

        view = DownloadButton(archive_id) if archive_id else None
        await starter_message.edit(embed=embed, view=view)
        return True
    except Exception as e:
        logger.error("Failed to edit thread %s: %s", thread_id, e)
        return False


async def _do_notify_submission(
    submission_id: int,
    title: Optional[str] = None,
    pseudonym: Optional[str] = None,
    chapters_count: Optional[int] = None,
    file_size: int = 0,
    is_rework: bool = False,
) -> None:
    notify_user_id = settings.notify_user_id
    if not notify_user_id:
        logger.warning("NOTIFY_USER_ID not configured, skipping submission DM")
        return

    try:
        user = await bot.fetch_user(int(notify_user_id))
    except Exception as e:
        logger.error("Failed to fetch notify user %s: %s", notify_user_id, e)
        return

    size_str = format_file_size(file_size) if file_size else "Inconnu"

    if is_rework:
        embed_title = "Re-soumission (rework)"
        embed_color = discord.Color.yellow()
    else:
        embed_title = "Nouvelle soumission"
        embed_color = discord.Color.orange()

    embed = discord.Embed(
        title=embed_title,
        color=embed_color,
    )
    embed.add_field(name="Titre", value=title or "Sans titre", inline=True)
    embed.add_field(name="Pseudo", value=pseudonym or "Anonyme", inline=True)
    if chapters_count:
        embed.add_field(name="Chapitres", value=str(chapters_count), inline=True)
    embed.add_field(name="Taille", value=size_str, inline=True)
    embed.set_footer(text=f"ID soumission : {submission_id}")

    try:
        await user.send(embed=embed)
    except discord.Forbidden:
        logger.error("Cannot DM notify user %s (DMs disabled)", notify_user_id)


async def _do_create_forum_tag(tag_name: str, emoji: str = "🗄️") -> bool:
    channel = await bot.fetch_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        return False
    existing_tags = {tag.name.lower(): tag for tag in channel.available_tags}
    if tag_name.lower() in existing_tags:
        return True
    if len(channel.available_tags) >= 20:
        return False
    new_tag = discord.ForumTag(name=tag_name, emoji=emoji, moderated=False)
    await channel.edit(available_tags=list(channel.available_tags) + [new_tag])
    return True


async def _do_delete_forum_tag(tag_name: str) -> bool:
    channel = await bot.fetch_channel(int(settings.discord_forum_channel_id))
    if not channel or not isinstance(channel, discord.ForumChannel):
        return False
    new_tags = [tag for tag in channel.available_tags if tag.name.lower() != tag_name.lower()]
    if len(new_tags) == len(channel.available_tags):
        return False
    await channel.edit(available_tags=new_tags)
    return True


async def start_bot():
    global bot_error
    try:
        await bot.start(settings.discord_bot_token)
    except discord.LoginFailure as e:
        bot_error = f"Invalid Discord token: {e}"
        logger.error(bot_error)
    except Exception as e:
        bot_error = f"Failed to start bot: {e}"
        logger.error(bot_error)
