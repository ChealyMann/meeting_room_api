// Writes tests/fixtures/khmer_lunar_2026_2027.json: the Khmer lunar date of every day of 2026 and
// 2027 as momentkh 3.0.3 (MIT, @thyrith/momentkh) gives it, run in a browser page. The Python port
// in app/services/khmer_calendar.py must match every row. Run from the repo root:
//   node scripts/make_lunar_fixture.cjs
const fs = require('fs')
const path = require('path')
const { chromium } = require(path.resolve('admin_dashboard/node_modules/playwright'))

const LIB = 'https://cdn.jsdelivr.net/npm/@thyrith/momentkh@3.0.3/momentkh.js'

;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage()
  await page.setContent(`<!doctype html><meta charset="utf-8"><script src="${LIB}"></script>`, { waitUntil: 'networkidle' })
  const rows = await page.evaluate(() => {
    const K = window.momentkh.fromGregorian ? window.momentkh : window.momentkh.default
    const kd = (v) => String(v).replace(/[0-9]/g, (d) => '០១២៣៤៥៦៧៨៩'[d])
    const out = []
    for (let t = Date.UTC(2026, 0, 1); t <= Date.UTC(2027, 11, 31); t += 86400000) {
      const d = new Date(t)
      const k = K.fromGregorian(d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()).khmer
      out.push({
        date: d.toISOString().slice(0, 10),
        line: `ថ្ងៃ${k.dayOfWeekName} ${kd(k.day)}${k.moonPhaseName} ខែ${k.monthName} ឆ្នាំ${k.animalYearName} ${k.sakName} ព.ស.${kd(k.beYear)}`,
      })
    }
    return out
  })
  await browser.close()
  const file = path.resolve('tests/fixtures/khmer_lunar_2026_2027.json')
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, JSON.stringify(rows, null, 0).replace(/},{/g, '},\n{') + '\n')
  console.log(`${rows.length} days → ${file}`)
})()
