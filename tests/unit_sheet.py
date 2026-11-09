"""Unit sheet: every unit, both teams, lined up and rendered at game zoom and close up.

Also renders a fight frame (shots in the air) and a death strip.
Usage:  python3 tests/unit_sheet.py outdir [tag]
"""
import sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1]); TAG = sys.argv[2] if len(sys.argv) > 2 else 'sheet'
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1200, 'height': 800})
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function('window.__game')
    pg.click('#btnStart')
    g = lambda js: pg.evaluate(js)
    g('__game.freeze(true); __game.reveal(true)')
    ids = g('''() => {
      const keys = ['rifle', 'grenadier', 'tank', 'harvester'], out = [];
      keys.forEach((k, i) => { out.push(__game.spawn(0, k, 19 + i * 1.6, 86.5, 0.5)); out.push(__game.spawn(1, k, 19 + i * 1.6, 88.3, 0.5)); });
      return out; }''')
    def shot(name, x, z, d, yaw=0):
        g(f'__game.cam.x={x};__game.cam.z={z};__game.cam.dist=__game.cam.distT={d};__game.cam.yaw=__game.cam.yawT={yaw}')
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(OUT / f'{TAG}_{name}.png'), clip={'x': 0, 'y': 34, 'width': 956, 'height': 766})
    shot('game_zoom', 21.5, 87.5, 20)
    shot('close', 21.5, 87.5, 8)
    # a fight frame: player units shoot their opposite numbers
    g(f'''() => {{ const ids = {ids}; for (let i = 0; i < 6; i += 2) __game.shoot(ids[i], ids[i + 1]); __game.tick(0.12); __game.effectsTick(0.05); }}''')
    shot('fight', 21.5, 87.5, 9)
    # death strip for an enemy rifle cat and an enemy tank
    for i, t in enumerate([0.05, 0.3, 0.7, 1.2]):
        if i == 0:
            g(f'__game.hurt({ids[1]}, 9999); __game.hurt({ids[5]}, 9999)')
        g(f'__game.tick({t if i == 0 else t - [0.05, 0.3, 0.7, 1.2][i - 1]}); __game.effectsTick({t if i == 0 else t - [0.05, 0.3, 0.7, 1.2][i - 1]})')
        shot(f'death{i}', 21.5, 88, 8)
    b.close()
print('errors:', errors)
sys.exit(1 if errors else 0)
