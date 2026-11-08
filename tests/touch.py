"""Phone test: portrait and landscape layouts, and the touch controls.

Taps a cat to select it, taps the ground to move it, drags one finger to scroll,
pinches to zoom, builds and places a barracks with taps, and uses the minimap.
Usage:  python3 tests/touch.py [outdir]      (exits 1 on any failure)
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

def touch(cdp, kind, pts):
    cdp.send('Input.dispatchTouchEvent', {'type': kind, 'touchPoints': [{'x': x, 'y': y, 'id': i} for i, (x, y) in enumerate(pts)]})

def drag(pg, cdp, path):
    touch(cdp, 'touchStart', [path[0]])
    for pt in path[1:]:
        touch(cdp, 'touchMove', [pt]); pg.wait_for_timeout(16)
    touch(cdp, 'touchEnd', [])

with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    for name, vp in [('portrait', {'width': 390, 'height': 844}), ('landscape', {'width': 844, 'height': 390})]:
        print(f'--- {name}')
        ctx = b.new_context(viewport=vp, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        cdp = ctx.new_cdp_session(pg)
        pg.goto((ROOT / 'index.html').as_uri())
        pg.wait_for_function('window.__game')
        pg.tap('#btnStart')
        pg.wait_for_timeout(500)
        g = lambda js: pg.evaluate(js)
        check(g('document.body.classList.contains("touch")'), 'touch layout is on')
        check(g('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight'), 'nothing spills off the screen')
        view = pg.locator('#view').bounding_box()
        check(view['width'] >= vp['width'] * 0.7, f"map gets most of the width ({view['width']:.0f}px)")

        # tap a cat, then the ground
        rid = g("__game.entities.find(e => e.team === 0 && e.key === 'rifle').id")
        sp = g(f'__game.screenOf({rid})')
        pg.touchscreen.tap(sp['x'], sp['y'])
        pg.wait_for_timeout(100)
        check(g('__game.selected').__contains__(rid), 'tap selects a cat')
        pg.touchscreen.tap(view['x'] + view['width'] * 0.5, view['y'] + view['height'] * 0.2)
        check(g(f"__game.entities.find(e => e.id === {rid}).state") == 'move', 'tap on the ground moves it')

        # one finger scrolls without changing the selection
        c0 = g('[__game.cam.x, __game.cam.z]')
        cx, cy = view['x'] + view['width'] / 2, view['y'] + view['height'] / 2
        drag(pg, cdp, [(cx, cy + 60 - i * 12) for i in range(12)])
        c1 = g('[__game.cam.x, __game.cam.z]')
        check(c1[1] > c0[1] + 1 and len(g('__game.selected')) == 1, f'one-finger drag scrolls ({c0[1]:.1f} -> {c1[1]:.1f}) and keeps the selection')

        # pinch out zooms in
        d0 = g('__game.cam.distT')
        touch(cdp, 'touchStart', [(cx - 30, cy), (cx + 30, cy)])
        for i in range(1, 8):
            touch(cdp, 'touchMove', [(cx - 30 - i * 12, cy), (cx + 30 + i * 12, cy)]); pg.wait_for_timeout(16)
        touch(cdp, 'touchEnd', [])
        d1 = g('__game.cam.distT')
        check(d1 < d0 * 0.7, f'pinch zooms in ({d0:.1f} -> {d1:.1f})')
        check(len(g('__game.selected')) == 1, 'pinch is not taken as a tap')

        # ALL TROOPS button
        pg.tap('#tbArmy')
        check(len(g('__game.selected')) >= 5, 'ALL TROOPS selects the army')

        # build and place a barracks with taps
        g('__game.cam.x = 15; __game.cam.z = 78; __game.cam.distT = __game.cam.dist = 24')
        pg.wait_for_timeout(200)
        pg.locator('.bbtn').nth(2).tap()
        g('__game.step(9)')
        pg.wait_for_timeout(150)
        pg.locator('.bbtn').nth(2).tap()
        check(g('__game.placing') == 'barracks', 'tapping READY starts placing')
        count = lambda: g("__game.entities.filter(e => !e.dead && e.team === 0 && e.key === 'barracks').length")
        placed = False
        for fy in (0.3, 0.45, 0.6, 0.75):
            for fx in (0.15, 0.35, 0.55, 0.75, 0.9):
                x, y = view['x'] + view['width'] * fx, view['y'] + view['height'] * fy
                pg.touchscreen.tap(x, y); pg.wait_for_timeout(40)
                pg.touchscreen.tap(x, y); pg.wait_for_timeout(40)
                if count():
                    placed = True; break
            if placed: break
        check(placed, 'tap, then tap the outline again, places it')

        # minimap jumps the camera
        mb = pg.locator('#mini').bounding_box()
        pg.touchscreen.tap(mb['x'] + mb['width'] * 0.8, mb['y'] + mb['height'] * 0.2)
        cm = g('[__game.cam.x, __game.cam.z]')
        check(cm[0] > 60 and cm[1] < 40, f'tapping the minimap moves the view ({cm[0]:.0f}, {cm[1]:.0f})')
        g('__game.cam.x = 17; __game.cam.z = 77')
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(OUT / f'cc_touch_{name}.png'))
        ctx.close()
    b.close()

for e in errors:
    print('error:', e)
check(not errors, 'no page errors')
sys.exit(1 if fails else 0)
