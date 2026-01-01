import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- 1. 頁面基礎設定 (必須在第一行) ---
st.set_page_config(page_title="排球戰績紀錄", layout="wide")

# --- 2. 初始化 Session State (記憶體) ---
# Streamlit 每次按按鈕都會重跑，所以要用 session_state 把資料存起來
if 'records' not in st.session_state:
    st.session_state.records = []
if 'our_score' not in st.session_state:
    st.session_state.our_score = 0
if 'opp_score' not in st.session_state:
    st.session_state.opp_score = 0
if 'active_slots' not in st.session_state:
    # 預設場上 7 個位置的球員名字 (可修改)
    st.session_state.active_slots = ["舉球-小明", "大砲-大華", "大砲-阿龍", "攔中-小瑋", "攔中-阿強", "舉對-小傑", "自由-阿文"]

# --- 3. 側邊欄：設定與換人 ---
with st.sidebar:
    st.header("⚙️ 比賽與陣容設定")
    
    # A. 比賽資訊
    match_date = st.text_input("日期", value=datetime.now().strftime("%Y-%m-%d"))
    opponent = st.text_input("對手", value="台積電")
    set_number = st.number_input("局數", min_value=1, value=1)
    
    st.divider()
    
    # B. 換人設定 (修改這 7 格會直接變更主畫面選項)
    st.subheader("📋 場上 7 人名單 (可隨時修改)")
    st.info("直接修改下方名字即可換人")
    
    new_slots = []
    for i in range(7):
        # 預設值抓目前的 session_state
        val = st.text_input(f"位置 {i+1}", value=st.session_state.active_slots[i], key=f"slot_{i}")
        new_slots.append(val)
    st.session_state.active_slots = new_slots # 更新名單

    st.divider()
    
    # C. 功能按鈕
    if st.button("🔄 新局 / 歸零 (小心誤按)", type="primary"):
        st.session_state.records = []
        st.session_state.our_score = 0
        st.session_state.opp_score = 0
        st.rerun()

# --- 4. 主畫面：比分板 ---
st.markdown(f"""
    <div style="text-align: center; padding: 10px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
        <h2 style="margin:0;">局數: {set_number} | 對手: {opponent}</h2>
        <h1 style="font-size: 60px; margin:0;">
            <span style="color: blue;">{st.session_state.our_score}</span> : 
            <span style="color: red;">{st.session_state.opp_score}</span>
        </h1>
    </div>
""", unsafe_allow_html=True)

# --- 5. 主畫面：操作區 ---
# 用 Columns 分隔左右：左邊操作(2)，右邊紀錄(1)
col_left, col_right = st.columns([2, 1])

with col_left:
    # --- A. 選擇球員 (單選區，解決長按問題) ---
    st.subheader("1. 選擇球員")
    # 使用 horizontal radio 讓它橫向排列，適合平板點擊
    # 為了讓"對手"也能選，我們暫時把它加進選項，或是由後面的按鈕處理
    # 這裡我們只列出本隊球員
    selected_player = st.radio("點擊球員以選取:", st.session_state.active_slots, horizontal=True)

    st.divider()
    
    # --- B. 動作按鈕 (依照你的Grid需求) ---
    st.subheader("2. 執行動作")
    
    # 定義動作處理函數
    def process_action(player, action, result_type):
        # result_type: 0=繼續, 1=得分, -1=失誤
        
        # 邏輯判斷
        final_player = player
        if "對手" in action: # 如果是按了對手失誤
            final_player = "對手"
            result_type = 1 # 對手失誤 = 我方得分
        
        # 加分
        if result_type == 1:
            st.session_state.our_score += 1
        elif result_type == -1:
            st.session_state.opp_score += 1
            
        # 紀錄
        score_str = f"{st.session_state.our_score}:{st.session_state.opp_score}"
        res_text = "得分" if result_type == 1 else ("失誤" if result_type == -1 else "繼續")
        
        new_record = {
            "時間": datetime.now().strftime("%H:%M:%S"),
            "球員": final_player,
            "動作": action,
            "結果": res_text,
            "比分": score_str,
            "Type": result_type # 用於統計
        }
        # 新增到最前面 (index 0)
        st.session_state.records.insert(0, new_record)
    
    # --- 建立按鈕 Grid ---
    # 使用 3 個 Column 分區: 繼續(藍) / 得分(綠) / 失誤(紅)
    c1, c2, c3 = st.columns(3)
    
    # 區塊 1: 繼續 (無分)
    with c1:
        st.info("🔵 繼續 (無分)")
        acts_cont = ["發球", "接發A", "接發B", "接球A", "接球B", "舉球", "攔網", "攻擊", "處理球"]
        for act in acts_cont:
            if st.button(act, key=f"cont_{act}", use_container_width=True):
                process_action(selected_player, act, 0)
                st.rerun()

    # 區塊 2: 得分 (本隊+1) - 包含對手失誤
    with c2:
        st.success("🟢 得分 (本隊+1)")
        # 本隊得分動作
        acts_score = ["發球得分", "攻擊得分", "吊球得分", "後排得分", "快攻得分", "修正得分", "攔網得分"]
        for act in acts_score:
            if st.button(act, key=f"score_{act}", use_container_width=True):
                process_action(selected_player, act, 1)
                st.rerun()
        
        st.markdown("---")
        st.write("🔻 **對手失誤 (我方得分)**")
        # 對手失誤動作 (你的11項)
        acts_opp_err = [
            "對手發球出界", "對手發球掛網", "對手發球犯規",
            "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", 
            "對手攻擊犯規", "對手舉球失誤", "對手舉球犯規", 
            "對手防守犯規", "對手攔網犯規"
        ]
        for act in acts_opp_err:
            if st.button(act, key=f"opp_{act}", use_container_width=True):
                process_action("對手", act, 1) # 這裡 player 會被覆寫為 "對手"
                st.rerun()

    # 區塊 3: 失誤 (對手+1)
    with c3:
        st.error("🔴 失誤 (對手+1)")
        acts_err = [
            "發球出界", "發球掛網", "發球犯規",
            "攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "觸網",
            "舉球失誤", "連擊",
            "接發失誤", "接球失誤", "防守噴球", "防守落地",
            "攔網觸網", "攔網出界"
        ]
        for act in acts_err:
            if st.button(act, key=f"err_{act}", use_container_width=True):
                process_action(selected_player, act, -1)
                st.rerun()

with col_right:
    # --- 右側：紀錄與統計 ---
    st.subheader("📊 即時紀錄")
    
    # 1. 刪除上一筆
    if st.button("↩️ 刪除最新一筆紀錄"):
        if st.session_state.records:
            removed = st.session_state.records.pop(0) # 移除第一筆
            # 嘗試回扣分數 (簡單邏輯)
            if removed["結果"] == "得分":
                st.session_state.our_score = max(0, st.session_state.our_score - 1)
            elif removed["結果"] == "失誤":
                st.session_state.opp_score = max(0, st.session_state.opp_score - 1)
            st.success(f"已刪除: {removed['動作']}")
            st.rerun()

    # 2. 顯示表格
    if st.session_state.records:
        df = pd.DataFrame(st.session_state.records)
        # 只顯示重要欄位
        st.dataframe(df[["球員", "動作", "結果", "比分"]], height=400, use_container_width=True)
        
        # 3. 匯出 Excel
        # 建立 Excel Bytes
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        excel_data = output.getvalue()
        
        file_name = f"{match_date}_{opponent}_Set{set_number}.xlsx"
        st.download_button(
            label="📥 下載 Excel 檔案",
            data=excel_data,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.write("目前尚無紀錄")