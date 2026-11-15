#!/usr/bin/env python3
"""Download the CC0 Poly Haven assets the apartment generator uses.

    python3 tools/fetch_assets.py            # download everything missing
    python3 tools/fetch_assets.py --dry      # only report sizes

Layout:
    assets/models/<id>/<id>_<res>.blend  (+ textures/ next to it)
    assets/textures/<id>/<id>_<map>_<res>.jpg
    assets/hdris/<id>_<res>.hdr
"""
import concurrent.futures as cf
import json
import os
import sys
import urllib.request

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
UA = {"User-Agent": "apartment-generator/1.0"}
API = "https://api.polyhaven.com/files/"

# Large furniture gets 2k textures, small props 1k.
MODELS_2K = """
sofa_03 sofa_02 modern_arm_chair_01 mid_century_lounge_chair modern_coffee_table_01 coffee_table_round_01
modern_wooden_cabinet side_table_01 side_table_tall_01 wooden_bookshelf_worn wooden_display_shelves_01
painted_wooden_shelves dining_table dining_chair_02 ClassicNightstand_01 painted_wooden_nightstand
drawer_cabinet vintage_wooden_drawer_01 metal_office_desk steel_frame_shelves_01 ClassicConsole_01
painted_wooden_bench ornate_mirror_01 round_wooden_table_01 painted_wooden_cabinet vintage_cabinet_01
Ottoman_01 painted_wooden_chair_01 wooden_stool_01 television_02 modern_ceiling_lamp_01
""".split()
MODELS_1K = """
throw_pillows_01 potted_plant_01 potted_plant_02 potted_plant_04 pachira_aquatica_01 anthurium_botany_01
fern_02 book_encyclopedia_set_01 decorative_book_set_01 hanging_picture_frame_01 hanging_picture_frame_02
hanging_picture_frame_03 fancy_picture_frame_01 standing_picture_frame_01 standing_picture_frame_02
ceramic_vase_01 ceramic_vase_02 ceramic_vase_03 ceramic_vase_04 gamepad gaming_console tea_set_01
wicker_basket_01 wicker_basket_02 football baseball_01 rubber_duck_toy wall_clock alarm_clock_01
desk_lamp_arm_01 round_spectacles classic_laptop binder_notebook office_notepads stationery_supplies
clipboard vintage_stapler cardboard_box_01 boombox Camera_01 postcard_set_01 Ukulele_01
digital_wrist_watch magnifying_glass_01 electric_stove vintage_microwave vintage_electric_kettle
food_apple_01 bananas lemon croissant hamburger_buns yellow_onion sweet_potato food_avocado_01
food_pears_asian_01 wooden_bowl_01 wooden_bowl_02 wooden_cutting_board wooden_spoon brass_pan_01
pot_enamel_01 jug_01 wine_bottles_01 carrot_cake all_purpose_cleaner multi_cleaner_bottle
metal_trash_can plastic_broom dustpan long_life_food russian_food_cans_01 bleach_bottle drain_cleaner
plunger rubber_boots vintage_suitcase fishermans_hat chess_set plastic_container trashbag
metal_stool_01 carved_wooden_elephant garden_gnome plastic_thermos lightbulb_led watering_can_metal_01
planter_pot_clay ceramic_pot metal_jug brass_vase_01 wooden_candlestick mantel_clock_01 jug_01
""".split()
TEXTURES = """
laminate_floor_02 herringbone_parquet large_floor_tiles_02 floor_tiles_06 terrazzo_tiles marble_tiles
long_white_tiles square_tiles_03 painted_plaster_wall white_plaster_02 marble_01 oak_veneer_01
walnut_veneer_02 white_oak_veneer plywood rough_linen cotton_jersey wool_boucle terry_cloth
fabric_pattern_07 fabric_pattern_05 gingham_check knitted_fleece poly_wool_herringbone velour_velvet
denim_fabric quatrefoil_jacquard_fabric waffle_pique_cotton brown_leather book_pattern curly_teddy_natural
""".split()
TEX_MAPS = ("Diffuse", "nor_gl", "Rough", "arm")
HDRIS = {"kloofendal_48d_partly_cloudy_puresky": "4k", "syferfontein_18d_clear_puresky": "4k"}


def api(asset):
    req = urllib.request.Request(API + asset, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))


def plan():
    jobs = []  # (url, dest, size)

    def add(entry, dest):
        jobs.append((entry["url"], dest, entry.get("size", 0)))

    def model(asset, res):
        try:
            files = api(asset)["blend"]
        except Exception as ex:  # noqa: BLE001
            return "model {}: {}".format(asset, ex)
        res_ = res if res in files else sorted(files)[0]
        entry = files[res_]["blend"]
        base = os.path.join(ROOT, "models", asset)
        add(entry, os.path.join(base, os.path.basename(entry["url"])))
        for rel, inc in entry.get("include", {}).items():
            add(inc, os.path.join(base, rel))
        return None

    def texture(asset):
        try:
            files = api(asset)
        except Exception as ex:  # noqa: BLE001
            return "texture {}: {}".format(asset, ex)
        for m in TEX_MAPS:
            if m in files and "2k" in files[m] and "jpg" in files[m]["2k"]:
                e = files[m]["2k"]["jpg"]
                add(e, os.path.join(ROOT, "textures", asset, "{}_{}.jpg".format(asset, m)))
        return None

    def hdri(asset, res):
        e = api(asset)["hdri"][res]["hdr"]
        add(e, os.path.join(ROOT, "hdris", "{}_{}.hdr".format(asset, res)))
        return None

    with cf.ThreadPoolExecutor(12) as ex:
        futs = [ex.submit(model, a, "2k") for a in dict.fromkeys(MODELS_2K)]
        futs += [ex.submit(model, a, "1k") for a in dict.fromkeys(MODELS_1K)]
        futs += [ex.submit(texture, a) for a in TEXTURES]
        futs += [ex.submit(hdri, a, r) for a, r in HDRIS.items()]
        errors = [f.result() for f in futs if f.result()]
    return jobs, errors


def fetch(job):
    url, dest, size = job
    if os.path.exists(dest) and (not size or os.path.getsize(dest) == size):
        return 0
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    tmp = dest + ".part"
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    os.replace(tmp, dest)
    return os.path.getsize(dest)


def main():
    jobs, errors = plan()
    total = sum(j[2] for j in jobs)
    print("files: {}  total: {:.0f} MB".format(len(jobs), total / 1e6))
    for e in errors:
        print("PLAN ERROR", e)
    if "--dry" in sys.argv:
        return
    done = 0
    failed = []
    with cf.ThreadPoolExecutor(16) as ex:
        futs = {ex.submit(fetch, j): j for j in jobs}
        for f in cf.as_completed(futs):
            try:
                done += f.result()
            except Exception as exn:  # noqa: BLE001
                failed.append((futs[f][1], str(exn)))
    print("downloaded {:.0f} MB, failed {}".format(done / 1e6, len(failed)))
    for d, e in failed[:20]:
        print("FAIL", d, e)


if __name__ == "__main__":
    main()
