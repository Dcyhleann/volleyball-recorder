import streamlit as st
import pandas as pd
from datetime import datetime
import io
import time

# ==========================================
# 0. 頁面設定與 CSS
# ==========================================
st.set_page_config(layout="wide", page_title="排球比賽紀錄系統 Pro", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 調整按鈕樣式 */
    div.stButton > button {
        min-height: 50px;
        font-size: 18px;
    }
    /* 選中球員的樣式 (黃色) */
    div.stButton > button:active {
        background-color: #FFD700 !important;
        color: black !important;
    }
    /* 位置標籤置中 */
    .pos-label {
        text-align: center;
        font-size: 14px;
        color: gray;
        margin-bottom: -10px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 資料結構與常數定義
# ==========================================

# 預設名單
ROSTER_DB = [
    {"背號": "1", "姓名": "舉球A", "位置": "S"},
    {"背號": "2", "姓名": "大砲B", "位置": "LH"},
    {"背號": "3", "姓名": "大砲C", "位置": "LH"},
    {"背號": "4", "姓名": "攔中D", "位置": "MB"},
    {"背號": "5", "姓名": "攔中E", "位置": "MB"},
    {"背號": "6", "姓名": "舉對F", "位置": "RH"},
    {"背號": "7", "姓名": "自由G", "位置": "L"},
    {"背號": "8", "姓名": "替補H", "位置": "LH"},
]

# --- 嚴格依照 Excel 附圖定義的順序 ---
ORDERED_ROWS = [
    # 繼續區 (Yellow)
    "發球繼續", "攔網繼續", "接發繼續", "接發好球繼續", 
    "接球繼續", "接球好球繼續", "舉球繼續", "舉球好球繼續", 
    "攻擊擊球繼續", "送球繼續",
    # 得分區 (Green)
    "發球得分", "直接得分", "對手接噴", "打手得分", "吊球得分", "送球得分", "攔網得分", 
    # 對手失誤類 (歸類在得分區呈現，但來源是對手)
    "對手失誤(總計)", 
    # 失誤區 (Red)
    "發球出界", "發球掛網", "發球犯規", 
    "攻擊出界", "攻擊掛網", "攻擊被攔", "送球失誤", "攻擊犯規", 
    "舉球失誤", "舉球犯規", 
    "接發失誤", "站位失誤", "接球失誤", "防守犯規", 
    "攔網失誤", "攔網犯規"
]

# 按鈕對應到統計表的名稱映射 (Button Name -> Stats Row Name)
# 左邊是程式按鈕的參數，右邊是統計表顯示的文字
ACTION_MAP = {
    # 繼續
    "發球": "發球繼續", "攔網": "攔網繼續", 
    "接發A": "接發好球繼續", "接發B": "接發繼續",
    "接球A": "接球好球繼續", "接球B": "接球繼續",
    "舉球": "舉球繼續", "舉球好球": "舉球好球繼續",
    "攻擊": "攻擊擊球繼續", "處理球": "送球繼續",
    # 得分
    "發球得分": "發球得分", 
    "攻擊得分": "直接得分", # 預設攻擊得分對應直接得分
    "吊球得分": "吊球得分", "後排得分": "直接得分", "快攻得分": "直接得分", "修正得分": "直接得分", "打手得分": "打手得分", "送球得分": "送球得分",
    "攔網得分": "攔網得分",
    "對手接噴": "對手接噴",
    # 失誤
    "發球出界": "發球出界", "發球掛網": "發球掛網", "發球犯規": "發球犯規",
    "攻擊出界": "攻擊出界", "攻擊掛網": "攻擊掛網", "攻擊被攔": "攻擊被攔", "攻擊犯規": "攻擊犯規", "送球失誤": "送球失誤",
    "舉球失誤": "舉球失誤", "連擊": "舉球犯規",
    "接發失誤": "接發失誤", "接球失誤": "接球失誤", "防守犯規": "防守犯規", "站位失誤": "站位失誤",
    "攔網失誤": "攔網失誤", "攔網觸網": "攔網犯規", "攔網犯規": "攔網犯規"
}

# 動作下拉選單 (給編輯用)
ALL_ACTIONS_DROPDOWN = list(ACTION_MAP.values()) + ["對手失誤(總計)"]

# ==========================================
# 2. Session State 初始化
# ==========================================
if 'logs' not in st.session_state: st.session_state.logs = []
if 'my_score' not in st.session_state: st.session_state.my_score = 0
if 'enemy_score' not in st.session_state: st.session_state.enemy_score = 0
if 'current_player' not in st.session_state: st.session_state.current_player = None 
if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False
# 用來控制 Tab 重置的 Key
if 'tab_key' not in st.session_state: st.session_state.tab_key = 0 

# 比賽資訊
if 'game_meta' not in st.session_state:
    st.session_state.game_meta = {
        "match_name": "校內聯賽", # 需求 1
        "date": datetime.now().date(),
        "opponent": "對手",
        "set": 1
    }

# 先發陣容
if 'active_lineup' not in st.session_state:
    st.session_state.active_lineup = [
        f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB[:7]
    ]

# ==========================================
# 3. 核心邏輯函數
# ==========================================
def log_event(action_key, type_code):
    """
    type_code: 0=Continue, 1=Score(My), -1=Error(Enemy Score)
    action_key: 按鈕傳進來的原始名稱
    """
    player = st.session_state.current_player
    is_opponent_action = "對手" in action_key
    
    # 檢查是否選取球員
    if not player and not is_opponent_action:
        st.toast("⚠️ 請先選擇一位球員！", icon="⚠️")
        return 

    # 映射到統計表的標準名稱
    stats_name = ACTION_MAP.get(action_key, action_key)
    if is_opponent_action and type_code == 1:
        stats_name = "對手失誤(總計)"
        final_player = "對手"
    else:
        final_player = player

    if is_opponent_action:
        st.session_state.current_player = None

    # 計算比分
    score_display = "" # 需求 6: 繼續時空白
    if type_code == 1:
        st.session_state.my_score += 1
        result_str = "得分"
        score_display = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    elif type_code == -1:
        st.session_state.enemy_score += 1
        result_str = "失誤"
        score_display = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    else:
        result_str = "繼續"
        score_display = "" # 繼續球不顯示比分

    # 新增紀錄
    new_record = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "球員": final_player, 
        "動作": stats_name, # 存入標準化後的名稱
        "結果": result_str,
        "比分": score_display,
        "原始分數": (st.session_state.my_score, st.session_state.enemy_score)
    }
    st.session_state.logs.insert(0, new_record)
    
    # 需求 3: 紀錄後取消選取球員
    st.session_state.current_player = None
    # 需求 3: 重置 Tab 回到第一個 (透過改變 key 強制重繪)
    st.session_state.tab_key += 1

# ==========================================
# 4. 介面佈局
# ==========================================

# --- 頂部資訊列 ---
col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    meta = st.session_state.game_meta
    st.markdown(f"### 🏆 {meta['match_name']} | 📅 {meta['date']} | 🆚 {meta['opponent']} (G{meta['set']})")

with col_info2:
    if st.button("🔄 新局/歸零", type="secondary", use_container_width=True):
        st.session_state.confirm_reset = True

if st.session_state.confirm_reset:
    with st.chat_message("assistant"):
        st.warning("確定要清空所有紀錄？")
        c1, c2 = st.columns(2)
        if c1.button("✅ 確定"):
            st.session_state.logs = []
            st.session_state.my_score = 0
            st.session_state.enemy_score = 0
            st.session_state.current_player = None
            st.session_state.confirm_reset = False
            st.rerun()
        if c2.button("❌ 取消"):
            st.session_state.confirm_reset = False
            st.rerun()

# --- 比分板 ---
st.markdown(f"""
<div style="text-align: center; background-color: #f0f2f6; padding: 5px; border-radius: 10px; margin-bottom: 10px;">
    <h1 style="margin:0; font-size: 3.5em;">
        <span style="color: blue">{st.session_state.my_score}</span> : <span style="color: red">{st.session_state.enemy_score}</span>
    </h1>
</div>
""", unsafe_allow_html=True)

# --- 設定區 ---
with st.expander("⚙️ 設定：比賽資訊與替補換人"):
    # 需求 1: 增加比賽名稱
    c0, c1, c2, c3 = st.columns(4)
    st.session_state.game_meta['match_name'] = c0.text_input("比賽名稱", value=st.session_state.game_meta['match_name'])
    st.session_state.game_meta['date'] = c1.date_input("日期", value=st.session_state.game_meta['date'])
    st.session_state.game_meta['opponent'] = c2.text_input("對手", value=st.session_state.game_meta['opponent'])
    st.session_state.game_meta['set'] = c3.number_input("局數", min_value=1, value=st.session_state.game_meta['set'])
    
    st.markdown("---")
    st.subheader("📋 場上陣容 (需求 2: 設定區顯示完整資訊)")
    
    roster_options = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB]
    cols_lineup = st.columns(7)
    for i in range(7):
        with cols_lineup[i]:
            # 讓使用者設定位置 1~7 是誰
            default_idx = roster_options.index(st.session_state.active_lineup[i]) if st.session_state.active_lineup[i] in roster_options else 0
            new_val = st.selectbox(f"位置 {i+1}", roster_options, index=default_idx, key=f"pos_{i}")
            st.session_state.active_lineup[i] = new_val

# --- 主操作區 ---
left_panel, right_panel = st.columns([2, 1])

with left_panel:
    # 1. 球員按鈕區 (需求 2: 按鈕只顯背號名字，位置在上方)
    st.subheader("1. 選擇球員")
    p_cols = st.columns(7)
    for idx, player_str in enumerate(st.session_state.active_lineup):
        # player_str: "1 - 名字 (位置)"
        try:
            parts = player_str.split(" - ")
            num = parts[0]
            name_pos = parts[1].split(" (")
            name = name_pos[0]
            pos = name_pos[1].replace(")", "")
        except:
            num, name, pos = "?", "?", "?"

        is_selected = (st.session_state.current_player == player_str)
        
        with p_cols[idx]:
            # 顯示位置在上方
            st.markdown(f"<div class='pos-label'>{pos}</div>", unsafe_allow_html=True)
            # 按鈕只顯示背號與名字
            btn_label = f"{num}\n{name}"
            if st.button(btn_label, key=f"btn_p_{idx}", type="primary" if is_selected else "secondary", use_container_width=True):
                if is_selected:
                    st.session_state.current_player = None
                else:
                    st.session_state.current_player = player_str
                st.rerun()

    st.divider()

    # 2. 動作按鈕區 (Grid Layout)
    st.subheader("2. 紀錄動作")
    
    # 需求 3: 紀錄動作後回到繼續分頁 (使用 dynamic key)
    tab_cont, tab_score, tab_error = st.tabs(["🔵 繼續 (無分)", "🟢 得分 (本隊+1)", "🔴 失誤 (對手+1)"]) # , key=f"tabs_{st.session_state.tab_key}" 
    # Streamlit Tab 重置的小技巧: 改變 key 會強制重繪組件，預設回到第一個 tab
    # 但為了避免畫面閃爍太大，我們可以用容器包裝

    with st.container():
        # 由於 st.tabs 不支援直接設定 index，我們用變數控制顯示內容，或者接受手動切換
        # 如果堅持要自動切回，必須使用 key hack，這裡示範 key hack 的版本：
        # 為了解決 key 改變導致的狀態遺失，這裡採用折衷方案：只在按鈕被點擊後的 rerun 重置 key
        
        pass 

    # 重新宣告 Tabs 帶有 dynamic key 才能實現自動切回
    current_tabs = st.tabs(["🔵 繼續 (無分)", "🟢 得分 (本隊+1)", "🔴 失誤 (對手+1)"])
    
    # --- 繼續區 ---
    with current_tabs[0]:
        r1 = st.columns(6)
        r1[0].button("發球", on_click=log_event, args=("發球", 0), use_container_width=True)
        r1[1].button("攔網", on_click=log_event, args=("攔網", 0), use_container_width=True)
        r1[2].button("接發A", on_click=log_event, args=("接發A", 0), use_container_width=True) # -> 接發好球繼續
        r1[2].button("接發B", on_click=log_event, args=("接發B", 0), use_container_width=True) # -> 接發繼續
        r1[3].button("接球A", on_click=log_event, args=("接球A", 0), use_container_width=True)
        r1[3].button("接球B", on_click=log_event, args=("接球B", 0), use_container_width=True)
        r1[4].button("舉球", on_click=log_event, args=("舉球", 0), use_container_width=True)
        r1[4].button("舉球好球", on_click=log_event, args=("舉球好球", 0), use_container_width=True)
        r1[5].button("攻擊", on_click=log_event, args=("攻擊", 0), use_container_width=True)
        r1[5].button("處理球", on_click=log_event, args=("處理球", 0), use_container_width=True)

    # --- 得分區 ---
    with current_tabs[1]:
        s_col1, s_col2, s_col3, s_col4 = st.columns([1, 2, 1, 2])
        
        with s_col1:
            st.caption("發球")
            st.button("發球得分", on_click=log_event, args=("發球得分", 1), use_container_width=True)
        
        with s_col2:
            st.caption("攻擊")
            st.button("攻擊得分", on_click=log_event, args=("攻擊得分", 1), use_container_width=True, help="直接得分")
            c_sub1, c_sub2 = st.columns(2)
            c_sub1.button("吊球得分", on_click=log_event, args=("吊球得分", 1), use_container_width=True)
            c_sub2.button("打手得分", on_click=log_event, args=("打手得分", 1), use_container_width=True)
            c_sub1.button("送球得分", on_click=log_event, args=("送球得分", 1), use_container_width=True)
            c_sub2.button("後排得分", on_click=log_event, args=("後排得分", 1), use_container_width=True)

        with s_col3:
            st.caption("攔網")
            st.button("攔網得分", on_click=log_event, args=("攔網得分", 1), use_container_width=True)

        with s_col4:
            st.caption("對手失誤 (我方得分)")
            # 這些按鈕會記錄為 "對手失誤(總計)"
            opp_errs = ["對手發球出界", "對手發球掛網", "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", "對手舉球失誤", "對手攔網犯規"]
            for oe in opp_errs:
                st.button(oe, on_click=log_event, args=(oe, 1), use_container_width=True)

    # --- 失誤區 ---
    with current_tabs[2]:
        e_col1, e_col2, e_col3, e_col4, e_col5 = st.columns(5)
        
        with e_col1:
            st.caption("發球")
            for act in ["發球出界", "發球掛網", "發球犯規"]:
                st.button(act, on_click=log_event, args=(act, -1), use_container_width=True)
        
        with e_col2:
            st.caption("攻擊")
            for act in ["攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "送球失誤"]:
                st.button(act, on_click=log_event, args=(act, -1), use_container_width=True)
        
        with e_col3:
            st.caption("舉球")
            for act in ["舉球失誤", "連擊"]:
                st.button(act, on_click=log_event, args=(act, -1), use_container_width=True)
        
        with e_col4:
            st.caption("防守")
            for act in ["接發失誤", "接球失誤", "站位失誤", "防守犯規"]:
                st.button(act, on_click=log_event, args=(act, -1), use_container_width=True)
        
        with e_col5:
            st.caption("攔網")
            for act in ["攔網觸網", "攔網失誤"]: # 攔網出界算失誤
                st.button(act, on_click=log_event, args=(act, -1), use_container_width=True)

with right_panel:
    # --- 紀錄明細 ---
    st.subheader("📝 紀錄明細")
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        player_options = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB] + ["對手"]
        
        edited_df = st.data_editor(
            df_logs,
            column_config={
                "球員": st.column_config.SelectboxColumn("球員", options=player_options, required=True),
                "動作": st.column_config.SelectboxColumn("動作", options=ALL_ACTIONS_DROPDOWN, required=True),
                "結果": st.column_config.TextColumn("結果", disabled=True),
                "比分": st.column_config.TextColumn("比分", disabled=True),
                "原始分數": None
            },
            hide_index=True,
            use_container_width=True,
            height=250,
            key=f"editor_{st.session_state.tab_key}" # key changed to avoid stale data
        )
        st.session_state.logs = edited_df.to_dict('records')
    else:
        st.info("尚無紀錄")

    # --- 嚴格統計 (需求 4) ---
    st.subheader("📊 統計 (依Excel附圖架構)")
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        
        # 1. 建立 Pivot Table
        # 只需要: index=動作, columns=背號 (只包含背號)
        # 先把球員名稱簡化成背號，方便顯示
        def get_number(p_str):
            if "對手" in p_str: return "對手"
            return p_str.split(" - ")[0]
        
        df['ShortName'] = df['球員'].apply(get_number)
        
        # 統計次數
        stats = df.pivot_table(index='動作', columns='ShortName', aggfunc='size', fill_value=0)
        
        # 2. 嚴格依照 ORDERED_ROWS 排序 Index
        # 使用 reindex 強制包含所有列，即使是 0
        stats = stats.reindex(ORDERED_ROWS, fill_value=0)
        
        # 3. 欄位排序 (本隊球員 -> 對手 -> Total)
        # 抓出目前有的欄位
        cols = [c for c in stats.columns if c != "對手"]
        # 簡單排序 (字串排序)
        cols.sort()
        # 加入對手
        if "對手" in stats.columns:
            cols.append("對手")
        
        stats = stats[cols]
        
        # 計算 Total
        stats["Total"] = stats.sum(axis=1)
        
        # 4. 增加底部「個人得分總和」與「個人失分總和」
        score_rows = ["發球得分", "直接得分", "對手接噴", "打手得分", "吊球得分", "送球得分", "攔網得分"]
        error_rows = ["發球出界", "發球掛網", "發球犯規", "攻擊出界", "攻擊掛網", "攻擊被攔", "送球失誤", "攻擊犯規", 
                      "舉球失誤", "舉球犯規", "接發失誤", "站位失誤", "接球失誤", "防守犯規", "攔網失誤", "攔網犯規"]
        
        total_score = stats.loc[stats.index.intersection(score_rows)].sum()
        total_error = stats.loc[stats.index.intersection(error_rows)].sum()
        
        stats.loc["個人得分總和"] = total_score
        stats.loc["個人失分總和"] = total_error

        # 顯示 (使用 pandas styling 簡單模擬)
        st.dataframe(stats, use_container_width=True, height=600)

        # --- Excel 匯出 (需求 5: 顏色與格式) ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            # 寫入資料
            sheet_name = f"G{st.session_state.game_meta['set']}_Stats"
            stats.to_excel(writer, sheet_name=sheet_name)
            
            workbook = writer.book
            worksheet = writer.sheets[sheet_name]
            
            # 定義格式 (參考附圖顏色)
            fmt_header_yellow = workbook.add_format({'bg_color': '#FFF2CC', 'bold': True, 'border': 1}) # 繼續
            fmt_header_green = workbook.add_format({'bg_color': '#D9EAD3', 'bold': True, 'border': 1})  # 得分
            fmt_header_red = workbook.add_format({'bg_color': '#F4CCCC', 'bold': True, 'border': 1})    # 失誤
            fmt_blue_total = workbook.add_format({'bg_color': '#CFE2F3', 'bold': True, 'border': 1})    # 底部加總
            
            # 應用格式到 Index (第一欄)
            # 遍歷 ORDERED_ROWS 找出對應的 Excel 列號 (index + 1 因為有 header)
            for idx, row_name in enumerate(stats.index):
                excel_row = idx + 1 
                
                # 判定顏色
                if row_name in ["個人得分總和", "個人失分總和"]:
                    worksheet.set_row(excel_row, None, fmt_blue_total)
                    continue

                fmt = None
                if "繼續" in row_name: fmt = fmt_header_yellow
                elif "得分" in row_name or "對手" in row_name: fmt = fmt_header_green
                elif "失誤" in row_name or "出界" in row_name or "掛網" in row_name or "犯規" in row_name or "被攔" in row_name: fmt = fmt_header_red
                
                if fmt:
                    worksheet.write(excel_row, 0, row_name, fmt)
            
            # 寫入流水帳 Sheet
            df_logs.to_excel(writer, sheet_name="Logs", index=False)

        fname = f"{st.session_state.game_meta['match_name']}_{st.session_state.game_meta['opponent']}_G{st.session_state.game_meta['set']}.xlsx"
        st.download_button("📥 下載 Excel (含配色)", data=buffer.getvalue(), file_name=fname, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")