"""Photo-scanned household objects from Google's "Scanned Objects" collection
(Google Research, CC-BY 4.0; fetched by tools/fetch_gso.py into assets/gso/NAME/).

Every model is one OBJ in metres, Z up, standing on z = 0 and centred on the origin, with a
single photographic albedo texture. The scanner captured no gloss, so each placement states a
roughness for the kind of surface it is (glazed mug, knitted shoe upper, printed carton)."""
import math
import os

import bpy
from mathutils import Euler, Matrix, Vector

from . import core as C

DIR = os.path.join(C.ASSETS, "gso")
_PROTO = {}
# short names used by rooms.py
N = {
    "mug_red": "ACE_Coffee_Mug_Kristen_16_oz_cup", "mug_teal": "Cole_Hardware_Mug_Classic_Blue",
    "mug_yellow": "Room_Essentials_Mug_White_Yellow", "mug_white": "Threshold_Porcelain_Coffee_Mug_All_Over_Bead_White",
    "teapot": "Threshold_Porcelain_Teapot_White", "drainer": "Room_Essentials_Dish_Drainer_Collapsible_White",
    "towel_waffle": "Tag_Dishtowel_Waffle_Gray_Checks_18_x_26", "towel_stripe": "Cole_Hardware_Dishtowel_Stripe",
    "sponge": "Big_O_Sponges_Assorted_Cellulose_12_pack", "bowl_white": "Threshold_Bead_Cereal_Bowl_White",
    "bowl_teal": "Room_Essentials_Bowl_Turquiose", "cereal": "Vans_Cereal_Honey_Nut_Crunch_11_oz_box",
    "cocoa": "Nestle_Nesquik_Chocolate_Powder_Flavored_Milk_Additive_109_Oz_Canister",
    "capsules": "Nescafe_16Count_Dolce_Gusto_Cappuccino_Capsules", "plate": "Threshold_Dinner_Plate_Square_Rim_White_Porcelain",
    "lunchbox": "Olive_Kids_Dinosaur_Land_Lunch_Box", "kid_backpack": "Olive_Kids_Dinosaur_Land_Sidekick_Backpack",
    "backpack": "Jansport_School_Backpack_Blue_Streak", "hat": "DPC_Handmade_Hat_Brown",
    "run_blue": "ASICS_GELChallenger_9_Royal_BlueWhiteBlack", "run_pink": "Reebok_ZIGLITE_RUSH",
    "kid_trainer": "Reebok_JR_ZIG_COOPERSTOWN_MR", "kid_deck": "GIRLS_DECKHAND", "sneaker_white": "Mens_Striper_Sneaker_in_White_rnp8HUli59Y",
    "boot_red": "Timberland_Mens_Earthkeepers_Newmarket_6Inch_Cupsole_Boot", "boot_ugg": "UGG_Bailey_Button_Womens_Boots_Black_7",
    "boat": "Womens_Bluefish_2Eye_Boat_Shoe_in_Tan",
    "duplo": "LEGO_Duplo_Build_and_Play_Box_4629", "abc": "Wooden_ABC_123_Blocks_50_pack", "truck": "FIRE_TRUCK",
    "dino": "Great_Dinos_Triceratops_Toy", "teddy": "Lovable_Huggable_Cuddly_Boutique_Teddy_Bear_Beige",
    "puzzle": "Melissa_Doug_Chunky_Puzzle_Vehicles", "monopoly": "My_Monopoly_Board_Game", "crayon_box": "Crayola_Crayons_Washable_24_crayons",
    "pencil_case": "Wishbone_Pencil_Case", "keyboard": "Kanex_MultiSync_Wireless_Keyboard", "mouse": "Razer_Taipan_Black_Ambidextrous_Gaming_Mouse",
    "drive": "Seagate_1TB_Backup_Plus_portable_drive_Silver", "tablet": "HP_1800_Tablet_8GB_7", "bin": "Hefty_Waste_Basket_Decorative_Bronze_85_liter",
    "basket": "Threshold_Basket_Natural_Finish_Fabric_Liner_Small", "clock": "Crosley_Alarm_Clock_Vintage_Metal",
    "bath_towel_blue": "Provence_Bath_Towel_Royal_Blue", "bath_towel_pink": "Threshold_Textured_Damask_Bath_Towel_Pink",
    "hand_towel": "Threshold_Hand_Towel_Blue_Medallion_16_x_27", "washcloth": "Home_Fashions_Washcloth_Linen",
    "soap_dish": "Threshold_Bamboo_Ceramic_Soap_Dish", "fish_holder": "Circo_Fish_Toothbrush_Holder_14995988",
    "jar_cream": "Perricone_MD_Neuropeptide_Firming_Moisturizer", "curl_cream": "Marc_Anthony_Strictly_Curls_Curl_Envy_Perfect_Curl_Cream_6_fl_oz_bottle",
    "argan": "Marc_Anthony_True_Professional_Oil_of_Morocco_Argan_Oil_Treatment", "cleanser": "Perricone_MD_Nutritive_Cleanser",
}


def _material(name, rough, spec):
    key = "GSO_{}_{:.2f}".format(name, rough)
    if key in C._MATS:
        return C._MATS[key]
    m, nt, bsdf, _ = C._new_mat(key)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = C._img(os.path.join(DIR, name, "materials", "textures", "texture.png"))
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Specular IOR Level"].default_value = spec
    # the scan's own shading is baked into the albedo; a faint bump from it keeps seams and
    # weave from looking printed on when the light rakes across
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.12
    bp.inputs["Distance"].default_value = 0.0015
    nt.links.new(tex.outputs["Color"], bw.inputs[0])
    nt.links.new(bw.outputs[0], bp.inputs["Height"])
    nt.links.new(bp.outputs[0], bsdf.inputs["Normal"])
    return m


def load(name):
    """Import one model once (kept out of the scene); returns (mesh datablock, lo, hi, heel_sign)."""
    name = N.get(name, name)
    if name in _PROTO:
        return _PROTO[name]
    path = os.path.join(DIR, name, "meshes", "model.obj")
    if not os.path.exists(path):
        raise FileNotFoundError("scanned object not downloaded: " + name)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="Y", up_axis="Z")
    new = [o for o in bpy.data.objects if o not in before]
    ob = new[0]
    me = ob.data
    me.name = "GSO_" + name
    me.use_fake_user = True
    for p in me.polygons:
        p.use_smooth = True
    co = [v.co.copy() for v in me.vertices]
    lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    # footwear: which end of the long axis carries the tall heel / ankle opening
    ax = 0 if hi.x - lo.x > hi.y - lo.y else 1
    mid = (lo[ax] + hi[ax]) / 2
    q = (hi[ax] - lo[ax]) / 4
    top_hi = max((c.z for c in co if c[ax] > mid + q), default=0.0)
    top_lo = max((c.z for c in co if c[ax] < mid - q), default=0.0)
    for o in new:
        bpy.data.objects.remove(o)
    _PROTO[name] = (me, lo, hi, (ax, 1.0 if top_hi > top_lo else -1.0))
    return _PROTO[name]


def size(name):
    _, lo, hi, _ = load(name)
    return hi - lo


def put(name, x, y, z, rot=0.0, scale=1.0, rough=0.5, spec=0.5, tilt=(0.0, 0.0), mirror=False, col=None, label=None, sink=0.0,
        pre=None):
    """Stand a scanned object with the bottom centre of its bounding box at (x, y, z), turned `rot`
    about Z. tilt = (about X, about Y) leans it. mirror flips it left-right (the other shoe of a pair).
    pre = Euler angles applied first, to lay a box on its back or a drive flat; the object is then
    anchored by the bounding box of that new pose."""
    short = name
    name = N.get(name, name)
    me, lo, hi, _ = load(name)
    o = bpy.data.objects.new(label or "Scan_" + short[:26], me)
    C._link(o, col)
    mat = _material(name, rough, spec)
    if not me.materials:
        me.materials.append(mat)
    o.material_slots[0].link = "OBJECT"            # the same scan may be glossier in one place than another
    o.material_slots[0].material = mat
    Pm = Euler(pre).to_matrix().to_4x4() if pre else Matrix.Identity(4)
    pts = [Pm @ Vector((a, b, c)) for a in (lo.x, hi.x) for b in (lo.y, hi.y) for c in (lo.z, hi.z)]
    lo2 = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi2 = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    anchor = Vector(((lo2.x + hi2.x) / 2, (lo2.y + hi2.y) / 2, lo2.z + sink))
    S = Matrix.Diagonal((-scale if mirror else scale, scale, scale, 1.0))
    o.matrix_world = (Matrix.Translation(Vector((x, y, z))) @ Euler((tilt[0], tilt[1], rot)).to_matrix().to_4x4()
                      @ S @ Matrix.Translation(-anchor) @ Pm)
    o["top"] = z + (hi2.z - lo2.z) * scale
    o["dims"] = tuple((hi2 - lo2) * scale)
    return o


def face(dx, dy):
    """Rotation that turns a front (-Y) towards direction (dx, dy)."""
    return math.atan2(dx, -dy)


def shoe(name, x, y, z, toe=0.0, mirror=False, rough=0.75, scale=1.0, tilt=(0.0, 0.0)):
    """One shoe with its toe pointing along heading `toe` (radians from +X)."""
    _, _, _, (ax, heel) = load(name)
    base = 0.0 if ax == 0 else math.pi / 2          # heading of the model's +long axis
    rot = toe - base + (math.pi if heel > 0 else 0.0)
    return put(name, x, y, z, rot, scale, rough, 0.35, tilt, mirror)


def pair(name, x, y, z, toe=0.0, gap=0.115, stagger=0.0, splay=0.06, **kw):
    """Left and right shoe side by side around (x, y); the second is the mirrored scan."""
    c, s = math.cos(toe), math.sin(toe)
    out = []
    for i, sgn in enumerate((-1.0, 1.0)):
        px = x - s * sgn * gap / 2 + c * sgn * stagger / 2
        py = y + c * sgn * gap / 2 + s * sgn * stagger / 2
        out.append(shoe(name, px, py, z, toe + sgn * splay, mirror=i == 1, **kw))
    return out
