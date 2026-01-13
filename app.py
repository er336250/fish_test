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
        content = uploaded_file.getvalue().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
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
            if original_name:
                not_found.append(original_name)
    return translated_data, not_found, translated_count

# ============================================
# 2. Streamlit 介面設定
# ============================================

st.set_page_config(page_title="魚名翻譯大師", page_icon="🐟", layout="wide")

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
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

st.title("🐟 魚表翻譯機")

# ============================================
# 3. 主畫面檔案上傳區 (標題下方)
# ============================================

upload_col1, upload_col2 = st.columns(2)

with upload_col1:
    json_file = st.file_uploader("1. 上傳原始 JSON (tw.json)", type=['json'])

with upload_col2:
    csv_file = st.file_uploader("2. 上傳字典 CSV", type=['csv'])

st.divider()

# ============================================
# 4. 邏輯處理與結果顯示
# ============================================

if json_file and csv_file:
    try:
        tw_data = json.load(json_file)
        if not isinstance(tw_data, list):
            st.error("❌ JSON 格式錯誤：根節點必須是一個清單 [ ... ]")
            st.stop()
            
        translation_dict = load_translation_dict_from_file(csv_file)
        
        # 統計資訊
        json_fish_names = {normalize_name(item.get('fishName', '')) for item in tw_data if item.get('fishName')}
        dict_fish_names = set(translation_dict.keys())
        covered = json_fish_names & dict_fish_names
        missing = sorted(list(json_fish_names - dict_fish_names))
        coverage_rate = (len(covered) / len(json_fish_names)) * 100 if json_fish_names else 0

        # 分頁選單
        tab1, tab2, tab3 = st.tabs(["📊 數據分析", "🔍 異常檢查", "🚀 執行翻譯"])

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
                st.dataframe(pd.DataFrame(missing, columns=["缺少的名稱"]), use_container_width=True)
            else:
                st.success("🎉 太棒了！字典已完全覆蓋所有項目。")

        with tab2:
            st.subheader("重複名稱與結構檢查")
            fish_map = defaultdict(list)
            for item in tw_data:
                name = normalize_name(item.get('fishName'))
                if name: fish_map[name].append(item.get('fishType'))
            
            duplicates = {n: t for n, t in fish_map.items() if len(t) > 1}
            
            if duplicates:
                st.error(f"⚠️ 偵測到 {len(duplicates)} 組重複魚名")
                df_dup = pd.DataFrame([{"魚名": k, "出現次數": len(v), "Type清單": v} for k, v in duplicates.items()])
                st.table(df_dup)
            else:
                st.success("✅ JSON 結構良好，未發現重複 fishName。")

        with tab3:
            st.subheader("翻譯結果與下載")
            translated_data, not_found, count = translate_fish_names(tw_data, translation_dict)
            
            res_col1, res_col2 = st.columns([2, 1])
            with res_col1:
                st.info(f"成功替換了 **{count}** 個魚名標籤。")
            with res_col2:
                output_json = json.dumps(translated_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 點我下載翻譯後的 JSON",
                    data=output_json,
                    file_name="translated_result.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            st.divider()
            st.write("🔍 **資料預覽 (前 5 筆)：**")
            st.json(translated_data[:5])

    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
else:
    # 檔案尚未上傳完全時的提示畫面
    st.markdown("""
        <div style="text-align: center; padding: 50px 20px;">
            <p style="color: #888888; font-size: 18px;">請上傳 JSON 與 CSV 檔案以開始翻譯程序</p>
        </div>
    """, unsafe_allow_html=True)
