import streamlit as st
import pandas as pd
from datetime import datetime
import io
import time

# ==========================================
# 0. 頁面設定與 CSS 優化
# ==========================================
st.set_page_config(layout="wide", page_title="排球比賽紀錄系統 Pro", initial_sidebar_state="expanded")

# 自訂 CSS 讓按鈕分區更有辨識度
st.markdown("""
    <style>
    /* 得分區按鈕微調 (綠色系意象) */
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stMarkdownContainer"] p:contains("得分")) button {
        border-color: #28a745 !important;
    }
    /* 失誤區按鈕微調 (紅色系意象) */
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stMarkdownContainer"] p:contains("失誤")) button {
        border-color: #dc3545 !important;
    }
    /* 選中球員的樣式 */
    div.stButton > button:active {
        background-color: #FFD700 !important;
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 資料結構與常數定義
# ==========================================

# 完整球員名單庫 (這裡可以填入整隊名單)
ROSTER_DB = [
    {"背號": "1", "姓名": "舉球員A", "位置": "舉球"},
    {"背號": "2", "姓名": "大砲B", "位置": "大砲"},
    {"背號": "3", "姓名": "大砲C", "位置": "大砲"},
    {"背號": "4", "姓名": "攔中D", "位置": "攔中"},
    {"背號": "5", "姓名": "攔中E", "位置": "攔中"},
    {"背號": "6", "姓名": "舉對F", "位置": "舉對"},
    {"背號": "7", "姓名": "自由G", "位置": "自由"},
    {"背號": "8", "姓名": "替補H", "位置": "大砲"},
    {"背號": "9", "姓名": "替補I", "位置": "發球"},
]

# 動作清單 (用於下拉選單與排序)
ACTIONS_CONTINUE = ["發球", "攔網", "接發A", "接發B", "接球A", "接球B", "舉球", "攻擊", "處理球"]
ACTIONS_SCORE = ["發球得分", "攻擊得分", "吊球得分", "後排得分", "快攻得分", "修正得分", "攔網得分", 
                 "對手發球出界", "對手發球掛網", "對手發球犯規", "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", 
                 "對手攻擊犯規", "對手舉球失誤", "對手舉球犯規", "對手防守犯規", "對手攔網犯規"]
ACTIONS_ERROR = ["發球出界", "發球掛網", "發球犯規", 
                 "攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "觸網",
                 "舉球失誤", "連擊", 
                 "接發失誤", "接球失誤", "防守噴球", "防守落地", 
                 "攔網觸網", "攔網出界"]

ALL_ACTIONS = ACTIONS_CONTINUE + ACTIONS_SCORE + ACTIONS_ERROR

# ==========================================
# 2. Session State 初始化
# ==========================================
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'my_score' not in st.session_state:
    st.session_state.my_score = 0
if 'enemy_score' not in st.session_state:
    st.session_state.enemy_score = 0
if 'current_player' not in st.session_state:
    st.session_state.current_player = None # 格式: "背號 - 姓名"
if 'confirm_reset' not in st.session_state:
    st.session_state.confirm_reset = False

# 比賽資訊 (預設值)
if 'game_meta' not in st.session_state:
    st.session_state.game_meta = {
        "date": datetime.now().date(),
        "opponent": "對手球隊",
        "set": 1
    }

# 先發陣容 (Active Lineup) - 對應畫面上的 7 顆按鈕
# 預設對應 ROSTER_DB 的前7人
if 'active_lineup' not in st.session_state:
    st.session_state.active_lineup = [
        f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB[:7]
    ]

# ==========================================
# 3. 核心邏輯函數
# ==========================================
def log_event(action, type_code):
    """
    type_code: 0=Continue, 1=Score(My), -1=Error(Enemy Score)
    """
    # 9. Debug: 檢查是否選取球員 (對手失誤除外)
    player = st.session_state.current_player
    is_opponent_error = "對手" in action
    
    if not player and not is_opponent_error:
        st.toast("⚠️ 請先選擇一位球員！", icon="⚠️")
        return # 中斷執行，不紀錄

    # 處理球員名稱
    final_player = player if not is_opponent_error else "對手"
    # 如果是對手失誤，不用選球員，清除選取狀態避免混淆
    if is_opponent_error:
        st.session_state.current_player = None

    # 計算比分
    if type_code == 1: # 得分 or 對手失誤
        st.session_state.my_score += 1
        result_str = "得分"
    elif type_code == -1: # 失誤
        st.session_state.enemy_score += 1
        result_str = "失誤"
    else:
        result_str = "繼續"

    current_score = f"{st.session_state.my_score}:{st.session_state.enemy_score}"

    # 新增紀錄 (插入到最前面，符合需求 6)
    new_record = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "球員": final_player, # 格式: "1 - 名字 (位置)"
        "動作": action,
        "結果": result_str,
        "比分": current_score,
        "原始分數": (st.session_state.my_score, st.session_state.enemy_score) # 用於除錯或進階統計
    }
    st.session_state.logs.insert(0, new_record)
    
    # 動作完成後，取消球員選取 (User 習慣)
    # st.session_state.current_player = None 

# ==========================================
# 4. 介面佈局
# ==========================================

# --- 頂部資訊列 (需求 1: 顯示在外) ---
col_info1, col_info2 = st.columns([3, 1])
with col_info1:
    st.markdown(f"### 📅 {st.session_state.game_meta['date']} | 🆚 {st.session_state.game_meta['opponent']} | 第 {st.session_state.game_meta['set']} 局")

with col_info2:
    # 需求 2: 歸零彈窗確認
    if st.button("🔄 新局/歸零", type="secondary", use_container_width=True):
        st.session_state.confirm_reset = True

if st.session_state.confirm_reset:
    with st.chat_message("assistant"):
        st.warning("確定要清空所有紀錄與比分嗎？(請確認已匯出檔案)")
        c1, c2 = st.columns(2)
        if c1.button("✅ 確定清空"):
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
<div style="text-align: center; background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
    <h1 style="margin:0; font-size: 3em;">
        <span style="color: blue">{st.session_state.my_score}</span> : <span style="color: red">{st.session_state.enemy_score}</span>
    </h1>
</div>
""", unsafe_allow_html=True)

# --- 設定區 (摺疊) ---
with st.expander("⚙️ 設定：比賽資訊與替補換人"):
    c1, c2, c3 = st.columns(3)
    st.session_state.game_meta['date'] = c1.date_input("日期", value=st.session_state.game_meta['date'])
    st.session_state.game_meta['opponent'] = c2.text_input("對手", value=st.session_state.game_meta['opponent'])
    st.session_state.game_meta['set'] = c3.number_input("局數", min_value=1, value=st.session_state.game_meta['set'])
    
    st.markdown("---")
    st.subheader("📋 場上陣容設定 (需求 11)")
    st.info("在此修改下拉選單，主畫面的按鈕會同步更新 (支援替補換人)")
    
    # 產生完整名單選項
    roster_options = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB]
    
    # 7 個位置的設定 (動態生成)
    cols_lineup = st.columns(7)
    for i in range(7):
        with cols_lineup[i]:
            # 預設值防呆
            default_idx = roster_options.index(st.session_state.active_lineup[i]) if st.session_state.active_lineup[i] in roster_options else 0
            new_val = st.selectbox(f"位置 {i+1}", roster_options, index=default_idx, key=f"pos_{i}")
            # 更新 session state
            st.session_state.active_lineup[i] = new_val

# --- 主操作區 (左右分欄) ---
left_panel, right_panel = st.columns([2, 1])

with left_panel:
    # 1. 球員按鈕區 (需求 10: 顯示位置, 需求 11: 只顯示7個)
    st.subheader("1. 選擇球員")
    p_cols = st.columns(7)
    for idx, player_str in enumerate(st.session_state.active_lineup):
        # player_str 格式: "1 - 名字 (位置)"
        # 解析出顯示用的 Label: "1\n名字\n(位置)"
        try:
            parts = player_str.split(" - ")
            num = parts[0]
            name_pos = parts[1].split(" (")
            name = name_pos[0]
            pos = name_pos[1].replace(")", "")
            display_label = f"{num}\n{name}\n({pos})"
        except:
            display_label = player_str

        # 檢查是否被選中
        is_selected = (st.session_state.current_player == player_str)
        
        with p_cols[idx]:
            if st.button(display_label, key=f"btn_p_{idx}", type="primary" if is_selected else "secondary", use_container_width=True):
                if is_selected:
                    st.session_state.current_player = None
                else:
                    st.session_state.current_player = player_str
                st.rerun()

    st.divider()

    # 2. 動作按鈕區 (Grid Layout)
    st.subheader("2. 紀錄動作")
    
    # 依照需求 3, 4, 5 分區
    tab_cont, tab_score, tab_error = st.tabs(["🔵 繼續 (無分)", "🟢 得分 (本隊+1)", "🔴 失誤 (對手+1)"])

    # --- 繼續區 (需求 3: 六區) ---
    with tab_cont:
        r1 = st.columns(6)
        # 發球(1)
        r1[0].button("發球", key="c_sv", on_click=log_event, args=("發球", 0), use_container_width=True)
        # 攔網(1)
        r1[1].button("攔網", key="c_bk", on_click=log_event, args=("攔網", 0), use_container_width=True)
        # 接發(2)
        r1[2].button("接發A", key="c_rv1", on_click=log_event, args=("接發A", 0), use_container_width=True)
        r1[2].button("接發B", key="c_rv2", on_click=log_event, args=("接發B", 0), use_container_width=True)
        # 接球(2)
        r1[3].button("接球A", key="c_dg1", on_click=log_event, args=("接球A", 0), use_container_width=True)
        r1[3].button("接球B", key="c_dg2", on_click=log_event, args=("接球B", 0), use_container_width=True)
        # 舉球(1)
        r1[4].button("舉球", key="c_st", on_click=log_event, args=("舉球", 0), use_container_width=True)
        # 攻擊/送球(2)
        r1[5].button("攻擊", key="c_at", on_click=log_event, args=("攻擊", 0), use_container_width=True)
        r1[5].button("處理球", key="c_fb", on_click=log_event, args=("處理球", 0), use_container_width=True)

    # --- 得分區 (需求 4: 四區) ---
    with tab_score:
        s_col1, s_col2, s_col3, s_col4 = st.columns([1, 2, 1, 2])
        
        # 發球(1)
        with s_col1:
            st.caption("發球")
            st.button("發球得分", key="s_sv", on_click=log_event, args=("發球得分", 1), use_container_width=True)
        
        # 攻擊(5)
        with s_col2:
            st.caption("攻擊")
            st.button("攻擊得分", key="s_at1", on_click=log_event, args=("攻擊得分", 1), use_container_width=True)
            c_sub1, c_sub2 = st.columns(2)
            c_sub1.button("吊球得分", key="s_at2", on_click=log_event, args=("吊球得分", 1), use_container_width=True)
            c_sub2.button("後排得分", key="s_at3", on_click=log_event, args=("後排得分", 1), use_container_width=True)
            c_sub1.button("快攻得分", key="s_at4", on_click=log_event, args=("快攻得分", 1), use_container_width=True)
            c_sub2.button("修正得分", key="s_at5", on_click=log_event, args=("修正得分", 1), use_container_width=True)

        # 攔網(1)
        with s_col3:
            st.caption("攔網")
            st.button("攔網得分", key="s_bk", on_click=log_event, args=("攔網得分", 1), use_container_width=True)

        # 對手(11) (完全按照附圖)
        with s_col4:
            st.caption("對手失誤 (我方得分)")
            opp_errs = [
                "對手發球出界", "對手發球掛網", "對手發球犯規",
                "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", 
                "對手攻擊犯規", "對手舉球失誤", "對手舉球犯規", 
                "對手防守犯規", "對手攔網犯規"
            ]
            # 用 selectbox 或 expander 避免佔用太大空間，或者依需求全部列出
            # 這裡為了快速點擊，使用密集排列
            for oe in opp_errs:
                st.button(oe, key=f"s_opp_{oe}", on_click=log_event, args=(oe, 1), use_container_width=True)

    # --- 失誤區 (需求 5: 五區) ---
    with tab_error:
        e_col1, e_col2, e_col3, e_col4, e_col5 = st.columns(5)
        
        # 發球(3)
        with e_col1:
            st.caption("發球")
            for act in ["發球出界", "發球掛網", "發球犯規"]:
                st.button(act, key=f"e_sv_{act}", on_click=log_event, args=(act, -1), use_container_width=True)
        
        # 攻擊(5)
        with e_col2:
            st.caption("攻擊")
            for act in ["攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "觸網"]:
                st.button(act, key=f"e_at_{act}", on_click=log_event, args=(act, -1), use_container_width=True)
        
        # 舉球(2)
        with e_col3:
            st.caption("舉球")
            for act in ["舉球失誤", "連擊"]:
                st.button(act, key=f"e_st_{act}", on_click=log_event, args=(act, -1), use_container_width=True)
        
        # 防守(4)
        with e_col4:
            st.caption("防守")
            for act in ["接發失誤", "接球失誤", "防守噴球", "防守落地"]:
                st.button(act, key=f"e_df_{act}", on_click=log_event, args=(act, -1), use_container_width=True)
        
        # 攔網(2)
        with e_col5:
            st.caption("攔網")
            for act in ["攔網觸網", "攔網出界"]:
                st.button(act, key=f"e_bk_{act}", on_click=log_event, args=(act, -1), use_container_width=True)

with right_panel:
    # --- 紀錄明細 (需求 7: 可編輯, 下拉選單) ---
    st.subheader("📝 紀錄明細")
    
    if st.session_state.logs:
        df_logs = pd.DataFrame(st.session_state.logs)
        
        # 設定編輯欄位
        # 需求 7: 背號、動作為下拉選單；比分與結果設為唯讀(或提醒)
        # 由於 data_editor 無法完全鎖定特定 column (只能 disabled)，我們將 Result/Score 設為 disabled
        
        # 準備球員選單
        player_options = [f"{p['背號']} - {p['姓名']} ({p['位置']})" for p in ROSTER_DB] + ["對手"]
        
        edited_df = st.data_editor(
            df_logs,
            column_config={
                "球員": st.column_config.SelectboxColumn("球員", options=player_options, required=True),
                "動作": st.column_config.SelectboxColumn("動作", options=ALL_ACTIONS, required=True),
                "結果": st.column_config.TextColumn("結果", disabled=True), # 限制編輯
                "比分": st.column_config.TextColumn("比分", disabled=True), # 限制編輯
                "原始分數": None # 隱藏此欄位
            },
            hide_index=True,
            use_container_width=True,
            height=300,
            key="editor"
        )
        
        # 簡單同步回 session state (注意：若修改動作導致結果改變，這裡不會自動重算比分，這是 data_editor 的限制，通常需要複雜的 callback)
        st.session_state.logs = edited_df.to_dict('records')
        
    else:
        st.info("尚無紀錄")

    # --- 即時統計 (需求 8: 分區鋪色) ---
    st.subheader("📊 即時統計")
    if st.session_state.logs:
        df = pd.DataFrame(st.session_state.logs)
        
        # 簡單樞紐分析
        if not df.empty:
            # 為了排序，我們先過濾出有數據的動作
            stats = df.groupby(['動作', '球員']).size().unstack(fill_value=0)
            
            # 依照 繼續/得分/失誤 順序排列 index
            # 建立一個排序用的 key
            def sort_key(action):
                if action in ACTIONS_SCORE: return 1
                if action in ACTIONS_ERROR: return 2
                return 0 # Continue
            
            sorted_index = sorted(stats.index, key=lambda x: (sort_key(x), x))
            stats = stats.reindex(sorted_index)
            
            # 顯示表格 (這裡用 style 進行簡單鋪色)
            # 綠色: 得分, 紅色: 失誤, 藍色: 繼續
            def highlight_rows(row):
                if row.name in ACTIONS_SCORE:
                    return ['background-color: #d4edda'] * len(row) # 淺綠
                elif row.name in ACTIONS_ERROR:
                    return ['background-color: #f8d7da'] * len(row) # 淺紅
                else:
                    return ['background-color: #e2e3e5'] * len(row) # 淺灰/藍

            st.dataframe(stats.style.apply(highlight_rows, axis=1), use_container_width=True, height=400)
            
            # --- Excel 匯出 (需求 1: 檔名包含資訊) ---
            fname = f"{st.session_state.game_meta['date']}_{st.session_state.game_meta['opponent']}_Set{st.session_state.game_meta['set']}.xlsx"
            
            # 寫入 Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                # Sheet 1: 統計
                stats.to_excel(writer, sheet_name=f"Set{st.session_state.game_meta['set']}_Stats")
                # Sheet 2: 明細
                df.to_excel(writer, sheet_name=f"Set{st.session_state.game_meta['set']}_Logs", index=False)
                
            st.download_button(
                label="📥 下載 Excel",
                data=buffer.getvalue(),
                file_name=fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )