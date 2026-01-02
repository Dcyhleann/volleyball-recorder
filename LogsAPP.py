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
    /* 全局字體優化 */
    .big-score {
        font-size: 40px;
        font-weight: 900;
        text-align: center;
        line-height: 1.2;
    }
    .score-sep {
        color: #888;
        font-size: 30px;
        vertical-align: middle;
    }
    
    /* 按鈕樣式 */
    div.stButton > button {
        min-height: 60px; /* 增加高度讓觸控更好按 */
        font-size: 16px;
        font-weight: bold;
        border-radius: 8px;
        border: 1px solid #ccc;
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
        font-size: 12px;
        color: #666;
        margin-bottom: -5px;
    }
    
    /* Radio 按鈕優化 (橫向選單) */
    div[role="radiogroup"] {
        flex-direction: row;
        width: 100%;
        justify-content: center;
    }
    div[data-testid="stRadio"] > label {
        display: none;
    }
    div[role="radiogroup"] label {
        background-color: #f8f9fa;
        padding: 12px 0;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        flex-grow: 1;
        text-align: center;
        margin: 0 4px;
        font-size: 18px;
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #e6f3ff; /* 選中時的淺藍底 */
        border-color: #0d6efd;
        color: #0d6efd;
        font-weight: bold;
        box-shadow: 0 0 5px rgba(13, 110, 253, 0.3);
    }
    
    /* 欄位標題置中 */
    div[data-testid="column"] > div {
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 資料與定義
# ==========================================

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

# 統計表順序
ORDERED_ROWS = [
    # 繼續
    "發球繼續", "攔網繼續", "接發繼續", "接發好球繼續", 
    "接球繼續", "接球好球繼續", "舉球繼續", "舉球好球繼續", 
    "攻擊擊球繼續", "送球繼續",
    # 得分
    "發球得分", "直接得分", "對手接噴", "打手得分", "吊球得分", "送球得分", "攔網得分", 
    "對手失誤(總計)", 
    # 失誤
    "發球出界", "發球掛網", "發球犯規", 
    "攻擊出界", "攻擊掛網", "攻擊被攔", "送球失誤", "攻擊犯規", 
    "舉球失誤", "舉球犯規", 
    "接發失誤", "站位失誤", "接球失誤", "防守犯規", 
    "攔網失誤", "攔網犯規"
]

# 用於計算總分的清單
SCORE_ROWS_LIST = ["發球得分", "直接得分", "對手接噴", "打手得分", "吊球得分", "送球得分", "攔網得分"]
ERROR_ROWS_LIST = ["發球出界", "發球掛網", "發球犯規", "攻擊出界", "攻擊掛網", "攻擊被攔", "送球失誤", "攻擊犯規", 
                   "舉球失誤", "舉球犯規", "接發失誤", "站位失誤", "接球失誤", "防守犯規", "攔網失誤", "攔網犯規"]

# 動作分數影響
ACTION_EFFECTS = {
    "發球": 0, "攔網": 0, "接發A": 0, "接發B": 0, "接球A": 0, "接球B": 0, 
    "舉球": 0, "舉球好球": 0, "攻擊": 0, "處理球": 0,
    "發球得分": 1, "攻擊得分": 1, "吊球得分": 1, "後排得分": 1, "快攻得分": 1, "修正得分": 1, "打手得分": 1, "送球得分": 1, "攔網得分": 1,
    "對手發球出界": 1, "對手發球掛網": 1, "對手發球犯規": 1, "對手攻擊出界": 1, "對手攻擊掛網": 1, "對手送球失誤": 1, 
    "對手攻擊犯規": 1, "對手舉球失誤": 1, "對手舉球犯規": 1, "對手防守犯規": 1, "對手攔網犯規": 1,
    "發球出界": -1, "發球掛網": -1, "發球犯規": -1,
    "攻擊出界": -1, "攻擊掛網": -1, "攻擊被攔": -1, "攻擊犯規": -1, "觸網": -1, "送球失誤": -1,
    "舉球失誤": -1, "連擊": -1,
    "接發失誤": -1, "接球失誤": -1, "防守噴球": -1, "防守落地": -1, "站位失誤": -1, "防守犯規": -1,
    "攔網觸網": -1, "攔網出界": -1, "攔網失誤": -1, "攔網犯規": -1
}

# 顯示名稱映射
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
# 2. Session State 初始化
# ==========================================
if 'logs' not in st.session_state: st.session_state.logs = []
if 'my_score' not in st.session_state: st.session_state.my_score = 0
if 'enemy_score' not in st.session_state: st.session_state.enemy_score = 0
if 'current_player' not in st.session_state: st.session_state.current_player = None 
if 'confirm_reset' not in st.session_state: st.session_state.confirm_reset = False
if 'radio_reset_id' not in st.session_state: st.session_state.radio_reset_id = 0

if 'game_meta' not in st.session_state:
    st.session_state.game_meta = {"match_name": "校內聯賽", "date": datetime.now().date(), "opponent": "對手", "set": 1}

if 'active_lineup' not in st.session_state:
    st.session_state.active_lineup = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB[:7]]

if 'seen_players' not in st.session_state:
    initial_players = []
    for p_str in st.session_state.active_lineup:
        try:
            short = p_str.split(" - ")[0]
            initial_players.append(short)
        except: pass
    st.session_state.seen_players = initial_players

# ==========================================
# 3. 核心邏輯
# ==========================================

def update_seen_players(player_str):
    if "對手" in player_str: return
    try:
        short = player_str.split(" - ")[0]
        if short not in st.session_state.seen_players:
            st.session_state.seen_players.append(short)
    except: pass

def recalculate_scores():
    temp_my = 0
    temp_opp = 0
    chronological_logs = st.session_state.logs[::-1]
    
    for log in chronological_logs:
        raw_action = log.get("原始動作", log.get("動作", ""))
        update_seen_players(log["球員"])
        
        effect = ACTION_EFFECTS.get(raw_action, 0)
        if "對手" in raw_action and raw_action in ACTION_EFFECTS: effect = 1

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
        log["比分"] = score_str
        
        stats_name = ACTION_MAP.get(raw_action, raw_action)
        if "對手" in raw_action and raw_action not in ["對手接噴"]:
            stats_name = "對手失誤(總計)"
        
        log["動作"] = stats_name

    st.session_state.logs = chronological_logs[::-1]
    st.session_state.my_score = temp_my
    st.session_state.enemy_score = temp_opp

def log_event(action_key):
    player = st.session_state.current_player
    is_opponent_action = "對手" in action_key
    
    if not player and not is_opponent_action:
        st.toast("⚠️ 請先選擇一位球員！", icon="⚠️")
        return 

    if player: update_seen_players(player)

    stats_name = ACTION_MAP.get(action_key, action_key)
    if is_opponent_action and action_key not in ["對手接噴"]: 
        stats_name = "對手失誤(總計)"
        final_player = "對手"
    else:
        final_player = player

    if is_opponent_action: st.session_state.current_player = None

    new_record = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "球員": final_player, 
        "動作": stats_name,
        "原始動作": action_key,
        "結果": "",
        "比分": "",
    }
    
    st.session_state.logs.insert(0, new_record)
    recalculate_scores()
    st.session_state.current_player = None
    st.session_state.radio_reset_id += 1 

# ==========================================
# 4. 介面佈局
# ==========================================

# --- [修正 1] Top Layout (整合比分與資訊) ---
# 比例: 資訊(3) - 比分(2) - 按鈕(1)
c_meta, c_score, c_btn = st.columns([3, 2, 1], gap="small")

with c_meta:
    meta = st.session_state.game_meta
    st.markdown(f"**{meta['match_name']}** | {meta['date']}")
    st.markdown(f"🆚 **{meta['opponent']}** (Set {meta['set']})")

with c_score:
    # 緊湊比分顯示
    st.markdown(
        f"<div class='big-score'>"
        f"<span style='color:#0d6efd'>{st.session_state.my_score}</span>"
        f"<span class='score-sep'> : </span>"
        f"<span style='color:#dc3545'>{st.session_state.enemy_score}</span>"
        f"</div>", 
        unsafe_allow_html=True
    )

with c_btn:
    if st.button("🔄 重置", type="secondary", use_container_width=True):
        st.session_state.confirm_reset = True

# 確認重置視窗
if st.session_state.confirm_reset:
    with st.chat_message("assistant"):
        st.warning("⚠️ 確定清空資料？")
        cols = st.columns(2)
        if cols[0].button("✅ 是"):
            st.session_state.logs = []
            st.session_state.my_score = 0
            st.session_state.enemy_score = 0
            st.session_state.current_player = None
            st.session_state.seen_players = []
            for p_str in st.session_state.active_lineup:
                try: st.session_state.seen_players.append(p_str.split(" - ")[0])
                except: pass
            st.session_state.confirm_reset = False
            st.rerun()
        if cols[1].button("❌ 否"):
            st.session_state.confirm_reset = False
            st.rerun()

# --- 設定區 (摺疊) ---
with st.expander("⚙️ 比賽資訊 / 換人設定"):
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
            new_val = st.selectbox(f"Pos {i+1}", roster_options, index=def_idx, key=f"pos_{i}", label_visibility="collapsed")
            if new_val != st.session_state.active_lineup[i]:
                st.session_state.active_lineup[i] = new_val
                update_seen_players(new_val)

# --- 主操作區 ---
# 1. 球員選擇
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

st.write("") # Spacer

# 2. 動作紀錄區
action_mode = st.radio(
    "Mode", ["🔵 繼續", "🟢 得分", "🔴 失誤"], 
    horizontal=True, 
    key=f"radio_{st.session_state.radio_reset_id}",
    label_visibility="collapsed"
)

# [修正 4] 六欄排版 Helper
def draw_action_grid(col_labels, btn_configs):
    """
    col_labels: list of 6 strings for header (optional)
    btn_configs: list of 6 lists, each inner list contains tuples (btn_label, action_key)
    """
    cols = st.columns(6)
    # 顯示標題 (可選)
    for i, title in enumerate(col_labels):
        cols[i].caption(title)
        
    for i in range(6):
        with cols[i]:
            buttons = btn_configs[i]
            if not buttons:
                st.write("") # Empty placeholder
            else:
                for label, key in buttons:
                    st.button(label, on_click=log_event, args=(key,), use_container_width=True)

# 定義六大類標題
grid_titles = ["發球", "攔網", "接發", "接球(防守)", "舉球", "攻擊"]

if "繼續" in action_mode:
    # 欄位對應: 0發球, 1攔網, 2接發, 3接球, 4舉球, 5攻擊
    btns = [
        [("發球", "發球")],                         # Col 0
        [("攔網", "攔網")],                         # Col 1
        [("接發A", "接發A"), ("接發B", "接發B")],   # Col 2
        [("接球A", "接球A"), ("接球B", "接球B")],   # Col 3
        [("舉球", "舉球"), ("舉好", "舉球好球")],    # Col 4
        [("攻擊", "攻擊"), ("處理", "處理球")]       # Col 5
    ]
    draw_action_grid(grid_titles, btns)

elif "得分" in action_mode:
    # 得分頁面：接發/接球/舉球 通常沒有直接得分 (除非吊球算在攻擊)
    btns = [
        [("發球得分", "發球得分")],               # Col 0: 發球
        [("攔網得分", "攔網得分")],               # Col 1: 攔網
        [],                                     # Col 2: 接發 (空)
        [],                                     # Col 3: 接球 (空)
        [],                                     # Col 4: 舉球 (空)
        [("攻擊得分", "攻擊得分"), ("吊球得分", "吊球得分"), 
         ("打手得分", "打手得分"), ("送球得分", "送球得分"),
         ("後排得分", "後排得分")]                # Col 5: 攻擊
    ]
    draw_action_grid(grid_titles, btns)
    
    st.markdown("---")
    st.caption("🔻 對手失誤 (我方得分)")
    # 對手失誤區 (獨立寬欄)
    oc1, oc2, oc3, oc4 = st.columns(4)
    opps = ["對手發球出界", "對手發球掛網", "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", "對手舉球失誤", "對手攔網犯規"]
    for i, o in enumerate(opps):
        with [oc1, oc2, oc3, oc4][i % 4]:
            st.button(o, on_click=log_event, args=(o,), use_container_width=True)

elif "失誤" in action_mode:
    btns = [
        [("發球出界", "發球出界"), ("發球掛網", "發球掛網"), ("發球犯規", "發球犯規")], # Col 0
        [("攔網觸網", "攔網觸網"), ("攔網失誤", "攔網失誤")],                         # Col 1
        [("接發失誤", "接發失誤")],                                                # Col 2
        [("防守失誤", "接球失誤"), ("防守犯規", "防守犯規"), ("站位失誤", "站位失誤")], # Col 3
        [("舉球失誤", "舉球失誤"), ("連擊", "連擊")],                               # Col 4
        [("攻擊出界", "攻擊出界"), ("攻擊掛網", "攻擊掛網"), 
         ("攻擊被攔", "攻擊被攔"), ("攻擊犯規", "攻擊犯規"), ("送球失誤", "送球失誤")]  # Col 5
    ]
    draw_action_grid(grid_titles, btns)

st.write("") 

# --- [修正 2] 統計表摺疊區 ---
with st.expander("📊 統計數據 & 紀錄明細", expanded=False):
    
    # Tab 1: 紀錄明細
    st.subheader("📝 紀錄明細 (可編輯/刪除)")
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        edit_actions = list(ACTION_EFFECTS.keys())
        
        edited_df = st.data_editor(
            df_logs,
            column_config={
                "球員": st.column_config.SelectboxColumn("球員", options=[f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB] + ["對手"], required=True),
                "原始動作": st.column_config.SelectboxColumn("動作修正", options=edit_actions, required=True), 
                "動作": None, 
                "結果": st.column_config.TextColumn("結果", disabled=True),
                "比分": st.column_config.TextColumn("比分", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=300,
            key="log_editor",
            num_rows="dynamic"
        )
        
        new_logs = edited_df.to_dict('records')
        if new_logs != st.session_state.logs:
            st.session_state.logs = new_logs
            recalculate_scores()
            st.rerun()
    else:
        st.info("尚無紀錄")

    st.markdown("---")

    # Tab 2: 統計表
    st.subheader("📈 數據統計")
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        
        def get_short_name(p_str):
            if "對手" in p_str: return "對手"
            return p_str.split(" - ")[0]
        
        df['ShortName'] = df['球員'].apply(get_short_name)
        stats = df.pivot_table(index='動作', columns='ShortName', aggfunc='size', fill_value=0)
        
        ordered_cols = []
        for p in st.session_state.seen_players:
            ordered_cols.append(p)
            if p not in stats.columns: stats[p] = 0
        
        final_cols = [c for c in ordered_cols]
        stats["Total"] = stats[[c for c in final_cols if c in stats.columns]].sum(axis=1)
        final_cols.append("Total")
        if "對手" in stats.columns: final_cols.append("對手")
            
        stats = stats.reindex(columns=final_cols, fill_value=0)
        stats = stats.reindex(ORDERED_ROWS, fill_value=0)
        
        # [修正 3] 計算個人總得分/總失誤
        # 篩選得分列 (Score Rows)
        score_mask = stats.index.isin(SCORE_ROWS_LIST)
        stats.loc["個人得分總和"] = stats[score_mask].sum()
        
        # 篩選失誤列 (Error Rows)
        error_mask = stats.index.isin(ERROR_ROWS_LIST)
        stats.loc["個人失分總和"] = stats[error_mask].sum()
        
        # 鋪色
        def color_rows(row):
            idx = row.name
            color = ''
            if idx in ["個人得分總和", "個人失分總和"]:
                color = 'background-color: #cfe2f3; color: black; font-weight: bold' # 藍色加總
            elif "繼續" in idx:
                color = 'background-color: #FFF2CC; color: black'
            elif "得分" in idx or "對手" in idx:
                color = 'background-color: #D9EAD3; color: black'
            elif "失誤" in idx or "出界" in idx or "掛網" in idx or "犯規" in idx or "被攔" in idx:
                color = 'background-color: #F4CCCC; color: black'
            return [color] * len(row)

        st.dataframe(stats.style.apply(color_rows, axis=1), use_container_width=True, height=800)
        
        # Excel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            sheet_name = f"G{st.session_state.game_meta['set']}_Stats"
            stats.to_excel(writer, sheet_name=sheet_name)
            wb = writer.book
            ws = writer.sheets[sheet_name]
            
            fmt_y = wb.add_format({'bg_color': '#FFF2CC', 'border': 1})
            fmt_g = wb.add_format({'bg_color': '#D9EAD3', 'border': 1})
            fmt_r = wb.add_format({'bg_color': '#F4CCCC', 'border': 1})
            fmt_b = wb.add_format({'bg_color': '#CFE2F3', 'border': 1, 'bold': True})
            
            for idx, row_name in enumerate(stats.index):
                row_num = idx + 1
                if row_name in ["個人得分總和", "個人失分總和"]: ws.set_row(row_num, None, fmt_b)
                elif "繼續" in row_name: ws.set_row(row_num, None, fmt_y)
                elif "得分" in row_name or "對手" in row_name: ws.set_row(row_num, None, fmt_g)
                elif "失誤" in row_name or "出界" in row_name: ws.set_row(row_num, None, fmt_r)
            
            df_logs.to_excel(writer, sheet_name="Logs", index=False)
            
        fname = f"{st.session_state.game_meta['match_name']}_G{st.session_state.game_meta['set']}.xlsx"
        st.download_button("📥 下載 Excel", data=buffer.getvalue(), file_name=fname)