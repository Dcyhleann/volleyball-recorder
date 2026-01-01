import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 初始化資料 (如果沒有紀錄過，就創立空的)
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'my_score' not in st.session_state:
    st.session_state.my_score = 0
if 'enemy_score' not in st.session_state:
    st.session_state.enemy_score = 0

st.title("🏐 排球比賽紀錄神器")

# 2.顯示目前比分
col1, col2 = st.columns(2)
with col1:
    st.metric("我方得分", st.session_state.my_score)
with col2:
    st.metric("對方得分", st.session_state.enemy_score)

st.divider()

# 3. 紀錄操作區
st.subheader("快速紀錄")

# 選擇球員 (可以用 selectbox 或按鈕)
player = st.selectbox("選擇球員", ["#1 隊長", "#7 舉球", "#10 大砲", "#12 自由", "對方失誤"])

# 動作按鈕區 (使用 columns 排版讓按鈕並排)
c1, c2, c3 = st.columns(3)

def add_log(action, point_change):
    # 紀錄當下時間、球員、動作、當下比分
    log = {
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Player": player,
        "Action": action,
        "Score": f"{st.session_state.my_score}:{st.session_state.enemy_score}"
    }
    
    # 分數變動邏輯
    if point_change == "win":
        st.session_state.my_score += 1
        log['Result'] = "得分"
    elif point_change == "lose":
        st.session_state.enemy_score += 1
        log['Result'] = "失分"
    
    st.session_state.logs.append(log)
    st.rerun() # 重新整理畫面更新比分

with c1:
    if st.button("攻擊得分 🏐", use_container_width=True):
        add_log("Attack Kill", "win")
    if st.button("攔網得分 ✋", use_container_width=True):
        add_log("Block Point", "win")

with c2:
    if st.button("發球得分 🎯", use_container_width=True):
        add_log("Ace", "win")
    if st.button("對手失誤 🤪", use_container_width=True):
        add_log("Opp Error", "win")

with c3:
    if st.button("攻擊出界/掛網 ❌", use_container_width=True):
        add_log("Attack Error", "lose")
    if st.button("發球失誤 ❌", use_container_width=True):
        add_log("Serve Error", "lose")

st.divider()

# 4. 資料檢視與下載
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    st.dataframe(df.tail(5)) # 顯示最近5筆
    
    # 下載成 CSV
    csv = df.to_csv(index=False).encode('utf-8-sig') # utf-8-sig 解決中文亂碼
    st.download_button(
        label="📥 下載比賽紀錄 CSV",
        data=csv,
        file_name='volleyball_match.csv',
        mime='text/csv',
    )