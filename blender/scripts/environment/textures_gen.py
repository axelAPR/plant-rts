# plantRTS — Kit d'environnement : textures générées (style peint à la main).
# blender -b --python blender/scripts/environment/textures_gen.py
#
# Complète le pack fourni (blender/Texture imp/) pour ce qu'il ne couvre pas :
# boiseries peintes et vitres (atlas Env_Trim), écorce, feuillage, mousse,
# carrosserie, métal, pneu, tissu. Même langage que le pack : bruit fractal
# périodique (textures raccordables), posterisé en 5 nuances (ombre profonde, ombre,
# base, lumière, accent), traits sombres pour les fissures et les fibres.
# Écrit des PNG 1024 px dans blender/environment/textures/ (déterministe : graines fixes).

import os, sys
import numpy as np
import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(ROOT, "blender", "environment", "textures")
N = 1024


def hexes(*codes):
    return np.array([[int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5)] for c in codes], dtype=np.float32)


def noise(seed, scale, aspect=(1.0, 1.0), n=N):
    """Bruit fractal périodique (raccordable) : bruit blanc filtré en fréquence.
    `scale` : taille caractéristique (en fraction de l'image) ; `aspect` étire (x, y)."""
    rnd = np.random.default_rng(seed)
    white = rnd.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None] * aspect[1]
    fx = np.fft.fftfreq(n)[None, :] * aspect[0]
    f = np.sqrt(fx * fx + fy * fy)
    spectrum = np.fft.fft2(white) * np.exp(-(f * scale * n / 2.5) ** 2) / np.maximum(f, 1.0 / n) ** 0.6
    out = np.real(np.fft.ifft2(spectrum))
    out -= out.min()
    return out / out.max()


def posterize(field, palette, cuts):
    """Aplats de couleur : `cuts` (croissants) découpent le champ en len(palette) zones."""
    idx = np.digitize(field, cuts)
    return palette[np.clip(idx, 0, len(palette) - 1)]


def lines(field, width):
    """Masque des lignes de niveau 0,5 d'un champ (fissures, fibres)."""
    return np.abs(field - 0.5) < width


def darken(img, mask, color, amount=1.0):
    img[mask] = img[mask] * (1 - amount) + color * amount
    return img


def save(name, img):
    os.makedirs(OUT, exist_ok=True)
    h, w = img.shape[:2]
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(img, 0, 1)
    im = bpy.data.images.new(name, w, h, alpha=False)
    # Blender : première ligne = bas de l'image ; on retourne pour garder l'orientation.
    im.pixels = rgba[::-1].ravel()
    im.filepath_raw = os.path.join(OUT, name + ".png")
    im.file_format = 'PNG'
    im.save()
    bpy.data.images.remove(im)
    print("TEXTURE", name)


def painted_wood(seed, palette):
    """Bois peint : fibres verticales douces, nœuds rares, usure claire."""
    grain = noise(seed, 0.012, aspect=(1.0, 0.08))
    blotch = noise(seed + 1, 0.08)
    field = 0.65 * grain + 0.35 * blotch
    img = posterize(field, palette, [0.22, 0.4, 0.68, 0.86])
    fibres = lines(noise(seed + 2, 0.02, aspect=(1.0, 0.05)), 0.006)
    return darken(img, fibres, palette[1], 0.6)


def trim_atlas():
    """Env_Trim : U 0–0,4 bois peint blanc, 0,4–0,6 bois peint rouge, 0,6–0,8 bois
    naturel, 0,8–1 vitre. Fil du bois vertical (le long de V)."""
    white = painted_wood(10, hexes("#9E9384", "#C9BFAE", "#E6DECD", "#F4EEE1", "#FFFBF2"))
    red = painted_wood(20, hexes("#4A1E24", "#6E2A2E", "#8E3A38", "#A84E46", "#C26A5A"))
    wood = painted_wood(25, hexes("#3A2422", "#5C3A2C", "#85593A", "#A8774A", "#CC9C62"))
    img = np.zeros((N, N, 3), dtype=np.float32)
    c1, c2, c3 = int(N * 0.4), int(N * 0.6), int(N * 0.8)
    img[:, :c1] = white[:, :c1]
    img[:, c1:c2] = red[:, :c2 - c1]
    img[:, c2:c3] = wood[:, :c3 - c2]
    # Vitre : dégradé nuit → reflet, deux traînées claires en diagonale, liseré sombre.
    w = N - c3
    y = np.linspace(0, 1, N)[:, None] * np.ones((1, w))
    x = np.ones((N, 1)) * np.linspace(0, 1, w)[None, :]
    glass = hexes("#24344A", "#2F4862", "#3E5E7A", "#5E86A2", "#A9CBE0")
    g = posterize(0.75 * y + 0.25 * noise(30, 0.05, n=N)[:, :w], glass, [0.25, 0.5, 0.72, 0.95])
    for k, (c, wdt) in enumerate(((0.4, 0.07),)):
        streak = np.abs((x * 0.6 + (1 - y)) - (c + 0.45)) < wdt
        g[streak] = g[streak] * 0.4 + glass[4] * 0.6
    edge = (x < 0.04) | (x > 0.96) | (y < 0.02) | (y > 0.98)
    g[edge] = glass[0]
    img[:, c3:] = g
    save("trim_atlas", img)


def worley(seed, count, stretch=(1.0, 1.0), n=N):
    """Cellules de Voronoï périodiques : distance au plus proche (f1) et au second (f2)
    germe, sur un tore (raccordable). `stretch` allonge les cellules (x, y)."""
    rnd = np.random.default_rng(seed)
    pts = rnd.uniform(0, n, (count, 2))
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    f1 = np.full((n, n), 1e9, dtype=np.float32)
    f2 = np.full((n, n), 1e9, dtype=np.float32)
    ident = np.zeros((n, n), dtype=np.int32)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(xx - px); dx = np.minimum(dx, n - dx) / stretch[0]
        dy = np.abs(yy - py); dy = np.minimum(dy, n - dy) / stretch[1]
        d = np.sqrt(dx * dx + dy * dy)
        closer = d < f1
        f2 = np.where(closer, f1, np.minimum(f2, d))
        ident = np.where(closer, i, ident)
        f1 = np.where(closer, d, f1)
    return f1, f2, ident


def bark():
    """Écorce : plaques verticales bombées, crevasses sombres, éclairage par la gauche."""
    pal = hexes("#2A1A1F", "#45302A", "#654737", "#87634B", "#A98766")
    f1, f2, ident = worley(40, 70, stretch=(1.0, 4.5))
    edge = f2 - f1                                   # 0 sur les crevasses
    rnd = np.random.default_rng(41)
    plate_tone = rnd.uniform(-0.12, 0.12, 70)[ident]
    gx = np.gradient(edge, axis=1)
    light = np.clip(0.5 + gx * 0.08, 0, 1)
    field = 0.45 * np.clip(edge / 40.0, 0, 1) + 0.35 * light + 0.2 * noise(42, 0.03, aspect=(1.0, 0.2)) + plate_tone
    img = posterize(field, pal, [0.28, 0.42, 0.58, 0.74])
    img[edge < 4.0] = pal[0]
    fibres = lines(noise(43, 0.01, aspect=(1.0, 0.08)), 0.008) & (edge > 8.0)
    img = darken(img, fibres, pal[1], 0.7)
    save("bark", img)


def foliage(name, pal, seed):
    """Feuillage : grappes de feuilles (ellipses orientées), ombrées du haut vers le
    bas de chaque feuille, sur un fond sombre ; tamponnées en boucle (raccordable)."""
    rnd = np.random.default_rng(seed)
    img = posterize(noise(seed, 0.05), pal[:3], [0.4, 0.7])
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    for _ in range(900):
        cx, cy = rnd.uniform(0, N, 2)
        L, W = rnd.uniform(28, 52), rnd.uniform(12, 20)
        a = rnd.uniform(0, np.pi)
        x0, y0 = int(cx - L - 2), int(cy - L - 2)
        size = int(2 * L + 5)
        sub_y, sub_x = np.mgrid[0:size, 0:size].astype(np.float32)
        dx, dy = sub_x + x0 - cx, sub_y + y0 - cy
        u = dx * np.cos(a) + dy * np.sin(a)
        v = -dx * np.sin(a) + dy * np.cos(a)
        inside = (u / L) ** 2 + (v / W) ** 2 < 1.0
        if not inside.any():
            continue
        shade = np.clip(0.5 + 0.5 * (v / W) + rnd.uniform(-0.25, 0.25), 0, 1)
        tone = np.digitize(shade, [0.3, 0.6, 0.85]) + 1
        col = pal[np.clip(tone, 1, 4)]
        rib = inside & (np.abs(v) < 1.6) & (np.abs(u) < L * 0.8)
        ys = (np.arange(size) + y0) % N
        xs = (np.arange(size) + x0) % N
        block = img[np.ix_(ys, xs)]
        block[inside] = col[inside]
        block[rib] = pal[1]
        img[np.ix_(ys, xs)] = block
    save(name, img)


def flat_paint(name, pal, seed, cuts=(0.2, 0.45, 0.75, 0.93)):
    img = posterize(0.6 * noise(seed, 0.08) + 0.4 * noise(seed + 1, 0.02), pal, list(cuts))
    save(name, img)


def car_paint():
    """Carrosserie : peinture presque unie, reflets très doux, rares éraflures."""
    pal = hexes("#46698E", "#4F749A", "#587FA6", "#6690B6", "#93B6D4")
    field = 0.85 * noise(55, 0.35) + 0.15 * noise(56, 0.12)
    img = posterize(field, pal, [0.08, 0.22, 0.8, 0.95])
    scratches = lines(noise(57, 0.004, aspect=(1.0, 0.15)), 0.0012) & (noise(58, 0.1) > 0.75)
    img = darken(img, scratches, pal[4], 0.6)
    save("car_paint", img)


def metal():
    pal = hexes("#3A3F47", "#5B626C", "#878E98", "#B3B9C1", "#E2E6EA")
    field = 0.55 * noise(60, 0.01, aspect=(0.05, 1.0)) + 0.45 * noise(61, 0.08)
    save("metal", posterize(field, pal, [0.18, 0.4, 0.7, 0.9]))


def rubber():
    pal = hexes("#16161A", "#222228", "#2E2E35", "#3C3C44", "#55555E")
    img = posterize(noise(70, 0.03), pal, [0.2, 0.45, 0.75, 0.93])
    save("rubber", img)


def moss():
    pal = hexes("#24402E", "#36593A", "#4E7746", "#6F9452", "#9DB86A")
    field = 0.6 * noise(80, 0.03) + 0.4 * noise(81, 0.006)
    img = posterize(field, pal, [0.25, 0.45, 0.68, 0.88])
    save("moss", img)


def cloth():
    pal = hexes("#9C968A", "#BDB7A9", "#D9D3C4", "#ECE7DA", "#FAF7EE")
    weave = noise(90, 0.004)
    field = 0.6 * noise(91, 0.06, aspect=(0.3, 1.0)) + 0.4 * weave
    save("cloth", posterize(field, pal, [0.15, 0.35, 0.7, 0.9]))


# ---------------------------------------------------------------- Variantes de couleur

def load_png(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(im)
    return px


def rgb_to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn + 1e-8
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6.0
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-8), 0)
    return np.stack([h % 1.0, s, mx], -1)


def hsv_to_rgb(hsv):
    h, s, v = hsv[..., 0] * 6, hsv[..., 1], hsv[..., 2]
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    choices = [np.stack(c, -1) for c in ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))]
    out = np.zeros_like(hsv)
    for k in range(6):
        out[i == k] = choices[k][i == k]
    return out


def recolor(source, name, hue=None, sat=1.0, val=1.0):
    """Variante de couleur d'une texture du dossier : teinte remplacée (`hue`, 0–1) ou
    conservée, saturation et valeur multipliées. Les ombres et les traits sont gardés."""
    rgb = load_png(os.path.join(OUT, source))
    hsv = rgb_to_hsv(rgb)
    if hue is not None:
        hsv[..., 0] = hue
    hsv[..., 1] = np.clip(hsv[..., 1] * sat, 0, 1)
    hsv[..., 2] = np.clip(hsv[..., 2] * val, 0, 1)
    save(name, hsv_to_rgb(hsv))


def variants():
    for name, hue, sat, val in (("siding_yellow", 0.13, 0.85, 1.05), ("siding_pink", 0.97, 0.55, 1.05),
                                ("siding_white", None, 0.12, 1.12), ("siding_mint", 0.38, 0.55, 1.0),
                                ("siding_lavender", 0.72, 0.35, 1.0), ("siding_rotten", 0.12, 0.25, 0.6)):
        recolor("pack_bardage_bois.png", name, hue, sat, val)
    for name, hue, sat, val in (("roof_slate", 0.6, 0.35, 0.85), ("roof_green", 0.36, 0.5, 0.8),
                                ("roof_brown", 0.07, 0.7, 0.75), ("roof_purple", 0.8, 0.45, 0.7),
                                ("roof_rotten", 0.75, 0.3, 0.55)):
        recolor("pack_toit_tuiles.png", name, hue, sat, val)
    for name, hue, sat, val in (("plaster_pink", 0.02, 1.4, 1.0), ("plaster_mint", 0.33, 0.9, 1.0),
                                ("plaster_grey", None, 0.15, 0.9)):
        recolor("pack_mur_crepi.png", name, hue, sat, val)
    recolor("pack_mur_briques.png", "brick_grey", None, 0.15, 0.95)
    recolor("pack_roche.png", "rock_grey", 0.08, 0.18, 0.72)
    recolor("foliage.png", "foliage_autumn", 0.075, 1.7, 1.35)
    recolor("foliage_shadow.png", "foliage_autumn_shadow", 0.04, 1.6, 1.25)
    recolor("bark.png", "bark_dead", 0.75, 0.15, 0.8)
    recolor("pack_fer_rouille.png", "rust_dull", None, 0.55, 0.78)
    recolor("pack_planches_bois.png", "wood_dark", 0.95, 0.35, 0.55)
    for name, pal in (("car_paint_red", ("#6E2226", "#842B2E", "#9A3634", "#B0463E", "#D27A68")),
                      ("car_paint_yellow", ("#8E6A1E", "#A87E24", "#C2962E", "#D6AC40", "#EBCF7A")),
                      ("car_paint_green", ("#2E5240", "#37604A", "#416E54", "#4F8062", "#86AE8E")),
                      ("car_paint_white", ("#A9A79F", "#C2C0B8", "#D6D4CC", "#E6E4DC", "#F7F5EE"))):
        field = 0.85 * noise(55, 0.35) + 0.15 * noise(56, 0.12)
        save(name, posterize(field, hexes(*pal), [0.08, 0.22, 0.8, 0.95]))


# ---------------------------------------------------------------- Nouvelles matières

def asphalt():
    pal = hexes("#2A2C33", "#34363E", "#3E4149", "#4A4D56", "#6A6D76")
    field = 0.55 * noise(100, 0.05) + 0.45 * noise(101, 0.004)
    img = posterize(field, pal, [0.18, 0.42, 0.7, 0.9])
    cracks = lines(noise(102, 0.04), 0.004) & (noise(103, 0.15) > 0.62)
    save("asphalt", darken(img, cracks, pal[0], 0.9))


def concrete_slabs():
    """Trottoir : dalles de béton (4 × 4 par texture), joints sombres, taches."""
    pal = hexes("#7F7B74", "#99958D", "#B0ACA3", "#C4C0B7", "#DAD6CC")
    img = posterize(0.6 * noise(110, 0.08) + 0.4 * noise(111, 0.006), pal, [0.15, 0.35, 0.72, 0.92])
    yy, xx = np.mgrid[0:N, 0:N]
    img[((xx % (N // 4)) < 6) | ((yy % (N // 4)) < 6)] = pal[0]
    save("concrete", img)


def straw():
    pal = hexes("#8A6A2A", "#A88634", "#C6A446", "#DCBE5E", "#F0DA8A")
    field = 0.7 * noise(130, 0.004, aspect=(1.0, 0.04)) + 0.3 * noise(131, 0.05)
    img = posterize(field, pal, [0.2, 0.42, 0.68, 0.88])
    save("straw", darken(img, lines(noise(132, 0.006, aspect=(1.0, 0.05)), 0.004), pal[0], 0.7))


def burlap():
    pal = hexes("#6A5638", "#83704A", "#9C875C", "#B29E72", "#CBB98E")
    yy, xx = np.mgrid[0:N, 0:N]
    weave = ((xx // 6 + yy // 6) % 2).astype(np.float32) * 0.25
    img = posterize(0.55 * noise(140, 0.06) + 0.2 * noise(141, 0.004) + weave, pal, [0.25, 0.42, 0.62, 0.8])
    save("burlap", img)


def wrought_iron():
    pal = hexes("#16161C", "#1F2027", "#2A2C35", "#3A3D48", "#5E6270")
    save("iron", posterize(0.6 * noise(150, 0.05) + 0.4 * noise(151, 0.008), pal, [0.2, 0.45, 0.75, 0.93]))


def water():
    pal = hexes("#1E6A8A", "#2A86A6", "#3AA2C0", "#62C0D6", "#BEEAF2")
    img = posterize(noise(160, 0.08), pal, [0.25, 0.5, 0.75, 0.9])
    save("water", darken(img, lines(noise(161, 0.03), 0.01), pal[4], 0.7))


def pumpkin():
    pal = hexes("#7A3410", "#A84A14", "#D2661C", "#EC8A2E", "#F8B45A")
    xx = np.arange(N)[None, :] * np.ones((N, 1))
    ribs = 0.5 + 0.5 * np.cos(xx / N * 2 * np.pi * 8)
    save("pumpkin", posterize(0.7 * ribs + 0.3 * noise(170, 0.05), pal, [0.2, 0.4, 0.65, 0.88]))


def bone():
    pal = hexes("#8E8266", "#B2A684", "#CEC4A2", "#E2DABA", "#F4EED6")
    img = posterize(0.7 * noise(180, 0.06) + 0.3 * noise(181, 0.006), pal, [0.15, 0.35, 0.7, 0.9])
    save("bone", darken(img, lines(noise(182, 0.03), 0.003), pal[0], 0.8))


def flowers():
    """Massif fleuri : feuillage bas semé de fleurs à cinq couleurs (raccordable)."""
    rnd = np.random.default_rng(190)
    base = posterize(noise(191, 0.03), hexes("#1F3E26", "#2C5532", "#3D6B3E"), [0.4, 0.7])
    colors = hexes("#E85A7A", "#F2C440", "#F4F0E6", "#9A6AD6", "#F08A3A")
    heart = hexes("#F2D04A")[0]
    for _ in range(420):
        cx, cy = rnd.uniform(0, N, 2)
        c = colors[rnd.integers(0, len(colors))]
        r = rnd.uniform(9, 16)
        size = int(2 * r + 4)
        x0, y0 = int(cx - r - 2), int(cy - r - 2)
        sy, sx = np.mgrid[0:size, 0:size].astype(np.float32)
        dx, dy = sx + x0 - cx, sy + y0 - cy
        ys, xs = (np.arange(size) + y0) % N, (np.arange(size) + x0) % N
        block = base[np.ix_(ys, xs)]
        for k in range(5):
            a = 2 * np.pi * k / 5
            px, py = np.cos(a) * r * 0.7, np.sin(a) * r * 0.7
            block[((dx - px) ** 2 + (dy - py) ** 2) < (r * 0.55) ** 2] = c
        block[(dx * dx + dy * dy) < (r * 0.3) ** 2] = heart
        base[np.ix_(ys, xs)] = block
    save("flowers", base)


def paint_atlas():
    """Env_Paint : huit bandes verticales de peinture vive usée (petits accessoires) :
    rouge, orange, jaune, vert, bleu, rose, blanc, noir."""
    pals = (("#6A1E22", "#8A2A2C", "#B03A36", "#C9503E", "#E07A62"),
            ("#8A3E14", "#B0541A", "#D46E24", "#E88A36", "#F4AE6A"),
            ("#8E6A12", "#B8901C", "#DAB02A", "#EAC640", "#F6DE7E"),
            ("#1E4A2A", "#2A6236", "#3A7E44", "#4E9652", "#82BA7A"),
            ("#1E3A6A", "#28508A", "#3468AA", "#4A82C0", "#82AED8"),
            ("#8A2E56", "#B03E6E", "#D45A8A", "#E87AA2", "#F6AAC4"),
            ("#A8A296", "#C4BEB2", "#DCD6CA", "#ECE8DE", "#FBF9F2"),
            ("#121216", "#1C1C22", "#26262E", "#33333C", "#4A4A54"))
    img = np.zeros((N, N, 3), dtype=np.float32)
    w = N // 8
    for i, pal in enumerate(pals):
        field = 0.7 * noise(200 + i, 0.15)[:, :w] + 0.3 * noise(210 + i, 0.01)[:, :w]
        img[:, i * w:(i + 1) * w] = posterize(field, hexes(*pal), [0.1, 0.3, 0.72, 0.92])
    save("paint_atlas", img)


def terracotta():
    pal = hexes("#6A2E1C", "#8E4024", "#B0562E", "#C8703E", "#E09A66")
    save("terracotta", posterize(0.7 * noise(220, 0.06) + 0.3 * noise(221, 0.006), pal, [0.15, 0.35, 0.7, 0.9]))


def all_new():
    variants()
    asphalt()
    concrete_slabs()
    foliage("hedge", hexes("#1C3A26", "#28502F", "#3A6A3A", "#56824A", "#86A865"), 120)
    straw()
    burlap()
    wrought_iron()
    water()
    pumpkin()
    bone()
    flowers()
    paint_atlas()
    terracotta()


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "new" in only:
        all_new()
        sys.exit(0)
    trim_atlas()
    bark()
    foliage("foliage", hexes("#163A2E", "#24503B", "#356B49", "#4C8458", "#79A86E"), 50)
    foliage("foliage_shadow", hexes("#0F271F", "#183A2C", "#22503A", "#2E6046", "#467A55"), 51)
    car_paint()
    metal()
    rubber()
    moss()
    cloth()
    all_new()
