# Morning Reading List: run instructions

The scheduled task follows these steps every day. It must finish before 4:00 am
US Eastern and send the email to **dvslice@gmail.com**.

## Rules (computed by `python3 brief.py plan`)

| Item | Rule |
|---|---|
| Date | Today in America/New_York |
| Daily Office source | https://dailyofficeforall.com (ACNA 2019 Prayer Book). Settings: **30-day psalter**, **regular** version, **praying by myself**, **traditional** Lord's Prayer. The site gives references; the psalm and lesson text comes from Bible Gateway in the **NIV** (NRSV only for Apocrypha, which the NIV lacks) |
| Psalms | 30-day psalter. **Odd-numbered months** (Jan, Mar, May, Jul, Sep, Nov): use the **Evening** psalms for that day. Even months: Morning psalms |
| OT and NT lessons | **Odd-numbered years** (2027, 2029…): use the **Evening** Prayer OT and NT lessons for that day. Even years: Morning lessons |
| Office text printed | Opening verse (always option 1, Philippians 1:2) · Confession of Sin · Invitatory, with **Psalm 95:1–7 (Venite) on even dates and Psalm 100 (Jubilate) on odd dates**, in prayer-book wording · Psalms and lessons (NIV) · Canticle (the site's default for the day) · Apostles' Creed · Lord's Prayer (traditional) · Suffrages · Collect of the Day · Collects for Peace and Grace · Prayer for Mission (rotates 1→2→3 by date) · Petitions, Intercessions, and Thanksgivings list. Not printed: General Thanksgiving, Prayer of St. John Chrysostom, closing benediction |
| Proverbs | Chapter = day of the month (1–31), **NIV**, full text |
| Murray | *With Christ in the School of Prayer*, lesson = day of the month (1–31). About a 200-word summary of the main points, pre-written in `murray/lesson-NN.md` |
| Weather | Boston, MA today plus a 14-day forecast. If `config/location.json` has an active travel location outside Massachusetts, add that location too |

## Steps

1. Nothing needs installing: the Python scripts use only the standard library,
   and Playwright and Chromium are pre-installed (don't reinstall them).
2. **Murray.** All 31 summaries are pre-written in `murray/lesson-01.md` …
   `lesson-31.md`. Use them as they are; don't rewrite them. (Only if a file is
   ever missing: summarize that lesson from
   https://ccel.org/ccel/m/murray/prayer/cache/prayer.txt in the same format,
   and include it in the email without committing.)
3. `python3 build.py --out /tmp/brief`. This:
   - renders dailyofficeforall.com in headless Chromium (`office.js`) with the
     settings above, picking the Morning or Evening office as the rules require
     for psalms and for lessons, and captures the day's title and the
     traditional Lord's Prayer
   - fetches each psalm and lesson from Bible Gateway
     in the NIV (NRSV for Apocrypha), plus Proverbs in the NIV (`scripture.py`)
   - fetches weather from Open-Meteo, retrying, and falls back to the 7-day NWS
     forecast if needed (`brief.py`)
   - writes `/tmp/brief/content.json` and `/tmp/brief/brief.html`
4. Send `/tmp/brief/brief.html` with Gmail `send_message` to dvslice@gmail.com.
   Subject: `Morning Reading: <Weekday, Month D>`. Put the HTML file's contents in
   `htmlBody`, plus a short plain-text `body`.
5. If any step fails, still send the email: include what you have, add a
   link for each missing section, and put a line at the top saying what failed.
   Never invent scripture text.

## Travel location

The user updates it by messaging the setup session, for example "I'm in Denver
until Nov 10". That session then edits `config/location.json` and pushes the
change to the `claude/morning-reading-list-weather-f4ix4t` branch, which the
scheduled task reads.
