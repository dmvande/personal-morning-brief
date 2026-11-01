# personal-morning-brief

A daily morning reading list, emailed to dvslice@gmail.com by 4:00 am ET every day.
It contains the Daily Office (dailyofficeforall.com), the Proverb for the day of the
month (NIV), a summary of Andrew Murray's lesson for the day, and Boston weather
(plus your travel location) with a 14-day forecast.

- `MORNING_BRIEF.md`: the rules and the step-by-step run instructions
- `build.py`: builds the whole email (`python3 build.py --out /tmp/brief`)
- `office.js`: reads the Daily Office for All page with your settings
- `scripture.py`: Bible Gateway passage text
- `brief.py`: date rules, weather lookup (Open-Meteo, with NWS fallback) and email rendering
- `config/location.json`: travel location (null means you're at home in MA)
- `murray/`: cached ~200-word lesson summaries
