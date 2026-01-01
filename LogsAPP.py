import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# 0. 全域設定與常數
# ==========================================
st.set_page_config(layout="wide", page_title="排球比賽紀錄系統 Pro")

# 依照 Excel 圖片定義的統計表顯示順序
ACTION_ORDER = [
    "發球繼續", "發球得分", "發球失誤",
    "攔網繼續", "攔網得分", "攔網失誤",
    "接發繼續", "接發好球繼續", "接發失誤",
    "接球繼續", "接球好球繼續", "接球失誤",
    "舉球繼續", "舉球好球繼續", "舉球失誤",
    "攻擊繼續", "攻擊得分", "攻擊失誤", "攻擊被攔",
    "送球繼續", "送球失誤",
    "防守犯規", "站位失誤" # 其他
]

# 預設球員名單 (可透過介面修改)
DEFAULT_PLAYERS = [
    {"背號": "3", "姓名": "存睿"},
    {"背號": "12", "姓名": "哲綸"},
    {"背號": "17", "姓名": "品融"},
    {"背號": "11", "姓名": "凱威"},
    {"背號": "7", "姓名": "譽鍇"},
    {"背號": "13", "姓名": "沈威"},
    {"背號": "22", "姓名": "恩岳"},
    {"背號": "18", "姓名": "安絡"}
]

# ==========================================
# 1. Session State 初始化
# ==========================================
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'my_score' not in st.session_state:
    st.session_state.my_score = 0
if 'enemy_score' not in st.session_state:
    st.session_state.enemy_score = 0
if 'current_player' not in st.session_state:
    st.session_state.current_player = None
# 比賽資訊設定
if 'game_info' not in st.session_state:
    st.session_state.game_info = {
        "date": datetime.now().date(),
        "opponent": "對手球隊",
        "set_num": 1,
        "players": DEFAULT_PLAYERS
    }

# ==========================================
# 2. 側邊欄/頂部設定區 (需求 11)
# ==========================================
with st.expander("⚙️ 比賽與球員設定 (點擊展開修改)", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.game_info['date'] = st.date_input("比賽日期", value=st.session_state.game_info['date'])
    with c2:
        st.session_state.game_info['opponent'] = st.text_input("對手名稱", value=st.session_state.game_info['opponent'])
    with c3:
        st.session_state.game_info['set_num'] = st.number_input("目前局數", min_value=1, value=st.session_state.game_info['set_num'])
    
    st.write("球員名單管理 (直接修改表格內容)：")
    # 讓使用者可以編輯球員名單
    edited_players = st.data_editor(
        st.session_state.game_info['players'], 
        num_rows="dynamic", # 允許新增/刪除球員
        key="player_editor"
    )
    # 更新球員名單
    st.session_state.game_info['players'] = edited_players

# 取得當前球員清單 (整理成按鈕要用的格式)
current_player_list = [f"{p['背號']} {p['姓名']}" for p in st.session_state.game_info['players']]
player_dict = {p['背號']: f"{p['背號']} {p['姓名']}" for p in st.session_state.game_info['players']}

# ==========================================
# 3. 核心邏輯函數
# ==========================================
def add_log(player_num, action, effect):
    # 1. 檢查是否選取球員 (對手失誤除外)
    if player_num is None and action != "對手失誤":
        st.toast("⚠️ 請先選擇球員！", icon="⚠️")
        return

    # 2. 處理比分
    current_my = st.session_state.my_score
    current_enemy = st.session_state.enemy_score
    
    score_snapshot = "" # 預設為空，只有得分改變才填入 (需求 8)
    
    if effect == 'win':
        st.session_state.my_score += 1
        score_snapshot = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    elif effect == 'lose':
        st.session_state.enemy_score += 1
        score_snapshot = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    
    # 3. 新增紀錄
    new_log = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "背號": player_num if player_num else "對手",
        "動作": action,
        "結果": "得分" if effect == 'win' else "失分" if effect == 'lose' else "繼續",
        "比分": score_snapshot
    }
    st.session_state.logs.append(new_log)
    
    # 4. 紀錄完後取消選擇球員 (需求 2)
    st.session_state.current_player = None 

# ==========================================
# 4. 主畫面佈局
# ==========================================
# 比分板
col_score1, col_score2, col_reset = st.columns([2, 2, 1])
with col_score1:
    st.metric("我方 (Home)", st.session_state.my_score)
with col_score2:
    st.metric(f"{st.session_state.game_info['opponent']} (Guest)", st.session_state.enemy_score)
with col_reset:
    # 需求 6: 歸零確認
    if st.button("🔄 新局/歸零", type="secondary"):
        with st.popover("確定要清空資料嗎？"):
            st.write("這將會刪除目前所有紀錄與比分。")
            if st.button("⚠️ 確認刪除", type="primary"):
                st.session_state.logs = []
                st.session_state.my_score = 0
                st.session_state.enemy_score = 0
                st.session_state.current_player = None
                st.rerun()

st.divider()

# 切分左右區塊：左邊操作 (70%)，右邊統計 (30%) (需求 5)
left_panel, right_panel = st.columns([7, 3])

# ==========================================
# 左側：操作區
# ==========================================
with left_panel:
    # --- 1. 球員選擇區 ---
    # 依照目前設定的球員產生按鈕
    cols = st.columns(6) # 一排6個
    for idx, p_data in enumerate(st.session_state.game_info['players']):
        p_num = p_data['背號']
        p_name = p_data['姓名']
        label = f"{p_num}\n{p_name}"
        
        # 判斷是否選中 (需求 1: 紅色亮起)
        is_selected = (st.session_state.current_player == p_num)
        
        with cols[idx % 6]:
            if st.button(label, key=f"btn_{p_num}", type="primary" if is_selected else "secondary", use_container_width=True):
                if is_selected:
                    st.session_state.current_player = None # 再次點擊取消
                else:
                    st.session_state.current_player = p_num
                st.rerun()

    st.markdown("---")

    # --- 2. 動作按鈕區 ---
    # 定義動作按鈕的排版
    tab_cont, tab_score, tab_error = st.tabs(["🔁 繼續 (Touch)", "🟢 得分 (Point)", "🔴 失誤 (Error)"])

    def action_btn(label, action_name, effect):
        if st.button(label, use_container_width=True):
            add_log(st.session_state.current_player, action_name, effect)
            st.rerun()

    with tab_cont:
        c1, c2, c3, c4 = st.columns(4)
        with c1: action_btn("發球繼續", "發球繼續", "cont"); action_btn("送球繼續", "送球繼續", "cont")
        with c2: action_btn("接發球", "接發繼續", "cont"); action_btn("接發到位", "接發好球繼續", "cont")
        with c3: action_btn("一般接球", "接球繼續", "cont"); action_btn("接球到位", "接球好球繼續", "cont")
        with c4: action_btn("舉球", "舉球繼續", "cont"); action_btn("舉球到位", "舉球好球繼續", "cont")
        
        st.caption("攻擊/攔網")
        c5, c6, c7, c8 = st.columns(4)
        with c5: action_btn("攻擊繼續", "攻擊繼續", "cont")
        with c6: action_btn("攔網繼續", "攔網繼續", "cont")
        
    with tab_score:
        c1, c2, c3 = st.columns(3)
        with c1: action_btn("攻擊得分 🏐", "攻擊得分", "win")
        with c2: action_btn("攔網得分 ✋", "攔網得分", "win")
        with c3: action_btn("發球得分 🎯", "發球得分", "win")
        st.caption("其他")
        if st.button("對手失誤 (送分)", use_container_width=True):
            add_log(None, "對手失誤", "win")
            st.rerun()

    with tab_error:
        c1, c2, c3 = st.columns(3)
        with c1: action_btn("發球失誤", "發球失誤", "lose"); action_btn("接發失誤", "接發失誤", "lose")
        with c2: action_btn("攻擊失誤", "攻擊失誤", "lose"); action_btn("攻擊被攔", "攻擊被攔", "lose")
        with c3: action_btn("舉球/防守失誤", "舉球失誤", "lose"); action_btn("站位/犯規", "防守犯規", "lose")
        # 補上其他可能的失誤
        action_btn("攔網失誤", "攔網失誤", "lose")

    st.markdown("### 📝 紀錄明細 (可直接修改)")
    # --- 3. 紀錄編輯區 (需求 7, 8, 9) ---
    if len(st.session_state.logs) > 0:
        # 將 logs 轉為 DataFrame
        df_logs = pd.DataFrame(st.session_state.logs)
        
        # 使用 data_editor 讓使用者可以編輯、刪除
        # num_rows="dynamic" 允許增刪行
        edited_df = st.data_editor(
            df_logs, 
            use_container_width=True, 
            height=300,  # 固定高度，可捲動 (需求 7)
            num_rows="dynamic",
            column_config={
                "比分": st.column_config.TextColumn("比分", disabled=False)
            },
            key="log_editor" 
        )
        
        # 關鍵：將編輯後的資料寫回 session_state，讓統計表連動更新 (需求 9)
        # 注意：雖然這裡直接覆蓋，但比分欄位的邏輯不會自動重算（這很複雜），
        # 但統計數據會根據「動作」和「背號」重新計算。
        st.session_state.logs = edited_df.to_dict('records')
    else:
        st.info("尚無紀錄")

# ==========================================
# 右側：統計區 (需求 3, 4, 5)
# ==========================================
with right_panel:
    st.subheader("📊 即時統計")
    
    if len(st.session_state.logs) > 0:
        df = pd.DataFrame(st.session_state.logs)
        
        # 1. 建立樞紐分析表
        # index=動作, columns=背號
        pivot = df.pivot_table(
            index="動作", 
            columns="背號", 
            values="時間", 
            aggfunc='count', 
            fill_value=0
        )
        
        # 2. 確保所有「目前設定的球員」都在欄位中 (依照背號順序)
        current_player_nums = [p['背號'] for p in st.session_state.game_info['players']]
        for p in current_player_nums:
            if p not in pivot.columns:
                pivot[p] = 0
        
        # 欄位排序 (依照設定的順序)
        existing_cols = [c for c in current_player_nums if c in pivot.columns]
        pivot = pivot[existing_cols] # 只保留我們名單內的，並照順序
        
        # 3. 確保所有「定義好的動作」都在列中 (依照 Excel 圖片順序)
        pivot = pivot.reindex(ACTION_ORDER, fill_value=0)
        
        # 4. 移除完全沒有數據且不在 ACTION_ORDER 裡的雜項 (Optional)
        # 但為了符合你的固定順序需求，我們主要依賴 reindex
        
        # 5. 計算「個人得分總和」與「個人失分總和」 (需求 4)
        # 定義哪些動作算得分，哪些算失分
        score_actions = ["發球得分", "攻擊得分", "攔網得分"] # 根據你的邏輯增減
        error_actions = ["發球失誤", "接發失誤", "接球失誤", "舉球失誤", "攻擊失誤", "攻擊被攔", "攔網失誤", "送球失誤", "防守犯規", "站位失誤"]
        
        # 計算總和
        total_score_row = pivot.loc[pivot.index.intersection(score_actions)].sum()
        total_error_row = pivot.loc[pivot.index.intersection(error_actions)].sum()
        
        # 將總和加回 DataFrame 底部
        pivot.loc['個人得分總和'] = total_score_row
        pivot.loc['個人失分總和'] = total_error_row
        
        # 6. 顯示表格
        st.dataframe(pivot, use_container_width=True, height=700)
        
        # ==========================================
        # Excel 下載區 (需求 10)
        # ==========================================
        # 產生 Excel 檔案 (包含兩個 Sheet)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: 統計表
            pivot.to_excel(writer, sheet_name='統計數據')
            # Sheet 2: 流水帳
            df.to_excel(writer, sheet_name='詳細流水帳', index=False)
            
        st.download_button(
            label="📥 下載 Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"volleyball_stats_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    else:
        st.caption("等待紀錄中...")