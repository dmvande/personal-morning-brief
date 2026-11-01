# Morning Reading List: run instructions

The scheduled task follows these steps every day. It must finish before 4:00 am
US Eastern and send the email to **dvslice@gmail.com**.

## Rules (computed by `python3 brief.py plan`)

| Item | Rule |
|---|---|
| Date | Today in America/New_York |
| Daily Office source | https://dailyofficeforall.com. Morning Prayer for the date, with settings: **30-day psalter**, **Regular** version, **praying by myself**, **traditional** Lord's Prayer |
| Psalms | 30-day psalter. **Odd-numbered months** (Jan, Mar, May, Jul, Sep, Nov): use the **Evening** psalms for that day. Even months: Morning psalms |
| OT and NT lessons | **Odd-numbered years** (2027, 2029…): use the **Evening** Prayer OT and NT lessons for that day. Even years: Morning lessons |
| Proverbs | Chapter = day of the month (1–31), **NIV**, full text |
| Murray | *With Christ in the School of Prayer*, lesson = day of the month (1–31). About a 200-word summary of the main points, cached in `murray/lesson-NN.md` |
| Weather | Boston, MA today plus a 14-day forecast. If `config/location.json` has an active travel location outside Massachusetts, add that location too |

## Steps

1. `python3 brief.py plan > /tmp/plan.json` and read it.
2. **Daily Office.** Open dailyofficeforall.com for the date with the settings above.
   Fetch Morning Prayer, and Evening Prayer as well if the plan needs it for psalms
   or lessons. Capture the psalm references and text, the OT and NT lesson
   references and text, the day's title (feast or season), and the traditional
   Lord's Prayer. Also include the gospel reading if the office lists a third
   lesson. If the site shows special readings for a feast, use the ones it gives
   for the chosen office and say so in `note`.
3. **Proverbs.** Fetch the NIV chapter from
   `https://www.biblegateway.com/passage/?search=Proverbs+N&version=NIV`.
   Keep the verse numbers and leave out the footnotes.
4. **Murray.** Read `murray/lesson-NN.md`. If it's missing, fetch the lesson
   from https://www.ccel.org/ccel/murray/prayer (or Project Gutenberg), write a
   faithful summary of about 200 words, save it to that file, and commit and push it.
5. `python3 brief.py weather > /tmp/weather.json`
6. Build `/tmp/content.json` with keys `plan`, `office` (`day_title`, `note`, `url`,
   `readings: [{label, reference, text}]`, `lords_prayer`), `proverbs` (`text`, `url`),
   `murray` (`title`, `summary`) and `weather` (from step 5). Then run
   `python3 brief.py render /tmp/content.json > /tmp/brief.html`.
7. Send it with Gmail `send_message` to dvslice@gmail.com, with subject
   `Morning Reading: <Weekday, Month D>`, `htmlBody` set to the rendered HTML, and a
   short plain-text `body`.
8. If any source fails, still send the email: include what you have, add a
   link for each missing section, and put a line at the top saying what failed.
   Never invent scripture text.

## Travel location

The user updates it by messaging the setup session, for example "I'm in Denver
until Nov 10". That session then edits `config/location.json` and pushes the
change to the `claude/morning-reading-list-weather-f4ix4t` branch, which the
scheduled task reads.
