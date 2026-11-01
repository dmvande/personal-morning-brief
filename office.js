// Render dailyofficeforall.com with the user's settings and print the readings as JSON.
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
  const r = await p.evaluate(() => {
    const vis = e => e && e.offsetParent !== null;
    const links = [...document.querySelectorAll('a[href*="biblegateway"]')].filter(vis)
      .map(a => ({ id: a.closest('li')?.id || '', reference: a.textContent.trim(), url: a.href }));
    const text = document.getElementById('content').innerText;
    const m = text.match(/The Lord’s Prayer\s*\n+([\s\S]*?Amen\.)/);
    return { date: document.getElementById('date').innerText.trim(), links, lords_prayer: m ? m[1].trim() : '' };
  });
  r.page = 'https://dailyofficeforall.com/morning-prayer.html';
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})();
