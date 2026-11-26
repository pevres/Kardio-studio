import hmac
import io
import json
import os
import re
import urllib.request
import zipfile
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps

st.set_page_config(
    page_title="Kardio • Social Card Studio",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ==========================================
# AUTENTICAZIONE CON PASSWORD (SOLO SECRETS)
# ==========================================
def check_password() -> bool:
    """Mostra una schermata di login pulita leggendo la password esclusivamente da st.secrets."""
    if st.session_state.get("authenticated", False):
        return True

    try:
        correct_password = st.secrets.get("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    except Exception:
        correct_password = os.environ.get("APP_PASSWORD")

    if not correct_password:
        st.error("Password non configurata. Imposta `APP_PASSWORD` nei Secrets di Streamlit.")
        return False

    st.markdown("<div style='max-width: 420px; margin: 4rem auto 0 auto;'>", unsafe_allow_html=True)
    st.title("Kardio • Accesso")
    st.caption("Inserisci la password per aprire lo studio grafico.")

    with st.form("login_form"):
        pwd_input = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entra in Kardio", type="primary", use_container_width=True)

        if submitted:
            if hmac.compare_digest(pwd_input, str(correct_password)):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Password non corretta.")

    st.markdown("</div>", unsafe_allow_html=True)
    return False


if not check_password():
    st.stop()


# ==========================================
# CSS RESPONSIVE (DESKTOP, TABLET, SMARTPHONE)
# ==========================================
st.markdown(
    """
    <style>
    /* Lascia spazio sufficiente per la barra superiore di Streamlit (Deploy / menu) */
    .block-container {
        padding-top: 3.6rem !important;
        padding-bottom: 1.5rem !important;
        padding-left: 1.4rem !important;
        padding-right: 1.4rem !important;
        max-width: 1400px;
    }

    /* Tab che vanno a capo su schermi piccoli invece di tagliarsi */
    .stTabs [data-baseweb="tab-list"] {
        flex-wrap: wrap;
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 8px 12px;
        font-size: 0.92rem;
        border-radius: 6px;
    }

    /* Pulsanti touch-friendly */
    .stButton > button, .stDownloadButton > button {
        min-height: 46px !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }

    /* Riquadro File Uploader ottimizzato per tocco su mobile */
    [data-testid="stFileUploader"] section {
        padding: 0.85rem !important;
        min-height: 64px !important;
    }
    [data-testid="stFileUploader"] button {
        min-height: 42px !important;
        padding: 0.4rem 1rem !important;
        width: 100% !important;
    }

    /* Anteprima contenuta così si vede tutta la card (incluso il footer) senza scroll */
    [data-testid="stImage"] img {
        max-height: 60vh;
        width: auto !important;
        max-width: 100% !important;
        margin: 0 auto;
        display: block;
        border-radius: 8px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
    }

    /* Tablet */
    @media (max-width: 1024px) {
        .block-container {
            padding-top: 3.4rem !important;
            padding-left: 0.9rem !important;
            padding-right: 0.9rem !important;
        }
        [data-testid="stImage"] img {
            max-height: 50vh;
        }
    }

    /* Smartphone */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 3.2rem !important;
            padding-left: 0.65rem !important;
            padding-right: 0.65rem !important;
        }
        h1 {
            font-size: 1.4rem !important;
            margin-bottom: 0.3rem !important;
        }
        h2, h3 {
            font-size: 1.15rem !important;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
        .stTabs [data-baseweb="tab"] {
            flex: 1 1 45%;
            justify-content: center;
            font-size: 0.85rem;
            padding: 7px 8px;
        }
        [data-testid="stImage"] img {
            max-height: 44vh;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==========================================
# GESTIONE STATO E BRAND KIT (SESSION STATE)
# ==========================================
DEFAULT_STATE = {
    "template": "Dichiarazione / Citazione",
    "kicker": "Aggiornamento • Focus",
    "big_number": "+42%",
    "headline": "Trasforma ogni idea in una *card visiva* pronta per i social in pochi secondi.",
    "subtext": "Personalizza testi, colori, foto e formati per comunicare con chiarezza su ogni canale.",
    "author": "Nome Autore • Brand o Progetto",
    "size_headline": 64,
    "size_subtext": 34,
    "size_kicker": 28,
    "size_number": 140,
    "size_author": 28,
    "padding": 85,
    "line_spacing": 1.22,
    "bar_width": 22,
    "horizontal_align": "Sinistra",
    "vertical_align": "Centrato",
    "horizontal_offset": 0,
    "vertical_offset": 0,
    "text_shadow": True,
    "logo_height": 95,
    "logo_position": "In basso a destra",
    "subject_size": 260,
    "subject_circle": True,
    "subject_side_by_side": True,
    "bg_color": "#18181B",
    "accent_color": "#E11D48",
    "text_color": "#FAFAFA",
    "show_footer_line": True,
    "footer_line_width_pct": 100,
    "footer_line_thickness": 4,
    "mobile_preview_top": False,
}

for k, v in DEFAULT_STATE.items():
    if k not in st.session_state:
        st.session_state[k] = v


def apply_brand_kit(data: dict):
    for key in DEFAULT_STATE:
        if key in data:
            st.session_state[key] = data[key]


def handle_restore_kit():
    uploaded_kit = st.session_state.get("kit_uploader")
    if uploaded_kit is not None:
        try:
            uploaded_kit.seek(0)
            raw_bytes = uploaded_kit.read()
            kit_data = json.loads(raw_bytes.decode("utf-8-sig"))
            apply_brand_kit(kit_data)
            st.session_state["kit_status"] = ("success", "Brand Kit ripristinato dal file.")
        except Exception as e:
            st.session_state["kit_status"] = ("error", f"File JSON non valido: {e}")


def handle_restore_kit_text():
    raw_json = st.session_state.get("kit_text_input", "").strip()
    if raw_json:
        try:
            kit_data = json.loads(raw_json)
            apply_brand_kit(kit_data)
            st.session_state["kit_status"] = ("success", "Brand Kit ripristinato dal testo JSON.")
        except Exception as e:
            st.session_state["kit_status"] = ("error", f"Testo JSON non valido: {e}")


def handle_apply_palette(bg_p: str, acc_p: str, txt_p: str):
    st.session_state["bg_color"] = bg_p
    st.session_state["accent_color"] = acc_p
    st.session_state["text_color"] = txt_p


def export_brand_kit_json() -> str:
    kit_keys = [
        "author",
        "size_headline",
        "size_subtext",
        "size_kicker",
        "size_number",
        "size_author",
        "padding",
        "line_spacing",
        "bar_width",
        "horizontal_align",
        "vertical_align",
        "horizontal_offset",
        "vertical_offset",
        "text_shadow",
        "logo_height",
        "logo_position",
        "subject_size",
        "subject_circle",
        "subject_side_by_side",
        "bg_color",
        "accent_color",
        "text_color",
        "show_footer_line",
        "footer_line_width_pct",
        "footer_line_thickness",
    ]
    payload = {k: st.session_state[k] for k in kit_keys}
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ==========================================
# GESTIONE FONT TRUETYPE
# ==========================================
@st.cache_resource
def ensure_fonts():
    os.makedirs("fonts", exist_ok=True)
    font_files = {
        "bold": (
            "fonts/Montserrat-Bold.ttf",
            "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf",
        ),
        "regular": (
            "fonts/Inter-Regular.ttf",
            "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf",
        ),
    }
    paths = {}
    for style, (local_path, url) in font_files.items():
        if not os.path.exists(local_path) or os.path.getsize(local_path) < 10000:
            try:
                urllib.request.urlretrieve(url, local_path)
            except Exception:
                pass
        paths[style] = local_path
    return paths


def load_font(size: int, bold: bool = False):
    paths = ensure_fonts()
    target = paths["bold"] if bold else paths["regular"]
    size = max(12, int(size))

    candidates = [
        target,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]

    for path in candidates:
        if os.path.exists(path) or not path.startswith("/"):
            try:
                font = ImageFont.truetype(path, size)
                try:
                    font.set_variation_by_axes([700 if bold else 400])
                except Exception:
                    pass
                return font
            except Exception:
                continue

    return ImageFont.load_default(size=size)


# ==========================================
# MOTORE GRAFICO PILLOW
# ==========================================
def open_uploaded_image(uploaded_file) -> Image.Image | None:
    """Apre in sicurezza un'immagine caricata da mobile/desktop correggendo l'orientamento EXIF."""
    if uploaded_file is None:
        return None
    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img = ImageOps.exif_transpose(img)
        return img.convert("RGBA")
    except Exception:
        return None


def hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def fit_cover(
    image: Image.Image,
    target_w: int,
    target_h: int,
    offset_x: float = 0.5,
    offset_y: float = 0.5,
    zoom: float = 1.0,
) -> Image.Image:
    base_ratio = max(target_w / image.width, target_h / image.height)
    ratio = base_ratio * max(1.0, zoom)
    new_w = int(image.width * ratio)
    new_h = int(image.height * ratio)
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    max_left = max(0, new_w - target_w)
    max_top = max(0, new_h - target_h)
    left = int(max_left * offset_x)
    top = int(max_top * offset_y)
    return resized.crop((left, top, left + target_w, top + target_h))


def draw_text_with_optional_shadow(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    shadow: bool = False,
    shadow_offset: int = 3,
):
    x, y = xy
    if shadow:
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 175))
    draw.text((x, y), text, font=font, fill=fill)


def measure_highlighted_text_height(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    line_spacing: float = 1.2,
) -> int:
    """Calcola l'altezza verticale complessiva del testo wrappato."""
    if not text:
        return 0
    words = text.split()
    lines = 0
    current_line = []
    current_w = 0
    space_w = draw.textbbox((0, 0), " ", font=font)[2]

    for w in words:
        clean_w = w.replace("*", "")
        w_width = draw.textbbox((0, 0), clean_w, font=font)[2]
        if current_line and (current_w + space_w + w_width > max_width):
            lines += 1
            current_line = [w]
            current_w = w_width
        else:
            current_line.append(w)
            current_w += (space_w if len(current_line) > 1 else 0) + w_width
    if current_line:
        lines += 1

    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_h = int((bbox[3] - bbox[1]) * line_spacing)
    return lines * line_h


def draw_highlighted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    base_color: str,
    highlight_color: str,
    max_width: int,
    line_spacing: float = 1.2,
    align: str = "Sinistra",
    shadow: bool = False,
    shadow_offset: int = 3,
) -> int:
    words = text.split()
    lines = []
    current_line = []
    current_w = 0
    space_w = draw.textbbox((0, 0), " ", font=font)[2]

    for w in words:
        clean_w = w.replace("*", "")
        w_width = draw.textbbox((0, 0), clean_w, font=font)[2]
        if current_line and (current_w + space_w + w_width > max_width):
            lines.append((current_line, current_w))
            current_line = [w]
            current_w = w_width
        else:
            current_line.append(w)
            current_w += (space_w if len(current_line) > 1 else 0) + w_width
    if current_line:
        lines.append((current_line, current_w))

    bbox = draw.textbbox((0, 0), "Ag", font=font)
    line_h = int((bbox[3] - bbox[1]) * line_spacing)

    in_highlight = False
    for line_tokens, line_w in lines:
        if align == "Centrato":
            cursor_x = x + max(0, (max_width - line_w) // 2)
        elif align == "Destra":
            cursor_x = x + max(0, max_width - line_w)
        else:
            cursor_x = x

        for token in line_tokens:
            starts = token.startswith("*")
            ends = token.endswith("*") and len(token) > 1
            if starts:
                in_highlight = True

            clean_token = token.strip("*")
            color = highlight_color if in_highlight else base_color

            draw_text_with_optional_shadow(
                draw,
                (cursor_x, y),
                clean_token,
                font=font,
                fill=color,
                shadow=shadow,
                shadow_offset=shadow_offset,
            )
            tok_w = draw.textbbox((0, 0), clean_token + " ", font=font)[2]
            cursor_x += tok_w

            if ends:
                in_highlight = False
        y += line_h

    return y


def generate_card(cfg: dict, override_w: int = None, override_h: int = None) -> Image.Image:
    W = override_w if override_w else cfg["width"]
    H = override_h if override_h else cfg["height"]

    scale = W / 1080.0
    pad = int(cfg["padding"] * scale)
    shadow_on = cfg.get("text_shadow", True)
    shadow_off = max(2, int(3 * scale))
    h_align = cfg.get("horizontal_align", "Sinistra")

    img = Image.new("RGBA", (W, H), cfg["bg_color"])

    # 1. IMMAGINE DI SFONDO
    bg = open_uploaded_image(cfg["bg_image"])
    if bg is not None:
        if cfg["bg_grayscale"]:
            gray = ImageOps.grayscale(bg)
            bg = Image.merge("RGBA", (gray, gray, gray, bg.split()[3]))
        if cfg["bg_contrast"] != 1.0:
            bg = ImageEnhance.Contrast(bg).enhance(cfg["bg_contrast"])

        bg = fit_cover(
            bg,
            W,
            H,
            cfg["bg_offset_x"],
            cfg["bg_offset_y"],
            cfg.get("bg_zoom", 1.0),
        )

        r, g, b = hex_to_rgb(cfg["bg_color"])
        overlay = Image.new("RGBA", (W, H), (r, g, b, int(255 * cfg["overlay_opacity"])))
        img = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(img)

    # 2. BARRA LATERALE ACCENTO
    if cfg["bar_width"] > 0:
        draw.rectangle([0, 0, int(cfg["bar_width"] * scale), H], fill=cfg["accent_color"])

    # 3. LOGO
    logo_img = None
    logo_h_scaled = int(cfg["logo_height"] * scale)
    raw_logo = open_uploaded_image(cfg["logo_file"])
    if raw_logo is not None:
        target_w = int(raw_logo.width * (logo_h_scaled / raw_logo.height))
        logo_img = raw_logo.resize((target_w, logo_h_scaled), Image.Resampling.LANCZOS)

    is_tall = (H / W) >= 1.5
    top_limit = int(H * 0.14) if is_tall else pad

    if logo_img is not None and cfg["logo_position"].startswith("In alto"):
        top_logo_y = pad
        lx = pad if "sinistra" in cfg["logo_position"] else (W - pad - logo_img.width)
        img.paste(logo_img, (lx, top_logo_y), logo_img)
        top_limit = max(top_limit, top_logo_y + logo_img.height + int(pad * 0.45))

    y = top_limit

    # 4. FOTO SOGGETTO / RITRATTO
    content_max_w = W - (2 * pad)
    subject_box = None
    subj = open_uploaded_image(cfg["subject_file"])
    if subj is not None:
        sw = int(cfg["subject_size"] * scale)
        sh = int(subj.height * (sw / subj.width))
        subj = subj.resize((sw, sh), Image.Resampling.LANCZOS)

        if cfg["subject_circle"]:
            subj = fit_cover(subj, sw, sw)
            sh = sw
            mask = Image.new("L", (sw, sw), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, sw, sw), fill=255)
            border = max(4, int(6 * scale))
            draw.ellipse(
                (W - pad - sw - border, y - border, W - pad + border, y + sw + border),
                fill=cfg["accent_color"],
            )
            img.paste(subj, (W - pad - sw, y), mask)
        else:
            img.paste(subj, (W - pad - sw, y), subj)

        subject_box = (W - pad - sw, y, W - pad, y + sh)
        if cfg["subject_side_by_side"] and not is_tall:
            content_max_w = W - (2 * pad) - sw - int(pad * 0.5)
        else:
            y += sh + int(pad * 0.45)

    # 5. FONT CARICATI CON LE DIMENSIONI SCELTE
    s_kicker = int(cfg["size_kicker"] * scale)
    s_number = int(cfg["size_number"] * scale)
    s_head = int(cfg["size_headline"] * scale)
    s_sub = int(cfg["size_subtext"] * scale)
    s_author = int(cfg["size_author"] * scale)

    f_kicker = load_font(s_kicker, bold=True)
    f_number = load_font(s_number, bold=True)
    f_head = load_font(s_head, bold=True)
    f_sub = load_font(s_sub, bold=False)
    f_author = load_font(s_author, bold=True)

    # 6. ALLINEAMENTO VERTICALE E ORIZZONTALE DEL BLOCCO TESTI
    footer_bottom_margin = int(H * 0.08) if is_tall else pad
    footer_y = H - footer_bottom_margin - max(
        s_author, logo_h_scaled if (logo_img and "basso" in cfg["logo_position"]) else 0
    )
    bottom_limit = footer_y - (48 if cfg["show_footer_line"] else 24)

    block_h = 0
    if cfg["kicker"]:
        block_h += int(s_kicker * 1.8)
    if cfg["template"] == "Dato & Numeri" and cfg["big_number"]:
        block_h += int(s_number * 1.25)
    if cfg["headline"]:
        block_h += measure_highlighted_text_height(
            draw, cfg["headline"], f_head, content_max_w, cfg["line_spacing"]
        ) + int(s_head * 0.5)
    if cfg["subtext"]:
        sub_w_est = (
            content_max_w
            if (subject_box and cfg["subject_side_by_side"] and not is_tall)
            else (W - 2 * pad)
        )
        block_h += measure_highlighted_text_height(draw, cfg["subtext"], f_sub, sub_w_est, 1.3)

    v_align = cfg.get("vertical_align", "Centrato")
    available_h = max(0, bottom_limit - y)
    if v_align == "Centrato" and block_h < available_h:
        y += (available_h - block_h) // 2
    elif v_align == "In basso" and block_h < available_h:
        y += available_h - block_h

    # Spostamenti fini manuali (liberi su tutta l'altezza e larghezza della card)
    y += int(cfg.get("vertical_offset", 0) * scale)
    y = max(int(24 * scale), min(H - int(80 * scale), y))

    base_x = pad + int(cfg.get("horizontal_offset", 0) * scale)

    def aligned_single_line_x(line_text: str, font: ImageFont.FreeTypeFont, box_w: int) -> int:
        tw = draw.textbbox((0, 0), line_text, font=font)[2]
        if h_align == "Centrato":
            return base_x + max(0, (box_w - tw) // 2)
        elif h_align == "Destra":
            return base_x + max(0, box_w - tw)
        return base_x

    # 7. OCCHIELLO / KICKER
    if cfg["kicker"]:
        kicker_str = cfg["kicker"].upper()
        kx = aligned_single_line_x(kicker_str, f_kicker, content_max_w)
        draw_text_with_optional_shadow(
            draw,
            (kx, y),
            kicker_str,
            font=f_kicker,
            fill=cfg["accent_color"],
            shadow=shadow_on,
            shadow_offset=shadow_off,
        )
        y += int(s_kicker * 1.8)

    # 8. DATO GIGANTE
    if cfg["template"] == "Dato & Numeri" and cfg["big_number"]:
        nx = aligned_single_line_x(cfg["big_number"], f_number, content_max_w)
        draw_text_with_optional_shadow(
            draw,
            (nx, y),
            cfg["big_number"],
            font=f_number,
            fill=cfg["accent_color"],
            shadow=shadow_on,
            shadow_offset=shadow_off,
        )
        y += int(s_number * 1.25)

    # 9. TITOLO PRINCIPALE
    if cfg["headline"]:
        y = draw_highlighted_text(
            draw=draw,
            text=cfg["headline"],
            x=base_x,
            y=y,
            font=f_head,
            base_color=cfg["text_color"],
            highlight_color=cfg["accent_color"],
            max_width=content_max_w,
            line_spacing=cfg["line_spacing"],
            align=h_align,
            shadow=shadow_on,
            shadow_offset=shadow_off,
        )
        y += int(s_head * 0.5)

    # 10. SOTTOTITOLO
    if cfg["subtext"]:
        sub_max_w = W - (2 * pad)
        if subject_box and cfg["subject_side_by_side"] and not is_tall and y < subject_box[3]:
            sub_max_w = content_max_w

        y = draw_highlighted_text(
            draw=draw,
            text=cfg["subtext"],
            x=base_x,
            y=y,
            font=f_sub,
            base_color=cfg["text_color"],
            highlight_color=cfg["accent_color"],
            max_width=sub_max_w,
            line_spacing=1.3,
            align=h_align,
            shadow=shadow_on,
            shadow_offset=shadow_off,
        )

    # 11. FOOTER
    if cfg["show_footer_line"]:
        max_line_w = W - (2 * pad)
        line_w = int(max_line_w * (cfg.get("footer_line_width_pct", 100) / 100.0))
        thickness = max(1, int(cfg.get("footer_line_thickness", 4) * scale))

        if h_align == "Centrato":
            line_x1 = pad + (max_line_w - line_w) // 2
        elif h_align == "Destra":
            line_x1 = W - pad - line_w
        else:
            line_x1 = pad

        line_y = footer_y - int(24 * scale)
        draw.line([(line_x1, line_y), (line_x1 + line_w, line_y)], fill=cfg["accent_color"], width=thickness)

    if cfg["author"]:
        text_y = footer_y + (
            (logo_h_scaled - s_author) // 2
            if (logo_img and "basso" in cfg["logo_position"])
            else 0
        )
        draw_text_with_optional_shadow(
            draw,
            (pad, text_y),
            cfg["author"],
            font=f_author,
            fill=cfg["text_color"],
            shadow=shadow_on,
            shadow_offset=shadow_off,
        )

    if logo_img is not None and cfg["logo_position"].startswith("In basso"):
        lx = (W - pad - logo_img.width) if "destra" in cfg["logo_position"] else pad
        img.paste(logo_img, (lx, footer_y), logo_img)

    return img.convert("RGB")


def build_multi_format_zip(cfg: dict) -> bytes:
    formats = [
        ("01_kardio_post_1080x1080.png", 1080, 1080),
        ("02_kardio_portrait_1080x1350.png", 1080, 1350),
        ("03_kardio_story_1080x1920.png", 1080, 1920),
    ]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, w, h in formats:
            rendered = generate_card(cfg, override_w=w, override_h=h)
            img_buf = io.BytesIO()
            rendered.save(img_buf, format="PNG")
            zf.writestr(filename, img_buf.getvalue())
    return zip_buffer.getvalue()


def auto_extract_from_press_release(raw_text: str):
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text.strip()) if s.strip()]
    if not sentences:
        return
    first = sentences[0]
    rest = " ".join(sentences[1:3]) if len(sentences) > 1 else ""

    num_match = re.search(r"([+-]?\d+(?:[.,]\d+)?\s*(?:%|Mln|Mld|mila|€|euro)?)", raw_text, re.IGNORECASE)
    if num_match and any(ch.isdigit() for ch in num_match.group(1)):
        st.session_state["big_number"] = num_match.group(1).strip()

    st.session_state["headline"] = first
    if rest:
        st.session_state["subtext"] = rest


# ==========================================
# FUNZIONI DI RENDERING UI MODULARI
# ==========================================
def render_media_and_colors(t_media, t_colori):
    with t_media:
        st.markdown("**1. Immagine di sfondo (piena pagina)**")
        bg_image = st.file_uploader("Carica sfondo (JPG, PNG, WEBP)", key="bg_up")
        if bg_image is not None:
            if open_uploaded_image(bg_image) is None:
                st.error("Formato immagine non supportato. Usa JPG, PNG o WEBP.")
            m1, m2, m3 = st.columns(3)
            overlay_opacity = m1.slider("Oscuramento", 0.0, 0.95, 0.75)
            bg_contrast = m2.slider("Contrasto", 0.5, 2.0, 1.1)
            bg_grayscale = m3.checkbox("Bianco e Nero", value=False)

            p1, p2, p3 = st.columns(3)
            bg_zoom = p1.slider("Zoom foto", 1.0, 2.5, 1.0, step=0.05)
            bg_offset_x = p2.slider("Sposta Orizzontale", 0.0, 1.0, 0.5)
            bg_offset_y = p3.slider("Sposta Verticale", 0.0, 1.0, 0.5)
        else:
            overlay_opacity, bg_contrast, bg_grayscale = 0.75, 1.0, False
            bg_zoom, bg_offset_x, bg_offset_y = 1.0, 0.5, 0.5

        st.divider()
        st.markdown("**2. Foto Soggetto / Ritratto**")
        subject_file = st.file_uploader("Carica ritratto o oggetto", key="subj_up")
        if subject_file is not None:
            if open_uploaded_image(subject_file) is None:
                st.error("Formato immagine non supportato. Usa JPG, PNG o WEBP.")
            sb1, sb2, sb3 = st.columns(3)
            subject_size = sb1.slider("Dimensione (px)", 120, 600, key="subject_size")
            subject_circle = sb2.checkbox("Ritaglio circolare", key="subject_circle")
            subject_side_by_side = sb3.checkbox("Affianca al testo", key="subject_side_by_side")
        else:
            subject_size = st.session_state["subject_size"]
            subject_circle = st.session_state["subject_circle"]
            subject_side_by_side = st.session_state["subject_side_by_side"]

        st.divider()
        st.markdown("**3. Logo / Marchio**")
        logo_file = st.file_uploader("Carica Logo (PNG trasparente)", key="logo_up")
        if logo_file is not None:
            if open_uploaded_image(logo_file) is None:
                st.error("Formato logo non supportato. Usa PNG o WEBP.")
            lg1, lg2 = st.columns(2)
            logo_height = lg1.slider("Altezza Logo (px)", 40, 260, key="logo_height")
            logo_position = lg2.selectbox(
                "Posizione Logo",
                ["In basso a destra", "In alto a sinistra", "In alto a destra"],
                key="logo_position",
            )
        else:
            logo_height = st.session_state["logo_height"]
            logo_position = st.session_state["logo_position"]

    with t_colori:
        st.markdown("**Palette Colori**")
        p_col1, p_col2 = st.columns([2, 1], vertical_alignment="bottom")
        palette = p_col1.selectbox(
            "Preset rapido",
            [
                "Rosso Editoriale",
                "Blu Istituzionale",
                "Verde Natura",
                "Chiara Minimal",
            ],
        )
        presets = {
            "Rosso Editoriale": ("#18181B", "#E11D48", "#FAFAFA"),
            "Blu Istituzionale": ("#0F172A", "#38BDF8", "#F8FAFC"),
            "Verde Natura": ("#064E3B", "#34D399", "#ECFDF5"),
            "Chiara Minimal": ("#F8FAFC", "#DC2626", "#0F172A"),
        }
        bg_p, acc_p, txt_p = presets[palette]
        p_col2.button(
            "Applica Palette",
            use_container_width=True,
            on_click=handle_apply_palette,
            args=(bg_p, acc_p, txt_p),
        )

        c1, c2, c3 = st.columns(3)
        bg_color = c1.color_picker("Sfondo", key="bg_color")
        accent_color = c2.color_picker("Accento", key="accent_color")
        text_color = c3.color_picker("Testo", key="text_color")

        show_footer_line = st.checkbox("Mostra linea separatrice in basso", key="show_footer_line")
        if show_footer_line:
            fl1, fl2 = st.columns(2)
            footer_line_width_pct = fl1.slider(
                "Lunghezza linea (%)", 10, 100, step=5, key="footer_line_width_pct"
            )
            footer_line_thickness = fl2.slider(
                "Spessore linea (px)", 1, 20, key="footer_line_thickness"
            )
        else:
            footer_line_width_pct = st.session_state["footer_line_width_pct"]
            footer_line_thickness = st.session_state["footer_line_thickness"]

        st.divider()
        st.markdown("**Brand Kit (JSON)**")
        kit_json_str = export_brand_kit_json()

        st.download_button(
            label="Scarica Brand Kit (.json)",
            data=kit_json_str,
            file_name="kardio_brand_kit.json",
            mime="application/json",
            use_container_width=True,
        )

        uploaded_kit = st.file_uploader(
            "Carica file Brand Kit (.json)",
            key="kit_uploader",
        )
        if uploaded_kit is not None:
            st.button(
                "Ripristina da File",
                type="primary",
                use_container_width=True,
                on_click=handle_restore_kit,
            )

        with st.expander("Copia / Incolla Brand Kit (ideale da smartphone)"):
            st.caption("Copia il codice qui sotto per salvarlo nelle note, oppure incolla un kit esistente:")
            st.code(kit_json_str, language="json")
            st.text_area(
                "Incolla qui il JSON del Brand Kit",
                height=110,
                key="kit_text_input",
                placeholder='{"author": "...", "bg_color": "#18181B", ...}',
            )
            st.button(
                "Ripristina da Testo Incollato",
                use_container_width=True,
                on_click=handle_restore_kit_text,
            )

        if "kit_status" in st.session_state:
            kind, msg = st.session_state.pop("kit_status")
            if kind == "success":
                st.success(msg)
            else:
                st.error(msg)

    return (
        bg_image, overlay_opacity, bg_contrast, bg_grayscale, bg_zoom, bg_offset_x, bg_offset_y,
        subject_file, subject_size, subject_circle, subject_side_by_side,
        logo_file, logo_height, logo_position,
        bg_color, accent_color, text_color,
        show_footer_line, footer_line_width_pct, footer_line_thickness,
    )


def render_preview_panel(config: dict):
    width, height = config["width"], config["height"]
    st.subheader(f"Anteprima ({width} × {height} px)")
    card = generate_card(config)
    st.image(card, use_container_width=True)

    dl1, dl2 = st.columns(2)
    buf_single = io.BytesIO()
    card.save(buf_single, format="PNG")
    dl1.download_button(
        label=f"Scarica PNG ({width}×{height})",
        data=buf_single.getvalue(),
        file_name=f"kardio_{width}x{height}.png",
        mime="image/png",
        type="primary",
        use_container_width=True,
    )

    dl2.download_button(
        label="Pacchetto 3 Formati (ZIP)",
        data=build_multi_format_zip(config),
        file_name="kardio_pack_social.zip",
        mime="application/zip",
        use_container_width=True,
    )


# ==========================================
# HEADER E LAYOUT ADATTIVO
# ==========================================
hdr_col1, hdr_col2, hdr_col3 = st.columns([2.2, 1, 0.55], vertical_alignment="center")
with hdr_col1:
    st.title("Kardio • Social Card Studio")
with hdr_col2:
    mobile_top = st.toggle(
        "Anteprima in alto (Mobile)",
        key="mobile_preview_top",
        help="Sposta l'anteprima sopra i controlli su smartphone o tablet verticali",
    )
with hdr_col3:
    if st.button("Esci", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

if mobile_top:
    preview_container = st.container()
    st.divider()
    controls_container = st.container()
else:
    controls_container, preview_container = st.columns([1.25, 1], gap="large")

with controls_container:
    t_testi, t_dimensioni, t_media, t_colori = st.tabs(
        [
            "1. Testi",
            "2. Dimensioni",
            "3. Immagini & Logo",
            "4. Colori & Kit",
        ]
    )

    with t_testi:
        template = st.selectbox(
            "Struttura Card",
            ["Dichiarazione / Citazione", "Dato & Numeri", "Notizia / Flash"],
            key="template",
        )
        kicker = st.text_input("Occhiello / Tema", key="kicker")
        big_number = ""
        if template == "Dato & Numeri":
            big_number = st.text_input("Numero / Dato principale", key="big_number")

        headline = st.text_area(
            "Messaggio principale (usa *parola* tra asterischi per evidenziarla)",
            height=95,
            key="headline",
        )
        subtext = st.text_area(
            "Sottotitolo / Approfondimento",
            height=75,
            key="subtext",
        )
        author = st.text_input("Firma / Autore / Brand", key="author")

        with st.expander("Importa da testo lungo"):
            raw_press = st.text_area(
                "Incolla 2-3 frasi per dividerle automaticamente in titolo e sottotitolo",
                height=85,
            )
            if st.button("Applica testo importato", use_container_width=True) and raw_press.strip():
                auto_extract_from_press_release(raw_press)
                st.rerun()

    with t_dimensioni:
        preset_format = st.selectbox(
            "Formato anteprima",
            [
                "1:1 Quadrato (1080 x 1080)",
                "4:5 Portrait Instagram (1080 x 1350)",
                "9:16 Story / Reel (1080 x 1920)",
                "16:9 Orizzontale X/FB (1200 x 675)",
                "Personalizzato",
            ],
        )

        if preset_format == "1:1 Quadrato (1080 x 1080)":
            width, height = 1080, 1080
        elif preset_format == "4:5 Portrait Instagram (1080 x 1350)":
            width, height = 1080, 1350
        elif preset_format == "9:16 Story / Reel (1080 x 1920)":
            width, height = 1080, 1920
        elif preset_format == "16:9 Orizzontale X/FB (1200 x 675)":
            width, height = 1200, 675
        else:
            c_w, c_h = st.columns(2)
            width = c_w.number_input("Larghezza (px)", min_value=400, max_value=3000, value=1080, step=10)
            height = c_h.number_input("Altezza (px)", min_value=400, max_value=3000, value=1080, step=10)

        st.markdown("**Dimensioni Font (px su base 1080p)**")
        f1, f2 = st.columns(2)
        size_headline = f1.slider("Grandezza Titolo", 28, 130, key="size_headline")
        size_subtext = f2.slider("Grandezza Sottotitolo", 18, 70, key="size_subtext")

        f3, f4, f5 = st.columns(3)
        size_kicker = f3.slider("Occhiello", 14, 55, key="size_kicker")
        size_number = f4.slider("Dato", 60, 240, key="size_number")
        size_author = f5.slider("Firma", 16, 55, key="size_author")

        st.markdown("**Margini & Struttura**")
        s1, s2, s3 = st.columns(3)
        padding = s1.slider("Margine (px)", 30, 180, key="padding")
        line_spacing = s2.slider("Interlinea", 1.0, 1.6, step=0.02, key="line_spacing")
        bar_width = s3.slider("Bordo (px)", 0, 60, key="bar_width")

        st.markdown("**Posizione & Leggibilità Testo**")
        va1, va2 = st.columns(2)
        horizontal_align = va1.selectbox(
            "Allineamento orizzontale",
            ["Sinistra", "Centrato", "Destra"],
            key="horizontal_align",
        )
        vertical_align = va2.selectbox(
            "Allineamento verticale",
            ["Centrato", "In alto", "In basso"],
            key="vertical_align",
        )

        off1, off2 = st.columns(2)
        horizontal_offset = off1.slider(
            "Sposta orizzontale (px)",
            min_value=-350,
            max_value=350,
            step=5,
            key="horizontal_offset",
        )
        vertical_offset = off2.slider(
            "Sposta verticale (px)",
            min_value=-650,
            max_value=650,
            step=10,
            key="vertical_offset",
        )
        text_shadow = st.checkbox("Ombra sotto i testi (migliora leggibilità su foto)", key="text_shadow")

    (
        bg_image, overlay_opacity, bg_contrast, bg_grayscale, bg_zoom, bg_offset_x, bg_offset_y,
        subject_file, subject_size, subject_circle, subject_side_by_side,
        logo_file, logo_height, logo_position,
        bg_color, accent_color, text_color,
        show_footer_line, footer_line_width_pct, footer_line_thickness,
    ) = render_media_and_colors(t_media, t_colori)

config = {
    "width": width,
    "height": height,
    "template": template,
    "kicker": kicker,
    "big_number": big_number,
    "headline": headline,
    "subtext": subtext,
    "author": author,
    "size_headline": size_headline,
    "size_subtext": size_subtext,
    "size_kicker": size_kicker,
    "size_number": size_number,
    "size_author": size_author,
    "padding": padding,
    "line_spacing": line_spacing,
    "bar_width": bar_width,
    "horizontal_align": horizontal_align,
    "vertical_align": vertical_align,
    "horizontal_offset": horizontal_offset,
    "vertical_offset": vertical_offset,
    "text_shadow": text_shadow,
    "bg_image": bg_image,
    "overlay_opacity": overlay_opacity,
    "bg_contrast": bg_contrast,
    "bg_grayscale": bg_grayscale,
    "bg_zoom": bg_zoom,
    "bg_offset_x": bg_offset_x,
    "bg_offset_y": bg_offset_y,
    "subject_file": subject_file,
    "subject_size": subject_size,
    "subject_circle": subject_circle,
    "subject_side_by_side": subject_side_by_side,
    "logo_file": logo_file,
    "logo_height": logo_height,
    "logo_position": logo_position,
    "bg_color": bg_color,
    "accent_color": accent_color,
    "text_color": text_color,
    "show_footer_line": show_footer_line,
    "footer_line_width_pct": footer_line_width_pct,
    "footer_line_thickness": footer_line_thickness,
}

with preview_container:
    render_preview_panel(config)
