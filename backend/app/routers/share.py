"""Share page with Open Graph meta tags for social media previews."""

import html
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import DownloadToken, Pack
from app.config import get_settings
from app.services.token import create_download_token

settings = get_settings()
router = APIRouter(tags=["share"])


def _error_page(message: str) -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yoto Library</title>
<style>
body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
       background:#1a1a2e; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
.card {{ text-align:center; padding:2rem; max-width:400px; }}
.card h1 {{ font-size:1.5rem; margin-bottom:1rem; color:#f8f8f8; }}
.card p {{ color:#aaa; }}
</style>
</head>
<body>
<div class="card">
<h1>{html.escape(message)}</h1>
</div>
</body>
</html>""")


@router.get("/share/{token}", response_class=HTMLResponse)
async def share_page(token: str, db: Session = Depends(get_db)):
    db_token = db.query(DownloadToken).filter(DownloadToken.token == token).first()

    if not db_token:
        return _error_page("Lien invalide")

    expires_at = db_token.expires_at
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return _error_page("Ce lien a expiré")

    archive = db_token.archive
    title = html.escape(archive.title or "Archive")
    author = html.escape(archive.author or "")
    description = html.escape(archive.description or author or "")
    download_url = f"/api/download/{html.escape(token)}"
    share_url = f"{settings.base_url}/share/{html.escape(token)}"

    og_image = ""
    cover_img = ""
    if archive.cover_path:
        cover_url = f"{settings.base_url}/api/archives/cover/{html.escape(archive.cover_path)}"
        og_image = f'<meta property="og:image" content="{cover_url}">'
        cover_img = f'<img src="/api/archives/cover/{html.escape(archive.cover_path)}" alt="{title}" style="max-width:300px;width:100%;border-radius:12px;margin-bottom:1.5rem;box-shadow:0 4px 24px rgba(0,0,0,0.4);">'

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Yoto Library</title>
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
{og_image}
<meta property="og:type" content="website">
<meta property="og:url" content="{share_url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<style>
body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
       background:#1a1a2e; color:#e0e0e0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
.card {{ text-align:center; padding:2rem; max-width:400px; }}
.card h1 {{ font-size:1.5rem; margin:0 0 0.5rem; color:#f8f8f8; }}
.card .author {{ color:#aaa; margin-bottom:1rem; font-size:0.95rem; }}
.card .desc {{ color:#ccc; margin-bottom:1.5rem; font-size:0.9rem; line-height:1.5; }}
.btn {{ display:inline-block; padding:0.75rem 2rem; background:#0ea5e9; color:#fff;
        text-decoration:none; border-radius:8px; font-weight:600; font-size:1rem;
        transition:background 0.2s; }}
.btn:hover {{ background:#0284c7; }}
</style>
</head>
<body>
<div class="card">
{cover_img}
<h1>{title}</h1>
{"<p class='author'>" + author + "</p>" if author else ""}
{"<p class='desc'>" + description + "</p>" if description else ""}
<a href="{download_url}" class="btn">Télécharger</a>
<p style="margin-top:2rem;font-size:0.85rem;color:#888;"><a href="/submit" style="color:#0ea5e9;text-decoration:none;">Vous aussi, partagez vos créations &rarr;</a></p>
</div>
</body>
</html>""")


@router.get("/pack/{token}", response_class=HTMLResponse)
async def pack_share_page(token: str, db: Session = Depends(get_db)):
    pack = db.query(Pack).filter(Pack.token == token).first()

    if not pack:
        return _error_page("Pack introuvable")

    expires_at = pack.expires_at
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        return _error_page("Ce pack a expiré")

    pack_name = html.escape(pack.name or "Pack")
    pack_desc = html.escape(pack.description or "Un pack d'histoires audio à écouter sur ta Yoto !")
    download_all_url = f"/api/packs/by-token/{html.escape(token)}/download-all"
    share_url = f"{settings.base_url}/pack/{html.escape(token)}"

    # OG image
    og_image = ""
    if pack.image_path:
        og_image_url = f"{settings.base_url}/api/packs/{pack.id}/image"
        og_image = (
            f'<meta property="og:image" content="{og_image_url}">\n'
            f'<meta property="og:image:type" content="image/jpeg">\n'
            f'<meta name="twitter:image" content="{og_image_url}">'
        )

    # Build archive list HTML
    archives_html = ""
    for archive in pack.archives:
        a_title = html.escape(archive.title or "Archive")
        a_author = html.escape(archive.author or "")

        # Create a reusable 30-day download token for each archive
        dl_token, _ = create_download_token(
            db, archive.id, expiry_seconds=2592000, reusable=True
        )
        dl_url = f"/api/download/{dl_token}"

        cover_html = ""
        if archive.cover_path:
            cover_html = f'<img src="/api/archives/cover/{html.escape(archive.cover_path)}" alt="{a_title}" style="width:80px;height:110px;object-fit:cover;border-radius:8px;flex-shrink:0;">'
        else:
            cover_html = '<div style="width:80px;height:110px;background:#334155;border-radius:8px;flex-shrink:0;display:flex;align-items:center;justify-content:center;color:#64748b;font-size:2rem;">&#128214;</div>'

        size_mb = archive.file_size / (1024 * 1024) if archive.file_size else 0
        archives_html += f"""
<div style="display:flex;gap:1rem;align-items:center;padding:1rem;background:#1e293b;border-radius:12px;">
{cover_html}
<div style="flex:1;min-width:0;">
<div style="font-weight:600;color:#f8fafc;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{a_title}</div>
{"<div style='color:#94a3b8;font-size:0.85rem;'>" + a_author + "</div>" if a_author else ""}
<div style="color:#64748b;font-size:0.8rem;">{size_mb:.1f} MB</div>
</div>
<a href="{dl_url}" style="padding:0.5rem 1rem;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:8px;font-weight:600;font-size:0.85rem;white-space:nowrap;">Télécharger</a>
</div>"""

    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{pack_name} - Yoto Library</title>
<meta property="og:title" content="#JEPARTAGE - {pack_name}">
<meta property="og:description" content="{pack_desc}">
{og_image}
<meta property="og:type" content="website">
<meta property="og:url" content="{share_url}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="#JEPARTAGE - {pack_name}">
<meta name="twitter:description" content="{pack_desc}">
<style>
body {{ margin:0; min-height:100vh; background:#0f172a; color:#e0e0e0;
       font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
.container {{ max-width:600px; margin:0 auto; padding:2rem 1rem; }}
.header {{ text-align:center; margin-bottom:2rem; }}
.header .tag {{ color:#0ea5e9; font-weight:700; font-size:1.1rem; margin-bottom:0.5rem; }}
.header h1 {{ font-size:1.8rem; margin:0 0 0.5rem; color:#f8fafc; }}
.header .desc {{ color:#94a3b8; font-size:0.95rem; line-height:1.5; }}
.download-all {{ display:block; text-align:center; padding:0.9rem 2rem; background:#0ea5e9; color:#fff;
                  text-decoration:none; border-radius:10px; font-weight:700; font-size:1.05rem;
                  margin-bottom:2rem; transition:background 0.2s; }}
.download-all:hover {{ background:#0284c7; }}
.archives {{ display:flex; flex-direction:column; gap:0.75rem; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<div class="tag">#JEPARTAGE</div>
<h1>{pack_name}</h1>
<p class="desc">{pack_desc}</p>
</div>
<a href="{download_all_url}" class="download-all">Tout télécharger ({len(pack.archives)} archive{"s" if len(pack.archives) != 1 else ""})</a>
<div class="archives">
{archives_html}
</div>
</div>
</body>
</html>""")
