// Render dailyofficeforall.com with the user's settings and print the readings
// and the chosen liturgy sections as JSON.
// Usage: node office.js <morning|evening> [YYYY-MM-DD]
const { chromium } = require('playwright');
(async () => {
  const which = process.argv[2] || 'morning', date = process.argv[3];
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('https://dailyofficeforall.com/morning-prayer.html', { waitUntil: 'networkidle' });
  const set = async (id, v) => {
    await p.evaluate(([i, v]) => { const e = document.getElementById(i); e.value = v; e.dispatchEvent(new Event('change')); }, [id, v]);
    await p.waitForTimeout(800);
  };
  if (date) await set('prayerDate', date);
  await set('liturgy-version', 'full');   // "regular"
  await set('in-group', 'single');        // "by myself"
  await set('psalmCycle', '30');
  await set('lp', 'traditional');
  await set('lessonsToUse', which);
  const day = date ? parseInt(date.split('-')[2], 10) : new Date().getDate();
  const r = await p.evaluate((day) => {
    const vis = e => e && e.offsetParent !== null;
    const links = [...document.querySelectorAll('a[href*="biblegateway"]')].filter(vis)
      .map(a => ({ id: a.closest('li')?.id || '', reference: a.textContent.trim(), url: a.href }));
    // Show a chosen option (the site hides the ones not selected) and read its text.
    const show = (id) => { const e = document.getElementById(id); if (!e) return null; e.classList.remove('hidden'); return e; };
    const tidy = t => t.replace(/ /g, ' ').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
    const sectionText = (id) => {          // section text without its <h2> or option buttons
      const s = document.getElementById(id); if (!s) return '';
      const c = s.cloneNode(true);
      c.querySelectorAll('h2, .option-selector-wrapper').forEach(x => x.remove());
      document.body.appendChild(c); const t = c.innerText; c.remove();
      return tidy(t);
    };
    const optText = (id, dropSel) => {
      const e = show(id); if (!e) return '';
      const c = e.cloneNode(true);
      if (dropSel) c.querySelectorAll(dropSel).forEach(x => x.remove());
      document.body.appendChild(c); const t = c.innerText; c.remove();
      return tidy(t);
    };
    // Opening verse: always option 1 (Philippians 1:2).
    const opening = optText('meditate-1');
    // Invitatory: versicles, then Venite (Ps 95:1-7) on even dates, Jubilate (Ps 100) on odd dates.
    const invPsalmId = day % 2 === 0 ? 'venite' : 'jubliate';
    const invHead = (document.querySelector('#' + invPsalmId + ' h3') || {}).innerText || '';
    const invitatory = {
      versicles: sectionText('invitatory'),
      psalm_title: tidy(invHead.replace(/;\s*8.?11/, '')),
      psalm_text: optText(invPsalmId, 'h3, [data-lent-only]'),
    };
    // Prayer for mission: rotate through the three by day of month.
    const missionId = 'mission-' + (((day - 1) % 3) + 1);
    const text = document.getElementById('content').innerText;
    const m = text.match(/The Lord’s Prayer\s*\n+([\s\S]*?Amen\.)/);
    return {
      date: document.getElementById('date').innerText.trim(), links,
      lords_prayer: m ? m[1].trim() : '',
      liturgy: {
        opening, confession: sectionText('confession'), invitatory,
        creed: sectionText('creed'), lords_prayer: sectionText('lords-prayer'),
        suffrages: sectionText('suffrages'), collect: sectionText('collect'),
        peace_grace: sectionText('peace-grace'),
        mission: optText(missionId) + '\n\nAmen.', mission_number: missionId.slice(-1),
        canticle: sectionText('canticle'),      // the site's default canticle for the day
        petitions: sectionText('petitions'),
      },
    };
  }, day);
  r.page = 'https://dailyofficeforall.com/morning-prayer.html';
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
