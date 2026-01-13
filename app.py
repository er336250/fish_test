import streamlit as st
import json
import csv
import copy
from collections import defaultdict
import io
import pandas as pd

# ============================================
# 1. 核心邏輯函數
# ============================================

def normalize_name(name):
    """字串正規化：去除前後空白並轉為字串"""
    if not name: return ''
    return str(name).strip()

def load_translation_dict_from_file(uploaded_file):
    """讀取上傳的 CSV 字典檔"""
    translation_dict = {}
    try:
        # 使用 utf-8-sig 處理 Excel 可能產生的 BOM 頭，避免讀取到亂碼
        content = uploaded_file.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        # 假設第一列是標題，從第二列開始讀取
        for row in rows[1:]:
            if len(row) >= 2:
                chinese = normalize_name(row[0])
                translation = row[1].strip()
                if chinese and translation:
                    translation_dict[chinese] = translation
    except Exception as e:
        st.error(f"解析 CSV 失敗: {e}")
    return translation_dict

def translate_fish_names(json_data, translation_dict):
    """執行翻譯邏輯"""
    translated_data = copy.deepcopy(json_data)
    translated_count = 0
    not_found = []
    for i, item in enumerate(translated_data):
        original_name = item.get('fishName', '')
        norm_name = normalize_name(original_name)
        if norm_name in translation_dict:
            translated_data[i]['fishName'] = translation_dict[norm_name]
            translated_count += 1
        else:
            if original_name: # 只記錄非空的缺失項
                not_found.append(original_name)
    return translated_data, not_found, translated_count

# ============================================
# 2. Streamlit 介面設定
# ============================================

st.set_page_config(page_title="魚名翻譯大師", page_icon="🐟", layout="wide")

# 自定義 CSS 美化
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
        border: 1px solid #eee;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        font-size: 16px;
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🐟 魚名自動翻譯系統")
st.caption("版本 2.0 | 專為 JSON 字典轉換優化的工具")

# ============================================
# 3. 側邊欄：檔案管理
# ============================================

with st.sidebar:
    st.header("📂 檔案上傳")
    json_file = st.file_uploader("1. 上傳原始 JSON (tw.json)", type=['json'], help="請上傳包含 fishName 欄位的 JSON 檔案")
    csv_file = st.file_uploader("2. 上傳字典 CSV", type=['csv'], help="第一欄為原文，第二欄為翻譯")
    
    st.divider()
    st.markdown("### 🛠️ 使用說明")
    st.write("1. 上傳兩個必要檔案")
    st.write("2. 在『數據分析』查看是否有缺漏")
    st.write("3. 在『執行翻譯』下載結果")
    st.info("💡 提示：CSV 第一列會被視為標題而忽略。")

# ============================================
# 4. 主畫面邏輯
# ============================================

if json_file and csv_file:
    try:
        # 解析上傳資料
        tw_data = json.load(json_file)
        if not isinstance(tw_data, list):
            st.error("❌ JSON 格式錯誤：根節點必須是一個清單 [ ... ]")
            st.stop()
            
        translation_dict = load_translation_dict_from_file(csv_file)
        
        # 統計資訊計算
        json_fish_names = {normalize_name(item.get('fishName', '')) for item in tw_data if item.get('fishName')}
        dict_fish_names = set(translation_dict.keys())
        covered = json_fish_names & dict_fish_names
        missing = sorted(list(json_fish_names - dict_fish_names))
        coverage_rate = (len(covered) / len(json_fish_names)) * 100 if json_fish_names else 0

        # 分頁選單
        tab1, tab2, tab3 = st.tabs(["📊 數據分析", "🔍 異常檢查", "🚀 執行翻譯"])

        # --- Tab 1: 數據分析 ---
        with tab1:
            st.subheader("翻譯覆蓋狀況")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("JSON 總筆數", len(tw_data))
            m2.metric("唯一魚名數", len(json_fish_names))
            m3.metric("字典可用數", len(dict_fish_names))
            m4.metric("完成率", f"{coverage_rate:.1f}%")

            st.progress(coverage_rate / 100)

            if missing:
                st.warning(f"⚠️ 尚有 {len(missing)} 個魚名在字典中找不到翻譯：")
                # 使用 DataFrame 讓列表更好看
                st.dataframe(pd.DataFrame(missing, columns=["缺少的名稱"]), use_container_width=True)
            else:
                st.success("🎉 太棒了！字典已完全覆蓋所有項目。")

        # --- Tab 2: 異常檢查 ---
        with tab2:
            st.subheader("重複名稱與結構檢查")
            fish_map = defaultdict(list)
            for item in tw_data:
                name = normalize_name(item.get('fishName'))
                if name: fish_map[name].append(item.get('fishType'))
            
            duplicates = {n: t for n, t in fish_map.items() if len(t) > 1}
            
            if duplicates:
                st.error(f"⚠️ 偵測到 {len(duplicates)} 組重複魚名 (相同的名稱對應不同 ID/Type)")
                df_dup = pd.DataFrame([{"魚名": k, "出現次數": len(v), "Type清單": v} for k, v in duplicates.items()])
                st.table(df_dup)
            else:
                st.success("✅ JSON 結構良好，未發現重複 fishName。")

        # --- Tab 3: 執行翻譯 ---
        with tab3:
            st.subheader("翻譯結果與下載")
            translated_data, not_found, count = translate_fish_names(tw_data, translation_dict)
            
            # 下載區域
            download_col1, download_col2 = st.columns([2, 1])
            with download_col1:
                st.info(f"此次處理共成功替換了 **{count}** 個魚名標籤。")
            with download_col2:
                output_json = json.dumps(translated_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 點我下載翻譯後的 JSON",
                    data=output_json,
                    file_name="translated_result.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            st.divider()
            st.write("🔍 **前 5 筆資料預覽：**")
            st.json(translated_data[:5])

    except Exception as e:
        st.error(f"❌ 處理過程中發生非預期錯誤: {e}")
else:
    # 歡迎畫面
    st.markdown("""
        <div style="text-align: center; padding: 100px 20px;">
            <h2 style="color: #4A4A4A;">歡迎使用魚名翻譯工具</h2>
            <p style="color: #888888; font-size: 18px;">請先在左側邊欄上傳您的 <b style="color: #FF4B4B;">JSON</b> 與 <b style="color: #FF4B4B;">CSV</b> 檔案</p>
            <div style="margin-top: 30px;">
                <img src="https://img.icons8.com/clouds/200/000000/upload.png" width="150">
            </div>
        </div>
    """, unsafe_allow_html=True)
