import os
import base64
import random
import datetime
import re
import io
import math
import zipfile
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
import plotly.graph_objects as go

# ==========================================
# 0. 環境変数（.env）の読み込み
# ==========================================
load_dotenv()
ENV_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 安定版モデル名
GEMINI_MODEL_NAME = "gemini-3.6-flash"

# ==========================================
# 1. ページ基本設定 & Session State
# ==========================================
st.set_page_config(page_title="SNSアイコン個性診断＆開運鑑定", page_icon="☯️", layout="centered")

adsense_code = """
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-11300734169227114"
     crossorigin="anonymous"></script>
"""
st.markdown(adsense_code, unsafe_allow_html=True)

if "mode" not in st.session_state:
    st.session_state.mode = None
if "step" not in st.session_state:
    st.session_state.step = 0
if "birth_date_str" not in st.session_state:
    st.session_state.birth_date_str = "19900101"
if "diagnosis_style" not in st.session_state:
    st.session_state.diagnosis_style = "甘口（褒めちぎり）"
if "result_text" not in st.session_state:
    st.session_state.result_text = None
if "card_images" not in st.session_state:
    st.session_state.card_images = None
if "radar_params" not in st.session_state:
    st.session_state.radar_params = None
if "omikuji_text" not in st.session_state:
    st.session_state.omikuji_text = None
if "omikuji_result_type" not in st.session_state:
    st.session_state.omikuji_result_type = None
if "omikuji_card_image" not in st.session_state:
    st.session_state.omikuji_card_image = None
if "direction_result_text" not in st.session_state:
    st.session_state.direction_result_text = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ENV_GEMINI_API_KEY

def get_api_key():
    return st.session_state.api_key if st.session_state.api_key else ENV_GEMINI_API_KEY

# 🎭 おみくじ結果に応じた文字＆黒猫絵文字乱舞演出（HTML/CSS/JS）
def trigger_omikuji_animation(fortune_type):
    if fortune_type in ["超大吉", "大吉"]:
        items = f"['{fortune_type}✨', '{fortune_type}🎉', '😸', '✨', '🎊', '🔴大吉🔴', '😸']"
        color = "#FF2222"
    elif fortune_type == "凶":
        items = "['凶💧', '😿', '☔', '😭', '凶😭', '😿']"
        color = "#6688AA"
    else:
        items = f"['{fortune_type}🌸', '😸', '✨', '🍀', '🌟']"
        color = "#FF9900"

    js_code = f"""
    <script>
    (function() {{
        const items = {items};
        const color = '{color}';
        const container = document.createElement('div');
        container.style.position = 'fixed';
        container.style.top = '0';
        container.style.left = '0';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.pointerEvents = 'none';
        container.style.zIndex = '999999';
        container.style.overflow = 'hidden';
        document.body.appendChild(container);

        for (let i = 0; i < 35; i++) {{
            const el = document.createElement('div');
            el.innerText = items[Math.floor(Math.random() * items.length)];
            el.style.position = 'absolute';
            el.style.left = Math.random() * 100 + 'vw';
            el.style.bottom = '-50px';
            el.style.fontSize = (Math.random() * 24 + 28) + 'px';
            el.style.fontWeight = 'bold';
            el.style.color = color;
            el.style.textShadow = '0 0 10px rgba(255,255,255,0.9), 2px 2px 4px #000';
            el.style.opacity = '0.9';
            
            const duration = Math.random() * 2.5 + 2.5;
            const delay = Math.random() * 1.5;
            
            el.animate([
                {{ transform: 'translateY(0) rotate(0deg)', opacity: 0.9 }},
                {{ transform: `translateY(-115vh) rotate(${{Math.random() * 360 - 180}}deg)`, opacity: 0 }}
            ], {{
                duration: duration * 1000,
                delay: delay * 1000,
                easing: 'ease-out',
                fill: 'forwards'
            }});

            container.appendChild(el);
        }}

        setTimeout(() => {{
            container.remove();
        }}, 6000);
    }})();
    </script>
    """
    st.components.v1.html(js_code, height=0)

# ==========================================
# 2. 背景画像（bg.jpg）＆デザイン設定
# ==========================================
def get_image_base64(image_filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(current_dir, image_filename),
        image_filename,
        os.path.join(".", image_filename)
    ]
    target_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not target_path:
        return None
    with open(target_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded}"

img_filename = "bg.jpg"
img_base64 = get_image_base64(img_filename)

if img_base64:
    css_template = """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@600;700;800&family=Noto+Sans+JP:wght@400;700&display=swap');

        .stApp {
            background-image: url('__IMAGE_DATA__');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        .main .block-container {
            background: rgba(10, 12, 24, 0.78) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border-radius: 20px;
            border: 1px solid rgba(255, 215, 0, 0.3);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
            padding: 1.5rem 1rem;
        }

        .hero-header { text-align: center; padding: 0.5rem 0 0.2rem 0; }
        .hero-badge {
            display: inline-block;
            background: linear-gradient(135deg, rgba(255,215,0,0.2), rgba(255,140,0,0.2));
            border: 1px solid rgba(255, 215, 0, 0.5);
            color: #FFE066;
            padding: 3px 12px;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
            box-shadow: 0 0 12px rgba(255, 215, 0, 0.2);
        }
        
        .main-title-text {
            font-family: 'Shippori Mincho', serif !important;
            font-size: 1.85rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.02em;
            background: linear-gradient(180deg, #EEEEEE 20%, #FFE066 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 3px 12px rgba(0,0,0,0.8);
            margin-bottom: 0.4rem;
            line-height: 1.3;
        }
        
        .subtitle-text {
            color: #D0D8EC !important;
            font-size: 0.88rem;
            font-weight: 400 !important;
            margin-bottom: 1.2rem;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
            padding: 0 0.5rem;
            line-height: 1.4;
        }

        .choice-title {
            text-align: center;
            font-family: 'Shippori Mincho', serif !important;
            font-size: 1.4rem;
            font-weight: 700;
            color: #FFE066 !important;
            margin: 1.2rem 0 0.8rem 0;
        }

        .omikuji-heading {
            font-family: 'Shippori Mincho', serif !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
            color: #FFE066 !important;
            text-align: center;
            margin-bottom: 0.5rem;
        }

        .step-container {
            display: flex;
            justify-content: space-between;
            gap: 8px;
            margin-bottom: 1.5rem;
            background: rgba(15, 20, 35, 0.7);
            padding: 8px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .step-box {
            flex: 1;
            text-align: center;
            padding: 6px 4px;
            border-radius: 8px;
            font-size: 0.78rem;
            font-weight: 700;
            color: #8892B0;
            background: rgba(255, 255, 255, 0.03);
        }
        .step-box.active {
            background: linear-gradient(135deg, rgba(255,215,0,0.25), rgba(255,140,0,0.25));
            color: #FFE066;
            border: 1px solid rgba(255, 215, 0, 0.6);
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span {
            color: #FFFFFF !important;
            text-shadow: 0px 2px 6px rgba(0, 0, 0, 0.9);
            font-weight: 600;
        }

        .upload-card-container {
            background: rgba(25, 30, 50, 0.7);
            border: 1px solid rgba(255, 215, 0, 0.4);
            border-radius: 12px;
            padding: 1.2rem 1rem;
            text-align: center;
            margin-bottom: 1.0rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .video-container-34 {
            max-width: 85% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            margin-bottom: 1.2rem !important;
        }

        .wx-wood { color: #55FF55 !important; font-weight: bold; }
        .wx-fire { color: #FF6666 !important; font-weight: bold; }
        .wx-earth { color: #FFDD44 !important; font-weight: bold; }
        .wx-metal { color: #E0E0E0 !important; font-weight: bold; }
        .wx-water { color: #66CCFF !important; font-weight: bold; }

        .center-msg {
            text-align: center !important;
            margin-bottom: 1rem !important;
        }

        /* トップ選択ボタン */
        div.stButton > button[kind="secondary"] {
            background: rgba(20, 26, 45, 0.85) !important;
            color: #FFE066 !important;
            border: 1.5px solid rgba(255, 215, 0, 0.7) !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5) !important;
            backdrop-filter: blur(6px) !important;
            border-radius: 10px !important;
        }
        div.stButton > button[kind="secondary"]:hover {
            background: rgba(35, 45, 75, 0.95) !important;
            color: #FFFFFF !important;
            border-color: #FFD700 !important;
            box-shadow: 0 0 12px rgba(255, 215, 0, 0.5) !important;
        }

        /* ZIPボタン */
        div.stDownloadButton > button {
            background-color: #2b304d !important;
            color: #FFE066 !important;
            border: 1.5px solid #FFD700 !important;
            font-weight: bold !important;
            font-size: 1rem !important;
        }
        div.stDownloadButton > button:hover {
            background-color: #3f466e !important;
            color: #FFFFFF !important;
        }

        /* Instagramキャプションエリア */
        .stCodeBlock, div[data-baseweb="textarea"], pre {
            background-color: #121624 !important;
            border: 1.5px solid rgba(255, 215, 0, 0.6) !important;
            border-radius: 10px !important;
        }
        .stCodeBlock code, .stCodeBlock span, pre code, pre span {
            color: #F0F4FF !important;
            font-weight: 700 !important;
            text-shadow: 0px 1px 2px rgba(0,0,0,0.8) !important;
        }

        .stCaption {
            color: #E2E8F0 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.9) !important;
        }

        /* 🧭 九星・方位盤グリッドのスタイル */
        .compass-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            max-width: 380px;
            margin: 1.2rem auto;
            padding: 12px;
            background: rgba(12, 16, 28, 0.65);
            backdrop-filter: blur(8px);
            border: 2px solid #FFD700;
            border-radius: 14px;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.2);
        }
        .compass-cell {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 8px;
            padding: 8px 4px;
            text-align: center;
        }
        .compass-cell.center { background: rgba(255, 215, 0, 0.22); border-color: #FFD700; }
        .compass-cell.good { background: rgba(50, 205, 50, 0.25); border-color: #55FF55; }
        .compass-cell.bad { background: rgba(255, 69, 0, 0.25); border-color: #FF6666; }
        .compass-title { font-size: 0.72rem; color: #CCCCCC; margin-bottom: 2px; }
        .compass-dir { font-size: 0.95rem; font-weight: bold; color: #FFFFFF; }
        .compass-status { font-size: 0.85rem; font-weight: bold; margin-top: 2px; }
        .status-good { color: #55FF55; text-shadow: 0 0 6px rgba(85,255,85,0.8); }
        .status-bad { color: #FF6666; text-shadow: 0 0 6px rgba(255,102,102,0.8); }
        .status-center { color: #FFE066; }
        </style>
    """
    css_code = css_template.replace('__IMAGE_DATA__', img_base64)
    st.markdown(css_code, unsafe_allow_html=True)

st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

# ヒーローヘッダー
st.markdown("""
<div class="hero-header notranslate">
    <div class="hero-badge">✨ AI陰陽心理鑑定 ✨</div>
    <div class="main-title-text">アイコン個性診断<br>＆ 開運鑑定</div>
    <div class="subtitle-text">✨アイコンから『個性と深層心理』を紐解き、開運アドバイスをお届けします✨</div>
</div>
""", unsafe_allow_html=True)

def render_video(video_filename="cat_video2.mp4"):
    if os.path.exists(video_filename):
        with open(video_filename, "rb") as f:
            v_bytes = f.read()
        v_base64 = base64.b64encode(v_bytes).decode()
        v_html = f"""
        <div class="video-container-34">
            <video width="100%" autoplay muted loop playsinline style="border-radius: 12px; border: 1.5px solid rgba(255, 215, 0, 0.6); box-shadow: 0 6px 20px rgba(0,0,0,0.5);">
                <source src="data:video/mp4;base64,{v_base64}" type="video/mp4">
            </video>
        </div>
        """
        st.markdown(v_html, unsafe_allow_html=True)

# ==========================================
# 3. 万年暦・五行・九星気学計算・カラー抽出・描画ヘルパー
# ==========================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
GAN_WU_XING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WU_XING_CLASS = {"木": "wx-wood", "火": "wx-fire", "土": "wx-earth", "金": "wx-metal", "水": "wx-water"}

NINE_STARS = ["一白水星", "二黒土星", "三碧木星", "四緑木星", "五黄土星", "六白金星", "七赤金星", "八白土星", "九紫火星"]

def get_honmei_sei(birth_date: datetime.date) -> str:
    year = birth_date.year
    if birth_date < datetime.date(year, 2, 4):
        year -= 1
    remainder = (11 - (year % 9)) % 9
    return NINE_STARS[remainder]

def get_day_gan(dt: datetime.date) -> str:
    base_date = datetime.date(1900, 1, 1)
    return TIAN_GAN[(dt - base_date).days % 10]

def calculate_guxing_info(birth_date: datetime.date, target_date: datetime.date):
    user_gan = get_day_gan(birth_date)
    today_gan = get_day_gan(target_date)
    honmei_sei = get_honmei_sei(birth_date)
    return {
        "user_gan": user_gan, 
        "user_wuxing": GAN_WU_XING[user_gan], 
        "today_gan": today_gan, 
        "today_wuxing": GAN_WU_XING[today_gan],
        "honmei_sei": honmei_sei
    }

def format_wuxing_color(text: str) -> str:
    for wx, cls_name in WU_XING_CLASS.items():
        text = text.replace(f"「{wx}」", f"「<span class='{cls_name}'>{wx}</span>」")
        text = text.replace(f"五行タイプ: {wx}", f"五行タイプ: <span class='{cls_name}'>{wx}</span>")
    return text

def extract_dominant_colors(image, num_colors=3):
    img = image.copy().convert("RGB").resize((100, 100))
    result = img.quantize(colors=num_colors)
    palette = result.getpalette()[:num_colors*3]
    colors = []
    for i in range(0, len(palette), 3):
        r, g, b = palette[i], palette[i+1], palette[i+2]
        colors.append(f"RGB({r},{g},{b})")
    
    stat = ImageOps.grayscale(img)
    avg_brightness = sum(stat.getdata()) / (100 * 100)
    brightness_text = "明るめ・親しみやすいトーン" if avg_brightness > 128 else "ダーク・ミステリアスなトーン"
    
    return f"主要カラー: {', '.join(colors)} / 全体の印象: {brightness_text}"

@st.cache_resource
def get_readable_font(size):
    font_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "C:\\Windows\\Fonts\\meiryob.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
    return ImageFont.load_default()

def wrap_text(text, font, max_width):
    lines, current_line = [], ""
    for char in text:
        w = font.getlength(current_line + char) if hasattr(font, 'getlength') else font.getbbox(current_line + char)[2]
        if w <= max_width: current_line += char
        else: lines.append(current_line); current_line = char
    if current_line: lines.append(current_line)
    return lines

def create_base_card():
    card = Image.new("RGBA", (1080, 1080), (12, 16, 28, 255))
    draw = ImageDraw.Draw(card)
    for y in range(1080):
        alpha_val = int(20 + 15 * math.sin(y / 60.0))
        draw.line([(0, y), (1080, y)], fill=(35, 40, 70, alpha_val))
    draw.rectangle([25, 25, 1055, 1055], outline=(212, 175, 55), width=6)
    draw.rectangle([40, 40, 1040, 1040], outline=(255, 224, 102), width=2)
    corner_len = 50
    for cx, cy in [(40, 40), (1040, 40), (40, 1040), (1040, 1040)]:
        dx, dy = (1 if cx == 40 else -1), (1 if cy == 40 else -1)
        draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=(255, 235, 120), width=5)
        draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=(255, 235, 120), width=5)
    return card, draw

def draw_radar_chart(draw, center_x, center_y, radius, params, font):
    labels = ["洞察力", "直感力", "社交性", "独自性", "柔軟性"]
    angle_step = 2 * math.pi / len(labels)
    start_angle = -math.pi / 2
    bg_pts = [(center_x + radius * math.cos(start_angle + i * angle_step), center_y + radius * math.sin(start_angle + i * angle_step)) for i in range(5)]
    draw.polygon(bg_pts, fill=(20, 25, 40, 200)) 
    for r_ratio in [0.25, 0.5, 0.75, 1.0]:
        r = radius * r_ratio
        pts = [(center_x + r * math.cos(start_angle + i * angle_step), center_y + r * math.sin(start_angle + i * angle_step)) for i in range(5)]
        draw.polygon(pts, outline=(120, 140, 180, 255), width=2)
    data_points = []
    for i, label in enumerate(labels):
        angle = start_angle + i * angle_step
        ax, ay = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
        draw.line([(center_x, center_y), (ax, ay)], fill=(120, 140, 180, 255), width=2)
        lx, ly = center_x + (radius + 60) * math.cos(angle), center_y + (radius + 40) * math.sin(angle)
        draw.text((lx, ly), label, font=font, fill=(255, 255, 255), anchor="mm")
        val = params.get(label, 70) / 100.0
        data_points.append((center_x + (radius * val) * math.cos(angle), center_y + (radius * val) * math.sin(angle)))
    draw.polygon(data_points, fill=(255, 215, 0, 100), outline=(255, 215, 0, 255), width=6)
    for pt in data_points: draw.ellipse([pt[0]-10, pt[1]-10, pt[0]+10, pt[1]+10], fill=(255, 255, 255), outline=(255, 215, 0), width=4)

def generate_carousel_images(user_icon_img, type_name, wuxing_type, tags, params, text_blocks, style_name="甘口（褒めちぎり）"):
    images = []
    title_font, ssr_font = get_readable_font(42), get_readable_font(34)
    subtitle_font, heading_font = get_readable_font(42), get_readable_font(40)
    body_font, tag_font, chart_font, thank_font = get_readable_font(30), get_readable_font(28), get_readable_font(30), get_readable_font(44)

    # 1枚目
    img1, draw1 = create_base_card()
    draw1.text((540, 120), "― 陰陽心理鑑定 ―", font=subtitle_font, fill=(255, 224, 102), anchor="mm")
    icon_size = 530
    icon_cropped = ImageOps.fit(user_icon_img.convert("RGBA"), (icon_size, icon_size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (icon_size, icon_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, icon_size, icon_size), fill=255)
    icon_x, icon_y = (1080 - icon_size) // 2, 200
    img1.paste(icon_cropped, (icon_x, icon_y), mask)
    draw1.ellipse([icon_x-6, icon_y-6, icon_x+icon_size+6, icon_y+icon_size+6], outline=(255, 215, 0), width=8)
    draw1.rectangle([70, 770, 1010, 910], fill=(20, 25, 40, 230), outline=(212, 175, 55), width=3)
    
    badge_text = "★ 激辛鑑定結果 🌶️ ★" if "超辛口" in style_name else ("★ 辛口鑑定結果 🌶️ ★" if "辛口" in style_name else "★ SSR ★")
    draw1.text((540, 810), badge_text, font=ssr_font, fill=(255, 90, 90) if "辛口" in style_name else (255, 235, 120), anchor="mm")
    
    wrapped_title = wrap_text(type_name, title_font, 880)
    draw1.text((540, 865), wrapped_title[0], font=title_font, fill=(255, 255, 255), anchor="mm")
    tag_str = f"五行: {wuxing_type} / " + " ".join([f"#{t.strip('#')}" for t in tags[:3]])
    wrapped_tags = wrap_text(tag_str, tag_font, 900)
    for i, wt in enumerate(wrapped_tags): draw1.text((540, 950 + i * 45), wt, font=tag_font, fill=(200, 220, 255), anchor="mm")
    images.append(img1)

    # 2枚目
    img2, draw2 = create_base_card()
    draw2.text((540, 130), "【 潜在能力パラメーター 】", font=heading_font, fill=(255, 224, 102), anchor="mm")
    draw_radar_chart(draw2, center_x=540, center_y=600, radius=320, params=params, font=chart_font)
    images.append(img2)

    # 3枚目
    img3, draw3 = create_base_card()
    draw3.text((100, 110), "■ 基本性格と深層心理", font=heading_font, fill=(64, 224, 208))
    y_offset = 180
    for line in wrap_text(text_blocks.get("summary_card", ""), body_font, 880):
        if y_offset > 480: break
        draw3.text((100, y_offset), line, font=body_font, fill=(240, 240, 250)); y_offset += 48
    y_offset = 550
    draw3.text((100, y_offset), "■ 対人コミュニケーション", font=heading_font, fill=(255, 140, 0))
    y_offset += 70
    for line in wrap_text(text_blocks.get("comm_card", ""), body_font, 880):
        if y_offset > 980: draw3.text((100, y_offset), "...", font=body_font, fill=(240, 240, 250)); break
        draw3.text((100, y_offset), line, font=body_font, fill=(240, 240, 250)); y_offset += 48
    images.append(img3)

    # 4枚目
    img4, draw4 = create_base_card()
    draw4.text((100, 120), "🔮 開運アドバイス & 本日の吉方位", font=heading_font, fill=(224, 176, 255))
    y_offset = 200
    for line in wrap_text(text_blocks.get("advice_card", ""), body_font, 880):
        draw4.text((100, y_offset), line, font=body_font, fill=(240, 240, 250)); y_offset += 48
    y_offset += 80
    phrase = text_blocks.get("phrase", "")
    if phrase:
        wrapped_phrase = wrap_text(f"「{phrase}」", heading_font, 860)
        box_height = len(wrapped_phrase) * 60 + 50
        draw4.rectangle([70, y_offset, 1010, y_offset + box_height], fill=(40, 30, 50, 230), outline=(255, 215, 0), width=4)
        phrase_y = y_offset + 25
        for w in wrapped_phrase: draw4.text((540, phrase_y + 25), w, font=heading_font, fill=(255, 224, 102), anchor="mm"); phrase_y += 60
    button_y = 920
    draw4.rectangle([140, button_y, 940, button_y + 100], fill=(220, 50, 50), outline=(255, 215, 0), width=5)
    draw4.text((540, button_y + 48), "👉 スワイプしてくれてありがとう！ ✨", font=thank_font, fill=(255, 255, 255), anchor="mm")
    images.append(img4)

    return images

def generate_omikuji_card_image(fortune_type, omikuji_raw_text):
    card_w, card_h = 1080, 1700
    card = Image.new("RGBA", (card_w, card_h), (25, 18, 30, 255))
    draw = ImageDraw.Draw(card)
    
    title_font = get_readable_font(36)
    fortune_font = get_readable_font(68)
    heading_font = get_readable_font(28)
    body_font = get_readable_font(23)
    footer_font = get_readable_font(22)
    
    draw.rectangle([20, 20, card_w - 20, card_h - 20], outline=(212, 175, 55), width=5)
    draw.rectangle([30, 30, card_w - 30, card_h - 30], outline=(255, 224, 102), width=2)
    draw.text((card_w // 2, 60), "― 陰陽開運おみくじ ―", font=title_font, fill=(255, 224, 102), anchor="mm")
    
    fortune_color = (255, 90, 90) if fortune_type in ["超大吉", "大吉"] else ((180, 200, 210) if fortune_type == "凶" else (255, 224, 102))
    draw.rectangle([card_w // 2 - 180, 95, card_w // 2 + 180, 185], fill=(40, 25, 45), outline=fortune_color, width=4)
    draw.text((card_w // 2, 140), fortune_type, font=fortune_font, fill=fortune_color, anchor="mm")
    
    box_top, box_bottom = 200, 1620
    draw.rectangle([45, box_top, card_w - 45, box_bottom], fill=(18, 12, 24), outline=(100, 80, 120), width=2)
    
    lines = omikuji_raw_text.split('\n')
    y_offset = box_top + 20
    for line in lines:
        if y_offset > box_bottom - 30: break
        clean_line = re.sub(r'\*+', '', line).strip()
        if not clean_line or clean_line.startswith("---") or clean_line.startswith("==="): continue
        
        if "【" in clean_line and "】" in clean_line:
            y_offset += 12
            draw.text((card_w // 2, y_offset), clean_line, font=heading_font, fill=(255, 220, 100), anchor="mm")
            y_offset += 32
        else:
            wrapped = wrap_text(clean_line, body_font, 950)
            for w in wrapped:
                if y_offset > box_bottom - 25: break
                draw.text((card_w // 2, y_offset), w, font=body_font, fill=(240, 240, 250), anchor="mm")
                y_offset += 28
            y_offset += 4

    draw.text((card_w // 2, 1655), "--- 陰陽SNSアイコン診断 & 開運おみくじ ---", font=footer_font, fill=(160, 170, 190), anchor="mm")
    return card

def render_plotly_radar(params):
    categories = ["洞察力", "直感力", "社交性", "独自性", "柔軟性"]
    values = [params.get(c, 70) for c in categories]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(255, 215, 0, 0.45)',
        line=dict(color='#FFD700', width=3),
        marker=dict(size=8, color='#FFFFFF')
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor="rgba(255,255,255,0.4)", gridcolor="rgba(255,255,255,0.2)"),
            angularaxis=dict(tickfont=dict(size=14, color="#FFE066"), gridcolor="rgba(255,255,255,0.2)"),
            bgcolor="rgba(20, 25, 45, 0.85)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=30, b=30),
        showlegend=False,
        height=360
    )
    st.plotly_chart(fig, use_container_width=True)

# 🧭 九星気学（3×3動的方位盤）
def render_compass_board(good_dirs, bad_dirs, honmei_sei):
    grid_layout = [
        ("南東", "大吉 ⭕" if "南東" in good_dirs else ("凶 ❌" if "南東" in bad_dirs else "―")),
        ("南", "大吉 ⭕" if "南" in good_dirs else ("凶 ❌" if "南" in bad_dirs else "―")),
        ("南西", "大吉 ⭕" if "南西" in good_dirs else ("凶 ❌" if "南西" in bad_dirs else "―")),
        ("東", "大吉 ⭕" if "東" in good_dirs else ("凶 ❌" if "東" in bad_dirs else "―")),
        ("中央", honmei_sei[:2]),
        ("西", "大吉 ⭕" if "西" in good_dirs else ("凶 ❌" if "西" in bad_dirs else "―")),
        ("北東", "大吉 ⭕" if "北東" in good_dirs else ("凶 ❌" if "北東" in bad_dirs else "―")),
        ("北", "大吉 ⭕" if "北" in good_dirs else ("凶 ❌" if "北" in bad_dirs else "―")),
        ("北西", "大吉 ⭕" if "北西" in good_dirs else ("凶 ❌" if "北西" in bad_dirs else "―"))
    ]

    grid_html = "<div class='compass-grid'>"
    for dir_name, status in grid_layout:
        cls = "center" if dir_name == "中央" else ("good" if "⭕" in status else ("bad" if "❌" in status else ""))
        status_cls = "status-center" if dir_name == "中央" else ("status-good" if "⭕" in status else ("status-bad" if "❌" in status else ""))
        
        grid_html += f"""
        <div class='compass-cell {cls}'>
            <div class='compass-title'>{dir_name if dir_name != "中央" else "本命星"}</div>
            <div class='compass-dir'>{dir_name if dir_name != "中央" else honmei_sei[:2]}</div>
            <div class='compass-status {status_cls}'>{status}</div>
        </div>
        """
    grid_html += "</div>"
    return grid_html

def generate_insta_caption(type_name, tags, style_name):
    tag_str = " ".join([f"#{t.strip('#')}" for t in tags])
    style_tag = " #超辛口AI診断 #ボコボコにされた" if "超辛口" in style_name else (" #辛口診断" if "辛口" in style_name else "")
    caption = f"""✨ AI陰陽心理鑑定でSNSアイコンを診断してみた！ ✨

私のアイコン診断タイプは...
【{type_name}】でした🔮 ({style_name}モード)

{tag_str}

みんなもやってみてね！👇
#アイコン診断 #陰陽鑑定 #九星気学 #吉方位 #AI診断 #SNSアイコン{style_tag}
"""
    return caption

# ==========================================
# 4. モード選択 & メインコンテンツ
# ==========================================
if st.session_state.mode is None:
    st.markdown('<div class="choice-title">✨ どの鑑定にするニャ？ ✨</div>', unsafe_allow_html=True)
    
    render_video("cat_video.mp4")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("🖼️ SNSアイコン診断", type="secondary", use_container_width=True):
            st.session_state.mode = "diagnosis"
            st.session_state.step = 0
            st.rerun()
    with col_b:
        if st.button("⛩️ 開運おみくじ", type="secondary", use_container_width=True):
            st.session_state.mode = "omikuji_only"
            st.rerun()
    with col_c:
        if st.button("🧭 今日の吉方位診断", type="secondary", use_container_width=True):
            st.session_state.mode = "direction_only"
            st.rerun()

# ------------------------------------------
# 🧭 モード3: 今日の吉方位診断（背景スケルトン極限修正）
# ------------------------------------------
elif st.session_state.mode == "direction_only":
    st.markdown('<div class="omikuji-heading">🧭 九星気学・今日の吉方位鑑定 🧭</div>', unsafe_allow_html=True)
    if st.button("⬅️ 最初に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.direction_result_text = None
        st.rerun()
        
    st.markdown('<p class="center-msg">生年月日を入力して、本日あなたに幸運をもたらす吉方位・注意すべき凶方位を鑑定します！</p>', unsafe_allow_html=True)
    
    b_input_dir = st.text_input("生年月日を8桁の数字で入力（例: 19900101）", value=st.session_state.birth_date_str, max_chars=8, key="b_dir_input")
    st.session_state.birth_date_str = b_input_dir
    
    if st.button("🔮 吉方位を鑑定する 🔮", type="primary", use_container_width=True):
        active_key = get_api_key()
        if not active_key:
            st.error(".env ファイルに GEMINI_API_KEY を設定するか、API Key を確認してください。")
        elif len(b_input_dir) != 8 or not b_input_dir.isdigit():
            st.error("生年月日は8桁の数字で入力してください。")
        else:
            try:
                valid_date = datetime.date(int(b_input_dir[:4]), int(b_input_dir[4:6]), int(b_input_dir[6:8]))
                wuxing_info = calculate_guxing_info(valid_date, datetime.date.today())
                
                status_holder_dir = st.empty()
                with status_holder_dir.container():
                    render_video("cat_video2.mp4")
                    with st.spinner("九星気学の盤面を読み解き、本日の吉方位・凶方位を鑑定中..."):
                        prompt_dir = f"""
あなたは九星気学に精通した知的な陰陽師です。
ユーザーの本命星は『{wuxing_info['honmei_sei']}』、本日の日付は『{datetime.date.today()}』です。

九星気学に基づき、本日の「吉方位」と「凶方位」を特定し、開運アドバイスを作成してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【厳格フォーマットルール】
1行目: 吉方位: [方位名のみ。カンマ区切り。例: 北東, 南]
2行目: 凶方位: [方位名のみ。カンマ区切り。例: 南, 北]
3行目: 【最高吉方位解説】
4行目: [最高吉方位と凶方位の補足解説]
5行目: 【項目別アドバイス】
6行目: 💖 恋愛・対人運: [アドバイス内容]
7行目: 💼 仕事・学業運: [アドバイス内容]
8行目: ✈️ 旅行・お出かけ運: [アドバイス内容]
9行目: 🏠 引っ越し・模様替え運: [アドバイス内容]
10行目: 【黒猫陰陽師からのメッセージ】
11行目: [アドバイス内容]
"""
                        client = genai.Client(api_key=active_key)
                        response_dir = client.models.generate_content(
                            model=GEMINI_MODEL_NAME,
                            contents=prompt_dir
                        )
                        st.session_state.direction_result_text = response_dir.text
                status_holder_dir.empty()
            except Exception as e:
                st.error(f"吉方位鑑定中にエラーが発生しました: {e}")

    if st.session_state.direction_result_text:
        valid_date = datetime.date(int(st.session_state.birth_date_str[:4]), int(st.session_state.birth_date_str[4:6]), int(st.session_state.birth_date_str[6:8]))
        honmei_sei = get_honmei_sei(valid_date)
        
        raw_text = st.session_state.direction_result_text
        lines = [re.sub(r'\*+', '', l).strip() for l in raw_text.split('\n') if l.strip()]
        
        good_dirs, bad_dirs = [], []
        for l in lines:
            if l.startswith("吉方位:"):
                good_dirs = [d.strip() for d in l.replace("吉方位:", "").split(",") if d.strip()]
            elif l.startswith("凶方位:"):
                bad_dirs = [d.strip() for d in l.replace("凶方位:", "").split(",") if d.strip()]
        
        compass_board_html = render_compass_board(good_dirs, bad_dirs, honmei_sei)
        
        good_text = ", ".join(good_dirs) if good_dirs else "特になし（平穏）"
        bad_text = ", ".join(bad_dirs) if bad_dirs else "特になし（平和）"

        st.markdown(f"""
        <div class="notranslate" style="background: rgba(12, 16, 28, 0.55); backdrop-filter: blur(8px); border: 1.5px solid rgba(212, 175, 55, 0.8); border-radius: 14px; padding: 1.5rem; margin-top: 1.2rem;">
            <h3 style="color:#FFE066; text-align:center; margin-top:0; font-size: 1.3rem; text-shadow: 0 2px 4px #000;">🧭 本日の九星気学 方位盤 🧭</h3>
            <div style="text-align:center; color:#D0D8EC; font-size:0.95rem; margin-bottom:8px; font-weight:bold;">本命星: {honmei_sei}</div>
            {compass_board_html}
            <div style="margin-top: 1.2rem;">
                <div style="background:rgba(20, 35, 25, 0.45); border-left:4px solid #55FF55; padding:10px 12px; border-radius:6px; margin-bottom:10px; border:1px solid rgba(85,255,85,0.3);">
                    <b style="color:#FFE066; font-size:1.0rem; text-shadow:0 1px 2px #000;">✨ 本日の最高吉方位：</b>
                    <span style="color:#55FF55; font-size:1.2rem; font-weight:bold; margin-left:6px; text-shadow:0 0 8px rgba(85,255,85,0.6);">{good_text}</span>
                </div>
                <div style="background:rgba(35, 20, 25, 0.45); border-left:4px solid #FF6666; padding:10px 12px; border-radius:6px; margin-bottom:16px; border:1px solid rgba(255,102,102,0.3);">
                    <b style="color:#FFE066; font-size:1.0rem; text-shadow:0 1px 2px #000;">⚠️ 本日の警戒凶方位：</b>
                    <span style="color:#FF6666; font-size:1.1rem; font-weight:bold; margin-left:6px; text-shadow:0 0 8px rgba(255,102,102,0.6);">{bad_text}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h4 style='color:#FFE066; margin-top:1.2rem; margin-bottom:0.8rem; text-shadow:0 2px 4px #000;'>【項目別開運アドバイス】</h4>", unsafe_allow_html=True)
        
        for line in lines:
            if any(line.startswith(prefix) for prefix in ["💖", "💼", "✈️", "🏠"]):
                parts = line.split(":", 1)
                title = parts[0]
                body = parts[1] if len(parts) > 1 else ""
                # 🎨 背景をさらに透かせるように透過度を 0.18 に調整
                st.markdown(f"""
                <div style="background: rgba(12, 16, 28, 0.18); backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px); border: 1px solid rgba(255, 215, 0, 0.5); padding: 12px 16px; margin-bottom: 12px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <div style="color:#FFE066; font-size:1.05rem; font-weight:bold; margin-bottom:6px; text-shadow:0 2px 4px rgba(0,0,0,0.95);">{title}</div>
                    <div style="color:#FFFFFF; font-size:0.95rem; line-height:1.65; font-weight:600; text-shadow:0 2px 4px rgba(0,0,0,0.95);">{body}</div>
                </div>
                """, unsafe_allow_html=True)
            elif "【黒猫陰陽師" in line or line.startswith("【"):
                continue
            elif not line.startswith("吉方位:") and not line.startswith("凶方位:"):
                st.markdown(f"""
                <div style="background: rgba(12, 16, 28, 0.18); backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px); border-left: 3px solid #E0B0FF; border-top: 1px solid rgba(224,176,255,0.3); border-right: 1px solid rgba(224,176,255,0.3); border-bottom: 1px solid rgba(224,176,255,0.3); padding: 10px 14px; margin-bottom: 10px; border-radius: 6px;">
                    <div style="color:#FFFFFF; font-size:0.95rem; line-height:1.65; font-weight:600; text-shadow:0 2px 4px rgba(0,0,0,0.95);">{line}</div>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------
# ⛩️ モード2: 開運おみくじ
# ------------------------------------------
elif st.session_state.mode == "omikuji_only":
    st.markdown('<div class="omikuji-heading">⛩️ 開運おみくじ ⛩️</div>', unsafe_allow_html=True)
    if st.button("⬅️ 最初に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.omikuji_text = None
        st.session_state.omikuji_card_image = None
        st.session_state.omikuji_result_type = None
        st.rerun()
        
    st.markdown('<p class="center-msg">ボタンを押すと、本日の運勢と開運おみくじが生成されます！</p>', unsafe_allow_html=True)
    if st.button("☯️ おみくじを引く ☯️", type="primary", use_container_width=True, key="omikuji_btn_single"):
        active_key = get_api_key()
        if not active_key:
            st.error(".env ファイルに GEMINI_API_KEY を設定するか、API Key を確認してください。")
        else:
            fortune_list = ["超大吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶"]
            selected_fortune = random.choice(fortune_list)
            st.session_state.omikuji_result_type = selected_fortune

            status_holder = st.empty()
            with status_holder.container():
                render_video("cat_video4.mp4")
                with st.spinner("黒猫がおみくじ筒をシャカシャカ振り振り、おみくじデータを錬成中..."):
                    try:
                        omikuji_prompt = f"""
あなたは黒猫の陰陽師です。本格的で読み応えのある神社のおみくじの文章を作成してください。
今回の運勢結果は『{selected_fortune}』です。
以下の項目に沿って、少しのユーモアと温かい知性を含め、充実した内容で記述してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【全体運】
（運勢の背景にある深い意味と、心構えを2〜3文で味わい深く書いてください）
【仕事・学業運】
（具体的なアドバイスや成果を出すためのコツを2文程度で書いてください）
【恋愛・対人運】
（人間関係を良好にするための秘訣を2文程度で書いてください）
【健康運】
（心身を健やかに保つための温かいアドバイスを書いてください）
【旅行・お出かけ運】
（吉となる方角や、お出かけ時の心構えを書いてください）
【ラッキーAIツール】
（例: ChatGPT, Gemini等のなかから1つと、その活用ワンポイント）
【SNS開運アクション】
（今日SNSで運気を上げるための具体的なアクション）
【黒猫陰陽師からの裏ひとこと】
（クスッと笑える親しみやすくユーモアのあるアドバイス）
"""
                        client = genai.Client(api_key=active_key)
                        omikuji_response = client.models.generate_content(
                            model=GEMINI_MODEL_NAME,
                            contents=omikuji_prompt
                        )
                        
                        st.session_state.omikuji_text = omikuji_response.text
                        st.session_state.omikuji_card_image = generate_omikuji_card_image(selected_fortune, omikuji_response.text)
                    except Exception as e:
                        st.error(f"おみくじ生成中にエラーが発生しました: {e}")
            status_holder.empty()

    if st.session_state.omikuji_text and st.session_state.omikuji_card_image:
        trigger_omikuji_animation(st.session_state.omikuji_result_type)
            
        st.success(f"⛩️ 今日のおみくじ結果: 【{st.session_state.omikuji_result_type}】 ⛩️ (タップで拡大できます)")
        st.image(st.session_state.omikuji_card_image, use_container_width=True)

# ------------------------------------------
# 🖼️ モード1: アイコン診断
# ------------------------------------------
elif st.session_state.mode == "diagnosis":
    if st.button("⬅️ モード選択に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.step = 0
        st.session_state.result_text = None
        st.session_state.card_images = None
        st.session_state.radar_params = None
        st.session_state.omikuji_text = None
        st.session_state.omikuji_card_image = None
        st.session_state.omikuji_result_type = None
        st.rerun()

    step_labels = ["1. 生年月日・設定", "2. アイコン選択", "3. 鑑定実行"]
    step_html = "<div class='step-container'>"
    for i, lbl in enumerate(step_labels):
        active_cls = " active" if i == st.session_state.step else ""
        step_html += f"<div class='step-box{active_cls}'>{lbl}</div>"
    step_html += "</div>"
    st.markdown(step_html, unsafe_allow_html=True)

    # STEP 0
    if st.session_state.step == 0:
        st.subheader("🗓️ 生年月日＆診断テイストの選択")
        b_input = st.text_input("生年月日を8桁の数字で入力してください（例: 19900101）", value="19900101" if st.session_state.birth_date_str == "19700101" else st.session_state.birth_date_str, max_chars=8)
        st.session_state.birth_date_str = b_input
        
        st.write("")
        st.write("🎭 **黒猫陰陽師の診断スタイルを選択**")
        style_choice = st.radio("診断の口調を選んでください", ["甘口（褒めちぎり）", "辛口（ズバッと毒舌）", "超辛口（容赦なし激辛）"], horizontal=True)
        st.session_state.diagnosis_style = style_choice
        
        st.write("")
        if st.button("次へ進む ➔（アイコン選択へ）", type="primary", use_container_width=True):
            if len(b_input) == 8 and b_input.isdigit():
                st.session_state.step = 1
                st.rerun()
            else:
                st.error("生年月日は8桁の数字で入力してください。")

    # STEP 1
    elif st.session_state.step == 1:
        st.subheader("🖼️ SNSアイコンのアップロード")
        
        st.markdown("""
        <div class="upload-card-container">
            <h3 style="color: #FFE066; margin-top: 0; font-size: 1.1rem; font-weight: 700;">✨ 下の枠からアイコン画像を選択してください ✨</h3>
            <p style="color: #D0D8EC; font-size: 0.88rem; margin-bottom: 0;">陰陽心理鑑定で、あなたのアイコンの特徴と魅力を深く解読します！</p>
        </div>
        """, unsafe_allow_html=True)

        st.info(
            "⚠️ **ご安心してご利用いただくために**\n\n"
            "• アップロードされた画像は診断の解析にのみ使用され、外部への保存や公開は一切されません。\n"
            "• ご自身が所有しているアイコンや、権利上の問題がない画像をご使用ください。"
        )

        uploaded_file = st.file_uploader("アイコン画像（PNG、JPG）", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
        if uploaded_file is not None:
            st.session_state.uploaded_file = uploaded_file
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2: st.image(Image.open(uploaded_file), caption="📷 選択されたアイコンプレビュー", use_container_width=True)
        st.write("")
        col_prev, col_next = st.columns(2)
        with col_prev:
            if st.button("⬅️ 前へ戻る", use_container_width=True): st.session_state.step = 0; st.rerun()
        with col_next:
            if st.button("次へ進む ➔（鑑定実行へ）", type="primary", use_container_width=True):
                if "uploaded_file" in st.session_state and st.session_state.uploaded_file is not None:
                    st.session_state.step = 2; st.rerun()
                else: st.warning("アイコン画像をアップロードしてください。")

    # STEP 2
    elif st.session_state.step == 2:
        st.subheader("🔮 鑑定の準備が整いました🔮")
        col_prev, col_start = st.columns([1, 2])
        with col_prev:
            if st.button("⬅️ 前へ戻る", use_container_width=True): st.session_state.step = 1; st.rerun()
        with col_start:
            start_button = st.button("☯️ 鑑定を開始する ☯️", type="primary", use_container_width=True)

        if start_button:
            birth_str = st.session_state.birth_date_str
            try:
                valid_date = datetime.date(int(birth_str[:4]), int(birth_str[4:6]), int(birth_str[6:8]))
            except:
                valid_date = None

            active_key = get_api_key()
            if not active_key:
                st.error(".env ファイルに GEMINI_API_KEY を設定するか、API Key を確認してください。")
            elif valid_date is None:
                st.error("生年月日のフォーマットが正しくありません。")
            elif "uploaded_file" not in st.session_state or st.session_state.uploaded_file is None:
                st.warning("アイコン画像がありません。")
            else:
                try:
                    image = Image.open(st.session_state.uploaded_file)
                    wuxing_info = calculate_guxing_info(valid_date, datetime.date.today())
                    color_analysis = extract_dominant_colors(image)
                    
                    st.session_state.omikuji_text = None
                    st.session_state.omikuji_result_type = None
                    st.session_state.omikuji_card_image = None
                    st.session_state.card_images = None
                    st.session_state.radar_params = None

                    status_holder = st.empty()
                    with status_holder.container():
                        render_video("cat_video3.mp4")

                        with st.spinner("深層心理と九星気学を解析し、鑑定結果を錬成中..."):
                            if st.session_state.diagnosis_style == "超辛口（容赦なし激辛）":
                                style_instruction = "容赦のない激辛毒舌モードです。画像の特徴（痛いセルフプロデュース感や、痛烈な視覚的突っ込みどころ）を鋭く笑いに変えつつ、皮肉と愛あるユーモアでボコボコにぶった斬ってください。"
                            elif st.session_state.diagnosis_style == "辛口（ズバッと毒舌）":
                                style_instruction = "愛のある毒舌と鋭いツッコミを交えつつ、本質をバッサリ突く『辛口モード』で記述してください。"
                            else:
                                style_instruction = "ユーザーの魅力を絶賛し、勇気と元気が湧き出る『甘口（褒めちぎり）モード』で記述してください。"
                            
                            prompt = f"""
あなたは人間観察に長けた、非常に知的な陰陽心理鑑定士（黒猫の陰陽師）です。
【鑑定スタイル】: {style_instruction}

提供された「SNSアイコン画像」の視覚的特徴と、以下の色覚自動解析データを組み合わせて分析してください。
【色覚解析データ】: {color_analysis}

※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

以下のフォーマットを「必ず」厳守して出力してください。

--------------------------------------------------
■ 診断結果：【[キャッチーな〇〇タイプ名]】
■ 3つのハッシュタグ: #[タグ1], #[タグ2], #[タグ3]
■ パラメータ: 洞察力:[40-100], 直感力:[40-100], 社交性:[40-100], 独自性:[40-100], 柔軟性:[40-100]

[アイコン全体の印象やセルフプロデュース力、視覚的ギャップについて、3〜4文で引き込まれる導入を書く]

1. 性格・行動の傾向
[画像の具体的な要素や色使いを根拠にして詳しく深く考察する（読み応えのあるボリュームで記述）]

2. コミュニケーションと人間関係
[人間関係での立ち位置や距離感などを詳しく解説する（読み応えのあるボリュームで記述）]

3. あなたへのアドバイス・キーワード
・アドバイス: [魅力をさらに高めるための深いアドバイス]
・キーフレーズ: 「[ユーザーの本質を表す素敵なフレーズ]」

--------------------------------------------------
🔮 本日のワンポイント開運鑑定（本命星: {wuxing_info['honmei_sei']} / 五行: {wuxing_info['user_wuxing']}）
[誕生日({valid_date})の九星「{wuxing_info['honmei_sei']}」と本日の気質から、本日の吉方位（例: 南東等）と今日を最高にする開運アドバイスを記述]
"""
                            client = genai.Client(api_key=active_key)
                            
                            img_byte_arr = io.BytesIO()
                            img_format = image.format if image.format and image.format.upper() in ["PNG", "JPEG", "JPG"] else "JPEG"
                            image.save(img_byte_arr, format=img_format)
                            img_bytes = img_byte_arr.getvalue()
                            mime_type = f"image/{img_format.lower()}"
                            if mime_type == "image/jpg": mime_type = "image/jpeg"

                            response = client.models.generate_content(
                                model=GEMINI_MODEL_NAME,
                                contents=[
                                    prompt,
                                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
                                ]
                            )

                            result_text = response.text
                            st.session_state.result_text = result_text

                            type_match = re.search(r'■ 診断結果：【(.*?)】', result_text)
                            type_name = type_match.group(1) if type_match else "神秘の探求者タイプ"
                            tags_match = re.search(r'■ 3つのハッシュタグ:\s*(.*)', result_text)
                            tags = [t.strip() for t in tags_match.group(1).split(',')] if tags_match else ["#隠れ情熱派", "#独自の世界観", "#観察眼"]
                            params = {"洞察力": 80, "直感力": 75, "社交性": 60, "独自性": 85, "柔軟性": 70}
                            param_match = re.search(r'■ パラメータ:\s*(.*)', result_text)
                            if param_match:
                                for item in param_match.group(1).split(','):
                                    if ':' in item:
                                        k, v = item.split(':')
                                        v_num = re.sub(r'\D', '', v)
                                        if k.strip() in params and v_num: params[k.strip()] = min(100, max(30, int(v_num)))
                            
                            st.session_state.radar_params = params
                            phrase_match = re.search(r'キーフレーズ: 「(.*?)」', result_text)
                            key_phrase = phrase_match.group(1) if phrase_match else "秘めたる才能が開花する刻"

                            summary_text, comm_text, advice_text = "", "", ""
                            lines = result_text.split('\n')
                            for i, line in enumerate(lines):
                                if "1. 性格・行動の傾向" in line: summary_text = " ".join([l.strip() for l in lines[i+1:i+6] if l.strip() and not l.startswith("2.")]).strip()
                                if "2. コミュニケーションと人間関係" in line: comm_text = " ".join([l.strip() for l in lines[i+1:i+6] if l.strip() and not l.startswith("3.")]).strip()
                                if "・アドバイス:" in line: advice_text = line.replace("・アドバイス:", "").strip()

                            if not summary_text: summary_text = "独自の感性と鋭い直感を持つ個性派。"
                            if not comm_text: comm_text = "周囲を魅了する独特の雰囲気を備えています。"
                            if not advice_text: advice_text = "自分の直感を信じて一歩踏み出すことで、新たな運気が開けます。"

                            text_blocks = {
                                "summary_card": summary_text[:180] + "..." if len(summary_text) > 180 else summary_text,
                                "comm_card": comm_text[:180] + "..." if len(comm_text) > 180 else comm_text,
                                "advice_card": advice_text[:140] + "..." if len(advice_text) > 140 else advice_text,
                                "phrase": key_phrase
                            }

                            st.session_state.card_images = generate_carousel_images(
                                image, type_name, wuxing_info['user_wuxing'], tags, params, text_blocks, st.session_state.diagnosis_style
                            )
                    status_holder.empty()
                except Exception as e:
                    st.error(f"鑑定中にエラーが発生しました: {e}")

        # 診断結果描画
        if st.session_state.result_text and st.session_state.card_images:
            st.success("✨ 鑑定画像が完成しました！※インスタ投稿サイズ ✨")
            cols = st.columns(2)
            for i, img in enumerate(st.session_state.card_images):
                cols[i % 2].image(img, caption=f"【{i+1}枚目】", use_container_width=True)
                
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for i, img in enumerate(st.session_state.card_images):
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='PNG')
                    z.writestr(f"manga_slide_{i+1}.png", img_byte_arr.getvalue())
            
            st.download_button(label="📦 4枚の画像をまとめて保存する（ZIP）", data=buf.getvalue(), file_name="diagnosis_4slides.zip", mime="application/zip", use_container_width=True)
            
            # Instagram投稿用テキストエリア
            st.markdown("### 📲 Instagram投稿用キャプション")
            st.caption("以下のテキストをコピーして、InstagramやSNSの投稿にそのままお使いいただけます！")
            
            type_match = re.search(r'■ 診断結果：【(.*?)】', st.session_state.result_text)
            t_name = type_match.group(1) if type_match else "神秘の探求者タイプ"
            tags_match = re.search(r'■ 3つのハッシュタグ:\s*(.*)', st.session_state.result_text)
            t_tags = [t.strip() for t in tags_match.group(1).split(',')] if tags_match else ["#アイコン診断", "#AI鑑定"]
            
            insta_caption = generate_insta_caption(t_name, t_tags, st.session_state.diagnosis_style)
            st.code(insta_caption, language=None)

            st.markdown("---")

            # 潜在能力レーダーチャート
            if st.session_state.radar_params:
                st.markdown("### 📊 潜在能力レーダーチャート")
                render_plotly_radar(st.session_state.radar_params)

            lines = st.session_state.result_text.split("\n")
            formatted_html_body = ""
            for line in lines:
                line_str = line.strip()
                clean_line = re.sub(r'\*+', '', line_str).strip()
                clean_line = format_wuxing_color(clean_line)
                if clean_line.startswith("■ 診断結果："): formatted_html_body += f"<div style='color:#FFD700; font-size:1.30rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.6rem; border-bottom:1px solid #FFD700; padding-bottom:0.3rem;'>{clean_line}</div>"
                elif clean_line.startswith("■ 3つのハッシュタグ:"): formatted_html_body += f"<div style='color:#FFE066; font-size:1.05rem; font-weight:bold; margin-bottom:0.6rem;'>{clean_line}</div>"
                elif clean_line.startswith("■ パラメータ:"): continue
                elif clean_line.startswith("1. "): formatted_html_body += f"<div style='color:#4EAEFF; font-size:1.12rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.4rem;'>{clean_line}</div>"
                elif clean_line.startswith("2. "): formatted_html_body += f"<div style='color:#40E0D0; font-size:1.12rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.4rem;'>{clean_line}</div>"
                elif clean_line.startswith("3. "): formatted_html_body += f"<div style='color:#FF8C00; font-size:1.12rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.4rem;'>{clean_line}</div>"
                elif clean_line.startswith("🔮 本日のワンポイント開運鑑定"): formatted_html_body += f"<div style='color:#E0B0FF; font-size:1.2rem; font-weight:bold; margin-top:1.4rem; margin-bottom:0.6rem; border-bottom:1px solid #E0B0FF; padding-bottom:0.3rem;'>{clean_line}</div>"
                elif clean_line.startswith("・"): formatted_html_body += f"<div style='color:#FFF3C4; font-size:0.98rem; line-height:1.6; margin-bottom:0.3rem; padding-left:0.5rem;'>{clean_line}</div>"
                elif clean_line == "": formatted_html_body += "<div style='height:0.5rem;'></div>"
                else: formatted_html_body += f"<div style='color:#FFFFFF; font-size:0.98rem; line-height:1.7; margin-bottom:0.4rem;'>{clean_line}</div>"

            card_html = f"""
            <div class="notranslate" style="background: rgba(10, 15, 25, 0.75); backdrop-filter: blur(8px); border: 1.5px solid rgba(212, 175, 55, 0.8); border-radius: 14px; padding: 1.5rem; margin-top: 1.2rem; margin-bottom: 2.0rem;">
                <h3 style="color:#FFE066; text-align:center; margin-top:0; font-size: 1.2rem;">📖 鑑定結果の詳細</h3>
                {formatted_html_body}
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown('<div class="omikuji-heading">⛩️ 今日の運試し ⛩️</div>', unsafe_allow_html=True)
            st.markdown('<p class="center-msg">鑑定結果をご覧いただいたあなたへ。本日の「開運おみくじ」を引いてみませんか！</p>', unsafe_allow_html=True)
            
            if st.button("☯️ おみくじを引く！ ☯️", type="primary", use_container_width=True, key="omikuji_btn_diag"):
                active_key = get_api_key()
                if not active_key:
                    st.error(".env ファイルに GEMINI_API_KEY を設定するか、API Key を確認してください。")
                else:
                    fortune_list = ["超大吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶"]
                    selected_fortune = random.choice(fortune_list)
                    st.session_state.omikuji_result_type = selected_fortune
                    
                    status_holder_diag = st.empty()
                    with status_holder_diag.container():
                        render_video("cat_video4.mp4")
                        with st.spinner("黒猫がみくじ筒をシャカシャカ振り振り、おみくじデータを錬成中..."):
                            try:
                                omikuji_prompt = f"""
あなたは黒猫の陰陽師です。本格的で読み応えのある神社のおみくじの文章を作成してください。
今回の運勢結果は『{selected_fortune}』です。
以下の項目に沿って、少しのユーモアと温かい知性を含め、充実した内容で記述してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【全体運】
（運勢の背景にある深い意味と、心構えを2〜3文で味わい深く書いてください）
【仕事・学業運】
（具体的なアドバイスや成果を出すためのコツを2文程度で書いてください）
【恋愛・対人運】
（人間関係を良好にするための秘訣を2文程度で書いてください）
【健康運】
（心身を健やかに保つための温かいアドバイスを書いてください）
【旅行・お出かけ運】
（吉となる方角や、お出かけ時の心構えを書いてください）
【ラッキーAIツール】
（例: ChatGPT, Gemini等のなかから1つと、その活用ワンポイント）
【SNS開運アクション】
（今日SNSで運気を上げるための具体的なアクション）
【黒猫陰陽師からの裏ひとこと】
（クスッと笑える親しみやすくユーモアのあるアドバイス）
"""
                                client = genai.Client(api_key=active_key)
                                omikuji_response = client.models.generate_content(
                                    model=GEMINI_MODEL_NAME,
                                    contents=omikuji_prompt
                                )

                                st.session_state.omikuji_text = omikuji_response.text
                                st.session_state.omikuji_card_image = generate_omikuji_card_image(selected_fortune, omikuji_response.text)
                            except Exception as e: 
                                st.error(f"おみくじ中にエラーが発生しました: {e}")
                    status_holder_diag.empty()

        if st.session_state.omikuji_text and st.session_state.omikuji_card_image:
            trigger_omikuji_animation(st.session_state.omikuji_result_type)
                
            st.success(f"⛩️ 今日のおみくじ結果: 【{st.session_state.omikuji_result_type}】 ⛩️ (タップで拡大できます)")
            st.image(st.session_state.omikuji_card_image, use_container_width=True)