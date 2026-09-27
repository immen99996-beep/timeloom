"""Generate the static site into public/.

Needs: pip install tzdata   (current time zone rules for the guide tables)
Run:   python3 scripts/build.py
Settings live in site.config.json.
"""
import html, json, re, shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import zoneinfo

zoneinfo.reset_tzpath(to=[])  # use the tzdata package, not the (possibly older) system copy
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "src", ROOT / "public"
CFG = json.loads((ROOT / "site.config.json").read_text())
DATA = json.loads((ROOT / "data" / "world.json").read_text())
URL = CFG["site_url"].rstrip("/")
NAME = CFG["site_name"]
TODAY = date.fromisoformat(CFG["lastmod"]) if CFG.get("lastmod") else date.today()
YEAR = TODAY.year
YEARS = [YEAR, YEAR + 1]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
JS_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
e = html.escape

COUNTRIES = DATA["countries"]
CITIES = [dict(zip(["id", "name", "cc", "tz", "al"], c)) for c in DATA["cities"]]
BY_CC = {}
for c in CITIES:
    BY_CC.setdefault(c["cc"], []).append(c)

pages = []  # (path, priority) for the sitemap


def weekend(cc):
    return DATA["weekend"].get(cc, [0, 6])  # JS day numbers, Sunday = 0


def wk_names(days):
    return " and ".join(JS_DAYS[d] for d in sorted(days, key=lambda d: (d + 6) % 7))


def js_dow(d):
    return (d.weekday() + 1) % 7


def offset_label(td):
    mins = int(td.total_seconds() // 60)
    if mins == 0:
        return "UTC+0"
    sign = "+" if mins > 0 else "−"
    a = abs(mins)
    return f"UTC{sign}{a // 60}" + (f":{a % 60:02d}" if a % 60 else "")


def fmt_date(d, year=True):
    s = f"{d.strftime('%b')} {d.day}"
    return f"{s}, {d.year}" if year else s


def icon(name, cls="icon"):
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"/></svg>'


def flag(cc, cls=""):
    return f'<img class="flag {cls}" src="/flags/{cc.lower()}.svg" alt="" width="24" height="18" loading="lazy">'


SPRITE = """<svg width="0" height="0" style="position:absolute" aria-hidden="true">
<symbol id="i-globe" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></symbol>
<symbol id="i-search" viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></symbol>
<symbol id="i-star" viewBox="0 0 24 24"><path d="M12 17.27 18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/></symbol>
<symbol id="i-close" viewBox="0 0 24 24"><path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></symbol>
<symbol id="i-share" viewBox="0 0 24 24"><path d="M18 16.08c-.76 0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></symbol>
<symbol id="i-clock" viewBox="0 0 24 24"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.2 14.2L11 13V7h1.5v5.2l4.5 2.7-.8 1.3z"/></symbol>
<symbol id="i-event" viewBox="0 0 24 24"><path d="M17 12h-5v5h5v-5zM16 1v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19a2 2 0 0 0 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2h-1V1h-2zm3 18H5V8h14v11z"/></symbol>
<symbol id="i-groups" viewBox="0 0 24 24"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></symbol>
<symbol id="i-warn" viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></symbol>
<symbol id="i-ok" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></symbol>
<symbol id="i-info" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></symbol>
<symbol id="i-block" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></symbol>
<symbol id="i-link" viewBox="0 0 24 24"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></symbol>
<symbol id="i-pin" viewBox="0 0 24 24"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5a2.5 2.5 0 1 1 0-5 2.5 2.5 0 0 1 0 5z"/></symbol>
</svg>"""

NAV = [("/", "Planner"), ("/holidays/", "Holidays"), ("/guides/", "Guides"), ("/about/", "About")]


def layout(path, title, description, body, *, section="", jsonld=None, scripts="", head_extra="", noindex=False, priority=None):
    canonical = URL + path
    ld = "".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in (jsonld or []))
    ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={e(CFG["adsense_client"])}" crossorigin="anonymous"></script>'
           if CFG.get("adsense_client") else "")
    verify = f'<meta name="google-site-verification" content="{e(CFG["google_site_verification"])}">' if CFG.get("google_site_verification") else ""
    nav = "".join(f'<a href="{href}"{" aria-current=\"page\"" if section == href else ""}>{label}</a>' for href, label in NAV)
    full_title = title if title == NAME else f"{title} | {CFG['short_name']}"
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{canonical}">
{'<meta name="robots" content="noindex">' if noindex else ''}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(NAME)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{URL}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#2563EB">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<link rel="stylesheet" href="/assets/style.css">
{verify}{ads}{head_extra}{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{SPRITE}
<header class="top">
  <div class="wrap">
    <a class="brand" href="/"><span class="brand-mark">{icon("globe")}</span><span class="brand-name">{e(NAME)}</span></a>
    <nav class="nav" aria-label="Main">{nav}</nav>
  </div>
</header>
{body}
<footer class="site-foot">
  <div class="wrap">
    <nav class="foot-links" aria-label="Footer">
      <a href="/">Planner</a><a href="/holidays/">Public holidays</a><a href="/guides/">Guides</a><a href="/about/">About</a><a href="/contact/">Contact</a><a href="/privacy/">Privacy Policy</a><a href="/terms/">Terms of Use</a>
    </nav>
    <p class="foot-note">Holiday lists cover national public holidays from {DATA['years'][0]} to {DATA['years'][1]}. Regional and bank holidays are not included, and dates marked “estimated” depend on official announcements. Check important dates with an official source.</p>
    <p class="foot-note">© {YEAR} {e(NAME)}</p>
  </div>
</footer>
{scripts}
</body>
</html>
"""
    target = OUT / path.lstrip("/") / "index.html" if path.endswith("/") else OUT / path.lstrip("/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc)
    if not noindex and priority is not None:
        pages.append((path, priority))


def crumbs_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": URL + p} for i, (n, p) in enumerate(items)]}


def crumbs_html(items):
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " / ".join(
        f'<a href="{p}">{e(n)}</a>' if i < len(items) - 1 else e(n) for i, (n, p) in enumerate(items)) + "</nav>"


# ---------------------------------------------------------------- home
def build_home():
    body = f"""
<section class="share" id="sharePanel" hidden>
  <div class="wrap">
    <div class="share-row">
      <label for="shareLink">Link to this plan</label>
      <input class="field num" id="shareLink" readonly>
      <button type="button" class="btn primary" data-action="copy-link">{icon("link")}Copy link</button>
    </div>
    <div class="share-row">
      <label for="openCode">Open a shared plan</label>
      <input class="field" id="openCode" placeholder="Paste a shared link">
      <button type="button" class="btn" data-action="open-code">Open</button>
    </div>
    <p class="hint">The link keeps the locations, the base location, the date and time, and the clock format.</p>
  </div>
</section>
<main class="wrap" id="main">
  <section class="hero">
    <h1>Where are you planning?</h1>
    <p class="lead">Add countries or cities to compare local times, check public holidays and find the hours when everyone is at work. Covers {len(COUNTRIES)} countries and territories.</p>
    <div class="search">
      <div class="search-box">
        {icon("search")}
        <input id="q" type="search" autocomplete="off" placeholder="Search a country or city, e.g. Seoul, Germany, 일본" aria-label="Search a country or city" aria-controls="results">
      </div>
      <div class="results" id="results" role="listbox" hidden></div>
    </div>
    <div class="chips" id="savedChips"></div>
  </section>

  <section class="panel meet" id="meet" aria-live="polite"><div class="empty-state"><span>Loading the planner…</span></div></section>

  <div class="sec-head" style="margin-top:14px;justify-content:flex-end">
    <div class="tools">
      <div class="seg" role="group" aria-label="Clock format">
        <button type="button" id="fmt12" data-action="fmt" data-v="12">12h</button>
        <button type="button" id="fmt24" data-action="fmt" data-v="24">24h</button>
      </div>
      <button type="button" class="btn primary" id="shareToggle" data-action="share-toggle" aria-controls="sharePanel" aria-expanded="false">{icon("share")}Share</button>
    </div>
  </div>

  <section class="sec" id="compare" style="margin-top:8px">
    <div class="sec-head">
      <h2>{icon("clock")}Time Comparison</h2>
      <p class="hint">Click a time to change it. The other locations update to match.</p>
    </div>
    <div class="cards" id="cards"></div>
  </section>

  <div class="split">
    <section class="sec" id="common">
      <div class="sec-head"><h2>{icon("groups")}Common Available Time</h2></div>
      <div class="panel tl-panel" id="timeline"></div>
    </section>
    <section class="sec" id="holidays">
      <div class="sec-head"><h2>{icon("event")}Holiday Information</h2></div>
      <div class="hol-list" id="holList"></div>
    </section>
  </div>

  <div class="home-info">
    <section>
      <h2>How the planner works</h2>
      <p>Each card shows the time at one location for the moment you pick. Change the time on any card, or in the bar at the top, and every other card converts to the same moment. The base location is the one used for the date picker and the day chart.</p>
      <p>A day counts as a working day unless it is a weekend in that country or a national public holiday. Working hours default to 09:00–18:00 and can be changed per location by clicking its time.</p>
      <ul>
        <li><b>Green</b> means a working day inside working hours.</li>
        <li><b>Orange</b> marks a public holiday, a weekend, or a time outside working hours.</li>
        <li><b>Red</b> marks a time before 07:00 or after 22:00.</li>
        <li><b>Blue</b> in the day chart marks the slots when everyone is available.</li>
      </ul>
    </section>
    <section class="faq">
      <h2>Questions</h2>
      {''.join(f'<details><summary>{q}</summary><p>{a}</p></details>' for q, a in FAQ)}
    </section>
  </div>

  <section class="sec">
    <div class="sec-head"><h2>Guides</h2><a href="/guides/" class="hint">All guides</a></div>
    <div class="guide-list">{''.join(guide_card(g) for g in GUIDES)}</div>
  </section>
</main>
<div class="toast" id="toast" role="status" hidden></div>"""
    ld = [
        {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": URL + "/"},
        {"@context": "https://schema.org", "@type": "WebApplication", "name": NAME, "url": URL + "/",
         "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "description": "Compare local times, public holidays and shared working hours across countries and cities."},
        {"@context": "https://schema.org", "@type": "FAQPage",
         "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in FAQ]},
    ]
    layout("/", NAME, f"Compare local times across {len(COUNTRIES)} countries, see public holidays and weekends, and find the working hours that overlap for every location in your meeting.",
           body, section="/", jsonld=ld, scripts='<script src="/assets/app.js" defer></script>',
           head_extra='<link rel="preload" href="/data/world.json" as="fetch" crossorigin>', priority="1.0")


FAQ = [
    ("Does the planner handle daylight saving time?",
     "Yes. Times are converted with your browser's time zone database, which includes daylight saving rules. If you pick a date after a clock change, the offsets shown are the ones that apply on that date."),
    ("Which holidays are included?",
     f"National public holidays for {DATA['years'][0]} to {DATA['years'][1]}. State, provincial and bank holidays are not included. Islamic holidays in some countries are marked “estimated” because the official date depends on the moon sighting."),
    ("Why is Friday a weekend day for some countries?",
     "Several countries, including Saudi Arabia, Qatar, Kuwait, Egypt and Israel, have a Friday–Saturday weekend. The planner uses each country's own weekend. See <a href=\"/guides/weekends-around-the-world/\">weekends around the world</a>."),
    ("Where are my saved locations stored?",
     "In your browser only, using local storage. Nothing is sent to a server, and clearing your browser data removes them."),
    ("How do I share a plan?",
     "Press Share and copy the link. It contains the locations, the date and time, and the clock format, so the other person sees the same plan."),
    ("A holiday date is wrong. How do I report it?",
     "Send the country, the date and a link to an official source through the <a href=\"/contact/\">contact page</a>."),
]


# ---------------------------------------------------------------- guides
def load_guides():
    out = []
    for f in sorted((SRC / "guides").glob("*.html")):
        text = f.read_text()
        m = re.match(r"<!--\s*(\{.*?\})\s*-->\n", text, re.S)
        meta = json.loads(m.group(1))
        meta["body"] = text[m.end():]
        out.append(meta)
    return out


def guide_card(g):
    return f'<a class="panel guide-card" href="/guides/{g["slug"]}/"><h3>{e(g["title"])}</h3><p>{e(g["summary"])}</p></a>'


def table(headers, rows):
    th = "".join(f"<th scope=\"col\">{h}</th>" for h in headers)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="table-wrap"><table class="data"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def transitions(tz, year):
    z = ZoneInfo(tz)
    t = datetime(year, 1, 1, tzinfo=timezone.utc)
    prev = t.astimezone(z).utcoffset()
    found = []
    while t.year == year:
        nxt = t + timedelta(hours=1)
        off = nxt.astimezone(z).utcoffset()
        if off != prev:
            found.append((nxt.astimezone(z), prev, off))
            prev = off
        t = nxt
    return found


def overlap_table():
    pairs = [("seoul", "london"), ("seoul", "new-york"), ("seoul", "san-francisco"), ("tokyo", "berlin"),
             ("singapore", "sydney"), ("jakarta", "london"), ("new-york", "london"), ("new-york", "los-angeles"),
             ("dubai", "london"), ("mumbai", "new-york"), ("sao-paulo", "madrid")]
    city = {c["id"]: c for c in CITIES}
    rows = []
    for a, b in pairs:
        ca, cb = city[a], city[b]
        cells = []
        for month in (1, 7):
            za, zb = ZoneInfo(ca["tz"]), ZoneInfo(cb["tz"])
            day = date(YEAR, month, 15)
            a0 = datetime(day.year, day.month, day.day, 9, tzinfo=za)
            a1 = datetime(day.year, day.month, day.day, 18, tzinfo=za)
            # b's working day that overlaps a's: try the same, previous and next local date
            best = None
            for shift in (-1, 0, 1):
                bd = day + timedelta(days=shift)
                b0 = datetime(bd.year, bd.month, bd.day, 9, tzinfo=zb)
                b1 = datetime(bd.year, bd.month, bd.day, 18, tzinfo=zb)
                s, t = max(a0, b0), min(a1, b1)
                if s < t:
                    best = (s, t)
            if best:
                s, t = best
                hrs = (t - s).total_seconds() / 3600
                cells.append(f'<span class="num">{s.astimezone(za):%H:%M}–{t.astimezone(za):%H:%M} {e(ca["name"])}</span><br><span class="hint num">{s.astimezone(zb):%H:%M}–{t.astimezone(zb):%H:%M} {e(cb["name"])} · {hrs:g} h</span>')
            else:
                diff = (datetime(day.year, day.month, day.day, 12, tzinfo=za).utcoffset() - datetime(day.year, day.month, day.day, 12, tzinfo=zb).utcoffset()).total_seconds() / 3600
                cells.append(f'<span class="badge b-red">No overlap</span><br><span class="hint num">{abs(diff):g} h apart</span>')
        rows.append([f'{flag(ca["cc"], "sm")} {e(ca["name"])} – {flag(cb["cc"], "sm")} {e(cb["name"])}', *cells])
    return table(["Cities", f"Overlap on Jan 15, {YEAR}", f"Overlap on Jul 15, {YEAR}"], rows)


def dst_table():
    regions = [("United States and Canada (most areas)", "America/New_York"), ("United Kingdom and Ireland", "Europe/London"),
               ("European Union", "Europe/Berlin"), ("Israel", "Asia/Jerusalem"), ("Egypt", "Africa/Cairo"),
               ("Chile (mainland)", "America/Santiago"), ("Australia (NSW, Victoria, ACT, Tasmania, South Australia)", "Australia/Sydney"),
               ("New Zealand", "Pacific/Auckland")]
    rows = []
    for label, tz in regions:
        cells = []
        for y in YEARS:
            tr = transitions(tz, y)
            starts = [t for t in tr if t[2] > t[1]]
            ends = [t for t in tr if t[2] < t[1]]
            fmt = lambda t: f'<span class="num">{t[0]:%a, %b %-d}</span>'
            cells.append((", ".join(fmt(t) for t in starts) or "–") + "<br><span class=\"hint\">ends</span> " + (", ".join(fmt(t) for t in ends) or "–"))
        std = min(datetime(YEAR, 1, 15, tzinfo=ZoneInfo(tz)).utcoffset(), datetime(YEAR, 7, 15, tzinfo=ZoneInfo(tz)).utcoffset())
        dst = max(datetime(YEAR, 1, 15, tzinfo=ZoneInfo(tz)).utcoffset(), datetime(YEAR, 7, 15, tzinfo=ZoneInfo(tz)).utcoffset())
        rows.append([e(label), f'<span class="num">{offset_label(std)} → {offset_label(dst)}</span>', *[f'<span class="hint">starts</span> {c}' for c in cells]])
    return table(["Region", "Offset", f"{YEARS[0]}", f"{YEARS[1]}"], rows)


def gap_table():
    ny, ldn = ZoneInfo("America/New_York"), ZoneInfo("Europe/London")
    rows = []
    for y in YEARS:
        d, run = date(y, 1, 1), None
        while d.year == y:
            noon = datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc)
            gap = (noon.astimezone(ldn).utcoffset() - noon.astimezone(ny).utcoffset()).total_seconds() / 3600
            if gap != 5 and run is None:
                run = [d, d, gap]
            elif gap != 5:
                run[1] = d
            elif run:
                rows.append([f'<span class="num">{fmt_date(run[0], False)} – {fmt_date(run[1])}</span>', f"{run[2]:g} hours"])
                run = None
            d += timedelta(days=1)
    return table(["Period", "New York to London"], rows)


NO_DST = [("Brazil", "America/Sao_Paulo", "stopped in 2019"), ("Mexico (most of the country)", "America/Mexico_City", "stopped in 2022"),
          ("Turkey", "Europe/Istanbul", "kept summer time all year from 2016"), ("Russia (Moscow)", "Europe/Moscow", "stopped in 2011"),
          ("Iran", "Asia/Tehran", "stopped in 2022"), ("Jordan and Syria", "Asia/Amman", "kept summer time all year from 2022"),
          ("Paraguay", "America/Asuncion", "kept summer time all year from 2024")]


def no_dst_list():
    items = []
    for label, tz, note in NO_DST:
        z = ZoneInfo(tz)
        offs = {datetime(YEAR, m, 15, tzinfo=z).utcoffset() for m in range(1, 13)}
        assert len(offs) == 1, f"{label} changes clocks in {YEAR}; update NO_DST"
        items.append(f"<li><b>{e(label)}</b>: {note}. Current offset {offset_label(offs.pop())}.</li>")
    return "\n".join(items)


def weekend_table():
    rows = []
    for cc, days in sorted(DATA["weekend"].items(), key=lambda kv: COUNTRIES[kv[0]]["name"]):
        work = [JS_DAYS[d] for d in range(7) if d not in days]
        rows.append([f'{flag(cc, "sm")} <a href="/holidays/{COUNTRIES[cc]["slug"]}/">{e(COUNTRIES[cc]["name"])}</a>',
                     wk_names(days), f"{len(work)} days"])
    return table(["Country", "Weekend", "Working week"], rows)


def build_guides():
    fills = {"OVERLAP_TABLE": overlap_table(), "DST_TABLE": dst_table(), "GAP_TABLE": gap_table(),
             "NO_DST_LIST": no_dst_list(), "WEEKEND_TABLE": weekend_table()}
    for g in GUIDES:
        body = re.sub(r"\{\{(\w+)\}\}", lambda m: fills[m.group(1)], g["body"])
        crumbs = [("Home", "/"), ("Guides", "/guides/"), (g["title"], f"/guides/{g['slug']}/")]
        others = "".join(guide_card(o) for o in GUIDES if o is not g)
        page = f"""<main class="wrap page" id="main">
{crumbs_html(crumbs)}
<article class="prose">
<h1>{e(g["title"])}</h1>
<p class="meta">Updated {fmt_date(date.fromisoformat(g["date"]))}</p>
{body}
</article>
<section class="sec"><div class="sec-head"><h2>More guides</h2></div><div class="guide-list">{others}</div></section>
</main>"""
        art = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"], "description": g["description"],
               "datePublished": g["date"], "dateModified": g["date"], "mainEntityOfPage": URL + f"/guides/{g['slug']}/",
               "author": {"@type": "Organization", "name": NAME}, "publisher": {"@type": "Organization", "name": NAME}}
        layout(f"/guides/{g['slug']}/", g["title"], g["description"], page, section="/guides/", jsonld=[art, crumbs_ld(crumbs)], priority="0.8")
    page = f"""<main class="wrap page" id="main">
{crumbs_html([("Home", "/"), ("Guides", "/guides/")])}
<div class="prose"><h1>Guides</h1><p class="lead">Short, practical articles on scheduling across countries: time differences, clock changes, weekends and public holidays.</p></div>
<div class="guide-list">{''.join(guide_card(g) for g in GUIDES)}</div>
</main>"""
    layout("/guides/", "Guides", "Practical guides to scheduling meetings across time zones, daylight saving time changes, and weekends around the world.",
           page, section="/guides/", jsonld=[crumbs_ld([("Home", "/"), ("Guides", "/guides/")])], priority="0.7")


# ---------------------------------------------------------------- holidays
def off_runs(cc, year, hol):
    """Stretches of 3+ consecutive days off (weekend or holiday) that include a holiday."""
    wk = weekend(cc)
    d, runs, cur = date(year, 1, 1) - timedelta(days=3), [], []
    end = date(year, 12, 31) + timedelta(days=3)
    while d <= end:
        off = js_dow(d) in wk or d.strftime("%Y%m%d") in hol
        if off:
            cur.append(d)
        else:
            if len(cur) >= 3 and any(x.strftime("%Y%m%d") in hol for x in cur) and any(x.year == year for x in cur):
                runs.append((cur[0], cur[-1]))
            cur = []
        d += timedelta(days=1)
    return runs


def zone_rows(cc):
    by_tz = {}
    for c in BY_CC.get(cc, []):
        by_tz.setdefault(c["tz"], []).append(c["name"])
    rows = []
    for tz, names in by_tz.items():
        z = ZoneInfo(tz)
        jan, jul = datetime(YEAR, 1, 15, tzinfo=z).utcoffset(), datetime(YEAR, 7, 15, tzinfo=z).utcoffset()
        if jan == jul:
            off, dst = offset_label(jan), "No"
        else:
            tr = transitions(tz, YEAR)
            off = f"{offset_label(min(jan, jul))} / {offset_label(max(jan, jul))}"
            dst = "Yes: " + ", ".join(f"{'starts' if t[2] > t[1] else 'ends'} {t[0]:%b %-d}" for t in tr)
        rows.append((tz, names, off, dst, jan))
    rows.sort(key=lambda r: -r[4])
    return rows


def build_country(cc):
    info = COUNTRIES[cc]
    name, slug = info["name"], info["slug"]
    hol = DATA["holidays"].get(cc, {})
    cities = BY_CC.get(cc, [])
    primary = cities[0]
    wk = weekend(cc)
    wk_text = wk_names(wk)
    zones = zone_rows(cc)

    sections, facts = [], []
    year_counts = {}
    for y in YEARS:
        keys = sorted(k for k in hol if k.startswith(str(y)))
        year_counts[y] = len(keys)
        if not keys:
            continue
        rows = []
        on_weekend = 0
        for k in keys:
            d = date(int(k[:4]), int(k[4:6]), int(k[6:]))
            is_wk = js_dow(d) in wk
            on_weekend += is_wk
            tag = '<span class="tag b-gray">weekend</span>' if is_wk else ""
            est = e(hol[k]).replace("(estimated)", '<span class="tag b-orange">estimated</span>')
            rows.append(f'<tr class="{"weekend" if is_wk else ""}" data-date="{k}"><td class="num">{fmt_date(d, False)}</td><td>{DAYS[d.weekday()]}</td><td>{est}{tag}</td></tr>')
        runs = off_runs(cc, y, set(keys))
        runs_html = ""
        if runs:
            runs_html = f'<h3>Long breaks in {y}</h3><p>Stretches of three or more days off in a row, counting the weekend ({e(wk_text)}):</p><ul>' + "".join(
                f'<li><span class="num">{fmt_date(a, False)} – {fmt_date(b, False)}</span> ({(b - a).days + 1} days)</li>' for a, b in runs) + "</ul>"
        weekday_count = len(keys) - on_weekend
        summary = (f"{name} has {len(keys)} national public holiday{'s' if len(keys) != 1 else ''} in {y}. "
                   f"{weekday_count} fall on a working day and {on_weekend} on the weekend.")
        sections.append(f"""<section><h2 id="y{y}">{e(name)} public holidays {y}</h2><p>{summary}</p>
<div class="table-wrap"><table class="data holidays"><thead><tr><th scope="col">Date</th><th scope="col">Day</th><th scope="col">Holiday</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
{runs_html}</section>""")

    facts = [
        ("Public holidays " + str(YEARS[0]), str(year_counts.get(YEARS[0], 0))),
        ("Weekend", wk_text),
        ("Time zones", str(len(zones))),
        ("UTC offset", zones[0][2] if len(zones) == 1 else f"{zones[-1][2].split(' / ')[0]} to {zones[0][2].split(' / ')[-1]}"),
    ]
    zone_html = table(["Time zone", "Cities", "UTC offset", f"Daylight saving in {YEAR}"],
                      [[f'<span class="num">{e(tz)}</span>', e(", ".join(n)), f'<span class="num">{off}</span>', e(dst)] for tz, n, off, dst, _ in zones])
    estimated = any("(estimated)" in v for v in hol.values())
    notes = []
    if estimated:
        notes.append("Dates marked <b>estimated</b> follow the lunar calendar. The government usually confirms them shortly before the holiday.")
    if cc in DATA["weekend"]:
        notes.append(f"The working week in {e(name)} runs " + ", ".join(JS_DAYS[d] for d in range(7) if d not in wk) + ". See <a href=\"/guides/weekends-around-the-world/\">weekends around the world</a>.")
    if len(zones) > 1:
        notes.append(f"{e(name)} has {len(zones)} time zones. Pick the city closest to the person you are meeting in the planner.")

    title = f"{name} Public Holidays {YEARS[0]} and {YEARS[1]}"
    desc = (f"All national public holidays in {name} for {YEARS[0]} and {YEARS[1]}, with weekdays, long weekends, "
            f"the weekend days ({wk_text}) and local time zones.")
    crumbs = [("Home", "/"), ("Public holidays", "/holidays/"), (name, f"/holidays/{slug}/")]
    tz_attr = e(primary["tz"])
    page = f"""<main class="wrap page" id="main">
{crumbs_html(crumbs)}
<div class="prose">
<div class="country-head">{flag(cc)}<h1 style="margin:0">{e(name)} public holidays {YEARS[0]} and {YEARS[1]}</h1></div>
<p class="clock-now" data-tz="{tz_attr}" data-cc="{cc}">Local time in {e(primary["name"])}: <b class="num js-clock">–</b> <span class="js-status"></span></p>
<div class="facts">{''.join(f'<div class="panel fact"><div class="k">{k}</div><div class="v num">{e(v)}</div></div>' for k, v in facts)}</div>
<div class="cta"><a class="btn primary" href="/?add={primary["id"]}">{icon("groups")}Plan a meeting with {e(primary["name"])}</a><a class="btn" href="#y{YEARS[1]}">{YEARS[1]} holidays</a></div>
{''.join(f'<p class="note">{n}</p>' for n in notes)}
{''.join(sections) or '<p>No national public holiday data is available for this country.</p>'}
<section><h2>Time zones in {e(name)}</h2>{zone_html}</section>
</div>
</main>"""
    event_ld = {"@context": "https://schema.org", "@type": "ItemList", "name": title,
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{hol[k]} ({k[:4]}-{k[4:6]}-{k[6:]})"}
                                    for i, k in enumerate(sorted(k for k in hol if int(k[:4]) in YEARS))]}
    layout(f"/holidays/{slug}/", title, desc, page, section="/holidays/", jsonld=[crumbs_ld(crumbs), event_ld],
           scripts=f'<script>window.HOLIDAYS={json.dumps({k: v for k, v in hol.items() if int(k[:4]) >= YEARS[0] - 1})};window.WEEKEND={json.dumps(wk)};</script><script src="/assets/site.js" defer></script>',
           priority="0.6")


def build_holiday_index():
    order = sorted(COUNTRIES, key=lambda c: COUNTRIES[c]["name"])
    groups = {}
    for cc in order:
        letter = re.sub(r"[^A-Z]", "", COUNTRIES[cc]["slug"][:1].upper()) or "#"
        groups.setdefault(letter, []).append(cc)
    az = "".join(f'<a href="#letter-{l}">{l}</a>' for l in groups)
    lists = "".join(
        f'<h2 class="letter" id="letter-{l}">{l}</h2><div class="country-grid">' + "".join(
            f'<a href="/holidays/{COUNTRIES[cc]["slug"]}/" data-name="{e(COUNTRIES[cc]["name"].lower())} {e(COUNTRIES[cc]["ko"])}">{flag(cc)}{e(COUNTRIES[cc]["name"])}</a>' for cc in ccs) + "</div>"
        for l, ccs in groups.items())
    crumbs = [("Home", "/"), ("Public holidays", "/holidays/")]
    page = f"""<main class="wrap page" id="main">
{crumbs_html(crumbs)}
<div class="prose"><h1>Public holidays by country</h1>
<p class="lead">National public holidays for {YEARS[0]} and {YEARS[1]} in {len(COUNTRIES)} countries and territories, with each country's weekend days and time zones.</p></div>
<div class="search-box filter"><svg class="icon" aria-hidden="true"><use href="#i-search"/></svg><input id="countryFilter" type="search" placeholder="Filter countries" aria-label="Filter countries"></div>
<nav class="az" aria-label="Jump to letter">{az}</nav>
{lists}
</main>"""
    layout("/holidays/", f"Public Holidays {YEARS[0]} and {YEARS[1]} by Country",
           f"Find national public holidays for {YEARS[0]} and {YEARS[1]} in {len(COUNTRIES)} countries, with weekend days and time zones for each.",
           page, section="/holidays/", jsonld=[crumbs_ld(crumbs)], scripts='<script src="/assets/site.js" defer></script>', priority="0.9")


# ---------------------------------------------------------------- static pages
def build_static():
    email = e(CFG["contact_email"])
    owner = e(CFG["owner_name"]) if CFG.get("owner_name") else None
    run_by = f"{NAME} is an independent project built and run by {owner}." if owner else f"{NAME} is an independent project."
    updated = fmt_date(TODAY)

    about = f"""<h1>About</h1>
<p>{run_by} It is made for anyone who plans calls or deadlines with people in other countries and needs to check local time, weekends and public holidays on every side at once.</p>
<h2>What the site does</h2>
<ul>
<li>Converts one moment into local time for every location you add, including the date and UTC offset.</li>
<li>Marks each location's day as a working day, weekend or public holiday, using that country's own weekend.</li>
<li>Finds the hours when everyone's working day overlaps.</li>
<li>Lists national public holidays for {len(COUNTRIES)} countries and territories.</li>
</ul>
<h2>Where the data comes from</h2>
<p><b>Time zones</b> come from the IANA time zone database. The planner uses the copy built into your browser, so daylight saving changes are applied for the date you pick.</p>
<p><b>Public holidays</b> come from the open-source <a href="https://github.com/vacanza/holidays" rel="noopener">python-holidays</a> project, which is maintained by volunteers and checked against official government sources. The site includes national holidays only. Regional holidays, bank holidays and one-off days announced at short notice may be missing.</p>
<p><b>Flags</b> come from the open-source <a href="https://github.com/lipis/flag-icons" rel="noopener">flag-icons</a> set.</p>
<h2>Accuracy</h2>
<p>Holiday dates are checked when the data is updated, but governments sometimes add or move holidays during the year. For anything important, such as a contract deadline or a flight, confirm the date with an official source. If you find a mistake, please <a href="/contact/">let us know</a>.</p>
<h2>Contact</h2>
<p>Email <a href="mailto:{email}">{email}</a>.</p>"""

    contact = f"""<h1>Contact</h1>
<p>Questions, corrections and suggestions are welcome.</p>
<p class="panel" style="padding:14px 16px"><b>Email:</b> <a href="mailto:{email}">{email}</a></p>
<h2>Reporting a wrong holiday</h2>
<p>Please include:</p>
<ul><li>the country and, if it matters, the region</li><li>the date and the holiday name</li><li>a link to an official source, such as a government announcement</li></ul>
<p>Corrections usually go live with the next data update.</p>
<h2>Requests</h2>
<p>If a city you need is missing from the search, tell us the city and country. We add cities that are in a different time zone from the ones already listed, or that people search for often.</p>"""

    privacy = f"""<h1>Privacy Policy</h1>
<p class="meta">Last updated {updated}</p>
<p>This policy explains what information {e(NAME)} (“the site”, “we”) collects and how it is used.</p>
<h2>Information you enter</h2>
<p>The locations, times and settings you choose in the planner are processed in your browser. Your saved locations and last plan are stored in your browser's local storage so they are there on your next visit. They are not sent to us. You can remove them at any time by clearing your browser's site data.</p>
<p>A share link contains the plan itself (the locations, date, time and clock format). Anyone you send the link to can see that plan.</p>
<h2>Server logs</h2>
<p>Like most websites, our hosting provider records standard request logs, such as IP address, browser type, the page requested and the time of the request. These logs are used to keep the site running and secure.</p>
<h2>Cookies and advertising</h2>
<p>We use Google AdSense to show advertising. Third-party vendors, including Google, use cookies to serve ads based on your previous visits to this site and other websites.</p>
<p>Google's use of advertising cookies enables it and its partners to serve ads to you based on your visits to this site and/or other sites on the internet. You can opt out of personalised advertising in <a href="https://adssettings.google.com" rel="noopener">Google Ads Settings</a>. You can also opt out of some third-party vendors' use of cookies for personalised advertising at <a href="https://www.aboutads.info/choices/" rel="noopener">www.aboutads.info</a>.</p>
<p>For more on how Google uses data, see <a href="https://policies.google.com/technologies/partner-sites" rel="noopener">How Google uses information from sites or apps that use its services</a>.</p>
<p>Visitors from the European Economic Area, the United Kingdom and Switzerland are asked for consent before personalised ads are shown. You can change your choice at any time through the privacy settings link shown with the consent message.</p>
<h2>Fonts</h2>
<p>The site loads the Inter font from Google Fonts. Your browser connects to Google's servers to download it.</p>
<h2>Children</h2>
<p>The site is not directed at children under 13, and we do not knowingly collect personal information from them.</p>
<h2>Changes</h2>
<p>We may update this policy. The date at the top shows when it last changed.</p>
<h2>Contact</h2>
<p>Questions about this policy: <a href="mailto:{email}">{email}</a>.</p>"""

    terms = f"""<h1>Terms of Use</h1>
<p class="meta">Last updated {updated}</p>
<p>By using {e(NAME)} you agree to these terms.</p>
<h2>Information only</h2>
<p>The site provides time zone conversions and public holiday lists for general information. We work to keep them accurate, but we do not guarantee that every date, time or holiday is correct or complete. Check important dates with an official source before relying on them.</p>
<h2>No liability</h2>
<p>The site is provided “as is”. We are not responsible for any loss that results from using it, including missed meetings, travel costs or business losses.</p>
<h2>Acceptable use</h2>
<p>Do not use automated tools to download the site in bulk, overload it, or interfere with its operation.</p>
<h2>Third-party content</h2>
<p>The site shows advertising from third parties and links to other websites. We are not responsible for their content or practices.</p>
<h2>Changes</h2>
<p>We may change these terms. The date at the top shows when they last changed.</p>
<h2>Contact</h2>
<p><a href="mailto:{email}">{email}</a></p>"""

    for path, title, desc, body, prio in [
        ("/about/", "About", f"What {NAME} does, where its time zone and holiday data comes from, and how to report a mistake.", about, "0.5"),
        ("/contact/", "Contact", f"Contact {NAME} with questions, holiday corrections or city requests.", contact, "0.4"),
        ("/privacy/", "Privacy Policy", f"How {NAME} handles your data, cookies and advertising.", privacy, "0.3"),
        ("/terms/", "Terms of Use", f"Terms for using {NAME}.", terms, "0.3"),
    ]:
        crumbs = [("Home", "/"), (title, path)]
        layout(path, title, desc, f'<main class="wrap page" id="main">{crumbs_html(crumbs)}<article class="prose">{body}</article></main>',
               section=path if path == "/about/" else "", jsonld=[crumbs_ld(crumbs)], priority=prio)

    layout("/404.html", "Page not found", "The page you asked for does not exist.",
           '<main class="wrap page" id="main"><div class="prose"><h1>Page not found</h1><p>The page you asked for does not exist or has moved.</p>'
           '<div class="cta"><a class="btn primary" href="/">Open the planner</a><a class="btn" href="/holidays/">Browse public holidays</a></div></div></main>',
           noindex=True)


# ---------------------------------------------------------------- sitemap etc.
def build_meta_files():
    urls = "".join(f"<url><loc>{URL}{p}</loc><lastmod>{TODAY.isoformat()}</lastmod><priority>{pr}</priority></url>\n" for p, pr in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {URL}/sitemap.xml\n")
    ads = OUT / "ads.txt"
    if CFG.get("adsense_client"):
        pub = CFG["adsense_client"].replace("ca-", "")
        ads.write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")
    elif ads.exists():
        ads.unlink()


def main():
    for sub in ["holidays", "guides", "about", "contact", "privacy", "terms", "assets", "data"]:
        shutil.rmtree(OUT / sub, ignore_errors=True)
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    for f in ["style.css", "app.js", "site.js"]:
        shutil.copy(SRC / f, OUT / "assets" / f)
    for f in ["favicon.svg", "apple-touch-icon.png", "og.png"]:
        if (SRC / f).exists():
            shutil.copy(SRC / f, OUT / ("assets/og.png" if f == "og.png" else f))
    shutil.copy(ROOT / "data" / "world.json", OUT / "data" / "world.json")

    build_home()
    build_guides()
    build_holiday_index()
    for cc in sorted(COUNTRIES, key=lambda c: COUNTRIES[c]["name"]):
        build_country(cc)
    build_static()
    build_meta_files()
    print(f"Built {len(pages)} indexable pages into {OUT}")


GUIDES = load_guides()
if __name__ == "__main__":
    main()
