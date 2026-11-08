"""Player flow test, driven by real mouse clicks.

Builds a barracks from the sidebar, places it on the map, trains rifle cats,
box-selects the army and right-clicks it somewhere. Exits 1 on any failure.
Usage:  python3 tests/flow.py [outdir]
"""
import sys, pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
errors, fails = [], []

def check(cond, msg):
    print(('ok   ' if cond else 'FAIL ') + msg)
    if not cond:
        fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1400, 'height': 860})
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function('window.__game')
    pg.click('#btnStart')
    pg.wait_for_timeout(400)
    count = lambda key: pg.evaluate(f"__game.entities.filter(e => !e.dead && e.team === 0 && e.key === '{key}').length")

    # 1. build a barracks from the sidebar
    btn = pg.locator('.bbtn').nth(2)          # Scratch Post Barracks
    btn.click()
    pg.evaluate('__game.step(9)')
    pg.wait_for_timeout(200)
    check(pg.evaluate('__game.teams[0].struct && __game.teams[0].struct.ready'), 'barracks finished building')
    btn.click()                               # enter placement mode

    # 2. place it: scan the view for a spot the game accepts
    view = pg.locator('#view').bounding_box()
    placed = False
    for dy in range(-120, 200, 40):
        for dx in range(80, 360, 40):
            x, y = view['x'] + view['width'] / 2 + dx, view['y'] + view['height'] / 2 + dy
            pg.mouse.move(x, y)
            pg.mouse.down(); pg.mouse.up()
            pg.wait_for_timeout(30)
            if count('barracks'):
                placed = True
                break
        if placed:
            break
    check(placed, 'barracks placed with a click on the map')
    pg.evaluate('__game.step(2)')

    # 3. train three rifle cats
    pg.click('#tabs button[data-tab=units]')
    rifle = pg.locator('.bbtn').nth(0)
    for _ in range(3):
        rifle.click()
    before = count('rifle')
    pg.evaluate('__game.step(14)')
    check(count('rifle') == before + 3, f'three rifle cats trained ({before} -> {count("rifle")})')

    # 4. box-select everything on screen and right-click a destination
    pg.evaluate('__game.cam.x = 17; __game.cam.z = 77; __game.cam.dist = __game.cam.distT = 26')
    pg.wait_for_timeout(300)
    pg.mouse.move(view['x'] + 10, view['y'] + 10)
    pg.mouse.down()
    pg.mouse.move(view['x'] + view['width'] - 10, view['y'] + view['height'] - 10, steps=5)
    pg.mouse.up()
    pg.wait_for_timeout(250)
    nsel = pg.evaluate("document.querySelector('#selpanel h3').textContent")
    check('UNITS' in nsel, f'box select picked units ({nsel})')
    pg.mouse.click(view['x'] + view['width'] * 0.8, view['y'] + view['height'] * 0.25)
    moving = pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle' && e.state === 'move').length")
    check(moving >= 3, f'left click on the ground sent units moving ({moving})')
    pg.evaluate('__game.step(3)')
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / 'cc_flow.png'))

    # 5. Mac trackpad: two-finger swipe pans, pinch (ctrl + wheel) zooms,
    #    Ctrl + click gives orders, right-drag pans without giving orders
    cx, cy = view['x'] + view['width'] / 2, view['y'] + view['height'] / 2
    cam = lambda: pg.evaluate('[__game.cam.x, __game.cam.z, __game.cam.distT]')
    pg.mouse.move(cx, cy)
    c0 = cam(); pg.mouse.wheel(0, 300); pg.wait_for_timeout(100); c1 = cam()
    check(c1[1] > c0[1] + 2, f'two-finger swipe down scrolls the map south ({c0[1]:.1f} -> {c1[1]:.1f})')
    pg.mouse.wheel(300, 0); pg.wait_for_timeout(100); c2 = cam()
    check(c2[0] > c1[0] + 2, f'two-finger swipe right scrolls east ({c1[0]:.1f} -> {c2[0]:.1f})')
    pg.keyboard.down('Control'); pg.mouse.wheel(0, -100); pg.keyboard.up('Control'); pg.wait_for_timeout(100); c3 = cam()
    check(c3[2] < c2[2] and abs(c3[1] - c2[1]) < 0.01, f'pinch zooms in without scrolling ({c2[2]:.1f} -> {c3[2]:.1f})')
    pg.evaluate('__game.cam.x = 17; __game.cam.z = 77')
    pg.wait_for_timeout(200)
    pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle').forEach(e => { e.state = 'idle'; e.path = null; })")
    army = pg.evaluate("__game.entities.filter(e => e.team === 0 && e.isUnit && e.def.weapon).map(e => e.id)")
    pg.evaluate(f'__game.select({army})')
    pg.keyboard.down('Control'); pg.mouse.click(cx + 150, cy - 100); pg.keyboard.up('Control')
    moving = pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle' && e.state === 'move').length")
    check(moving == 0 and pg.evaluate('__game.selected.length') == 0, f'classic controls: Ctrl + click deselects (moving {moving})')
    pg.evaluate("__game.setOrders('right')")
    pg.evaluate(f'__game.select({army})')
    pg.keyboard.down('Control'); pg.mouse.click(cx + 150, cy - 100); pg.keyboard.up('Control')
    moving = pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle' && e.state === 'move').length")
    check(moving >= 3, f'right-click controls: Ctrl + click gives a move order ({moving})')
    pg.evaluate("__game.setOrders('left')")
    pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle').forEach(e => { e.state = 'idle'; e.path = null; })")
    c4 = cam()
    pg.mouse.move(cx, cy); pg.mouse.down(button='right'); pg.mouse.move(cx - 200, cy, steps=6); pg.mouse.up(button='right')
    c5 = cam()
    moving = pg.evaluate("__game.entities.filter(e => e.team === 0 && e.key === 'rifle' && e.state === 'move').length")
    check(c5[0] > c4[0] + 1 and moving == 0, f'right-drag pans and gives no order (x {c4[0]:.1f} -> {c5[0]:.1f}, moving {moving})')
    b.close()

for e in errors:
    print('error:', e)
check(not errors, 'no page errors')
sys.exit(1 if fails else 0)
