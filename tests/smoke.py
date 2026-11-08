"""Smoke test: load the game headless, start it, fast-forward, report and screenshot.

Usage:  python3 tests/smoke.py [minutes] [outdir]
Fails (exit 1) on any page error or console error.
"""
import json, os, sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else '.')
OUT.mkdir(parents=True, exist_ok=True)

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1400, 'height': 860})
    pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function('window.__game', timeout=60000)
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(OUT / 'cc_briefing.png'))
    pg.click('#btnStart')
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(OUT / 'cc_start.png'))

    report = []
    for minute in range(int(MINUTES)):
        pg.evaluate('__game.step(60)')
        s = pg.evaluate('''() => {
          const g = __game, by = t => g.entities.filter(e => !e.dead && e.team === t);
          const summary = t => { const c = {}; for (const e of by(t)) c[e.key] = (c[e.key] || 0) + 1; return c; };
          return { t: Math.round(g.time), ended: g.ended,
                   credits: g.teams.map(T => Math.round(T.credits)), harvested: g.teams.map(T => T.stats.harvested),
                   p: summary(0), e: summary(1), wave: g.AI.waveSize };
        }''')
        report.append(s)
        print(json.dumps(s))
        if s['ended']:
            break
    pg.evaluate('__game.cam.x = 48; __game.cam.z = 48; __game.cam.distT = 30')
    pg.wait_for_timeout(600)
    pg.screenshot(path=str(OUT / 'cc_mid.png'))
    b.close()

for e in errors:
    print(e)
print('ERRORS:', len(errors))
sys.exit(1 if errors else 0)
