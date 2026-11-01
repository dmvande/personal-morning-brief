#!/usr/bin/env python3
"""Build the day's content.json and brief.html.

Usage: python3 build.py [YYYY-MM-DD] [--out DIR] [--weather weather.json]
Needs murray/lesson-NN.md to exist (see MORNING_BRIEF.md step 4).
"""
import json, os, re, subprocess, sys
import brief, scripture

ROOT = os.path.dirname(os.path.abspath(__file__))


def office(which, date):
    out = subprocess.check_output(["node", os.path.join(ROOT, "office.js"), which, date], cwd=ROOT)
    return json.loads(out)


def split_psalms(ref):
    # "Psalm 6, 7, 8" -> ["Psalm 6", "Psalm 7", "Psalm 8"]; keeps "Psalm 119:1-24"
    nums = ref.replace("Psalm", "").split(",")
    return ["Psalm " + n.strip() for n in nums if n.strip()]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_dir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp"
    wfile = sys.argv[sys.argv.index("--weather") + 1] if "--weather" in sys.argv else None
    args = [a for a in args if a not in (out_dir, wfile)]
    p = brief.plan(brief.parse_date(args))
    d = p["date"]
    psalm_src = office(p["daily_office"]["psalms_from"].lower(), d)
    lesson_src = psalm_src if p["daily_office"]["ot_nt_from"] == p["daily_office"]["psalms_from"] \
        else office(p["daily_office"]["ot_nt_from"].lower(), d)

    readings = []
    for l in psalm_src["links"]:
        if l["id"] == "psalm-lesson":
            for ps in split_psalms(l["reference"]):
                t = scripture.fetch(ps, "ESV")
                readings.append({"label": f"Psalm ({p['daily_office']['psalms_from']}, day {p['daily_office']['psalter_day']})",
                                 "reference": ps, "text": t["text"], "url": t["url"]})
    labels = {"OT": "First Lesson", "NT": "Second Lesson"}
    for l in lesson_src["links"]:
        if l["id"].startswith("lesson-"):
            ver = "NRSV" if "NRSV" in l["url"] else "ESV"
            t = scripture.fetch(l["reference"], ver)
            readings.append({"label": f"{labels[l['id'][-2:]]} ({p['daily_office']['ot_nt_from']})",
                             "reference": f"{l['reference']} ({ver})", "text": t["text"], "url": t["url"]})

    day_title = psalm_src["date"].split("–", 1)[1].strip() if "–" in psalm_src["date"] else ""
    pv = scripture.fetch(f"Proverbs {p['proverbs']['chapter']}", "NIV")
    mpath = os.path.join(ROOT, p["murray"]["summary_file"])
    mtxt = open(mpath).read().strip()
    title = mtxt.split("\n", 1)[0].removeprefix("Title:").strip() if mtxt.startswith("Title:") else ""
    summary = mtxt.split("\n", 1)[1].strip() if title else mtxt

    content = {
        "plan": p,
        "office": {"day_title": day_title, "url": psalm_src["page"], "readings": readings,
                   "lords_prayer": psalm_src["lords_prayer"]},
        "proverbs": {"text": pv["text"], "url": pv["url"]},
        "murray": {"title": title, "summary": summary},
        "weather": json.load(open(wfile)) if wfile else brief.weather(brief.parse_date(args)),
    }
    os.makedirs(out_dir, exist_ok=True)
    json.dump(content, open(os.path.join(out_dir, "content.json"), "w"), ensure_ascii=False, indent=1)
    open(os.path.join(out_dir, "brief.html"), "w").write(brief.render(content))
    print(os.path.join(out_dir, "brief.html"))


if __name__ == "__main__":
    main()
