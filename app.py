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
if "four_pillars_text" not in st.session_state:
    st.session_state.four_pillars_text = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ENV_GEMINI_API_KEY

def get_api_key():
    return st.session_state.api_key if st.session_state.api_key else ENV_GEMINI_API_KEY

# 🎭 おみくじ演出
def trigger_omikuji_animation(fortune_type):
    if fortune_type in ["超大吉", "大吉"]:
        items = f"['{fortune_type}✨', '{fortune_type}🎉', '✨', '🎊', '🔴大吉🔴']"
        color = "#FF2222"
    elif fortune_type == "凶":
        items = "['凶💧', '☔', '😭', '凶😭']"
        color = "#6688AA"
    else:
        items = f"['{fortune_type}🌸', '✨', '🍀', '🌟']"
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
            background: rgba(10, 12, 24, 0.75) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border-radius: 20px;
            border: 1px solid rgba(255, 215, 0, 0.3);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7);
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
            transition: all 0.3s ease;
        }
        .step-box.active {
            background: linear-gradient(135deg, rgba(255,215,0,0.25), rgba(255,140,0,0.25));
            color: #FFE066;
            border: 1px solid rgba(255, 215, 0, 0.6);
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
        }

        .upload-card-container {
            background: linear-gradient(135deg, rgba(30, 35, 60, 0.85) 0%, rgba(15, 20, 35, 0.9) 100%);
            border: 2px dashed rgba(255, 215, 0, 0.6);
            border-radius: 14px;
            padding: 1.5rem 1rem;
            text-align: center;
            margin-bottom: 1.2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp span {
            color: #FFFFFF !important;
            text-shadow: 0px 2px 6px rgba(0, 0, 0, 0.9);
            font-weight: 600;
        }

        .video-container-34 {
            max-width: 85% !important;
            margin-left: auto !important;
            margin-right: auto !important;
            margin-bottom: 1.2rem !important;
        }

        .glass-card-box {
            background: rgba(20, 26, 40, 0.55) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(255, 215, 0, 0.5) !important;
            padding: 14px 18px !important;
            margin-bottom: 12px !important;
            border-radius: 12px !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.5) !important;
        }

        .meishiki-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: rgba(10, 14, 26, 0.6);
            border: 1.5px solid #FFD700;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.25);
        }
        .meishiki-table th {
            background: rgba(255, 215, 0, 0.25);
            color: #FFE066;
            padding: 8px 4px;
            font-size: 0.80rem;
            border: 1px solid rgba(255, 215, 0, 0.3);
            text-align: center;
        }
        .meishiki-table td {
            padding: 10px 4px;
            color: #FFFFFF;
            font-size: 0.90rem;
            font-weight: bold;
            border: 1px solid rgba(255, 215, 0, 0.2);
            text-align: center;
        }
        .highlight-nikkan {
            color: #FFD700 !important;
            font-size: 1.1rem !important;
            background: rgba(255, 215, 0, 0.2);
        }

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
        
        .wx-wood { color: #55FF55 !important; font-weight: bold; }
        .wx-fire { color: #FF6666 !important; font-weight: bold; }
        .wx-earth { color: #FFDD44 !important; font-weight: bold; }
        .wx-metal { color: #E0E0E0 !important; font-weight: bold; }
        .wx-water { color: #66CCFF !important; font-weight: bold; }

        .center-msg {
            text-align: center !important;
            margin-bottom: 1rem !important;
        }
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
# 3. 万年暦・五行・九星・四柱推命計算エンジン & 画像処理
# ==========================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN_WU_XING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WU_XING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
WU_XING_CLASS = {"木": "wx-wood", "火": "wx-fire", "土": "wx-earth", "金": "wx-metal", "水": "wx-water"}

ZHI_ZOUGAN_HONKI = {
    "子": "癸", "丑": "己", "寅": "甲", "卯": "乙",
    "辰": "戊", "巳": "丙", "午": "丁", "未": "己",
    "申": "庚", "酉": "辛", "戌": "辛", "亥": "壬"
}

NINE_STARS = ["一白水星", "二黒土星", "三碧木星", "四緑木星", "五黄土星", "六白金星", "七赤金星", "八白土星", "九紫火星"]
STAR_ELEMENTS = {
    "一白水星": "水", "二黒土星": "土", "三碧木星": "木", "四緑木星": "木",
    "五黄土星": "土", "六白金星": "金", "七赤金星": "金", "八白土星": "土", "九紫火星": "火"
}

SOSEI_MAP = {
    "木": ["水", "火"],
    "火": ["木", "土"],
    "土": ["火", "金"],
    "金": ["土", "水"],
    "水": ["金", "木"]
}

OPPOSITE_DIR = {
    "北": "南", "南": "北", "東": "西", "西": "東",
    "北東": "南西", "南西": "北東", "南東": "北西", "北西": "南東"
}

TSUHEN_MAP = {
    "甲": {"甲": "比肩", "乙": "劫財", "丙": "食神", "丁": "傷官", "戊": "偏財", "己": "正財", "庚": "偏官", "辛": "正官", "壬": "偏印", "癸": "印綬"},
    "乙": {"甲": "劫財", "乙": "比肩", "丙": "傷官", "丁": "食神", "戊": "正財", "己": "偏財", "庚": "正官", "辛": "偏官", "壬": "印綬", "癸": "偏印"},
    "丙": {"甲": "偏印", "乙": "印綬", "丙": "比肩", "丁": "劫財", "戊": "食神", "己": "傷官", "庚": "偏財", "辛": "正財", "壬": "偏官", "癸": "正官"},
    "丁": {"甲": "印綬", "乙": "偏印", "丙": "劫財", "丁": "比肩", "戊": "傷官", "己": "食神", "庚": "正財", "辛": "偏財", "壬": "正官", "癸": "偏官"},
    "戊": {"甲": "偏官", "乙": "正官", "丙": "偏印", "丁": "印綬", "戊": "比肩", "己": "劫財", "庚": "食神", "辛": "傷官", "壬": "偏財", "癸": "正財"},
    "己": {"甲": "正官", "乙": "偏官", "丙": "印綬", "丁": "偏印", "戊": "劫財", "己": "比肩", "庚": "傷官", "辛": "食神", "壬": "正財", "癸": "偏財"},
    "庚": {"甲": "偏財", "乙": "正財", "丙": "偏官", "丁": "正官", "戊": "偏印", "己": "印綬", "庚": "比肩", "辛": "劫財", "壬": "食神", "癸": "傷官"},
    "辛": {"甲": "正財", "乙": "偏財", "丙": "正官", "丁": "偏官", "戊": "印綬", "己": "偏印", "庚": "劫財", "辛": "比肩", "壬": "傷官", "癸": "食神"},
    "壬": {"甲": "食神", "乙": "傷官", "丙": "偏財", "丁": "正財", "戊": "偏官", "己": "正官", "庚": "偏印", "辛": "印綬", "壬": "比肩", "癸": "劫財"},
    "癸": {"甲": "傷官", "乙": "食神", "丙": "正財", "丁": "偏財", "戊": "正官", "己": "偏官", "庚": "印綬", "辛": "偏印", "壬": "劫財", "癸": "比肩"}
}

COLOR_CSS_MAP = {
    "エメラルドグリーン": "#50C878", "ゴールド": "#FFD700", "金": "#FFD700", "金星": "#FFD700",
    "シルバー": "#C0C0C0", "銀": "#C0C0C0", "レッド": "#FF5555", "赤": "#FF5555",
    "ピンク": "#FF77CB", "桃色": "#FF77CB", "ブルー": "#33AAFF", "青": "#33AAFF",
    "イエロー": "#FFFF55", "黄": "#FFFF55", "グリーン": "#55FF55", "緑": "#55FF55",
    "パープル": "#DD77FF", "紫": "#DD77FF", "オレンジ": "#FF9933", "橙": "#FF9933",
    "ホワイト": "#FFFFFF", "白": "#FFFFFF", "ブラック": "#CCCCCC", "黒": "#CCCCCC"
}

def colorize_lucky_colors(text: str) -> str:
    for color_name, hex_code in COLOR_CSS_MAP.items():
        if color_name in text:
            pattern = re.compile(rf"({color_name})")
            replacement = rf"<span style='color:{hex_code}; font-weight:800; text-shadow:0 0 12px {hex_code};'>\1</span>"
            text = pattern.sub(replacement, text)
    return text

def format_wuxing_color(text: str) -> str:
    for wx, cls_name in WU_XING_CLASS.items():
        text = text.replace(f"「{wx}」", f"「<span class='{cls_name}'>{wx}</span>」")
        text = text.replace(f"五行タイプ: {wx}", f"五行タイプ: <span class='{cls_name}'>{wx}</span>")
    return text

def get_day_gan(dt: datetime.date) -> str:
    base_date = datetime.date(1900, 1, 1)
    return TIAN_GAN[(dt - base_date).days % 10]

def calculate_guxing_info(birth_date: datetime.date, target_date: datetime.date):
    user_gan = get_day_gan(birth_date)
    today_gan = get_day_gan(target_date)
    return {"user_gan": user_gan, "user_wuxing": GAN_WU_XING[user_gan], "today_gan": today_gan, "today_wuxing": GAN_WU_XING[today_gan]}

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

def generate_carousel_images(user_icon_img, type_name, wuxing_type, tags, params, text_blocks):
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
    draw1.text((540, 810), "★ SSR ★", font=ssr_font, fill=(255, 235, 120), anchor="mm")
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
    draw4.text((100, 120), "🔮 開運アドバイス", font=heading_font, fill=(224, 176, 255))
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

# ── 四柱推命計算関数 ──
HOUR_ZHI_MAP = [
    (23, 1, "子"), (1, 3, "丑"), (3, 5, "寅"), (5, 7, "卯"),
    (7, 9, "辰"), (9, 11, "巳"), (11, 13, "午"), (13, 15, "未"),
    (15, 17, "申"), (17, 19, "酉"), (19, 21, "戌"), (21, 23, "亥")
]

def get_hour_zhi(hour_val):
    if hour_val is None: return None
    for start, end, zhi in HOUR_ZHI_MAP:
        if start == 23:
            if hour_val >= 23 or hour_val < 1: return zhi
        elif start <= hour_val < end:
            return zhi
    return "子"

def calculate_four_pillars(dt: datetime.date, hour_val=None):
    base_date = datetime.date(1900, 1, 1)
    diff = (dt - base_date).days
    
    day_gan_idx = (0 + diff) % 10
    day_zhi_idx = (10 + diff) % 12
    day_gan = TIAN_GAN[day_gan_idx]
    day_zhi = DI_ZHI[day_zhi_idx]
    
    year = dt.year
    if dt < datetime.date(year, 2, 4):
        year -= 1
    year_gan_idx = (year - 4) % 10
    year_zhi_idx = (year - 4) % 12
    year_gan = TIAN_GAN[year_gan_idx]
    year_zhi = DI_ZHI[year_zhi_idx]
    
    month = dt.month
    if dt.day < 5: month -= 1
    if month < 1: month = 12
    month_zhi_idx = (month + 1) % 12
    month_gan_idx = (year_gan_idx * 2 + month) % 10
    month_gan = TIAN_GAN[month_gan_idx]
    month_zhi = DI_ZHI[month_zhi_idx]
    
    hour_gan, hour_zhi, tsuhen_hour = "不明", "不明", "不明"
    if hour_val is not None:
        hour_zhi = get_hour_zhi(hour_val)
        hour_zhi_idx = DI_ZHI.index(hour_zhi)
        hour_gan_start = (day_gan_idx % 5) * 2
        hour_gan_idx = (hour_gan_start + hour_zhi_idx) % 10
        hour_gan = TIAN_GAN[hour_gan_idx]
        tsuhen_hour = TSUHEN_MAP[day_gan][hour_gan]
    
    tsuhen_year = TSUHEN_MAP[day_gan][year_gan]
    tsuhen_month = TSUHEN_MAP[day_gan][month_gan]
    
    month_zougan_honki = ZHI_ZOUGAN_HONKI[month_zhi]
    main_kaku = TSUHEN_MAP[day_gan][month_zougan_honki]

    wuxing_counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    wuxing_counts[GAN_WU_XING[year_gan]] += 1
    wuxing_counts[GAN_WU_XING[month_gan]] += 1
    wuxing_counts[GAN_WU_XING[day_gan]] += 1
    wuxing_counts[ZHI_WU_XING[year_zhi]] += 1
    wuxing_counts[ZHI_WU_XING[month_zhi]] += 1
    wuxing_counts[ZHI_WU_XING[day_zhi]] += 1

    if hour_gan != "不明":
        wuxing_counts[GAN_WU_XING[hour_gan]] += 1
        wuxing_counts[ZHI_WU_XING[hour_zhi]] += 1
    
    return {
        "nikkan": day_gan,
        "nikkan_element": GAN_WU_XING[day_gan],
        "year_kanto": f"{year_gan}{year_zhi}",
        "month_kanto": f"{month_gan}{month_zhi}",
        "day_kanto": f"{day_gan}{day_zhi}",
        "hour_kanto": f"{hour_gan}{hour_zhi}" if hour_gan != "不明" else "不明",
        "year_tsuhen": tsuhen_year,
        "month_tsuhen": tsuhen_month,
        "hour_tsuhen": tsuhen_hour,
        "main_kaku": main_kaku,
        "wuxing_counts": wuxing_counts
    }

# ── 九星気学計算関数 ──
def get_honmei_sei(birth_date: datetime.date) -> str:
    year = birth_date.year
    if birth_date < datetime.date(year, 2, 4):
        year -= 1
    remainder = (11 - (year % 9)) % 9
    return NINE_STARS[remainder]

def get_day_star(dt: datetime.date) -> str:
    base_date = datetime.date(2024, 1, 1)
    diff = (dt - base_date).days
    remainder = (0 - diff) % 9
    return NINE_STARS[remainder]

def get_day_board(center_star: str) -> dict:
    center_idx = NINE_STARS.index(center_star)
    offsets = {"北": 4, "北東": 7, "東": 2, "南東": 3, "南": 8, "南西": 1, "西": 5, "北西": 6}
    board = {}
    for d, off in offsets.items():
        star_idx = (center_idx + off) % 9
        board[d] = NINE_STARS[star_idx]
    return board

def calculate_exact_directions(birth_date: datetime.date, target_date: datetime.date):
    honmei_sei = get_honmei_sei(birth_date)
    user_element = STAR_ELEMENTS[honmei_sei]
    
    day_center = get_day_star(target_date)
    board = get_day_board(day_center)
    
    good_dirs = []
    bad_dirs = []
    
    goou_dir = None
    for d, s in board.items():
        if s == "五黄土星":
            goou_dir = d
            break
            
    anken_dir = OPPOSITE_DIR.get(goou_dir) if goou_dir else None
    
    honmei_dir = None
    for d, s in board.items():
        if s == honmei_sei:
            honmei_dir = d
            break
            
    teki_dir = OPPOSITE_DIR.get(honmei_dir) if honmei_dir else None

    for d, star in board.items():
        if d in [goou_dir, anken_dir, honmei_dir, teki_dir]:
            bad_dirs.append(d)
            continue
            
        star_elem = STAR_ELEMENTS[star]
        if star_elem == user_element or star_elem in SOSEI_MAP[user_element]:
            good_dirs.append(d)
        else:
            bad_dirs.append(d)
            
    return honmei_sei, good_dirs, bad_dirs

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

def render_wuxing_radar(wuxing_counts, nikkan_elem):
    elements_order = ["木", "火", "土", "金", "水"]
    tsuhen_label_map = {
        0: "自星 [比肩/劫財]",
        1: "食傷 [食神/傷官]",
        2: "財星 [偏財/正財]",
        3: "官星 [偏官/正官]",
        4: "印星 [偏印/印綬]"
    }

    nikkan_idx = elements_order.index(nikkan_elem)
    rotated_elements = [elements_order[(nikkan_idx + i) % 5] for i in range(5)]
    
    categories = []
    values = []
    for i, elem in enumerate(rotated_elements):
        role_text = tsuhen_label_map[i]
        label = f"{elem} ({elem_to_romaji(elem)})<br><b>{role_text}</b>"
        categories.append(label)
        values.append(wuxing_counts.get(elem, 0))

    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(255, 215, 0, 0.40)',
        line=dict(color='#FFD700', width=3),
        marker=dict(size=8, color='#FFE066')
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(max(values), 4) + 1], dtick=1, gridcolor="rgba(255, 255, 255, 0.2)", tickfont=dict(color="#FFE066")),
            angularaxis=dict(gridcolor="rgba(255, 255, 255, 0.2)", tickfont=dict(color="#FFFFFF", size=12), direction="clockwise"),
            bgcolor="rgba(15, 20, 35, 0.65)"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        height=400,
        margin=dict(l=50, r=50, t=40, b=40)
    )
    st.plotly_chart(fig, use_container_width=True)

def elem_to_romaji(elem):
    return {"木": "MOKU", "火": "KA", "土": "DO", "金": "GON", "水": "SUI"}.get(elem, "")

# ==========================================
# 4. モード選択 & メインコンテンツ
# ==========================================
if st.session_state.mode is None:
    st.markdown('<div class="choice-title">✨ どの鑑定にするニャ？ ✨</div>', unsafe_allow_html=True)
    render_video("cat_video.mp4")

    col_1, col_2 = st.columns(2)
    with col_1:
        if st.button("🖼️ SNSアイコン診断", type="secondary", use_container_width=True):
            st.session_state.mode = "diagnosis"
            st.session_state.step = 0; st.rerun()
    with col_2:
        if st.button("📜 四柱推命・本命命式鑑定", type="secondary", use_container_width=True):
            st.session_state.mode = "four_pillars"
            st.rerun()

    col_3, col_4 = st.columns(2)
    with col_3:
        if st.button("⛩️ 開運おみくじ", type="secondary", use_container_width=True):
            st.session_state.mode = "omikuji_only"; st.rerun()
    with col_4:
        if st.button("🧭 今日の吉方位診断", type="secondary", use_container_width=True):
            st.session_state.mode = "direction_only"; st.rerun()

# ------------------------------------------
# 🖼 モード1: アイコン診断
# ------------------------------------------
elif st.session_state.mode == "diagnosis":
    if st.button("⬅️ モード選択に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.step = 0
        st.session_state.result_text = None
        st.session_state.card_images = None
        st.session_state.omikuji_text = None
        st.session_state.omikuji_card_image = None
        st.rerun()

    step_labels = ["1. 生年月日", "2. アイコン選択", "3. 鑑定実行"]
    step_html = "<div class='step-container'>"
    for i, lbl in enumerate(step_labels):
        active_cls = " active" if i == st.session_state.step else ""
        step_html += f"<div class='step-box{active_cls}'>{lbl}</div>"
    step_html += "</div>"
    st.markdown(step_html, unsafe_allow_html=True)

    # STEP 0: 生年月日の入力
    if st.session_state.step == 0:
        st.subheader("🗓️ 生年月日の入力")
        b_input = st.text_input("生年月日を8桁の数字で入力してください（例: 19900101）", value="19900101" if st.session_state.birth_date_str == "19700101" else st.session_state.birth_date_str, max_chars=8)
        st.session_state.birth_date_str = b_input
        st.write("")
        if st.button("次へ進む ➔（アイコン選択へ）", type="primary", use_container_width=True):
            if len(b_input) == 8 and b_input.isdigit():
                st.session_state.step = 1
                st.rerun()
            else:
                st.error("生年月日は8桁の数字で入力してください。")

    # STEP 1: アイコン選択
    elif st.session_state.step == 1:
        st.subheader("🖼️ SNSアイコンのアップロード")
        st.markdown("""
        <div class="upload-card-container">
            <h3 style="color: #FFE066; margin-top: 0; font-size: 1.1rem;">✨ SNSアイコンを👇にUPしてください ✨</h3>
            <p style="color: #CCCCCC; font-size: 0.85rem; margin-bottom: 0.5rem;">陰陽心理鑑定で、アイコンの特徴と魅力を解説します！</p>
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

    # STEP 2: 鑑定実行 & 結果表示
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
                    st.session_state.omikuji_text = None
                    st.session_state.omikuji_result_type = None
                    st.session_state.omikuji_card_image = None
                    st.session_state.card_images = None

                    status_holder = st.empty()
                    with status_holder.container():
                        render_video("cat_video3.mp4")

                        with st.spinner("深層心理を解析し、鑑定結果を錬成中..."):
                            prompt = f"""
あなたは人間観察に長けた、非常に知的な陰陽心理鑑定士です。
提供された「SNSアイコン画像」の細かい視覚的特徴（被写体、服装、背景、構図、色合い、ギャップなど）を巧みに分析し、ユーザーのパーソナリティを読み解いてください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

以下のフォーマットを「必ず」厳守して出力してください。

--------------------------------------------------
■ 診断結果：【[キャッチーな〇〇タイプ名]】
■ 3つのハッシュタグ: #[タグ1], #[タグ2], #[タグ3]
■ パラメータ: 洞察力:[40-100], 直感力:[40-100], 社交性:[40-100], 独自性:[40-100], 柔軟性:[40-100]

[アイコン全体の印象やセルフプロデュース力、視覚的ギャップについて、3〜4文で引き込まれる導入を書く]

1. 性格・行動の傾向
[画像の具体的な要素を根拠にして詳しく深く考察する（読み応えのあるボリュームで記述）]

2. コミュニケーションと人間関係
[人間関係での立ち位置や距離感などを詳しく解説する（読み応えのあるボリュームで記述）]

3. あなたへのアドバイス・キーワード
・アドバイス: [魅力をさらに高めるための深いアドバイス]
・キーフレーズ: 「[ユーザーの本質を表す素敵なフレーズ]」

--------------------------------------------------
🔮 本日のワンポイント開運鑑定（五行タイプ: {wuxing_info['user_wuxing']}）
[誕生日({valid_date})の五行気質「{wuxing_info['user_wuxing']}」と本日の気質「{wuxing_info['today_wuxing']}」を掛け合わせ、今日を最高の1日にするためのアドバイスを伝えてください]
"""
                            client = genai.Client(api_key=active_key)
                            
                            img_byte_arr = io.BytesIO()
                            img_format = image.format if image.format and image.format.upper() in ["PNG", "JPEG", "JPG"] else "JPEG"
                            image.save(img_byte_arr, format=img_format)
                            img_bytes = img_byte_arr.getvalue()
                            mime_type = f"image/{img_format.lower()}"
                            if mime_type == "image/jpg":
                                mime_type = "image/jpeg"

                            response = client.models.generate_content(
                                model=GEMINI_MODEL_NAME,
                                contents=[
                                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                                    prompt
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
                            phrase_match = re.search(r'キーフレーズ: 「(.*?)」', result_text)
                            key_phrase = phrase_match.group(1) if phrase_match else "秘めたる才能が開花する刻"

                            summary_text, comm_text, advice_text = "", "", ""
                            lines = result_text.split('\n')
                            for i, line in enumerate(lines):
                                if "1. 性格・行動の傾向" in line: summary_text = " ".join([l.strip() for l in lines[i+1:i+6] if l.strip() and not l.startswith("2.")]).strip()
                                if "2. コミュニケーションと人間関係" in line: comm_text = " ".join([l.strip() for l in lines[i+1:i+6] if l.strip() and not l.startswith("3.")]).strip()
                                if "・アドバイス:" in line: advice_text = line.replace("・アドバイス:", "").strip()

                            if not summary_text: 
                                summary_text = random.choice([
                                    "独自の感性と鋭い直感を持つ個性派。",
                                    "内に秘めた情熱と冷静な判断力を併せ持つタイプ。",
                                    "周囲を惹きつけるミステリアスな魅力の持ち主。"
                                ])
                            if not comm_text: 
                                comm_text = random.choice([
                                    "周囲を魅了する独特の雰囲気を備えています。",
                                    "適度な距離感を保ちながら、深い信頼関係を築きます。"
                                ])
                            if not advice_text: 
                                advice_text = random.choice([
                                    "自分の直感を信じて一歩踏み出すことで、新たな運気が開けます。",
                                    "肩の力を抜いてリラックスする時間を作ることで、さらなるひらめきが訪れます。"
                                ])

                            text_blocks = {
                                "summary_card": summary_text[:180] + "..." if len(summary_text) > 180 else summary_text,
                                "comm_card": comm_text[:180] + "..." if len(comm_text) > 180 else comm_text,
                                "advice_card": advice_text[:140] + "..." if len(advice_text) > 140 else advice_text,
                                "phrase": key_phrase
                            }

                            st.session_state.card_images = generate_carousel_images(image, type_name, wuxing_info['user_wuxing'], tags, params, text_blocks)
                    status_holder.empty()
                except Exception as e:
                    st.error(f"鑑定中にエラーが発生しました: {e}")

        # 診断結果カード描画
        if st.session_state.result_text and st.session_state.card_images:
            st.success("✨ 鑑定画像が完成しました！※インスタ用サイズ ✨")
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
            st.markdown("---")

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
                                trigger_omikuji_animation(selected_fortune)
                            except Exception as e: 
                                st.error(f"おみくじ中にエラーが発生しました: {e}")
                    status_holder_diag.empty()

        if st.session_state.omikuji_text and st.session_state.omikuji_card_image:
            st.success("⛩️ 今日のおみくじ結果がでました ⛩️️ (タップで拡大できます)")
            st.image(st.session_state.omikuji_card_image, use_container_width=True)

# ------------------------------------------
# ⛩️ モード2: 開運おみくじ
# ------------------------------------------
elif st.session_state.mode == "omikuji_only":
    st.markdown('<div class="omikuji-heading">⛩️ 開運おみくじ ⛩️</div>', unsafe_allow_html=True)
    if st.button("⬅️ 最初に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.omikuji_text = None
        st.session_state.omikuji_card_image = None
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
（運勢の背景にある深い意味と, 心構えを2〜3文で味わい深く書いてください）
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
                        trigger_omikuji_animation(selected_fortune)
                    except Exception as e:
                        st.error(f"おみくじ生成中にエラーが発生しました: {e}")
            status_holder.empty()

    if st.session_state.omikuji_text and st.session_state.omikuji_card_image:
        st.success("⛩️ 今日のおみくじ結果がでました ⛩️ (タップで拡大できます)")
        st.image(st.session_state.omikuji_card_image, use_container_width=True)

# ------------------------------------------
# 🧭 モード3: 今日の吉方位診断（★アドバイスレパートリー50倍強化版★）
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
                honmei_sei, exact_good_dirs, exact_bad_dirs = calculate_exact_directions(valid_date, datetime.date.today())
                
                good_str = ", ".join(exact_good_dirs) if exact_good_dirs else "特になし（平穏な1日）"
                bad_str = ", ".join(exact_bad_dirs) if exact_bad_dirs else "特になし"

                status_holder_dir = st.empty()
                with status_holder_dir.container():
                    render_video("cat_video2.mp4")
                    with st.spinner("九星気学の盤面を読み解き、本日の吉方位アドバイスを生成中..."):
                        # ★ レパートリーを50倍に拡張するプロンプト設計 ★
                        prompt_dir = f"""
あなたは九星気学と陰陽五行説を極めた、非常に知的な陰陽師です。
ありきたりで抽象的なアドバイスは避け、ユーザーが「なるほど！今日やってみよう」と思える超具体的で新鮮な開運アドバイスを生成してください。

ユーザー情報:
- 本命星: 『{honmei_sei}』
- 本日の日付: 『{datetime.date.today()}』
- 確定吉方位: 『{good_str}』
- 確定凶方位: 『{bad_str}』

【絶対指示】
本日の吉方位は「{good_str}」、凶方位は「{bad_str}」で確定しています。この決定された吉方位・凶方位のデータを「変更せず」そのまま用いて解説を作成してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【アドバイスの多角化・バリエーション拡張ガイドライン】
吉方位「{good_str}」と本命星「{honmei_sei}」の組み合わせから、以下の【多様なテーマ】の中から本日に最もふさわしい要素をいくつかピックアップし、ランダムかつ具体的にアドバイスに組み込んでください。
（テーマ例：
・時間帯別のおすすめ行動（朝の換気、午後のカフェタイム、夜の習慣など）
・開運フード・ドリンク（味覚、温冷、素材、カフェメニューなど）
・ラッキーアイテム・ fashion（身につける色、持ち物、小物など）
・空間・生活環境（部屋の片づけ場所、吉方位に向いたデスク配置など）
・人間関係・デジタル開運（SNSでの発言、連絡するタイミング、距離感など）
）

【出力フォーマット】
【最高吉方位解説】
[確定吉方位({good_str})のエネルギー解説と、本日吉方位のパワーを最大限に吸収するための具体的でユニークな行動（2〜3文）]

【項目別アドバイス】
💖 恋愛・対人運: [人間関係の距離感やコミュニケーションの切り口、開運アドバイス]
💼 仕事・学業運: [集中力・決断力を高める具体的行動や吉方位デスク活用・デジタル開運法]
✈️ 旅行・お出かけ運: [吉方位への移動、ラッキーフード・ラッキースポット、移動中の過ごし方]
🏠 暮らし・開運アクション: [身につけるカラー・アイテム、部屋での過ごし方や開運習慣]

【陰陽師からのメッセージ】
[知性と温かみがあり、ハッとさせられるような特別なメッセージ]
"""
                        client = genai.Client(api_key=active_key)
                        
                        # 生成の多様性を高める設定（temperature: 1.0）
                        response_dir = client.models.generate_content(
                            model=GEMINI_MODEL_NAME,
                            contents=prompt_dir,
                            config=types.GenerateContentConfig(
                                temperature=1.0
                            )
                        )
                        st.session_state.direction_result_text = response_dir.text
                        st.session_state.exact_good_dirs = exact_good_dirs
                        st.session_state.exact_bad_dirs = exact_bad_dirs
                        st.session_state.honmei_sei = honmei_sei
                status_holder_dir.empty()
            except Exception as e:
                st.error(f"吉方位鑑定中にエラーが発生しました: {e}")

    if st.session_state.direction_result_text:
        honmei_sei = st.session_state.get("honmei_sei", "一白水星")
        good_dirs = st.session_state.get("exact_good_dirs", [])
        bad_dirs = st.session_state.get("exact_bad_dirs", [])
        
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
        
        raw_text = st.session_state.direction_result_text
        lines = [re.sub(r'\*+', '', l).strip() for l in raw_text.split('\n') if l.strip()]

        for line in lines:
            line_colored = colorize_lucky_colors(line)
            if any(line.startswith(prefix) for prefix in ["💖", "💼", "✈️", "🏠"]):
                parts = line_colored.split(":", 1)
                title = parts[0]
                body = parts[1] if len(parts) > 1 else ""
                st.markdown(f"""
                <div class="glass-card-box">
                    <div style="color:#FFE066; font-size:1.05rem; font-weight:bold; margin-bottom:6px;">{title}</div>
                    <div style="color:#FFFFFF; font-size:0.98rem; line-height:1.7; font-weight:600;">{body}</div>
                </div>
                """, unsafe_allow_html=True)
            elif not line.startswith("【"):
                st.markdown(f"""
                <div class="glass-card-box">
                    <div style="color:#FFFFFF; font-size:0.98rem; line-height:1.7; font-weight:600;">{line_colored}</div>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------
# 📜 モード4: 四柱推命・本命命式鑑定
# ------------------------------------------
elif st.session_state.mode == "four_pillars":
    st.markdown('<div class="omikuji-heading">📜 四柱推命・本命命式＆開運鑑定 📜</div>', unsafe_allow_html=True)
    if st.button("⬅️ 最初に戻る", use_container_width=True):
        st.session_state.mode = None
        st.session_state.four_pillars_text = None
        st.rerun()

    st.markdown('<p class="center-msg">生年月日・時間・性別を入力すると、あなたの命式（年柱・月柱・日柱・時柱）と五行バランス、本日の開運運勢を詳細鑑定します！</p>', unsafe_allow_html=True)
    
    b_input_fp = st.text_input("生年月日を8桁の数字で入力（例: 19900101）", value=st.session_state.birth_date_str, max_chars=8, key="b_fp_input")
    st.session_state.birth_date_str = b_input_fp

    col_fp1, col_fp2 = st.columns(2)
    with col_fp1:
        gender = st.radio("性別", ["女性", "男性"], horizontal=True, key="gender_input")
    with col_fp2:
        hours_options = ["不明"] + [f"{h:02d}:00頃" for h in range(24)]
        selected_hour_str = st.selectbox("生まれた時間（分かる場合）", hours_options, key="hour_input")

    hour_val = None
    if selected_hour_str != "不明":
        hour_val = int(selected_hour_str.split(":")[0])

    if st.button("☯️️ 命式を解読して鑑定する ☯️", type="primary", use_container_width=True):
        active_key = get_api_key()
        if not active_key:
            st.error(".env ファイルに GEMINI_API_KEY を設定するか、API Key を確認してください。")
        elif len(b_input_fp) != 8 or not b_input_fp.isdigit():
            st.error("生年月日は8桁の数字で入力してください。")
        else:
            try:
                valid_date = datetime.date(int(b_input_fp[:4]), int(b_input_fp[4:6]), int(b_input_fp[6:8]))
                
                fp_data = calculate_four_pillars(valid_date, hour_val)
                today_fp = calculate_four_pillars(datetime.date.today())

                status_holder_fp = st.empty()
                with status_holder_fp.container():
                    render_video("cat_video2.mp4")
                    with st.spinner("四柱推命の盤面と時柱・五行バランスを解析中..."):
                        prompt_fp = f"""
あなたは四柱推命の真髄を極めた知的な陰陽師です。

ユーザー命式データ:
- 性別: 『{gender}』
- 日干（本質）: 『{fp_data['nikkan']}（五行: {fp_data['nikkan_element']}）』
- メイン格（通変星中心）: 『{fp_data['main_kaku']}格』
- 五行バランス（要素数）: {fp_data['wuxing_counts']}
- 年柱干支: 『{fp_data['year_kanto']}』（通変星: {fp_data['year_tsuhen']}）
- 月柱干支: 『{fp_data['month_kanto']}』（通変星: {fp_data['month_tsuhen']}）
- 日柱干支: 『{fp_data['day_kanto']}』
- 時柱干支: 『{fp_data['hour_kanto']}』（通変星: {fp_data['hour_tsuhen']}）
- 本日の日干支: 『{today_fp['day_kanto']}』

【厳格出力ルール】
※マークダウンの太字（**）は使用禁止。
性別（{gender}）およびメイン属性「{fp_data['main_kaku']}格」を含めた高精度な命式データから、四柱推命の観点で深く知性あふれる本日のアドバイスを作成してください。

【本日の全体運＆開運ポイント】
[日干「{fp_data['nikkan']}」および「{fp_data['main_kaku']}格」の本質から見る、本日絶好調な点と注意すべきポイント（2-3文）]

【項目別詳細運勢】
💖 恋愛・対人運: [{gender}の視点も含めた対人アドバイス]
💼 仕事・学業運: [アドバイス内容]
✈️ 旅行・お出かけ運: [アドバイス内容]

【本日の開運キーアイテム】
・ラッキーカラー：エメラルドグリーン、ゴールド
・開運アクション：[幸運を引き寄せる具体的な行動]
"""
                        client = genai.Client(api_key=active_key)
                        response_fp = client.models.generate_content(
                            model=GEMINI_MODEL_NAME,
                            contents=prompt_fp
                        )
                        st.session_state.four_pillars_text = response_fp.text
                        st.session_state.fp_data = fp_data
                        st.session_state.gender = gender
                status_holder_fp.empty()
            except Exception as e:
                st.error(f"四柱推命鑑定中にエラーが発生しました: {e}")

    if st.session_state.four_pillars_text and "fp_data" in st.session_state:
        fp = st.session_state.fp_data
        user_gender = st.session_state.get("gender", "女性")

        st.markdown(f"""
        <div class="notranslate" style="background: rgba(10, 14, 26, 0.65); backdrop-filter: blur(10px); border: 1.5px solid rgba(255, 215, 0, 0.8); border-radius: 14px; padding: 1.2rem; margin-top: 1.2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.5);">
            <h3 style="color:#FFE066; text-align:center; margin-top:0; font-size: 1.25rem; text-shadow:0 2px 4px #000;">📜 あなたの四柱推命 精密命式チャート 📜</h3>
            <div style="text-align:center; color:#CCCCCC; font-size:0.85rem; margin-bottom:8px;">性別: {user_gender}</div>
            <table class="meishiki-table">
                <tr>
                    <th>項目</th>
                    <th>年柱（祖先・幼少）</th>
                    <th>月柱（社会・青年）</th>
                    <th>日柱（自分・本質）</th>
                    <th>時柱（晩年・子孫）</th>
                </tr>
                <tr>
                    <td style="color:#FFE066;">天干地支</td>
                    <td>{fp['year_kanto']}</td>
                    <td>{fp['month_kanto']}</td>
                    <td class="highlight-nikkan">{fp['day_kanto']}</td>
                    <td>{fp['hour_kanto']}</td>
                </tr>
                <tr>
                    <td style="color:#FFE066;">通変星</td>
                    <td>{fp['year_tsuhen']}</td>
                    <td style="color:#FFD700; background:rgba(255,215,0,0.25);">{fp['month_tsuhen']}</td>
                    <td style="color:#4EAEFF;">日干（主星）</td>
                    <td>{fp['hour_tsuhen']}</td>
                </tr>
            </table>
            <div style="text-align:center; color:#E0B0FF; font-size:0.95rem; font-weight:bold;">
                ✨ あなたの主格: <span style="font-size:1.2rem; color:#FFD700;">【{fp['main_kaku']}格】</span> / 日干: <span style="font-size:1.2rem; color:#FFD700;">【{fp['nikkan']}】</span>（五行: {fp['nikkan_element']}）
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h4 style='color:#FFE066; text-align:center; margin-top:1.5rem; margin-bottom:0.2rem; text-shadow:0 2px 4px #000;'>☯️ 五行エネルギーバランス ☯️</h4>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center; color:#E0E0E0; font-size:0.85rem; margin-bottom:0;'>※あなたの魂のシンボル（日干: <b>{fp['nikkan_element']}</b>）を頂点（真上）に配置しています</p>", unsafe_allow_html=True)
        render_wuxing_radar(fp['wuxing_counts'], fp['nikkan_element'])

        st.markdown("<h4 style='color:#FFE066; margin-top:1.2rem; margin-bottom:0.8rem; text-shadow:0 2px 4px #000;'>【本日の四柱推命 開運鑑定】</h4>", unsafe_allow_html=True)
        
        lines = [re.sub(r'\*+', '', l).strip() for l in st.session_state.four_pillars_text.split('\n') if l.strip()]
        for line in lines:
            line_colored = colorize_lucky_colors(line)
            
            if any(line.startswith(prefix) for prefix in ["💖", "💼", "✈️"]):
                parts = line_colored.split(":", 1)
                st.markdown(f"""
                <div class="glass-card-box">
                    <div style="color:#FFE066; font-size:1.05rem; font-weight:bold; margin-bottom:6px;">{parts[0]}</div>
                    <div style="color:#FFFFFF; font-size:0.98rem; line-height:1.7; font-weight:600;">{parts[1] if len(parts)>1 else ""}</div>
                </div>
                """, unsafe_allow_html=True)
            elif not line.startswith("【"):
                st.markdown(f"""
                <div class="glass-card-box">
                    <div style="color:#FFFFFF; font-size:0.98rem; line-height:1.7; font-weight:600;">{line_colored}</div>
                </div>
                """, unsafe_allow_html=True)