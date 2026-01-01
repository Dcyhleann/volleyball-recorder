import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. 設定與初始化
# ==========================================
st.set_page_config(layout="wide", page_title="排球比賽紀錄系統")

# 初始化 Session State
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'my_score' not in st.session_state:
    st.session_state.my_score = 0
if 'enemy_score' not in st.session_state:
    st.session_state.enemy_score = 0
if 'current_player' not in st.session_state:
    st.session_state.current_player = None # 用來記錄當前選中的球員

# 預設球員名單 (可依實際情況修改)
PLAYERS = {
    "3": "3 存睿", "12": "12 哲綸", "17": "17 品融", 
    "11": "11 凱威", "7": "7 譽鍇", "13": "13 沈威", 
    "22": "22 恩岳", "18": "18 安絡"
}

# 動作分類 (依照你的 Excel 圖片定義)
ACTIONS = {
    "繼續 (碰球)": ["發球繼續", "接發繼續", "接球繼續", "舉球繼續", "攻擊繼續", "攔網繼續", "送球繼續"],
    "得分 (Win)": ["發球得分", "攻擊得分", "攔網得分", "對手失誤"],
    "失誤 (Loss)": ["發球失誤", "攻擊失誤", "防守失誤", "舉球失誤", "攔網失誤"]
}

# ==========================================
# 2. 核心函數
# ==========================================
def add_log(player, action, effect):
    """
    effect: 'cont' (繼續), 'win' (得分), 'lose' (失分)
    """
    # 邏輯判斷：如果沒選球員，提醒使用者
    if player is None and action != "對手失誤": 
        st.warning("⚠️ 請先點擊上方按鈕選擇球員！")
        return

    # 處理比分變動
    score_snapshot = f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    if effect == 'win':
        st.session_state.my_score += 1
        score_snapshot = f"{st.session_state.my_score}:{st.session_state.enemy_score}" # 更新分數
    elif effect == 'lose':
        st.session_state.enemy_score += 1
        score_snapshot = f"{st.session_state.my_score}:{st.session_state.enemy_score}"

    # 寫入紀錄
    new_log = {
        "時間": datetime.now().strftime("%H:%M:%S"),
        "背號": player if player else "對手", # 若是對手失誤可能沒有特定我方球員
        "動作": action,
        "結果": "得分" if effect == 'win' else "失分" if effect == 'lose' else "繼續",
        "比分": score_snapshot
    }
    st.session_state.logs.append(new_log)
    
    # 紀錄完後，清空選擇的球員，方便下一次操作 (或保留看習慣)
    # st.session_state.current_player = None 

# ==========================================
# 3. 介面佈局
# ==========================================
st.title("🏐 專業排球紀錄表")

# 上方比分板
col_score1, col_score2, col_reset = st.columns([2, 2, 1])
with col_score1:
    st.metric("我方得分 (Home)", st.session_state.my_score)
with col_score2:
    st.metric("敵方得分 (Guest)", st.session_state.enemy_score)
with col_reset:
    if st.button("歸零/新局"):
        st.session_state.logs = []
        st.session_state.my_score = 0
        st.session_state.enemy_score = 0
        st.rerun()

st.markdown("---")

# 使用 columns 將畫面切成 [左：操作區] [右：統計表]
left_panel, right_panel = st.columns([1, 1.2])

# ----------------- 左側：操作區 -----------------
with left_panel:
    st.subheader("1. 選擇球員")
    # 建立球員按鈕網格
    p_cols = st.columns(4)
    for idx, (p_num, p_name) in enumerate(PLAYERS.items()):
        col = p_cols[idx % 4]
        # 如果是當前選中球員，按鈕變色 (利用 type='primary')
        is_selected = (st.session_state.current_player == p_num)
        if col.button(p_name, key=f"p_{p_num}", type="primary" if is_selected else "secondary", use_container_width=True):
            st.session_state.current_player = p_num
            st.rerun()

    # 顯示目前選中的球員
    current_p_name = PLAYERS.get(st.session_state.current_player, "尚未選擇")
    st.info(f"👉 目前操作球員：**{current_p_name}**")

    st.subheader("2. 紀錄動作")
    
    # 分頁籤來節省空間，或者直接列出
    tab1, tab2, tab3 = st.tabs(["🔁 繼續 (Touch)", "🔴 失誤 (Error)", "🟢 得分 (Point)"])

    with tab1: # 繼續
        st.caption("好球延續 / 無得分變動")
        cols = st.columns(3)
        for i, act in enumerate(ACTIONS["繼續 (碰球)"]):
            if cols[i % 3].button(act, use_container_width=True):
                add_log(st.session_state.current_player, act, 'cont')
                st.rerun()

    with tab2: # 失誤
        st.caption("我方失分 / 對方得分")
        cols = st.columns(3)
        for i, act in enumerate(ACTIONS["失誤 (Loss)"]):
            if cols[i % 3].button(act, use_container_width=True):
                add_log(st.session_state.current_player, act, 'lose')
                st.rerun()

    with tab3: # 得分
        st.caption("我方得分")
        cols = st.columns(3)
        for i, act in enumerate(ACTIONS["得分 (Win)"]):
            if cols[i % 3].button(act, use_container_width=True):
                # 特殊處理：對手失誤不需要選我方球員
                p = st.session_state.current_player
                if act == "對手失誤":
                    p = None 
                add_log(p, act, 'win')
                st.rerun()

# ----------------- 右側：統計區 -----------------
with right_panel:
    st.subheader("📊 即時統計 (Excel樣式)")
    
    if len(st.session_state.logs) > 0:
        # 1. 轉換成 DataFrame
        df = pd.DataFrame(st.session_state.logs)
        
        # 2. 製作樞紐分析表 (Pivot Table) 模仿你的 Excel 格式
        # index=動作, columns=背號, values=計數
        pivot_df = df.pivot_table(
            index="動作", 
            columns="背號", 
            values="結果", 
            aggfunc='count', 
            fill_value=0
        )
        
        # 為了讓表格好看，我們可以確保所有球員都在列中 (即使沒數據)
        for p_num in PLAYERS.keys():
            if p_num not in pivot_df.columns:
                pivot_df[p_num] = 0
        # 排序欄位
        pivot_df = pivot_df.reindex(columns=sorted(pivot_df.columns), fill_value=0)

        # 3. 顯示表格
        st.dataframe(pivot_df, use_container_width=True, height=600)
        
        # 4. 下載功能
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載流水帳 CSV", csv, "volleyball_log.csv", "text/csv")
    else:
        st.write("尚未有紀錄，請開始比賽！")

    # 顯示最近 5 筆流水帳，方便確認
    st.subheader("📝 最近紀錄")
    if st.session_state.logs:
        st.table(pd.DataFrame(st.session_state.logs[-5:]))