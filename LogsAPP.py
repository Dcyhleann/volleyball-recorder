import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 0. 頁面設定與 CSS
# ==========================================
st.set_page_config(layout="wide", page_title="排球比賽紀錄系統 Pro", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* 加大按鈕 */
    div.stButton > button {
        min-height: 55px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 8px;
    }
    /* 選中球員的樣式 (黃色) */
    div.stButton > button:active {
        background-color: #FFD700 !important;
        color: black !important;
        border: 2px solid black;
    }
    /* 位置標籤 */
    .pos-label {
        text-align: center;
        font-size: 14px;
        color: #555;
        font-weight: bold;
        margin-bottom: -5px;
    }
    /* 調整 Radio 按鈕變成橫向 Tab 樣式 */
    div[role="radiogroup"] {
        flex-direction: row;
        width: 100%;
        justify-content: space-between;
    }
    div[data-testid="stRadio"] > label {
        display: none;
    }
    div[role="radiogroup"] label {
        background-color: #f0f2f6;
        padding: 10px 20px;
        border-radius: 5px;
        border: 1px solid #ddd;
        flex-grow: 1;
        text-align: center;
        margin: 0 5px;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #e6f3ff;
        border-color: #007bff;
        color: #007bff;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 資料與定義
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
    {"背號": "9", "姓名": "替補I", "位置": "MB"},
]

# 統計表順序 (Rows) - 嚴格依照附圖
ORDERED_ROWS = [
    "發球繼續", "攔網繼續", "接發繼續", "接發好球繼續", 
    "接球繼續", "接球好球繼續", "舉球繼續", "舉球好球繼續", 
    "攻擊擊球繼續", "送球繼續",
    "發球得分", "直接得分", "對手接噴", "打手得分", "吊球得分", "送球得分", "攔網得分", 
    "對手失誤(總計)", 
    "發球出界", "發球掛網", "發球犯規", 
    "攻擊出界", "攻擊掛網", "攻擊被攔", "送球失誤", "攻擊犯規", 
    "舉球失誤", "舉球犯規", 
    "接發失誤", "站位失誤", "接球失誤", "防守犯規", 
    "攔網失誤", "攔網犯規"
]

# 動作分數影響 (Value: 1=我方得分, -1=對手得分, 0=繼續)
ACTION_EFFECTS = {
    # 繼續
    "發球": 0, "攔網": 0, "接發A": 0, "接發B": 0, "接球A": 0, "接球B": 0, 
    "舉球": 0, "舉球好球": 0, "攻擊": 0, "處理球": 0,
    # 得分
    "發球得分": 1, "攻擊得分": 1, "吊球得分": 1, "後排得分": 1, "快攻得分": 1, "修正得分": 1, "打手得分": 1, "送球得分": 1, "攔網得分": 1,
    "對手發球出界": 1, "對手發球掛網": 1, "對手發球犯規": 1, "對手攻擊出界": 1, "對手攻擊掛網": 1, "對手送球失誤": 1, 
    "對手攻擊犯規": 1, "對手舉球失誤": 1, "對手舉球犯規": 1, "對手防守犯規": 1, "對手攔網犯規": 1,
    # 失誤
    "發球出界": -1, "發球掛網": -1, "發球犯規": -1,
    "攻擊出界": -1, "攻擊掛網": -1, "攻擊被攔": -1, "攻擊犯規": -1, "觸網": -1, "送球失誤": -1,
    "舉球失誤": -1, "連擊": -1,
    "接發失誤": -1, "接球失誤": -1, "防守噴球": -1, "防守落地": -1, "站位失誤": -1, "防守犯規": -1,
    "攔網觸網": -1, "攔網出界": -1, "攔網失誤": -1, "攔網犯規": -1
}

# 顯示名稱映射 (Button Name -> Stats Name)
ACTION_MAP = {
    "發球": "發球繼續", "攔網": "攔網繼續", "接發A": "接發好球繼續", "接發B": "接發繼續",
    "接球A": "接球好球繼續", "接球B": "接球繼續", "舉球": "舉球繼續", "舉球好球": "舉球好球繼續",
    "攻擊": "攻擊擊球繼續", "處理球": "送球繼續",
    "發球得分": "發球得分", "攻擊得分": "直接得分", "吊球得分": "吊球得分", "後排得分": "直接得分", 
    "快攻得分": "直接得分", "修正得分": "直接得分", "打手得分": "打手得分", "送球得分": "送球得分", "攔網得分": "攔網得分",
    "對手接噴": "對手接噴",
    "發球出界": "發球出界", "發球掛網": "發球掛網", "發球犯規": "發球犯規",
    "攻擊出界": "攻擊出界", "攻擊掛網": "攻擊掛網", "攻擊被攔": "攻擊被攔", "攻擊犯規": "攻擊犯規", "送球失誤": "送球失誤",
    "舉球失誤": "舉球失誤", "連擊": "舉球犯規",
    "接發失誤": "接發失誤", "接球失誤": "接球失誤", "防守犯規": "防守犯規", "站位失誤": "站位失誤",
    "攔網失誤": "攔網失誤", "攔網觸網": "攔網犯規", "攔網犯規": "攔網犯規", "攔網出界": "攔網失誤",
    "觸網": "攻擊犯規", "防守噴球": "接球失誤", "防守落地": "接球失誤"
}

# ==========================================
# 2. Session State
# ==========================================
if 'logs' not in st.session_state: st.session_state.logs = []
if 'my_score' not in st.session_state: st.session_state.my_score = 0
if 'enemy_score' not in st.session_state: st.session_state.enemy_score = 0
if 'current_player' not in st.session_state: st.session_state.current_player = None 
if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False

# [關鍵修正] 使用 reset_id 來控制 Radio 的強制重置
if 'radio_reset_id' not in st.session_state: st.session_state.radio_reset_id = 0

if 'game_meta' not in st.session_state:
    st.session_state.game_meta = {"match_name": "校內聯賽", "date": datetime.now().date(), "opponent": "對手", "set": 1}

if 'active_lineup' not in st.session_state:
    st.session_state.active_lineup = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB[:7]]

# ==========================================
# 3. 核心邏輯
# ==========================================

def recalculate_scores():
    """ 從頭重算比分 (當編輯紀錄後觸發) """
    temp_my = 0
    temp_opp = 0
    
    # 轉正序計算
    chronological_logs = st.session_state.logs[::-1]
    
    for log in chronological_logs:
        raw_action = log.get("原始動作", log["動作"])
        
        # 判斷效果
        effect = ACTION_EFFECTS.get(raw_action, 0)
        # 修正：對手失誤系列都是我方得分
        if "對手" in raw_action and raw_action in ACTION_EFFECTS:
             effect = 1

        res_str = "繼續"
        score_str = ""
        
        if effect == 1:
            temp_my += 1
            res_str = "得分"
            score_str = f"{temp_my}:{temp_opp}"
        elif effect == -1:
            temp_opp += 1
            res_str = "失誤"
            score_str = f"{temp_my}:{temp_opp}"
            
        log["結果"] = res_str
        log["比分"] = score_str # 若為繼續球，這裡是空字串

    # 更新回 Session State
    st.session_state.logs = chronological_logs[::-1]
    st.session_state.my_score = temp_my
    st.session_state.enemy_score = temp_opp

def log_event(action_key):
    """ 紀錄動作並更新分數 """
    player = st.session_state.current_player
    is_opponent_action = "對手" in action_key
    
    if not player and not is_opponent_action:
        st.toast("⚠️ 請先選擇一位球員！", icon="⚠️")
        return 

    # 取得統計表顯示名稱
    stats_name = ACTION_MAP.get(action_key, action_key)
    if is_opponent_action and action_key not in ["對手接噴"]: 
        stats_name = "對手失誤(總計)"
        final_player = "對手"
    else:
        final_player = player

    if is_opponent_action: st.session_state.current_player = None

    raw_action_name = action_key

    # 預先計算分數 (雖然會重算，但為了 UI 即時性)
    effect = ACTION_EFFECTS.get(action_key, 0)
    score_display = ""
    result_str = "繼續"
    
    if effect == 1:
        st.session_state.my_score += 1
        result_str = "得分"
        score_display = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    elif effect == -1:
        st.session_state.enemy_score += 1
        result_str = "失誤"
        score_display = f"{st.session_state.my_score}:{st.session_state.enemy_score}"

    new_record = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "球員": final_player, 
        "動作": stats_name,
        "原始動作": raw_action_name,
        "結果": result_str,
        "比分": score_display,
    }
    st.session_state.logs.insert(0, new_record)
    
    # [修正] 動作後取消選取 & 強制重置 Radio (透過更改 ID)
    st.session_state.current_player = None
    st.session_state.radio_reset_id += 1 

# ==========================================
# 4. 介面佈局
# ==========================================

col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    meta = st.session_state.game_meta
    st.markdown(f"### 🏆 {meta['match_name']} | 📅 {meta['date']} | 🆚 {meta['opponent']} (G{meta['set']})")

with col_info2:
    if st.button("🔄 新局/歸零", type="secondary", use_container_width=True):
        st.session_state.confirm_reset = True

if st.session_state.confirm_reset:
    with st.chat_message("assistant"):
        st.warning("確定清空？")
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

st.markdown(f"""
<div style="text-align: center; background-color: #f0f2f6; padding: 5px; border-radius: 10px; margin-bottom: 10px;">
    <h1 style="margin:0; font-size: 3.5em;">
        <span style="color: blue">{st.session_state.my_score}</span> : <span style="color: red">{st.session_state.enemy_score}</span>
    </h1>
</div>
""", unsafe_allow_html=True)

with st.expander("⚙️ 設定：比賽與陣容"):
    c0, c1, c2, c3 = st.columns(4)
    st.session_state.game_meta['match_name'] = c0.text_input("比賽", value=st.session_state.game_meta['match_name'])
    st.session_state.game_meta['date'] = c1.date_input("日期", value=st.session_state.game_meta['date'])
    st.session_state.game_meta['opponent'] = c2.text_input("對手", value=st.session_state.game_meta['opponent'])
    st.session_state.game_meta['set'] = c3.number_input("局", min_value=1, value=st.session_state.game_meta['set'])
    
    st.markdown("---")
    roster_options = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB]
    cols_lineup = st.columns(7)
    for i in range(7):
        with cols_lineup[i]:
            def_idx = roster_options.index(st.session_state.active_lineup[i]) if st.session_state.active_lineup[i] in roster_options else 0
            st.session_state.active_lineup[i] = st.selectbox(f"位置 {i+1}", roster_options, index=def_idx, key=f"pos_{i}")

left_panel, right_panel = st.columns([2, 1])

with left_panel:
    # 1. 球員區
    st.subheader("1. 選擇球員")
    p_cols = st.columns(7)
    for idx, player_str in enumerate(st.session_state.active_lineup):
        try:
            parts = player_str.split(" - ")
            num = parts[0]
            name = parts[1].split(" (")[0]
            pos = parts[1].split(" (")[1].replace(")", "")
        except:
            num, name, pos = "?", "?", "?"

        is_selected = (st.session_state.current_player == player_str)
        with p_cols[idx]:
            st.markdown(f"<div class='pos-label'>{pos}</div>", unsafe_allow_html=True)
            if st.button(f"{num}\n{name}", key=f"btn_p_{idx}", type="primary" if is_selected else "secondary", use_container_width=True):
                st.session_state.current_player = None if is_selected else player_str
                st.rerun()

    st.divider()

    # 2. 動作區
    st.subheader("2. 紀錄動作")
    
    # [關鍵修正] 使用 dynamic key 強制重置 Radio Button 回到 index 0
    action_mode = st.radio(
        "動作類別", 
        ["🔵 繼續", "🟢 得分", "🔴 失誤"], 
        horizontal=True,
        key=f"action_radio_{st.session_state.radio_reset_id}", # 每次 ID 改變，元件就會重建並回到預設值
        index=0
    )
    
    if "繼續" in action_mode:
        r1 = st.columns(6)
        r1[0].button("發球", on_click=log_event, args=("發球",), use_container_width=True)
        r1[1].button("攔網", on_click=log_event, args=("攔網",), use_container_width=True)
        r1[2].button("接發A", on_click=log_event, args=("接發A",), use_container_width=True)
        r1[2].button("接發B", on_click=log_event, args=("接發B",), use_container_width=True)
        r1[3].button("接球A", on_click=log_event, args=("接球A",), use_container_width=True)
        r1[3].button("接球B", on_click=log_event, args=("接球B",), use_container_width=True)
        r1[4].button("舉球", on_click=log_event, args=("舉球",), use_container_width=True)
        r1[4].button("舉球好球", on_click=log_event, args=("舉球好球",), use_container_width=True)
        r1[5].button("攻擊", on_click=log_event, args=("攻擊",), use_container_width=True)
        r1[5].button("處理球", on_click=log_event, args=("處理球",), use_container_width=True)
    
    elif "得分" in action_mode:
        s_col1, s_col2, s_col3, s_col4 = st.columns([1, 2, 1, 2])
        with s_col1:
            st.caption("發球")
            st.button("發球得分", on_click=log_event, args=("發球得分",), use_container_width=True)
        with s_col2:
            st.caption("攻擊")
            st.button("攻擊得分", on_click=log_event, args=("攻擊得分",), use_container_width=True)
            c1, c2 = st.columns(2)
            c1.button("吊球得分", on_click=log_event, args=("吊球得分",), use_container_width=True)
            c2.button("打手得分", on_click=log_event, args=("打手得分",), use_container_width=True)
            c1.button("送球得分", on_click=log_event, args=("送球得分",), use_container_width=True)
            c2.button("後排得分", on_click=log_event, args=("後排得分",), use_container_width=True)
        with s_col3:
            st.caption("攔網")
            st.button("攔網得分", on_click=log_event, args=("攔網得分",), use_container_width=True)
        with s_col4:
            st.caption("對手失誤")
            opps = ["對手發球出界", "對手發球掛網", "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", "對手舉球失誤", "對手攔網犯規"]
            for o in opps: st.button(o, on_click=log_event, args=(o,), use_container_width=True)
    
    elif "失誤" in action_mode:
        e_col1, e_col2, e_col3, e_col4, e_col5 = st.columns(5)
        with e_col1:
            st.caption("發球")
            for a in ["發球出界", "發球掛網", "發球犯規"]: st.button(a, on_click=log_event, args=(a,), use_container_width=True)
        with e_col2:
            st.caption("攻擊")
            for a in ["攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "送球失誤"]: st.button(a, on_click=log_event, args=(a,), use_container_width=True)
        with e_col3:
            st.caption("舉球")
            for a in ["舉球失誤", "連擊"]: st.button(a, on_click=log_event, args=(a,), use_container_width=True)
        with e_col4:
            st.caption("防守")
            for a in ["接發失誤", "接球失誤", "站位失誤", "防守犯規"]: st.button(a, on_click=log_event, args=(a,), use_container_width=True)
        with e_col5:
            st.caption("攔網")
            for a in ["攔網觸網", "攔網失誤"]: st.button(a, on_click=log_event, args=(a,), use_container_width=True)

with right_panel:
    st.subheader("📝 紀錄明細")
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        edit_actions = list(ACTION_EFFECTS.keys())
        
        # [關鍵修正] 修復 TypeError: label 參數重複定義的問題
        edited_df = st.data_editor(
            df_logs,
            column_config={
                "球員": st.column_config.SelectboxColumn("球員", options=[f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB] + ["對手"], required=True),
                # 這裡修正了：label 參數不使用關鍵字傳遞，直接作為第一個參數 "動作修正"
                "原始動作": st.column_config.SelectboxColumn("動作修正", options=edit_actions, required=True), 
                "動作": None, 
                "結果": st.column_config.TextColumn("結果", disabled=True),
                "比分": st.column_config.TextColumn("比分", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=250,
            key="log_editor",
            # [新增] on_change 回調，當表格變動時自動觸發重算
            on_change=recalculate_scores
        )
    else:
        st.info("尚無紀錄")

    # --- 統計表 ---
    st.subheader("📊 統計")
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        
        # 1. 取得所有場上球員背號 (依照 active_lineup 順序)
        active_numbers = []
        for p_str in st.session_state.active_lineup:
            try:
                active_numbers.append(p_str.split(" - ")[0])
            except: pass
        
        # 2. 處理資料
        def get_short_name(p_str):
            if "對手" in p_str: return "對手"
            return p_str.split(" - ")[0]
        
        df['ShortName'] = df['球員'].apply(get_short_name)
        stats = df.pivot_table(index='動作', columns='ShortName', aggfunc='size', fill_value=0)
        
        # 3. 強制包含所有場上球員 (Columns)
        for num in active_numbers:
            if num not in stats.columns:
                stats[num] = 0
        
        # 4. [修正] 欄位排序：球員 1~7 -> Total -> 對手 (完全依照附圖)
        final_cols = [n for n in active_numbers if n in stats.columns]
        
        # 先計算 Total (不含對手)
        stats["Total"] = stats[final_cols].sum(axis=1)
        final_cols.append("Total")

        # 最後加入對手 (若有)
        if "對手" in stats.columns:
            final_cols.append("對手")
        
        # 重新排列
        stats = stats.reindex(columns=final_cols, fill_value=0)
        
        # 5. 強制包含所有 Row (ORDERED_ROWS)
        stats = stats.reindex(ORDERED_ROWS, fill_value=0)
        
        # 鋪色
        def color_rows(row):
            idx = row.name
            color = ''
            if "繼續" in idx:
                color = 'background-color: #FFF2CC; color: black' # 黃
            elif "得分" in idx or "對手" in idx:
                color = 'background-color: #D9EAD3; color: black' # 綠
            elif "失誤" in idx or "出界" in idx or "掛網" in idx or "犯規" in idx or "被攔" in idx:
                color = 'background-color: #F4CCCC; color: black' # 紅
            return [color] * len(row)

        st.dataframe(stats.style.apply(color_rows, axis=1), use_container_width=True, height=600)
        
        # Excel 匯出
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            sheet_name = f"G{st.session_state.game_meta['set']}_Stats"
            stats.to_excel(writer, sheet_name=sheet_name)
            wb = writer.book
            ws = writer.sheets[sheet_name]
            
            fmt_y = wb.add_format({'bg_color': '#FFF2CC', 'border': 1})
            fmt_g = wb.add_format({'bg_color': '#D9EAD3', 'border': 1})
            fmt_r = wb.add_format({'bg_color': '#F4CCCC', 'border': 1})
            
            for idx, row_name in enumerate(stats.index):
                row_num = idx + 1
                if "繼續" in row_name: ws.set_row(row_num, None, fmt_y)
                elif "得分" in row_name or "對手" in row_name: ws.set_row(row_num, None, fmt_g)
                elif "失誤" in row_name or "出界" in row_name: ws.set_row(row_num, None, fmt_r)
            
            df_logs.to_excel(writer, sheet_name="Logs", index=False)
            
        fname = f"{st.session_state.game_meta['match_name']}_G{st.session_state.game_meta['set']}.xlsx"
        st.download_button("📥 下載 Excel", data=buffer.getvalue(), file_name=fname)