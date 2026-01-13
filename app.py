import streamlit as st
import json
import csv
import copy
from collections import defaultdict
import io
import pandas as pd

# --- 核心邏輯函數 ---

def normalize_name(name):
    if not name: return ''
    return str(name).strip()

def load_translation_dict_from_file(uploaded_file):
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
            not_found.append(original_name)
    return translated_data, not_found, translated_count

# --- Streamlit 介面優化 ---

st.set_page_config(page_title="魚名翻譯大師", page_icon="🐟", layout="wide")

# 自定義 CSS 讓介面更精緻
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_stdio=True)

st.title("🐟 魚名自動翻譯系統")
st.caption("專為遊戲字典檔設計的快速比對與轉換工具")

# 側邊欄設計
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/fish.png", width=80)
    st.header("📂 檔案上傳")
    json_file = st.file_uploader("1. 上傳原始 JSON (tw.json)", type=['json'], help="請上傳包含 fishName 欄位的 JSON 檔案")
    csv_file = st.file_uploader("2. 上傳字典 CSV", type=['csv'], help="第一欄為原文，第二欄為翻譯")
    
    st.divider()
    st.markdown("### 🛠️ 說明")
    st.info("系統會自動過濾空格並比對名稱。完成後可切換分頁查看分析報告。")

if json_file and csv_file:
    try:
        # 讀取資料
        tw_data = json.load(json_file)
        translation_dict = load_translation_dict_from_file(csv_file)
        
        # 預處理統計
        json_fish_names = {normalize_name(item.get('fishName', '')) for item in tw_data if item.get('fishName')}
        dict_fish_names = set(translation_dict.keys())
        covered = json_fish_names & dict_fish_names
        missing = sorted(list(json_fish_names - dict_fish_names))
        coverage_rate = (len(covered) / len(json_fish_names)) * 100 if json_fish_names else 0

        # 分頁系統
        tab1, tab2, tab3 = st.tabs(["📊 覆蓋率分析", "🔍 異常檢查", "🚀 執行翻譯"])

        # Tab 1: 統計分析
        with tab1:
            st.subheader("數據概覽")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("JSON 總項目", len(tw_data))
            m2.metric("唯一魚名數量", len(json_fish_names))
            m3.metric("字典可用項目", len(dict_fish_names))
            m4.metric("完成率", f"{coverage_rate:.1f}%")

            st.progress(coverage_rate / 100)

            if missing:
                st.warning(f"💡 尚有 {len(missing)} 個魚名在字典中找不到翻譯：")
                st.write(missing)
            else:
                st.success("🎉 太棒了！字典已完全覆蓋所有項目。")

        # Tab 2: 異常檢查
        with tab2:
            st.subheader("重複項與結構檢查")
            fish_map = defaultdict(list)
            for item in tw_data:
                name = normalize_name(item.get('fishName'))
                if name: fish_map[name].append(item.get('fishType'))
            
            duplicates = {n: t for n, t in fish_map.items() if len(t) > 1}
            
            if duplicates:
                st.error("⚠️ 偵測到重複魚名 (相同的 fishName 對應多個 fishType)")
                df_dup = pd.DataFrame([{"名稱": k, "出現次數": len(v), "對應 Type": v} for k, v in duplicates.items()])
                st.table(df_dup)
            else:
                st.success("✅ JSON 結構良好，未發現重複 fishName。")

        # Tab 3: 執行翻譯
        with tab3:
            st.subheader("翻譯預覽與下載")
            translated_data, not_found, count = translate_fish_names(tw_data, translation_dict)
            
            col_pre1, col_pre2 = st.columns(2)
            with col_pre1:
                st.info(f"替換總次數：{count}")
            with col_pre2:
                output_json = json.dumps(translated_data, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 立即下載翻譯後的 JSON",
                    data=output_json,
                    file_name="translated_result.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with st.expander("👀 點我預覽前 5 筆翻譯結果"):
                st.json(translated_data[:5])

    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
else:
    # 初始歡迎畫面
    st.empty()
    st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <img src="https://img.icons8.com/bubbles/200/000000/data-configuration.png" width="150">
            <h2>等待檔案上傳中...</h2>
            <p>請使用左側邊欄上傳您的 JSON 和 CSV 檔案</p>
        </div>
    """, unsafe_allow_html=True)
