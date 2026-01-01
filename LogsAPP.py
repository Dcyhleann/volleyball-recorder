import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from datetime import datetime

class VolleyballRecorder:
    def __init__(self, root):
        self.root = root
        self.root.title("排球比賽即時紀錄系統 (專業版 v3.0)")
        self.root.geometry("1400x900")

        # --- 初始化變數 ---
        self.match_date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.opponent = tk.StringVar(value="對手")
        self.set_number = tk.IntVar(value=1)
        self.our_score = tk.IntVar(value=0)
        self.opp_score = tk.IntVar(value=0)
        
        self.selected_player = tk.StringVar()
        self.current_records = []
        
        # 完整球員名單 (資料庫)
        self.full_roster = {
            "1": {"name": "小明", "pos": "舉球"},
            "2": {"name": "大華", "pos": "大砲"},
            "3": {"name": "阿龍", "pos": "大砲"},
            "4": {"name": "小瑋", "pos": "攔中"},
            "5": {"name": "阿強", "pos": "攔中"},
            "6": {"name": "小傑", "pos": "舉對"},
            "7": {"name": "阿文", "pos": "自由"},
            "8": {"name": "板凳A", "pos": "大砲"},
            "9": {"name": "板凳B", "pos": "發球"},
            "10": {"name": "板凳C", "pos": "攔中"},
        }
        
        # 目前場上按鈕對應的背號 (依序對應 Button 1 ~ Button 7)
        # 這裡直接存背號，方便對應
        self.active_slots = ["1", "2", "3", "4", "5", "6", "7"]

        # --- 動作定義 ---
        self.actions_continue = {
            "發球": ["發球"],
            "攔網": ["攔網"],
            "接發": ["接發A", "接發B"],
            "接球": ["接球A", "接球B"],
            "舉球": ["舉球"],
            "攻擊/送球": ["攻擊", "處理球"]
        }
        self.actions_score = {
            "發球": ["發球得分"],
            "攻擊": ["攻擊得分", "吊球得分", "後排得分", "快攻得分", "修正得分"],
            "攔網": ["攔網得分"],
            "對手": [
                "對手發球出界", "對手發球掛網", "對手發球犯規",
                "對手攻擊出界", "對手攻擊掛網", "對手送球失誤", 
                "對手攻擊犯規", "對手舉球失誤", "對手舉球犯規", 
                "對手防守犯規", "對手攔網犯規"
            ]
        }
        self.actions_error = {
            "發球": ["發球出界", "發球掛網", "發球犯規"],
            "攻擊": ["攻擊出界", "攻擊掛網", "攻擊被攔", "攻擊犯規", "觸網"],
            "舉球": ["舉球失誤", "連擊"],
            "防守": ["接發失誤", "接球失誤", "防守噴球", "防守落地"],
            "攔網": ["攔網觸網", "攔網出界"]
        }

        self.setup_ui()

    def setup_ui(self):
        # 1. 頂部設定區
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill="x")

        tk.Label(top_frame, text="日期:").pack(side="left", padx=5)
        tk.Entry(top_frame, textvariable=self.match_date, width=12).pack(side="left")
        tk.Label(top_frame, text="對手:").pack(side="left", padx=5)
        tk.Entry(top_frame, textvariable=self.opponent, width=10).pack(side="left")
        tk.Label(top_frame, text="局數:").pack(side="left", padx=5)
        tk.Entry(top_frame, textvariable=self.set_number, width=5).pack(side="left")

        score_label = tk.Label(top_frame, text=" 比分 ", font=("Arial", 20, "bold"))
        score_label.pack(side="left", padx=20)
        tk.Label(top_frame, textvariable=self.our_score, font=("Arial", 24, "bold"), fg="blue").pack(side="left")
        tk.Label(top_frame, text=" : ", font=("Arial", 24)).pack(side="left")
        tk.Label(top_frame, textvariable=self.opp_score, font=("Arial", 24, "bold"), fg="red").pack(side="left")

        tk.Button(top_frame, text="新局/歸零", command=self.reset_game, bg="orange").pack(side="right", padx=10)
        tk.Button(top_frame, text="匯出 Excel", command=self.save_to_excel, bg="green", fg="white").pack(side="right", padx=10)

        # 2. 主要操作區
        main_pane = tk.PanedWindow(self.root, orient="horizontal")
        main_pane.pack(fill="both", expand=True, padx=5, pady=5)
        left_frame = tk.Frame(main_pane)
        right_frame = tk.Frame(main_pane)
        main_pane.add(left_frame, minsize=800)
        main_pane.add(right_frame)

        # --- 左側：球員選擇區 (修改重點) ---
        # 標題列包含「陣容設定」按鈕
        player_header_frame = tk.Frame(left_frame)
        player_header_frame.pack(fill="x", pady=5)
        
        tk.Label(player_header_frame, text="場上球員 (點擊選取)", font=("Arial", 12, "bold")).pack(side="left")
        
        # [NEW] 管理陣容的按鈕
        tk.Button(player_header_frame, text="⚙️ 設定先發/換人", command=self.open_lineup_settings, 
                  bg="#4a90e2", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=20)

        # 球員按鈕容器
        self.player_buttons_frame = tk.Frame(left_frame)
        self.player_buttons_frame.pack(fill="x", padx=5, pady=5)
        self.refresh_player_buttons()

        # --- 左側：動作按鈕區 ---
        action_container = tk.Frame(left_frame)
        action_container.pack(fill="both", expand=True)

        cont_frame = tk.LabelFrame(action_container, text="繼續 (無分)", fg="blue", font=("Arial", 11, "bold"))
        cont_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.create_grid_buttons(cont_frame, self.actions_continue, "blue")

        score_frame = tk.LabelFrame(action_container, text="得分 (本隊+1)", fg="green", font=("Arial", 11, "bold"))
        score_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)
        self.create_grid_buttons(score_frame, self.actions_score, "green")

        error_frame = tk.LabelFrame(action_container, text="失誤 (對手+1)", fg="red", font=("Arial", 11, "bold"))
        error_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
        self.create_grid_buttons(error_frame, self.actions_error, "red")
        
        action_container.grid_columnconfigure(0, weight=1)
        action_container.grid_columnconfigure(1, weight=1)

        # --- 右側：紀錄與統計 ---
        log_frame = tk.LabelFrame(right_frame, text="紀錄明細 (雙擊編輯)", font=("Arial", 10))
        log_frame.pack(fill="both", expand=True, pady=5)

        cols = ("No", "背號", "動作", "結果", "比分")
        self.tree = ttk.Treeview(log_frame, columns=cols, show="headings", height=15)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=50, anchor="center")
        self.tree.column("動作", width=120)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.on_tree_double_click)

        tk.Button(log_frame, text="刪除選取紀錄", command=self.delete_record, bg="pink").pack(fill="x")

        stats_frame = tk.LabelFrame(right_frame, text="即時統計", font=("Arial", 10))
        stats_frame.pack(fill="both", expand=True, pady=5)
        self.stats_text = tk.Text(stats_frame, width=40, height=20, state="disabled")
        self.stats_text.pack(fill="both", expand=True)
        self.stats_text.tag_config("title", font=("Arial", 10, "bold"), background="#ddd")
        self.stats_text.tag_config("score", foreground="green")
        self.stats_text.tag_config("error", foreground="red")
        self.stats_text.tag_config("cont", foreground="blue")

    # --- [NEW] 陣容管理邏輯 ---
    def open_lineup_settings(self):
        """ 開啟設定視窗，讓使用者指定 7 個按鈕分別是誰 """
        win = tk.Toplevel(self.root)
        win.title("設定場上球員 (換人)")
        win.geometry("400x500")

        tk.Label(win, text="請分配 7 個按鈕對應的球員", font=("Arial", 12)).pack(pady=10)

        # 準備下拉選單的選項 (格式: "背號 - 名字")
        roster_options = [f"{k} - {v['name']} ({v['pos']})" for k, v in self.full_roster.items()]
        
        # 暫存選擇結果的變數
        combo_vars = []
        
        # 建立 7 個下拉選單
        for i in range(7):
            frame = tk.Frame(win)
            frame.pack(fill="x", padx=20, pady=5)
            
            tk.Label(frame, text=f"按鈕 {i+1}:", width=8).pack(side="left")
            
            combo = ttk.Combobox(frame, values=roster_options, state="readonly", width=25)
            combo.pack(side="left")
            
            # 設定預設值 (讀取目前 active_slots)
            current_num = self.active_slots[i] if i < len(self.active_slots) else ""
            # 找到對應的選項文字
            for opt in roster_options:
                if opt.startswith(f"{current_num} -"):
                    combo.set(opt)
                    break
            
            combo_vars.append(combo)

        def save_lineup():
            new_slots = []
            for combo in combo_vars:
                val = combo.get()
                if val:
                    # 從 "1 - 小明 (舉球)" 擷取 "1"
                    num = val.split(" - ")[0]
                    new_slots.append(num)
                else:
                    # 如果沒選，為了防呆，可以塞個空或者保留原值，這裡假設一定要選
                    pass
            
            if len(new_slots) != 7:
                 messagebox.showwarning("提示", "請確保 7 個按鈕都設定了球員 (若無自由球員可重複選別人或設空位)")
                 # 這裡簡單處理，允許存入
            
            self.active_slots = new_slots
            self.refresh_player_buttons() # 更新主畫面
            
            # 自動記錄換人事件 (可選)
            self.log_action("系統", "進行換人/陣容調整", 0)
            
            win.destroy()

        tk.Button(win, text="確認變更", command=save_lineup, bg="#4a90e2", fg="white", font=("Arial", 12)).pack(pady=20)

    def refresh_player_buttons(self):
        """ 根據 active_slots 繪製按鈕，純點擊選取 """
        for widget in self.player_buttons_frame.winfo_children():
            widget.destroy()

        for num in self.active_slots:
            p_data = self.full_roster.get(num, {"name": "空", "pos": "-"})
            text = f"{num}\n{p_data['name']}\n({p_data['pos']})"
            
            btn = tk.Button(self.player_buttons_frame, text=text, width=8, height=3,
                            command=lambda n=num: self.select_player(n))
            btn.pack(side="left", padx=2)

            if self.selected_player.get() == num:
                btn.config(bg="yellow", relief="sunken")
            else:
                btn.config(bg="#f0f0f0", relief="raised")

    def select_player(self, num):
        self.selected_player.set(num)
        self.refresh_player_buttons()

    def create_grid_buttons(self, parent, action_dict, color_theme):
        row_idx = 0
        bg_color = "#e0f7fa" if color_theme == "blue" else ("#e8f5e9" if color_theme == "green" else "#ffebee")

        for category, actions in action_dict.items():
            lbl = tk.Label(parent, text=category, bg="gray", fg="white", width=8)
            lbl.grid(row=row_idx, column=0, padx=1, pady=1, sticky="ns")
            
            btn_frame = tk.Frame(parent)
            btn_frame.grid(row=row_idx, column=1, sticky="w", padx=1, pady=1)
            
            for act_name in actions:
                res_type = 0
                if color_theme == "green": res_type = 1
                if color_theme == "red": res_type = -1
                if "對手" in category: res_type = 1 

                tk.Button(btn_frame, text=act_name, bg=bg_color, width=12,
                          command=lambda a=act_name, r=res_type: self.process_action(a, r)).pack(side="left", padx=1)
            row_idx += 1

    def process_action(self, action_name, result_type):
        player = self.selected_player.get()
        if not player and "對手" not in action_name:
            messagebox.showwarning("操作錯誤", "請先選擇一位球員！")
            return

        if result_type == 1:
            self.our_score.set(self.our_score.get() + 1)
        elif result_type == -1:
            self.opp_score.set(self.opp_score.get() + 1)
        
        self.log_action(player if "對手" not in action_name else "對手", action_name, result_type)

    def log_action(self, player, action, result_type):
        current_score = f"{self.our_score.get()}:{self.opp_score.get()}"
        res_text = "繼續"
        if result_type == 1: res_text = "得分"
        elif result_type == -1: res_text = "失誤"
        
        record = {
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Player": player,
            "Action": action,
            "Result": res_text,
            "Score": current_score,
            "ResultType": result_type
        }
        self.current_records.append(record)
        
        # 顯示在最上面
        self.tree.insert("", 0, values=(
            len(self.current_records), player, action, res_text, current_score
        ))
        self.update_statistics()

    def on_tree_double_click(self, event):
        item_id = self.tree.selection()
        if not item_id: return
        
        item = self.tree.item(item_id)
        vals = item['values']
        
        edit_win = tk.Toplevel(self.root)
        edit_win.title("編輯紀錄")
        
        tk.Label(edit_win, text="背號:").grid(row=0, column=0)
        p_list = list(self.full_roster.keys()) + ["對手"]
        p_combo = ttk.Combobox(edit_win, values=p_list)
        p_combo.set(vals[1])
        p_combo.grid(row=0, column=1)

        tk.Label(edit_win, text="動作:").grid(row=1, column=0)
        all_acts = []
        for d in [self.actions_continue, self.actions_score, self.actions_error]:
            for k, v in d.items():
                all_acts.extend(v)
        a_combo = ttk.Combobox(edit_win, values=all_acts)
        a_combo.set(vals[2])
        a_combo.grid(row=1, column=1)
        
        def save_edit():
            new_p = p_combo.get()
            new_a = a_combo.get()
            self.tree.item(item_id, values=(vals[0], new_p, new_a, vals[3], vals[4]))
            
            # 更新內部 list (簡單版：只透過 list index 反查)
            list_idx = len(self.current_records) - int(vals[0])
            if 0 <= list_idx < len(self.current_records):
                 self.current_records[list_idx]['Player'] = new_p
                 self.current_records[list_idx]['Action'] = new_a
            
            self.update_statistics()
            edit_win.destroy()

        tk.Button(edit_win, text="儲存", command=save_edit).grid(row=3, column=0, columnspan=2)

    def delete_record(self):
        selected = self.tree.selection()
        if not selected: return
        confirm = messagebox.askyesno("確認", "確定要刪除此紀錄嗎？")
        if confirm:
            self.tree.delete(selected)

    def update_statistics(self):
        self.stats_text.config(state="normal")
        self.stats_text.delete(1.0, "end")
        
        stats = {}
        for r in self.current_records:
            p = r['Player']
            if p == "對手": continue
            if p not in stats: stats[p] = {"score": 0, "error": 0, "cont": 0}
            
            if r['ResultType'] == 1: stats[p]['score'] += 1
            elif r['ResultType'] == -1: stats[p]['error'] += 1
            else: stats[p]['cont'] += 1
            
        header = f"{'背號':<6}{'得分':<6}{'失誤':<6}{'繼續':<6}\n"
        self.stats_text.insert("end", header, "title")
        self.stats_text.insert("end", "-"*30 + "\n")
        
        for p, d in stats.items():
            line_start = f"{p:<8}"
            self.stats_text.insert("end", line_start)
            self.stats_text.insert("end", f"{d['score']:<8}", "score")
            self.stats_text.insert("end", f"{d['error']:<8}", "error")
            self.stats_text.insert("end", f"{d['cont']:<8}\n", "cont")
        self.stats_text.config(state="disabled")

    def reset_game(self):
        ans = messagebox.askyesno("新局", "確定要開始新的一局嗎？")
        if ans:
            self.our_score.set(0)
            self.opp_score.set(0)
            self.current_records = []
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.update_statistics()

    def save_to_excel(self):
        if not self.current_records:
            messagebox.showinfo("提示", "無紀錄")
            return
        df = pd.DataFrame(self.current_records)
        filename = f"{self.match_date.get()}_{self.opponent.get()}_Set{self.set_number.get()}.xlsx"
        filename = filename.replace("/", "").replace(":", "")
        try:
            df.to_excel(filename, index=False)
            messagebox.showinfo("成功", f"存檔成功: {filename}")
        except Exception as e:
            messagebox.showerror("錯誤", f"存檔失敗: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VolleyballRecorder(root)
    root.mainloop()