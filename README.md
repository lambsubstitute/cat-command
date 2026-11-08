# Cat Command

A 3D real-time strategy game in the browser, played by cats. You run the Tabby Task Force against the Sphynx Directorate: harvest tuna, build a base, train an army and flatten every enemy structure.

Open `index.html` in a desktop browser and it runs. There's no build step and no install. The only things it loads from outside are Three.js (from jsDelivr) and two Google fonts.

## How it plays

- **Tuna** is the money. Your Roomba Harvester scoops up spilled tuna cans and drives them back to a Litter Tray Refinery.
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

| | |
|---|---|
| Left click / drag | Select (Shift adds; double-click selects every unit of that type on screen) |
| Right click | Move, attack, harvest, return to refinery, or set a rally point for a barracks or factory. On a Mac trackpad: two-finger click, or Ctrl + click |
| A, then click | Attack-move |
| S | Stop |
| Two-finger swipe | Scroll the map |
| Pinch, or + / − | Zoom |
| Arrow keys, screen edge, Option + drag, right-drag, middle drag, or drag on the minimap | Also scroll |
| F | Full screen (makes edge scrolling much easier) |
| Q / E | Rotate the view |
| Ctrl + 1-9, then 1-9 | Make and recall squads (press twice to jump to them) |
| H | Jump to your Command Box |
| Space | Jump to the last alert |
| P or Esc | Pause |
| Sidebar | Left click builds or queues, right click puts on hold, then cancels and refunds |

Selected buildings can be repaired (costs tuna) or sold for half price.

`?seed=12` on the page address gives a different map.

## Making changes

Everything is in `index.html`: the page and styles first, then one script split into sections with capitalised banners (MODEL TOOLKIT, PATHFINDING, UNIT BEHAVIOUR, ENEMY AI...). Find your way with:

```sh
grep -nE '^// [A-Z][A-Z ,:()-]{5,}$' index.html
```

- Unit and structure stats live in `DEFS` and `WEAPONS` near the top.
- Models are built from boxes and cylinders in the MODEL TOOLKIT section (`makeCat`, `makeRoomba`, `makeBuildingModel`). Sidebar icons are rendered from the same models when the page loads.
- The map is 96 x 96 tiles and one tile is one world unit.
- Difficulty settings are in `DIFFICULTY`.

## Tests

The tests drive the game in headless Chromium with Playwright.

```sh
pip install playwright --break-system-packages && python3 -m playwright install chromium   # once
python3 tests/smoke.py 6 out      # six game minutes of a do-nothing player; prints each side's forces every minute
python3 tests/flow.py out         # builds and places a barracks, trains troops, box-selects and moves them with real clicks, then checks the trackpad controls
```

Both fail on any page or console error. Screenshots land in the folder you name (`out` above), and `*.png` is git-ignored.

The page exposes `window.__game` for tests: `step(seconds)` runs the simulation, `reveal(true)` lifts the fog, and there are `select`, `command`, `queue` and `place` helpers.
