import streamlit as st
import json
import csv
import copy
from collections import defaultdict
import io

# --- 核心邏輯函數 (從你原本的代碼搬移並稍作修改以符合 Streamlit) ---

def normalize_name(name):
    if not name: return ''
    return str(name).strip()

def load_translation_dict_from_file(uploaded_file):
    translation_dict = {}
    # Streamlit 上傳的檔案需要先讀取內容
    content = uploaded_file.getvalue().decode("utf-8-sig") # 處理 BOM
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    for row in rows[1:]:  # 跳過標題列
        if len(row) >= 2:
            chinese = normalize_name(row[0])
            translation = row[1].strip()
            if chinese and translation:
                translation_dict[chinese] = translation
    return translation_dict

def translate_fish_names(json_data, translation_dict):
    translated_data = copy.deepcopy(json_data)
    translated_count = 0
    not_found = []
    for i, item in enumerate(translated_data):
        original_name = item.get('fishName')
        norm_name = normalize_name(original_name)
        if norm_name in translation_dict:
            translated_data[i]['fishName'] = translation_dict[norm_name]
            translated_count += 1
        else:
            not_found.append(original_name)
    return translated_data, not_found, translated_count

# --- Streamlit 介面設計 ---

st.set_page_config(page_title="魚名翻譯工具", page_icon="🐟", layout="wide")

st.title("🐟 魚名翻譯與檢查工具")
st.markdown("上傳 JSON 與 CSV 字典檔，快速完成名稱轉換並檢查覆蓋率。")

# 側邊欄：上傳檔案
with st.sidebar:
    st.header("1. 上傳檔案")
    json_file = st.file_uploader("上傳原始 JSON (tw.json)", type=['json'])
    csv_file = st.file_uploader("上傳字典 CSV (字典檔.csv)", type=['csv'])
    st.divider()
    st.info("💡 確保 CSV 第一欄為中文，第二欄為翻譯。")

if json_file and csv_file:
    # 讀取資料
    try:
        tw_data = json.load(json_file)
        translation_dict = load_translation_dict_from_file(csv_file)
        
        # 建立主頁面兩欄佈局
        col1, col2 = st.columns(2)

        # 邏輯計算
        json_fish_names = {normalize_name(item['fishName']) for item in tw_data if item.get('fishName')}
        dict_fish_names = set(translation_dict.keys())
        covered = json_fish_names & dict_fish_names
        missing = json_fish_names - dict_fish_names
        coverage_rate = (len(covered) / len(json_fish_names)) * 100 if json_fish_names else 0

        with col1:
            st.subheader("📊 翻譯覆蓋統計")
            m1, m2, m3 = st.columns(3)
            m1.metric("JSON 總筆數", len(tw_data))
            m2.metric("唯一魚名", len(json_fish_names))
            m3.metric("覆蓋率", f"{coverage_rate:.2f}%")

            if missing:
                st.error(f"⚠️ 缺少的翻譯數量：{len(missing)}")
                st.write(list(missing))
            else:
                st.success("✅ 字典已完美覆蓋所有魚名！")

        with col2:
            st.subheader("🔍 重複名稱檢查")
            fish_map = defaultdict(list)
            for item in tw_data:
                name = normalize_name(item.get('fishName'))
                if name: fish_map[name].append(item.get('fishType'))
            
            duplicates = {n: t for n, t in fish_map.items() if len(t) > 1}
            if duplicates:
                st.warning(f"偵測到 {len(duplicates)} 個重複名稱")
                st.json(duplicates)
            else:
                st.success("✅ 未發現重複魚名")

        # 執行翻譯並下載
        st.divider()
        st.subheader("🚀 執行結果")
        
        translated_data, not_found, count = translate_fish_names(tw_data, translation_dict)
        
        st.write(f"成功替換了 **{count}** 處名稱。")
        
        # 轉換回 JSON 字串供下載
        output_json = json.dumps(translated_data, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 下載翻譯後的 JSON",
            data=output_json,
            file_name="translated_output.json",
            mime="application/json"
        )

    except Exception as e:
        st.error(f"處理檔案時發生錯誤: {e}")
else:
    st.info("請在左側上傳兩個檔案以開始分析。")