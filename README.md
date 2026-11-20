# Generate3D: a lived-in apartment, generated in Blender

Python scripts that build a photorealistic two-bedroom apartment for a family of three
(two adults, one toddler) in Blender, render thirteen hand-held "phone photo" stills of it,
and fly a camera through every room for a 2K video. Rooms are furnished with photo-scanned
and artist-made assets and then worn in: stains, scuffs by the doors, dust on hard-to-reach
surfaces, clutter where people actually leave things.

The layout, materials, lighting, camera list and asset credits are specified in
[PLAN.md](PLAN.md); the scripts follow it.

## What's in `out/`

| Path | What it is |
| --- | --- |
| `out/apartment_scene.blend` | The finished scene (Git LFS). One timeline frame per still camera; markers carry the view names. |
| `out/stills/*.png` | The 13 stills, 1920 × 1080, after the camera "development" (glare, lens distortion, sensor noise). |
| `out/raw/*.exr` | Scene-linear Cycles renders of the stills, used to re-develop them without re-rendering. Not in git. |
| `out/preview_top.png` | Roofless top view, to check the floor plan. |
| `out/flythrough/apartment_2k.mp4` | Fly-through video, 2560 × 1440, 24 fps, 92.5 s (Git LFS). |
| `out/flythrough/path.png` | The fly-through camera path drawn on the plan. |
| `out/flythrough/passes/` | One frame per room as a Turbo-coloured depth map and as an object map, plus `sheet.jpg` comparing them with the video frames. |
| `out/flythrough/frames/` | The 2,220 PNG frames the video was encoded from. Not in git. |

## Requirements

- **Blender 5.3** (5.x should work; older versions cannot open the saved scene).
- **Python 3** for the download scripts and **git-lfs** to get the `.blend` and the video
  when cloning (`git lfs install` before `git clone`).
- **ffmpeg** to encode the video.
- A GPU is strongly recommended: Cycles uses Metal on a Mac and OptiX or CUDA on NVIDIA.
  A 2K fly-through frame takes about 1.3 min on an M3 Max and about 7 min on a GTX 1060.

## 1. Get the assets (about 2 GB, not in git)

All sources are free and need no account. See "Asset sources" in [PLAN.md](PLAN.md) for
licences; several are CC-BY and must be credited if you publish renders.

```sh
python3 tools/fetch_assets.py          # Poly Haven models, textures, HDRIs (CC0) -> assets/
python3 tools/fetch_gso.py get NAME…   # Google Scanned Objects (CC-BY 4.0) -> assets/gso/NAME/
```

`apartment/gso.py` (the `N` table) and `apartment/rooms.py` name the scanned objects that are
used; `python3 tools/fetch_gso.py list [regex]` searches the catalogue of 1,033 models.

Fetched by hand:

- `assets/scenes/{kitchen,bathroom,bedroom}/`: unzip
  `https://benedikt-bitterli.me/resources/mitsuba/<name>.zip` from Benedikt Bitterli's
  [rendering resources](https://benedikt-bitterli.me/resources/).
- `assets/demo/flat-archiviz.blend`: from <https://download.blender.org/demo/> (sofa and dining
  sets, CC-BY Flavio Della Tommasa).
- `assets/backdrops/{balcony,stuttgart_suburbs}.jpg`: Poly Haven panoramas (tonemapped JPGs)
  seen through the windows.

## 2. Build the scene

Everything is driven from `apartment/build.py`. Run it in a headless Blender from the
repository root:

```sh
blender -b --factory-startup --python-expr "
import sys; sys.path.insert(0, '.')
import apartment.build as B
B.build()      # shell, joinery, furniture, props, wear, lights, cameras
B.save()       # -> out/apartment_scene.blend  (the build takes about 3 min on an M3 Max)
"
```

Or use the scene that is already saved in `out/apartment_scene.blend`.

| Module | Builds |
| --- | --- |
| `shell.py` | Walls, floors, ceilings, doors, windows, skirting, cornices |
| `rooms.py` | Furniture and props room by room |
| `fixtures.py`, `props.py`, `art.py` | Generated fittings, small objects and artwork |
| `mitsuba.py` | Imports the artist-made kitchen, bathroom and bed from Bitterli's scenes |
| `gso.py` | Places Google Scanned Objects (shoes in pairs, mugs, towels, toys, …) |
| `wear.py` | Imperfections: stains, scratches, smudges, dust on upward faces, film on glass, crumbs, a crayon scribble |
| `render.py` | World and sun, metering, Cycles settings, the photographic finish of the stills |

## 3. Render the stills

In the same Blender session after `B.build()`:

```python
B.shot("kitchen_01", "final")    # -> out/raw/kitchen_01.exr and out/stills/kitchen_01.png
B.shot("kitchen_01")             # quick preview -> out/preview_kitchen_01.png (+ out/raw/preview_kitchen_01.exr)
B.shot("top")                    # roofless plan check -> out/preview_top.png
B.refinish()                     # re-develop every out/raw/*.exr into out/stills/ without rendering
B.check_floating()               # list props that float or sink into their support
```

The view names are the keys of `VIEWS` in `apartment/build.py` and are listed in
[PLAN.md](PLAN.md#cameras-and-stills). Opening `out/apartment_scene.blend` and pressing
Render Animation also renders all 13 views (without the photographic finish).

## 4. Render the fly-through

`apartment/flythrough.py` runs on the saved scene:

```sh
B="blender -b out/apartment_scene.blend -P apartment/flythrough.py --"
$B plan                 # draw the camera path -> out/flythrough/path.png
$B preview              # 640 × 360 EEVEE frames, every 2nd frame -> out/flythrough/preview_frames/
$B final                # 2560 × 1440 Cycles frames -> out/flythrough/frames/
$B final 950 2220       # only a range of frames
$B passes               # depth and object maps, one frame per room -> out/flythrough/passes/

ffmpeg -framerate 24 -i out/flythrough/frames/f_%04d.png \
       -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p out/flythrough/apartment_2k.mp4
```

The camera starts at the front door and visits the living room, bedroom, kitchen, office and
bathroom in that order. In each room it circles along the walls with its back to the wall,
looking across the room. `final` keeps existing frames, so a stopped render picks up where it
left off. Settings through environment variables:

| Variable | Default | Effect |
| --- | --- | --- |
| `FLY_SAMPLES` | 128 | Cycles samples per pixel (adaptive, denoised) |
| `FLY_CPU` | 0 | `1` lets the CPU render alongside an NVIDIA/AMD GPU (barely faster on a GTX 1060) |
| `FLY_CLAIM` | – | A command that hands out frame numbers, to share one render between machines (below) |

### Sharing the render with a second machine

For long renders, the frames can be split between two machines without rendering any frame
twice:

1. Copy `apartment/` and a packed copy of the scene to the second machine (in Blender:
   File › External Data › Pack Resources, then save). Start it with `final FIRST LAST`; it
   renders upwards and skips every frame whose file already exists.
2. On this machine, set the SSH target and the remote frames folder in
   `scratch/claim_frame.py` and run `scratch/render_mac_share.sh`. It renders downwards from
   the last frame. Before each frame it leaves an empty placeholder file of that name on the
   other machine, which then skips it. It stops when it gets within two frames of the other
   machine.
3. Stop it with `pkill -f render_mac_share.sh; pkill -f apartment/flythrough.py`, then run
   `python3 -I scratch/claim_frame.py release` to drop the placeholder of a frame that did not
   finish.
4. When all frames are done, copy the other machine's non-empty frames back (skip the empty
   placeholders) and encode.

`scratch/render_win.bat` is the Windows launcher. Run it as a scheduled task, because Windows
OpenSSH stops programs started from an SSH session when the session closes.
`scratch/fix_frames.py` merges the overlapping window-frame boxes in the packed file, which
CUDA otherwise renders as black squares.

## Working through the MCP bridge (optional)

While developing, the scene was built live in a headless Blender controlled through an MCP
server:

```sh
tools/start_blender_mcp.sh &          # headless Blender serving the bridge on port 9877
tools/bx exec scratch/run.py          # run a script inside it (scratch/run.json picks build/shots/save)
tools/bx code 'import bpy; print(len(bpy.data.objects))'
```

`tools/bx` and `.mcp.json` point to a local install of the Blender Lab MCP server; adjust
the paths to yours. Calls time out after about 5–10 minutes, so long renders run in their own
Blender as above. `scratch/` holds the helper and diagnostic scripts used along the way.

## The prompt

The project was built by Claude Code, an AI coding agent, driving Blender through the MCP
bridge. This is the brief it worked from, lightly edited, followed by the requests that
shaped it along the way.

> **Build a photorealistic 3D apartment interior in Blender, through the Blender MCP server,
> that looks indistinguishable from real interior photography at first glance.**
>
> **1. Plan and layout.** Before modelling, write a spatial blueprint to `PLAN.md` with exact
> metric dimensions and door and window positions, so scale stays consistent between rooms.
> The apartment is on one level: a large central hallway connecting a living room, a primary
> bedroom, a home office, a kitchen and a bathroom. Model the architecture properly: wall
> thicknesses, skirting boards, door frames with handles and hinges, window frames with
> sills, ceiling cornices, sockets and light switches.
>
> **2. Lived-in set dressing for a family of three (two adults, one young child).** Every room
> should look lived in: neither a sterile catalogue shot nor a mess, with objects where people
> actually leave them.
>
> - *Hallway:* shoe rack with mismatched everyday shoes, coat hooks with jackets and a
>   backpack, a console with keys and mail, a runner rug.
> - *Living room:* sofa with creased cushions and a draped blanket; coffee table with mugs,
>   a remote and a book; TV stand; plants; signs of a child (a toy bin, a picture book on
>   the rug).
> - *Kitchen:* cabinets, appliances, a coffee maker, a dish rack with drying dishes, a
>   chopping board, a fruit bowl, spices, fridge magnets and notes.
> - *Office:* desk with monitor, keyboard, mouse, laptop, desk lamp, notebook and pen, a mug,
>   cables, and a bookshelf with books of varied heights and storage boxes.
> - *Bedroom:* casually made bed with layered bedding, bedside tables with lamps, chargers
>   and books, a wardrobe, a chair with clothes draped over it.
> - *Bathroom:* vanity with toothbrushes, soap, skincare bottles, unevenly hung towels, a bath
>   mat, toilet, and a bath or shower with shampoo bottles.
>
> **3. Materials and lighting (Cycles).** Physically based materials with real wear: roughness
> variation, micro-scratches, fabric weave, wood grain, tile grout, smudges on glass and
> screens. Light with late-afternoon daylight through the windows plus warm practical lamps
> (desk lamp, under-cabinet LEDs, floor and bedside lamps), for natural contrast and colour
> temperature.
>
> **4. Critique loop.** Place cameras at eye height (1.3–1.6 m) with natural focal lengths
> (24–35 mm), render quick previews, and look at them critically for anything that gives the
> image away as CG: floating objects, intersecting meshes, unnatural symmetry, sterile
> surfaces, flat light, wrong scale. Fix every defect and re-render until they pass.
>
> **5. Deliverables.** A clean `out/apartment_scene.blend` with one collection per room, and
> denoised 1920 × 1080 Cycles stills of every room and the hallway in `out/stills/`.

Follow-up requests:

- *Imperfections:* add stains on the rug and sofa, scuffs on the walls where hands and bags
  touch them (by the doors), and dust on hard-to-reach surfaces.
- *Better assets:* replace generated objects with photo-scanned and artist-made ones from
  free sources.
- *Fly-through:* render a 2K video flying through the whole apartment with the best render
  settings. In each room the camera circles along the walls with its back to the wall,
  looking at the farthest point of the room. Visit the rooms in the order they lie: living
  room, the bedroom across the hall, kitchen, office, bathroom. Show a low-resolution
  preview for approval first.
- *Data passes:* render one frame per room as a Turbo-coloured depth map and as an object map.

## Credits

Poly Haven (CC0) · Google Research, *Scanned Objects* (CC-BY 4.0) · "Country Kitchen" by
Jay-Artist (CC-BY), "Contemporary Bathroom" by Mareck (CC0), "Bedroom" by SlykDrako (CC0),
via Benedikt Bitterli's rendering resources · sofa and dining sets from Blender's
`flat-archiviz.blend` demo, CC-BY Flavio Della Tommasa (malapixel.com).
