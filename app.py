import os
import base64
import random
import datetime
import re
import io
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st
from google import genai

# ==========================================
# 1. ページ基本設定 & Session State
# ==========================================
st.set_page_config(page_title="SNSアイコン個性診断＆開運鑑定", page_icon="☯️", layout="centered")

if "step" not in st.session_state:
    st.session_state.step = 0
if "birth_date_str" not in st.session_state:
    st.session_state.birth_date_str = "19700101"
if "result_text" not in st.session_state:
    st.session_state.result_text = None
if "card_image" not in st.session_state:
    st.session_state.card_image = None
if "omikuji_text" not in st.session_state:
    st.session_state.omikuji_text = None
if "omikuji_result_type" not in st.session_state:
    st.session_state.omikuji_result_type = None
if "omikuji_card_image" not in st.session_state:
    st.session_state.omikuji_card_image = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

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
    
    target_path = None
    for p in possible_paths:
        if os.path.exists(p):
            target_path = p
            break

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
        @import url('https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@600;800&display=swap');

        .stApp {
            background-image: url('__IMAGE_DATA__');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
        }

        .title-container {
            text-align: center;
            margin-bottom: 0.8rem;
        }

        .main-title-text {
            font-family: 'Shippori Mincho', 'Sawarabi Mincho', serif !important;
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            letter-spacing: 0.1em;
            color: #FFE066 !important;
            text-shadow: 0px 0px 10px rgba(255, 224, 102, 0.8), 0px 3px 6px #000000 !important;
            vertical-align: middle;
        }

        .title-icon {
            font-size: 2.0rem;
            vertical-align: middle;
            margin: 0 8px;
            filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.8));
        }

        .main .block-container {
            background-color: rgba(0, 0, 0, 0.40) !important;
            backdrop-filter: blur(6px) !important;
            -webkit-backdrop-filter: blur(6px) !important;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 2.5rem 2rem;
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
        .stApp p, .stApp label, .stApp span, .stMarkdown, .stMarkdown p {
            color: #FFFFFF !important;
            text-shadow: 0px 2px 6px rgba(0, 0, 0, 0.95), 0px 0px 4px #000000 !important;
            font-weight: 700 !important;
        }

        div[data-testid="stTextInput"] > div,
        div[data-testid="stTextInput"] div[data-baseweb="base-input"],
        div[data-testid="stTextInput"] div[data-baseweb="input"],
        div[data-testid="stTextInput"] input {
            background: rgba(10, 10, 20, 0.65) !important;
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            border: 1.5px solid rgba(255, 215, 0, 0.6) !important;
            border-radius: 10px !important;
        }

        .upload-card-container {
            background: linear-gradient(135deg, rgba(30, 35, 60, 0.85) 0%, rgba(15, 20, 35, 0.9) 100%);
            border: 2px dashed rgba(255, 215, 0, 0.7);
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            margin-bottom: 1.5rem;
        }

        div[data-testid="stFileUploader"] section {
            background: rgba(10, 10, 20, 0.5) !important;
            border: 1px dashed rgba(255, 215, 0, 0.5) !important;
            border-radius: 12px !important;
        }

        button[data-testid="stBaseButton-primary"],
        button[kind="primary"] {
            background: linear-gradient(135deg, #FF4500 0%, #C8102E 50%, #8B0000 100%) !important;
            border: 2px solid #FF7F50 !important;
            border-radius: 12px !important;
            box-shadow: 0px 4px 15px rgba(200, 16, 46, 0.6), 0px 2px 4px rgba(0, 0, 0, 0.8) !important;
        }

        button[data-testid="stBaseButton-primary"] p,
        button[kind="primary"] p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            letter-spacing: 0.05em !important;
        }

        .step-bar {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1.5rem;
            background: rgba(20, 25, 45, 0.6);
            border-radius: 10px;
            padding: 8px 12px;
            border: 1px solid rgba(255, 215, 0, 0.4);
        }
        .step-item {
            color: #888888;
            font-size: 0.9rem;
            font-weight: bold;
        }
        .step-item.active {
            color: #FFD700;
            border-bottom: 2px solid #FFD700;
        }

        .wx-wood { color: #55FF55 !important; font-weight: bold; }
        .wx-fire { color: #FF6666 !important; font-weight: bold; }
        .wx-earth { color: #FFDD44 !important; font-weight: bold; }
        .wx-metal { color: #E0E0E0 !important; font-weight: bold; }
        .wx-water { color: #66CCFF !important; font-weight: bold; }
        </style>
    """
    css_code = css_template.replace('__IMAGE_DATA__', img_base64)
    st.markdown(css_code, unsafe_allow_html=True)

st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

st.markdown("""
<div class="title-container notranslate">
    <span class="title-icon">☯️</span>
    <span class="main-title-text">アイコン個性診断＆開運鑑定</span>
    <span class="title-icon">☯️</span>
</div>
""", unsafe_allow_html=True)

st.caption("あなたのアイコンから『個性と深層心理』を読み解き、今日の運勢と開運アドバイスをお届けします。")
st.markdown("---")

# ==========================================
# 3. 万年暦・五行計算 & フォント・描画ヘルパー
# ==========================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
GAN_WU_XING = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水"
}

WU_XING_CLASS = {
    "木": "wx-wood", "火": "wx-fire", "土": "wx-earth", "金": "wx-metal", "水": "wx-water"
}

def get_day_gan(dt: datetime.date) -> str:
    base_date = datetime.date(1900, 1, 1)
    diff_days = (dt - base_date).days
    return TIAN_GAN[diff_days % 10]

def calculate_guxing_info(birth_date: datetime.date, target_date: datetime.date):
    user_gan = get_day_gan(birth_date)
    today_gan = get_day_gan(target_date)
    return {
        "user_gan": user_gan,
        "user_wuxing": GAN_WU_XING[user_gan],
        "today_gan": today_gan,
        "today_wuxing": GAN_WU_XING[today_gan],
    }

def format_wuxing_color(text: str) -> str:
    for wx, cls_name in WU_XING_CLASS.items():
        text = text.replace(f"「{wx}」", f"「<span class='{cls_name}'>{wx}</span>」")
        text = text.replace(f"五行タイプ: {wx}", f"五行タイプ: <span class='{cls_name}'>{wx}</span>")
    return text

def get_readable_font(size):
    font_candidates = [
        "C:\\Windows\\Fonts\\meiryob.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def wrap_text(text, font, max_width):
    lines = []
    current_line = ""
    for char in text:
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        if bbox[2] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines

# 高精度レーダーチャート描画
def draw_radar_chart(draw, center_x, center_y, radius, params, font):
    labels = ["洞察力", "直感力", "社交性", "独自性", "柔軟性"]
    num_vars = len(labels)
    angle_step = 2 * math.pi / num_vars
    start_angle = -math.pi / 2

    for r_ratio in [0.33, 0.66, 1.0]:
        r = radius * r_ratio
        grid_points = []
        for i in range(num_vars):
            angle = start_angle + i * angle_step
            gx = center_x + r * math.cos(angle)
            gy = center_y + r * math.sin(angle)
            grid_points.append((gx, gy))
        draw.polygon(grid_points, outline=(80, 100, 150), width=1)

    for i in range(num_vars):
        angle = start_angle + i * angle_step
        ax = center_x + radius * math.cos(angle)
        ay = center_y + radius * math.sin(angle)
        draw.line([(center_x, center_y), (ax, ay)], fill=(80, 100, 150), width=1)

        lx = center_x + (radius + 28) * math.cos(angle)
        ly = center_y + (radius + 18) * math.sin(angle)
        draw.text((lx, ly), f"{labels[i]}", font=font, fill=(220, 230, 255), anchor="mm")

    data_points = []
    for i, label in enumerate(labels):
        val = params.get(label, 70) / 100.0
        angle = start_angle + i * angle_step
        px = center_x + (radius * val) * math.cos(angle)
        py = center_y + (radius * val) * math.sin(angle)
        data_points.append((px, py))

    draw.polygon(data_points, outline=(255, 215, 0), width=3)
    for pt in data_points:
        draw.ellipse([pt[0]-4, pt[1]-4, pt[0]+4, pt[1]+4], fill=(255, 224, 102))

# 1枚の完璧な1:1正方形カードに情報をスッキリまとめるジェネレーター
def generate_card_image(user_icon_img, type_name, wuxing_type, tags, params, summary_text, advice_text, key_phrase):
    card_w, card_h = 1080, 1080  # Instagramに最適な1:1正方形
    card = Image.new("RGBA", (card_w, card_h), (12, 16, 28, 255))
    draw = ImageDraw.Draw(card)

    for y in range(card_h):
        alpha_val = int(15 + 10 * math.sin(y / 50.0))
        draw.line([(0, y), (card_w, y)], fill=(30, 35, 60, alpha_val))

    # 豪華な金枠とコーナー装飾
    draw.rectangle([15, 15, card_w - 15, card_h - 15], outline=(212, 175, 55), width=5)
    draw.rectangle([25, 25, card_w - 25, card_h - 25], outline=(255, 224, 102), width=2)
    
    corner_len = 35
    for cx, cy in [(25, 25), (card_w-25, 25), (25, card_h-25), (card_w-25, card_h-25)]:
        dx = 1 if cx == 25 else -1
        dy = 1 if cy == 25 else -1
        draw.line([(cx, cy), (cx + corner_len * dx, cy)], fill=(255, 235, 120), width=4)
        draw.line([(cx, cy), (cx, cy + corner_len * dy)], fill=(255, 235, 120), width=4)

    # 上部タイトル
    title_font = get_readable_font(28)
    draw.text((card_w // 2, 45), "― 陰陽心理鑑定カード ―", font=title_font, fill=(255, 224, 102), anchor="mm")

    # アイコン配置（左上）
    icon_size = 180
    user_icon_resized = user_icon_img.convert("RGBA").resize((icon_size, icon_size))
    mask = Image.new("L", (icon_size, icon_size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, icon_size, icon_size), fill=255)
    
    icon_x, icon_y = 55, 80
    card.paste(user_icon_resized, (icon_x, icon_y), mask)
    draw.ellipse([icon_x - 3, icon_y - 3, icon_x + icon_size + 3, icon_y + icon_size + 3], outline=(255, 215, 0), width=3)

    # タイプ名 & SSRバッジ & 五行属性
    type_font = get_readable_font(32)
    ssr_font = get_readable_font(18)
    badge_font = get_readable_font(20)
    tag_font = get_readable_font(18)

    draw.text((255, 85), f"【{type_name}】", font=type_font, fill=(255, 215, 0))
    
    draw.rectangle([255, 130, 350, 160], fill=(255, 140, 0), outline=(255, 224, 102), width=2)
    draw.text((302, 145), "★ SSR ★", font=ssr_font, fill=(255, 255, 255), anchor="mm")

    draw.rectangle([365, 130, 535, 160], fill=(40, 50, 80), outline=(212, 175, 55), width=2)
    draw.text((450, 145), f"五行属性: {wuxing_type}", font=badge_font, fill=(255, 255, 255), anchor="mm")

    # ハッシュタグ
    tag_x = 255
    tag_y = 175
    for tag in tags[:3]:
        tag_str = f"#{tag.strip('#')}"
        t_bbox = tag_font.getbbox(tag_str)
        t_w = t_bbox[2] - t_bbox[0] + 16
        if tag_x + t_w > card_w - 50:
            break
        draw.rectangle([tag_x, tag_y, tag_x + t_w, tag_y + 26], fill=(50, 40, 70), outline=(255, 224, 102), width=1)
        draw.text((tag_x + t_w//2, tag_y + 13), tag_str, font=tag_font, fill=(255, 224, 102), anchor="mm")
        tag_x += t_w + 10

    # 右上にレーダーチャート
    chart_label_font = get_readable_font(16)
    draw_radar_chart(draw, center_x=910, center_y=135, radius=75, params=params, font=chart_label_font)

    # 鑑定文章コンテナ（中央エリア）
    box_top, box_bottom = 225, 960
    draw.rectangle([45, box_top, card_w - 45, box_bottom], fill=(18, 22, 38), outline=(120, 140, 200), width=2)

    body_font = get_readable_font(21)
    heading_font = get_readable_font(22)
    
    full_body_text = f"【基本性格】\n{summary_text}\n\n【開運アドバイス】\n{advice_text}"
    
    y_offset = box_top + 20
    for block in full_body_text.split('\n'):
        if y_offset > box_bottom - 30:
            break
        if block.startswith("【"):
            draw.text((65, y_offset), block, font=heading_font, fill=(255, 224, 102))
            y_offset += 30
        elif block.strip():
            lines = wrap_text(block, body_font, 930)
            for l in lines:
                if y_offset > box_bottom - 25:
                    break
                draw.text((65, y_offset), l, font=body_font, fill=(240, 240, 250))
                y_offset += 26
            y_offset += 8

    # 最下部：キーフレーズ
    phrase_font = get_readable_font(24)
    if key_phrase:
        wrapped_phrase = wrap_text(f"「{key_phrase}」", phrase_font, 950)
        draw.text((card_w // 2, 1005), wrapped_phrase[0], font=phrase_font, fill=(255, 224, 102), anchor="mm")

    return card

# おみくじカード生成
def generate_omikuji_card_image(fortune_type, omikuji_raw_text):
    card_w, card_h = 1080, 1440
    card = Image.new("RGBA", (card_w, card_h), (25, 18, 30, 255))
    draw = ImageDraw.Draw(card)

    title_font = get_readable_font(38)
    fortune_font = get_readable_font(76)
    heading_font = get_readable_font(28)
    body_font = get_readable_font(23)
    footer_font = get_readable_font(22)

    draw.rectangle([20, 20, card_w - 20, card_h - 20], outline=(212, 175, 55), width=6)
    draw.rectangle([30, 30, card_w - 30, card_h - 30], outline=(255, 224, 102), width=2)
    draw.text((card_w // 2, 70), "― 陰陽開運おみくじ ―", font=title_font, fill=(255, 224, 102), anchor="mm")

    fortune_color = (255, 224, 102)
    if fortune_type in ["超大吉", "大吉"]:
        fortune_color = (255, 90, 90)
    elif fortune_type == "凶":
        fortune_color = (180, 200, 210)

    draw.rectangle([card_w // 2 - 200, 110, card_w // 2 + 200, 215], fill=(40, 25, 45), outline=fortune_color, width=4)
    draw.text((card_w // 2, 162), fortune_type, font=fortune_font, fill=fortune_color, anchor="mm")

    box_top, box_bottom = 245, 1350
    draw.rectangle([50, box_top, card_w - 50, box_bottom], fill=(18, 12, 24), outline=(100, 80, 120), width=2)

    lines = omikuji_raw_text.split('\n')
    y_offset = box_top + 25

    for line in lines:
        if y_offset > box_bottom - 35:
            break
        clean_line = re.sub(r'\*+', '', line).strip()
        if not clean_line or clean_line.startswith("---"):
            continue

        if "【" in clean_line and "】" in clean_line:
            h_color = (255, 220, 100)
            draw.text((70, y_offset), clean_line, font=heading_font, fill=h_color)
            y_offset += 38
        else:
            wrapped = wrap_text(clean_line, body_font, 920)
            for w in wrapped:
                if y_offset > box_bottom - 32:
                    break
                draw.text((70, y_offset), w, font=body_font, fill=(240, 240, 250))
                y_offset += 34
            y_offset += 6

    draw.text((card_w // 2, 1395), "--- 陰陽SNSアイコン診断 & 開運おみくじ ---", font=footer_font, fill=(160, 170, 190), anchor="mm")
    return card

# ==========================================
# 4. サイドバー
# ==========================================
with st.sidebar:
    st.header("⚙️ 設定")
    st.session_state.api_key = st.text_input("Gemini API Key を入力", value=st.session_state.api_key, type="password")
    st.markdown("[Gemini API Keyの取得はこちら](https://aistudio.google.com/app/apikey)")

# ==========================================
# 5. ステップ表示＆画面切り替え処理
# ==========================================
step_labels = ["1. 生年月日", "2. アイコン選択", "3. 鑑定実行"]
step_html = "<div class='step-bar'>"
for i, lbl in enumerate(step_labels):
    active_class = " active" if i == st.session_state.step else ""
    step_html += f"<div class='step-item{active_class}'>{lbl}</div>"
step_html += "</div>"
st.markdown(step_html, unsafe_allow_html=True)

# ------------------------------------------
# STEP 0: 生年月日の入力
# ------------------------------------------
if st.session_state.step == 0:
    st.subheader("🗓️ 生年月日の入力")
    b_input = st.text_input(
        "生年月日を8桁の数字で入力してください（例: 19700101）",
        value=st.session_state.birth_date_str,
        max_chars=8
    )
    st.session_state.birth_date_str = b_input

    st.write("")
    if st.button("次へ進む ➔（アイコン選択へ）", type="primary", use_container_width=True):
        if len(b_input) == 8 and b_input.isdigit():
            st.session_state.step = 1
            st.rerun()
        else:
            st.error("生年月日は8桁の数字で入力してください。")

# ------------------------------------------
# STEP 1: アイコン選択
# ------------------------------------------
elif st.session_state.step == 1:
    st.subheader("🖼️ SNSアイコンのアップロード")
    
    st.markdown("""
    <div class="upload-card-container">
        <h3 style="color: #FFE066; margin-top: 0;">✨ あなたのSNSアイコンを選択してください ✨</h3>
        <p style="color: #CCCCCC; font-size: 0.95rem; margin-bottom: 1rem;">高精度の陰陽心理鑑定で、あなたの魅力をトレーディングカード化します！</p>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader("アイコン画像（PNG、JPG）", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
    
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            image = Image.open(uploaded_file)
            st.image(image, caption="📷 選択されたアイコンプレビュー", use_container_width=True)

    st.write("")
    col_prev, col_next = st.columns(2)
    with col_prev:
        if st.button("⬅️ 前へ戻る", use_container_width=True):
            st.session_state.step = 0
            st.rerun()
    with col_next:
        if st.button("次へ進む ➔（鑑定実行へ）", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("サイドバーに Gemini API Key を入力してください。")
            elif "uploaded_file" in st.session_state and st.session_state.uploaded_file is not None:
                st.session_state.step = 2
                st.rerun()
            else:
                st.warning("アイコン画像をアップロードしてください。")

# ------------------------------------------
# STEP 2: 鑑定実行 & 結果表示
# ------------------------------------------
elif st.session_state.step == 2:
    st.subheader("🔮 鑑定の準備が整えました")
    
    col_prev, col_start = st.columns([1, 2])
    with col_prev:
        if st.button("⬅️ 前へ戻る", use_container_width=True):
            st.session_state.step = 1
            st.rerun()
    with col_start:
        start_button = st.button("☯️ 鑑定を開始する ☯️", type="primary", use_container_width=True)

    if start_button:
        birth_str = st.session_state.birth_date_str
        valid_date = None
        try:
            year = int(birth_str[:4])
            month = int(birth_str[4:6])
            day = int(birth_str[6:8])
            valid_date = datetime.date(year, month, day)
        except Exception:
            valid_date = None

        if not st.session_state.api_key:
            st.error("サイドバーで Gemini API Key を入力してください。")
        elif valid_date is None:
            st.error("生年月日のフォーマットが正しくありません。ステップ1に戻って再入力してください。")
        elif "uploaded_file" not in st.session_state or st.session_state.uploaded_file is None:
            st.warning("アイコン画像がありません。ステップ2に戻ってアップロードしてください。")
        else:
            try:
                uploaded_file = st.session_state.uploaded_file
                image = Image.open(uploaded_file)
                wuxing_info = calculate_guxing_info(valid_date, datetime.date.today())
                
                st.session_state.omikuji_text = None
                st.session_state.omikuji_result_type = None
                st.session_state.omikuji_card_image = None

                status_holder = st.empty()
                
                with status_holder.container():
                    shrine_img_path = "shrine.jpg"
                    if os.path.exists(shrine_img_path):
                        st.image(shrine_img_path, use_container_width=True)
                    with st.spinner("深層心理を解析し、最高級トレーディングカードを錬成中..."):
                        prompt = f"""
あなたは人間観察に長けた、非常に知的な陰陽心理鑑定士です。
提供された「SNSアイコン画像」の細かい視覚的特徴（被写体、服装、背景、構図、色合い、ギャップなど）を巧みに分析し、ユーザーのパーソナリティを読み解いてください。

※文章中で太字（**）などのマークダウン装飾記号は使わないでください。

以下のフォーマットを「必ず」厳守して出力してください。

--------------------------------------------------
■ 診断結果：【[キャッチーな〇〇タイプ名]】
■ 3つのハッシュタグ: #[タグ1], #[タグ2], #[タグ3]
■ パラメータ: 洞察力:[40-100], 直感力:[40-100], 社交性:[40-100], 独自性:[40-100], 柔軟性:[40-100]

[アイコン全体の印象やセルフプロデュース力、視覚的ギャップについて、2〜3文で引き込まれる導入を書く]

1. 性格・行動の傾向
[画像の具体的な要素を根拠にして詳しく考察する解説文を120文字程度で]

2. あなたへのアドバイス・キーワード
・アドバイス: [魅力をさらに高めるためのアドバイスを100文字程度で]
・キーフレーズ: 「[ユーザーの本質を表す素敵なフレーズ]」

--------------------------------------------------
🔮 本日のワンポイント開運鑑定（五行タイプ: {wuxing_info['user_wuxing']}）
[誕生日({valid_date})の五行気質「{wuxing_info['user_wuxing']}」と本日の気質「{wuxing_info['today_wuxing']}」を掛け合わせ、今日を最高の1日にするためのアドバイスを簡潔に伝えてください]
"""

                        client = genai.Client(api_key=st.session_state.api_key)
                        response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[image, prompt]
                        )

                        result_text = response.text
                        st.session_state.result_text = result_text

                        type_match = re.search(r'■ 診断結果：【(.*?)】', result_text)
                        type_name = type_match.group(1) if type_match else "神秘の探求者タイプ"

                        tags_match = re.search(r'■ 3つのハッシュタグ:\s*(.*)', result_text)
                        if tags_match:
                            tags = [t.strip() for t in tags_match.group(1).split(',')]
                        else:
                            tags = ["#隠れ情熱派", "#独自の世界観", "#観察眼"]

                        params = {"洞察力": 80, "直感力": 75, "社交性": 60, "独自性": 85, "柔軟性": 70}
                        param_match = re.search(r'■ パラメータ:\s*(.*)', result_text)
                        if param_match:
                            p_str = param_match.group(1)
                            for item in p_str.split(','):
                                if ':' in item:
                                    k, v = item.split(':')
                                    k = k.strip()
                                    v_num = re.sub(r'\D', '', v)
                                    if k in params and v_num:
                                        params[k] = min(100, max(30, int(v_num)))

                        phrase_match = re.search(r'キーフレーズ: 「(.*?)」', result_text)
                        key_phrase = phrase_match.group(1) if phrase_match else "秘めたる才能が開花する刻"

                        summary_text, advice_text = "", ""
                        lines = result_text.split('\n')
                        for i, line in enumerate(lines):
                            if "1. 性格・行動の傾向" in line:
                                summary_text = " ".join([l.strip() for l in lines[i+1:i+4] if l.strip() and not l.startswith("2.")]).strip()
                            if "・アドバイス:" in line:
                                advice_text = line.replace("・アドバイス:", "").strip()

                        if not summary_text:
                            summary_text = "独自の感性と鋭い直感を持つ個性派。周囲を魅了する独特の雰囲気を備えています。"
                        if not advice_text:
                            advice_text = "自分の直感を信じて一歩踏み出すことで、新たな運気が開けます。"

                        card_img = generate_card_image(
                            user_icon_img=image,
                            type_name=type_name,
                            wuxing_type=wuxing_info['user_wuxing'],
                            tags=tags,
                            params=params,
                            summary_text=summary_text,
                            advice_text=advice_text,
                            key_phrase=key_phrase
                        )
                        st.session_state.card_image = card_img

                status_holder.empty()

            except Exception as e:
                st.error(f"鑑定中にエラーが発生しました: {e}")

    # 鑑定結果表示
    if st.session_state.result_text and st.session_state.card_image:
        st.success("✨ 1枚完結型の鑑定トレーディングカードが完成しました！ ✨")

        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.image(st.session_state.card_image, caption="📷 長押し または 下のボタンで保存してSNSに投稿できます！", use_container_width=True)
            
            buf = io.BytesIO()
            st.session_state.card_image.save(buf, format="PNG")
            byte_im = buf.getvalue()

            st.download_button(
                label="🎴 鑑定カード（画像）を保存する",
                data=byte_im,
                file_name="gogyo_icon_card.png",
                mime="image/png",
                use_container_width=True
            )

        st.markdown("---")

        lines = st.session_state.result_text.split("\n")
        formatted_html_body = ""
        for line in lines:
            line_str = line.strip()
            clean_line = re.sub(r'\*+', '', line_str).strip()
            clean_line = format_wuxing_color(clean_line)
            
            if clean_line.startswith("■ 診断結果："):
                formatted_html_body += f"<div style='color:#FFD700; font-size:1.35rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.6rem; border-bottom:1px solid #FFD700; padding-bottom:0.3rem;'>{clean_line}</div>"
            elif clean_line.startswith("■ 3つのハッシュタグ:"):
                formatted_html_body += f"<div style='color:#FFE066; font-size:1.1rem; font-weight:bold; margin-bottom:0.6rem;'>{clean_line}</div>"
            elif clean_line.startswith("■ パラメータ:"):
                continue
            elif clean_line.startswith("1. "):
                formatted_html_body += f"<div style='color:#4EAEFF; font-size:1.18rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.4rem;'>{clean_line}</div>"
            elif clean_line.startswith("2. "):
                formatted_html_body += f"<div style='color:#FF8C00; font-size:1.18rem; font-weight:bold; margin-top:1.2rem; margin-bottom:0.4rem;'>{clean_line}</div>"
            elif clean_line.startswith("🔮 本日のワンポイント開運鑑定"):
                formatted_html_body += f"<div style='color:#E0B0FF; font-size:1.3rem; font-weight:bold; margin-top:1.4rem; margin-bottom:0.6rem; border-bottom:1px solid #E0B0FF; padding-bottom:0.3rem;'>{clean_line}</div>"
            elif clean_line.startswith("・"):
                formatted_html_body += f"<div style='color:#FFF3C4; font-size:1.02rem; line-height:1.7; margin-bottom:0.3rem; padding-left:0.5rem;'>{clean_line}</div>"
            elif clean_line == "":
                formatted_html_body += "<div style='height:0.6rem;'></div>"
            else:
                formatted_html_body += f"<div style='color:#FFFFFF; font-size:1.02rem; line-height:1.8; margin-bottom:0.4rem;'>{clean_line}</div>"

        card_html = f"""
        <div class="notranslate" style="
            background: rgba(10, 15, 25, 0.75);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1.5px solid rgba(212, 175, 55, 0.8);
            border-radius: 14px;
            padding: 1.8rem;
            margin-top: 1.2rem;
            margin-bottom: 2.0rem;
        ">
            <h3 style="color:#FFE066; text-align:center; margin-top:0;">📖 鑑定詳細結果</h3>
            {formatted_html_body}
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # ------------------------------------------
        # 開運おみくじ
        # ------------------------------------------
        st.markdown("---")
        st.subheader("⛩️ 今日の運試し ⛩️")
        st.write("鑑定結果をご覧いただいたあなたへ。本日の「開運おみくじ」を引いてみませんか？")

        if st.button("☯️ 開運おみくじを引く！ ☯️", type="primary", use_container_width=True):
            if not st.session_state.api_key:
                st.error("サイドバーで Gemini API Key を入力してください。")
            else:
                fortune_list = ["超大吉", "大吉", "中吉", "小吉", "吉", "末吉", "凶"]
                selected_fortune = random.choice(fortune_list)
                st.session_state.omikuji_result_type = selected_fortune

                with st.spinner("みくじ筒をシャカシャカ振り、おみくじトレカを錬成中..."):
                    try:
                        omikuji_prompt = f"""
アントは黒猫の陰陽師です。神社のおみくじの文章を作成してください。
今回の運勢結果は『{selected_fortune}』です。

以下の項目に沿って、少しのユーモアと温かい知性を含めたおみくじ文を作成してください。
※文章中で太字（**）などのマークダウン装飾記号は絶対に使わないでください。

【全体運】: 簡潔で心に刺さる和風の一言メッセージ
【仕事・学業運】: 短いアドバイス
【恋愛・対人運】: 短いアドバイス
【健康運】: 短いアドバイス
【旅行・お出かけ運】: 短いアドバイス
【ラッキーAIツール】: （例: ChatGPT, Gemini等から1つとお勧め理由）
【SNS開運アクション】: （例: ポジティブなコメントをする等）
【黒猫陰陽師からの裏ひとこと】: （クスッと笑える親しみやすいアドバイス）

全体のトーンは親しみやすく、かつ陰陽師らしい神秘的な文体で書いてください。
"""
                        client = genai.Client(api_key=st.session_state.api_key)
                        omikuji_response = client.models.generate_content(
                            model='gemini-3.6-flash',
                            contents=[omikuji_prompt]
                        )
                        omikuji_text = omikuji_response.text
                        st.session_state.omikuji_text = omikuji_text

                        omikuji_card_img = generate_omikuji_card_image(
                            fortune_type=selected_fortune,
                            omikuji_raw_text=omikuji_text
                        )
                        st.session_state.omikuji_card_image = omikuji_card_img

                    except Exception as e:
                        st.error(f"おみくじ生成中にエラーが発生しました: {e}")

        if st.session_state.omikuji_text and st.session_state.omikuji_card_image:
            st.success("⛩️ おみくじトレーディングカードが完成しました！ ⛩️")