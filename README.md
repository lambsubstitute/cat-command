# Cat Command

A 3D real-time strategy game in the browser, played by cats. You run the Tabby Task Force against the Sphynx Directorate: harvest tuna, build a base, train an army and flatten every enemy structure.

Open `index.html` in a desktop browser and it runs. There's no build step and no install. The only things it loads from outside are Three.js (from jsDelivr) and two Google fonts.

## How it plays

- **Tuna** is the money. Your Roomba Harvester scoops up spilled tuna cans and drives them back to a Litter Tray Refinery.
  Only one harvester can unload at a refinery at a time; the others wait their turn close by, so a second refinery helps once you have three or four.
- **Power** comes from Treadmill Generators (a cat on a hamster wheel). Most buildings draw power. If you run short, building slows down and Laser Pointer Towers switch off.
- **Building** works like the old classics. Click a structure in the sidebar and it's built over time, paid for as it goes. When it says READY, click it again and place it on the map, close to your other buildings. Units queue up at the barracks or the factory.
- **Fog of war.** You only see what your troops and buildings can see. Ground you've explored but aren't watching stays dim.
- **The enemy** has a base in the north-east. It harvests, builds, trains, and sends bigger attack waves as time goes on. It also defends its base if you attack it.
- You win when every enemy structure is gone. You lose when you have no structures left and no fighting units.

| Structure | Cost | Does |
|---|---|---|
| Treadmill Generator | 300 | +100 power |
| Litter Tray Refinery | 1400 | Processes tuna, comes with a free harvester |
| Scratch Post Barracks | 400 | Trains infantry |
| Roomba Works | 1600 | Builds vehicles |
| Laser Pointer Tower | 500 | Base defence, needs power |

| Unit | Cost | Good against |
|---|---|---|
| Rifle Cat | 100 | Infantry |
| Hiss Grenadier | 250 | Structures and groups (splash damage) |
| Roomba Tank | 800 | Vehicles |
| Roomba Harvester | 1200 | Unarmed, collects tuna |

## Controls

### Mouse and trackpad

Orders go on the **left** click by default, like the classic games: click your troops (or drag a box round them), then click the ground to move or an enemy to attack. If you'd rather give orders with the right button, switch "Orders on" to Right click on the briefing screen or in the pause menu. The game remembers your choice.

| | |
|---|---|
| Left click / drag | Select. With troops selected, click the ground to move, an enemy to attack, tuna to harvest, or your refinery to unload |
| Right click, Ctrl + click or Esc | Deselect (or give orders, if you've switched orders to the right button) |
| Shift + click, double-click | Add to the selection; select every unit of that type on screen |
| A, then click | Attack-move |
| S | Stop |
| Two-finger swipe | Scroll the map |
| Pinch, or + / − | Zoom |
| Arrow keys, screen edge, Option + drag, right-drag, middle drag, or the minimap | Also scroll |
| F | Full screen (makes edge scrolling much easier) |
| Q / E | Rotate the view |
| Ctrl + 1-9, then 1-9 | Make and recall squads (press twice to jump to them) |
| H | Jump to your Command Box |
| Space | Jump to the last alert |
| P | Pause |
| Sidebar | Left click builds or queues, right click puts on hold, then cancels and refunds |

The pointer turns into a crosshair over an enemy you can attack.

### Phones and tablets

The game works held either way. Upright, the map is on top with the command panel along the bottom; sideways, there's a slim sidebar. The minimap floats in the corner.

| | |
|---|---|
| Tap | Select a cat or building; double-tap selects every unit of that type |
| Tap the ground | Move the selected troops (tap an enemy to attack, tuna to harvest) |
| One-finger drag | Scroll the map |
| Pinch | Zoom |
| BOX SELECT | Turn on, then drag across a group |
| ALL TROOPS | Select your whole army |
| Command panel | Tap to build or queue; press and hold to put on hold or cancel |
| Placing a structure | Tap where it goes, then tap the outline again to build |
| Minimap | Tap or drag to jump around |

On an iPhone, "Add to Home Screen" from the share menu runs it full screen.

Selected buildings can be repaired (costs tuna) or sold for half price, and a barracks or Roomba Works can be given a rally point (SET RALLY) where new units gather.

`?seed=12` on the page address gives a different map.

## Making changes

Everything is in `index.html`: the page and styles first, then one script split into sections with capitalised banners (MODEL TOOLKIT, PATHFINDING, UNIT BEHAVIOUR, ENEMY AI...). Find your way with:

```sh
grep -nE '^// [A-Z][A-Z ,:()-]{5,}$' index.html
```

- Unit and structure stats live in `DEFS` and `WEAPONS` near the top.
- Models are built from boxes and cylinders in the MODEL TOOLKIT section (`makeCat`, `makeRoomba`, `makeBuildingModel`). Sidebar icons are rendered from the same models when the page loads.
- Each side has a team colour (`team` in `TEAM`): green for the tabbies, red for the Sphynx. It's on every unit's scarf, hat band or rim stripe, and on the ring under its feet, so keep it on anything new you add.
- Units should be easy to tell apart from the game camera by shape alone: rifle cats have a helmet and a long rifle, grenadiers a wide hat and a drum on their back, tanks have tracks, harvesters a bin and a scoop. Check new art with `tests/unit_sheet.py`.
- Getting about is in UNIT BEHAVIOUR: units follow an A* path, look ahead and pass oncoming units on their right, slow down behind slower ones, and ask idle friends in the way to step aside. A unit that stops getting closer for two seconds finds a way round the crowd, then backs off to one side. Run `tests/jam.py` after changing any of it.
- Battle effects (muzzle flashes, hit flashes, sparks, wrecks, rubble, order lines) live in COMBAT, PROJECTILES AND EFFECTS.
- The map is 96 x 96 tiles and one tile is one world unit.
- The ground is one big plane with per-vertex colours (grass, dry patches, dirt, the road and its ruts, oily tuna stains) under a tiling detail texture drawn on a canvas at load (`groundDetailTex`). Grass tufts, pebbles, flowers and litter are instanced meshes scattered in `buildGroundProps`, and hidden under anything built. Every building gets a soft dark patch underneath (`groundShadow`). Lighting is a warm low sun with blue-grey shade and ACES tone mapping, so tweak `toneMappingExposure` before touching the colours.
- Difficulty settings are in `DIFFICULTY`.

## Tests

The tests drive the game in headless Chromium with Playwright.

```sh
pip install playwright --break-system-packages && python3 -m playwright install chromium   # once
python3 tests/smoke.py 6 out      # six game minutes of a do-nothing player; prints each side's forces every minute
python3 tests/flow.py out         # builds and places a barracks, trains troops, box-selects and moves them with real clicks, then checks the trackpad controls
python3 tests/touch.py out        # phone sizes, upright and sideways: layout fits, tap, drag, pinch, placing, minimap
python3 tests/jam.py out          # traffic: units meeting head-on, crossing, driving through a crowd, four harvesters sharing a refinery
python3 tests/unit_sheet.py out   # pictures, not a pass/fail test: every unit for both sides, a shot being fired, and units dying
```

All but `unit_sheet.py` fail on any page or console error. Screenshots land in the folder you name (`out` above), and `*.png` is git-ignored.

The page exposes `window.__game` for tests: `step(seconds)` runs the simulation, `reveal(true)` lifts the fog, and there are `select`, `command`, `queue` and `place` helpers.
