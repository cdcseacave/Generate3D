# Apartment blueprint

Single-level flat for two adults and one toddler. Units are metres. Origin at the
south-west outer corner on the floor; **+X = east, +Y = north, +Z = up**. All room
rectangles are given on wall centre lines; clear interior size is in brackets.

## Envelope

| Item | Value |
|---|---|
| Footprint (centre lines) | 10.00 × 10.60 |
| Ceiling height | 2.70 |
| Exterior walls | 0.30 thick |
| Interior partitions | 0.12 thick |
| Baseboard | 0.075 high × 0.014 |
| Ceiling cornice | 0.06 × 0.06 cove, all rooms |
| Interior doors | 0.90 (bath 0.80) × 2.07 clear, leaf 42 mm, lever at 1.02 |
| Entrance door | 0.95 × 2.07, walnut veneer, lock + peephole |
| Switches / sockets | switch 1.10 above floor on the latch side; sockets at 0.30 |

## Rooms

```
y=10.6 ┌───────────┬─────────┬────────┐
       │  Bedroom  │ Office  │  Bath  │   north band  y 6.6 → 10.6
y=6.6  ├────  ─────┴──  ─────┴─  ─────┤
       │            Hallway           │   hall band   y 4.6 → 6.6
y=4.6  ├───────  ────────┬────  ──────┤
       │   Living room   │  Kitchen   │   south band  y 0 → 4.6
y=0    └─────────────────┴────────────┘
      x=0        4.2    6.2   7.4    10
```

| Room | x range | y range | Clear size | Floor | Walls |
|---|---|---|---|---|---|
| Hallway | 0 → 10.0 | 4.6 → 6.6 | 9.70 × 1.88 | herringbone oak parquet | warm white paint |
| Living room | 0 → 6.2 | 0 → 4.6 | 5.99 × 4.39 | herringbone oak parquet | warm off-white paint |
| Kitchen | 6.2 → 10.0 | 0 → 4.6 | 3.59 × 4.39 | beige stone tile | white paint, tiled backsplash |
| Primary bedroom | 0 → 4.2 | 6.6 → 10.6 | 3.99 × 3.79 | herringbone oak parquet | pale sage paint |
| Home office | 4.2 → 7.4 | 6.6 → 10.6 | 3.08 × 3.79 | herringbone oak parquet | warm beige paint |
| Bathroom | 7.4 → 10.0 | 6.6 → 10.6 | 2.39 × 3.79 | grey stone tile | 60 × 30 glazed white tile in half bond, full height |

## Openings

Position = start → end along the wall (x for east–west walls, y for north–south walls).

| Wall | Opening | Position | Sill → head | Notes |
|---|---|---|---|---|
| West (x=0) | Entrance door | y 5.15 → 6.10 | 0 → 2.07 | into the hallway, closed |
| Hall south (y=4.6) | Cased opening → living | x 2.00 → 3.40 | 0 → 2.20 | no leaf |
| Hall south (y=4.6) | Cased opening → kitchen | x 7.30 → 8.30 | 0 → 2.20 | no leaf |
| Hall north (y=6.6) | Bedroom door | x 2.60 → 3.50 | 0 → 2.07 | hinged east, open 84° into the room |
| Hall north (y=6.6) | Office door | x 5.00 → 5.90 | 0 → 2.07 | hinged east, open 76° |
| Hall north (y=6.6) | Bathroom door | x 8.00 → 8.80 | 0 → 2.07 | hinged west, open 80° |
| South (y=0) | Living window | x 1.60 → 4.40 | 0.50 → 2.40 | 3 sashes, radiator below, linen drapes |
| South (y=0) | Kitchen window | x 7.30 → 8.90 | 1.08 → 2.30 | above the sink, roller blind |
| North (y=10.6) | Bedroom window | x 1.20 → 3.00 | 0.85 → 2.30 | drapes + sheer, radiator below |
| North (y=10.6) | Office window | x 5.00 → 6.60 | 0.85 → 2.30 | desk below, roller blind |
| North (y=10.6) | Bathroom window | x 8.45 → 9.15 | 1.40 → 2.20 | clear glass, roller blind half down |
| East (x=10) | Hall window | y 5.10 → 6.10 | 0.85 → 2.30 | daylight for the corridor |

Windows: white PVC frame set 0.10 in from the outer face, interior stone sill
projecting 40 mm, exterior ledge.

## Furniture zones (all against the named wall unless stated)

- **Hallway** — north wall west end: coat hooks at 1.78 with jackets, child's raincoat,
  backpack and tote; open shoe rack below (0.9 × 0.3 × 0.5) with mismatched pairs.
  South wall west end: console table (1.0 × 0.32 × 0.8) with key bowl and mail, arched
  mirror above. Kilim runner 4.6 × 0.8 down the middle. Slim walnut console and gallery wall
  between the two cased openings; plant at the east window.
- **Living room** — TV + low cabinet on the west wall; modular sofa set (sofa, cushions,
  throw and shag rug as one group) centred at x≈2.75, y≈2.2 facing the TV, coffee table
  in front of it; armchair south-west; reading chair south-east; shelving on the east
  wall; play mat, toy bin and child's table in the east third.
- **Kitchen** — L-shaped run: south wall (sink under the window, dishwasher) and east wall
  (oven/hob with hood); fridge north of the east run; marble-top dining table with six
  chairs in the middle of the room (centre x≈7.5, y≈2.75) carrying the child's bowl and
  cup, fruit and the day's clutter.
- **Primary bedroom** — 1.6 × 2.0 bed with a striped ticking duvet cover, head on the west wall, nightstand each side;
  1.7 m wardrobe on the south wall; crib and dresser on the east wall; clothes chair by
  the window.
- **Home office** — 2.0 × 0.92 scanned steel desk under the north window (monitor, keyboard and mouse on the left, laptop and lamp on the right); steel/oak bookshelf and printer
  on the west wall; two-seat sofa on the east wall under a corkboard.
- **Bathroom** — 1.7 × 0.75 tub along the north wall with screen and hand shower; washing
  machine in the north-west corner; toilet on the west wall; 0.9 m vanity with mirror
  cabinet and towel radiator on the east wall.

## Lighting

- Late-afternoon sun, elevation ≈ 18°, from the south-west (azimuth ≈ 225°), through the
  living-room and kitchen windows; HDRI sky fills the north rooms.
- Rooms are lit by their windows; ceiling fittings and pendants are off except in the hall
  and bathroom. Warm practicals (≈ 2700–3000 K) stay on: living-room floor lamp, hall console
  lamp, bedside lamp, desk lamp, under-cabinet kitchen puck lights, hood light, vanity light.
- The view through the windows is a photographed panorama of fields and trees, exposed
  brighter than the interior.

## Wear and imperfections (`apartment/wear.py`)

Applied last, on top of the finished materials, placed by world position:

- **Walls** — thin scratches at hand/bag height beside every door and cased opening, rubbed
  smears, finger marks around each light switch, shoe scuffs low by the entrance, splashes
  behind the kitchen bin; slow plaster undulation on all painted walls.
- **Woodwork** — knocks on door casings, scuffs along skirting boards, hand grime around
  door levers.
- **Soft furnishings** — stains on the sofa seat, chaise and arm (matted, sheen gone), dried
  milk on the living-room rug, trodden-in dirt on the hall runner, stains on the bedroom and
  office rugs, damp footprints on the bath mat.
- **Dust** — on upward faces of high shelves, cabinet and frame tops, skirting, sills,
  radiators and black metal furniture (heavier above reach height); patches on the floor
  under console tables, the living-room radiator, the desk, dresser and crib.
- **Kitchen** — grease spatter behind the hob, coffee and cup rings on worktop and table,
  crumbs around the plates and under the child's seat, spill marks on the floor.
- **Bathroom** — specks low on the mirror, limescale where the shower hits, water spots on the
  shower screen, per-tile tilt and uneven grout on the wall tile. Windows carry a faint dirt film.

## Cameras and stills

Nine hand-held views at 1.45–1.5 m, 28–35 mm on a 36 mm sensor, held like a phone: the whole
tilt is real pitch (verticals converge), with up to about 3° of roll.

| Still | Subject | Lens | Light |
|---|---|---|---|
| `living_room_01` | armchair, floor lamp, end of the TV cabinet | 35 mm | daylight + floor lamp |
| `living_room_02` | leather reading chair, plant, curtain by the window | 35 mm | direct sun |
| `kitchen_01` | fruit bowl, bottles, pot and pan by the hob | 35 mm | daylight |
| `hallway_01` | entrance door, coat hooks, shoe rack, console | 28 mm | on-camera flash |
| `hallway_02` | large plant and watering can by the east window | 35 mm | backlit window |
| `bedroom_01` | bedside table, lamp, clock, charging phone | 35 mm | bedside lamp |
| `bedroom_02` | worn dresser beside the crib | 28 mm | on-camera flash |
| `office_01` | lamp end of the scanned steel desk: old laptop, stapler, clipboard, glasses, notepad, mug | 35 mm | direct sun |
| `bathroom_01` | washer top with cleaners, tub corner with bottles | 35 mm | on-camera flash |

Flash power is metered per view (about 1.7× the ambient reading) and capped so white subjects
do not blow out. `out/preview_*.png` are diagnostics, `out/raw/*.exr` the scene-linear Cycles
frames with their metered exposure, `out/stills/*.png` the 1920 × 1080 finals after the
camera development in `apartment/render.py:photo_finish` (each still has its own settings in
`apartment/build.py:CAMERA`). Wide whole-room views were tried first and dropped: they scored
worst in blind tests.

## Asset sources

- Poly Haven models, textures and HDRIs — CC0 (`tools/fetch_assets.py`).
- Sofa set and dining set — appended from Blender's official demo scene
  `flat-archiviz.blend`, CC-BY Flavio Della Tommasa (malapixel.com); credit required if the
  renders are published.
- Everything else (shell, joinery, kitchen, bathroom, bed, soft goods, small props, artwork)
  is generated by the scripts in `apartment/`.
