"""
ModDesk v5 - a small desktop notebook for moderation work (profiles, settings window, installer, updater).

* Tree of groups / users (drag & drop, inline rename like File Explorer, colored tag dots)
* Per user: main name, real name, number(s), AKAs, tag, accounts per platform (starred main account, collapsible),
  each account has USERNAME, DISPLAY NAME, ID, LINK, custom fields (e.g. Bio) and notes
* Convert / scan / avatar buttons and a global Autofill button, driven by apis.json + Settings > API keys
* Find socials: name variants (separators, numbers, repeated letters) -> web searches in your browser
* Settings: platform presets, tags (color + text), API keys (Discord bot token, Bloxlink key list), icon, updates
* Everything is saved as plain JSON next to the program:
      data/users.json   (your records, with a .bak copy of the previous save)
      apis.json         (API endpoints used by the buttons)
      settings.json     (presets, tags, keys, options)
* Tools > HTTP request tool: GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS
"""
import datetime
import json
import os
import queue
import re
import sys
import threading
import urllib.parse
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================================================
# Constants and paths
# ==========================================================================

APP_NAME = "ModDesk"

APP_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = os.path.join(APP_DIR, "data")

DATA_FILE = os.path.join(DATA_DIR, "users.json")

API_FILE = os.path.join(APP_DIR, "apis.json")

SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

RESPONSES_DIR = os.path.join(APP_DIR, "responses")

# Colors the dot in the list cycles through (name, hex). Edit freely.
COLORS = [("None", ""), ("Red", "#e5484d"), ("Yellow", "#f5c518"), ("Blue", "#3b82f6"), ("Green", "#30a46c")]

BUTTON_SETS = {"": "None", "roblox": "Roblox buttons", "discord": "Discord buttons"}

SETTINGS_VERSION = 4

APIS_VERSION = 4

APP_CODE = os.path.abspath(globals().get("__file__") or sys.argv[0])

PALETTE = [("Red", "#e5484d"), ("Orange", "#f76b15"), ("Yellow", "#f5c518"), ("Green", "#30a46c"),
           ("Blue", "#3b82f6"), ("Purple", "#8e4ec6"), ("Gray", "#8b8d98")]

CONF_LEVELS = ["", "Confirmed", "Likely", "Possible", "Guess"]

CONF_NONE = "—"

APP_VERSION = "5.2.0"

# Your GitHub repo as owner/name (public). Fills the Settings > Updates box and lets the installer fetch the newest code.
DEFAULT_UPDATE_REPO = "WebDemon7896/moddesk"

APP_CFG_FILE = os.path.join(APP_DIR, "app.json")

PROFILES_DIR = os.path.join(APP_DIR, "profiles")

CURRENT_PROFILE = ""

TERMS_TEXT = """MODDESK - PURPOSE, TERMS AND DISCLAIMERS

Please read this before using ModDesk. You must accept it the first time you start the program.

WHAT MODDESK IS FOR
- A personal notebook that helps volunteer or professional moderators and trust-and-safety staff keep their own notes organised: which accounts (Roblox, Discord, others) seem to belong to the same person, what was observed, and why.
- Looking up information that is public, or that you are legitimately allowed to access, to support a moderation decision: confirming an account is the one you were told about, spotting ban evasion or alternate accounts, and keeping a record of your reasoning.
- Saving everything on YOUR computer, in plain files that you control.

WHAT MODDESK IS NOT FOR
- Stalking, harassment, intimidation, doxxing, or exposing a person's identity, home address, school, workplace or family.
- Tracking or building profiles on private individuals who have nothing to do with a moderation matter.
- Contacting, pressuring or befriending minors outside of your official moderation role. Many Roblox and Discord users are children: collect the minimum, and report serious threats to the platform's trust and safety team or to the authorities instead of acting on your own.
- Getting into accounts, bypassing logins or platform protections, or scraping at large scale.
- Evading the rules of any platform, or selling or sharing the data you collect.
- Making accusations or punishing someone only because a name, number or avatar looked similar.

IMPORTANT DISCLAIMERS
- Matches are LEADS, NOT PROOF. Names, numbers and avatars are often reused or copied by different people. Always confirm with several independent signs before you act, and give the person a chance to explain where your rules allow it.
- Results from search links, name variants, avatars and lookups can be wrong, outdated or incomplete. Nothing here is guaranteed to be accurate.
- ModDesk uses services owned by other companies (for example Roblox, Discord and Bloxlink). They are not affiliated with ModDesk. You are responsible for following their terms, rules and rate limits and for keeping your own keys private.
- Your records, API keys and tokens are stored on your computer as PLAIN, UNENCRYPTED text files. Protect the folder, do not share it, and delete data you no longer need.
- You are responsible for obeying the laws and workplace or community rules that apply to you, including privacy and data protection laws, and for how you use and store any personal information.
- ModDesk is provided "as is", without any warranty. The authors are not responsible for harm, loss or decisions that result from using it.

By pressing "I accept" you confirm that you understand the above and will use ModDesk only for legitimate moderation work.

This software, its text and these terms were generated by AI (Claude, made by Anthropic). They have not been reviewed by a lawyer and are not legal advice.
"""

KEY_ACTIONS = [
    ("save", "Save now"),
    ("new_user", "New user"),
    ("new_group", "New group"),
    ("find_user", "Search the list"),
    ("autofill", "Autofill the open user"),
    ("find_socials", "Find socials for the open user"),
    ("settings", "Open settings"),
]

DEFAULT_KEYBINDS = {
    "save": "<Control-s>",
    "new_user": "<Control-n>",
    "new_group": "<Control-N>",
    "find_user": "<Control-f>",
    "autofill": "<Control-Alt-a>",
    "find_socials": "<Control-Alt-f>",
    "settings": "<Control-comma>",
}

SETTING_TOGGLES = [
    ("auto_link", "Fill ID <-> link automatically when leaving a field"),
    ("autofill_scans", "Autofill also runs scans"),
    ("show_scan", "Show the Scan button on accounts"),
    ("confirm_delete", "Ask before deleting"),
    ("show_tag_text", "Show the tag text next to names in the list"),
]

MOD_KEYSYMS = {"Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R", "Super_L",
               "Super_R", "Caps_Lock", "Num_Lock", "Win_L", "Win_R"}

TOUR_PAGES = [
    ("The list", "The left side is your tree of groups and users. + Group / + User add rows you can type straight "
                 "into (F2 renames). Drag a row onto a group to move it. Click a colored dot to cycle its tag."),
    ("A user", "On the right you see the user's main name, real name, number(s), AKAs and tag, then one box per "
               "platform. Each account has Username, Display Name, ID, Link, extra fields and notes. The star marks "
               "the main account; [-] / [+] collapses it."),
    ("Buttons", "2rblxId, 2discId, 2roblox and 2discord convert between usernames and IDs. Scan reads the public "
                "profile. Avatar shows the picture and opens reverse image searches. Autofill does everything it can "
                "at once. Matches are leads, not proof."),
    ("Find socials", "Builds spellings of the user's names (separators, numbers, leetspeak, repeated letters) and "
                     "opens a handful of combined searches in your browser. It never opens dozens of tabs."),
    ("Profiles", "A profile is a separate save file (like a vault): its own users, tags and platform presets. "
                 "File > Switch profile opens the picker again. Your API keys are shared by all profiles."),
    ("Settings", "Settings (Ctrl+,) holds toggles, keyboard shortcuts you can change, API keys, updates and the "
                 "terms. Updates work without Git: Install update from file, or point it at a GitHub repo."),
]

BAD_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# ==========================================================================
# Defaults: presets, tags, settings
# ==========================================================================

DEFAULT_PRESETS = [
    {"name": "Roblox", "link_template": "https://www.roblox.com/users/{id}/profile",
     "display_name": True, "fields": ["Bio"], "buttons": "roblox", "default": True},
    {"name": "Discord", "link_template": "https://discord.com/users/{id}",
     "display_name": True, "fields": [], "buttons": "discord", "default": True},
    {"name": "Real life", "link_template": "", "display_name": False, "hide_core": True,
     "fields": ["Real name", "Location", "Timezone", "Birthday", "Phone", "Email", "How we know each other"],
     "buttons": "", "default": False},
]

DEFAULT_TAGS = [
    {"id": "t-red", "name": "Flagged", "color": "#e5484d"},
    {"id": "t-yellow", "name": "Watching", "color": "#f5c518"},
    {"id": "t-blue", "name": "Linked / alt", "color": "#3b82f6"},
    {"id": "t-green", "name": "Cleared", "color": "#30a46c"},
]

DEFAULT_SEARCH = [
    {"group": "Web search", "name": "Google - exact",
     "url": "https://www.google.com/search?q=%22{q}%22"},
    {"group": "Web search", "name": "Google - not on Roblox/Discord",
     "url": "https://www.google.com/search?q=%22{q}%22+-site%3Aroblox.com+-site%3Adiscord.com"},
    {"group": "Web search", "name": "Google - social sites only",
     "url": ("https://www.google.com/search?q=%22{q}%22+%28site%3Atiktok.com+OR+site%3Ainstagram.com+OR+site%3Ax.com"
             "+OR+site%3Atwitter.com+OR+site%3Ayoutube.com+OR+site%3Areddit.com+OR+site%3Atwitch.tv"
             "+OR+site%3Agithub.com+OR+site%3Asteamcommunity.com%29")},
    {"group": "Web search", "name": "Google - in page address (inurl)", "spaces": False,
     "url": "https://www.google.com/search?q=inurl%3A{q}"},
    {"group": "Web search", "name": "Google - in page title (intitle)",
     "url": "https://www.google.com/search?q=intitle%3A%22{q}%22"},
    {"group": "Web search", "name": "Bing - exact", "url": "https://www.bing.com/search?q=%22{q}%22"},
    {"group": "Web search", "name": "DuckDuckGo - exact", "url": "https://duckduckgo.com/?q=%22{q}%22"},
    {"group": "Web search", "name": "Yandex - exact", "url": "https://yandex.com/search/?text=%22{q}%22"},
    {"group": "Profile guess", "name": "Roblox user search", "url": "https://www.roblox.com/search/users?keyword={q}"},
    {"group": "Profile guess", "name": "TikTok", "spaces": False, "url": "https://www.tiktok.com/@{q}"},
    {"group": "Profile guess", "name": "X / Twitter", "spaces": False, "url": "https://x.com/{q}"},
    {"group": "Profile guess", "name": "Instagram", "spaces": False, "url": "https://www.instagram.com/{q}/"},
    {"group": "Profile guess", "name": "YouTube", "spaces": False, "url": "https://www.youtube.com/@{q}"},
    {"group": "Profile guess", "name": "Twitch", "spaces": False, "url": "https://www.twitch.tv/{q}"},
    {"group": "Profile guess", "name": "GitHub", "spaces": False, "url": "https://github.com/{q}"},
    {"group": "Profile guess", "name": "Reddit", "spaces": False, "url": "https://www.reddit.com/user/{q}"},
    {"group": "Profile guess", "name": "Steam", "spaces": False, "url": "https://steamcommunity.com/id/{q}"},
]

DEFAULT_SETTINGS = {
    "version": SETTINGS_VERSION,
    "presets": DEFAULT_PRESETS,
    "tags": DEFAULT_TAGS,
    "auto_link": True,
    "autofill_scans": True,
    "confirm_delete": True,
    "show_tag_text": True,
    "show_scan": True,
    "keys": {"discord_token": "", "bloxlink": []},
    "search_templates": DEFAULT_SEARCH,
}

REAL_LIFE_PRESET = {"name": "Real life", "link_template": "", "display_name": False, "hide_core": True,
                    "fields": ["Real name", "Location", "Timezone", "Birthday", "Phone", "Email",
                               "How we know each other"],
                    "buttons": "", "default": False}

PRESET_LIBRARY = [
    {"name": "GitHub", "link_template": "https://github.com/{username}", "display_name": True,
     "fields": ["Bio", "Location", "Created"], "buttons": "", "default": False,
     "lookups": [{"label": "2ghId", "api": "gh_user", "src": "username", "dst": "id"},
                 {"label": "2ghUser", "api": "gh_id", "src": "id", "dst": "username"}],
     "scan": "gh_user", "scan_src": "username",
     "about": "Username <-> numeric ID and profile (bio, location, created). No key; 60 requests/hour per IP."},
    {"name": "Bluesky", "link_template": "https://bsky.app/profile/{username}", "display_name": True,
     "fields": ["Bio"], "buttons": "", "default": False,
     "lookups": [{"label": "2did", "api": "bsky_resolve", "src": "username", "dst": "id"},
                 {"label": "2handle", "api": "bsky_profile", "src": "id", "dst": "username"}],
     "scan": "bsky_profile", "scan_src": "username",
     "about": "Handle <-> DID and profile (display name, bio). No key."},
    {"name": "Steam", "link_template": "https://steamcommunity.com/profiles/{id}", "display_name": True,
     "fields": ["Country"], "buttons": "", "default": False,
     "lookups": [{"label": "2steamId", "api": "steam_resolve", "src": "username", "dst": "id"}],
     "scan": "steam_profile", "scan_src": "id",
     "about": "Vanity name -> SteamID64, then profile data. Needs a free Steam Web API key (Settings > API keys)."},
    {"name": "Reddit", "link_template": "https://www.reddit.com/user/{username}", "display_name": False,
     "fields": ["Bio"], "buttons": "", "default": False,
     "lookups": [{"label": "2redditId", "api": "reddit_user", "src": "username", "dst": "id"}],
     "scan": "reddit_user", "scan_src": "username",
     "about": "Public profile JSON. No key. Reddit may refuse requests at times (HTTP 429/403). Not checked against docs."},
    {"name": "Chess.com", "link_template": "https://www.chess.com/member/{username}", "display_name": True,
     "fields": ["Location"], "buttons": "", "default": False,
     "lookups": [{"label": "2chessId", "api": "chess_user", "src": "username", "dst": "id"}],
     "scan": "chess_user", "scan_src": "username",
     "about": "Public player profile. No key. Not checked against docs."},
    {"name": "Lichess", "link_template": "https://lichess.org/@/{username}", "display_name": False,
     "fields": ["Bio", "Location"], "buttons": "", "default": False,
     "scan": "lichess_user", "scan_src": "username",
     "about": "Public user profile. No key. Not checked against docs."},
    {"name": "Minecraft", "link_template": "https://namemc.com/profile/{username}", "display_name": False,
     "fields": [], "buttons": "", "default": False,
     "lookups": [{"label": "2uuid", "api": "mc_user", "src": "username", "dst": "id"},
                 {"label": "2mcName", "api": "mc_uuid", "src": "id", "dst": "username"}],
     "about": "Java name <-> UUID through Mojang. No key. Not checked against docs."},
    {"name": "Hacker News", "link_template": "https://news.ycombinator.com/user?id={username}",
     "display_name": False, "fields": ["Bio", "Karma"], "buttons": "", "default": False,
     "scan": "hn_user", "scan_src": "username",
     "about": "Public profile (about, karma). No key. Not checked against docs."},
]

# ==========================================================================
# API layer (requests, keys, run_api, endpoint library)
# ==========================================================================

# --------------------------------------------------------------------------
# API configuration
# --------------------------------------------------------------------------
# {value} is replaced by the username / ID in the URL (URL-encoded), in the
# body (JSON-escaped) and in the headers (raw).
# "extract" = path into the JSON answer ("data.0.id"), a list of paths (one
# "path: value" line each) or "" (whole answer, pretty printed).
# Anything still containing YOUR_ (or an empty url) is treated as "not set up".
DEFAULT_APIS = {
    "_version": APIS_VERSION,
    "_help": (
        "Edit the entries below. {value} = the username/ID from the field. {discord_token}, and (with pool) {bloxlink_guild} and "
        "{key} are filled from Settings > API keys. extract = path in the JSON answer (or a list of paths, or '' "
        "for everything). fill = fields to fill from the answer. pool = try each key from the settings list in order. "
        "needs = settings that must be filled in. not_found = HTTP codes that just mean 'no result'. "
        "discord_user_to_id: Discord has no official username->ID lookup, so point this at your own service."
    ),
    "rblx_user_to_id": {
        "method": "POST",
        "url": "https://users.roblox.com/v1/usernames/users",
        "headers": {"Content-Type": "application/json", "Accept": "application/json"},
        "body": "{\"usernames\": [\"{value}\"], \"excludeBannedUsers\": false}",
        "extract": "data.0.id",
        "fill": {"username": "data.0.name", "display": "data.0.displayName"},
    },
    "rblx_id_to_discord": {
        "method": "GET",
        "url": "https://api.blox.link/v4/public/guilds/{bloxlink_guild}/roblox-to-discord/{value}",
        "headers": {"Authorization": "{key}"},
        "pool": "bloxlink",
        "needs": ["bloxlink"],
        "not_found": [404],
        "extract": "discordIDs",
    },
    "discord_id_to_roblox": {
        "method": "GET",
        "url": "https://api.blox.link/v4/public/guilds/{bloxlink_guild}/discord-to-roblox/{value}",
        "headers": {"Authorization": "{key}"},
        "pool": "bloxlink",
        "needs": ["bloxlink"],
        "not_found": [404],
        "extract": "robloxID",
    },
    "discord_user_to_id": {
        "method": "GET",
        "url": "",
        "headers": {},
        "extract": "",
    },
    "scan_roblox": {
        "method": "GET",
        "url": "https://users.roblox.com/v1/users/{value}",
        "headers": {"Accept": "application/json"},
        "extract": ["name", "displayName", "id", "created", "isBanned", "hasVerifiedBadge", "description"],
        "fill": {"username": "name", "display": "displayName", "Bio": "description"},
    },
    "scan_discord": {
        "method": "GET",
        "url": "https://discord.com/api/v10/users/{value}",
        "headers": {"Authorization": "Bot {discord_token}"},
        "needs": ["discord_token"],
        "extract": ["username", "global_name", "id", "bot", "avatar", "banner", "public_flags"],
        "fill": {"username": "username", "display": "global_name"},
    },
    "avatar_roblox": {
        "method": "GET",
        "url": ("https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={value}"
                "&size=420x420&format=Png&isCircular=false"),
        "headers": {"Accept": "application/json"},
        "extract": "data.0.imageUrl",
    },
}

class ApiError(Exception):
    pass

def do_request(method, url, headers=None, body=None, timeout=25):
    """Plain HTTP(S) request. Returns (status, reason, headers, text). HTTP errors are returned, not raised."""
    import urllib.request  # imported lazily: it is slow to import and not needed at startup
    import urllib.error
    headers = dict(headers or {})
    headers.setdefault("User-Agent", APP_NAME + "/2.0")
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.reason, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.reason, dict(e.headers), e.read().decode("utf-8", "replace")

def dig(obj, path):
    for part in path.split("."):
        try:
            obj = obj[int(part)] if isinstance(obj, list) else obj[part]
        except (KeyError, IndexError, ValueError, TypeError):
            return None
    return obj

def fmt(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(fmt(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return str(v)

def apply_extract(parsed, spec):
    if not spec:
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    if isinstance(spec, list):
        return "\n".join("%s: %s" % (p, fmt(dig(parsed, p))) for p in spec)
    return fmt(dig(parsed, spec))

SECRET_LABELS = {"discord_token": "Discord bot token", "bloxlink": "a Bloxlink server ID + key",
                 "steam_key": "a Steam Web API key"}

KEY_COOLDOWN = {}  # key -> time until which it is skipped (rate limited / rejected)

NOT_SET_UP = ("This button is not configured yet.\nOpen apis.json (Tools > Open apis.json), fill in the URL, "
              "then use Tools > Reload apis.json.")

REVERSE_IMAGE = [
    ("Google Lens", "https://lens.google.com/uploadbyurl?url={u}"),
    ("Bing Visual Search", "https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:{u}"),
    ("TinEye", "https://tineye.com/search?url={u}"),
    ("Yandex Images", "https://yandex.com/images/search?rpt=imageview&url={u}"),
]

def secret_list(secrets, name):
    v = secrets.get(name)
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [str(v).strip()] if v and str(v).strip() else []

def pool_items(secrets, pool):
    """Complete (server ID + key) pairs of a pool, e.g. secrets['bloxlink'] = [{'guild': '123', 'key': 'abc'}]."""
    out = []
    items = secrets.get(pool)
    if isinstance(items, list):
        for it in items:
            if isinstance(it, dict):
                g, k = str(it.get("guild", "")).strip(), str(it.get("key", "")).strip()
                if g and k:
                    out.append({"guild": g, "key": k})
    return out

def has_secret(secrets, name):
    if name == "bloxlink":
        return bool(pool_items(secrets, "bloxlink"))
    return bool(secret_list(secrets, name))

def fill_template(text, value, secrets, key, mode, guild=""):
    quote = {"url": lambda s: urllib.parse.quote(s, safe=""),
             "json": lambda s: json.dumps(s)[1:-1],
             "raw": lambda s: s}[mode]
    pairs = {"value": str(value),
             "discord_token": (secrets.get("discord_token") or "").strip(),
             "bloxlink_guild": guild or "",
             "steam_key": (secrets.get("steam_key") or "").strip(),
             "key": key or ""}
    for k, v in pairs.items():
        text = text.replace("{%s}" % k, quote(v))
    return text

def run_api(cfg, value, secrets=None):
    """Call one apis.json entry. Returns (text, parsed). text is '' when the thing simply was not found.
    With "pool", every (server ID + key) pair from the settings is tried in turn; a rejected or rate limited
    key is skipped for a while."""
    import time
    secrets = secrets or {}
    if not isinstance(cfg, dict):
        raise ApiError("This API entry is missing from apis.json.")
    url = cfg.get("url", "")
    headers = cfg.get("headers") or {}
    body = cfg.get("body") or ""
    if not url or "YOUR_" in (url + json.dumps(headers) + body):
        raise ApiError(NOT_SET_UP)
    missing = [SECRET_LABELS.get(n, n) for n in cfg.get("needs", []) if not has_secret(secrets, n)]
    if missing:
        raise ApiError("Missing in Settings > API keys: " + ", ".join(missing))
    pool = cfg.get("pool")
    if pool:
        ready = [it for it in pool_items(secrets, pool) if KEY_COOLDOWN.get(it["key"], 0) <= time.time()]
        if not ready:
            raise ApiError("All %s keys are cooling down after errors or rate limits.\nTry again later, or add "
                           "another server key in Settings > API keys." % pool)
    else:
        ready = [None]
    last = None
    for item in ready:
        key = item["key"] if item else None
        guild = item["guild"] if item else ""
        try:
            req_url = fill_template(url, value, secrets, key, "url", guild)
            hdrs = {k: fill_template(str(v), value, secrets, key, "raw", guild) for k, v in headers.items()}
            payload = fill_template(body, value, secrets, key, "json", guild) if body else None
            status, reason, h, text = do_request(cfg.get("method", "GET"), req_url, hdrs, payload)
        except (OSError, ValueError) as e:
            last = ApiError("Network error: %s" % e)
            continue
        if status in (401, 403) and key:
            KEY_COOLDOWN[key] = time.time() + 12 * 3600
            last = ApiError("HTTP %s: the key for server %s was rejected (wrong key or wrong server ID?)." % (
                status, guild))
            continue
        if status == 429:
            retry = next((v for k, v in h.items() if k.lower() == "retry-after"), "")
            wait = int(retry) if str(retry).isdigit() else 900
            if key:
                KEY_COOLDOWN[key] = time.time() + min(wait, 86400)
            last = ApiError("HTTP 429: rate limited, slow down or add another server key.")
            continue
        if status >= 500:
            last = ApiError("HTTP %s %s" % (status, reason))
            continue
        if status in cfg.get("not_found", []):
            return "", None
        if status >= 400:
            raise ApiError("HTTP %s %s\n%s" % (status, reason, text[:300]))
        try:
            parsed = json.loads(text)
        except ValueError:
            return text.strip(), None
        err = parsed.get("error") if isinstance(parsed, dict) else None
        if err:
            if "not found" in str(err).lower():
                return "", None
            raise ApiError(str(err))
        return apply_extract(parsed, cfg.get("extract")), parsed
    raise last or ApiError("No key worked.")

def fetch_bytes(url, timeout=20, limit=4000000):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": APP_NAME + "/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit)

def discord_avatar_url(parsed, ident):
    h = parsed.get("avatar") if isinstance(parsed, dict) else None
    if h:
        return "https://cdn.discordapp.com/avatars/%s/%s.png?size=256" % (ident, h)
    try:
        idx = (int(ident) >> 22) % 6
    except ValueError:
        idx = 0
    return "https://cdn.discordapp.com/embed/avatars/%d.png" % idx

_UA = {"User-Agent": "ModDesk/5 (moderation notebook)", "Accept": "application/json"}

LIB_APIS = {
    "gh_user": {"method": "GET", "url": "https://api.github.com/users/{value}", "headers": _UA,
                "extract": "id", "not_found": [404],
                "fill": {"username": "login", "display": "name", "Bio": "bio", "Location": "location",
                         "Created": "created_at", "id": "id"}},
    "gh_id": {"method": "GET", "url": "https://api.github.com/user/{value}", "headers": _UA,
              "extract": "login", "not_found": [404],
              "fill": {"username": "login", "display": "name", "Bio": "bio", "Location": "location",
                       "Created": "created_at"}},
    "bsky_resolve": {"method": "GET",
                     "url": "https://public.api.bsky.app/xrpc/com.atproto.identity.resolveHandle?handle={value}",
                     "headers": _UA, "extract": "did", "not_found": [400, 404]},
    "bsky_profile": {"method": "GET",
                     "url": "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor={value}",
                     "headers": _UA, "extract": "handle", "not_found": [400, 404],
                     "fill": {"username": "handle", "display": "displayName", "Bio": "description", "id": "did"}},
    "steam_resolve": {"method": "GET",
                      "url": ("https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/"
                              "?key={steam_key}&vanityurl={value}"),
                      "headers": _UA, "needs": ["steam_key"], "extract": "response.steamid", "not_found": [404]},
    "steam_profile": {"method": "GET",
                      "url": ("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
                              "?key={steam_key}&steamids={value}"),
                      "headers": _UA, "needs": ["steam_key"], "extract": "response.players.0.personaname",
                      "not_found": [404],
                      "fill": {"display": "response.players.0.personaname", "link": "response.players.0.profileurl",
                               "Country": "response.players.0.loccountrycode"}},
    "reddit_user": {"method": "GET", "url": "https://www.reddit.com/user/{value}/about.json", "headers": _UA,
                    "extract": "data.id", "not_found": [404],
                    "fill": {"username": "data.name", "id": "data.id", "Bio": "data.subreddit.public_description"}},
    "chess_user": {"method": "GET", "url": "https://api.chess.com/pub/player/{value}", "headers": _UA,
                   "extract": "player_id", "not_found": [404],
                   "fill": {"username": "username", "display": "name", "id": "player_id", "Location": "location"}},
    "lichess_user": {"method": "GET", "url": "https://lichess.org/api/user/{value}", "headers": _UA,
                     "extract": "id", "not_found": [404],
                     "fill": {"username": "username", "id": "id", "Bio": "profile.bio",
                              "Location": "profile.location"}},
    "mc_user": {"method": "GET", "url": "https://api.mojang.com/users/profiles/minecraft/{value}", "headers": _UA,
                "extract": "id", "not_found": [204, 404], "fill": {"username": "name"}},
    "mc_uuid": {"method": "GET", "url": "https://sessionserver.mojang.com/session/minecraft/profile/{value}",
                "headers": _UA, "extract": "name", "not_found": [204, 404]},
    "hn_user": {"method": "GET", "url": "https://hacker-news.firebaseio.com/v0/user/{value}.json", "headers": _UA,
                "extract": "id", "not_found": [404],
                "fill": {"username": "id", "Bio": "about", "Karma": "karma"}},
}

DEFAULT_APIS.update(LIB_APIS)

# ==========================================================================
# Small helpers: links, entries, profiles, keys
# ==========================================================================

def log_crash(text):
    """Append an error report next to the program (crash.log)."""
    try:
        with open(os.path.join(APP_DIR, "crash.log"), "a", encoding="utf-8") as f:
            f.write("--- %s ---\n%s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), text))
    except OSError:
        pass

# --------------------------------------------------------------------------
# Link templates:  https://www.roblox.com/users/{id}/profile
# --------------------------------------------------------------------------
_PLACEHOLDER = re.compile(r"(\{id\}|\{username\})")

def template_regex(tpl):
    seen = set()
    out = []
    for p in _PLACEHOLDER.split(tpl):
        if p in ("{id}", "{username}"):
            name = p[1:-1]
            if name in seen:
                out.append(r"[^/?#&\s]+")
            else:
                seen.add(name)
                out.append(r"(?P<%s>[^/?#&\s]+)" % name)
        else:
            out.append(re.escape(p))
    return re.compile("".join(out), re.I)

def extract_from_link(tpl, link):
    """Pull {id} / {username} out of a link using the template. Returns a dict (maybe empty)."""
    link = (link or "").strip()
    if not tpl or not link or not _PLACEHOLDER.search(tpl):
        return {}
    rx = template_regex(tpl)
    for cand in (link, "https://" + link):
        m = rx.match(cand)
        if m:
            return {k: v for k, v in m.groupdict().items() if v}
    return {}

def build_link(tpl, ident, username=""):
    if not tpl or not _PLACEHOLDER.search(tpl):
        return ""
    if "{id}" in tpl and not ident:
        return ""
    if "{username}" in tpl and not username:
        return ""
    return tpl.replace("{id}", ident).replace("{username}", username)

# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def uid():
    return os.urandom(8).hex()

def now_stamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

def new_entry(preset=None):
    preset = preset or {}
    return {"username": "", "display": "", "id": "", "link": "",
            "extra": [{"key": f, "value": ""} for f in preset.get("fields", []) if f.strip()],
            "notes": "", "main": False, "collapsed": False}

def new_group(name):
    return {"id": uid(), "type": "group", "name": name, "open": True, "children": []}

def walk_nodes(items):
    for n in items:
        yield n
        if n.get("type") == "group":
            yield from walk_nodes(n.get("children", []))

def load_app_cfg():
    cfg = {"last_profile": "", "ask_on_start": True, "onboarded": False, "terms": "", "tour_pending": False,
           "keys": None, "keybinds": {}, "update_repo": DEFAULT_UPDATE_REPO, "update_branch": "main",
           "first_profile": "", "auto_update_check": True,
           "browser": {"kind": "default", "profile": "", "path": "", "args": ""}}
    try:
        with open(APP_CFG_FILE, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            for k in cfg:
                if k in loaded:
                    cfg[k] = loaded[k]
    except (OSError, ValueError):
        pass
    if not isinstance(cfg["keybinds"], dict):
        cfg["keybinds"] = {}
    return cfg

def save_app_cfg(cfg):
    try:
        tmp = APP_CFG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        os.replace(tmp, APP_CFG_FILE)
    except OSError as e:
        log_crash("could not save app.json: %s" % e)

def clean_profile_name(name):
    return BAD_NAME_CHARS.sub("", str(name or "")).strip().strip(".").strip()[:60]

def list_profiles():
    try:
        return sorted((d for d in os.listdir(PROFILES_DIR)
                       if not d.startswith("_") and os.path.isdir(os.path.join(PROFILES_DIR, d))), key=str.lower)
    except OSError:
        return []

def create_profile(name):
    name = clean_profile_name(name)
    if not name:
        raise ValueError("Give the profile a name.")
    if name.lower() in [p.lower() for p in list_profiles()]:
        raise ValueError("A profile called '%s' already exists." % name)
    os.makedirs(os.path.join(PROFILES_DIR, name, "data"), exist_ok=True)
    return name

def set_profile(name):
    """Point the data/settings paths at profiles/<name>/ (all file code reads these globals)."""
    global CURRENT_PROFILE, DATA_DIR, DATA_FILE, SETTINGS_FILE
    base = os.path.join(PROFILES_DIR, name)
    os.makedirs(os.path.join(base, "data"), exist_ok=True)
    CURRENT_PROFILE = name
    DATA_DIR = os.path.join(base, "data")
    DATA_FILE = os.path.join(DATA_DIR, "users.json")
    SETTINGS_FILE = os.path.join(base, "settings.json")

def migrate_legacy():
    """Older versions kept data\\ and settings.json next to the program: move them into profiles\\Default."""
    import shutil
    if list_profiles():
        return ""
    old_data = os.path.join(APP_DIR, "data")
    old_set = os.path.join(APP_DIR, "settings.json")
    if not (os.path.isdir(old_data) or os.path.exists(old_set)):
        return ""
    base = os.path.join(PROFILES_DIR, "Default")
    os.makedirs(base, exist_ok=True)
    try:
        if os.path.isdir(old_data) and not os.path.exists(os.path.join(base, "data")):
            shutil.move(old_data, os.path.join(base, "data"))
        if os.path.exists(old_set) and not os.path.exists(os.path.join(base, "settings.json")):
            shutil.move(old_set, os.path.join(base, "settings.json"))
    except OSError as e:
        log_crash("legacy migration failed: %s" % e)
    return "Default"

def key_sequence(state, keysym):
    """Tk binding string for a key press, or '' if it is only a modifier / not allowed (a bare letter would break typing)."""
    if keysym in MOD_KEYSYMS or not keysym:
        return ""
    ctrl = bool(state & 0x4)
    alt = bool(state & (0x20000 if sys.platform == "win32" else 0x8))
    shift = bool(state & 0x1)
    k = keysym
    parts = []
    if ctrl:
        parts.append("Control")
    if alt:
        parts.append("Alt")
    if len(k) == 1 and k.isalpha():
        k = k.upper() if shift else k.lower()
    elif shift:
        parts.append("Shift")
    if not (ctrl or alt or re.fullmatch(r"F\d{1,2}", k)):
        return ""
    return "<%s>" % "-".join(parts + [k])

def pretty_key(seq):
    s = seq.strip("<>")
    out = []
    for p in s.split("-"):
        p = {"Control": "Ctrl", "comma": ",", "period": ".", "slash": "/"}.get(p, p)
        out.append(p.upper() if len(p) == 1 else p)
    if "Control" in s and len(s.split("-")[-1]) == 1 and s.split("-")[-1].isupper():
        out.insert(-1, "Shift")
    return "+".join(out)

def src_version(src):
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', src, re.M)
    return m.group(1) if m else ""

def ver_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:4]) or (0,)

# ==========================================================================
# Names and search planning
# ==========================================================================

SEPARATORS = ["", "_", "-", ".", " "]

def split_words(name):
    """'Web Demon' / 'web_demon' / 'WebDemon' -> ['web', 'demon'] (digits stay as their own words)."""
    out = []
    for part in re.split(r"[\s_\-.]+", (name or "").strip()):
        if part:
            out += re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", part) or [part]
    return [w.lower() for w in out]

def name_variants(names, numbers=(), repeat_last=2, limit=400):
    """Spellings people use for one online name: separators, numbers glued on, a repeated last letter.
    'Web Demon' + 7896 -> webdemon, web_demon, web-demon, web.demon, web demon, webdemon7896, web_demon_7896 ..."""
    nums = [str(n).strip() for n in numbers if str(n).strip()]
    seen = {}

    def add(v):
        v = v.strip()
        if v and v.lower() not in seen and len(v) <= 40:
            seen[v.lower()] = v

    forms = []
    for name in names:
        words = split_words(name)
        for w in words:
            if w.isdigit() and w not in nums:
                nums.append(w)
        letters = [w for w in words if not w.isdigit()]
        if not letters:
            continue
        for sep in SEPARATORS:
            forms.append(sep.join(letters))
        forms.append(letters[0])
    repeated = []
    for f in forms:
        if f and f[-1].isalpha():
            repeated += [f + f[-1] * k for k in range(1, repeat_last + 1)]
    for f in forms + repeated:
        add(f)
    for f in forms + repeated:
        for num in nums:
            for sep in SEPARATORS:
                add(f + sep + num)
    return list(seen.values())[:limit]

def search_url(tpl, q):
    return tpl.replace("{q}", urllib.parse.quote(q, safe=""))

MAX_WINDOWS = 12

OR_CHUNK = 5

def plan_searches(variants, templates, chunk=OR_CHUNK):
    """Turn (variants x sites) into as few URLs as possible. A site whose URL has an exact-phrase query
    ("{q}" in quotes) gets several variants OR-ed into ONE search; profile-guess sites need one URL per variant."""
    out = []
    for t in templates:
        url = t.get("url", "")
        vs = [v for v in variants if not (t.get("spaces", True) is False and " " in v)]
        if not vs:
            continue
        if "%22{q}%22" in url:
            for i in range(0, len(vs), chunk):
                q = " OR ".join('"%s"' % v for v in vs[i:i + chunk])
                out.append(url.replace("%22{q}%22", urllib.parse.quote(q, safe="")))
        else:
            for v in vs:
                out.append(search_url(url, v))
    return out

LEET = {"o": "0", "i": "1", "l": "1", "e": "3", "a": "4", "s": "5"}

HANDLE_SUFFIXES = ["_roblox", "rbx", "dc", "yt", "tt", "ig"]

def extra_variants(names, leet=False, suffixes=False):
    """Extra guesses beyond separators/numbers: leetspeak (w3b, we3) and platform tags (web_roblox, webdc)."""
    out, seen = [], set()

    def add(v):
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    for n in names:
        base = re.sub(r"\s+", "", n.strip())
        if not base:
            continue
        if leet:
            full = "".join(LEET.get(c.lower(), c) for c in base)
            if full != base:
                add(full)
            singles = 0
            for i, c in enumerate(base):
                if c.lower() in LEET and singles < 4:
                    add(base[:i] + LEET[c.lower()] + base[i + 1:])
                    singles += 1
        if suffixes:
            for s in HANDLE_SUFFIXES:
                add(base + s)
    return out

# ==========================================================================
# Real life helpers: timezone, birthday
# ==========================================================================

TZ_ABBR = {"EST": -5, "EDT": -4, "CST": -6, "CDT": -5, "MST": -7, "MDT": -6, "PST": -8, "PDT": -7, "AKST": -9,
           "AKDT": -8, "HST": -10, "AST": -4, "NST": -3.5, "GMT": 0, "UTC": 0, "BST": 1, "CET": 1, "CEST": 2,
           "EET": 2, "EEST": 3, "MSK": 3, "IST": 5.5, "PKT": 5, "SGT": 8, "HKT": 8, "JST": 9, "KST": 9,
           "AEST": 10, "AEDT": 11, "NZST": 12, "NZDT": 13}

def parse_tz(text):
    """'UTC-5', '-5:30', 'EST', 'America/Toronto' -> a tzinfo, or None."""
    t = (text or "").strip()
    if not t:
        return None
    up = t.upper()
    if up in TZ_ABBR:
        return datetime.timezone(datetime.timedelta(hours=TZ_ABBR[up]))
    m = re.match(r"^(?:UTC|GMT)?\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", t, re.I)
    if m:
        mins = int(m.group(2)) * 60 + int(m.group(3) or 0)
        return datetime.timezone(datetime.timedelta(minutes=-mins if m.group(1) == "-" else mins))
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(t)
    except Exception:  # noqa - unknown name, or no tz database on this Windows
        return None

def fmt_offset(td):
    mins = int(round(td.total_seconds() / 60))
    sign = "-" if mins < 0 else "+"
    mins = abs(mins)
    return "UTC%s%d%s" % (sign, mins // 60, (":%02d" % (mins % 60)) if mins % 60 else "")

def tz_now_text(text, now=None):
    tz = parse_tz(text)
    if tz is None:
        return "(type UTC-5, EST or America/Toronto)" if (text or "").strip() else ""
    now = (now or datetime.datetime.now(datetime.timezone.utc)).astimezone(tz)
    return "there it is %s (%s)" % (now.strftime("%a %H:%M"), fmt_offset(now.utcoffset()))

def parse_clock(text):
    """'3:15 pm', '15:15', '3pm' -> minutes after midnight, or None."""
    m = re.fullmatch(r"\s*(\d{1,2})(?::(\d{2}))?\s*([ap]\.?m\.?)?\s*", (text or "").lower())
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if mi > 59 or h > 23:
        return None
    if ap:
        if h < 1 or h > 12:
            return None
        h = h % 12 + (12 if ap.startswith("p") else 0)
    return h * 60 + mi

def offset_from_times(their_text, my_text, my_offset=None):
    """'Their clock says X while mine says Y' -> 'UTC-5' (rounded to 15 minutes), or None."""
    a, b = parse_clock(their_text), parse_clock(my_text)
    if a is None or b is None:
        return None
    if my_offset is None:
        my_offset = datetime.datetime.now().astimezone().utcoffset()
    diff = (a - b + 720) % 1440 - 720          # -12h .. +12h
    mins = int(round((my_offset.total_seconds() / 60 + diff) / 15.0)) * 15
    return fmt_offset(datetime.timedelta(minutes=mins))

def parse_birthday(text):
    """Returns (year or None, month, day) for 2008-03-05, 03-05, March 5, 5 March 2008 ... or None."""
    import calendar
    t = (text or "").strip().replace(",", " ")
    t = re.sub(r"\s+", " ", t)
    names = {n.lower(): i for i, n in enumerate(calendar.month_name) if n}
    names.update({n.lower(): i for i, n in enumerate(calendar.month_abbr) if n})
    y = mo = d = None
    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", t)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})", t)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            mo, d = (b, a) if a > 12 else (a, b)
        else:
            m = re.fullmatch(r"([A-Za-z]+)\.? (\d{1,2})(?: (\d{4}))?", t)
            if m and m.group(1).lower() in names:
                mo, d, y = names[m.group(1).lower()], int(m.group(2)), int(m.group(3)) if m.group(3) else None
            else:
                m = re.fullmatch(r"(\d{1,2}) ([A-Za-z]+)\.?(?: (\d{4}))?", t)
                if m and m.group(2).lower() in names:
                    mo, d, y = names[m.group(2).lower()], int(m.group(1)), int(m.group(3)) if m.group(3) else None
    if mo is None:
        return None
    try:
        datetime.date(y or 2000, mo, d)
    except ValueError:
        return None
    return y, mo, d

def birthday_hint(text, today=None):
    b = parse_birthday(text)
    if not (text or "").strip():
        return ""
    if b is None:
        return "(try 2008-03-05, 03-05 or March 5)"
    y, mo, d = b
    today = today or datetime.date.today()

    def on(year):
        try:
            return datetime.date(year, mo, d)
        except ValueError:      # Feb 29 in a non-leap year
            return datetime.date(year, 3, 1)
    nxt = on(today.year)
    if nxt < today:
        nxt = on(today.year + 1)
    days = (nxt - today).days
    when = "birthday today" if days == 0 else "birthday in %d day%s" % (days, "" if days == 1 else "s")
    if y:
        age = today.year - y - ((today.month, today.day) < (mo, d))
        return "age %d, %s" % (age, when)
    return when

# ==========================================================================
# Browser choice
# ==========================================================================

BROWSERS = [("default", "System default"), ("firefox", "Firefox"), ("chrome", "Google Chrome"),
            ("edge", "Microsoft Edge"), ("brave", "Brave"), ("custom", "Other program...")]

def find_browser(kind):
    """Path of an installed browser (PATH, registry 'App Paths', then the usual folders), or ''."""
    import shutil
    names = {"firefox": ["firefox.exe", "firefox"], "chrome": ["chrome.exe", "google-chrome", "chrome"],
             "edge": ["msedge.exe", "microsoft-edge"], "brave": ["brave.exe", "brave-browser", "brave"]}.get(kind)
    if not names:
        return ""
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    try:
        import winreg
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%s" % names[0]) as k:
                    p = winreg.QueryValue(k, None)
                    if p and os.path.exists(p):
                        return p
            except OSError:
                continue
    except ImportError:
        pass
    pf, pf86, la = (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""),
                    os.environ.get("LOCALAPPDATA", ""))
    rel = {"firefox": [(pf, "Mozilla Firefox", "firefox.exe"), (pf86, "Mozilla Firefox", "firefox.exe")],
           "chrome": [(pf, "Google", "Chrome", "Application", "chrome.exe"),
                      (pf86, "Google", "Chrome", "Application", "chrome.exe"),
                      (la, "Google", "Chrome", "Application", "chrome.exe")],
           "edge": [(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
                    (pf, "Microsoft", "Edge", "Application", "msedge.exe")],
           "brave": [(pf, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                     (la, "BraveSoftware", "Brave-Browser", "Application", "brave.exe")]}[kind]
    for parts in rel:
        if parts[0]:
            p = os.path.join(*parts)
            if os.path.exists(p):
                return p
    return ""

def browser_profiles(kind):
    """Profile names to pick from: Firefox from profiles.ini, Chrome/Edge/Brave from their Local State file."""
    out = []
    try:
        if kind == "firefox":
            import configparser
            ini = os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "profiles.ini")
            cp = configparser.ConfigParser()
            cp.read(ini, encoding="utf-8")
            for sec in cp.sections():
                if sec.lower().startswith("profile") and cp.has_option(sec, "Name"):
                    out.append(cp.get(sec, "Name"))
        elif kind in ("chrome", "edge", "brave"):
            la = os.environ.get("LOCALAPPDATA", "")
            path = {"chrome": os.path.join(la, "Google", "Chrome", "User Data", "Local State"),
                    "edge": os.path.join(la, "Microsoft", "Edge", "User Data", "Local State"),
                    "brave": os.path.join(la, "BraveSoftware", "Brave-Browser", "User Data", "Local State")}[kind]
            with open(path, encoding="utf-8") as f:
                cache = json.load(f).get("profile", {}).get("info_cache", {})
            for d, info in cache.items():
                out.append("%s (%s)" % (info.get("name", d), d))
    except Exception:  # noqa - not installed / no such file
        pass
    return out

def browser_command(cfg, urls):
    """argv list that opens urls in the chosen browser/profile, or None for the system default."""
    kind = (cfg or {}).get("kind", "default")
    prof = (cfg or {}).get("profile", "").strip()
    if kind == "default":
        return None
    if kind == "custom":
        path = (cfg.get("path") or "").strip().strip('"')
        if not path:
            return None
        args = (cfg.get("args") or "").strip()
        if "{url}" in args:
            import shlex
            toks = [t.strip('"') for t in shlex.split(args, posix=False)]
            cmd = [path]
            for t in toks:
                if "{url}" in t:
                    cmd += [t.replace("{url}", u) for u in urls]
                else:
                    cmd.append(t)
            return cmd
        return [path] + ([a.strip('"') for a in args.split()] if args else []) + list(urls)
    exe = (cfg.get("path") or "").strip().strip('"') if kind == (cfg.get("path_kind") or "") else ""
    exe = exe or find_browser(kind)
    if not exe:
        return None
    if kind == "firefox":
        cmd = [exe]
        if prof:
            cmd += ["-P", prof]
        for u in urls:
            cmd += ["-new-tab", u]
        return cmd
    cmd = [exe]
    if prof:
        m = re.search(r"\(([^()]+)\)\s*$", prof)
        cmd.append("--profile-directory=%s" % (m.group(1) if m else prof))
    return cmd + list(urls)

# ==========================================================================
# Interface: dialogs and the main window
# ==========================================================================

class Worker:
    """Runs network calls in threads and hands results back to the Tk thread."""

    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.on_error = None
        root.after(100, self.poll)

    def run(self, fn, ok, err):
        def work():
            try:
                self.q.put((ok, fn()))
            except Exception as e:  # noqa
                self.q.put((err, e))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            while True:
                cb, arg = self.q.get_nowait()
                try:
                    cb(arg)
                except Exception:  # noqa - one failing callback must not stop all later ones
                    import traceback
                    log_crash(traceback.format_exc())
                    if self.on_error:
                        self.on_error()
        except queue.Empty:
            pass
        self.root.after(100, self.poll)


# --------------------------------------------------------------------------
# Reusable widgets
# --------------------------------------------------------------------------
class EditableLabel(ttk.Frame):
    """A plain label. Right-click > Rename (or double-click) turns it into an entry; Enter / click away commits."""

    def __init__(self, parent, text, on_commit, on_cancel=None, editing=False, extra_menu=None, width=14, font=None,
                 tone=""):
        super().__init__(parent, **({"style": tone + ".TFrame"} if tone else {}))
        self.lstyle = tone + ".TLabel" if tone else ""
        self.text = text
        self.on_commit = on_commit
        self.on_cancel = on_cancel
        self.extra_menu = extra_menu or []
        self.width = width
        self.font = font
        self.entry = None
        self.done = True
        if editing:
            self.edit(text or "New field")
        else:
            self.show()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def show(self):
        self.clear()
        lbl = ttk.Label(self, text=self.text, font=self.font, **({"style": self.lstyle} if self.lstyle else {}))
        lbl.pack(anchor="w")
        lbl.bind("<Button-3>", self.popup)
        lbl.bind("<Double-Button-1>", lambda e: self.edit())

    def popup(self, e):
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Rename", command=self.edit)
        for label, cmd in self.extra_menu:
            m.add_command(label=label, command=cmd)
        m.tk_popup(e.x_root, e.y_root)

    def edit(self, initial=None):
        self.clear()
        self.done = False
        e = ttk.Entry(self, width=self.width)
        e.insert(0, self.text if initial is None else initial)
        e.pack(fill="x")
        self.entry = e
        e.bind("<Return>", lambda ev: self.finish(True))
        e.bind("<Escape>", lambda ev: self.finish(False))
        e.bind("<FocusOut>", lambda ev: self.finish(True))

        def focus():
            try:
                e.focus_force()
                e.select_range(0, "end")
            except tk.TclError:
                pass
        e.after_idle(focus)

    def finish(self, commit):
        if self.done or not self.winfo_exists():
            return
        self.done = True
        try:
            text = self.entry.get().strip()
        except tk.TclError:
            return
        if commit and text:
            self.text = text
            self.show()
            self.on_commit(text)
        else:
            if self.text:
                self.show()
            if self.on_cancel:
                self.on_cancel()


class PlatformDialog(tk.Toplevel):
    """Pick a platform: type to search presets (Enter picks the highlighted one) or type a brand new name."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.result = None
        self.kind = ""
        self.items = []
        self.title("Add platform")
        self.transient(app.root)
        self.resizable(False, False)
        ttk.Label(self, text="Platform name - start typing to use a preset:").pack(anchor="w", padx=10, pady=(10, 2))
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=40)
        self.entry.pack(fill="x", padx=10)
        self.lb = tk.Listbox(self, height=7, exportselection=False, activestyle="none")
        self.lb.pack(fill="both", expand=True, padx=10, pady=6)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Add", command=self.accept).pack(side="right", padx=6)
        self.var.trace_add("write", lambda *a: self.refresh())
        self.entry.bind("<Return>", lambda e: self.accept())
        self.entry.bind("<Down>", lambda e: self.move(1))
        self.entry.bind("<Up>", lambda e: self.move(-1))
        self.lb.bind("<Double-Button-1>", lambda e: self.accept())
        self.lb.bind("<Return>", lambda e: self.accept())
        self.bind("<Escape>", lambda e: self.destroy())
        self.refresh()
        self.entry.focus_set()
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.wait_window(self)

    def refresh(self):
        text = self.var.get().strip()
        low = text.lower()
        names = [p["name"] for p in self.app.settings["presets"]]
        lib = [p["name"] for p in PRESET_LIBRARY if p["name"].lower() not in {n.lower() for n in names}]
        self.items = []
        if text and low not in [n.lower() for n in names + lib]:
            self.items.append(("custom", text))
        for n in names:
            if low in n.lower():
                self.items.append(("preset", n))
        for n in lib:
            if low in n.lower():
                self.items.append(("library", n))
        self.lb.delete(0, "end")
        for kind, n in self.items:
            self.lb.insert("end", {"custom": 'New platform "%s"' % n, "preset": n + "   (preset)",
                                   "library": n + "   (from library - adds it)"}[kind])
        sel = 0
        for i, (kind, n) in enumerate(self.items):
            if kind != "custom" and low and n.lower().startswith(low):
                sel = i
                break
        if self.items:
            self.lb.selection_set(sel)
            self.lb.activate(sel)

    def move(self, delta):
        if not self.items:
            return "break"
        cur = self.lb.curselection()
        i = (cur[0] if cur else 0) + delta
        i = max(0, min(len(self.items) - 1, i))
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(i)
        self.lb.see(i)
        return "break"

    def accept(self):
        if not self.items:
            return
        cur = self.lb.curselection()
        self.kind, self.result = self.items[cur[0] if cur else 0]
        self.destroy()


class PresetsDialog(tk.Toplevel):
    """Settings > Platform presets. Changes are applied and saved immediately."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.presets = app.settings["presets"]
        self.cur = None
        self.loading = False
        self.title("Platform presets")
        self.geometry("780x560")

        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        self.lb = tk.Listbox(left, width=24, exportselection=False, activestyle="none")
        self.lb.pack(fill="y", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.on_pick())
        lb = ttk.Frame(left)
        lb.pack(fill="x", pady=(6, 0))
        ttk.Button(lb, text="+ New", command=self.new).pack(side="left")
        ttk.Button(lb, text="Delete", command=self.delete).pack(side="left", padx=4)

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        right.columnconfigure(1, weight=1)
        self.name_var = tk.StringVar()
        self.tpl_var = tk.StringVar()
        self.disp_var = tk.BooleanVar()
        self.default_var = tk.BooleanVar()
        self.btn_var = tk.StringVar()
        self.test_var = tk.StringVar()

        ttk.Label(right, text="Name").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(right, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(right, text="Link template").grid(row=1, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.tpl_var).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Label(right, foreground="#666", justify="left", wraplength=480,
                  text="Put {id} (and optionally {username}) where the value goes, e.g.\n"
                       "https://www.roblox.com/users/{id}/profile\n"
                       "The ID is then filled from the link, and the link from the ID.").grid(
            row=2, column=1, sticky="w", pady=(0, 4))

        ttk.Label(right, text="Test a link").grid(row=3, column=0, sticky="w")
        ttk.Entry(right, textvariable=self.test_var).grid(row=3, column=1, sticky="ew", pady=2)
        self.test_lbl = ttk.Label(right, text="", foreground="#666")
        self.test_lbl.grid(row=4, column=1, sticky="w")

        ttk.Checkbutton(right, text="Show a Display Name field", variable=self.disp_var).grid(
            row=5, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(right, text="Add this platform to every new user", variable=self.default_var).grid(
            row=6, column=1, sticky="w")

        ttk.Label(right, text="Buttons").grid(row=7, column=0, sticky="w", pady=(8, 0))
        self.btn_combo = ttk.Combobox(right, textvariable=self.btn_var, state="readonly",
                                      values=list(BUTTON_SETS.values()))
        self.btn_combo.grid(row=7, column=1, sticky="w", pady=(8, 0))

        ttk.Label(right, text="Extra fields\n(one per line,\nadded to new accounts)", justify="left").grid(
            row=8, column=0, sticky="nw", pady=(8, 0))
        self.fields_text = tk.Text(right, height=8, width=30)
        self.fields_text.grid(row=8, column=1, sticky="nsew", pady=(8, 0))
        right.rowconfigure(8, weight=1)

        for v in (self.name_var, self.tpl_var, self.disp_var, self.default_var, self.btn_var):
            v.trace_add("write", self.commit)
        self.tpl_var.trace_add("write", lambda *a: self.test())
        self.test_var.trace_add("write", lambda *a: self.test())
        self.fields_text.bind("<KeyRelease>", self.commit)

        self.refill()
        if self.presets:
            self.select(0)

    def refill(self):
        self.lb.delete(0, "end")
        for p in self.presets:
            self.lb.insert("end", p["name"])

    def select(self, i):
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(i)
        self.on_pick()

    def on_pick(self):
        cur = self.lb.curselection()
        if not cur:
            return
        p = self.presets[cur[0]]
        self.loading = True
        self.cur = p
        self.name_var.set(p["name"])
        self.tpl_var.set(p.get("link_template", ""))
        self.disp_var.set(bool(p.get("display_name")))
        self.default_var.set(bool(p.get("default")))
        self.btn_var.set(BUTTON_SETS.get(p.get("buttons", ""), "None"))
        self.fields_text.delete("1.0", "end")
        self.fields_text.insert("1.0", "\n".join(p.get("fields", [])))
        self.loading = False
        self.test()

    def commit(self, *_):
        if self.loading or self.cur is None:
            return
        p = self.cur
        p["name"] = self.name_var.get().strip() or "Unnamed"
        p["link_template"] = self.tpl_var.get().strip()
        p["display_name"] = bool(self.disp_var.get())
        p["default"] = bool(self.default_var.get())
        label = self.btn_var.get()
        p["buttons"] = next((k for k, v in BUTTON_SETS.items() if v == label), "")
        p["fields"] = [ln.strip() for ln in self.fields_text.get("1.0", "end").splitlines() if ln.strip()]
        idx = self.presets.index(p)
        self.lb.delete(idx)
        self.lb.insert(idx, p["name"])
        self.lb.selection_set(idx)
        self.app.save_settings_soon()

    def test(self):
        link = self.test_var.get().strip()
        if not link:
            self.test_lbl.config(text="")
            return
        got = extract_from_link(self.tpl_var.get(), link)
        self.test_lbl.config(text=("Found: " + ", ".join("%s = %s" % kv for kv in got.items())) if got
                             else "No match - the link does not fit the template.")

    def new(self):
        p = {"name": "New preset", "link_template": "", "display_name": False, "fields": [],
             "buttons": "", "default": False}
        self.presets.append(p)
        self.refill()
        self.select(len(self.presets) - 1)
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")
        self.app.save_settings_soon()

    def delete(self):
        cur = self.lb.curselection()
        if not cur:
            return
        p = self.presets[cur[0]]
        if not self.app.confirm("Delete the preset '%s'?\nPlatforms already on users are kept." % p["name"]):
            return
        self.presets.remove(p)
        self.cur = None
        self.refill()
        if self.presets:
            self.select(0)
        self.app.save_settings_soon()


class HttpTool(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("HTTP request tool")
        self.geometry("820x720")
        self.last_text = ""

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        self.method = ttk.Combobox(top, values=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
                                   width=9, state="readonly")
        self.method.set("GET")
        self.method.pack(side="left")
        self.url = ttk.Entry(top)
        self.url.pack(side="left", fill="x", expand=True, padx=6)
        self.url.insert(0, "https://")
        ttk.Button(top, text="Send", command=self.send).pack(side="left")

        ttk.Label(self, text="Headers (one per line, Key: Value)").pack(anchor="w", padx=8)
        self.headers = tk.Text(self, height=4)
        self.headers.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(self, text="Body").pack(anchor="w", padx=8)
        self.body = tk.Text(self, height=6)
        self.body.pack(fill="x", padx=8, pady=(0, 6))

        bar = ttk.Frame(self, padding=(8, 0))
        bar.pack(fill="x")
        self.info = ttk.Label(bar, text="Ready")
        self.info.pack(side="left")
        ttk.Button(bar, text="Save response to file", command=self.save).pack(side="right")

        frame = ttk.Frame(self, padding=8)
        frame.pack(fill="both", expand=True)
        self.out = tk.Text(frame, wrap="word")
        sb = ttk.Scrollbar(frame, command=self.out.yview)
        self.out.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.out.pack(side="left", fill="both", expand=True)

    def send(self):
        url = self.url.get().strip()
        if not url:
            return
        headers = {}
        for line in self.headers.get("1.0", "end").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()
        body = self.body.get("1.0", "end-1c")
        method = self.method.get()
        self.info.config(text="Sending...")

        def ok(r):
            status, reason, hdrs, text = r
            try:
                text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
            except ValueError:
                pass
            head = "\n".join("%s: %s" % kv for kv in hdrs.items())
            self.last_text = "HTTP %s %s\n%s\n\n%s" % (status, reason, head, text)
            self.out.delete("1.0", "end")
            self.out.insert("1.0", self.last_text)
            self.info.config(text="HTTP %s %s" % (status, reason))

        self.app.worker.run(lambda: do_request(method, url, headers, body or None), ok,
                            lambda e: self.info.config(text="Error: %s" % e))

    def save(self):
        if not self.last_text:
            return
        os.makedirs(RESPONSES_DIR, exist_ok=True)
        path = os.path.join(RESPONSES_DIR, "response-%s.txt" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.last_text)
        self.info.config(text="Saved to " + path)


# --------------------------------------------------------------------------
# Main application
# --------------------------------------------------------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title(APP_NAME)
        root.geometry("1200x760")
        self.worker = Worker(root)
        self.app_cfg = load_app_cfg()
        self.settings_win = None
        self.bound_keys = []
        self.settings = self.load_settings()
        self.data = self.load_data()
        self.apis = self.load_apis()
        self.save_job = None
        self.settings_job = None
        self.current = None        # id of the node shown in the editor
        self.cur_node = None
        self.nav = []
        self.aka_entries = []
        self.main_entry = None
        self.numbers_entry = None
        self.pending_focus = None
        self.drag_src = None
        self.dragging = False
        self.drag_start = (0, 0)
        self.tree_edit = None
        self.autofill_busy = False
        self.dot_cache = {}
        self.gradient_img = None
        self.tag_var = None
        self.tag_combo = None
        self.inner = None
        self.frame_bg = "#f0f0f0"
        self.icon_img = None
        self.worker.on_error = lambda: self.status("Something went wrong - details are in crash.log")
        self.apply_icon()
        self.migrate_data()
        self.build_ui()
        self.apply_keybinds()
        self.root.after(3000, self.auto_check)
        self.rebuild_tree()
        root.title("%s - %s" % (APP_NAME, CURRENT_PROFILE or "profile"))
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ----- files -----
    def load_settings(self):
        s = json.loads(json.dumps(DEFAULT_SETTINGS))
        loaded = None
        existed = os.path.exists(SETTINGS_FILE)
        if existed:
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    loaded = json.load(f)
                if not isinstance(loaded, dict):
                    raise ValueError("not a settings object")
                for k in s:
                    if k in loaded:
                        s[k] = loaded[k]
            except Exception as e:  # noqa
                import shutil
                bad = SETTINGS_FILE + ".corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                try:
                    shutil.copy(SETTINGS_FILE, bad)
                except OSError:
                    pass
                messagebox.showwarning(APP_NAME, "settings.json has a problem (%s).\nA copy was kept as:\n%s\n"
                                                 "Using defaults." % (e, bad))
                s = json.loads(json.dumps(DEFAULT_SETTINGS))
                loaded = None
        old_version = loaded.get("version", 2) if loaded is not None else SETTINGS_VERSION
        if old_version < 3:
            for p in s["presets"]:
                if str(p.get("name", "")).lower() == "roblox" and "Bio" not in p.get("fields", []):
                    p.setdefault("fields", []).append("Bio")
        if old_version < 4 and not any(str(p.get("name", "")).lower() == "real life" for p in s["presets"]):
            s["presets"].append(json.loads(json.dumps(REAL_LIFE_PRESET)))
        s["version"] = SETTINGS_VERSION
        for p in s["presets"]:
            p.setdefault("link_template", "")
            p.setdefault("display_name", False)
            p.setdefault("fields", [])
            p.setdefault("buttons", "")
            p.setdefault("default", False)
        keys = s.get("keys") if isinstance(s.get("keys"), dict) else {}
        pairs = []
        if isinstance(keys.get("bloxlink"), list):
            for it in keys["bloxlink"]:
                if isinstance(it, dict):
                    pairs.append({"guild": str(it.get("guild", "")), "key": str(it.get("key", ""))})
        old_keys = keys.get("bloxlink_keys")
        if isinstance(old_keys, list):  # v3 layout: one server ID + a list of keys -> pairs
            for k in old_keys:
                pairs.append({"guild": str(keys.get("bloxlink_guild", "")), "key": str(k)})
        s["keys"] = {"discord_token": str(keys.get("discord_token", "")), "bloxlink": pairs,
                     "steam_key": str(keys.get("steam_key", ""))}
        if not isinstance(s.get("tags"), list):
            s["tags"] = json.loads(json.dumps(DEFAULT_TAGS))
        for t in s["tags"]:
            t.setdefault("id", uid())
            t.setdefault("name", "Tag")
            t.setdefault("color", "#8b8d98")
        if not isinstance(s.get("search_templates"), list):
            s["search_templates"] = json.loads(json.dumps(DEFAULT_SEARCH))
        ck = self.app_cfg.get("keys")
        if isinstance(ck, dict):  # API keys live in app.json and are shared by every profile
            if not ck.get("discord_token") and s["keys"].get("discord_token"):
                ck["discord_token"] = s["keys"]["discord_token"]
            have = {(p.get("guild"), p.get("key")) for p in ck.get("bloxlink", []) if isinstance(p, dict)}
            for p in s["keys"]["bloxlink"]:
                if (p["guild"], p["key"]) not in have:
                    ck.setdefault("bloxlink", []).append(p)
            ck.setdefault("discord_token", "")
            ck.setdefault("bloxlink", [])
            s["keys"] = ck
        else:
            self.app_cfg["keys"] = s["keys"]
        save_app_cfg(self.app_cfg)
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({k: v for k, v in s.items() if k != "keys"}, f, indent=2, ensure_ascii=False)
        except OSError:
            pass
        return s

    def save_settings_soon(self):
        if self.settings_job:
            self.root.after_cancel(self.settings_job)
        self.settings_job = self.root.after(300, self.save_settings)

    def save_settings(self):
        self.settings_job = None
        try:
            self.app_cfg["keys"] = self.settings.get("keys", {})  # keys are shared by all profiles
            save_app_cfg(self.app_cfg)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump({k: v for k, v in self.settings.items() if k != "keys"}, f, indent=2, ensure_ascii=False)
        except OSError as e:
            self.status("Could not save settings: %s" % e)

    def set_setting(self, key, value):
        self.settings[key] = bool(value)
        self.save_settings_soon()
        if key == "show_tag_text":
            self.refresh_tree_items()
        elif key == "show_scan" and isinstance(self.cur_node, dict):
            self.render_editor(self.cur_node)

    def load_data(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, encoding="utf-8") as f:
                    d = json.load(f)
                d.setdefault("items", [])
                return d
            except Exception as e:  # noqa
                import shutil
                bad = DATA_FILE + ".corrupt-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                shutil.copy(DATA_FILE, bad)
                messagebox.showwarning(APP_NAME, "Could not read users.json (%s).\nA copy was kept as:\n%s\n"
                                                 "Starting with an empty list." % (e, bad))
        return {"items": []}

    def load_apis(self):
        apis = json.loads(json.dumps(DEFAULT_APIS))
        current = False
        missing = False
        if os.path.exists(API_FILE):
            try:
                with open(API_FILE, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict) and loaded.get("_version", 1) >= APIS_VERSION:
                    for k, v in DEFAULT_APIS.items():   # new built-in entries appear without touching your edits
                        if k not in loaded:
                            loaded[k] = v
                            missing = True
                    apis.update(loaded)
                    current = True
                else:
                    import shutil
                    shutil.copy(API_FILE, API_FILE + ".old")  # older layout: keep a copy, write the new one
            except Exception as e:  # noqa
                messagebox.showwarning(APP_NAME, "apis.json has a problem (%s). Using defaults until it is fixed." % e)
                return apis
        if not current or missing:
            try:
                with open(API_FILE, "w", encoding="utf-8") as f:
                    json.dump(apis if current else DEFAULT_APIS, f, indent=2, ensure_ascii=False)
            except OSError:
                pass
        return apis

    def changed(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(400, self.save_now)

    def save_now(self):
        self.save_job = None
        try:
            import shutil
            os.makedirs(DATA_DIR, exist_ok=True)
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            if os.path.exists(DATA_FILE):
                shutil.copy(DATA_FILE, DATA_FILE + ".bak")
            os.replace(tmp, DATA_FILE)
            self.status("Saved at " + datetime.datetime.now().strftime("%H:%M:%S"))
        except Exception as e:  # noqa
            self.status("SAVE FAILED: %s" % e)
            messagebox.showerror(APP_NAME, "Could not save:\n%s" % e)

    def on_close(self):
        if isinstance(self.cur_node, dict) and self.cur_node.get("type") == "user":
            self.prune(self.cur_node)
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_now()
        if self.settings_job:
            self.root.after_cancel(self.settings_job)
            self.save_settings()
        self.root.destroy()

    def status(self, msg):
        self.status_lbl.config(text=msg)

    def error(self, e):
        self.status("Failed")
        messagebox.showwarning(APP_NAME, str(e))

    def confirm(self, msg):
        if not self.settings.get("confirm_delete", True):
            return True
        return messagebox.askyesno(APP_NAME, msg)

    # ----- presets -----
    def preset_of(self, plat):
        name = plat["platform"].strip().lower()
        for p in self.settings["presets"]:
            if p["name"].strip().lower() == name:
                return p
        for p in DEFAULT_PRESETS:
            if p["name"].lower() == name:
                return p
        return {}

    def add_library_preset(self, name):
        """Copy a library preset into this profile and make sure the API entries it needs exist in apis.json."""
        lib = next((p for p in PRESET_LIBRARY if p["name"].lower() == name.lower()), None)
        if lib is None:
            return None
        have = self.find_preset(lib["name"])
        if have is None:
            have = json.loads(json.dumps({k: v for k, v in lib.items() if k != "about"}))
            self.settings["presets"].append(have)
            self.save_settings_soon()
        needed = [lk["api"] for lk in have.get("lookups", [])] + ([have["scan"]] if have.get("scan") else [])
        added = [a for a in needed if a not in self.apis and a in LIB_APIS]
        for a in added:
            self.apis[a] = json.loads(json.dumps(LIB_APIS[a]))
        if added:
            try:
                with open(API_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.apis, f, indent=2, ensure_ascii=False)
            except OSError as e:
                messagebox.showwarning(APP_NAME, "Could not write apis.json (%s)." % e)
        return have

    def find_preset(self, name):
        low = name.strip().lower()
        for p in self.settings["presets"]:
            if p["name"].strip().lower() == low:
                return p
        return None

    def make_user(self, name):
        accounts = []
        for p in self.settings["presets"]:
            if p.get("default"):
                accounts.append({"platform": p["name"], "entries": [new_entry(p)]})
        return {"id": uid(), "type": "user", "name": name, "main_name": name, "real_name": "", "numbers": "",
                "akas": [], "accounts": accounts, "notes": ""}

    # ----- icons -----
    def make_icons(self):
        self.icons = {}
        self.icons["dot:"] = self.draw_dot(None)
        for _n, hexc in COLORS:
            if hexc:
                self.icons["dot:" + hexc] = self.draw_dot(hexc)
        folder = tk.PhotoImage(width=16, height=14)
        folder.put("#c98d1a", to=(0, 0, 7, 3))
        folder.put("#e3a72f", to=(0, 2, 16, 14))
        self.icons["folder"] = folder

    def draw_dot(self, color, size=14):
        img = tk.PhotoImage(width=size, height=size)
        c = (size - 1) / 2.0
        r = size / 2.0 - 1.2
        for y in range(size):
            for x in range(size):
                d = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
                if color:
                    if d <= r:
                        img.put(color, to=(x, y))
                elif r - 1.4 <= d <= r:
                    img.put("#b0b0b0", to=(x, y))
        return img

    def icon_for(self, n):
        if n["type"] == "group":
            return self.icons["folder"]
        return self.icons.get("dot:" + n.get("color", ""), self.icons["dot:"])

    # ----- UI skeleton -----
    def build_ui(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=24)
        self.plat_bg, self.acct_bg, self.head_bg = "#d4d4da", "#f8f8f9", "#e6e6ea"
        for tone, bg in (("Plat", self.plat_bg), ("Acct", self.acct_bg)):
            style.configure(tone + ".TFrame", background=bg)
            style.configure(tone + ".TLabel", background=bg)
        self.frame_bg = style.lookup("TFrame", "background") or self.root.cget("bg")
        try:
            self.root.configure(bg=self.frame_bg)
        except tk.TclError:
            pass

        menu = tk.Menu(self.root)
        fm = tk.Menu(menu, tearoff=0)
        fm.add_command(label="Save now", command=self.save_now, accelerator="Ctrl+S")
        fm.add_command(label="Switch profile...", command=self.switch_profile)
        fm.add_command(label="Open profile folder", command=lambda: self.open_path(os.path.dirname(DATA_DIR)))
        fm.add_separator()
        fm.add_command(label="Exit", command=self.on_close)
        menu.add_cascade(label="File", menu=fm)

        tm = tk.Menu(menu, tearoff=0)
        tm.add_command(label="HTTP request tool...", command=lambda: HttpTool(self))
        tm.add_command(label="Open apis.json", command=lambda: self.open_path(API_FILE))
        tm.add_command(label="Reload apis.json", command=self.reload_apis)
        menu.add_cascade(label="Tools", menu=tm)

        sm = tk.Menu(menu, tearoff=0)
        sm.add_command(label="Settings...", command=self.open_settings, accelerator="Ctrl+,")
        sm.add_separator()
        sm.add_command(label="Platform presets...", command=lambda: PresetsDialog(self))
        sm.add_command(label="Preset library (GitHub, Bluesky, Steam...)", command=lambda: PresetLibraryDialog(self))
        sm.add_command(label="Tags (colors)...", command=lambda: TagsDialog(self))
        sm.add_command(label="API keys...", command=lambda: KeysDialog(self))
        sm.add_separator()
        sm.add_command(label="Install update from file...", command=self.install_update)
        sm.add_command(label="Reload settings.json", command=self.reload_settings)
        menu.add_cascade(label="Settings", menu=sm)

        hm = tk.Menu(menu, tearoff=0)
        hm.add_command(label="Quick tour", command=self.open_tour)
        hm.add_command(label="Terms and disclaimers", command=self.open_terms)
        hm.add_command(label="About ModDesk", command=lambda: self.open_settings(4))
        menu.add_cascade(label="Help", menu=hm)
        self.root.config(menu=menu)

        self.status_lbl = ttk.Label(self.root, text="Ready", anchor="w", padding=(8, 2))
        self.status_lbl.pack(side="bottom", fill="x")

        pw = ttk.PanedWindow(self.root, orient="horizontal")
        pw.pack(fill="both", expand=True)

        # left: tree
        left = ttk.Frame(pw, padding=6)
        pw.add(left, weight=1)
        srow = ttk.Frame(left)
        srow.pack(fill="x")
        ttk.Label(srow, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.rebuild_tree())
        self.search_entry = ttk.Entry(srow, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=4)

        brow = ttk.Frame(left)
        brow.pack(fill="x", pady=4)
        ttk.Button(brow, text="+ Group", command=self.add_group).pack(side="left")
        ttk.Button(brow, text="+ User", command=self.add_user).pack(side="left", padx=4)
        ttk.Button(brow, text="Rename", command=self.rename_selected).pack(side="left")
        ttk.Button(brow, text="Delete", command=self.delete_selected).pack(side="left", padx=4)

        trow = ttk.Frame(left)
        trow.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(trow, show="tree", selectmode="browse")
        tsb = ttk.Scrollbar(trow, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<<TreeviewOpen>>", lambda e: self.set_open(True))
        self.tree.bind("<<TreeviewClose>>", lambda e: self.set_open(False))
        self.tree.bind("<ButtonPress-1>", self.on_press)
        self.tree.bind("<B1-Motion>", self.on_motion)
        self.tree.bind("<ButtonRelease-1>", self.on_release)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<F2>", lambda e: self.rename_selected())
        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        ttk.Label(left, foreground="#666", justify="left",
                  text="Click a dot to cycle its tag (Settings > Tags). F2 = rename.\n"
                       "Drag onto a group to move; drop on empty space = top level.").pack(anchor="w", pady=(4, 0))

        self.ctx = tk.Menu(self.root, tearoff=0)
        self.ctx.add_command(label="New group here", command=self.add_group)
        self.ctx.add_command(label="New user here", command=self.add_user)
        self.ctx.add_command(label="Rename", command=self.rename_selected)
        self.tag_menu = tk.Menu(self.ctx, tearoff=0)
        self.ctx.add_cascade(label="Tag", menu=self.tag_menu)
        self.ctx.add_command(label="Move to top level", command=self.move_to_top)
        self.ctx.add_separator()
        self.ctx.add_command(label="Delete", command=self.delete_selected)

        # right: scrollable editor. Pages are built off-screen and swapped in (see attach_inner), so it never flashes.
        right = ttk.Frame(pw)
        pw.add(right, weight=3)
        self.canvas = tk.Canvas(right, highlightthickness=0, bg=self.frame_bg)
        rsb = ttk.Scrollbar(right, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=rsb.set)
        rsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.win_id = self.canvas.create_window((0, 0), anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win_id, width=e.width))
        self.root.bind_all("<MouseWheel>", self.on_wheel)  # one permanent binding; on_wheel checks where the pointer is
        self.show_placeholder()

    def on_wheel(self, e):
        w = self.root.winfo_containing(e.x_root, e.y_root)
        inside = False
        while w is not None:
            if w is self.canvas:
                inside = True
                break
            if isinstance(w, (tk.Toplevel, tk.Tk)):
                break
            w = getattr(w, "master", None)
        if not inside:
            return
        under = self.root.winfo_containing(e.x_root, e.y_root)
        if isinstance(under, tk.Text):
            lo, hi = under.yview()
            if not (lo <= 0.0 and hi >= 1.0):
                return  # the notes box scrolls itself
        self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")

    def show_placeholder(self):
        self.current = None
        self.cur_node = None
        self.tag_var = None
        f = ttk.Frame(self.canvas)
        ttk.Label(f, text="Select or create a user on the left.", padding=20).pack()
        self.attach_inner(f)

    def open_path(self, path):
        try:
            if hasattr(os, "startfile"):
                os.startfile(path)  # Windows
            else:
                import webbrowser
                webbrowser.open("file://" + path)
        except Exception as e:  # noqa
            self.error(e)

    def reload_apis(self):
        self.apis = self.load_apis()
        self.status("apis.json reloaded")

    # ----- model helpers -----
    def locate(self, nid, items=None):
        items = self.data["items"] if items is None else items
        for n in items:
            if n["id"] == nid:
                return n, items
            if n["type"] == "group":
                r = self.locate(nid, n["children"])
                if r:
                    return r
        return None

    def contains(self, group, nid):
        for c in group.get("children", []):
            if c["id"] == nid or (c["type"] == "group" and self.contains(c, nid)):
                return True
        return False

    def selected_id(self):
        s = self.tree.selection()
        return s[0] if s else None

    def container_for(self, iid):
        if not iid:
            return self.data["items"]
        r = self.locate(iid)
        if not r:
            return self.data["items"]
        n, lst = r
        if n["type"] == "group":
            n["open"] = True
            return n["children"]
        return lst

    def user_blob(self, n):
        parts = [n["name"], n.get("main_name", ""), n.get("real_name", ""), n.get("numbers", ""), n.get("notes", "")]
        t = self.tag_of(n)
        if t:
            parts.append(t["name"])
        parts += [a["name"] for a in n.get("akas", [])]
        for p in n.get("accounts", []):
            parts.append(p["platform"])
            for e in p["entries"]:
                parts += [e.get("username", ""), e.get("display", ""), e.get("id", ""), e.get("link", ""),
                          e.get("notes", "")]
                parts += [x.get("key", "") + " " + x.get("value", "") for x in e.get("extra", [])]
        return " ".join(parts).lower()

    def prune(self, node):
        """Drop AKA rows that were left empty."""
        before = len(node.get("akas", []))
        node["akas"] = [a for a in node.get("akas", []) if a.get("name", "").strip()]
        if len(node["akas"]) != before:
            self.changed()

    # ----- tree -----
    def rebuild_tree(self, select=None):
        self.kill_tree_edit()
        keep = select or self.selected_id()
        q = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        if q:
            def walk(items, path):
                for n in items:
                    if n["type"] == "group":
                        walk(n["children"], path + [n["name"]])
                    elif q in self.user_blob(n):
                        label = self.node_label(n) + ("   (" + " / ".join(path) + ")" if path else "")
                        self.tree.insert("", "end", iid=n["id"], text=label, image=self.node_image(n))
            walk(self.data["items"], [])
        else:
            self.insert_items("", self.data["items"])
        if keep and self.tree.exists(keep):
            self.tree.selection_set(keep)
            self.tree.see(keep)

    def insert_items(self, parent, items):
        for n in sorted(items, key=lambda x: (x["type"] != "group", x["name"].lower())):
            if n["type"] == "group":
                self.tree.insert(parent, "end", iid=n["id"], text=self.node_label(n), open=n.get("open", False))
                self.insert_items(n["id"], n["children"])
            else:
                self.tree.insert(parent, "end", iid=n["id"], text=self.node_label(n), image=self.node_image(n))

    def set_open(self, state):
        iid = self.tree.focus()
        r = self.locate(iid) if iid else None
        if r and r[0]["type"] == "group":
            r[0]["open"] = state
            self.changed()

    def on_select(self, _e):
        sid = self.selected_id()
        if not sid or sid == self.current:
            return
        r = self.locate(sid)
        if r:
            self.render_editor(r[0])

    # inline editing of tree rows (like File Explorer)
    def kill_tree_edit(self):
        if self.tree_edit:
            ent, state = self.tree_edit
            state["done"] = True
            self.tree_edit = None
            try:
                ent.destroy()
            except tk.TclError:
                pass

    def start_tree_edit(self, iid, initial, on_done):
        self.kill_tree_edit()
        self.tree.see(iid)
        self.tree.update_idletasks()
        bb = self.tree.bbox(iid, "#0")
        if not bb:
            on_done(None)
            return
        x, y, w, h = bb
        off = 22
        width = max(100, min(w - off, self.tree.winfo_width() - x - off - 4))
        ent = ttk.Entry(self.tree)
        ent.insert(0, initial)
        ent.place(x=x + off, y=y, width=width, height=h)
        state = {"done": False}

        def finish(commit):
            if state["done"]:
                return
            state["done"] = True
            try:
                text = ent.get().strip()
            except tk.TclError:
                text = ""
            self.tree_edit = None
            try:
                ent.destroy()
            except tk.TclError:
                pass
            on_done(text if commit and text else None)

        ent.bind("<Return>", lambda e: finish(True))
        ent.bind("<Escape>", lambda e: finish(False))
        ent.bind("<FocusOut>", lambda e: finish(True))
        self.tree_edit = (ent, state)

        def focus():
            try:
                ent.focus_force()
                ent.select_range(0, "end")
                ent.icursor("end")
            except tk.TclError:
                pass
        ent.after_idle(focus)

    def apply_rename(self, n, text):
        if text is None or text == n["name"]:
            return
        old = n["name"]
        n["name"] = text
        if n["type"] == "user" and n.get("main_name", "") in ("", old):
            n["main_name"] = text
        self.changed()

    def add_group(self):
        sel = self.selected_id()
        if self.search_var.get():
            self.search_var.set("")
        n = new_group("New group")
        self.container_for(sel).append(n)
        self.changed()
        self.insert_row(n, sel)
        self.tree.selection_set(n["id"])

        def done(text):
            self.apply_rename(n, text)
            self.refresh_item(n)
            self.resort_item(n)
        self.start_tree_edit(n["id"], n["name"], done)

    def add_user(self):
        sel = self.selected_id()
        if self.search_var.get():
            self.search_var.set("")
        n = self.make_user("New user")
        self.container_for(sel).append(n)
        self.changed()
        self.insert_row(n, sel)
        self.tree.selection_set(n["id"])

        def done(text):
            self.apply_rename(n, text)
            self.refresh_item(n)
            self.resort_item(n)
            self.render_editor(n)
        self.start_tree_edit(n["id"], n["name"], done)

    def rename_selected(self):
        sid = self.selected_id()
        r = self.locate(sid) if sid else None
        if not r:
            return
        n = r[0]

        def done(text):
            self.apply_rename(n, text)
            self.refresh_item(n)
            self.resort_item(n)
            if n["type"] == "user" and self.current == sid:
                self.render_editor(n)
        self.start_tree_edit(sid, n["name"], done)

    def delete_selected(self):
        sid = self.selected_id()
        r = self.locate(sid) if sid else None
        if not r:
            return
        n, lst = r
        what = "the group '%s' and everything inside it" % n["name"] if n["type"] == "group" else "'%s'" % n["name"]
        if not self.confirm("Delete %s?\nThis cannot be undone." % what):
            return
        lst.remove(n)
        self.changed()
        if self.current == sid or (n["type"] == "group" and self.current and not self.locate(self.current)):
            self.show_placeholder()
        self.rebuild_tree()

    def move_to_top(self):
        sid = self.selected_id()
        r = self.locate(sid) if sid else None
        if not r:
            return
        n, lst = r
        if lst is not self.data["items"]:
            lst.remove(n)
            self.data["items"].append(n)
            self.changed()
            self.rebuild_tree(select=sid)

    # colors
    def cycle_color(self, n):
        order = [h for _n, h in COLORS]
        cur = n.get("color", "")
        nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else order[1]
        self.set_color(n, nxt)

    def set_color(self, n, hexc):
        n["color"] = hexc
        self.changed()
        if self.tree.exists(n["id"]):
            self.tree.item(n["id"], image=self.icon_for(n))

    def set_color_selected(self, hexc):
        sid = self.selected_id()
        r = self.locate(sid) if sid else None
        if r and r[0]["type"] == "user":
            self.set_color(r[0], hexc)

    def on_right_click(self, e):
        row = self.tree.identify_row(e.y)
        if row:
            self.tree.selection_set(row)
        else:
            self.tree.selection_remove(self.tree.selection())
        self.tag_menu.delete(0, "end")
        self.tag_menu.add_command(label="(none)", command=lambda: self.set_tag_selected(""))
        for t in self.settings["tags"]:
            self.tag_menu.add_command(label="● " + t["name"], foreground=t["color"],
                                      command=lambda i=t["id"]: self.set_tag_selected(i))
        self.ctx.tk_popup(e.x_root, e.y_root)

    # click on a dot / drag & drop
    def is_icon_click(self, e, row):
        try:
            elem = str(self.tree.identify_element(e.x, e.y))
        except (tk.TclError, AttributeError):
            elem = ""
        if elem:
            return elem.endswith("image")
        bb = self.tree.bbox(row, "#0")
        return bool(bb) and bb[0] <= e.x <= bb[0] + 20

    def on_press(self, e):
        row = self.tree.identify_row(e.y)
        self.drag_src = row or None
        self.drag_start = (e.x, e.y)
        self.dragging = False
        if row and self.is_icon_click(e, row):
            r = self.locate(row)
            if r and r[0]["type"] == "user":
                self.cycle_tag(r[0])
                self.drag_src = None

    def on_motion(self, e):
        if not self.drag_src or self.search_var.get().strip():
            return
        if not self.dragging and abs(e.x - self.drag_start[0]) + abs(e.y - self.drag_start[1]) > 8:
            self.dragging = True
            self.tree.configure(cursor="hand2")

    def on_release(self, e):
        self.tree.configure(cursor="")
        if self.dragging and self.drag_src:
            self.drop(self.drag_src, self.tree.identify_row(e.y) or None)
        self.dragging = False
        self.drag_src = None

    def drop(self, src, target):
        r = self.locate(src)
        if not r or target == src:
            return
        n, src_list = r
        if target is None:
            dest = self.data["items"]
        else:
            t = self.locate(target)
            if not t:
                return
            tn, tlist = t
            if tn["type"] == "group":
                if tn["id"] == n["id"] or (n["type"] == "group" and self.contains(n, tn["id"])):
                    return
                tn["open"] = True
                dest = tn["children"]
            else:
                if n["type"] == "group" and self.contains(n, tn["id"]):
                    return
                dest = tlist
        if dest is src_list:
            return
        src_list.remove(n)
        dest.append(n)
        self.changed()
        self.rebuild_tree(select=src)

    # ----- editor helpers -----
    def entry_bound(self, parent, d, key, width=30, fkey=None):
        var = tk.StringVar(value=d.get(key, ""))

        def on_write(*_):
            d[key] = var.get()
            self.changed()
        var.trace_add("write", on_write)
        e = ttk.Entry(parent, textvariable=var, width=width)
        e._var = var
        e._fkey = fkey
        self.nav.append(e)
        e.bind("<Return>", lambda ev, w=e: self.on_enter(w))
        e.bind("<Down>", lambda ev, w=e: self.nav_move(w, 1))
        e.bind("<Up>", lambda ev, w=e: self.nav_move(w, -1))
        return e, var

    def text_bound(self, parent, d, key, height):
        t = tk.Text(parent, height=height, wrap="word", undo=True)
        t.insert("1.0", d.get(key, ""))

        def sync(*_):
            d[key] = t.get("1.0", "end-1c")
            self.changed()
        t.bind("<KeyRelease>", sync)
        t.bind("<<Paste>>", lambda e: t.after(10, sync))
        return t

    def focus_widget(self, w):
        try:
            w.focus_set()
            if isinstance(w, ttk.Entry):
                w.select_range(0, "end")
                w.icursor("end")
        except tk.TclError:
            return
        self.ensure_visible(w)

    def ensure_visible(self, w):
        try:
            self.root.update_idletasks()
            top = w.winfo_rooty() - self.inner.winfo_rooty()
            bottom = top + w.winfo_height()
            total = max(1, self.inner.winfo_height())
            view = self.canvas.winfo_height()
            y0 = self.canvas.yview()[0] * total
            if top < y0:
                self.canvas.yview_moveto(max(0.0, (top - 12) / total))
            elif bottom > y0 + view:
                self.canvas.yview_moveto(min(1.0, (bottom - view + 12) / total))
        except tk.TclError:
            pass

    def nav_move(self, w, delta):
        if w not in self.nav:
            return "break"
        i = self.nav.index(w) + delta
        if 0 <= i < len(self.nav):
            self.focus_widget(self.nav[i])
        return "break"

    def on_enter(self, w):
        node = self.cur_node
        if node is None:
            return
        if w is self.numbers_entry and not node["akas"]:
            self.add_aka(node)
            return
        if self.aka_entries and w is self.aka_entries[-1] and w.get().strip():
            self.add_aka(node)
            return
        self.nav_move(w, 1)

    def add_aka(self, node):
        a = {"name": ""}
        node["akas"].append(a)
        self.changed()
        self.render_editor(node, focus=("aka", id(a)))

    def apply_focus(self):
        key = self.pending_focus
        self.pending_focus = None
        if not key:
            return
        for w in self.nav:
            if getattr(w, "_fkey", None) == key:
                self.focus_widget(w)
                return

    def rerender(self, node, focus=None):
        if self.current == node["id"]:
            self.render_editor(node, focus=focus)

    def append_to(self, lst, item, node, focus=None):
        lst.append(item)
        self.changed()
        self.rerender(node, focus)

    def remove_from(self, lst, item, node):
        lst.remove(item)
        self.changed()
        self.rerender(node)

    # ----- editor -----
    def render_editor(self, node, focus=None):
        same = self.current == node["id"]
        ypix = self.canvas.canvasy(0) if same else 0
        if isinstance(self.cur_node, dict) and self.cur_node is not node and self.cur_node.get("type") == "user":
            self.prune(self.cur_node)
        self.current = node["id"]
        self.cur_node = node
        self.nav = []
        self.aka_entries = []
        self.main_entry = None
        self.numbers_entry = None
        self.pending_focus = focus
        self.tag_var = None
        self.tag_combo = None
        inner = ttk.Frame(self.canvas)  # built off-screen, swapped in below
        if node["type"] == "group":
            n = len(node["children"])
            ttk.Label(inner, text="Group: %s" % node["name"], font=("Segoe UI", 13, "bold"),
                      padding=(12, 12, 12, 2)).pack(anchor="w")
            ttk.Label(inner, text="%d item(s) directly inside. Rename: select it and press F2." % n,
                      padding=(12, 0)).pack(anchor="w")
            self.attach_inner(inner)
            return
        self.build_user_editor(inner, node)
        try:
            self.attach_inner(inner)
            # size the page now (not "later"), then put the scroll back at the same pixel offset
            inner.update_idletasks()
            h = max(inner.winfo_reqheight(), 1)
            w = max(self.canvas.winfo_width(), 1)
            self.canvas.configure(scrollregion=(0, 0, w, h))
            view = max(self.canvas.winfo_height(), 1)
            top = min(ypix, max(0, h - view))
            self.canvas.yview_moveto(top / h)
        except tk.TclError:
            pass
        self.root.after_idle(self.apply_focus)

    def collapse_all(self, node, flag):
        for p in node["accounts"]:
            for e in p["entries"]:
                e["collapsed"] = flag
        self.changed()
        self.rerender(node)

    def add_platform(self, node):
        d = PlatformDialog(self)
        if not d.result:
            return
        preset = self.add_library_preset(d.result) if d.kind == "library" else self.find_preset(d.result)
        plat = {"platform": preset["name"] if preset else d.result, "entries": [new_entry(preset)]}
        self.append_to(node["accounts"], plat, node)

    def platform_renamed(self, node, plat, text):
        plat["platform"] = text
        self.changed()
        self.rerender(node)

    def delete_platform(self, node, plat):
        if self.confirm("Delete the platform '%s' and all its accounts?" % plat["platform"]):
            self.remove_from(node["accounts"], plat, node)

    def delete_entry(self, node, plat, ent):
        if self.confirm("Delete this account?"):
            self.remove_from(plat["entries"], ent, node)

    def toggle_collapse(self, node, ent):
        ent["collapsed"] = not ent.get("collapsed", False)
        self.changed()
        self.rerender(node)

    def toggle_main(self, node, plat, ent):
        was = ent.get("main", False)
        for e in plat["entries"]:
            e["main"] = False
        ent["main"] = not was
        self.changed()
        self.rerender(node)

    def render_platform(self, parent, node, plat):
        pf = ttk.Frame(parent, style="Plat.TFrame", relief="ridge", borderwidth=1, padding=6)
        pf.pack(fill="x", pady=4)
        head = ttk.Frame(pf, style="Plat.TFrame")
        head.pack(fill="x")
        EditableLabel(head, plat["platform"], lambda t: self.platform_renamed(node, plat, t),
                      extra_menu=[("Delete platform", lambda: self.delete_platform(node, plat))],
                      width=20, font=("Segoe UI", 10, "bold"), tone="Plat").pack(side="left")
        ttk.Button(head, text="+ Account",
                   command=lambda: self.append_to(plat["entries"], new_entry(self.preset_of(plat)), node)
                   ).pack(side="left", padx=8)
        preset = self.preset_of(plat)
        # starred (main) account first
        for ent in sorted(plat["entries"], key=lambda e: not e.get("main", False)):
            self.render_entry(pf, node, plat, ent, preset)

    def entry_summary(self, ent):
        main = ent.get("username", "").strip() or ent.get("display", "").strip() or ent.get("id", "").strip()
        if not main:
            x = next((x for x in ent.get("extra", []) if x.get("value", "").strip()), None)
            if x:
                main = "%s: %s" % (x.get("key", "").strip() or "field", x["value"].strip())
        text = main or "(empty account)"
        if ent.get("username", "").strip() and ent.get("display", "").strip():
            text += "  •  " + ent["display"].strip()
        if ent.get("id", "").strip() and main != ent["id"].strip():
            text += "  •  ID " + ent["id"].strip()
        lvl = (ent.get("conf") or {}).get("level") if isinstance(ent.get("conf"), dict) else ""
        if lvl:
            text += "  [%s]" % lvl
        return text

    def render_entry(self, parent, node, plat, ent, preset):
        kind = preset.get("buttons", "")
        main = bool(ent.get("main"))
        edge = "#e0a800" if main else "#85858c"
        box = tk.Frame(parent, bg=self.acct_bg, bd=0, highlightthickness=2 if main else 1,
                       highlightbackground=edge, highlightcolor=edge)
        box.pack(fill="x", pady=3)
        collapsed = ent.get("collapsed", False)
        hdr, set_summary = self.entry_header(box, node, plat, ent, main, collapsed)
        hdr.pack(fill="x")
        if collapsed:
            return

        body = ttk.Frame(box, padding=4, style="Acct.TFrame")
        body.pack(fill="x")
        body.columnconfigure(1, weight=1)
        vars_ = {}
        row = [0]

        def add_row(text, key):
            ttk.Label(body, text=text, style="Acct.TLabel").grid(row=row[0], column=0, sticky="w", padx=(0, 6))
            e, v = self.entry_bound(body, ent, key, fkey=("ent", id(ent), key))
            e.grid(row=row[0], column=1, sticky="ew", pady=1)
            bf = ttk.Frame(body, style="Acct.TFrame")
            bf.grid(row=row[0], column=2, sticky="w", padx=4)
            vars_[key] = v
            row[0] += 1
            v.trace_add("write", lambda *a: set_summary(self.entry_summary(ent)))
            return e, bf

        hide_core = bool(preset.get("hide_core"))
        if hide_core:                       # e.g. "Real life": only the preset's own fields
            eu = ei = el = None
            ub = ib = lb = ttk.Frame(body)  # never shown
        else:
            eu, ub = add_row("Username", "username")
            if preset.get("display_name"):
                add_row("Display Name", "display")
            ei, ib = add_row("ID", "id")
            el, lb = add_row("Link", "link")

        # Only a field you actually changed drives the others, so you can clear a link or ID without it coming back.
        seen = {}

        def focus_in(ev, k):
            seen[k] = vars_[k].get()

        def focus_out(ev, k):
            if k in seen and seen[k] != vars_[k].get():
                self.link_id_sync(plat, ent, vars_, src=k)
        for w, k in ((eu, "username"), (ei, "id"), (el, "link")):
            if w is None:
                continue
            w.bind("<FocusIn>", lambda ev, k=k: focus_in(ev, k), add="+")
            w.bind("<FocusOut>", lambda ev, k=k: focus_out(ev, k), add="+")

        if kind == "roblox":
            ttk.Button(ub, text="2rblxId", command=lambda: self.convert(
                "rblx_user_to_id", node, plat, ent, "username", "id")).pack(side="left")
            ttk.Button(ib, text="2discord", command=lambda: self.cross(
                node, "rblx_id_to_discord", ent, "discord")).pack(side="left")
        elif kind == "discord":
            ttk.Button(ub, text="2discId", command=lambda: self.convert(
                "discord_user_to_id", node, plat, ent, "username", "id")).pack(side="left")
            ttk.Button(ib, text="2roblox", command=lambda: self.cross(
                node, "discord_id_to_roblox", ent, "roblox")).pack(side="left")
        if kind in ("roblox", "discord"):
            if self.settings.get("show_scan", True):
                ttk.Button(ib, text="Scan", command=lambda: self.scan(node, plat, kind, ent)).pack(side="left", padx=2)
            if self.settings.get("show_scan", True):
                ttk.Button(ib, text="Condo", command=lambda: CondoDialog(self, kind, ent)).pack(side="left")
            ttk.Button(ib, text="Avatar", command=lambda: AvatarDialog(self, node, plat, ent, kind)).pack(side="left")
        if kind not in ("roblox", "discord") and not hide_core:
            for lk in preset.get("lookups", []):
                host = ub if lk.get("src") == "username" else ib
                ttk.Button(host, text=lk.get("label", "lookup"), command=lambda lk=lk: self.convert(
                    lk["api"], node, plat, ent, lk["src"], lk["dst"])).pack(side="left", padx=1)
            if preset.get("scan") and self.settings.get("show_scan", True):
                ttk.Button(ib, text="Scan", command=lambda: self.generic_scan(node, plat, ent, preset)).pack(
                    side="left", padx=2)
        if not hide_core:
            ob = ttk.Button(lb, text="Open", command=lambda: self.open_link(vars_["link"].get()))
            ob.pack(side="left")

        ttk.Label(body, text="Confidence", style="Acct.TLabel").grid(row=row[0], column=0, sticky="w", padx=(0, 6))
        cf = ttk.Frame(body, style="Acct.TFrame")
        cf.grid(row=row[0], column=1, sticky="ew", pady=1)
        ccb, cen = self.conf_widgets(cf, ent, on_change=lambda: set_summary(self.entry_summary(ent)))
        ccb.pack(side="left")
        ttk.Label(cf, text="found via", style="Acct.TLabel").pack(side="left", padx=(8, 4))
        cen.pack(side="left", fill="x", expand=True)
        row[0] += 1

        # custom fields: the title is a normal label (right-click to rename / delete)
        for x in ent.get("extra", []):
            new_field = not x.get("key")
            lab = EditableLabel(
                body, x.get("key", ""),
                on_commit=lambda t, x=x: self.field_titled(node, x, t),
                on_cancel=lambda x=x: self.field_cancelled(node, ent, x),
                editing=new_field,
                extra_menu=[("Delete field", lambda x=x: self.remove_from(ent["extra"], x, node))], tone="Acct")
            lab.grid(row=row[0], column=0, sticky="w", padx=(0, 6))
            e, _v = self.entry_bound(body, x, "value", fkey=("xval", id(x)))
            e.grid(row=row[0], column=1, sticky="ew", pady=1)
            kl = x.get("key", "").strip().lower()
            if kl in ("timezone", "time zone", "tz"):
                hf = ttk.Frame(body, style="Acct.TFrame")
                hf.grid(row=row[0], column=2, sticky="w", padx=4)
                hl = ttk.Label(hf, text=tz_now_text(x.get("value", "")), style="Acct.TLabel")
                ttk.Button(hf, text="Work out...", command=lambda v=_v: TimezoneDialog(self, v.set)).pack(side="left")
                hl.pack(side="left", padx=6)
                _v.trace_add("write", lambda *a, v=_v, hl=hl: hl.configure(text=tz_now_text(v.get())))
            elif kl in ("birthday", "birthdate", "birth date", "date of birth", "dob"):
                hl = ttk.Label(body, text=birthday_hint(x.get("value", "")), style="Acct.TLabel")
                hl.grid(row=row[0], column=2, sticky="w", padx=4)
                _v.trace_add("write", lambda *a, v=_v, hl=hl: hl.configure(text=birthday_hint(v.get())))
            row[0] += 1

        fr = ttk.Frame(body, style="Acct.TFrame")
        fr.grid(row=row[0], column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Button(fr, text="+ Field", command=lambda: self.append_to(
            ent["extra"], {"key": "", "value": ""}, node)).pack(side="left")
        row[0] += 1

        ttk.Label(body, text="Notes / scan output", style="Acct.TLabel").grid(row=row[0], column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.text_bound(body, ent, "notes", 5).grid(row=row[0] + 1, column=0, columnspan=3, sticky="ew")

    def field_titled(self, node, x, text):
        x["key"] = text
        self.changed()
        self.rerender(node, focus=("xval", id(x)))

    def field_cancelled(self, node, ent, x):
        if not x.get("key") and x in ent["extra"]:
            ent["extra"].remove(x)
            self.changed()
            self.rerender(node)

    def open_link(self, url):
        url = url.strip()
        if url.lower().startswith(("http://", "https://")):
            self.open_external([url])
        else:
            self.status("The link must start with http:// or https://")

    # ----- link <-> id -----
    def link_id_sync(self, plat, ent, vars_=None, force=False, src=None):
        """Fill ID/username from the link, or the link from the ID, using the preset's link template.
        src = the field you just edited: only it drives the others, and an emptied field is never refilled."""
        if not force and not self.settings.get("auto_link", True):
            return False
        tpl = self.preset_of(plat).get("link_template", "")
        if not tpl:
            return False
        changed = [False]

        def put(key, val):
            v = (vars_ or {}).get(key)
            if v is not None:
                v.set(val)
            else:
                ent[key] = val
            changed[0] = True

        ident = ent.get("id", "").strip()
        link = ent.get("link", "").strip()
        user = ent.get("username", "").strip()
        if src in (None, "link") and link:
            got = extract_from_link(tpl, link)
            if got.get("id") and not ident:
                put("id", got["id"])
                ident = got["id"]
            if got.get("username") and not user:
                put("username", got["username"])
                user = got["username"]
        if src in (None, "id", "username") and ident and not link:
            made = build_link(tpl, ident, user)
            if made:
                put("link", made)
        return changed[0]

    # ----- convert / scan -----
    def convert(self, api, node, plat, ent, src, dst):
        val = ent.get(src, "").strip()
        if not val:
            self.status("Fill the source field first.")
            return
        self.status("Working...")
        cfg = self.apis.get(api)

        def ok(res):
            text, parsed = res
            text = (text or "").strip()
            if not text:
                self.status("No result found.")
                messagebox.showinfo(APP_NAME, "No result found for '%s'." % val)
                return
            ent[dst] = text.split(",")[0].strip()
            self.apply_fill(plat, ent, cfg, parsed)
            self.link_id_sync(plat, ent, force=True)
            self.changed()
            self.rerender(node)
            self.status("Done.")

        self.worker.run(lambda: run_api(cfg, val, self.secrets()), ok, self.error)

    def kind_plat(self, node, kind):
        """The platform on this user that uses the given button set (created from its preset if missing)."""
        for p in node["accounts"]:
            if self.preset_of(p).get("buttons") == kind:
                return p
        preset = next((p for p in self.settings["presets"] if p.get("buttons") == kind), None)
        plat = {"platform": preset["name"] if preset else kind.title(), "entries": []}
        node["accounts"].append(plat)
        return plat

    def ids_of(self, node, kind):
        out = []
        for p in node["accounts"]:
            if self.preset_of(p).get("buttons") == kind:
                out += [e for e in p["entries"] if e.get("id", "").strip()]
        return out

    def first_id(self, node, kind):
        ents = self.ids_of(node, kind)
        for e in ents:
            if e.get("main"):
                return e["id"].strip()
        return ents[0]["id"].strip() if ents else ""

    def ensure_entry(self, node, kind, value):
        if any(e["id"].strip() == value for e in self.ids_of(node, kind)):
            return
        plat = self.kind_plat(node, kind)
        target = next((e for e in plat["entries"] if not e.get("id", "").strip()), None)
        if target is None:
            target = new_entry(self.preset_of(plat))
            plat["entries"].append(target)
        target["id"] = value
        self.link_id_sync(plat, target, force=True)

    def cross(self, node, api, src_ent, target_kind):
        val = src_ent.get("id", "").strip()
        if not val:
            self.status("Fill the ID first.")
            return
        self.status("Working...")
        cfg = self.apis.get(api)

        def ok(res):
            ids = [x.strip() for x in (res[0] or "").split(",") if x.strip()]
            if not ids:
                self.status("No result found.")
                messagebox.showinfo(APP_NAME, "No %s account found for '%s'." % (target_kind.title(), val))
                return
            for i in ids:
                self.ensure_entry(node, target_kind, i)
            self.changed()
            self.rerender(node)
            self.status("Added %d %s ID(s)." % (len(ids), target_kind.title()))

        self.worker.run(lambda: run_api(cfg, val, self.secrets()), ok, self.error)

    def add_scan_note(self, ent, kind, val, res):
        extra = ""
        if kind == "discord" and val.isdigit():
            ts = ((int(val) >> 22) + 1420070400000) / 1000
            created = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            extra = "\naccount created (from ID): " + created
        ent["notes"] = (ent.get("notes", "") + "[%s] %s scan of %s\n%s%s\n\n"
                        % (now_stamp(), kind.title(), val, res, extra))

    def scan(self, node, plat, kind, ent):
        val = ent.get("id", "").strip()
        if not val:
            self.status("Fill the ID first.")
            return
        self.status("Scanning...")
        cfg = self.apis.get("scan_" + kind)

        def ok(res):
            self.record_scan(node, plat, kind, ent, val, res)
            self.changed()
            self.rerender(node)
            self.status("Scan finished.")

        self.worker.run(lambda: run_api(cfg, val, self.secrets()), ok, self.error)

    # ----- global autofill -----
    def autofill_user(self, node):
        if self.autofill_busy:
            self.status("Autofill is already running...")
            return
        self.autofill_busy = True
        log = {"done": [], "skipped": [], "links": 0}
        gen = self.autofill_steps(node, log)

        def advance(send=None, exc=None):
            try:
                task = gen.throw(exc) if exc is not None else gen.send(send)
            except StopIteration:
                self.autofill_busy = False
                self.finish_autofill(node, log)
                return
            except Exception as e:  # noqa
                self.autofill_busy = False
                self.error(e)
                return
            self.worker.run(task, lambda r: advance(send=r), lambda e: advance(exc=e))

        self.status("Autofill running...")
        advance()

    def autofill_call(self, api, val, label, log):
        try:
            return (yield (lambda: run_api(self.apis.get(api), val, self.secrets())))
        except Exception as e:  # noqa
            msg = (str(e).splitlines() or [e.__class__.__name__])[0]
            line = "%s: %s" % (label, msg)
            if line not in log["skipped"]:
                log["skipped"].append(line)
            return None

    def fill_all_links(self, node, log):
        for p in node["accounts"]:
            for e in p["entries"]:
                if self.link_id_sync(p, e, force=True):
                    log["links"] += 1

    def autofill_steps(self, node, log):
        # 1. link <-> ID from the preset templates
        self.fill_all_links(node, log)

        # 2. usernames -> IDs (2rblxId / 2discId); also fills the display name when the answer has it
        for plat in list(node["accounts"]):
            kind = self.preset_of(plat).get("buttons", "")
            api = {"roblox": "rblx_user_to_id", "discord": "discord_user_to_id"}.get(kind)
            if not api:
                continue
            for ent in list(plat["entries"]):
                user, ident = ent.get("username", "").strip(), ent.get("id", "").strip()
                if user and not ident:
                    res = yield from self.autofill_call(api, user, "%s username -> ID" % plat["platform"], log)
                    text = ((res[0] if res else "") or "").strip()
                    if text:
                        ent["id"] = text.split(",")[0].strip()
                        self.apply_fill(plat, ent, self.apis.get(api), res[1])
                        log["done"].append("%s: found the ID for %s" % (plat["platform"], user))
        self.fill_all_links(node, log)

        # 3. across platforms (2discord / 2roblox)
        rob = self.first_id(node, "roblox")
        if rob and not self.ids_of(node, "discord"):
            res = yield from self.autofill_call("rblx_id_to_discord", rob, "Roblox -> Discord", log)
            for i in [x.strip() for x in ((res[0] if res else "") or "").split(",") if x.strip()]:
                self.ensure_entry(node, "discord", i)
                log["done"].append("Discord ID %s found from Roblox" % i)
        dis = self.first_id(node, "discord")
        if dis and not self.ids_of(node, "roblox"):
            res = yield from self.autofill_call("discord_id_to_roblox", dis, "Discord -> Roblox", log)
            for i in [x.strip() for x in ((res[0] if res else "") or "").split(",") if x.strip()]:
                self.ensure_entry(node, "roblox", i)
                log["done"].append("Roblox ID %s found from Discord" % i)
        self.fill_all_links(node, log)

        # 4. scans (fill empty username / display name / bio; skipped when that ID was already scanned)
        if self.settings.get("autofill_scans", True):
            for plat in list(node["accounts"]):
                kind = self.preset_of(plat).get("buttons", "")
                if kind not in ("roblox", "discord"):
                    continue
                for ent in list(plat["entries"]):
                    ident = ent.get("id", "").strip()
                    if not ident or ("scan of %s" % ident) in ent.get("notes", ""):
                        continue
                    res = yield from self.autofill_call("scan_" + kind, ident, "%s scan" % kind.title(), log)
                    if res is not None:
                        self.record_scan(node, plat, kind, ent, ident, res)
                        log["done"].append("%s scan of %s added to notes" % (kind.title(), ident))

    def finish_autofill(self, node, log):
        self.changed()
        self.rerender(node)
        n = len(log["done"]) + (1 if log["links"] else 0)
        msg = "Autofill finished: %d change(s)" % n if n else "Autofill: nothing new to fill"
        if log["skipped"]:
            msg += ", %d skipped" % len(log["skipped"])
        self.status(msg + ".")
        if log["skipped"]:
            lines = []
            if log["done"] or log["links"]:
                lines.append("Done:")
                if log["links"]:
                    lines.append("- filled %d link/ID value(s) from templates" % log["links"])
                lines += ["- " + d for d in log["done"]]
                lines.append("")
            lines.append("Skipped:")
            lines += ["- " + s for s in log["skipped"]]
            messagebox.showinfo("Autofill", "\n".join(lines))

    def migrate_data(self):
        """v2 stored a color per user; v3 stores a tag (named color). Convert once."""
        by_color = {t["color"].lower(): t["id"] for t in self.settings["tags"]}
        moved = []

        def walk(items):
            for n in items:
                if n["type"] == "group":
                    walk(n["children"])
                elif "color" in n:
                    hexc = (n.pop("color") or "").lower()
                    moved.append(1)
                    if hexc and "tag" not in n:
                        if hexc not in by_color:
                            t = {"id": uid(), "name": "Color " + hexc, "color": hexc}
                            self.settings["tags"].append(t)
                            by_color[hexc] = t["id"]
                        n["tag"] = by_color[hexc]
        walk(self.data["items"])
        if moved:
            self.changed()
            self.save_settings_soon()

    def secrets(self):
        return self.settings.get("keys", {})

    def reload_settings(self):
        self.settings = self.load_settings()
        self.tags_changed()
        self.status("settings.json reloaded")

    def apply_icon(self):
        cands = []
        for name in ("icon.png", "icon.ico"):
            path = os.path.join(APP_DIR, name)
            if os.path.exists(path):
                cands.append((os.path.getmtime(path), path))
        for _t, path in sorted(cands, reverse=True):
            try:
                if path.endswith(".png"):
                    self.icon_img = tk.PhotoImage(file=path)
                    self.root.iconphoto(True, self.icon_img)
                else:
                    self.root.iconbitmap(default=path)
                return True
            except tk.TclError:
                continue
        return False

    def set_icon_file(self):
        from tkinter import filedialog
        import shutil
        path = filedialog.askopenfilename(title="Choose an icon (.ico or .png)",
                                          filetypes=[("Icon / image", "*.ico *.png"), ("All files", "*.*")])
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        if ext not in (".ico", ".png"):
            messagebox.showinfo(APP_NAME, "Please choose a .ico or .png file.")
            return
        try:
            shutil.copy(path, os.path.join(APP_DIR, "icon" + ext))
        except OSError as e:
            self.error(e)
            return
        ok = self.apply_icon()
        msg = "Window icon updated." if ok else "Saved, but this icon could not be loaded. Try a square .png."
        msg += ("\n\nTo change the icon on your pinned taskbar shortcut: right-click the pinned icon, right-click "
                "ModDesk in the list, Properties > Change Icon, and choose icon.ico from the program folder. "
                "(Or rebuild with build.bat, which embeds icon.ico in the .exe.)")
        messagebox.showinfo(APP_NAME, msg)

    def install_update(self):
        from tkinter import filedialog
        import zipfile
        path = filedialog.askopenfilename(title="Choose the new moddesk.py (or a ZIP of the source)",
                                          filetypes=[("ModDesk update", "*.py *.zip"), ("All files", "*.*")])
        if not path:
            return
        try:
            if path.lower().endswith(".zip"):
                with zipfile.ZipFile(path) as z:
                    names = sorted((n for n in z.namelist() if n.replace("\\", "/").endswith("moddesk.py")), key=len)
                    if not names:
                        raise ValueError("There is no moddesk.py inside that ZIP.")
                    src = z.read(names[0]).decode("utf-8")
            else:
                with open(path, encoding="utf-8") as f:
                    src = f.read()
        except (OSError, ValueError, UnicodeDecodeError, zipfile.BadZipFile) as e:
            messagebox.showerror(APP_NAME, "That file can't be used:\n%s" % e)
            return
        if os.path.abspath(path) == APP_CODE:
            messagebox.showinfo(APP_NAME, "That is the file already running.")
            return
        self.apply_update_source(src, os.path.basename(path))

    def restart(self, extra=None):
        import subprocess
        cmd = ([sys.executable] if getattr(sys, "frozen", False) else [sys.executable, APP_CODE]) + list(extra or [])
        self.save_now()
        try:
            subprocess.Popen(cmd, cwd=APP_DIR)
        except OSError as e:
            self.error(e)
            return
        self.on_close()

    def tag_of(self, n):
        tid = n.get("tag")
        if not tid:
            return None
        return next((t for t in self.settings["tags"] if t["id"] == tid), None)

    def tag_name(self, n):
        t = self.tag_of(n)
        return t["name"] if t else "(none)"

    def tag_choices(self):
        return ["(none)"] + [t["name"] for t in self.settings["tags"]]

    def tag_picked(self, node):
        name = self.tag_var.get() if self.tag_var is not None else ""
        t = next((t for t in self.settings["tags"] if t["name"] == name), None)
        self.set_tag(node, t["id"] if t else "")

    def dot_image(self, color):
        if color not in self.dot_cache:
            self.dot_cache[color] = self.draw_dot(color) if color else tk.PhotoImage(width=14, height=14)
        return self.dot_cache[color]

    def node_label(self, n):
        if n["type"] == "group":
            return "\U0001F4C1 " + n["name"]
        text = "\U0001F464 " + n["name"]
        t = self.tag_of(n)
        if t and self.settings.get("show_tag_text", True):
            text += "   · " + t["name"]
        return text

    def node_image(self, n):
        t = self.tag_of(n)
        return self.dot_image(t["color"] if t else "")

    def refresh_item(self, n):
        if not self.tree.exists(n["id"]):
            return
        if n["type"] == "group":
            self.tree.item(n["id"], text=self.node_label(n))
        else:
            self.tree.item(n["id"], text=self.node_label(n), image=self.node_image(n))

    def resort_item(self, n):
        r = self.locate(n["id"])
        if not r or not self.tree.exists(n["id"]) or self.search_var.get().strip():
            return
        sibs = sorted(r[1], key=lambda x: (x["type"] != "group", x["name"].lower()))
        self.tree.move(n["id"], self.tree.parent(n["id"]), sibs.index(n))

    def refresh_tree_items(self):
        if self.search_var.get().strip():
            self.rebuild_tree()
            return

        def walk(items):
            for n in items:
                self.refresh_item(n)
                if n["type"] == "group":
                    walk(n["children"])
        walk(self.data["items"])

    def tags_changed(self):
        self.save_settings_soon()
        self.refresh_tree_items()
        try:
            if self.tag_combo is not None and self.tag_combo.winfo_exists() and self.cur_node is not None:
                self.tag_combo.configure(values=self.tag_choices())
                self.tag_var.set(self.tag_name(self.cur_node))
        except tk.TclError:
            pass

    def cycle_tag(self, n):
        ids = [""] + [t["id"] for t in self.settings["tags"]]
        cur = n.get("tag", "")
        if cur in ids:
            nxt = ids[(ids.index(cur) + 1) % len(ids)]
        else:
            nxt = ids[1] if len(ids) > 1 else ""
        self.set_tag(n, nxt)

    def set_tag(self, n, tid):
        if tid:
            n["tag"] = tid
        else:
            n.pop("tag", None)
        self.changed()
        self.refresh_item(n)
        if self.current == n["id"] and self.tag_var is not None:
            self.tag_var.set(self.tag_name(n))

    def set_tag_selected(self, tid):
        sid = self.selected_id()
        r = self.locate(sid) if sid else None
        if r and r[0]["type"] == "user":
            self.set_tag(r[0], tid)

    def insert_row(self, n, sel):
        """Add one row without rebuilding the whole tree (no flicker)."""
        parent = ""
        if sel and self.tree.exists(sel):
            r = self.locate(sel)
            parent = sel if (r and r[0]["type"] == "group") else self.tree.parent(sel)
        if parent:
            self.tree.item(parent, open=True)
        kw = {"iid": n["id"], "text": self.node_label(n)}
        if n["type"] == "user":
            kw["image"] = self.node_image(n)
        else:
            kw["open"] = True
        self.tree.insert(parent, "end", **kw)

    def attach_inner(self, frame):
        """Swap the editor page in one step: the new page is complete before the old one goes away."""
        old = self.inner
        self.inner = frame
        self.canvas.itemconfigure(self.win_id, window=frame)
        try:
            self.canvas.itemconfigure(self.win_id, width=self.canvas.winfo_width())
        except tk.TclError:
            pass

        def resized(e, f=frame):
            if f is self.inner:
                try:
                    keep = self.canvas.yview()[0]
                    self.canvas.configure(scrollregion=(0, 0, e.width, e.height))
                    self.canvas.yview_moveto(keep)
                except tk.TclError:
                    pass
        frame.bind("<Configure>", resized)
        if old is not None and old is not frame:
            old.destroy()

    def make_gradient(self, w, h, c1, c2):
        img = tk.PhotoImage(width=w, height=h)

        def rgb(c):
            return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        a, b = rgb(c1), rgb(c2)
        row = []
        for x in range(w):
            t = min(1.0, x / (0.65 * (w - 1)))
            row.append("#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))
        line = "{" + " ".join(row) + "}"
        img.put(" ".join([line] * h))
        return img

    def build_user_editor(self, inner, node):
        # top bar: list label, tag dropdown, autofill, find
        top = ttk.Frame(inner, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        ttk.Label(top, text="List label:").pack(side="left")
        el, vlabel = self.entry_bound(top, node, "name", 28, fkey=("label",))
        el.pack(side="left", padx=6)
        ttk.Label(top, text="Tag:").pack(side="left")
        self.tag_var = tk.StringVar(value=self.tag_name(node))
        combo = ttk.Combobox(top, textvariable=self.tag_var, values=self.tag_choices(), state="readonly", width=14)
        combo.pack(side="left", padx=(4, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: self.tag_picked(node))
        self.tag_combo = combo
        ttk.Button(top, text="Autofill", command=lambda: self.autofill_user(node)).pack(side="left", padx=2)
        ttk.Button(top, text="Find socials...", command=lambda: FindDialog(self, node)).pack(side="left", padx=2)
        ttk.Button(top, text="Check usernames...", command=lambda: self.check_usernames(node)).pack(side="left", padx=2)

        # names
        nf = ttk.LabelFrame(inner, text="Names", padding=6)
        nf.pack(fill="x", padx=8, pady=6)
        nf.columnconfigure(1, weight=1)
        ttk.Label(nf, text="Main name").grid(row=0, column=0, sticky="w")
        em, vmain = self.entry_bound(nf, node, "main_name", fkey=("main",))
        em.grid(row=0, column=1, sticky="ew", padx=4, pady=1)
        self.main_entry = em
        ucb, uen = self.conf_widgets(nf, node, src_width=14)
        ucb.grid(row=0, column=3, padx=2)
        uen.grid(row=0, column=4)
        ttk.Label(nf, foreground="#666", text="confidence / found via").grid(row=3, column=3, columnspan=2, sticky="w")
        ttk.Label(nf, text="Real name").grid(row=1, column=0, sticky="w")
        er, _v = self.entry_bound(nf, node, "real_name", fkey=("real",))
        er.grid(row=1, column=1, sticky="ew", padx=4, pady=1)
        ttk.Label(nf, text="Number(s)").grid(row=2, column=0, sticky="w")
        en, _v = self.entry_bound(nf, node, "numbers", fkey=("numbers",))
        en.grid(row=2, column=1, sticky="ew", padx=4, pady=1)
        self.numbers_entry = en
        ttk.Label(nf, foreground="#666",
                  text="Numbers people tie to their name (7896), comma separated - used to build name variants "
                       "in Find socials.").grid(row=3, column=1, sticky="w", padx=4)
        for i, aka in enumerate(node["akas"]):
            ttk.Label(nf, text="AKA").grid(row=i + 4, column=0, sticky="w")
            e, _v = self.entry_bound(nf, aka, "name", fkey=("aka", id(aka)))
            e.grid(row=i + 4, column=1, sticky="ew", padx=4, pady=1)
            self.aka_entries.append(e)
            ttk.Button(nf, text="✕", width=3,
                       command=lambda a=aka: self.remove_from(node["akas"], a, node)).grid(row=i + 4, column=2)

        ttk.Button(nf, text="+ AKA", command=lambda: self.add_aka(node)
                   ).grid(row=len(node["akas"]) + 4, column=1, sticky="w", pady=3)

        # the list label feeds the main name until you edit the main name yourself
        last = [node["name"]]

        def on_label(*_):
            new = node["name"]
            self.refresh_item(node)
            if vmain.get().strip() in ("", last[0]):
                vmain.set(new)
            last[0] = new
        vlabel.trace_add("write", on_label)

        # accounts
        af = ttk.LabelFrame(inner, text="Accounts", padding=6)
        af.pack(fill="x", padx=8, pady=6)
        hb = ttk.Frame(af)
        hb.pack(fill="x")
        ttk.Button(hb, text="+ Add platform", command=lambda: self.add_platform(node)).pack(side="left")
        ttk.Button(hb, text="Collapse all", command=lambda: self.collapse_all(node, True)).pack(side="left", padx=4)
        ttk.Button(hb, text="Expand all", command=lambda: self.collapse_all(node, False)).pack(side="left")
        ttk.Label(af, foreground="#666",
                  text="Right-click (or double-click) a platform or field title to rename it.").pack(
            anchor="w", pady=(2, 0))
        for plat in node["accounts"]:
            self.render_platform(af, node, plat)

        self.build_links(inner, node)

        # notes
        nof = ttk.LabelFrame(inner, text="Notes", padding=6)
        nof.pack(fill="x", padx=8, pady=6)
        self.text_bound(nof, node, "notes", 8).pack(fill="x")

    def entry_header(self, parent, node, plat, ent, main, collapsed):
        """Header row of one account: [-]/[+] like a tree, star, summary, Delete. Starred = gold gradient."""
        h = 30
        end_bg = "#fff8dc"
        c = tk.Canvas(parent, height=h, bg=end_bg if main else self.head_bg, highlightthickness=0, bd=0)
        if main:
            if self.gradient_img is None:
                self.gradient_img = self.make_gradient(760, h, "#ffd34d", end_bg)
            c.create_image(0, 0, image=self.gradient_img, anchor="nw")
        x0, y0 = 10, (h - 11) // 2
        c.create_rectangle(x0, y0, x0 + 10, y0 + 10, outline="#919191", fill="white", tags=("tog",))
        c.create_line(x0 + 2, y0 + 5, x0 + 9, y0 + 5, fill="#222222", tags=("tog",))
        if collapsed:
            c.create_line(x0 + 5, y0 + 2, x0 + 5, y0 + 9, fill="#222222", tags=("tog",))
        c.create_text(38, h // 2, text="★" if main else "☆", font=("Segoe UI Symbol", 14),
                      fill="#c98f00" if main else "#8a8a8a", tags=("star",))
        sid = c.create_text(60, h // 2, anchor="w", text=self.entry_summary(ent),
                            font=("Segoe UI", 10, "bold" if main else "normal"), fill="#222222", tags=("sum",))
        btn = ttk.Button(c, text="Delete", command=lambda: self.delete_entry(node, plat, ent))
        win = c.create_window(0, h // 2, window=btn, anchor="e")
        c.bind("<Configure>", lambda e: c.coords(win, e.width - 6, h // 2))

        def bind(tag, cmd):
            c.tag_bind(tag, "<Button-1>", lambda e: cmd())
            c.tag_bind(tag, "<Enter>", lambda e: c.configure(cursor="hand2"))
            c.tag_bind(tag, "<Leave>", lambda e: c.configure(cursor=""))
        bind("tog", lambda: self.toggle_collapse(node, ent))
        bind("sum", lambda: self.toggle_collapse(node, ent))
        bind("star", lambda: self.toggle_main(node, plat, ent))
        return c, (lambda text: c.itemconfigure(sid, text=text))

    def apply_fill(self, plat, ent, cfg, parsed):
        """Fill empty fields of an account from an API answer (cfg['fill']). Returns notes about differences."""
        notes = []
        if not isinstance(cfg, dict) or parsed is None:
            return notes
        preset = self.preset_of(plat)
        for target, path in (cfg.get("fill") or {}).items():
            val = " ".join(fmt(dig(parsed, path)).split())
            if not val:
                continue
            if target in ("username", "display", "id", "link"):
                cur = ent.get(target, "").strip()
                if not cur or (cur.lower() == val.lower() and cur != val):
                    ent[target] = val
                elif cur != val:
                    notes.append("%s differs: saved '%s', now '%s'" % (target, cur, val))
            else:
                x = next((x for x in ent.get("extra", []) if x.get("key", "").strip().lower() == target.lower()), None)
                if x is None and any(f.strip().lower() == target.lower() for f in preset.get("fields", [])):
                    x = {"key": target, "value": ""}
                    ent.setdefault("extra", []).append(x)
                if x is not None and not x.get("value", "").strip():
                    x["value"] = val
        return notes

    def record_scan(self, node, plat, kind, ent, val, res):
        """Put a scan answer into the account: fill empty fields, and keep the full output as a note."""
        text, parsed = res
        if not text and parsed is None:
            self.add_scan_note(ent, kind, val, "(nothing found)")
            return
        diffs = self.apply_fill(plat, ent, self.apis.get("scan_" + kind), parsed)
        self.add_scan_note(ent, kind, val, text + ("\n" + "\n".join(diffs) if diffs else ""))

    def check_usernames(self, node, names=None):
        if names is None:
            names = [n for n in [node.get("main_name", ""), node.get("name", "")] + [a.get("name", "") for a in node.get("akas", [])]
                     if n]
            for plat in node.get("accounts", []):
                names += [e.get("username", "") for e in plat.get("entries", []) if e.get("username")]
        seen = []
        for n in names:
            n = re.sub(r"\s+", "", n.strip())
            if n and n.lower() not in [x.lower() for x in seen]:
                seen.append(n)
        UsernameCheckDialog(self, node, seen)

    def keybinds(self):
        b = dict(DEFAULT_KEYBINDS)
        for k, v in self.app_cfg.get("keybinds", {}).items():
            if k in b and isinstance(v, str) and v.startswith("<"):
                b[k] = v
        return b

    def set_keybind(self, action, seq):
        self.app_cfg.setdefault("keybinds", {})[action] = seq
        save_app_cfg(self.app_cfg)
        self.apply_keybinds()

    def apply_keybinds(self):
        for seq in getattr(self, "bound_keys", []):
            try:
                self.root.unbind(seq)
            except tk.TclError:
                pass
        handlers = {"save": self.save_now, "new_user": self.add_user, "new_group": self.add_group,
                    "find_user": self.focus_search, "autofill": self.key_autofill,
                    "find_socials": self.key_find, "settings": self.open_settings}
        self.bound_keys = []
        for action, seq in self.keybinds().items():
            fn = handlers.get(action)
            if not fn:
                continue
            try:
                self.root.bind(seq, lambda e, fn=fn: (fn(), "break")[1])
                self.bound_keys.append(seq)
            except tk.TclError:
                self.status("Shortcut %s is not valid; reset it in Settings > Keybinds." % seq)

    def focus_search(self):
        try:
            self.search_entry.focus_set()
            self.search_entry.selection_range(0, "end")
        except (AttributeError, tk.TclError):
            pass

    def key_autofill(self):
        if isinstance(self.cur_node, dict) and self.cur_node.get("type") == "user":
            self.autofill_user(self.cur_node)

    def key_find(self):
        if isinstance(self.cur_node, dict) and self.cur_node.get("type") == "user":
            FindDialog(self, self.cur_node)

    def open_settings(self, tab=0):
        win = getattr(self, "settings_win", None)
        try:
            if win is not None and win.winfo_exists():
                win.lift()
                win.focus_force()
                return
        except tk.TclError:
            pass
        self.settings_win = SettingsWindow(self, tab)

    def open_terms(self):
        self.open_settings(5)

    def open_tour(self):
        TourDialog(self.root)

    def maybe_tour(self):
        if self.app_cfg.get("tour_pending"):
            self.app_cfg["tour_pending"] = False
            save_app_cfg(self.app_cfg)
            TourDialog(self.root)

    def switch_profile(self):
        """Save, then start ModDesk again showing the profile picker."""
        self.restart(["--pick"])

    def apply_update_source(self, src, label):
        import shutil
        try:
            compile(src, label, "exec")
        except (SyntaxError, ValueError) as e:
            messagebox.showerror(APP_NAME, "That code can't be used:\n%s" % e)
            return
        if "class App" not in src or "def main" not in src or "APP_NAME" not in src:
            messagebox.showerror(APP_NAME, "That does not look like a ModDesk moddesk.py.")
            return
        new_v = src_version(src)
        note = ""
        if new_v and ver_tuple(new_v) < ver_tuple(APP_VERSION):
            note = "\n\nNote: this is OLDER than the version you have (%s)." % APP_VERSION
        if not messagebox.askyesno(APP_NAME, "Install ModDesk %s from %s?\nYour profiles, keys and settings are not "
                                             "touched, and the current version is saved in the backups "
                                             "folder.%s" % (new_v or "(unknown version)", label, note)):
            return
        try:
            bdir = os.path.join(os.path.dirname(APP_CODE), "backups")
            os.makedirs(bdir, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.copy(APP_CODE, os.path.join(bdir, "moddesk-%s.py" % stamp))
            olds = sorted(f for f in os.listdir(bdir) if f.startswith("moddesk-") and f.endswith(".py"))
            for f in olds[:-10]:
                os.remove(os.path.join(bdir, f))
            tmp = APP_CODE + ".new"
            with open(tmp, "w", encoding="utf-8", newline="") as f:
                f.write(src)
            os.replace(tmp, APP_CODE)
        except OSError as e:
            self.error(e)
            return
        if messagebox.askyesno(APP_NAME, "Updated. Restart ModDesk now?"):
            self.restart()

    def auto_check(self):
        """Quiet startup check: only mentions a newer version in the status bar, never installs by itself."""
        repo = (self.app_cfg.get("update_repo") or "").strip()
        if not repo or not self.app_cfg.get("auto_update_check", True) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            return
        url = "https://raw.githubusercontent.com/%s/%s/moddesk.py" % (
            repo, urllib.parse.quote(self.app_cfg.get("update_branch") or "main"))

        def ok(src):
            v = src_version(src)
            if v and ver_tuple(v) > ver_tuple(APP_VERSION):
                self.status("ModDesk %s is available - Settings > Updates" % v)
        self.worker.run(lambda: fetch_bytes(url, timeout=8, limit=8000000).decode("utf-8"), ok, lambda e: None)

    def check_github_update(self, repo, branch, msg_var):
        repo = (repo or "").strip().strip("/")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            msg_var.set("Enter the repo as owner/name, for example  someone/moddesk")
            return
        url = "https://raw.githubusercontent.com/%s/%s/moddesk.py" % (repo, urllib.parse.quote(branch or "main"))
        msg_var.set("Checking...")

        def work():
            return fetch_bytes(url, limit=8000000).decode("utf-8")

        def ok(src):
            new_v = src_version(src)
            if new_v and ver_tuple(new_v) <= ver_tuple(APP_VERSION):
                msg_var.set("You are up to date (installed %s, repo has %s)." % (APP_VERSION, new_v))
                return
            msg_var.set("Version %s is available." % (new_v or "(unknown)"))
            self.apply_update_source(src, "%s (%s)" % (repo, branch))

        def err(e):
            msg_var.set("Could not check: %s (is the repo public and does it contain moddesk.py?)" % e)
        self.worker.run(work, ok, err)

    def conf_widgets(self, parent, obj, on_change=None, src_width=18, tone=""):
        """Confidence level + 'found via' note for any record (user, account, AKA)."""
        c = obj.get("conf")
        if not isinstance(c, dict):
            c = obj["conf"] = {"level": "", "source": ""}
        lvl = tk.StringVar(value=c.get("level") or CONF_NONE)
        cb = ttk.Combobox(parent, textvariable=lvl, values=[CONF_NONE] + CONF_LEVELS[1:], state="readonly", width=10)

        def picked(_e=None):
            c["level"] = "" if lvl.get() == CONF_NONE else lvl.get()
            self.changed()
            if on_change:
                on_change()
        cb.bind("<<ComboboxSelected>>", picked)
        src = tk.StringVar(value=c.get("source", ""))

        def typed(*_a):
            c["source"] = src.get()
            self.changed()
        src.trace_add("write", typed)
        en = ttk.Entry(parent, textvariable=src, width=src_width)
        return cb, en

    def user_label(self, n):
        return n.get("name") or n.get("main_name") or "(unnamed)"

    def build_links(self, inner, node):
        """Linked people: pick another user and say how they are connected; the other side shows it too."""
        links = node.setdefault("links", [])
        lf = ttk.LabelFrame(inner, text="Linked people", padding=6)
        lf.pack(fill="x", padx=8, pady=6)
        others = [n for n in walk_nodes(self.data["items"]) if n.get("type") == "user" and n["id"] != node["id"]]
        labels, seen = {}, {}
        for n in others:
            base = self.user_label(n)
            seen[base] = seen.get(base, 0) + 1
            labels[n["id"]] = base if seen[base] == 1 else "%s (%d)" % (base, seen[base])
        choices = [labels[n["id"]] for n in others]
        by_label = {v: k for k, v in labels.items()}
        for lk in links:
            row = ttk.Frame(lf)
            row.pack(fill="x", pady=1)
            var = tk.StringVar(value=labels.get(lk.get("to"), ""))
            cb = ttk.Combobox(row, textvariable=var, values=choices, state="readonly", width=26)
            cb.pack(side="left")

            def picked(_e=None, lk=lk, var=var):
                lk["to"] = by_label.get(var.get(), "")
                self.changed()
            cb.bind("<<ComboboxSelected>>", picked)
            ttk.Label(row, text="how:").pack(side="left", padx=(8, 2))
            e, _v = self.entry_bound(row, lk, "rel", fkey=("rel", id(lk)))
            e.configure(width=24)
            e.pack(side="left")
            ttk.Button(row, text="Open", width=6, command=lambda lk=lk: self.open_person(lk.get("to"))).pack(
                side="left", padx=4)
            ttk.Button(row, text="✕", width=3, command=lambda lk=lk: self.remove_from(links, lk, node)).pack(
                side="left")
        back = []
        for n in others:
            for lk in n.get("links", []):
                if lk.get("to") == node["id"]:
                    back.append("%s%s" % (labels[n["id"]], " (%s)" % lk["rel"] if lk.get("rel") else ""))
        if back:
            ttk.Label(lf, foreground="#555", wraplength=640, justify="left",
                      text="Also linked from: " + ", ".join(back)).pack(anchor="w", pady=(4, 0))
        ttk.Button(lf, text="+ Link a person", command=lambda: self.append_to(
            links, {"to": "", "rel": ""}, node)).pack(anchor="w", pady=(4, 0))

    def open_person(self, pid):
        if pid and self.locate(pid):
            self.rebuild_tree(select=pid)
            self.root.after(50, lambda: self.on_select(None))

    def generic_scan(self, node, plat, ent, preset):
        api = preset.get("scan")
        cfg = self.apis.get(api)
        src = preset.get("scan_src", "id")
        val = (ent.get(src) or ent.get("id") or ent.get("username") or "").strip()
        if not val:
            self.status("Fill the username or ID first.")
            return
        self.status("Scanning...")

        def ok(res):
            text, parsed = res
            self.apply_fill(plat, ent, cfg, parsed)
            self.add_scan_note(ent, preset.get("name", "scan").lower(), val, text or "(nothing found)")
            self.link_id_sync(plat, ent, force=True)
            self.changed()
            self.rerender(node)
            self.status("Scan finished.")
        self.worker.run(lambda: run_api(cfg, val, self.secrets()), ok, self.error)

    def open_external(self, urls):
        """Open links in the browser chosen in Settings (and its profile), else the system default."""
        import subprocess
        urls = [u for u in urls if u]
        if not urls:
            return
        cmd = browser_command(self.app_cfg.get("browser"), urls)
        if cmd:
            try:
                subprocess.Popen(cmd, cwd=APP_DIR)
                return
            except OSError as e:
                self.status("Could not start that browser (%s); using the default one." % e)
        elif (self.app_cfg.get("browser") or {}).get("kind", "default") != "default":
            self.status("That browser was not found (Settings > General > Browser); using the default one.")
        import webbrowser
        for i, u in enumerate(urls):
            self.root.after(i * 300, lambda u=u: webbrowser.open_new_tab(u))


class TagsDialog(tk.Toplevel):
    """Settings > Tags: named colors you can put on users (dropdown in the editor, dot in the list)."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.tags = app.settings["tags"]
        self.cur = None
        self.loading = False
        self.title("Tags (color + text)")
        self.geometry("600x400")

        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        self.lb = tk.Listbox(left, width=24, exportselection=False, activestyle="none")
        self.lb.pack(fill="y", expand=True)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.on_pick())
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="+ New", command=self.new).pack(side="left")
        ttk.Button(bar, text="Delete", command=self.delete).pack(side="left", padx=4)
        ttk.Button(bar, text="▲", width=3, command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(bar, text="▼", width=3, command=lambda: self.move(1)).pack(side="left", padx=2)

        right = ttk.Frame(self, padding=8)
        right.pack(side="left", fill="both", expand=True)
        right.columnconfigure(1, weight=1)
        self.name_var = tk.StringVar()
        self.color_var = tk.StringVar()
        ttk.Label(right, text="Text").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(right, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Label(right, text="Color").grid(row=1, column=0, sticky="w")
        crow = ttk.Frame(right)
        crow.grid(row=1, column=1, sticky="w", pady=2)
        self.swatch = tk.Label(crow, width=4, relief="sunken", bg="#8b8d98")
        self.swatch.pack(side="left")
        ttk.Entry(crow, textvariable=self.color_var, width=10).pack(side="left", padx=4)
        ttk.Button(crow, text="Pick...", command=self.pick).pack(side="left")
        pal = ttk.Frame(right)
        pal.grid(row=2, column=1, sticky="w", pady=4)
        for _name, hexc in PALETTE:
            b = tk.Label(pal, width=3, bg=hexc, relief="raised", cursor="hand2")
            b.pack(side="left", padx=2)
            b.bind("<Button-1>", lambda e, h=hexc: self.color_var.set(h))
        ttk.Label(right, foreground="#666", justify="left", wraplength=340,
                  text="A tag is a colored dot + a short text. Pick it in the dropdown at the top of a user, or click "
                       "the dot in the list to cycle through them. Deleting a tag just clears it from the users "
                       "that had it.").grid(row=3, column=1, sticky="w", pady=10)
        self.name_var.trace_add("write", self.commit)
        self.color_var.trace_add("write", self.commit)
        self.refill()
        if self.tags:
            self.select(0)

    def refill(self):
        self.lb.delete(0, "end")
        for t in self.tags:
            self.lb.insert("end", "●  " + t["name"])
            self.lb.itemconfig("end", foreground=t["color"])

    def select(self, i):
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(i)
        self.on_pick()

    def on_pick(self):
        cur = self.lb.curselection()
        if not cur:
            return
        t = self.tags[cur[0]]
        self.loading = True
        self.cur = t
        self.name_var.set(t["name"])
        self.color_var.set(t["color"])
        self.loading = False
        self.swatch.configure(bg=t["color"])

    def commit(self, *_):
        if self.loading or self.cur is None:
            return
        t = self.cur
        t["name"] = self.name_var.get().strip() or "Unnamed"
        c = self.color_var.get().strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", c):
            t["color"] = c
            self.swatch.configure(bg=c)
        idx = self.tags.index(t)
        self.lb.delete(idx)
        self.lb.insert(idx, "●  " + t["name"])
        self.lb.itemconfig(idx, foreground=t["color"])
        self.lb.selection_set(idx)
        self.app.tags_changed()

    def pick(self):
        from tkinter import colorchooser
        rgb, hexc = colorchooser.askcolor(color=self.color_var.get() or "#8b8d98", parent=self)
        if hexc:
            self.color_var.set(hexc)

    def new(self):
        self.tags.append({"id": uid(), "name": "New tag", "color": "#8b8d98"})
        self.refill()
        self.select(len(self.tags) - 1)
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")
        self.app.tags_changed()

    def delete(self):
        cur = self.lb.curselection()
        if not cur:
            return
        t = self.tags[cur[0]]
        if not self.app.confirm("Delete the tag '%s'?\nUsers that had it just lose the tag." % t["name"]):
            return
        self.tags.remove(t)
        self.cur = None
        self.refill()
        if self.tags:
            self.select(0)
        self.app.tags_changed()

    def move(self, delta):
        cur = self.lb.curselection()
        if not cur:
            return
        i, j = cur[0], cur[0] + delta
        if 0 <= j < len(self.tags):
            self.tags[i], self.tags[j] = self.tags[j], self.tags[i]
            self.refill()
            self.select(j)
            self.app.tags_changed()


class KeysDialog(tk.Toplevel):
    """Settings > API keys: Discord bot token, and Bloxlink server ID + key pairs (tried in order)."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.keys = app.settings["keys"]
        self.rows = []  # (frame, guild_var, key_var, key_entry)
        self.title("API keys")
        self.geometry("640x650")
        self.minsize(580, 600)
        pad = ttk.Frame(self, padding=10)
        pad.pack(fill="both", expand=True)
        pad.columnconfigure(0, weight=1)

        ttk.Label(pad, text="Discord bot token (for Discord scans)", font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, sticky="w")
        row = ttk.Frame(pad)
        row.grid(row=1, column=0, sticky="ew", pady=2)
        row.columnconfigure(0, weight=1)
        self.tok_var = tk.StringVar(value=self.keys.get("discord_token", ""))
        self.tok_entry = ttk.Entry(row, textvariable=self.tok_var, show="•")
        self.tok_entry.grid(row=0, column=0, sticky="ew")
        self.show_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Show", variable=self.show_var, command=self.toggle_show).grid(
            row=0, column=1, padx=6)
        ttk.Button(row, text="Test", command=self.test_discord).grid(row=0, column=2)
        ttk.Label(pad, foreground="#666", wraplength=580, justify="left",
                  text="Create a bot at discord.com/developers and copy its token here. The bot does not need to "
                       "be in any server to look up users by ID.").grid(row=2, column=0, sticky="w", pady=(0, 10))

        ttk.Label(pad, text="Bloxlink - one key per server", font=("Segoe UI", 10, "bold")).grid(
            row=3, column=0, sticky="w")
        ttk.Label(pad, foreground="#666", wraplength=580, justify="left",
                  text="A Bloxlink key is made for one server, so put each server ID next to its key. Add several "
                       "pairs and they are tried in order: if one is rejected or hits its daily limit (about 2000 "
                       "requests per key per day), the next one is used automatically.").grid(
            row=4, column=0, sticky="w", pady=(0, 4))
        head = ttk.Frame(pad)
        head.grid(row=5, column=0, sticky="ew")
        ttk.Label(head, text="Server (guild) ID", width=26).pack(side="left")
        ttk.Label(head, text="Authorization key").pack(side="left")
        self.rows_frame = ttk.Frame(pad)
        self.rows_frame.grid(row=6, column=0, sticky="nsew")
        self.rows_frame.columnconfigure(1, weight=1)
        pad.rowconfigure(6, weight=1)
        bar = ttk.Frame(pad)
        bar.grid(row=7, column=0, sticky="w", pady=6)
        ttk.Button(bar, text="+ Add server key", command=lambda: self.add_row("", "", True)).pack(side="left")
        ttk.Button(bar, text="Test Bloxlink keys", command=self.test_bloxlink).pack(side="left", padx=6)
        self.res_var = tk.StringVar(value="")
        ttk.Label(pad, textvariable=self.res_var, wraplength=580, justify="left").grid(
            row=8, column=0, sticky="w", pady=4)
        ttk.Label(pad, text="Steam Web API key (optional, for the Steam preset)", font=("Segoe UI", 10, "bold")).grid(
            row=9, column=0, sticky="w", pady=(6, 0))
        self.steam_var = tk.StringVar(value=self.keys.get("steam_key", ""))
        ttk.Entry(pad, textvariable=self.steam_var, show="•").grid(row=10, column=0, sticky="ew", pady=2)
        ttk.Label(pad, foreground="#a15c00", wraplength=580, justify="left",
                  text="Keys are saved as plain text in app.json next to the program. Do not share that file."
                  ).grid(row=11, column=0, sticky="w", pady=(6, 0))

        for it in self.keys.get("bloxlink", []):
            self.add_row(str(it.get("guild", "")), str(it.get("key", "")), False)
        if not self.rows:
            self.add_row("", "", False)
        self.tok_var.trace_add("write", self.commit)
        self.steam_var.trace_add("write", self.commit)

    def toggle_show(self):
        mask = "" if self.show_var.get() else "•"
        self.tok_entry.configure(show=mask)
        for _f, _g, _k, ent in self.rows:
            ent.configure(show=mask)

    def add_row(self, guild, key, focus):
        r = len(self.rows)
        gvar, kvar = tk.StringVar(value=guild), tk.StringVar(value=key)
        ge = ttk.Entry(self.rows_frame, textvariable=gvar, width=26)
        ke = ttk.Entry(self.rows_frame, textvariable=kvar, show="" if self.show_var.get() else "•")
        xb = ttk.Button(self.rows_frame, text="✕", width=3)
        entry = (ge, gvar, kvar, ke, xb)
        ge.grid(row=r, column=0, padx=(0, 6), pady=2)
        ke.grid(row=r, column=1, sticky="ew", pady=2)
        xb.grid(row=r, column=2, padx=4)
        xb.configure(command=lambda e=entry: self.remove_row(e))
        self.rows.append((ge, gvar, kvar, ke))
        gvar.trace_add("write", self.commit)
        kvar.trace_add("write", self.commit)
        if focus:
            ge.focus_set()

    def remove_row(self, entry):
        ge, gvar, kvar, ke, xb = entry
        self.rows = [r for r in self.rows if r[0] is not ge]
        for w in (ge, ke, xb):
            w.destroy()
        self.commit()

    def pairs(self):
        return [{"guild": g.get().strip(), "key": k.get().strip()} for _e, g, k, _ke in self.rows
                if g.get().strip() or k.get().strip()]

    def commit(self, *_):
        self.keys["discord_token"] = self.tok_var.get().strip()
        self.keys["steam_key"] = self.steam_var.get().strip()
        self.keys["bloxlink"] = self.pairs()
        self.keys.pop("bloxlink_guild", None)
        self.keys.pop("bloxlink_keys", None)
        self.app.save_settings_soon()

    def test_discord(self):
        tok = self.tok_var.get().strip()
        if not tok:
            self.res_var.set("Enter the Discord token first.")
            return
        self.res_var.set("Testing Discord...")

        def work():
            status, reason, h, text = do_request("GET", "https://discord.com/api/v10/users/@me",
                                                 {"Authorization": "Bot " + tok})
            return status, text

        def ok(r):
            status, text = r
            if status == 200:
                try:
                    name = json.loads(text).get("username", "?")
                except ValueError:
                    name = "?"
                self.res_var.set("Discord OK - bot '%s'." % name)
            else:
                self.res_var.set("Discord answered HTTP %s - is the token right?" % status)
        self.app.worker.run(work, ok, lambda e: self.res_var.set("Discord test failed: %s" % e))

    def test_bloxlink(self):
        pairs = [p for p in self.pairs() if p["guild"] and p["key"]]
        if not pairs:
            self.res_var.set("Fill in at least one server ID + key first.")
            return
        self.res_var.set("Testing %d key(s)..." % len(pairs))

        def work():
            out = []
            for i, p in enumerate(pairs, 1):
                url = "https://api.blox.link/v4/public/guilds/%s/roblox-to-discord/1" % urllib.parse.quote(
                    p["guild"], safe="")
                label = "server %s" % p["guild"]
                try:
                    status = do_request("GET", url, {"Authorization": p["key"]})[0]
                except (OSError, ValueError) as e:
                    out.append("%s: network error (%s)" % (label, e))
                    continue
                if status in (200, 404):
                    out.append("%s: OK" % label)
                elif status in (401, 403):
                    out.append("%s: rejected (HTTP %s) - wrong key or wrong server ID?" % (label, status))
                elif status == 429:
                    out.append("%s: rate limited (HTTP 429)" % label)
                else:
                    out.append("%s: HTTP %s" % (label, status))
            return "\n".join(out)
        self.app.worker.run(work, lambda t: self.res_var.set(t), lambda e: self.res_var.set("Test failed: %s" % e))


class FindDialog(tk.Toplevel):
    """Find socials: builds spellings of a person's name (separators, numbers, repeated letters) and opens
    web searches / profile URLs for the ones you pick, in your browser. Nothing is collected automatically."""

    def __init__(self, app, node):
        super().__init__(app.root)
        self.app = app
        self.node = node
        self.extra = []
        self.variants = []
        self.templates = [t for t in app.settings.get("search_templates", []) if t.get("url")]
        self.title("Find socials - %s" % node["name"])
        self.geometry("920x640")

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        self.names_lbl = ttk.Label(top, text="", wraplength=880, justify="left")
        self.names_lbl.pack(anchor="w")
        opts = ttk.Frame(top)
        opts.pack(anchor="w")
        self.leet_var = tk.BooleanVar(value=False)
        self.suf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Leetspeak (w3b, we3)", variable=self.leet_var, command=self.regen).pack(side="left")
        ttk.Checkbutton(opts, text="Platform tags (web_roblox, webdc, webyt...)", variable=self.suf_var,
                        command=self.regen).pack(side="left", padx=10)

        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill="both", expand=True)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(1, weight=1)
        ttk.Label(mid, text="1. Name variants - select the ones to search").grid(row=0, column=0, sticky="w")
        ttk.Label(mid, text="2. Where to search - select sites").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.vlb = self.make_list(mid, 0, 0)
        self.slb = self.make_list(mid, 1, 8)
        for t in self.templates:
            self.slb.insert("end", "%s  -  %s" % (t.get("group", ""), t.get("name", "")))
        for i in range(min(3, len(self.templates))):
            self.slb.selection_set(i)

        vc = ttk.Frame(mid)
        vc.grid(row=2, column=0, sticky="ew", pady=4)
        self.custom_var = tk.StringVar()
        ce = ttk.Entry(vc, textvariable=self.custom_var, width=18)
        ce.pack(side="left")
        ce.bind("<Return>", lambda e: self.add_custom())
        ttk.Button(vc, text="Add", command=self.add_custom).pack(side="left", padx=2)
        ttk.Label(vc, text="Repeat last letter up to").pack(side="left", padx=(8, 2))
        self.rep_var = tk.IntVar(value=2)
        ttk.Spinbox(vc, from_=0, to=4, width=3, textvariable=self.rep_var, command=self.regen).pack(side="left")
        ttk.Button(vc, text="All", width=4, command=lambda: self.vlb.selection_set(0, "end")).pack(side="left", padx=(8, 2))
        ttk.Button(vc, text="None", width=5, command=lambda: self.vlb.selection_clear(0, "end")).pack(side="left")

        sc = ttk.Frame(mid)
        sc.grid(row=2, column=1, sticky="ew", pady=4, padx=(8, 0))
        ttk.Button(sc, text="All", width=4, command=lambda: self.slb.selection_set(0, "end")).pack(side="left")
        ttk.Button(sc, text="None", width=5, command=lambda: self.slb.selection_clear(0, "end")).pack(side="left", padx=2)
        ttk.Button(sc, text="Edit sites...", command=lambda: app.open_path(SETTINGS_FILE)).pack(side="left", padx=8)
        ttk.Label(sc, foreground="#666", text="(then Settings > Reload settings.json)").pack(side="left")

        bot = ttk.Frame(self, padding=8)
        bot.pack(fill="x")
        self.count_lbl = ttk.Label(bot, text="")
        self.count_lbl.pack(side="left")
        ttk.Button(bot, text="Close", command=self.destroy).pack(side="right")
        ob = ttk.Button(bot, text="Open searches", command=self.open_searches)
        ob.pack(side="right", padx=6)
        ttk.Button(bot, text="Copy selected variants", command=self.copy_variants).pack(side="right")
        ttk.Label(self, foreground="#666", padding=(8, 0, 8, 8), wraplength=880,
                  text="Searches open in your browser (Settings > General > Browser); nothing is sent anywhere else. Same name or avatar on two "
                       "accounts is a lead, not proof - confirm before acting on it.").pack(anchor="w")
        self.vlb.bind("<<ListboxSelect>>", lambda e: self.update_count())
        self.slb.bind("<<ListboxSelect>>", lambda e: self.update_count())
        self.regen()

    def make_list(self, parent, col, padx):
        fr = ttk.Frame(parent)
        fr.grid(row=1, column=col, sticky="nsew", padx=(padx, 0))
        lb = tk.Listbox(fr, selectmode="extended", exportselection=False, activestyle="none")
        sb = ttk.Scrollbar(fr, command=lb.yview)
        lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        lb.pack(side="left", fill="both", expand=True)
        return lb

    def gather(self):
        n = self.node
        names, seen = [], set()

        def add(v):
            v = (v or "").strip()
            if v and v.lower() not in seen:
                seen.add(v.lower())
                names.append(v)
        add(n.get("main_name"))
        add(n.get("name"))
        for a in n.get("akas", []):
            add(a.get("name"))
        for p in n.get("accounts", []):
            for e in p.get("entries", []):
                add(e.get("username"))
                add(e.get("display"))
        numbers = [x for x in re.split(r"[,;\s]+", n.get("numbers", "")) if x]
        return names, numbers

    def regen(self):
        names, numbers = self.gather()
        self.names_lbl.configure(text="Names used: %s     Numbers: %s" % (
            ", ".join(names) or "(none yet)", ", ".join(numbers) or "(none)"))
        try:
            rep = int(self.rep_var.get())
        except (ValueError, tk.TclError):
            rep = 2
        self.variants = name_variants(names + self.extra, numbers, repeat_last=rep)
        have = {v.lower() for v in self.variants}
        for v in extra_variants(names + self.extra, self.leet_var.get(), self.suf_var.get()):
            if v.lower() not in have:
                self.variants.append(v)
        self.vlb.delete(0, "end")
        for v in self.variants:
            self.vlb.insert("end", v)
        for i in range(min(OR_CHUNK, len(self.variants))):
            self.vlb.selection_set(i)
        self.update_count()

    def add_custom(self):
        v = self.custom_var.get().strip()
        if v:
            self.extra.append(v)
            self.custom_var.set("")
            self.regen()

    def chosen(self):
        vs = [self.variants[i] for i in self.vlb.curselection()]
        ts = [self.templates[i] for i in self.slb.curselection()]
        return vs, ts

    def urls(self):
        vs, ts = self.chosen()
        return plan_searches(vs, ts)

    def update_count(self):
        vs, ts = self.chosen()
        n = len(self.urls())
        self.count_lbl.configure(
            text="%d variant(s) x %d site(s) = %d window(s) (max %d; web searches combine up to %d variants each)" % (
                len(vs), len(ts), n, MAX_WINDOWS, OR_CHUNK))

    def copy_variants(self):
        vs, _ts = self.chosen()
        self.clipboard_clear()
        self.clipboard_append("\n".join(vs))
        self.app.status("Copied %d variant(s)." % len(vs))

    def open_searches(self):
        urls = self.urls()
        if not urls:
            self.app.status("Nothing selected.")
            return
        if len(urls) > MAX_WINDOWS:
            messagebox.showinfo(APP_NAME, "That would open %d windows. Pick fewer variants or sites (limit %d).\n\n"
                                "Tip: the Web search sites combine several variants into one search, so use those "
                                "for many names; use Profile guess sites only for your best 2-3 variants." % (
                                    len(urls), MAX_WINDOWS), parent=self)
            return
        self.app.open_external(urls)


class AvatarDialog(tk.Toplevel):
    """Shows an account's avatar and opens reverse image searches (people often reuse avatars across sites)."""

    def __init__(self, app, node, plat, ent, kind):
        super().__init__(app.root)
        self.app = app
        self.node = node
        self.ent = ent
        self.kind = kind
        self.url = ""
        self.photo = None
        self.title("Avatar - %s" % (ent.get("username") or ent.get("id") or "account"))
        self.geometry("400x470")
        self.pic = ttk.Label(self, text="", anchor="center")
        self.pic.pack(pady=(12, 4))
        self.msg = tk.StringVar(value="Fetching avatar...")
        ttk.Label(self, textvariable=self.msg, wraplength=360, justify="center").pack(padx=10)
        ttk.Label(self, text="Reverse image search:").pack(pady=(12, 2))
        row = ttk.Frame(self)
        row.pack()
        for name, tpl in REVERSE_IMAGE:
            sb = ttk.Button(row, text=name, command=lambda t=tpl: self.search(t))
            sb.pack(side="left", padx=2, pady=2)
        row2 = ttk.Frame(self)
        row2.pack(pady=8)
        ttk.Button(row2, text="Open image", command=self.open_image).pack(side="left", padx=2)
        ttk.Button(row2, text="Copy image URL", command=self.copy_url).pack(side="left", padx=2)
        ttk.Button(row2, text="Add URL to notes", command=self.add_note).pack(side="left", padx=2)
        ttk.Label(self, foreground="#666", wraplength=360, justify="center",
                  text="Matches are leads, not proof. Check names, dates and context before acting.").pack(padx=10)
        self.fetch()

    def fetch(self):
        ident = self.ent.get("id", "").strip()
        if not ident:
            self.msg.set("This account has no ID yet.")
            return
        app, kind = self.app, self.kind

        def work():
            if kind == "roblox":
                text, _parsed = run_api(app.apis.get("avatar_roblox"), ident, app.secrets())
                url = text.strip()
            else:
                _text, parsed = run_api(app.apis.get("scan_discord"), ident, app.secrets())
                url = discord_avatar_url(parsed, ident)
            if not url:
                raise ApiError("No avatar available (the account may be new, banned, or still rendering).")
            try:
                data = fetch_bytes(url)
            except (OSError, ValueError):
                data = b""
            return url, data

        def ok(r):
            self.url, data = r
            self.ent["avatar"] = self.url
            app.changed()
            self.msg.set(self.url)
            try:
                import base64
                img = tk.PhotoImage(data=base64.b64encode(data))
                f = max(1, img.width() // 200)
                self.photo = img.subsample(f) if f > 1 else img
                self.pic.configure(image=self.photo)
            except (tk.TclError, ValueError):
                self.msg.set("(No preview, but the image link works.)\n" + self.url)

        def err(e):
            self.msg.set(str(e))
        app.worker.run(work, ok, err)

    def search(self, tpl):
        if not self.url:
            self.msg.set("No image yet.")
            return
        u = tpl.replace("{u}", urllib.parse.quote(self.url, safe=""))
        self.app.open_external([u])

    def open_image(self):
        if self.url:
            self.app.open_external([self.url])

    def copy_url(self):
        if self.url:
            self.clipboard_clear()
            self.clipboard_append(self.url)
            self.app.status("Image URL copied.")

    def add_note(self):
        if self.url:
            self.ent["notes"] = (self.ent.get("notes", "") + "[%s] avatar: %s\n" % (now_stamp(), self.url))
            self.app.changed()
            self.app.rerender(self.node)
            self.app.status("Added to notes.")


class TimezoneDialog(tk.Toplevel):
    """'Their clock says X while mine says Y' -> a UTC offset you can store in the Timezone field."""

    def __init__(self, app, on_pick):
        super().__init__(app.root)
        self.on_pick = on_pick
        self.title("Work out their timezone")
        self.geometry("420x250")
        self.resizable(False, False)
        pad = ttk.Frame(self, padding=14)
        pad.pack(fill="both", expand=True)
        ttk.Label(pad, wraplength=380, justify="left",
                  text="Ask what time it is for them right now, then compare with your own clock.").pack(anchor="w")
        self.theirs = tk.StringVar()
        self.mine = tk.StringVar(value=datetime.datetime.now().strftime("%H:%M"))
        self.out = tk.StringVar(value="")
        for text, var in (("Their time now (3:15 pm or 15:15)", self.theirs), ("My time now", self.mine)):
            ttk.Label(pad, text=text).pack(anchor="w", pady=(10, 0))
            e = ttk.Entry(pad, textvariable=var, width=18)
            e.pack(anchor="w")
            var.trace_add("write", self.update)
            if var is self.theirs:
                e.focus_set()
        ttk.Label(pad, textvariable=self.out, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=10)
        bar = ttk.Frame(pad)
        bar.pack(anchor="e", fill="x")
        ttk.Button(bar, text="Use this", command=self.use).pack(side="right")
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right", padx=6)

    def update(self, *_):
        r = offset_from_times(self.theirs.get(), self.mine.get())
        self.out.set(r or "")

    def use(self):
        r = offset_from_times(self.theirs.get(), self.mine.get())
        if not r:
            messagebox.showinfo(APP_NAME, "Enter both times, like 3:15 pm and 12:15.", parent=self)
            return
        self.on_pick(r)
        self.destroy()


class PresetLibraryDialog(tk.Toplevel):
    """Optional platform presets with ready-made lookup buttons. None of them is added by default."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Preset library")
        self.geometry("560x420")
        pad = ttk.Frame(self, padding=12)
        pad.pack(fill="both", expand=True)
        ttk.Label(pad, wraplength=520, justify="left",
                  text="Pick a platform to add it to this profile's presets. Its lookups come with buttons on each "
                       "account. Endpoints live in apis.json, so you can edit them.").pack(anchor="w")
        row = ttk.Frame(pad)
        row.pack(fill="both", expand=True, pady=8)
        self.lb = tk.Listbox(row, exportselection=False, activestyle="none", height=9)
        self.lb.pack(side="left", fill="y")
        self.info = ttk.Label(row, wraplength=300, justify="left", anchor="nw")
        self.info.pack(side="left", fill="both", expand=True, padx=10)
        self.lb.bind("<<ListboxSelect>>", lambda e: self.show())
        bar = ttk.Frame(pad)
        bar.pack(fill="x")
        ttk.Button(bar, text="Close", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Add to this profile", command=self.add).pack(side="right", padx=6)
        self.refresh()

    def have(self):
        return {p.get("name", "").lower() for p in self.app.settings["presets"]}

    def refresh(self):
        have = self.have()
        self.lb.delete(0, "end")
        for p in PRESET_LIBRARY:
            self.lb.insert("end", p["name"] + ("   (added)" if p["name"].lower() in have else ""))
        if PRESET_LIBRARY:
            self.lb.selection_set(0)
            self.show()

    def show(self):
        sel = self.lb.curselection()
        if not sel:
            return
        p = PRESET_LIBRARY[sel[0]]
        needs = "\n\nNeeds a key: Settings > API keys." if "steam" in p["name"].lower() else ""
        self.info.configure(text="%s\n\nFields: %s\nLink: %s%s" % (
            p.get("about", ""), ", ".join(p.get("fields", [])) or "-", p.get("link_template", ""), needs))

    def add(self):
        sel = self.lb.curselection()
        if not sel:
            return
        p = PRESET_LIBRARY[sel[0]]
        if p["name"].lower() in self.have():
            messagebox.showinfo(APP_NAME, "'%s' is already in this profile." % p["name"], parent=self)
            return
        self.app.add_library_preset(p["name"])
        self.refresh()
        self.app.status("Added the %s preset. Use + Add platform to use it." % p["name"])


class ProfilePicker(tk.Toplevel):
    """Startup window: choose which profile (save file) to open, or make a new one."""

    def __init__(self, root, cfg):
        super().__init__(root)
        self.cfg = cfg
        self.result = None
        self.title("ModDesk - choose a profile")
        self.geometry("460x420")
        self.minsize(420, 360)
        pad = ttk.Frame(self, padding=14)
        pad.pack(fill="both", expand=True)
        ttk.Label(pad, text="Open a profile", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(pad, foreground="#666", wraplength=420, justify="left",
                  text="A profile is a separate save file with its own users, tags and platform presets "
                       "(like a vault). Your API keys are shared.").pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(pad)
        row.pack(fill="both", expand=True)
        self.lb = tk.Listbox(row, exportselection=False, activestyle="none", font=("Segoe UI", 11))
        sb = ttk.Scrollbar(row, command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.lb.pack(side="left", fill="both", expand=True)
        self.lb.bind("<Double-Button-1>", lambda e: self.open_selected())
        self.lb.bind("<Return>", lambda e: self.open_selected())
        bar = ttk.Frame(pad)
        bar.pack(fill="x", pady=8)
        ttk.Button(bar, text="New...", command=self.new).pack(side="left")
        ttk.Button(bar, text="Rename...", command=self.rename).pack(side="left", padx=4)
        ttk.Button(bar, text="Delete...", command=self.delete).pack(side="left")
        self.ask = tk.BooleanVar(value=bool(cfg.get("ask_on_start", True)))
        ttk.Checkbutton(pad, text="Ask me every time ModDesk starts (untick to open the last profile directly)",
                        variable=self.ask).pack(anchor="w")
        bot = ttk.Frame(pad)
        bot.pack(fill="x", pady=(10, 0))
        ttk.Button(bot, text="Quit", command=self.cancel).pack(side="right")
        ttk.Button(bot, text="Open", command=self.open_selected).pack(side="right", padx=6)
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.refresh(cfg.get("last_profile"))
        self.grab_set()
        self.lb.focus_set()

    def refresh(self, select=None):
        names = list_profiles()
        self.lb.delete(0, "end")
        for n in names:
            self.lb.insert("end", n)
        if names:
            i = names.index(select) if select in names else 0
            self.lb.selection_set(i)
            self.lb.see(i)

    def current(self):
        sel = self.lb.curselection()
        return self.lb.get(sel[0]) if sel else None

    def ask_name(self, title, initial=""):
        from tkinter import simpledialog
        return simpledialog.askstring(title, "Profile name:", initialvalue=initial, parent=self)

    def new(self):
        name = self.ask_name("New profile")
        if name is None:
            return
        try:
            made = create_profile(name)
        except (ValueError, OSError) as e:
            messagebox.showwarning(APP_NAME, str(e), parent=self)
            return
        self.refresh(made)

    def rename(self):
        cur = self.current()
        if not cur:
            return
        name = self.ask_name("Rename profile", cur)
        name = clean_profile_name(name) if name else ""
        if not name or name == cur:
            return
        if name.lower() in [p.lower() for p in list_profiles() if p != cur]:
            messagebox.showwarning(APP_NAME, "A profile called '%s' already exists." % name, parent=self)
            return
        try:
            os.rename(os.path.join(PROFILES_DIR, cur), os.path.join(PROFILES_DIR, name))
        except OSError as e:
            messagebox.showwarning(APP_NAME, "Could not rename: %s" % e, parent=self)
            return
        if self.cfg.get("last_profile") == cur:
            self.cfg["last_profile"] = name
        self.refresh(name)

    def delete(self):
        cur = self.current()
        if not cur:
            return
        if not messagebox.askyesno(APP_NAME, "Remove the profile '%s'?\n\nIts folder is moved to profiles\\_trash, "
                                             "so you can still get it back by hand." % cur, parent=self):
            return
        try:
            import shutil
            trash = os.path.join(PROFILES_DIR, "_trash")
            os.makedirs(trash, exist_ok=True)
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            shutil.move(os.path.join(PROFILES_DIR, cur), os.path.join(trash, "%s-%s" % (cur, stamp)))
        except OSError as e:
            messagebox.showwarning(APP_NAME, "Could not remove: %s" % e, parent=self)
            return
        self.refresh()

    def open_selected(self):
        cur = self.current()
        if not cur:
            messagebox.showinfo(APP_NAME, "Pick a profile, or make a new one first.", parent=self)
            return
        self.cfg["ask_on_start"] = bool(self.ask.get())
        self.result = cur
        self.destroy()

    def cancel(self):
        self.cfg["ask_on_start"] = bool(self.ask.get())
        self.result = None
        self.destroy()


class OnboardingWizard(tk.Toplevel):
    """First start: terms -> first profile -> API keys (skippable) -> optional tour."""

    def __init__(self, root, cfg):
        super().__init__(root)
        self.cfg = cfg
        self.done = False
        self.title("Welcome to ModDesk")
        self.geometry("660x560")
        self.resizable(False, False)
        self.accept = tk.BooleanVar(value=False)
        self.pname = tk.StringVar(value=cfg.get("first_profile") or (list_profiles() or ["Default"])[0])
        keys = cfg.get("keys") or {}
        self.tok = tk.StringVar(value=keys.get("discord_token", ""))
        self.guild = tk.StringVar()
        self.key = tk.StringVar()
        self.tour = tk.BooleanVar(value=True)
        self.body = ttk.Frame(self, padding=14)
        self.body.pack(fill="both", expand=True)
        bar = ttk.Frame(self, padding=(14, 0, 14, 12))
        bar.pack(fill="x")
        self.back_btn = ttk.Button(bar, text="Back", command=self.prev)
        self.next_btn = ttk.Button(bar, text="Next", command=self.nxt)
        self.skip_btn = ttk.Button(bar, text="Skip", command=self.skip)
        self.next_btn.pack(side="right")
        self.skip_btn.pack(side="right", padx=6)
        self.back_btn.pack(side="left")
        self.pages = [self.p_terms, self.p_profile, self.p_keys, self.p_finish]
        self.i = 0
        self.accept.trace_add("write", lambda *a: self.update_buttons())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.show()
        self.grab_set()

    def show(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.pages[self.i]()
        self.update_buttons()

    def update_buttons(self):
        last = self.i == len(self.pages) - 1
        self.next_btn.configure(text="Start using ModDesk" if last else "Next")
        state = "normal"
        if self.i == 0 and not self.accept.get():
            state = "disabled"
        self.next_btn.configure(state=state)
        self.back_btn.configure(state="normal" if self.i > 0 else "disabled")
        if self.i == 2:
            self.skip_btn.pack(side="right", padx=6)
        else:
            self.skip_btn.pack_forget()

    def head(self, title, sub=""):
        ttk.Label(self.body, text=title, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        if sub:
            ttk.Label(self.body, text=sub, foreground="#555", wraplength=600, justify="left").pack(
                anchor="w", pady=(2, 8))

    def p_terms(self):
        self.head("Before you start", "Read what ModDesk is for - and what it is not for.")
        fr = ttk.Frame(self.body)
        fr.pack(fill="both", expand=True)
        txt = tk.Text(fr, wrap="word", height=18, padx=8, pady=6, relief="solid", borderwidth=1)
        sb = ttk.Scrollbar(fr, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.insert("1.0", TERMS_TEXT)
        txt.configure(state="disabled")
        ttk.Checkbutton(self.body, text="I have read this and I accept (legitimate moderation use only)",
                        variable=self.accept).pack(anchor="w", pady=(8, 0))

    def p_profile(self):
        self.head("Your first profile", "A profile is a separate save file, like a vault. You can make more later "
                                        "and pick one each time ModDesk starts.")
        ttk.Label(self.body, text="Profile name:").pack(anchor="w", pady=(10, 2))
        e = ttk.Entry(self.body, textvariable=self.pname, width=40)
        e.pack(anchor="w")
        e.focus_set()
        existing = list_profiles()
        if existing:
            ttk.Label(self.body, foreground="#555", wraplength=600, justify="left",
                      text="Found existing data: %s. It is kept - pick one of these names to keep using it, or a "
                           "new name to start fresh." % ", ".join(existing)).pack(anchor="w", pady=10)

    def p_keys(self):
        self.head("API keys (optional)", "You can skip this and add keys later in Settings. Keys are stored as "
                                         "plain text on this computer.")
        ttk.Label(self.body, text="Discord bot token (for Discord lookups):").pack(anchor="w", pady=(8, 2))
        ttk.Entry(self.body, textvariable=self.tok, show="•", width=64).pack(anchor="w")
        ttk.Label(self.body, text="Bloxlink server ID and key (one pair now, more in Settings):").pack(
            anchor="w", pady=(14, 2))
        row = ttk.Frame(self.body)
        row.pack(anchor="w")
        ttk.Entry(row, textvariable=self.guild, width=24).pack(side="left")
        ttk.Entry(row, textvariable=self.key, show="•", width=38).pack(side="left", padx=6)

    def p_finish(self):
        self.head("All set", "Everything can be changed later in Settings (Ctrl+,).")
        ttk.Checkbutton(self.body, text="Show me a quick tour (about a minute, skippable)",
                        variable=self.tour).pack(anchor="w", pady=10)
        ttk.Label(self.body, foreground="#555", wraplength=600, justify="left",
                  text="Tip: Settings > Updates can install a new moddesk.py from a file you downloaded, so you "
                       "never need Git.").pack(anchor="w")

    def prev(self):
        if self.i > 0:
            self.i -= 1
            self.show()

    def skip(self):
        self.tok.set("")
        self.guild.set("")
        self.key.set("")
        self.nxt()

    def nxt(self):
        if self.i == 1:
            name = clean_profile_name(self.pname.get())
            if not name:
                messagebox.showinfo(APP_NAME, "Give the profile a name.", parent=self)
                return
            self.pname.set(name)
        if self.i < len(self.pages) - 1:
            self.i += 1
            self.show()
            return
        self.finish()

    def finish(self):
        cfg = self.cfg
        name = self.pname.get()
        if name.lower() not in [p.lower() for p in list_profiles()]:
            try:
                name = create_profile(name)
            except (ValueError, OSError) as e:
                messagebox.showwarning(APP_NAME, str(e), parent=self)
                return
        else:
            name = next(p for p in list_profiles() if p.lower() == name.lower())
        tok, guild, key = self.tok.get().strip(), self.guild.get().strip(), self.key.get().strip()
        if tok or (guild and key):
            keys = cfg.get("keys") if isinstance(cfg.get("keys"), dict) else {"discord_token": "", "bloxlink": []}
            if tok:
                keys["discord_token"] = tok
            if guild and key:
                keys.setdefault("bloxlink", []).append({"guild": guild, "key": key})
            cfg["keys"] = keys
        cfg["first_profile"] = name
        cfg["last_profile"] = name
        cfg["onboarded"] = True
        cfg["terms"] = "%s %s" % (APP_VERSION, datetime.date.today().isoformat())
        cfg["tour_pending"] = bool(self.tour.get())
        save_app_cfg(cfg)
        self.done = True
        self.destroy()

    def cancel(self):
        self.done = False
        self.destroy()


class TourDialog(tk.Toplevel):
    """A short, skippable walk through the main ideas (also in Help > Quick tour)."""

    def __init__(self, root):
        super().__init__(root)
        self.title("Quick tour")
        self.geometry("520x330")
        self.resizable(False, False)
        self.i = 0
        self.head = ttk.Label(self, font=("Segoe UI", 13, "bold"), padding=(16, 16, 16, 4))
        self.head.pack(anchor="w")
        self.body = ttk.Label(self, wraplength=480, justify="left", padding=(16, 0))
        self.body.pack(anchor="w", fill="x")
        self.count = ttk.Label(self, foreground="#777", padding=(16, 8))
        self.count.pack(anchor="w")
        bar = ttk.Frame(self, padding=16)
        bar.pack(side="bottom", fill="x")
        ttk.Button(bar, text="Skip tour", command=self.destroy).pack(side="left")
        self.next_btn = ttk.Button(bar, text="Next", command=self.nxt)
        self.next_btn.pack(side="right")
        ttk.Button(bar, text="Back", command=self.prev).pack(side="right", padx=6)
        self.show()

    def show(self):
        title, text = TOUR_PAGES[self.i]
        self.head.configure(text=title)
        self.body.configure(text=text)
        self.count.configure(text="%d / %d" % (self.i + 1, len(TOUR_PAGES)))
        self.next_btn.configure(text="Done" if self.i == len(TOUR_PAGES) - 1 else "Next")

    def nxt(self):
        if self.i >= len(TOUR_PAGES) - 1:
            self.destroy()
            return
        self.i += 1
        self.show()

    def prev(self):
        if self.i > 0:
            self.i -= 1
            self.show()


class SettingsWindow(tk.Toplevel):
    """One place for options: General, Keybinds, Data & keys, Updates, About, Terms."""

    def __init__(self, app, tab=0):
        super().__init__(app.root)
        self.app = app
        self.title("ModDesk settings")
        self.geometry("740x580")
        self.minsize(660, 500)
        self.capturing = None
        self.key_btns = {}
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)
        self.nb = nb
        for title, build in [("General", self.tab_general), ("Keybinds", self.tab_keys),
                             ("Data & keys", self.tab_data), ("Updates", self.tab_updates),
                             ("About", self.tab_about), ("Terms", self.tab_terms)]:
            fr = ttk.Frame(nb, padding=12)
            nb.add(fr, text=title)
            build(fr)
        try:
            nb.select(tab)
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.app.settings_win = None
        self.destroy()

    def tab_general(self, f):
        box = ttk.LabelFrame(f, text="Behaviour", padding=10)
        box.pack(fill="x")
        self.vars = {}
        for key, label in SETTING_TOGGLES:
            var = tk.BooleanVar(value=bool(self.app.settings.get(key, True)))
            var.trace_add("write", lambda *a, k=key, v=var: self.app.set_setting(k, v.get()))
            self.vars[key] = var
            ttk.Checkbutton(box, text=label, variable=var).pack(anchor="w", pady=2)
        self.browser_box(f)
        pb = ttk.LabelFrame(f, text="Profile", padding=10)
        pb.pack(fill="x", pady=12)
        ttk.Label(pb, text="Current profile: %s" % (CURRENT_PROFILE or "(none)"),
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.ask = tk.BooleanVar(value=bool(self.app.app_cfg.get("ask_on_start", True)))
        self.ask.trace_add("write", self.set_ask)
        ttk.Checkbutton(pb, text="Ask which profile to open every time ModDesk starts", variable=self.ask).pack(
            anchor="w", pady=4)
        row = ttk.Frame(pb)
        row.pack(anchor="w")
        ttk.Button(row, text="Switch profile...", command=self.app.switch_profile).pack(side="left")
        ttk.Button(row, text="Open profile folder", command=lambda: self.app.open_path(
            os.path.dirname(DATA_DIR))).pack(side="left", padx=6)

    def set_ask(self, *_):
        self.app.app_cfg["ask_on_start"] = bool(self.ask.get())
        save_app_cfg(self.app.app_cfg)

    def tab_keys(self, f):
        ttk.Label(f, foreground="#555", wraplength=660, justify="left",
                  text="Click a shortcut, then press the new keys (Esc cancels). Use Ctrl or Alt with a key, so "
                       "typing in fields is never affected.").pack(anchor="w", pady=(0, 8))
        binds = self.app.keybinds()
        for action, label in KEY_ACTIONS:
            row = ttk.Frame(f)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=label, width=34).pack(side="left")
            btn = ttk.Button(row, text=pretty_key(binds[action]), width=20,
                             command=lambda a=action: self.capture(a))
            btn.pack(side="left")
            self.key_btns[action] = btn
        ttk.Label(f, foreground="#777", text="Fixed: F2 renames the selected row.").pack(anchor="w", pady=(10, 0))
        ttk.Button(f, text="Reset all to defaults", command=self.reset_keys).pack(anchor="w", pady=10)

    def capture(self, action):
        self.capturing = action
        self.key_btns[action].configure(text="Press the keys...")
        self.bind("<Key>", self.on_key)
        self.focus_force()

    def stop_capture(self):
        self.unbind("<Key>")
        self.capturing = None
        binds = self.app.keybinds()
        for action, btn in self.key_btns.items():
            btn.configure(text=pretty_key(binds[action]))

    def on_key(self, e):
        if self.capturing is None:
            return None
        if e.keysym == "Escape":
            self.stop_capture()
            return "break"
        seq = key_sequence(e.state, e.keysym)
        if not seq:
            if e.keysym not in MOD_KEYSYMS:
                self.key_btns[self.capturing].configure(text="Use Ctrl or Alt + a key")
            return "break"
        binds = self.app.keybinds()
        clash = [a for a, s in binds.items() if s == seq and a != self.capturing]
        if clash:
            label = dict(KEY_ACTIONS)[clash[0]]
            messagebox.showinfo(APP_NAME, "%s is already used for '%s'." % (pretty_key(seq), label), parent=self)
            self.stop_capture()
            return "break"
        self.app.set_keybind(self.capturing, seq)
        self.stop_capture()
        return "break"

    def reset_keys(self):
        self.app.app_cfg["keybinds"] = {}
        save_app_cfg(self.app.app_cfg)
        self.app.apply_keybinds()
        self.stop_capture()

    def tab_data(self, f):
        ttk.Label(f, foreground="#555", wraplength=660, justify="left",
                  text="API keys are shared by every profile. Platform presets and tags belong to the open "
                       "profile.").pack(anchor="w", pady=(0, 10))
        for text, cmd in [("API keys...", lambda: KeysDialog(self.app)),
                          ("Platform presets...", lambda: PresetsDialog(self.app)),
                          ("Preset library (GitHub, Bluesky...)", lambda: PresetLibraryDialog(self.app)),
                          ("Tags (colors)...", lambda: TagsDialog(self.app)),
                          ("Set window icon...", self.app.set_icon_file),
                          ("Open apis.json (edit endpoints)", lambda: self.app.open_path(API_FILE)),
                          ("Open program folder", lambda: self.app.open_path(APP_DIR))]:
            ttk.Button(f, text=text, command=cmd, width=34).pack(anchor="w", pady=3)

    def tab_updates(self, f):
        ttk.Label(f, text="Installed version: %s" % APP_VERSION, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(f, foreground="#555", wraplength=660, justify="left",
                  text="Code file: %s\nUpdates replace only this file. Your profiles, keys and settings are not "
                       "touched, and the old version is saved in the backups folder." % APP_CODE).pack(
            anchor="w", pady=(2, 10))
        a = ttk.LabelFrame(f, text="From a file (no Git needed)", padding=10)
        a.pack(fill="x")
        ttk.Label(a, wraplength=640, justify="left",
                  text="Download the new moddesk.py (or a source ZIP that contains it) and pick it here.").pack(
            anchor="w")
        ttk.Button(a, text="Install update from file...", command=self.app.install_update).pack(anchor="w", pady=6)
        b = ttk.LabelFrame(f, text="From GitHub (optional)", padding=10)
        b.pack(fill="x", pady=12)
        ttk.Label(b, wraplength=640, justify="left",
                  text="If the project lives in a GitHub repo, put it as owner/name. ModDesk reads moddesk.py "
                       "from that branch and installs it when the version is newer.").pack(anchor="w")
        row = ttk.Frame(b)
        row.pack(anchor="w", pady=6)
        self.repo = tk.StringVar(value=self.app.app_cfg.get("update_repo") or DEFAULT_UPDATE_REPO)
        self.branch = tk.StringVar(value=self.app.app_cfg.get("update_branch", "main"))
        ttk.Label(row, text="Repo").pack(side="left")
        ttk.Entry(row, textvariable=self.repo, width=30).pack(side="left", padx=4)
        ttk.Label(row, text="Branch").pack(side="left")
        ttk.Entry(row, textvariable=self.branch, width=10).pack(side="left", padx=4)
        self.msg = tk.StringVar(value="")
        self.auto = tk.BooleanVar(value=bool(self.app.app_cfg.get("auto_update_check", True)))
        self.auto.trace_add("write", self.set_auto)
        ttk.Checkbutton(b, text="Tell me in the status bar when a newer version exists (checks at start)",
                        variable=self.auto).pack(anchor="w")
        ttk.Button(b, text="Check for updates", command=self.check).pack(anchor="w", pady=(6, 0))
        ttk.Label(b, textvariable=self.msg, wraplength=640, justify="left").pack(anchor="w", pady=4)
        ttk.Label(f, foreground="#555", wraplength=660, justify="left",
                  text="To change the program itself (exe, installer), run ModDesk-Setup.exe again - it updates in "
                       "place and keeps your data.").pack(anchor="w")

    def set_auto(self, *_):
        self.app.app_cfg["auto_update_check"] = bool(self.auto.get())
        save_app_cfg(self.app.app_cfg)

    def check(self):
        cfg = self.app.app_cfg
        cfg["update_repo"] = self.repo.get().strip()
        cfg["update_branch"] = self.branch.get().strip() or "main"
        save_app_cfg(cfg)
        self.app.check_github_update(cfg["update_repo"], cfg["update_branch"], self.msg)

    def tab_about(self, f):
        ttk.Label(f, text="ModDesk %s" % APP_VERSION, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(f, wraplength=660, justify="left", padding=(0, 8),
                  text="A private notebook for moderation and background-check work on Roblox and Discord: who "
                       "owns which accounts, what you saw, and why - kept as plain files on your computer.\n\n"
                       "It is for organising legitimate moderation work. It is not for stalking, doxxing or "
                       "targeting private people (see the Terms tab).").pack(anchor="w")
        info = ("Program folder: %s\nProfiles: %s\nOpen profile: %s" % (APP_DIR, PROFILES_DIR, CURRENT_PROFILE))
        ttk.Label(f, text=info, foreground="#555", wraplength=660, justify="left").pack(anchor="w", pady=8)
        ttk.Label(f, wraplength=660, justify="left", font=("Segoe UI", 10, "bold"),
                  text="Matches are leads, not proof - review the results yourself.").pack(anchor="w", pady=(10, 0))

    def tab_terms(self, f):
        fr = ttk.Frame(f)
        fr.pack(fill="both", expand=True)
        txt = tk.Text(fr, wrap="word", padx=8, pady=6, relief="solid", borderwidth=1)
        sb = ttk.Scrollbar(fr, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        txt.insert("1.0", TERMS_TEXT)
        txt.configure(state="disabled")

    def browser_box(self, f):
        cfg = self.app.app_cfg.setdefault("browser", {"kind": "default", "profile": "", "path": "", "args": ""})
        bf = ttk.LabelFrame(f, text="Browser for links", padding=10)
        bf.pack(fill="x", pady=(12, 0))
        labels = {k: v for k, v in BROWSERS}
        self.bkind = tk.StringVar(value=labels.get(cfg.get("kind", "default"), "System default"))
        self.bprof = tk.StringVar(value=cfg.get("profile", ""))
        self.bpath = tk.StringVar(value=cfg.get("path", ""))
        self.bargs = tk.StringVar(value=cfg.get("args", ""))
        r1 = ttk.Frame(bf)
        r1.pack(fill="x")
        ttk.Label(r1, text="Open links in:").pack(side="left")
        kc = ttk.Combobox(r1, textvariable=self.bkind, values=[v for _k, v in BROWSERS], state="readonly", width=20)
        kc.pack(side="left", padx=6)
        kc.bind("<<ComboboxSelected>>", lambda e: (self.refresh_profiles(), self.save_browser()))
        ttk.Label(r1, text="Profile:").pack(side="left", padx=(10, 2))
        self.pcombo = ttk.Combobox(r1, textvariable=self.bprof, width=28)
        self.pcombo.pack(side="left")
        r2 = ttk.Frame(bf)
        r2.pack(fill="x", pady=(6, 0))
        ttk.Label(r2, text="Program (Other only):").pack(side="left")
        ttk.Entry(r2, textvariable=self.bpath, width=34).pack(side="left", padx=6)
        ttk.Button(r2, text="Browse...", command=self.browse_exe).pack(side="left")
        r3 = ttk.Frame(bf)
        r3.pack(fill="x", pady=(6, 0))
        ttk.Label(r3, text="Extra arguments (use {url}):").pack(side="left")
        ttk.Entry(r3, textvariable=self.bargs, width=34).pack(side="left", padx=6)
        ttk.Button(r3, text="Test", command=self.test_browser).pack(side="left")
        ttk.Label(bf, foreground="#555", wraplength=640, justify="left",
                  text="Pick a browser and, if you use several, the profile (Firefox profile names come from "
                       "Firefox itself). Firefox opens a different profile only when it is closed or already on "
                       "that profile. 'System default' uses Windows' default browser.").pack(anchor="w", pady=(6, 0))
        for v in (self.bprof, self.bpath, self.bargs):
            v.trace_add("write", lambda *a: self.save_browser())
        self.refresh_profiles()

    def browser_kind(self):
        back = {v: k for k, v in BROWSERS}
        return back.get(self.bkind.get(), "default")

    def refresh_profiles(self):
        self.pcombo.configure(values=browser_profiles(self.browser_kind()))

    def save_browser(self):
        self.app.app_cfg["browser"] = {"kind": self.browser_kind(), "profile": self.bprof.get().strip(),
                                       "path": self.bpath.get().strip(), "args": self.bargs.get().strip()}
        save_app_cfg(self.app.app_cfg)

    def browse_exe(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(title="Choose a browser program", parent=self,
                                       filetypes=[("Programs", "*.exe"), ("All files", "*.*")])
        if p:
            self.bpath.set(p)

    def test_browser(self):
        self.save_browser()
        self.app.open_external(["https://www.example.com"])


# ==========================================================================
# Tools: username checker and condo-scan placeholders
# ==========================================================================

# Username checker (Sherlock-style). Leads only: a site that answers "found" is not proof it is the same person.
# The site list comes from the open-source Sherlock project (MIT), downloaded on demand and cached next to the app.
SHERLOCK_URLS = [
    "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock_project/resources/data.json",
    "https://raw.githubusercontent.com/sherlock-project/sherlock/master/sherlock/resources/data.json",
    "https://raw.githubusercontent.com/sherlock-project/sherlock/main/sherlock_project/resources/data.json",
    "https://raw.githubusercontent.com/sherlock-project/sherlock/main/sherlock/resources/data.json",
]

SITES_FILE = os.path.join(APP_DIR, "sherlock_sites.json")

CHECK_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/124.0 Safari/537.36", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.8"}

POPULAR_SITES = ["GitHub", "GitLab", "Reddit", "Twitter", "Instagram", "TikTok", "YouTube", "Twitch", "Steam",
                 "SoundCloud", "Pinterest", "Medium", "DeviantArt", "Tumblr", "Spotify", "Pastebin", "Replit",
                 "Roblox", "Snapchat", "Telegram", "Bluesky", "Mastodon", "Patreon", "Linktree", "Kick"]

BUILTIN_SITES = {
    "GitHub": {"url": "https://github.com/{}", "errorType": "status_code"},
    "GitLab": {"url": "https://gitlab.com/{}", "errorType": "status_code"},
    "DEV Community": {"url": "https://dev.to/{}", "errorType": "status_code"},
    "Medium": {"url": "https://medium.com/@{}", "errorType": "status_code"},
    "Replit": {"url": "https://replit.com/@{}", "errorType": "status_code"},
    "Pastebin": {"url": "https://pastebin.com/u/{}", "errorType": "status_code"},
    "SoundCloud": {"url": "https://soundcloud.com/{}", "errorType": "status_code"},
    "Steam": {"url": "https://steamcommunity.com/id/{}", "errorType": "message",
              "errorMsg": "The specified profile could not be found"},
}

MAX_CHECK_NAMES = 6
MAX_CHECK_JOBS = 800


def norm_sites(raw):
    """Turn Sherlock's data.json into a simple sorted list of dicts we can check."""
    out = []
    for name, d in (raw or {}).items():
        if not isinstance(d, dict) or not isinstance(d.get("url"), str) or name.startswith("$"):
            continue
        out.append({"name": name, "url": d["url"], "main": d.get("urlMain", ""),
                    "type": d.get("errorType", "status_code"), "msg": d.get("errorMsg"),
                    "code": d.get("errorCode"), "regex": d.get("regexCheck"), "probe": d.get("urlProbe"),
                    "headers": d.get("headers") or {}, "method": d.get("request_method"),
                    "nsfw": bool(d.get("isNSFW")), "waf": list((d.get("errors") or {}).keys())})
    return sorted(out, key=lambda s: s["name"].lower())


def load_sites():
    """(sites, where) - the downloaded Sherlock list if present, else a tiny built-in list."""
    try:
        with open(SITES_FILE, encoding="utf-8") as f:
            sites = norm_sites(json.load(f))
        if sites:
            return sites, "Sherlock list (%d sites)" % len(sites)
    except (OSError, ValueError):
        pass
    return norm_sites(BUILTIN_SITES), "built-in list (%d sites) - use Update site list for 400+" % len(BUILTIN_SITES)


def download_sites():
    """Fetch Sherlock's data.json into SITES_FILE. Returns the number of sites; raises if every URL failed."""
    last = None
    for url in SHERLOCK_URLS:
        try:
            raw = json.loads(fetch_bytes(url, timeout=30, limit=8000000).decode("utf-8"))
            if norm_sites(raw):
                with open(SITES_FILE, "w", encoding="utf-8") as f:
                    json.dump(raw, f)
                return len(norm_sites(raw))
        except Exception as e:  # noqa - try the next location
            last = e
    raise RuntimeError("Could not download the site list (%s)." % last)


def _fetch(url, method, headers, follow, timeout, want_body):
    import urllib.request
    import urllib.error

    class Stop(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(Stop)
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as r:
            body = r.read(300000).decode("utf-8", "replace") if want_body else ""
            return r.status, body
    except urllib.error.HTTPError as e:
        body = ""
        if want_body:
            try:
                body = e.read(300000).decode("utf-8", "replace")
            except Exception:  # noqa
                pass
        return e.code, body


def check_site(site, name, timeout=12):
    """-> (result, link); result is found / missing / unsure / skipped."""
    link = site["url"].replace("{}", urllib.parse.quote(name, safe=""))
    if site.get("regex"):
        try:
            if not re.fullmatch(site["regex"], name):
                return "skipped", link
        except re.error:
            pass
    types = site["type"] if isinstance(site["type"], list) else [site["type"]]
    probe = (site.get("probe") or site["url"]).replace("{}", urllib.parse.quote(name, safe=""))
    headers = dict(CHECK_HEADERS)
    headers.update(site.get("headers") or {})
    want_body = "message" in types or bool(site.get("waf"))
    method = (site.get("method") or ("GET" if want_body else "HEAD")).upper()
    try:
        status, body = _fetch(probe, method, headers, "response_url" not in types, timeout, want_body)
    except Exception:  # noqa - network error, timeout, TLS
        return "unsure", link
    if status in (403, 405, 429) or status >= 500 or any(w in body for w in site.get("waf", [])):
        return "unsure", link
    verdicts = []
    for t in types:
        if t == "message":
            msgs = site.get("msg")
            msgs = [msgs] if isinstance(msgs, str) else (msgs or [])
            verdicts.append(not any(m in body for m in msgs))
        elif t == "response_url":
            verdicts.append(200 <= status < 300)
        else:
            codes = site.get("code")
            codes = [codes] if isinstance(codes, int) else (codes or [])
            verdicts.append(status not in codes if codes else 200 <= status < 300)
    return ("found" if verdicts and all(verdicts) else "missing"), link


class UsernameCheckDialog(tk.Toplevel):
    """Check which sites have an account with the given username(s). Results are leads, not proof."""

    def __init__(self, app, node, names):
        super().__init__(app.root)
        self.app = app
        self.node = node
        self.title("Check usernames - %s" % node["name"])
        self.geometry("980x640")
        self.sites, self.where = load_sites()
        self.picked = {s["name"] for s in self.sites if s["name"] in POPULAR_SITES} or {s["name"] for s in self.sites}
        self.shown = []
        self.q = queue.Queue()
        self.stop = threading.Event()
        self.running = False
        self.counts = {"done": 0, "total": 0, "found": 0, "unsure": 0}

        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, justify="left", wraplength=940,
                  text="Usernames to check (one per line, max %d). A 'Found' only means a page exists at that "
                       "address - it can be a different person. Treat results as leads, then confirm them." %
                       MAX_CHECK_NAMES).pack(anchor="w")
        self.names_text = tk.Text(top, height=4, width=40)
        self.names_text.pack(anchor="w", pady=4)
        self.names_text.insert("1.0", "\n".join(names[:MAX_CHECK_NAMES]))

        mid = ttk.Frame(self, padding=(8, 0))
        mid.pack(fill="both", expand=True)
        mid.columnconfigure(1, weight=1)
        mid.rowconfigure(1, weight=1)
        self.where_lbl = ttk.Label(mid, text="Sites: " + self.where)
        self.where_lbl.grid(row=0, column=0, sticky="w")
        left = ttk.Frame(mid)
        left.grid(row=1, column=0, sticky="ns", padx=(0, 8))
        self.filter_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.filter_var).pack(fill="x")
        self.filter_var.trace_add("write", lambda *a: self.fill_sites())
        fr = ttk.Frame(left)
        fr.pack(fill="both", expand=True, pady=4)
        self.slb = tk.Listbox(fr, selectmode="extended", exportselection=False, activestyle="none", width=26)
        sb = ttk.Scrollbar(fr, command=self.slb.yview)
        self.slb.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.slb.pack(side="left", fill="both", expand=True)
        self.slb.bind("<<ListboxSelect>>", lambda e: self.remember())
        sbar = ttk.Frame(left)
        sbar.pack(fill="x")
        ttk.Button(sbar, text="Popular", command=self.pick_popular).pack(side="left")
        ttk.Button(sbar, text="All", command=self.pick_all).pack(side="left", padx=2)
        ttk.Button(sbar, text="None", command=self.pick_none).pack(side="left")
        ttk.Button(left, text="Update site list", command=self.update_sites).pack(fill="x", pady=(6, 0))

        right = ttk.Frame(mid)
        right.grid(row=1, column=1, sticky="nsew")
        cols = ("site", "name", "result", "link")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", selectmode="extended")
        for c, t, w in (("site", "Site", 150), ("name", "Username", 130), ("result", "Result", 70),
                        ("link", "Link", 420)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        tsb = ttk.Scrollbar(right, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tsb.set)
        tsb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Double-Button-1>", lambda e: self.open_selected())

        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        self.go_btn = ttk.Button(bar, text="Check", command=self.start)
        self.go_btn.pack(side="left")
        ttk.Button(bar, text="Stop", command=self.stop.set).pack(side="left", padx=4)
        self.msg = tk.StringVar(value="Pick sites and press Check.")
        ttk.Label(bar, textvariable=self.msg).pack(side="left", padx=10)
        ttk.Button(bar, text="Close", command=self.close).pack(side="right")
        ttk.Button(bar, text="Add as guess accounts", command=self.add_guesses).pack(side="right", padx=4)
        ttk.Button(bar, text="Copy links", command=self.copy_links).pack(side="right")
        ttk.Button(bar, text="Open", command=self.open_selected).pack(side="right", padx=4)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.fill_sites()

    # ----- site list -----
    def fill_sites(self):
        low = self.filter_var.get().strip().lower()
        self.shown = [s["name"] for s in self.sites if not s["nsfw"] and low in s["name"].lower()]
        self.slb.delete(0, "end")
        for i, n in enumerate(self.shown):
            self.slb.insert("end", n)
            if n in self.picked:
                self.slb.selection_set(i)

    def remember(self):
        chosen = {self.shown[i] for i in self.slb.curselection()}
        self.picked -= set(self.shown)
        self.picked |= chosen

    def pick_popular(self):
        self.picked = {s["name"] for s in self.sites if s["name"] in POPULAR_SITES}
        self.fill_sites()

    def pick_all(self):
        self.picked = {s["name"] for s in self.sites if not s["nsfw"]}
        self.fill_sites()

    def pick_none(self):
        self.picked = set()
        self.fill_sites()

    def update_sites(self):
        self.msg.set("Downloading the site list...")

        def work():
            try:
                self.q.put(("sites", download_sites()))
            except Exception as e:  # noqa
                self.q.put(("error", str(e)))
        threading.Thread(target=work, daemon=True).start()
        self.after(150, self.poll)

    # ----- running -----
    def names(self):
        out = []
        for ln in self.names_text.get("1.0", "end").splitlines():
            ln = ln.strip()
            if ln and ln not in out:
                out.append(ln)
        return out[:MAX_CHECK_NAMES]

    def start(self):
        if self.running:
            return
        names = self.names()
        sites = [s for s in self.sites if s["name"] in self.picked and not s["nsfw"]]
        if not names or not sites:
            self.msg.set("Enter at least one username and pick at least one site.")
            return
        if len(names) * len(sites) > MAX_CHECK_JOBS:
            messagebox.showinfo(APP_NAME, "That is %d checks (limit %d). Pick fewer sites or usernames." % (
                len(names) * len(sites), MAX_CHECK_JOBS), parent=self)
            return
        self.tree.delete(*self.tree.get_children())
        self.stop.clear()
        self.running = True
        self.counts = {"done": 0, "total": len(names) * len(sites), "found": 0, "unsure": 0}
        self.go_btn.state(["disabled"])
        jobs = [(s, n) for n in names for s in sites]

        def one(job):
            if self.stop.is_set():
                return
            s, n = job
            res, link = check_site(s, n)
            self.q.put(("result", s["name"], n, res, link))

        def work():
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=16) as ex:
                list(ex.map(one, jobs))
            self.q.put(("end",))
        threading.Thread(target=work, daemon=True).start()
        self.after(150, self.poll)

    def poll(self):
        again = self.running
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "result":
                    _k, site, name, res, link = m
                    self.counts["done"] += 1
                    if res in ("found", "unsure"):
                        self.counts[res] += 1
                        self.tree.insert("", "end", values=(site, name, res.title(), link))
                elif m[0] == "end":
                    self.running = False
                    self.go_btn.state(["!disabled"])
                    again = False
                elif m[0] == "sites":
                    self.sites, self.where = load_sites()
                    self.where_lbl.config(text="Sites: " + self.where)
                    self.pick_popular()
                    self.msg.set("Site list updated: %d sites." % m[1])
                elif m[0] == "error":
                    self.msg.set(m[1])
        except queue.Empty:
            pass
        c = self.counts
        if self.running or c["total"]:
            self.msg.set("%s %d/%d - found %d, unsure %d" % ("Checking" if self.running else "Finished",
                                                          c["done"], c["total"], c["found"], c["unsure"])
                         if c["total"] else self.msg.get())
        if again:
            self.after(150, self.poll)

    # ----- results -----
    def rows(self, only_selected=True):
        ids = self.tree.selection() if only_selected else self.tree.get_children()
        return [self.tree.item(i, "values") for i in ids]

    def open_selected(self):
        urls = [r[3] for r in self.rows()][:MAX_WINDOWS]
        if urls:
            self.app.open_external(urls)

    def copy_links(self):
        rows = self.rows() or self.rows(False)
        self.clipboard_clear()
        self.clipboard_append("\n".join(r[3] for r in rows))
        self.msg.set("Copied %d link(s)." % len(rows))

    def add_guesses(self):
        rows = [r for r in (self.rows() or self.rows(False)) if r[2] == "Found"]
        if not rows:
            self.msg.set("Select Found rows (or run a check) first.")
            return
        added = 0
        for site, name, _res, link in rows:
            plat = next((p for p in self.node["accounts"] if p["platform"].strip().lower() == site.lower()), None)
            if plat is None:
                plat = {"platform": site, "entries": []}
                self.node["accounts"].append(plat)
            if any(e.get("username", "").lower() == name.lower() for e in plat["entries"]):
                continue
            ent = new_entry()
            ent.update({"username": name, "link": link, "conf": {"level": "Guess", "source": "Username check"}})
            plat["entries"].append(ent)
            added += 1
        self.app.changed()
        self.app.rerender(self.node)
        self.msg.set("Added %d guess account(s) to %s." % (added, self.node["name"]))

    def close(self):
        self.stop.set()
        self.destroy()


# Condo scan services. PLACEHOLDERS: the buttons exist on Roblox and Discord accounts but nothing is called yet.
# To wire one later, add its endpoints to apis.json and replace the "not wired" branch in CondoDialog.run().
CONDO_SERVICES = [
    {"name": "Moco-co / TASE (simmer.icu)", "site": "https://simmer.icu", "api": "https://api.simmer.icu",
     "platforms": ["roblox", "discord"], "how": "GET/POST requests with an API key"},
    {"name": "Rotector (rayward.app)", "site": "https://rayward.app", "api": "",
     "platforms": ["roblox", "discord"], "how": "API key (details to be added)"},
]


class CondoDialog(tk.Toplevel):
    """Condo-scan services for one Roblox/Discord account. Placeholder: opening the sites works, checks do not run yet."""

    def __init__(self, app, kind, ent):
        super().__init__(app.root)
        self.app = app
        self.kind = kind
        self.ent = ent
        self.title("Condo scan - %s" % kind.title())
        self.transient(app.root)
        pad = ttk.Frame(self, padding=12)
        pad.pack(fill="both", expand=True)
        who = ent.get("id") or ent.get("username") or "(no ID yet)"
        ttk.Label(pad, text="%s account: %s" % (kind.title(), who)).pack(anchor="w")
        ttk.Label(pad, foreground="#666", wraplength=460, justify="left",
                  text="Not wired yet. These services need API keys, so the checks are switched off for now. "
                       "You can already open their sites.").pack(anchor="w", pady=(2, 8))
        for svc in CONDO_SERVICES:
            if kind not in svc["platforms"]:
                continue
            row = ttk.Frame(pad)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=svc["name"], width=30).pack(side="left")
            ttk.Button(row, text="Open site", command=lambda s=svc: app.open_external([s["site"]])).pack(side="left")
            b = ttk.Button(row, text="Check (later)", command=lambda s=svc: self.run(s))
            b.pack(side="left", padx=4)
            b.state(["disabled"])
        ttk.Button(pad, text="Close", command=self.destroy).pack(anchor="e", pady=(10, 0))

    def run(self, svc):
        messagebox.showinfo(APP_NAME, "%s is not wired yet." % svc["name"], parent=self)


# ==========================================================================
# Entry point
# ==========================================================================

def main():
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ModDesk.App")  # own taskbar identity
    except Exception:  # noqa - not Windows
        pass
    root = tk.Tk()
    cfg = load_app_cfg()
    migrate_legacy()
    root.withdraw()
    if not cfg.get("onboarded"):
        wiz = OnboardingWizard(root, cfg)
        root.wait_window(wiz)
        if not wiz.done:
            root.destroy()
            return
    if not list_profiles():
        create_profile("Default")
    profiles = list_profiles()
    name = cfg.get("last_profile")
    if "--pick" in sys.argv or cfg.get("ask_on_start", True) or name not in profiles:
        picker = ProfilePicker(root, cfg)
        root.wait_window(picker)
        if not picker.result:
            save_app_cfg(cfg)
            root.destroy()
            return
        name = picker.result
    cfg["last_profile"] = name
    save_app_cfg(cfg)
    set_profile(name)
    root.deiconify()
    try:
        app = App(root)
    except Exception:  # noqa
        import traceback
        log_crash(traceback.format_exc())
        messagebox.showerror(APP_NAME, "ModDesk could not start. Details were saved in crash.log next to the program.")
        raise

    def report(exc, val, tb):
        import traceback
        log_crash("".join(traceback.format_exception(exc, val, tb)))
        app.status("Something went wrong - details are in crash.log")
    root.report_callback_exception = report
    root.after(500, app.maybe_tour)
    root.mainloop()


if __name__ == "__main__":
    main()
