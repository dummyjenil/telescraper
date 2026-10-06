"""
TeleScraper Interactive Master CLI & Control Center.
Built-in component of the TeleScraper library (100% Pure Synchronous MTProto 2.0 Engine).
Equipped with arrow-key keyboard navigation (↑/↓), multi-select, and live Rich UI.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from .client import TeleScraper
from .network.connection import (
    ConnectionHttp,
    ConnectionTcpAbridged,
    ConnectionTcpFull,
    ConnectionTcpIntermediate,
    ConnectionTcpMTProxyIntermediate,
    ConnectionTcpObfuscated,
    ConnectionTcpRandomizedIntermediate,
)
from .sessions.string_session import StringSession
from .utils import get_display_name

# Rich & Questionary & QRCode
try:
    import questionary
    from questionary import Choice, Separator, Style
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
    from rich.table import Table

    HAS_LIBS = True
except ImportError:
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "rich", "qrcode", "questionary", "openpyxl", "pandas"]
    )
    import questionary
    from questionary import Choice, Separator, Style
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn, TransferSpeedColumn
    from rich.table import Table

    HAS_LIBS = True

console = Console()

CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:#00ffff bold"),
        ("question", "bold fg:#ffffff"),
        ("answer", "fg:#00ff88 bold"),
        ("pointer", "fg:#00ffff bold"),
        ("highlighted", "fg:#00ffff bold underline"),
        ("selected", "fg:#00ff88 bold"),
        ("separator", "fg:#6c7086"),
        ("instruction", "fg:#a6adc8 italic"),
    ]
)

CONFIG_FILE = Path.cwd() / "config.json"
DEFAULT_SESSION_NAME = "my_telegram"

TRANSPORTS_MAP = {
    "intermediate": ConnectionTcpIntermediate,
    "randomized": ConnectionTcpRandomizedIntermediate,
    "obfuscated": ConnectionTcpObfuscated,
    "mtproxy": ConnectionTcpMTProxyIntermediate,
    "full": ConnectionTcpFull,
    "abridged": ConnectionTcpAbridged,
    "http": ConnectionHttp,
}


# ==============================================================================
# Configuration Management
# ==============================================================================


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not save config: {e}[/yellow]")


def get_credentials(
    api_id: Optional[int] = None, api_hash: Optional[str] = None, session_name: Optional[str] = None
) -> tuple[int, str, str]:
    cfg = load_config()
    final_api_id = api_id or cfg.get("api_id")
    final_api_hash = api_hash or cfg.get("api_hash")
    final_session = session_name or cfg.get("session_name", DEFAULT_SESSION_NAME)

    if not final_api_id or not final_api_hash:
        console.print(
            Panel(
                "[bold cyan]Telegram API Credentials Setup[/bold cyan]\n\n"
                "To connect to Telegram MTProto, you need an [bold]API ID[/bold] and [bold]API Hash[/bold].\n"
                "Get them instantly for free from [link=https://my.telegram.org]https://my.telegram.org[/link] (API development tools).",
                border_style="cyan",
            )
        )

        while not final_api_id:
            val = questionary.text("Enter your Telegram API ID:", style=CUSTOM_STYLE).ask()
            if val and val.strip().isdigit():
                final_api_id = int(val.strip())
            else:
                console.print("[red]API ID must be an integer.[/red]")

        while not final_api_hash:
            val = questionary.text("Enter your Telegram API Hash:", style=CUSTOM_STYLE).ask()
            if val and val.strip():
                final_api_hash = val.strip()

        if questionary.confirm(
            "Save these credentials in config.json for future use?", default=True, style=CUSTOM_STYLE
        ).ask():
            cfg["api_id"] = final_api_id
            cfg["api_hash"] = final_api_hash
            cfg["session_name"] = final_session
            save_config(cfg)
            console.print("[green]✔ Credentials saved to config.json[/green]")

    return int(final_api_id), str(final_api_hash), str(final_session)


def get_client(
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
    transport: str = "intermediate",
    proxy: Optional[tuple] = None,
) -> TeleScraper:
    aid, ahash, sname = get_credentials(api_id, api_hash, session_name)
    session_path = Path.cwd() / f"{sname}.session"
    conn_cls = TRANSPORTS_MAP.get(transport.lower(), ConnectionTcpIntermediate)
    return TeleScraper(session=str(session_path), api_id=aid, api_hash=ahash, connection=conn_cls, proxy=proxy)


# ==============================================================================
# Helper for Selecting Chats / Dialogs Interactively
# ==============================================================================


def pick_chat_interactively(client: TeleScraper, allow_custom: bool = True) -> str:
    """Prompt user to select a chat from their joined dialogs with arrow keys, or type custom username."""
    with console.status("[cyan]Loading your dialogs & channels...[/cyan]"):
        try:
            chats = client.get_chats()
        except Exception:
            chats = []

    choices = []
    if allow_custom:
        choices.append(Choice(title="✏️  Enter Custom Username / Chat ID / Invite Link", value="__CUSTOM__"))
        choices.append(Separator())

    for c in chats:
        ctype = (
            "📢 Channel"
            if c.is_channel
            else ("👥 Supergroup" if c.is_megagroup else ("👥 Group" if c.is_group else "👤 Chat"))
        )
        uname = f"(@{c.username})" if c.username else ""
        title = f"{ctype} | {c.title[:30]} {uname} [ID: {c.id}]"
        val = c.username or str(c.id)
        choices.append(Choice(title=title, value=val))

    if not chats and not allow_custom:
        return questionary.text("Enter target username or chat ID (e.g. @channel or me):", style=CUSTOM_STYLE).ask()

    res = questionary.select(
        "Select a Target Chat / Channel:", choices=choices, style=CUSTOM_STYLE, use_shortcuts=True
    ).ask()

    if res == "__CUSTOM__" or res is None:
        return questionary.text("Enter target username or chat ID (e.g. @channel or me):", style=CUSTOM_STYLE).ask()
    return res


# ==============================================================================
# 1. Authentication & QR Code
# ==============================================================================


def cmd_login_qr(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None, timeout: int = 120
) -> None:
    client = get_client(session_name, api_id, api_hash)
    console.print(Panel("[bold green]Starting Telegram QR Code Login Engine...[/bold green]", border_style="green"))
    client.connect()

    if client.is_user_authorized():
        me = client.get_me()
        console.print(
            f"[bold green]✔ Already logged in as:[/bold green] [bold cyan]{me.first_name} (@{me.username or 'No username'})[/bold cyan] (ID: {me.id})"
        )
        console.print(f"[blue]Active session file:[/blue] {getattr(client.session, 'filename', 'active session')}")
        return

    qr = client.qr_login(print_qr=True)
    try:
        user = qr.wait(timeout=timeout, auto_handle_2fa=True)
        console.print(
            Panel(
                f"[bold green]🎉 QR LOGIN SUCCESSFUL![/bold green]\n\n"
                f"[bold]Name:[/bold] {get_display_name(user)}\n"
                f"[bold]User ID:[/bold] {user.id}\n"
                f"[bold]Username:[/bold] @{getattr(user, 'username', 'N/A')}\n"
                f"[bold]Session File Saved:[/bold] {getattr(client.session, 'filename', 'active session')}",
                border_style="green",
                title="Authorized",
            )
        )
    except TimeoutError:
        console.print("[red]❌ QR Login timed out without being scanned. Please try again.[/red]")


def cmd_login_phone(
    phone: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if client.is_user_authorized():
        me = client.get_me()
        console.print(f"[green]✔ Already logged in as:[/green] {me.first_name} (ID: {me.id})")
        return

    target_phone = phone or questionary.text("Enter your phone number (e.g. +1234567890):", style=CUSTOM_STYLE).ask()
    console.print(f"[cyan]Sending OTP code to {target_phone}...[/cyan]")
    client.start(phone=target_phone)
    console.print("[bold green]✔ Login successful![/bold green]")


def cmd_login_bot(
    bot_token: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    token = bot_token or questionary.text("Enter Bot Token (from @BotFather):", style=CUSTOM_STYLE).ask()
    client.bot_login(token)
    console.print("[bold green]✔ Bot login successful![/bold green]")


def cmd_export_string_session(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if not client.is_user_authorized():
        console.print("[red]❌ Client is not authorized. Please login first.[/red]")
        return

    str_session = StringSession.save(client.session)
    console.print(
        Panel(
            f"[bold green]Base64 StringSession (Telethon & TeleScraper Compatible):[/bold green]\n\n"
            f"[yellow]{str_session}[/yellow]\n\n"
            f"[dim]Keep this secret! It grants full access to your Telegram account.[/dim]",
            border_style="green",
            title="StringSession Export",
        )
    )


def cmd_whoami(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if not client.is_user_authorized():
        console.print("[red]❌ Not logged in! Run QR Login or Phone Login first.[/red]")
        return

    me = client.get_me()
    table = Table(title="👤 Authenticated Account Profile", border_style="cyan")
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("User ID", str(me.id))
    table.add_row("First Name", str(me.first_name or ""))
    table.add_row("Last Name", str(me.last_name or ""))
    table.add_row("Username", f"@{me.username}" if me.username else "None")
    table.add_row("Account Type", "🤖 Bot" if me.is_bot else "👤 User Account")
    table.add_row("Online Status", str(me.status or "N/A"))
    table.add_row("Session File", str(getattr(client.session, "filename", "active session")))

    console.print(table)


# ==============================================================================
# 2. Chats, Scraping, Data Extraction & Exporters
# ==============================================================================


def cmd_list_chats(
    filter_type: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    with console.status("[cyan]Fetching dialogs & channels...[/cyan]"):
        types_filter = [filter_type] if filter_type else None
        chats = client.get_chats(types_filter=types_filter)

    table = Table(title=f"📋 Dialogs & Channels ({len(chats)} found)", border_style="cyan")
    table.add_column("ID", style="bold yellow")
    table.add_column("Title", style="bold white")
    table.add_column("Type", style="green")
    table.add_column("Username", style="cyan")
    table.add_column("Members", style="magenta")

    for c in chats:
        ctype = "Channel" if c.is_channel else ("Supergroup" if c.is_megagroup else ("Group" if c.is_group else "Chat"))
        uname = f"@{c.username}" if c.username else "-"
        members = str(c.participants_count) if c.participants_count else "-"
        table.add_row(str(c.id), c.title[:35], ctype, uname, members)

    console.print(table)


def cmd_chat_info(
    target: str, session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    with console.status(f"[cyan]Fetching info for {target}...[/cyan]"):
        info = client.get_chat_info(target)

    table = Table(title=f"ℹ️ Chat Information: {info.title}", border_style="green")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Title", info.title)
    table.add_row("ID", str(info.id))
    table.add_row("Username", f"@{info.username}" if info.username else "None")
    table.add_row("Subscribers / Members", str(info.participants_count or "N/A"))
    table.add_row("Type", "Channel" if info.is_channel else ("Group" if info.is_group else "Chat"))
    table.add_row("Description / About", str(getattr(info, "description", "") or "None"))

    console.print(table)


def cmd_scrape(
    target: str,
    limit: int = 50,
    search: Optional[str] = None,
    filter_type: Optional[str] = None,
    checkpoint: Optional[str] = None,
    output: Optional[str] = None,
    reverse: bool = False,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(
        f"[cyan]Scraping up to {limit} messages from [bold]{target}[/bold] (Filter: {filter_type or 'All'}, Search: {search or 'None'})...[/cyan]"
    )

    messages = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.completed}/{task.total} msgs"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching messages...", total=limit)

        for msg in client.iter_messages(
            target=target, limit=limit, search=search, filter_type=filter_type, reverse=reverse, checkpoint=checkpoint
        ):
            messages.append(msg)
            progress.update(task, advance=1)

    table = Table(title=f"📩 Scraped Messages ({len(messages)} items)", border_style="blue")
    table.add_column("ID", style="yellow", width=8)
    table.add_column("Date", style="dim", width=19)
    table.add_column("Media", style="magenta", width=10)
    table.add_column("Views", style="cyan", width=6)
    table.add_column("Text Preview", style="white")

    for m in messages[:30]:
        med = m.media.media_type if m.media else "-"
        txt = (m.text or "").replace("\n", " ")[:60]
        v = str(m.views) if m.views is not None else "-"
        d = str(m.date)[:19] if m.date else "-"
        table.add_row(str(m.id), d, med, v, txt)

    console.print(table)
    if len(messages) > 30:
        console.print(f"[dim]... and {len(messages) - 30} more messages.[/dim]")

    if output:
        ext = Path(output).suffix.lower()
        if ext == ".xlsx":
            client.export_to_excel(target, output, limit=limit)
        elif ext == ".csv":
            client.export_to_csv(target, output, limit=limit)
        elif ext == ".db":
            client.export_to_sqlite(target, output, limit=limit)
        else:
            client.export_to_json(target, output, limit=limit)
        console.print(f"[bold green]✔ Saved dataset to {output}[/bold green]")


def cmd_takeout(
    target: str,
    limit: int = 1000,
    output: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(f"[bold cyan]Starting High-Speed Takeout Session for {target}...[/bold cyan]")
    messages = []

    with client.takeout(message_channels=True, message_chats=True, files=True) as takeout:
        for msg in takeout.iter_messages(target, limit=limit):
            messages.append(msg)

    console.print(f"[bold green]✔ Successfully scraped {len(messages)} messages via Takeout session.[/bold green]")
    if output:
        client.export_to_json(target, output, limit=limit)
        console.print(f"[green]Saved to {output}[/green]")


def cmd_comments(
    target: str,
    post_id: int,
    limit: int = 50,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(f"[cyan]Scraping comments for post [bold]#{post_id}[/bold] in [bold]{target}[/bold]...[/cyan]")
    comments = []

    for c in client.iter_comments(target, post_id=post_id, limit=limit):
        comments.append(c)

    table = Table(title=f"💬 Comments for Post #{post_id} ({len(comments)} found)", border_style="cyan")
    table.add_column("ID", style="yellow", width=8)
    table.add_column("Sender", style="bold green")
    table.add_column("Comment Text", style="white")

    for c in comments:
        sender = c.sender_name or f"User {c.sender_id or 'Unknown'}"
        txt = (c.text or "").replace("\n", " ")[:80]
        table.add_row(str(c.id), sender, txt)

    console.print(table)


def cmd_members(
    target: str,
    limit: int = 100,
    output: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(f"[cyan]Scraping up to {limit} members from [bold]{target}[/bold]...[/cyan]")
    members = []

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task("Fetching participants...", total=None)
        for mem in client.iter_members(target, limit=limit):
            members.append(mem)

    table = Table(title=f"👥 Members in {target} ({len(members)} scraped)", border_style="green")
    table.add_column("User ID", style="yellow")
    table.add_column("Username", style="cyan")
    table.add_column("Full Name", style="white")
    table.add_column("Role/Status", style="magenta")
    table.add_column("Bot?", style="dim")

    for m in members[:40]:
        uname = f"@{m.username}" if m.username else "-"
        name = f"{m.first_name or ''} {m.last_name or ''}".strip()
        is_bot = "🤖 Yes" if m.is_bot else "No"
        table.add_row(str(m.id), uname, name, str(m.status or "Member"), is_bot)

    console.print(table)
    if len(members) > 40:
        console.print(f"[dim]... and {len(members) - 40} more members.[/dim]")

    if output:
        data = [
            {
                "id": m.id,
                "username": m.username,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "is_bot": m.is_bot,
                "status": m.status,
            }
            for m in members
        ]
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        console.print(f"[bold green]✔ Saved member list to {output}[/bold green]")


def cmd_extract(
    target: str,
    limit: int = 100,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(f"[cyan]Scanning {limit} messages in [bold]{target}[/bold] for sensitive & structured data...[/cyan]")
    data = client.extract_from_messages(target, limit=limit)

    console.print(
        Panel(
            f"[bold cyan]🔍 Entity Extraction Results for {target}[/bold cyan]\n\n"
            f"[bold]📧 Emails Found ({len(data.get('emails', []))}):[/bold] {', '.join(data.get('emails', [])) or 'None'}\n"
            f"[bold]📞 Phone Numbers ({len(data.get('phones', []))}):[/bold] {', '.join(data.get('phones', [])) or 'None'}\n"
            f"[bold]🔗 URLs ({len(data.get('urls', []))}):[/bold] {len(data.get('urls', []))} discovered\n\n"
            f"[bold yellow]💰 Crypto Wallets Discovered:[/bold yellow]\n"
            f"  • Bitcoin (BTC): {len(data.get('wallets', {}).get('bitcoin', []))}\n"
            f"  • Ethereum (ETH): {len(data.get('wallets', {}).get('ethereum', []))}\n"
            f"  • USDT TRC20: {len(data.get('wallets', {}).get('tron', []))}\n"
            f"  • TON: {len(data.get('wallets', {}).get('ton', []))}\n"
            f"  • Solana (SOL): {len(data.get('wallets', {}).get('solana', []))}",
            border_style="yellow",
        )
    )

    wallets = data.get("wallets", {})
    for chain, addrs in wallets.items():
        if addrs:
            console.print(f"\n[bold green]-- {chain.upper()} ({len(addrs)}) --[/bold green]")
            for a in addrs:
                console.print(f"  {a}")


def cmd_export(
    target: str,
    output: str,
    format_type: str = "json",
    limit: int = 500,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    console.print(
        f"[cyan]Exporting {limit} messages from [bold]{target}[/bold] to [bold]{output}[/bold] ({format_type})...[/cyan]"
    )
    fmt = format_type.lower()
    if fmt in ("xlsx", "excel"):
        client.export_to_excel(target, output, limit=limit)
    elif fmt == "csv":
        client.export_to_csv(target, output, limit=limit)
    elif fmt in ("sqlite", "db"):
        client.export_to_sqlite(target, output, limit=limit)
    else:
        client.export_to_json(target, output, limit=limit)

    console.print(f"[bold green]✔ Successfully exported dataset to {output}[/bold green]")


# ==============================================================================
# 3. Media & File Downloader / Uploader
# ==============================================================================


def cmd_download_media(
    target: str,
    limit: int = 10,
    output_dir: str = "./downloads",
    media_types: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    m_types = (
        media_types.split(",") if isinstance(media_types, str) else (media_types or ["photo", "document", "video"])
    )
    console.print(
        f"[cyan]Downloading media from [bold]{target}[/bold] into [bold]{output_dir}[/bold] (Limit: {limit}, Types: {m_types})...[/cyan]"
    )

    os.makedirs(output_dir, exist_ok=True)
    paths = client.download_all_media(target=target, output_dir=output_dir, limit=limit, media_types=m_types)
    console.print(f"[bold green]✔ Downloaded {len(paths)} files to {output_dir}[/bold green]")


def cmd_avatar_manager(
    action: str,
    target: str = "me",
    file_path: Optional[str] = None,
    output_dir: str = "./avatars",
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "download":
        os.makedirs(output_dir, exist_ok=True)
        path = client.download_profile_photo(target, output_dir=output_dir)
        if path:
            console.print(f"[bold green]✔ Profile photo saved to:[/bold green] {path}")
        else:
            console.print(f"[yellow]No profile photo found for {target}[/yellow]")
    elif action == "upload":
        if not file_path or not Path(file_path).exists():
            console.print(f"[red]❌ File not found: {file_path}[/red]")
            return
        client.set_profile_photo(file_path, workers=4)
        console.print("[bold green]✔ Profile photo updated successfully![/bold green]")
    elif action == "history":
        photos = client.get_profile_photos(target, limit=10)
        console.print(f"[green]Found {len(photos)} profile photos in history.[/green]")
        for p in photos:
            console.print(f"  • Photo ID: {p.id} (Date: {p.date})")
    elif action == "delete":
        photos = client.get_profile_photos("me", limit=1)
        if photos:
            client.delete_profile_photos([photos[0].id])
            console.print("[bold green]✔ Latest profile photo deleted.[/bold green]")
        else:
            console.print("[yellow]No profile photos to delete.[/yellow]")


def cmd_upload_file(
    target: str,
    file_path: str,
    caption: Optional[str] = None,
    workers: int = 4,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    p = Path(file_path)
    if not p.exists():
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        return

    file_size = p.stat().st_size
    console.print(
        f"[cyan]Uploading [bold]{p.name}[/bold] ({file_size / (1024 * 1024):.2f} MB) to [bold]{target}[/bold] using {workers} workers...[/cyan]"
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Uploading...", total=file_size)

        def on_prog(uploaded, total):
            progress.update(task, completed=uploaded)

        msg = client.send_file(
            target=target, file=str(p), caption=caption or "", workers=workers, progress_callback=on_prog
        )

    console.print(f"[bold green]✔ File successfully uploaded & sent! (Message ID: {msg.id})[/bold green]")


# ==============================================================================
# 4. Message Operations
# ==============================================================================


def cmd_send_message(
    target: str,
    message: str,
    reply_to: Optional[int] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    msg = client.send_message(target, message, reply_to=reply_to)
    console.print(f"[bold green]✔ Message sent! (ID: {msg.id})[/bold green]")


def cmd_edit_message(
    target: str,
    message_id: int,
    new_text: str,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.edit_message(target, message_id, new_text)
    console.print(f"[bold green]✔ Message #{message_id} edited successfully![/bold green]")


def cmd_delete_messages(
    target: str,
    message_ids: List[int],
    revoke: bool = True,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.delete_messages(target, message_ids, revoke=revoke)
    console.print(f"[bold green]✔ Deleted messages {message_ids} from {target}[/bold green]")


def cmd_pin_message(
    target: str,
    message_id: int,
    notify: bool = False,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.pin_message(target, message_id, notify=notify)
    console.print(f"[bold green]✔ Message #{message_id} pinned in {target}[/bold green]")


def cmd_send_reaction(
    target: str,
    message_id: int,
    reaction: str = "🔥",
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.send_reaction(target, message_id, reaction=reaction)
    console.print(f"[bold green]✔ Sent reaction {reaction} to message #{message_id}[/bold green]")


def cmd_save_draft(
    target: str,
    message: str,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.save_draft(target, message)
    console.print(f"[bold green]✔ Draft saved for {target}[/bold green]")


# ==============================================================================
# 5. Group & Channel Administration & Moderation
# ==============================================================================


def cmd_create_channel(
    title: str,
    about: str = "",
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    ch = client.create_channel(title=title, about=about)
    console.print(f"[bold green]✔ Broadcast Channel created: {title} (ID: {getattr(ch, 'id', 'created')})[/bold green]")


def cmd_create_group(
    title: str,
    users: Optional[List[str]] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    grp = client.create_group(title=title, users=users)
    console.print(f"[bold green]✔ Supergroup created: {title} (ID: {getattr(grp, 'id', 'created')})[/bold green]")


def cmd_kick_user(
    target: str,
    user: str,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.kick_participant(target, user)
    console.print(f"[bold green]✔ Kicked user {user} from {target}[/bold green]")


def cmd_edit_permissions(
    target: str,
    user: str,
    send_messages: bool = True,
    send_media: bool = True,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    client.edit_permissions(target, user, send_messages=send_messages, send_media=send_media)
    console.print(f"[bold green]✔ Updated permissions for {user} in {target}[/bold green]")


def cmd_admin_log(
    target: str,
    limit: int = 50,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    events = client.get_admin_log(target, limit=limit)
    table = Table(title=f"🛡️ Admin Audit Log for {target} ({len(events)} events)", border_style="red")
    table.add_column("Date", style="dim")
    table.add_column("User ID", style="yellow")
    table.add_column("Action", style="white")

    for ev in events:
        table.add_row(
            str(getattr(ev, "date", "")),
            str(getattr(ev, "user_id", "")),
            str(type(getattr(ev, "action", None)).__name__),
        )
    console.print(table)


def cmd_invite_link_manager(
    action: str,
    target: str,
    title: Optional[str] = None,
    link: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "create":
        res = client.create_invite_link(target, title=title)
        console.print(f"[bold green]✔ Created Invite Link:[/bold green] {getattr(res, 'link', res)}")
    elif action == "revoke":
        if not link:
            link = questionary.text("Enter invite link URL to revoke:", style=CUSTOM_STYLE).ask()
        if link:
            client.revoke_invite_link(target, link=link)
            console.print(f"[bold green]✔ Revoked invite link {link}[/bold green]")
    elif action == "list":
        links = client.get_invite_links(target)
        table = Table(title=f"🔗 Active Invite Links for {target}", border_style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Link", style="bold green")
        table.add_column("Usage", style="yellow")
        for link_item in links:
            table.add_row(
                str(getattr(link_item, "title", "-")),
                str(getattr(link_item, "link", "-")),
                f"{getattr(link_item, 'usage', 0)}/{getattr(link_item, 'usage_limit', '∞')}",
            )
        console.print(table)


# ==============================================================================
# 6. Telegram Stories
# ==============================================================================


def cmd_stories(
    action: str,
    target: str = "me",
    file_path: Optional[str] = None,
    caption: Optional[str] = None,
    story_id: Optional[int] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "get":
        stories = client.get_peer_stories(target)
        console.print(f"[cyan]Stories for {target}:[/cyan] {stories}")
    elif action == "post":
        if not file_path or not Path(file_path).exists():
            file_path = questionary.text("Enter story image/video path:", style=CUSTOM_STYLE).ask()
        if file_path and Path(file_path).exists():
            st = client.post_story(target=target, file_path=file_path, caption=caption or "", workers=4)
            console.print(f"[bold green]✔ Story posted successfully! (ID: {getattr(st, 'id', 'ok')})[/bold green]")
        else:
            console.print(f"[red]❌ File not found: {file_path}[/red]")
    elif action == "delete":
        if not story_id:
            val = questionary.text("Enter Story ID to delete:", style=CUSTOM_STYLE).ask()
            story_id = int(val) if val and val.isdigit() else None
        if story_id:
            client.delete_stories(target=target, story_ids=[story_id])
            console.print(f"[bold green]✔ Deleted story #{story_id}[/bold green]")


# ==============================================================================
# 7. State Sync & Gap Recovery
# ==============================================================================


def cmd_state_sync(
    action: str = "state",
    channel: Optional[str] = None,
    pts: Optional[int] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "state":
        st = client.get_state()
        table = Table(title="🔄 Telegram Account Update State", border_style="cyan")
        table.add_column("Field", style="bold cyan")
        table.add_column("Value", style="white")
        table.add_row("PTS (Persistent Timed Sequence)", str(st.pts))
        table.add_row("QTS (Secret Chat Sequence)", str(st.qts))
        table.add_row("Date", str(st.date))
        table.add_row("Seq", str(st.seq))
        console.print(table)
    elif action == "difference":
        st = client.get_state()
        diff = client.get_difference(pts=pts or (st.pts - 50))
        console.print(f"[bold green]✔ Recovered Difference:[/bold green] {diff}")
    elif action == "channel-diff":
        ch = channel or pick_chat_interactively(client)
        if not pts:
            val = questionary.text("Enter current PTS sequence value:", style=CUSTOM_STYLE).ask()
            pts = int(val) if val and val.isdigit() else 1
        diff = client.get_channel_difference(channel=ch, pts=pts)
        console.print(f"[bold green]✔ Channel Difference:[/bold green] {diff}")


# ==============================================================================
# 8. VoIP Signalling & Secret Chats
# ==============================================================================


def cmd_voip(
    action: str,
    target: Optional[str] = None,
    call_id: Optional[int] = None,
    access_hash: Optional[int] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "config":
        cfg = client.voip.get_call_config()
        console.print(
            Panel(f"[bold cyan]VoIP Configuration & STUN/TURN Servers:[/bold cyan]\n\n{cfg}", border_style="blue")
        )
    elif action == "request":
        tgt = target or questionary.text("Enter username to call:", style=CUSTOM_STYLE).ask()
        if tgt:
            res = client.voip.request_call(tgt)
            console.print(f"[bold green]✔ Outgoing call requested to {tgt}:[/bold green] {res}")
    elif action == "discard":
        if not call_id:
            val = questionary.text("Enter Call ID:", style=CUSTOM_STYLE).ask()
            call_id = int(val) if val and val.isdigit() else None
        if not access_hash:
            val = questionary.text("Enter Access Hash:", style=CUSTOM_STYLE).ask()
            access_hash = int(val) if val and val.isdigit() else None
        if call_id and access_hash:
            client.voip.discard_call(call_id=call_id, access_hash=access_hash)
            console.print(f"[bold green]✔ Call #{call_id} discarded.[/bold green]")


def cmd_secret_chat(
    target: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    tgt = target or questionary.text("Enter target username for E2EE Secret Chat:", style=CUSTOM_STYLE).ask()
    if tgt:
        console.print(f"[cyan]Initiating End-to-End Encrypted (E2EE) Secret Chat with {tgt}...[/cyan]")
        sc = client.create_secret_chat(tgt)
        console.print(f"[bold green]✔ Secret Chat requested! (ID: {sc.chat_id})[/bold green]")


# ==============================================================================
# 9. Session & Device Administration
# ==============================================================================


def cmd_list_sessions(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    auths = client.get_authorizations()
    table = Table(title=f"💻 Active Authorized Devices ({len(auths)})", border_style="cyan")
    table.add_column("Hash", style="yellow")
    table.add_column("Device Model", style="bold white")
    table.add_column("Platform / App", style="cyan")
    table.add_column("IP Address", style="magenta")
    table.add_column("Country", style="green")
    table.add_column("Current?", style="bold green")

    for a in auths:
        is_cur = "✔ YES" if getattr(a, "current", False) else ""
        table.add_row(
            str(a.hash), f"{a.device_model} ({a.app_name} {a.app_version})", a.platform, a.ip, a.country, is_cur
        )

    console.print(table)


def cmd_terminate_session(
    auth_hash: int, session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()
    res = client.terminate_session(hash=auth_hash)
    console.print(f"[bold green]✔ Session with hash {auth_hash} terminated: {res}[/bold green]")


def cmd_reset_sessions(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    if questionary.confirm(
        "Are you sure you want to terminate all other active Telegram sessions?", default=False, style=CUSTOM_STYLE
    ).ask():
        client = get_client(session_name, api_id, api_hash)
        client.connect()
        res = client.reset_authorizations()
        if res:
            console.print("[bold green]✔ All other remote sessions terminated successfully.[/bold green]")
        else:
            console.print("[red]❌ Could not reset authorizations.[/red]")


def cmd_logout(
    session_name: Optional[str] = None, api_id: Optional[int] = None, api_hash: Optional[str] = None
) -> None:
    if questionary.confirm("Are you sure you want to log out from Telegram?", default=False, style=CUSTOM_STYLE).ask():
        client = get_client(session_name, api_id, api_hash)
        client.connect()
        client.log_out()
        console.print("[bold green]✔ Logged out successfully. Auth key revoked.[/bold green]")


def cmd_contacts(
    action: str = "list",
    sort_by: str = "name",
    query: Optional[str] = None,
    phone: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    user: Optional[str] = None,
    session_name: Optional[str] = None,
    api_id: Optional[int] = None,
    api_hash: Optional[str] = None,
) -> None:
    client = get_client(session_name, api_id, api_hash)
    client.connect()

    if action == "list":
        contacts = client.get_contacts(sort_by=sort_by)
        sort_label = "Name (A-Z)" if sort_by == "name" else "Last Seen / Activity"
        table = Table(title=f"👥 Telegram Contacts ({len(contacts)} total) [Sorted by: {sort_label}]", box=box.ROUNDED)
        table.add_column("User ID", style="cyan")
        table.add_column("Name", style="bold white")
        table.add_column("Username", style="magenta")
        table.add_column("Phone", style="green")
        table.add_column("Status / Last Seen", style="yellow")

        for c in contacts:
            table.add_row(
                str(c.user_id),
                c.full_name or "Unknown",
                f"@{c.username}" if c.username else "-",
                c.phone or "-",
                c.status or "-",
            )
        console.print(table)

    elif action == "search":
        if not query:
            query = questionary.text("Enter search query (name/@username):", style=CUSTOM_STYLE).ask()
        if not query:
            return
        res = client.search_contacts(query)
        users = res.get("users", [])
        table = Table(title=f"🔍 Search Results for '{query}' ({len(users)} users)", box=box.ROUNDED)
        table.add_column("User ID", style="cyan")
        table.add_column("Name", style="bold white")
        table.add_column("Username", style="magenta")
        for u in users:
            table.add_row(str(u.user_id), u.full_name or "Unknown", f"@{u.username}" if u.username else "-")
        console.print(table)

    elif action == "add":
        if not phone:
            phone = questionary.text("Phone Number (with +country code):", style=CUSTOM_STYLE).ask()
        if not first_name:
            first_name = questionary.text("First Name:", style=CUSTOM_STYLE).ask()
        if last_name is None:
            last_name = questionary.text("Last Name (optional):", style=CUSTOM_STYLE).ask() or ""
        if phone and first_name:
            imported = client.import_contacts([{"phone": phone, "first_name": first_name, "last_name": last_name}])
            if imported:
                console.print(f"[bold green]✔ Added contact {first_name} ({phone}) successfully![/bold green]")
            else:
                console.print("[yellow]Could not import contact. Phone might not be registered on Telegram.[/yellow]")

    elif action == "blocked":
        blocked = client.get_blocked_users()
        table = Table(title=f"🚫 Blocked Users ({len(blocked)} total)", box=box.ROUNDED)
        table.add_column("User ID", style="cyan")
        table.add_column("Name", style="bold white")
        table.add_column("Username", style="magenta")
        for b in blocked:
            table.add_row(str(b.user_id), b.full_name or "Unknown", f"@{b.username}" if b.username else "-")
        console.print(table)

    elif action == "block":
        if not user:
            user = questionary.text("Target username or User ID to block:", style=CUSTOM_STYLE).ask()
        if user:
            client.block_user(user)
            console.print(f"[bold green]✔ User '{user}' blocked successfully.[/bold green]")

    elif action == "unblock":
        if not user:
            user = questionary.text("Target username or User ID to unblock:", style=CUSTOM_STYLE).ask()
        if user:
            client.unblock_user(user)
            console.print(f"[bold green]✔ User '{user}' unblocked successfully.[/bold green]")


# ==============================================================================
# Interactive Keyboard-Driven TUI Menu (with Arrow Keys ↑/↓)
# ==============================================================================


def interactive_menu():
    while True:
        cfg = load_config()
        cur_session = cfg.get("session_name", DEFAULT_SESSION_NAME)

        console.clear()
        console.print(
            Panel(
                "[bold cyan]⚡ TELESCRAPER MASTER CONTROL CENTER ⚡[/bold cyan]\n"
                f"[dim]100% Pure Synchronous MTProto 2.0 Engine | Active Session: [bold green]{cur_session}.session[/bold green][/dim]\n"
                "[italic cyan]Use Arrow Keys (↑ / ↓) to navigate, Enter to select, Ctrl+C to exit.[/italic cyan]",
                border_style="cyan",
            )
        )

        choice = questionary.select(
            "Select an Operation:",
            choices=[
                Separator("--- 🖥️ GRAPHICAL TELEGRAM TUI ---"),
                Choice("🚀  Launch Full Telegram TUI (Textual Graphical Desktop)", value="tui"),
                Separator("--- 🔑 AUTHENTICATION & SESSIONS ---"),
                Choice("📱  QR Code Login (Scan with Telegram App & Auto 2FA)", value="qr_login"),
                Choice("📞  Phone Number & OTP Login (SMS / App Code)", value="phone_login"),
                Choice("🤖  Bot Token Login (from @BotFather)", value="bot_login"),
                Choice("👤  My Profile & Account Status (WhoAmI)", value="whoami"),
                Choice("🔑  Export Base64 StringSession (Telethon Compatible)", value="string_session"),
                Separator("--- 🔍 SCRAPING & DATA DISCOVERY ---"),
                Choice("📋  List Dialogs, Channels & Groups", value="chats"),
                Choice("ℹ️   Get Chat / Channel Metadata & Subscriber Count", value="info"),
                Choice("🔍  Scrape Messages (Server-side Filters, Search, Checkpoints)", value="scrape"),
                Choice("⚡  High-Speed Takeout Session (Mass Data Export)", value="takeout"),
                Choice("💬  Scrape Post Comments (Linked Discussion Groups)", value="comments"),
                Choice("👥  Scrape Group Members (Participants List)", value="members"),
                Choice("💰  Extract Crypto Wallets (BTC, ETH, TRC20, TON, SOL) & Contacts", value="extract"),
                Choice("📦  Export Channel Dataset (Excel, SQLite, CSV, JSON)", value="export"),
                Separator("--- ⬇️ MEDIA & 2GB UPLOADS ---"),
                Choice("⬇️   Bulk Parallel Media Downloader (Photos, Videos, Docs)", value="download_media"),
                Choice("🖼️   Profile Avatar Manager (Download, Upload new, Delete)", value="avatar"),
                Choice("⬆️   Upload & Send Files (Up to 2GB with chunk workers)", value="upload"),
                Choice("✉️   Send Text Message / Reaction / Pin / Draft", value="message_ops"),
                Separator("--- 🛡️ MODERATION & ADMIN ---"),
                Choice("📢  Create Broadcast Channel or Supergroup", value="create_chat"),
                Choice("🚫  Moderate Participants (Kick, Ban, Edit Permissions)", value="mod_user"),
                Choice("🛡️   Inspect Admin Audit Log", value="admin_log"),
                Choice("🔗  Manage Custom Invite Links (Create, Revoke, List)", value="invite_links"),
                Separator("--- ⚡ ADVANCED MTPROTO ENGINE ---"),
                Choice("📖  Telegram Stories Engine (View, Post, Delete Stories)", value="stories"),
                Choice("🔄  State Synchronization & Gap Recovery (PTS, QTS, Updates)", value="state_sync"),
                Choice("📞  VoIP Call Signalling & STUN/TURN Config", value="voip"),
                Choice("🔒  End-to-End Encrypted Secret Chat", value="secret_chat"),
                Separator("--- 💻 DEVICES & ACCOUNT SETTINGS ---"),
                Choice("💻  Manage Active Devices & Remote Sessions", value="devices"),
                Choice("⚙️   Switch Session / Edit Credentials", value="switch_session"),
                Choice("🚪  Logout / Exit", value="exit"),
            ],
            style=CUSTOM_STYLE,
            use_shortcuts=True,
        ).ask()

        if choice is None or choice == "exit":
            if questionary.confirm("Do you want to log out before exiting?", default=False, style=CUSTOM_STYLE).ask():
                cmd_logout()
            console.print("[green]Goodbye![/green]")
            break

        try:
            client = get_client()

            if choice == "tui":
                from .tui import run_tui

                run_tui(client)
                return

            elif choice == "qr_login":
                cmd_login_qr()

            elif choice == "phone_login":
                cmd_login_phone()

            elif choice == "bot_login":
                cmd_login_bot()

            elif choice == "whoami":
                cmd_whoami()

            elif choice == "string_session":
                cmd_export_string_session()

            elif choice == "chats":
                flt = questionary.select(
                    "Filter Dialogs:", choices=["All", "Channels only", "Groups only"], style=CUSTOM_STYLE
                ).ask()
                flt_val = "channel" if flt == "Channels only" else ("group" if flt == "Groups only" else None)
                cmd_list_chats(filter_type=flt_val)

            elif choice == "info":
                tgt = pick_chat_interactively(client)
                if tgt:
                    cmd_chat_info(tgt)

            elif choice == "scrape":
                tgt = pick_chat_interactively(client)
                if tgt:
                    lim = questionary.text("Maximum messages to scrape:", default="50", style=CUSTOM_STYLE).ask()
                    srch = questionary.text(
                        "Search keyword (optional, enter to skip):", default="", style=CUSTOM_STYLE
                    ).ask()

                    filter_choice = questionary.select(
                        "Select Server-Side Filter:",
                        choices=[
                            Choice("All Messages (No filter)", value=None),
                            Choice("📷 Photos Only", value="photos"),
                            Choice("🎬 Videos Only", value="videos"),
                            Choice("📄 Documents / Files", value="documents"),
                            Choice("🎵 Music & Audio", value="audio"),
                            Choice("🎙️ Voice Messages", value="voice"),
                            Choice("🔗 Links & URLs", value="urls"),
                            Choice("📌 Pinned Messages", value="pinned"),
                            Choice("✨ GIFs & Animations", value="gifs"),
                        ],
                        style=CUSTOM_STYLE,
                    ).ask()

                    out = questionary.text(
                        "Export file path (e.g. data.xlsx or messages.json, optional):", default="", style=CUSTOM_STYLE
                    ).ask()
                    cmd_scrape(
                        target=tgt,
                        limit=int(lim) if lim.isdigit() else 50,
                        search=srch or None,
                        filter_type=filter_choice,
                        output=out or None,
                    )

            elif choice == "takeout":
                tgt = pick_chat_interactively(client)
                if tgt:
                    lim = questionary.text("Maximum messages for Takeout:", default="1000", style=CUSTOM_STYLE).ask()
                    out = questionary.text(
                        "Export JSON file path:", default=f"{tgt}_takeout.json", style=CUSTOM_STYLE
                    ).ask()
                    cmd_takeout(target=tgt, limit=int(lim) if lim.isdigit() else 1000, output=out or None)

            elif choice == "comments":
                tgt = pick_chat_interactively(client)
                if tgt:
                    pid = questionary.text("Enter Channel Post / Message ID:", style=CUSTOM_STYLE).ask()
                    lim = questionary.text("Max comments to fetch:", default="50", style=CUSTOM_STYLE).ask()
                    if pid and pid.isdigit():
                        cmd_comments(target=tgt, post_id=int(pid), limit=int(lim) if lim.isdigit() else 50)

            elif choice == "members":
                tgt = pick_chat_interactively(client)
                if tgt:
                    lim = questionary.text("Maximum members to scrape:", default="100", style=CUSTOM_STYLE).ask()
                    out = questionary.text("Export to JSON path (optional):", default="", style=CUSTOM_STYLE).ask()
                    cmd_members(target=tgt, limit=int(lim) if lim.isdigit() else 100, output=out or None)

            elif choice == "extract":
                tgt = pick_chat_interactively(client)
                if tgt:
                    lim = questionary.text("Messages to analyze:", default="100", style=CUSTOM_STYLE).ask()
                    cmd_extract(target=tgt, limit=int(lim) if lim.isdigit() else 100)

            elif choice == "export":
                tgt = pick_chat_interactively(client)
                if tgt:
                    fmt = questionary.select(
                        "Choose Export Format:",
                        choices=[
                            Choice("📊 Excel Spreadsheet (.xlsx)", value="xlsx"),
                            Choice("🗄️  SQLite Database (.db)", value="sqlite"),
                            Choice("📄 JSON Dataset (.json)", value="json"),
                            Choice("📝 CSV File (.csv)", value="csv"),
                        ],
                        style=CUSTOM_STYLE,
                    ).ask()

                    default_out = f"{tgt}_export.{fmt if fmt != 'sqlite' else 'db'}"
                    out = questionary.text("Output file path:", default=default_out, style=CUSTOM_STYLE).ask()
                    lim = questionary.text("Max messages to export:", default="500", style=CUSTOM_STYLE).ask()
                    cmd_export(target=tgt, output=out, format_type=fmt, limit=int(lim) if lim.isdigit() else 500)

            elif choice == "download_media":
                tgt = pick_chat_interactively(client)
                if tgt:
                    out_dir = questionary.text("Destination folder:", default="./downloads", style=CUSTOM_STYLE).ask()
                    lim = questionary.text("Max files to download:", default="10", style=CUSTOM_STYLE).ask()
                    m_types = questionary.checkbox(
                        "Select Media Types to Download:",
                        choices=[
                            Choice("Photos", value="photo", checked=True),
                            Choice("Documents", value="document", checked=True),
                            Choice("Videos", value="video", checked=True),
                            Choice("Audio", value="audio"),
                            Choice("Voice", value="voice"),
                        ],
                        style=CUSTOM_STYLE,
                    ).ask()
                    cmd_download_media(
                        target=tgt,
                        limit=int(lim) if lim.isdigit() else 10,
                        output_dir=out_dir,
                        media_types=",".join(m_types or ["photo"]),
                    )

            elif choice == "avatar":
                act = questionary.select(
                    "Profile Photo Action:",
                    choices=[
                        Choice("📥 Download Profile Photo", value="download"),
                        Choice("📤 Upload & Set New Avatar", value="upload"),
                        Choice("📜 View Photo History", value="history"),
                        Choice("🗑️ Delete Latest Avatar", value="delete"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()

                tgt = questionary.text("Target user (default 'me'):", default="me", style=CUSTOM_STYLE).ask()
                if act == "upload":
                    fp = questionary.text("Path to image file:", style=CUSTOM_STYLE).ask()
                    cmd_avatar_manager(action=act, target=tgt, file_path=fp)
                else:
                    cmd_avatar_manager(action=act, target=tgt)

            elif choice == "upload":
                tgt = pick_chat_interactively(client)
                if tgt:
                    fp = questionary.text("Enter path of file to upload:", style=CUSTOM_STYLE).ask()
                    cap = questionary.text("Caption (optional):", default="", style=CUSTOM_STYLE).ask()
                    workers = questionary.select(
                        "Parallel Chunk Workers:",
                        choices=["1 (Standard)", "2 (Fast)", "4 (Ultra Fast 4x)", "8 (Maximum)"],
                        style=CUSTOM_STYLE,
                    ).ask()
                    w_num = int(workers[0]) if workers else 4
                    cmd_upload_file(target=tgt, file_path=fp, caption=cap or None, workers=w_num)

            elif choice == "message_ops":
                op = questionary.select(
                    "Select Message Operation:",
                    choices=[
                        Choice("✉️  Send New Text Message", value="send"),
                        Choice("🔥 Send Emoji Reaction", value="react"),
                        Choice("📌 Pin Message in Chat", value="pin"),
                        Choice("✏️  Edit Sent Message", value="edit"),
                        Choice("🗑️ Delete Message", value="delete"),
                        Choice("📝 Save Draft", value="draft"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()

                tgt = pick_chat_interactively(client)
                if tgt:
                    if op == "send":
                        txt = questionary.text("Message text:", style=CUSTOM_STYLE).ask()
                        cmd_send_message(tgt, txt)
                    elif op == "react":
                        mid = questionary.text("Message ID:", style=CUSTOM_STYLE).ask()
                        emo = questionary.select(
                            "Choose Emoji Reaction:", choices=["🔥", "👍", "❤️", "👏", "🎉", "💩"], style=CUSTOM_STYLE
                        ).ask()
                        if mid and mid.isdigit():
                            cmd_send_reaction(tgt, int(mid), reaction=emo)
                    elif op == "pin":
                        mid = questionary.text("Message ID to pin:", style=CUSTOM_STYLE).ask()
                        if mid and mid.isdigit():
                            cmd_pin_message(tgt, int(mid))
                    elif op == "edit":
                        mid = questionary.text("Message ID to edit:", style=CUSTOM_STYLE).ask()
                        txt = questionary.text("New message text:", style=CUSTOM_STYLE).ask()
                        if mid and mid.isdigit():
                            cmd_edit_message(tgt, int(mid), txt)
                    elif op == "delete":
                        mid = questionary.text("Message ID to delete:", style=CUSTOM_STYLE).ask()
                        if mid and mid.isdigit():
                            cmd_delete_messages(tgt, [int(mid)])
                    elif op == "draft":
                        txt = questionary.text("Draft text:", style=CUSTOM_STYLE).ask()
                        cmd_save_draft(tgt, txt)

            elif choice == "create_chat":
                sub = questionary.select(
                    "Select Type:", choices=["📢 Broadcast Channel", "👥 Community Supergroup"], style=CUSTOM_STYLE
                ).ask()
                tit = questionary.text("Enter Title:", style=CUSTOM_STYLE).ask()
                if sub.startswith("📢"):
                    ab = questionary.text(
                        "Channel Description / About (optional):", default="", style=CUSTOM_STYLE
                    ).ask()
                    cmd_create_channel(title=tit, about=ab)
                else:
                    cmd_create_group(title=tit)

            elif choice == "mod_user":
                tgt = pick_chat_interactively(client)
                if tgt:
                    act = questionary.select(
                        "Moderation Action:",
                        choices=["👢 Kick User from Group", "🚫 Restrict / Ban Permissions"],
                        style=CUSTOM_STYLE,
                    ).ask()
                    usr = questionary.text("Target Username or User ID:", style=CUSTOM_STYLE).ask()
                    if act.startswith("👢"):
                        cmd_kick_user(tgt, usr)
                    else:
                        cmd_edit_permissions(tgt, usr, send_messages=False, send_media=False)

            elif choice == "admin_log":
                tgt = pick_chat_interactively(client)
                if tgt:
                    cmd_admin_log(tgt)

            elif choice == "invite_links":
                tgt = pick_chat_interactively(client)
                if tgt:
                    act = questionary.select(
                        "Invite Link Action:",
                        choices=[
                            Choice("📋 List Active Invite Links", value="list"),
                            Choice("✨ Create New Custom Invite Link", value="create"),
                            Choice("❌ Revoke Invite Link", value="revoke"),
                        ],
                        style=CUSTOM_STYLE,
                    ).ask()
                    if act == "create":
                        tit = questionary.text("Title for this link (optional):", default="", style=CUSTOM_STYLE).ask()
                        cmd_invite_link_manager("create", tgt, title=tit or None)
                    elif act == "revoke":
                        lnk = questionary.text("Invite link URL to revoke:", style=CUSTOM_STYLE).ask()
                        cmd_invite_link_manager("revoke", tgt, link=lnk)
                    else:
                        cmd_invite_link_manager("list", tgt)

            elif choice == "stories":
                act = questionary.select(
                    "Stories Operation:",
                    choices=[
                        Choice("📖 View Active Peer Stories", value="get"),
                        Choice("📸 Post New Story", value="post"),
                        Choice("🗑️ Delete Story", value="delete"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()
                tgt = questionary.text("Target username (default 'me'):", default="me", style=CUSTOM_STYLE).ask()
                cmd_stories(action=act, target=tgt)

            elif choice == "state_sync":
                act = questionary.select(
                    "Select Sync Action:",
                    choices=[
                        Choice("🔄 View Current PTS / QTS Update State", value="state"),
                        Choice("⚡ Recover Missed Account Updates (Difference)", value="difference"),
                        Choice("📡 Recover Channel Missed Updates", value="channel-diff"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()
                cmd_state_sync(action=act)

            elif choice == "voip":
                act = questionary.select(
                    "VoIP Operation:",
                    choices=[
                        Choice("⚙️ View VoIP Configuration & STUN/TURN Servers", value="config"),
                        Choice("📞 Request Outgoing Voice/Video Call", value="request"),
                        Choice("❌ Discard / Hang Up Call", value="discard"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()
                cmd_voip(action=act)

            elif choice == "secret_chat":
                tgt = questionary.text(
                    "Target username for End-to-End Encrypted (E2EE) Secret Chat:", style=CUSTOM_STYLE
                ).ask()
                if tgt:
                    cmd_secret_chat(tgt)

            elif choice == "devices":
                cmd_list_sessions()
                act = questionary.select(
                    "Device Action:",
                    choices=[
                        Choice("Keep Active (Back to Menu)", value="back"),
                        Choice("🗑️ Terminate Specific Remote Session by Hash", value="term"),
                        Choice("⚠️ Reset ALL Other Remote Sessions", value="reset"),
                    ],
                    style=CUSTOM_STYLE,
                ).ask()
                if act == "term":
                    h = questionary.text("Enter session hash to terminate:", style=CUSTOM_STYLE).ask()
                    if h and h.isdigit():
                        cmd_terminate_session(int(h))
                elif act == "reset":
                    cmd_reset_sessions()

            elif choice == "switch_session":
                new_s = questionary.text(
                    "Enter Session Name to activate/switch to:", default=cur_session, style=CUSTOM_STYLE
                ).ask()
                if new_s:
                    cfg["session_name"] = new_s.strip()
                    save_config(cfg)
                    console.print(f"[green]✔ Switched active session to: {new_s}.session[/green]")

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

        questionary.text("\nPress Enter to return to main menu...", style=CUSTOM_STYLE).ask()


# ==============================================================================
# Argument Parsing CLI Entrypoint
# ==============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="TeleScraper Master CLI - Complete Pure-Synchronous Telegram MTProto Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m telescraper                            # Launch interactive keyboard menu
  python3 -m telescraper login-qr                   # QR Code login & save session
  python3 -m telescraper login-phone --phone +1234  # Phone OTP login
  python3 -m telescraper whoami                     # Profile details
  python3 -m telescraper chats                      # List channels & groups
  python3 -m telescraper scrape durov --limit 50    # Scrape messages
  python3 -m telescraper extract crypto_channel     # Extract crypto wallets
  python3 -m telescraper export news output.xlsx    # Export to Excel
  python3 -m telescraper upload me --file dump.zip  # 4x fast 2GB file upload
        """,
    )

    # Global options
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive terminal menu")
    parser.add_argument("--tui", action="store_true", help="Launch Telegram Textual Desktop TUI")
    parser.add_argument("--session", help="Session file name")
    parser.add_argument("--api-id", type=int, help="Telegram API ID")
    parser.add_argument("--api-hash", help="Telegram API Hash")
    parser.add_argument(
        "--transport",
        default="intermediate",
        choices=list(TRANSPORTS_MAP.keys()),
        help="Anti-censorship MTProto transport",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # 0. tui
    subparsers.add_parser("tui", help="Launch full graphical Telegram Textual TUI client")

    # 1. login-qr
    p_qr = subparsers.add_parser("login-qr", help="Login via Telegram Mobile App QR Code")
    p_qr.add_argument("--timeout", type=int, default=120, help="Scan timeout in seconds")

    # 2. login-phone
    p_phone = subparsers.add_parser("login-phone", help="Login via Phone Number & OTP Code")
    p_phone.add_argument("--phone", help="Phone number with country code")

    # 3. login-bot
    p_bot = subparsers.add_parser("login-bot", help="Login with Telegram Bot Token")
    p_bot.add_argument("--token", help="Bot token from @BotFather")

    # 4. whoami
    subparsers.add_parser("whoami", help="Display authenticated profile")

    # 5. chats
    p_chats = subparsers.add_parser("chats", help="List dialogs and channels")
    p_chats.add_argument("--filter", choices=["channel", "group"], help="Filter chat type")

    # 6. info
    p_info = subparsers.add_parser("info", help="Get chat or channel metadata")
    p_info.add_argument("target", help="Username, invite link or chat ID")

    # 7. scrape
    p_scrape = subparsers.add_parser("scrape", help="Scrape channel/group messages")
    p_scrape.add_argument("target", help="Username or ID")
    p_scrape.add_argument("--limit", type=int, default=50, help="Max messages to scrape")
    p_scrape.add_argument("--search", help="Search keyword")
    p_scrape.add_argument(
        "--filter",
        choices=["photos", "videos", "documents", "audio", "voice", "urls", "round_videos", "gifs", "pinned"],
        help="Server-side filter",
    )
    p_scrape.add_argument("--checkpoint", help="Checkpoint file for resumable scraping")
    p_scrape.add_argument("--output", help="Output file path (.json, .csv, .xlsx, .db)")
    p_scrape.add_argument("--reverse", action="store_true", help="Scrape oldest to newest")

    # 8. takeout
    p_take = subparsers.add_parser("takeout", help="High-speed data takeout export")
    p_take.add_argument("target", help="Channel / Group username")
    p_take.add_argument("--limit", type=int, default=1000, help="Max messages")
    p_take.add_argument("--output", help="Output file path")

    # 9. comments
    p_com = subparsers.add_parser("comments", help="Scrape discussion comments from a post")
    p_com.add_argument("target", help="Channel username")
    p_com.add_argument("post_id", type=int, help="Message / Post ID")
    p_com.add_argument("--limit", type=int, default=50, help="Max comments")

    # 10. members
    p_mem = subparsers.add_parser("members", help="Scrape participant list from group/supergroup")
    p_mem.add_argument("target", help="Group / Channel username or ID")
    p_mem.add_argument("--limit", type=int, default=100, help="Max members")
    p_mem.add_argument("--output", help="Save members to JSON file")

    # 11. extract
    p_ext = subparsers.add_parser("extract", help="Regex extract crypto wallets, emails, phone numbers")
    p_ext.add_argument("target", help="Channel username")
    p_ext.add_argument("--limit", type=int, default=100, help="Messages to scan")

    # 12. export
    p_exp = subparsers.add_parser("export", help="Export channel data to Excel/JSON/CSV/SQLite")
    p_exp.add_argument("target", help="Channel username")
    p_exp.add_argument("output", help="Output file path")
    p_exp.add_argument(
        "--format", default="json", choices=["json", "csv", "xlsx", "excel", "sqlite", "db"], help="Export format"
    )
    p_exp.add_argument("--limit", type=int, default=500, help="Max messages")

    # 13. download
    p_down = subparsers.add_parser("download", help="Bulk parallel media downloader")
    p_down.add_argument("target", help="Channel username")
    p_down.add_argument("--dir", default="./downloads", help="Output directory")
    p_down.add_argument("--limit", type=int, default=10, help="Max media items")
    p_down.add_argument("--types", help="Comma-separated types (photo,video,document)")

    # 14. avatar
    p_av = subparsers.add_parser("avatar", help="Profile photo / avatar management")
    p_av.add_argument("action", choices=["download", "upload", "history", "delete"], help="Action to perform")
    p_av.add_argument("--target", default="me", help="Username or ID")
    p_av.add_argument("--file", help="Avatar image file path (for upload)")
    p_av.add_argument("--dir", default="./avatars", help="Output directory (for download)")

    # 15. send
    p_send = subparsers.add_parser("send", help="Send a text message")
    p_send.add_argument("target", help="Recipient username, 'me', or ID")
    p_send.add_argument("message", help="Message text")
    p_send.add_argument("--reply-to", type=int, help="Reply to message ID")

    # 16. upload
    p_up = subparsers.add_parser("upload", help="Upload and send file (up to 2GB)")
    p_up.add_argument("target", help="Recipient username, 'me', or ID")
    p_up.add_argument("file", help="File path")
    p_up.add_argument("--caption", help="Caption text")
    p_up.add_argument("--workers", type=int, default=4, help="Parallel chunk upload workers")

    # 17. edit-message
    p_ed = subparsers.add_parser("edit-message", help="Edit a previously sent message")
    p_ed.add_argument("target", help="Chat / User")
    p_ed.add_argument("message_id", type=int, help="Message ID")
    p_ed.add_argument("text", help="New message text")

    # 18. delete-message
    p_del = subparsers.add_parser("delete-message", help="Delete messages")
    p_del.add_argument("target", help="Chat / User")
    p_del.add_argument("ids", type=int, nargs="+", help="Message IDs to delete")

    # 19. pin
    p_pin = subparsers.add_parser("pin", help="Pin a message in chat")
    p_pin.add_argument("target", help="Chat / User")
    p_pin.add_argument("message_id", type=int, help="Message ID")
    p_pin.add_argument("--notify", action="store_true", help="Notify members")

    # 20. react
    p_react = subparsers.add_parser("react", help="Send emoji reaction to a message")
    p_react.add_argument("target", help="Chat / User")
    p_react.add_argument("message_id", type=int, help="Message ID")
    p_react.add_argument("--emoji", default="🔥", help="Emoji reaction")

    # 21. admin
    p_adm = subparsers.add_parser("admin", help="Group & channel administration")
    p_adm.add_argument(
        "action", choices=["create-channel", "create-group", "kick", "restrict", "log"], help="Admin action"
    )
    p_adm.add_argument("--target", help="Chat / Channel target")
    p_adm.add_argument("--title", help="Channel/Group title")
    p_adm.add_argument("--about", default="", help="Channel description")
    p_adm.add_argument("--user", help="Target user to kick or restrict")
    p_adm.add_argument("--limit", type=int, default=50, help="Audit log limit")

    # 22. invite-link
    p_inv = subparsers.add_parser("invite-link", help="Custom invite links management")
    p_inv.add_argument("action", choices=["create", "revoke", "list"], help="Action")
    p_inv.add_argument("target", help="Chat / Channel")
    p_inv.add_argument("--title", help="Link title")
    p_inv.add_argument("--link", help="Invite link URL (for revoke)")

    # 23. stories
    p_st = subparsers.add_parser("stories", help="Telegram Stories engine")
    p_st.add_argument("action", choices=["get", "post", "delete"], help="Action")
    p_st.add_argument("--target", default="me", help="Target user/channel")
    p_st.add_argument("--file", help="Story photo/video file path")
    p_st.add_argument("--caption", help="Story caption")
    p_st.add_argument("--story-id", type=int, help="Story ID to delete")

    # 24. state
    p_state = subparsers.add_parser("state", help="State synchronization & gap recovery")
    p_state.add_argument(
        "--action", default="state", choices=["state", "difference", "channel-diff"], help="Sync action"
    )
    p_state.add_argument("--channel", help="Channel for channel difference")
    p_state.add_argument("--pts", type=int, help="PTS sequence value")

    # 25. voip
    p_voip = subparsers.add_parser("voip", help="VoIP calls & STUN/TURN config")
    p_voip.add_argument("action", choices=["config", "request", "discard"], help="VoIP action")
    p_voip.add_argument("--target", help="Target user for call")
    p_voip.add_argument("--call-id", type=int, help="Call ID")
    p_voip.add_argument("--access-hash", type=int, help="Call Access Hash")

    # 26. secret-chat
    p_sc = subparsers.add_parser("secret-chat", help="Create End-to-End Encrypted Secret Chat")
    p_sc.add_argument("target", help="Target username")

    # 27. string-session
    subparsers.add_parser("string-session", help="Export session to Base64 StringSession")

    # 28. sessions
    subparsers.add_parser("sessions", help="List active authorized devices")

    # 29. terminate-session
    p_term = subparsers.add_parser("terminate-session", help="Terminate specific remote session")
    p_term.add_argument("hash", type=int, help="Authorization session hash")

    # 30. reset-sessions
    subparsers.add_parser("reset-sessions", help="Terminate all other remote sessions")

    # 31. contacts
    p_cnt = subparsers.add_parser("contacts", help="Telegram Contacts & Address Book management")
    p_cnt.add_argument(
        "action",
        default="list",
        nargs="?",
        choices=["list", "search", "add", "blocked", "block", "unblock"],
        help="Contacts action",
    )
    p_cnt.add_argument(
        "--sort-by",
        default="name",
        choices=["name", "last_seen", "time"],
        help="Sorting method: 'name' (A-Z) or 'last_seen' (online/recent activity)",
    )
    p_cnt.add_argument("--query", help="Search query (name/@username)")
    p_cnt.add_argument("--phone", help="Phone number with country code")
    p_cnt.add_argument("--first-name", help="First Name")
    p_cnt.add_argument("--last-name", help="Last Name")
    p_cnt.add_argument("--user", help="Username or ID to block/unblock")

    # 32. logout
    subparsers.add_parser("logout", help="Log out and revoke session")

    args = parser.parse_args()

    if args.command == "tui" or args.tui:
        from .tui import run_tui

        client = get_client(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
        run_tui(client)
        return

    if not args.command or args.interactive:
        interactive_menu()
        return

    # Direct CLI command execution
    if args.command == "login-qr":
        cmd_login_qr(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash, timeout=args.timeout)
    elif args.command == "login-phone":
        cmd_login_phone(phone=args.phone, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "login-bot":
        cmd_login_bot(bot_token=args.token, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "whoami":
        cmd_whoami(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "chats":
        cmd_list_chats(filter_type=args.filter, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "info":
        cmd_chat_info(args.target, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "scrape":
        cmd_scrape(
            target=args.target,
            limit=args.limit,
            search=args.search,
            filter_type=args.filter,
            checkpoint=args.checkpoint,
            output=args.output,
            reverse=args.reverse,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "takeout":
        cmd_takeout(
            target=args.target,
            limit=args.limit,
            output=args.output,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "comments":
        cmd_comments(
            target=args.target,
            post_id=args.post_id,
            limit=args.limit,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "members":
        cmd_members(
            target=args.target,
            limit=args.limit,
            output=args.output,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "extract":
        cmd_extract(
            target=args.target, limit=args.limit, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash
        )
    elif args.command == "export":
        cmd_export(
            target=args.target,
            output=args.output,
            format_type=args.format,
            limit=args.limit,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "download":
        cmd_download_media(
            target=args.target,
            limit=args.limit,
            output_dir=args.dir,
            media_types=args.types,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "avatar":
        cmd_avatar_manager(
            action=args.action,
            target=args.target,
            file_path=args.file,
            output_dir=args.dir,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "send":
        cmd_send_message(
            target=args.target,
            message=args.message,
            reply_to=args.reply_to,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "upload":
        cmd_upload_file(
            target=args.target,
            file_path=args.file,
            caption=args.caption,
            workers=args.workers,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "edit-message":
        cmd_edit_message(
            target=args.target,
            message_id=args.message_id,
            new_text=args.text,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "delete-message":
        cmd_delete_messages(
            target=args.target,
            message_ids=args.ids,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "pin":
        cmd_pin_message(
            target=args.target,
            message_id=args.message_id,
            notify=args.notify,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "react":
        cmd_send_reaction(
            target=args.target,
            message_id=args.message_id,
            reaction=args.emoji,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "admin":
        if args.action == "create-channel":
            cmd_create_channel(
                title=args.title or "New Channel",
                about=args.about,
                session_name=args.session,
                api_id=args.api_id,
                api_hash=args.api_hash,
            )
        elif args.action == "create-group":
            cmd_create_group(
                title=args.title or "New Group", session_name=args.session, api_id=args.api_id, api_hash=args.api_hash
            )
        elif args.action == "kick":
            cmd_kick_user(
                target=args.target,
                user=args.user,
                session_name=args.session,
                api_id=args.api_id,
                api_hash=args.api_hash,
            )
        elif args.action == "restrict":
            cmd_edit_permissions(
                target=args.target,
                user=args.user,
                send_messages=False,
                send_media=False,
                session_name=args.session,
                api_id=args.api_id,
                api_hash=args.api_hash,
            )
        elif args.action == "log":
            cmd_admin_log(
                target=args.target,
                limit=args.limit,
                session_name=args.session,
                api_id=args.api_id,
                api_hash=args.api_hash,
            )
    elif args.command == "invite-link":
        cmd_invite_link_manager(
            action=args.action,
            target=args.target,
            title=args.title,
            link=args.link,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "stories":
        cmd_stories(
            action=args.action,
            target=args.target,
            file_path=args.file,
            caption=args.caption,
            story_id=args.story_id,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "state":
        cmd_state_sync(
            action=args.action,
            channel=args.channel,
            pts=args.pts,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "voip":
        cmd_voip(
            action=args.action,
            target=args.target,
            call_id=args.call_id,
            access_hash=args.access_hash,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "secret-chat":
        cmd_secret_chat(target=args.target, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "string-session":
        cmd_export_string_session(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "sessions":
        cmd_list_sessions(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "terminate-session":
        cmd_terminate_session(
            auth_hash=args.hash, session_name=args.session, api_id=args.api_id, api_hash=args.api_hash
        )
    elif args.command == "reset-sessions":
        cmd_reset_sessions(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)
    elif args.command == "contacts":
        cmd_contacts(
            action=args.action,
            sort_by=args.sort_by,
            query=args.query,
            phone=args.phone,
            first_name=args.first_name,
            last_name=args.last_name,
            user=args.user,
            session_name=args.session,
            api_id=args.api_id,
            api_hash=args.api_hash,
        )
    elif args.command == "logout":
        cmd_logout(session_name=args.session, api_id=args.api_id, api_hash=args.api_hash)


if __name__ == "__main__":
    main()
