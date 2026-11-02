#!/usr/bin/env python3
"""Morning reading list helper.

Subcommands:
  plan    [YYYY-MM-DD]          Print the day's reading plan (JSON) per the rules.
  weather [YYYY-MM-DD]          Fetch Boston (+ travel location) weather as JSON.
  render  content.json          Render the email HTML from a content JSON file.

Only the standard library is used so it runs anywhere.
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.abspath(__file__))
ET = ZoneInfo("America/New_York")
BOSTON = {"name": "Boston, MA", "latitude": 42.3601, "longitude": -71.0589,
          "timezone": "America/New_York"}

WMO = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
       45: "Fog", 48: "Freezing fog", 51: "Light drizzle", 53: "Drizzle",
       55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
       61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain",
       67: "Freezing rain", 71: "Light snow", 73: "Snow", 75: "Heavy snow",
       77: "Snow grains", 80: "Rain showers", 81: "Rain showers",
       82: "Violent showers", 85: "Snow showers", 86: "Heavy snow showers",
       95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ hail"}


def today_et():
    return dt.datetime.now(ET).date()


def parse_date(args):
    return dt.date.fromisoformat(args[0]) if args else today_et()


def plan(d: dt.date) -> dict:
    """Apply the user's rules for which office each reading comes from."""
    psalm_office = "Evening" if d.month % 2 == 1 else "Morning"
    lesson_office = "Evening" if d.year % 2 == 1 else "Morning"
    return {
        "date": d.isoformat(),
        "date_long": d.strftime("%A, %B %-d, %Y"),
        "daily_office": {
            "site": "https://dailyofficeforall.com",
            "settings": {"psalter": "30-day", "version": "Regular",
                         "praying": "By myself",
                         "lords_prayer": "Traditional"},
            "psalms_from": psalm_office,          # odd month -> Evening
            "psalter_day": d.day,                 # 30-day psalter day
            "ot_nt_from": lesson_office,          # odd year -> Evening
            "base_office": "Morning",
        },
        "proverbs": {"chapter": d.day, "translation": "NIV"},
        "murray": {"lesson": d.day,
                   "book": "With Christ in the School of Prayer (Andrew Murray, 1885)",
                   "summary_file": f"murray/lesson-{d.day:02d}.md"},
    }


def _get_json(url, tries=6):
    import time
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "personal-morning-brief"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # rate limits (429) and timeouts are common
            if i == tries - 1:
                raise
            time.sleep(min(60, 5 * 2 ** i))


def geocode(name):
    q = urllib.parse.urlencode({"name": name.split(",")[0].strip(), "count": 10})
    res = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{q}").get("results") or []
    if not res:
        raise SystemExit(f"Could not geocode {name!r}")
    hint = name.split(",")[1].strip().lower() if "," in name else ""
    for r in res:
        if hint and hint in (str(r.get("admin1", "")) + " " + str(r.get("country_code", "")) + " " + str(r.get("country", ""))).lower():
            break
    else:
        r = res[0]
    return {"name": name, "latitude": r["latitude"], "longitude": r["longitude"],
            "timezone": r.get("timezone", "auto"), "admin1": r.get("admin1"),
            "country_code": r.get("country_code")}


def travel_location(d: dt.date):
    """Return the configured travel location if active on date d and outside MA."""
    path = os.path.join(ROOT, "config", "location.json")
    try:
        cfg = json.load(open(path))
    except FileNotFoundError:
        return None
    loc = cfg.get("current")
    if not loc or not loc.get("name"):
        return None
    if loc.get("until") and d > dt.date.fromisoformat(loc["until"]):
        return None
    if loc.get("from") and d < dt.date.fromisoformat(loc["from"]):
        return None
    g = geocode(loc["name"])
    if g.get("country_code") == "US" and g.get("admin1") == "Massachusetts":
        return None
    return g


def _clock(iso):
    return dt.datetime.fromisoformat(iso).strftime("%-I:%M %p").lower()


def forecast(loc, start=None):
    q = urllib.parse.urlencode({
        "latitude": loc["latitude"], "longitude": loc["longitude"],
        "timezone": loc.get("timezone", "auto"),
        **({"start_date": start.isoformat(), "end_date": (start + dt.timedelta(days=13)).isoformat()}
           if start else {"forecast_days": 14}),
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "daily": ",".join(["weather_code", "temperature_2m_max", "temperature_2m_min",
                           "precipitation_probability_max", "precipitation_sum",
                           "wind_speed_10m_max", "sunrise", "sunset"]),
    })
    data = _get_json(f"https://api.open-meteo.com/v1/forecast?{q}")["daily"]
    days = []
    for i, day in enumerate(data["time"]):
        days.append({
            "date": day,
            "summary": WMO.get(data["weather_code"][i], "—"),
            "high": round(data["temperature_2m_max"][i]),
            "low": round(data["temperature_2m_min"][i]),
            "precip_chance": data["precipitation_probability_max"][i],
            "precip_in": data["precipitation_sum"][i],
            "wind_mph": round(data["wind_speed_10m_max"][i]),
            "sunrise": _clock(data["sunrise"][i]), "sunset": _clock(data["sunset"][i]),
        })
    return {"location": loc["name"], "days": days}


def forecast_nws(loc, start=None):
    """Fallback: US National Weather Service (7 days, US locations only)."""
    pt = _get_json(f"https://api.weather.gov/points/{loc['latitude']:.4f},{loc['longitude']:.4f}")
    periods = _get_json(pt["properties"]["forecast"])["properties"]["periods"]
    days = {}
    for per in periods:
        date = per["startTime"][:10]
        d = days.setdefault(date, {"date": date, "summary": None, "high": None, "low": None,
                                   "precip_chance": None, "precip_in": None, "wind_mph": None,
                                   "sunrise": "—", "sunset": "—"})
        pc = (per.get("probabilityOfPrecipitation") or {}).get("value")
        if pc is not None:
            d["precip_chance"] = max(pc, d["precip_chance"] or 0)
        wind = [int(x) for x in re.findall(r"\d+", per.get("windSpeed", ""))]
        if wind:
            d["wind_mph"] = max(max(wind), d["wind_mph"] or 0)
        if per["isDaytime"]:
            d["high"], d["summary"] = per["temperature"], per["shortForecast"]
        else:
            d["low"] = per["temperature"]
            d["summary"] = d["summary"] or per["shortForecast"]
    kept = [x for x in days.values() if not start or x["date"] >= start.isoformat()]
    return {"location": loc["name"], "days": kept,
            "note": "14-day source unavailable this morning; showing the 7-day National Weather Service forecast."}


def forecast_any(loc, start=None):
    try:
        return forecast(loc, start)
    except Exception:
        if loc.get("country_code", "US") == "US":
            return forecast_nws(loc, start)
        raise


def weather(d: dt.date):
    out = [forecast_any(BOSTON, d)]
    t = travel_location(d)
    if t:
        out.append(forecast_any(t, d))
    return out


# ---------------------------------------------------------------- rendering

CSS = """
body{margin:0;background:#f6f3ee;font-family:Georgia,'Times New Roman',serif;color:#2b2622}
.wrap{max-width:680px;margin:0 auto;padding:20px 16px}
h1{font-size:24px;margin:0 0 4px}
.sub{color:#7a6f64;font-size:14px;margin-bottom:18px}
.card{background:#fff;border-radius:10px;padding:18px 20px;margin:0 0 16px;border:1px solid #e7e0d6}
h2{font-size:18px;margin:0 0 4px;color:#5b3a1e}
.meta{font-size:13px;color:#7a6f64;margin-bottom:10px;font-family:Helvetica,Arial,sans-serif}
h3{font-size:15px;margin:16px 0 4px}
h3.sec{font-size:13px;margin:22px 0 6px;letter-spacing:.08em;text-transform:uppercase;color:#5b3a1e;border-bottom:1px solid #eee;padding-bottom:3px}
p{line-height:1.55;margin:0 0 10px}
.verse sup{color:#9a8b7c;font-size:10px;margin-right:2px}
table{border-collapse:collapse;width:100%;font-family:Helvetica,Arial,sans-serif;font-size:13px}
th,td{padding:5px 4px;border-bottom:1px solid #eee;text-align:left}
th{color:#7a6f64;font-weight:600}
.today{font-family:Helvetica,Arial,sans-serif;font-size:15px;margin-bottom:10px}
a{color:#5b3a1e}
"""


def esc(s):
    return html.escape(str(s))


def paragraphs(text):
    out = []
    for para in str(text).split("\n\n"):
        if para.strip():
            h = esc(para.strip()).replace("\n", "<br>")
            h = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h)
            h = re.sub(r"(?<![\w*])\*(?!\*)(.+?)\*(?![\w*])", r"<i>\1</i>", h)
            h = re.sub(r"(^|<br>)- ", r"\1&bull; ", h)
            h = re.sub(r"\[\[(\d+)\]\]\s*", r"<sup>\1</sup>", h)
            out.append(f"<p>{h}</p>")
    return "".join(out)


def render_reading(r):
    ref = esc(r.get('reference', ''))
    if r.get("url"):
        ref = f"<a href='{esc(r['url'])}'>{ref}</a>"
    out = f"<h3>{esc(r.get('label',''))}: {ref}</h3>"
    if r.get("text"):
        out += f"<div class='verse'>{paragraphs(r['text'])}</div>"
    return out


def render_weather(w):
    def v(x, suffix=""):
        return "—" if x is None else f"{x}{suffix}"
    d0 = w["days"][0]
    rows = "".join(
        f"<tr><td>{dt.date.fromisoformat(x['date']).strftime('%a %-m/%-d')}</td>"
        f"<td>{esc(x['summary'])}</td><td>{v(x['high'], '°')} / {v(x['low'], '°')}</td>"
        f"<td>{v(x['precip_chance'], '%')}</td>"
        f"<td>{v(x['wind_mph'], ' mph')}</td></tr>" for x in w["days"])
    note = f"<div class='meta'>{esc(w['note'])}</div>" if w.get("note") else ""
    return (f"<div class='card'><h2>Weather: {esc(w['location'])}</h2>{note}"
            f"<div class='today'><b>Today:</b> {esc(d0['summary'])}, high {v(d0['high'], '°F')}, "
            f"low {v(d0['low'], '°F')}, {v(d0['precip_chance'], '%')} chance of precipitation"
            f"{'' if d0['precip_in'] is None else ' (' + str(d0['precip_in']) + ' in)'}, "
            f"wind up to {v(d0['wind_mph'], ' mph')}."
            f"{'' if d0['sunrise'] == '—' else ' Sunrise ' + d0['sunrise'] + ', sunset ' + d0['sunset'] + '.'}</div>"
            f"<table><tr><th>Day</th><th>Conditions</th><th>Hi / Lo</th><th>Precip</th><th>Wind</th></tr>"
            f"{rows}</table></div>")


def render(c):
    p = c["plan"]
    o = c["office"]
    parts = [f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='wrap'>",
             f"<h1>Morning Reading</h1><div class='sub'>{esc(p['date_long'])}"
             f"{' · ' + esc(o['day_title']) if o.get('day_title') else ''}</div>"]
    # 1. Daily Office, in the order of the office
    L = o.get("liturgy") or {}
    inv = L.get("invitatory") or {}

    def sec(title, body, sub=""):
        if body:
            parts.append(f"<h3 class='sec'>{esc(title)}</h3>"
                         + (f"<div class='meta'>{esc(sub)}</div>" if sub else "")
                         + paragraphs(body))

    parts.append("<div class='card'><h2>1. Morning Prayer</h2>"
                 f"<div class='meta'>dailyofficeforall.com · 30-day psalter · praying by myself · "
                 f"psalms from {esc(p['daily_office']['psalms_from'])} Prayer, lessons from "
                 f"{esc(p['daily_office']['ot_nt_from'])} Prayer · readings in the NIV</div>")
    if o.get("note"):
        parts.append(f"<p><i>{esc(o['note'])}</i></p>")
    sec("Opening Verse", L.get("opening"))
    sec("Confession of Sin", L.get("confession"))
    if inv:
        sec("Invitatory", inv.get("versicles"))
        sec(inv.get("psalm_title") or "Invitatory Psalm", inv.get("psalm_text"))
    if o.get("readings"):
        parts.append("<h3 class='sec'>The Lessons</h3>")
    for r in o.get("readings", []):
        parts.append(render_reading(r))
    sec("The Apostles' Creed", L.get("creed"))
    sec("The Lord's Prayer", L.get("lords_prayer") or o.get("lords_prayer"))
    sec("The Suffrages", L.get("suffrages"))
    sec("The Collect of the Day", L.get("collect"))
    sec("Collects for Peace and Grace", L.get("peace_grace"))
    sec("Prayer for Mission", L.get("mission"),
        f"Prayer {L.get('mission_number')} of 3 (rotates daily)" if L.get("mission_number") else "")
    if o.get("url"):
        parts.append(f"<p class='meta'><a href='{esc(o['url'])}'>Open the full office</a></p>")
    parts.append("</div>")
    # 2. Proverbs
    pv = c["proverbs"]
    parts.append(f"<div class='card'><h2>2. Proverbs {p['proverbs']['chapter']} (NIV)</h2>"
                 f"<div class='verse'>{paragraphs(pv['text'])}</div>"
                 f"{'<p class=meta><a href=' + chr(39) + esc(pv['url']) + chr(39) + '>Read on Bible Gateway</a></p>' if pv.get('url') else ''}</div>")
    # 3. Murray
    m = c["murray"]
    parts.append(f"<div class='card'><h2>3. With Christ in the School of Prayer: Lesson {p['murray']['lesson']}</h2>"
                 f"<div class='meta'>{esc(m.get('title',''))}</div>{paragraphs(m['summary'])}</div>")
    # 4. Weather
    parts.append("<h2 style='margin:20px 0 10px'>4. Weather</h2>")
    for w in c["weather"]:
        parts.append(render_weather(w))
    parts.append("</div></body></html>")
    return "".join(parts)


def main():
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("plan", [])
    if cmd == "plan":
        print(json.dumps(plan(parse_date(args)), indent=2))
    elif cmd == "weather":
        print(json.dumps(weather(parse_date(args)), indent=2))
    elif cmd == "render":
        print(render(json.load(open(args[0]))))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
