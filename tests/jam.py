"""Traffic test: do units get past each other, and do harvesters keep working?

Usage:  python3 tests/jam.py [outdir]

1. Two harvesters drive straight at each other and must swap places.
2. Two rows of tanks swap sides through each other.
3. A harvester drives through a clump of parked troops.
4. Four harvesters share one refinery for three minutes: none may sit jammed,
   and they must keep bringing tuna home.
Fails (exit 1) on a jam, a timeout or any page error.
"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
OUT.mkdir(parents=True, exist_ok=True)

SETUP = '''() => {
  const g = __game;
  // a clear rectangle of ground for the driving tests
  for (let z = 30; z < 70; z++) for (let x = 25; x < 75; x++) {
    let ok = true;
    for (let dz = 0; dz < 8 && ok; dz++) for (let dx = 0; dx < 16 && ok; dx++) if (g.blocked(x + dx, z + dz)) ok = false;
    if (ok) return [x, z];
  }
  return null;
}'''

# drive units to targets; returns seconds taken (or None) and how far each ended from its goal
DRIVE = '''([moves, limit]) => {
  const g = __game, by = id => g.entities.find(e => e.id === id);
  for (const [id, x, z] of moves) g.order(id, x, z);
  let t = 0;
  while (t < limit) {
    g.tick(0.5); t += 0.5;
    if (moves.every(([id, x, z]) => { const u = by(id); return u && Math.hypot(u.x - x, u.z - z) < 1.3 && !u.moving; })) return { t, miss: [] };
  }
  return { t: null, miss: moves.map(([id, x, z]) => { const u = by(id); return +Math.hypot(u.x - x, u.z - z).toFixed(1); }) };
}'''

fails, errors = [], []
def check(name, ok, info):
    print(('ok   ' if ok else 'FAIL ') + name + '  ' + json.dumps(info))
    if not ok: fails.append(name)

with sync_playwright() as p:
    b = p.chromium.launch(args=['--enable-unsafe-swiftshader', '--use-gl=angle', '--use-angle=swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': 1200, 'height': 800})
    pg.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    pg.on('console', lambda m: errors.append('console: ' + m.text) if m.type == 'error' else None)
    pg.goto((ROOT / 'index.html').as_uri())
    pg.wait_for_function('window.__game', timeout=60000)
    pg.evaluate('__game.start(1); __game.freeze(true); __game.reveal(true)')
    # keep the enemy out of it: no money, no attack waves
    pg.evaluate('__game.teams[1].credits = 0; __game.AI.waveT = 1e9; __game.AI.income = 0; __game.AI.think = 1e9')
    ox, oz = pg.evaluate(SETUP)

    # 1. head-on harvesters
    a = pg.evaluate(f'__game.spawn(0, "harvester", {ox + 1.5}, {oz + 4.5}, Math.PI/2)')
    c = pg.evaluate(f'__game.spawn(0, "harvester", {ox + 14.5}, {oz + 4.5}, -Math.PI/2)')
    pg.evaluate(f'__game.entities.filter(e => e.id === {a} || e.id === {c}).forEach(u => {{ u.state = "idle"; u.hs = null; }})')
    r = pg.evaluate(DRIVE, [[[a, ox + 14.5, oz + 4.5], [c, ox + 1.5, oz + 4.5]], 30])
    check('head-on harvesters swap', r['t'] is not None and r['t'] <= 16, r)

    # 2. two rows of tanks swap sides
    left = [pg.evaluate(f'__game.spawn(0, "tank", {ox + 2.5}, {oz + 1.5 + i * 1.2}, Math.PI/2)') for i in range(5)]
    right = [pg.evaluate(f'__game.spawn(0, "tank", {ox + 13.5}, {oz + 1.5 + i * 1.2}, -Math.PI/2)') for i in range(5)]
    moves = [[u, ox + 13.5, oz + 1.5 + i * 1.2] for i, u in enumerate(left)] + [[u, ox + 2.5, oz + 1.5 + i * 1.2] for i, u in enumerate(right)]
    r = pg.evaluate(DRIVE, [moves, 40])
    check('tank rows swap', r['t'] is not None and r['t'] <= 22, r)
    pg.screenshot(path=str(OUT / 'jam_tanks.png'))

    # 3. harvester through a clump of parked troops (tanks now sit on the right)
    clump = []
    for i in range(4):
        for j in range(3):
            clump.append(pg.evaluate(f'__game.spawn(0, "rifle", {ox + 7.2 + i * 0.6}, {oz + 3.6 + j * 0.6})'))
    r = pg.evaluate(DRIVE, [[[a, ox + 1.5, oz + 4.5]], 30])   # a is at the right end after test 1
    check('harvester through parked troops', r['t'] is not None and r['t'] <= 18, r)

    # 4. four harvesters on one refinery, on a fresh game so the timing is the same every run
    pg.reload()
    pg.wait_for_function('window.__game', timeout=60000)
    pg.evaluate('__game.start(1); __game.freeze(true); __game.reveal(true)')
    pg.evaluate('__game.teams[1].credits = 0; __game.AI.waveT = 1e9; __game.AI.income = 0; __game.AI.think = 1e9')
    ids = pg.evaluate('''() => {
      const g = __game, ref = g.entities.find(e => e.team === 0 && e.key === 'refinery');
      const out = g.entities.filter(e => e.team === 0 && e.key === 'harvester' && !e.dead).map(e => e.id);
      for (let i = 0; out.length < 4; i++) { const id = g.spawn(0, 'harvester', ref.x - 2 + i * 1.5, ref.z + 3.5); g.harvest(id); out.push(id); }
      return out;
    }''')
    start = pg.evaluate('__game.teams[0].stats.harvested')
    r = pg.evaluate('''(ids) => {
      const g = __game, by = id => g.entities.find(e => e.id === id);
      const still = {}, last = {}, full = {}, trips = {}; let worst = 0, who = null, longest = 0;
      for (let t = 0; t < 180; t += 0.5) {
        g.tick(0.5);
        for (const id of ids) {
          const u = by(id); if (!u || u.dead) continue;
          // how long it has been carrying a full load without getting it home
          if (u.cargo >= 500) { full[id] = (full[id] || 0) + 0.5; longest = Math.max(longest, full[id]); }
          else { if (full[id]) trips[id] = (trips[id] || 0) + 1; full[id] = 0; }
          const busy = u.hs === 'mining' || u.hs === 'unload' || u.hs === 'wait' || u.hs === 'queue';
          const p = last[id]; last[id] = [u.x, u.z];
          if (busy || !p || Math.hypot(u.x - p[0], u.z - p[1]) > 0.15) { still[id] = 0; continue; }
          still[id] = (still[id] || 0) + 0.5;
          if (still[id] > worst) { worst = still[id]; who = [id, u.hs, +u.x.toFixed(1), +u.z.toFixed(1)]; }
        }
      }
      return { worst, who, longestFull: longest, trips: ids.map(id => trips[id] || 0) };
    }''', ids)
    got = pg.evaluate('__game.teams[0].stats.harvested') - start
    r['harvested'] = got
    check('four harvesters keep moving', r['worst'] < 4, r)
    check('every harvester gets its load home', r['longestFull'] < 60 and min(r['trips']) >= 2, r)
    check('four harvesters bring tuna home', got >= 6000, {'harvested': got})
    pg.evaluate('''() => { const r = __game.entities.find(e => e.team === 0 && e.key === 'refinery'); __game.cam.x = r.x; __game.cam.z = r.z + 4; __game.cam.distT = 22; }''')
    pg.evaluate('__game.render()')
    pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / 'jam_refinery.png'))
    b.close()

for e in errors: print(e)
print('FAILS:', len(fails), ' ERRORS:', len(errors))
sys.exit(1 if fails or errors else 0)
