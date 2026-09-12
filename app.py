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
if "card_images" not in st.session_state:
    st.session_state.card_images = None
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

# ==========================================
# 2. 背景画像（bg.jpg）＆デザイン設定
# ==========================================
def get_image_base64(image_filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [os.path.join(current_dir, image_filename), image_filename, os.path.join(".", image_filename)]
    target_path = next((p for p in possible_paths if os.path.exists(p)), None)
    if not target_path:
        return None
    with open(target_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    return f"data:image/jpeg;base64,{encoded}"

img_base64 = get_image_base64("bg.jpg")
if img_base64:
    css_code = f"""
        <style>
        .stApp {{ background-image: url('{img_base64}'); background-size: cover; background-attachment: fixed; }}
        .main .block-container {{ background-color: rgba(0, 0, 0, 0.40) !important; backdrop-filter: blur(6px) !important; border-radius: 16px; padding: 2.5rem 2rem; }}
        h1, h2, h3, p, label, span {{ color: #FFFFFF !important; text-shadow: 0px 2px 6px rgba(0, 0, 0, 0.9) !important; }}
        .step-bar {{ display: flex; justify-content: space-between; margin-bottom: 1.5rem; background: rgba(20, 25, 45, 0.6); padding: 8px 12px; border-radius: 10px; border: 1px solid rgba(255, 215, 0, 0.4); }}
        .step-item {{ color: #888888; font-size: 0.9rem; font-weight: bold; }}
        .step-item.active {{ color: #FFD700; border-bottom: 2px solid #FFD700; }}
        </style>
    """
    st.markdown(css_code, unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #FFE066;'>☯️ アイコン個性診断＆開運鑑定 ☯️</h2>", unsafe_allow_html=True)
st.markdown("---")

# ==========================================
# 3. 五行計算 & 描画ヘルパー
# ==========================================
TIAN_GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
GAN_WU_XING = {"甲":"木","乙":"木","丙":"火","丁":"火","戊":"土","己":"土","庚":"金","辛":"金","壬":"水","癸":"水"}

def get_day_gan(dt: datetime.date) -> str:
    return TIAN_GAN[(dt - datetime.date(1900, 1, 1)).days % 10]

def get_readable_font(size):
    font_candidates = [
        "C:\\Windows\\Fonts\\meiryob.ttc",
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc"
    ]
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except: continue
    return ImageFont.load_default()

def wrap_text(text, font, max_width):
    lines, current_line = [], ""
    for char in text:
        if font.getbbox(current_line + char)[2] <= max_width:
            current_line += char
        else:
            lines.append(current_line)
            current_line = char
    if current_line: lines.append(current_line)
    return lines

def create_base_card():
    card = Image.new("RGBA", (1080, 1080), (12, 16, 28, 255))
    draw = ImageDraw.Draw(card)
    draw.rectangle([20, 20, 1060, 1060], outline=(212, 175, 55), width=6)
    draw.rectangle([35, 35, 1045, 1045], outline=(255, 224, 102), width=2)
    return card, draw

def draw_radar_chart(draw, center_x, center_y, radius, params, font):
    labels = ["洞察力", "直感力", "社交性", "独自性", "柔軟性"]
    angle_step = 2 * math.pi / len(labels)
    start_angle = -math.pi / 2

    for r_ratio in [0.33, 0.66, 1.0]:
        r = radius * r_ratio
        pts = [(center_x + r * math.cos(start_angle + i * angle_step), center_y + r * math.sin(start_angle + i * angle_step)) for i in range(5)]
        draw.polygon(pts, outline=(80, 100, 150), width=2)

    data_points = []
    for i, label in enumerate(labels):
        angle = start_angle + i * angle_step
        ax, ay = center_x + radius * math.cos(angle), center_y + radius * math.sin(angle)
        draw.line([(center_x, center_y), (ax, ay)], fill=(80, 100, 150), width=2)
        lx, ly = center_x + (radius + 40) * math.cos(angle), center_y + (radius + 30) * math.sin(angle)
        draw.text((lx, ly), label, font=font, fill=(220, 230, 255), anchor="mm")
        
        val = params.get(label, 70) / 100.0
        data_points.append((center_x + (radius * val) * math.cos(angle), center_y + (radius * val) * math.sin(angle)))

    draw.polygon(data_points, outline=(255, 215, 0), width=4)
    for pt in data_points:
        draw.ellipse([pt[0]-6, pt[1]-6, pt[0]+6, pt[1]+6], fill=(255, 224, 102))

# ==========================================
# 4. 4枚の画像を生成するメイン処理
# ==========================================
def generate_carousel_images(user_icon_img, type_name, wuxing_type, tags, params, text_blocks):
    images = []
    title_font = get_readable_font(52)
    heading_font = get_readable_font(42)
    body_font = get_readable_font(34)
    tag_font = get_readable_font(30)
    chart_font = get_readable_font(26)

    # 【1枚目】表紙（アイコンメイン）
    img1, draw1 = create_base_card()
    icon_size = 700
    icon_cropped = ImageOps.fit(user_icon_img.convert("RGBA"), (icon_size, icon_size), Image.Resampling.LANCZOS)
    img1.paste(icon_cropped, (190, 120))
    draw1.rectangle([190, 120, 190+icon_size, 120+icon_size], outline=(255, 215, 0), width=6)
    
    draw1.text((540, 880), f"★ SSR ★ {type_name}", font=title_font, fill=(255, 235, 120), anchor="mm")
    draw1.text((540, 960), f"五行属性: {wuxing_type} / " + " ".join([f"#{t.strip('#')}" for t in tags[:3]]), font=tag_font, fill=(200, 220, 255), anchor="mm")
    images.append(img1)

    # 【2枚目】基本性格 ＆ レーダーチャート
    img2, draw2 = create_base_card()
    draw2.text((80, 80), "■ 基本性格", font=heading_font, fill=(255, 224, 102))
    y_offset = 160
    for line in wrap_text(text_blocks.get("summary", ""), body_font, 920):
        draw2.text((80, y_offset), line, font=body_font, fill=(240, 240, 250))
        y_offset += 50
    draw_radar_chart(draw2, 540, 750, 220, params, chart_font)
    images.append(img2)

    # 【3枚目】対人関係 ＆ アドバイス
    img3, draw3 = create_base_card()
    draw3.text((80, 80), "■ コミュニケーション傾向", font=heading_font, fill=(64, 224, 208))
    y_offset = 160
    for line in wrap_text(text_blocks.get("comm", ""), body_font, 920):
        draw3.text((80, y_offset), line, font=body_font, fill=(240, 240, 250))
        y_offset += 50
        
    y_offset += 60
    draw3.text((80, y_offset), "■ 開運アドバイス", font=heading_font, fill=(255, 140, 0))
    y_offset += 80
    for line in wrap_text(text_blocks.get("advice", ""), body_font, 920):
        draw3.text((80, y_offset), line, font=body_font, fill=(240, 240, 250))
        y_offset += 50
    images.append(img3)

    # 【4枚目】今日のワンポイント開運鑑定
    img4, draw4 = create_base_card()
    draw4.text((80, 80), "🔮 本日のワンポイント鑑定", font=heading_font, fill=(224, 176, 255))
    y_offset = 180
    for line in wrap_text(text_blocks.get("daily", ""), body_font, 920):
        draw4.text((80, y_offset), line, font=body_font, fill=(240, 240, 250))
        y_offset += 55
        
    y_offset += 100
    phrase = text_blocks.get("phrase", "")
    if phrase:
        draw4.rectangle([60, y_offset-30, 1020, y_offset+120], fill=(40, 30, 50), outline=(255, 215, 0), width=2)
        draw4.text((540, y_offset+45), f"「{phrase}」", font=heading_font, fill=(255, 224, 102), anchor="mm")
    images.append(img4)

    return images

# ==========================================
# 5. UIと実行ロジック
# ==========================================
with st.sidebar:
    st.header("⚙️ 設定")
    st.session_state.api_key = st.text_input("Gemini API Key を入力", value=st.session_state.api_key, type="password")

step_labels = ["1. 生年月日", "2. アイコン選択", "3. 鑑定結果"]
step_html = "<div class='step-bar'>"
for i, lbl in enumerate(step_labels):
    active_class = " active" if i == st.session_state.step else ""
    step_html += f"<div class='step-item{active_class}'>{lbl}</div>"
step_html += "</div>"
st.markdown(step_html, unsafe_allow_html=True)

if st.session_state.step == 0:
    st.session_state.birth_date_str = st.text_input("生年月日（8桁）", value=st.session_state.birth_date_str, max_chars=8)
    if st.button("次へ進む ➔", type="primary", use_container_width=True):
        if len(st.session_state.birth_date_str) == 8: 
            st.session_state.step = 1
            st.rerun()

elif st.session_state.step == 1:
    uploaded_file = st.file_uploader("アイコン画像", type=["png", "jpg", "jpeg"])
    if uploaded_file: 
        st.session_state.uploaded_file = uploaded_file
        st.image(Image.open(uploaded_file), width=200)
    
    col1, col2 = st.columns(2)
    if col1.button("⬅️ 戻る", use_container_width=True): 
        st.session_state.step = 0
        st.rerun()
    if col2.button("鑑定開始 ➔", type="primary", use_container_width=True):
        if not st.session_state.api_key:
            st.error("サイドバーに Gemini API Key を入力してください。")
        elif "uploaded_file" not in st.session_state: 
            st.warning("アイコン画像をアップロードしてください。")
        else:
            st.session_state.step = 2
            st.rerun()

elif st.session_state.step == 2:
    if st.button("⬅️ 最初からやり直す"):
        st.session_state.step = 0
        st.session_state.card_images = None
        st.rerun()

    if not st.session_state.card_images:
        if not st.session_state.api_key:
            st.error("APIキーが入力されていません。サイドバーを確認してください。")
            st.stop()

        valid_date = datetime.date(int(st.session_state.birth_date_str[:4]), int(st.session_state.birth_date_str[4:6]), int(st.session_state.birth_date_str[6:8]))
        user_gan = get_day_gan(valid_date)
        today_gan = get_day_gan(datetime.date.today())

        with st.spinner("4枚の鑑定画像を錬成中..."):
            image = Image.open(st.session_state.uploaded_file)
            prompt = f"""
提供された画像から性格を分析し、以下のフォーマットのみで出力してください。（マークダウン装飾不要）
■タイプ名: [キャッチーなタイプ名]
■ハッシュタグ: #[タグ1], #[タグ2], #[タグ3]
■パラメータ: 洞察力:[40-100], 直感力:[40-100], 社交性:[40-100], 独自性:[40-100], 柔軟性:[40-100]
■基本性格: [150文字程度の解説]
■コミュニケーション: [150文字程度の解説]
■アドバイス: [100文字程度のアドバイス]
■キーフレーズ: [20文字程度の決め台詞]
■今日の鑑定: [五行「{GAN_WU_XING[user_gan]}」に基づく本日のアドバイスを150文字程度で]
"""
            client = genai.Client(api_key=st.session_state.api_key)
            res = client.models.generate_content(model='gemini-3.6-flash', contents=[image, prompt]).text
            
            def extract(key):
                m = re.search(f'■{key}:(.*?)(?=■|$)', res, re.DOTALL)
                return m.group(1).strip() if m else ""

            params = {k: int(re.search(fr'{k}:(\d+)', extract("パラメータ")).group(1)) for k in ["洞察力", "直感力", "社交性", "独自性", "柔軟性"] if re.search(fr'{k}:(\d+)', extract("パラメータ"))}
            
            text_blocks = {
                "summary": extract("基本性格"),
                "comm": extract("コミュニケーション"),
                "advice": extract("アドバイス"),
                "phrase": extract("キーフレーズ"),
                "daily": extract("今日の鑑定")
            }

            st.session_state.card_images = generate_carousel_images(
                image, extract("タイプ名"), GAN_WU_XING[user_gan], extract("ハッシュタグ").split(','), params, text_blocks
            )

    if st.session_state.card_images:
        st.success("✨ 4枚の鑑定画像が完成しました！スワイプ感覚で確認できます。")
        
        cols = st.columns(2)
        for i, img in enumerate(st.session_state.card_images):
            cols[i%2].image(img, caption=f"{i+1}枚目", use_container_width=True)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for i, img in enumerate(st.session_state.card_images):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                z.writestr(f"manga_slide_{i+1}.png", img_byte_arr.getvalue())
        
        st.download_button(
            label="📦 4枚の画像をまとめて保存（ZIP）",
            data=buf.getvalue(),
            file_name="diagnosis_4slides.zip",
            mime="application/zip",
            use_container_width=True
        )