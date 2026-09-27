"""Build data/world.json: countries, cities, time zones, public holidays and weekends.

Needs: pip install holidays babel
Run:   python3 scripts/gen_data.py
"""
import json, re, unicodedata
from pathlib import Path
import holidays
from babel import Locale
from curated_cities import C as CURATED

ROOT = Path(__file__).resolve().parent.parent
YEARS = list(range(2025, 2029))
EN, KO = Locale("en").territories, Locale("ko").territories

# Extra well-known cities that are not time-zone names.
EXTRA = [
    ("canberra", "Canberra", "AU", "Australia/Sydney", "capital"),
    ("adelaide", "Adelaide", "AU", "Australia/Adelaide", ""),
    ("ottawa", "Ottawa", "CA", "America/Toronto", "capital"),
    ("calgary", "Calgary", "CA", "America/Edmonton", ""),
    ("brasilia", "Brasília", "BR", "America/Sao_Paulo", "brasilia capital"),
    ("ankara", "Ankara", "TR", "Europe/Istanbul", "capital"),
    ("abuja", "Abuja", "NG", "Africa/Lagos", "capital"),
    ("pretoria", "Pretoria", "ZA", "Africa/Johannesburg", "capital"),
    ("wellington", "Wellington", "NZ", "Pacific/Auckland", "capital"),
    ("christchurch", "Christchurch", "NZ", "Pacific/Auckland", ""),
    ("bern", "Bern", "CH", "Europe/Zurich", "capital"),
    ("geneva", "Geneva", "CH", "Europe/Zurich", ""),
    ("rabat", "Rabat", "MA", "Africa/Casablanca", "capital"),
    ("islamabad", "Islamabad", "PK", "Asia/Karachi", "capital"),
    ("lahore", "Lahore", "PK", "Asia/Karachi", ""),
    ("jerusalem", "Jerusalem", "IL", "Asia/Jerusalem", ""),
    ("kyoto", "Kyoto", "JP", "Asia/Tokyo", ""),
    ("fukuoka", "Fukuoka", "JP", "Asia/Tokyo", ""),
    ("incheon", "Incheon", "KR", "Asia/Seoul", "인천"),
    ("jeju", "Jeju", "KR", "Asia/Seoul", "제주"),
    ("daegu", "Daegu", "KR", "Asia/Seoul", "대구"),
    ("surabaya", "Surabaya", "ID", "Asia/Jakarta", ""),
    ("bandung", "Bandung", "ID", "Asia/Jakarta", ""),
    ("yogyakarta", "Yogyakarta", "ID", "Asia/Jakarta", "jogja"),
    ("cebu", "Cebu", "PH", "Asia/Manila", ""),
    ("chennai", "Chennai", "IN", "Asia/Kolkata", "madras"),
    ("hyderabad", "Hyderabad", "IN", "Asia/Kolkata", ""),
    ("guangzhou", "Guangzhou", "CN", "Asia/Shanghai", "canton"),
    ("chengdu", "Chengdu", "CN", "Asia/Shanghai", ""),
    ("hamburg", "Hamburg", "DE", "Europe/Berlin", ""),
    ("lyon", "Lyon", "FR", "Europe/Paris", ""),
    ("marseille", "Marseille", "FR", "Europe/Paris", ""),
    ("rotterdam", "Rotterdam", "NL", "Europe/Amsterdam", ""),
    ("krakow", "Kraków", "PL", "Europe/Warsaw", "krakow"),
    ("porto", "Porto", "PT", "Europe/Lisbon", ""),
    ("seville", "Seville", "ES", "Europe/Madrid", "sevilla"),
    ("florence", "Florence", "IT", "Europe/Rome", "firenze"),
    ("birmingham", "Birmingham", "GB", "Europe/London", "uk"),
    ("austin", "Austin", "US", "America/Chicago", "usa texas"),
    ("las-vegas", "Las Vegas", "US", "America/Los_Angeles", "usa nevada"),
    ("san-diego", "San Diego", "US", "America/Los_Angeles", "usa"),
    ("philadelphia", "Philadelphia", "US", "America/New_York", "usa"),
    ("guadalajara", "Guadalajara", "MX", "America/Mexico_City", ""),
    ("medellin", "Medellín", "CO", "America/Bogota", "medellin"),
    ("jeddah", "Jeddah", "SA", "Asia/Riyadh", ""),
    ("giza", "Giza", "EG", "Africa/Cairo", ""),
    ("accra", "Accra", "GH", "Africa/Accra", ""),
    ("addis-ababa", "Addis Ababa", "ET", "Africa/Addis_Ababa", ""),
    ("st-petersburg", "Saint Petersburg", "RU", "Europe/Moscow", "st petersburg"),
    ("chiang-mai", "Chiang Mai", "TH", "Asia/Bangkok", ""),
    ("phuket", "Phuket", "TH", "Asia/Bangkok", ""),
    ("da-nang", "Da Nang", "VN", "Asia/Ho_Chi_Minh", "danang"),
    ("penang", "Penang", "MY", "Asia/Kuala_Lumpur", "george town"),
]

def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def country_name(cc):
    fix = {"CI": "Côte d’Ivoire", "US": "United States", "GB": "United Kingdom", "KR": "South Korea",
           "KP": "North Korea", "RU": "Russia", "TW": "Taiwan", "HK": "Hong Kong", "MO": "Macao",
           "CZ": "Czechia", "TR": "Turkey", "PS": "Palestine", "VN": "Vietnam", "LA": "Laos", "SY": "Syria",
           "IR": "Iran", "BO": "Bolivia", "VE": "Venezuela", "TZ": "Tanzania", "MD": "Moldova", "FM": "Micronesia"}
    return fix.get(cc) or EN.get(cc) or cc

# --- zones from the system tz database
zones = {}
for line in Path("/usr/share/zoneinfo/zone.tab").read_text().splitlines():
    if line.startswith("#") or not line.strip():
        continue
    cols = line.split("\t")
    cc, tz = cols[0], cols[2]
    if cc == "AQ":
        continue
    zones.setdefault(cc, []).append(tz)

cities, seen = [], set()
def add(cid, name, cc, tz, al=""):
    key = (cc, slug(name))
    if key in seen:
        return
    seen.add(key)
    base = cid
    n = 2
    while any(c[0] == cid for c in cities):
        cid = f"{base}-{n}"; n += 1
    cities.append([cid, name, cc, tz, al])

for cc, (_, lst) in CURATED.items():
    for (cid, name, tz, al) in lst:
        add(cid, name, cc, tz, al)
for (cid, name, cc, tz, al) in EXTRA:
    add(cid, name, cc, tz, al)
for cc, tzs in zones.items():
    for tz in tzs:
        parts = tz.split("/")
        if len(parts) == 3 and parts[1] != "Argentina":
            continue
        name = parts[-1].replace("_", " ")
        name = {"Kiev": "Kyiv", "Ho Chi Minh": "Ho Chi Minh City", "Calcutta": "Kolkata"}.get(name, name)
        add(slug(name), name, cc, tz, "")

# --- countries, holidays, weekends
supported = {k for k in holidays.list_supported_countries() if len(k) == 2}
countries, hol, weekend = {}, {}, {}
for cc in sorted(zones):
    name = country_name(cc)
    ko = KO.get(cc, "") + {"KR": " 한국 남한", "KP": " 북한", "US": " 미국", "GB": " 영국", "CN": " 중국", "TW": " 대만"}.get(cc, "")
    countries[cc] = {"name": name, "ko": ko.strip(), "slug": slug(name)}
    if cc not in supported:
        continue
    try:
        probe = holidays.country_holidays(cc, years=YEARS[0])
    except Exception:
        continue
    langs = getattr(probe, "supported_languages", ()) or ()
    lang = next((l for l in ("en_US", "en_GB", "en") if l in langs), None)
    h = holidays.country_holidays(cc, years=YEARS, language=lang) if lang else holidays.country_holidays(cc, years=YEARS)
    names = {d.strftime("%Y%m%d"): n for d, n in sorted(h.items())}
    if lang is None and any(ord(ch) > 0x24F for n in names.values() for ch in n):
        continue  # names only in a non-Latin script
    hol[cc] = names
    # The library's weekend is for moving holidays to weekdays. Only trust it for
    # Friday-based working weeks; Sunday-only entries are usually Sat-Sun offices.
    wk = sorted((d + 1) % 7 for d in probe.weekend)
    if 5 in wk:
        weekend[cc] = wk
weekend["NP"] = [6]  # Nepal: Saturday only

out = {"years": [YEARS[0], YEARS[-1]], "countries": countries, "cities": cities, "holidays": hol, "weekend": weekend}
(ROOT / "data" / "world.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"{len(countries)} countries, {len(cities)} cities, holidays for {len(hol)}, custom weekends {weekend}")
