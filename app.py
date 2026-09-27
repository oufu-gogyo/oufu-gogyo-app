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

        /* すりガラス（透け感）デザイン */
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

        /* 四柱推命 命式テーブルデザイン */
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

        /* 🧭 九星気学 3x3 方位盤スタイル（添付コード準拠） */
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
# 3. 万年暦・五行・九星・四柱推命計算エンジン
# ==========================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DI_ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

GAN_WU_XING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_WU_XING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

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

# 五行の相性定義（相生関係：添付コードより）
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

# ------------------------------------------
# 🧭 九星気学ロジック（添付コードより移植）
# ------------------------------------------
def get_honmei_sei(birth_date: datetime.date) -> str:
    year = birth_date.year
    if birth_date < datetime.date(year, 2, 4):
        year -= 1
    remainder = (11 - (year % 9)) % 9
    return NINE_STARS[remainder]

def get_day_star(dt: datetime.date) -> str:
    """日付から日盤の盤面中宮（中心）の九星を固定算出"""
    base_date = datetime.date(2024, 1, 1)
    diff = (dt - base_date).days
    remainder = (0 - diff) % 9
    return NINE_STARS[remainder]

def get_day_board(center_star: str) -> dict:
    """中宮の星から8方位の九星を算出"""
    center_idx = NINE_STARS.index(center_star)
    offsets = {"北": 4, "北東": 7, "東": 2, "南東": 3, "南": 8, "南西": 1, "西": 5, "北西": 6}
    board = {}
    for d, off in offsets.items():
        star_idx = (center_idx + off) % 9
        board[d] = NINE_STARS[star_idx]
    return board

def calculate_exact_directions(birth_date: datetime.date, target_date: datetime.date):
    """Python側で九星気学に基づき100%固定で吉方位・凶方位を計算"""
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

# 🧭 九星気学（3×3動的方位盤：添付コードより移植）
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

    if st.button("☯️ 命式を解読して鑑定する ☯️", type="primary", use_container_width=True):
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

        # 📊 四柱推命 4柱フル対応命式チャート表示
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

        # ☯️ 五行バランスレーダーチャート
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

# ------------------------------------------
# 🧭 モード3: 今日の吉方位診断（添付コード完全準拠版）
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
                
                # 💡 Python側で九星気学に基づき100%固定計算（添付コード準拠）
                honmei_sei, exact_good_dirs, exact_bad_dirs = calculate_exact_directions(valid_date, datetime.date.today())
                
                good_str = ", ".join(exact_good_dirs) if exact_good_dirs else "特になし（平穏な1日）"
                bad_str = ", ".join(exact_bad_dirs) if exact_bad_dirs else "特になし"

                status_holder_dir = st.empty()
                with status_holder_dir.container():
                    render_video("cat_video2.mp4")
                    with st.spinner("九星気学の盤面を読み解き、本日の吉方位アドバイスを生成中..."):
                        prompt_dir = f"""
あなたは九星気学に精通した知的な陰陽師です。

ユーザー情報:
- 本命星: 『{honmei_sei}』
- 本日の日付: 『{datetime.date.today()}』
- 確定吉方位: 『{good_str}』
- 確定凶方位: 『{bad_str}』

【絶対指示】
本日の吉方位は「{good_str}」、凶方位は「{bad_str}」で確定しています。この決定された吉方位・凶方位のデータを「変更せず」そのまま用いて解説を作成してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【出力フォーマット】
【最高吉方位解説】
[確定吉方位({good_str})の理由と運気アップのための過ごし方解説]

【項目別アドバイス】
💖 恋愛・対人運: [アドバイス内容]
💼 仕事・学業運: [アドバイス内容]
✈️ 旅行・お出かけ運: [アドバイス内容]
🏠 引っ越し・模様替え運: [アドバイス内容]

【陰陽師からのメッセージ】
[心温まる・知的なひとことメッセージ]
"""
                        client = genai.Client(api_key=active_key)
                        response_dir = client.models.generate_content(
                            model=GEMINI_MODEL_NAME,
                            contents=prompt_dir
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
# ⛩️ モード2: 開運おみくじ
# ------------------------------------------
elif st.session_state.mode == "omikuji_only":
    st.markdown('<div class="omikuji-heading">⛩️ 開運おみくじ ⛩️</div>', unsafe_allow_html=True)
    if st.button("⬅️ 最初に戻る", use_container_width=True): st.session_state.mode = None; st.rerun()
    if st.button("☯️ おみくじを引く ☯️", type="primary", use_container_width=True):
        st.session_state.omikuji_text = "大吉"
        st.success("⛩️ 今日のおみくじ結果: 【大吉】 ⛩️")

# ------------------------------------------
# 🖼️ モード1: アイコン診断
# ------------------------------------------
elif st.session_state.mode == "diagnosis":
    if st.button("⬅️ モード選択に戻る", use_container_width=True): st.session_state.mode = None; st.rerun()
    st.subheader("🗓️ 生年月日＆診断テイストの選択")