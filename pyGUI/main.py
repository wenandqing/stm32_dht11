# -*- coding: gbk -*-
import tkinter as tk
from tkinter import ttk, messagebox
import pymysql
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading

plt.rcParams["font.family"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams['axes.unicode_minus'] = False

# 数据库连接配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'data_user',
    'password': 'data456',
    'database': 'TempHumidityDB',
    'charset': 'utf8mb4'
}

# 温湿度报警阈值配置
TEMP_MAX = 30.00
TEMP_MIN = 20.00
HUM_MAX = 90.00
HUM_MIN = 20.00

# 工业风格配色
COLORS = {
    'bg_dark': '#ececec',
    'bg_light': '#fcfcfc',
    'accent': '#0078d4',
    'success': '#289e3c',
    'warning': '#e69100',
    'danger': '#dd3333',
    'text': '#222222',
    'text_dim': '#555555'
}


class LoginWindow:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title('温湿度监控系统 - 登录')
        self.window.geometry('400x300')
        self.window.resizable(False, False)
        self.window.configure(bg=COLORS['bg_dark'])
        
        tk.Label(self.window, text='温湿度采集管理系统', font=('微软雅黑', 18), 
                 fg=COLORS['text'], bg=COLORS['bg_dark']).pack(pady=30)
        tk.Label(self.window, text='用户名', fg=COLORS['text'], bg=COLORS['bg_dark']).pack()
        self.entry_username = tk.Entry(self.window, width=30, bg=COLORS['bg_light'], 
                                        fg=COLORS['text'], insertbackground='white')
        self.entry_username.pack(pady=5)
        tk.Label(self.window, text='密码', fg=COLORS['text'], bg=COLORS['bg_dark']).pack()
        self.entry_password = tk.Entry(self.window, show='*', width=30, 
                                        bg=COLORS['bg_light'], fg=COLORS['text'], insertbackground='white')
        self.entry_password.pack(pady=5)
        
        tk.Button(self.window, text='登录', command=self.login, width=15,
                  bg=COLORS['accent'], fg='white', relief='flat').pack(pady=20)
        self.window.mainloop()
    
    def login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, role FROM User WHERE username=%s AND password=%s", 
                          (username, password))
            result = cursor.fetchone()
            conn.close()
            if result:
                self.window.destroy()
                MainWindow(result[0], result[1], result[2])
            else:
                messagebox.showerror('错误', '用户名或密码错误')
        except Exception as e:
            messagebox.showerror('错误', f'数据库连接失败: {e}')

class GaugeChart:
    """仪表盘组件"""
    def __init__(self, parent, title, color, width=200, height=150):
        self.fig = Figure(figsize=(width/100, height/100), dpi=100, facecolor=COLORS['bg_light'])
        self.ax = self.fig.add_subplot(111, projection='polar')
        self.ax.set_facecolor(COLORS['bg_light'])
        self.title = title
        self.color = color
        self.value = 0
        self.init_plot()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack()
    
    def init_plot(self):
        self.ax.set_theta_zero_location('N')
        self.ax.set_theta_direction(-1)
        self.ax.set_ylim(0, 100)
        self.ax.set_yticks([25, 50, 75, 100])
        self.ax.set_yticklabels(['25', '50', '75', '100'], color=COLORS['text_dim'])
        self.ax.set_xticklabels([])
        self.ax.spines['polar'].set_color(COLORS['text_dim'])
        self.ax.set_title(self.title, color=COLORS['text'], fontsize=10, pad=10)
    
    def update(self, value):
        self.value = min(max(value, 0), 100)
        self.ax.clear()
        self.init_plot()
        theta = self.value / 100 * 180
        self.ax.bar([0], [self.value], width=0.3, color=self.color, alpha=0.7)
        self.ax.plot([0, 0], [0, self.value], color=self.color, linewidth=3)
        self.ax.text(0, self.value + 5, f'{self.value:.1f}', ha='center', va='bottom',
                     color=self.color, fontsize=12, fontweight='bold')
        self.canvas.draw()

class AlertPanel:
    """报警信息面板"""
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent, bg=COLORS['bg_light'], relief='sunken', bd=1)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        tk.Label(self.frame, text='实时预警', font=('微软雅黑', 12, 'bold'),
                 fg=COLORS['warning'], bg=COLORS['bg_light']).pack(pady=5)
        
        self.listbox = tk.Listbox(self.frame, bg=COLORS['bg_dark'], fg=COLORS['danger'],
                                   font=('微软雅黑', 9), selectbackground=COLORS['accent'],
                                   relief='flat', height=8)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.clear_btn = tk.Button(self.frame, text='清除预警', command=self.clear_alerts,
                                    bg=COLORS['bg_dark'], fg=COLORS['text'],
                                    relief='flat', cursor='hand2')
        self.clear_btn.pack(pady=5)
        
        self.alerts = []
    
    def add_alert(self, alert_msg, alert_type='warning'):
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.alerts.insert(0, f'[{timestamp}] {alert_msg}')
        self.listbox.insert(0, f'[{timestamp}] {alert_msg}')
        
        while self.listbox.size() > 50:
            self.listbox.delete(tk.END)
    
    def clear_alerts(self):
        self.alerts.clear()
        self.listbox.delete(0, tk.END)

class MainWindow:
    def __init__(self, user_id, username, role):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.window = tk.Tk()
        self.window.title(f'温湿度监控系统 - 欢迎 {username}({role})')
        self.window.geometry('1400x800')
        self.window.configure(bg=COLORS['bg_dark'])
        
        self.page_now = 1
        self.page_size = 20
        self.is_operating = False
        
        self.create_menu()
        self.create_main_layout()
        self.load_data()
        
        self.refresh_timer = None
        self.schedule_refresh()
        
        self.window.mainloop()
    
    def schedule_refresh(self):
        self.refresh_timer = self.window.after(300000, self.refresh_data)#每5min刷新一次数据
    
    def refresh_data(self):
        # 不在操作时才刷新
        if not self.is_operating:
            self.load_data()
        self.schedule_refresh()
    
    def create_menu(self):
        menubar = tk.Menu(self.window, bg=COLORS['bg_dark'], fg=COLORS['text'])
        
        # ---------- 数据管理菜单 ----------
        data_menu = tk.Menu(menubar, tearoff=0, bg=COLORS['bg_light'], fg=COLORS['text'])
        data_menu.add_command(label='数据查询', command=self.show_data_query)
        # 数据录入：admin 和 operator 可用
        if self.role in ('admin', 'operator'):
            data_menu.add_command(label='数据录入', command=self.show_data_add)
        data_menu.add_command(label='数据统计', command=self.show_data_stats)
        # 阈值设置：admin 和 operator 可用
        if self.role in ('admin', 'operator'):
            data_menu.add_command(label='阈值设置', command=self.set_threshold_win)
        menubar.add_cascade(label='数据管理', menu=data_menu)
        
        # ---------- 设备管理菜单 ----------
        device_menu = tk.Menu(menubar, tearoff=0, bg=COLORS['bg_light'], fg=COLORS['text'])
        device_menu.add_command(label='设备列表', command=self.show_device_list)
        # 添加/修改设备：admin 和 operator 可用
        if self.role in ('admin', 'operator'):
            device_menu.add_command(label='添加/修改设备', command=self.show_device_edit)
        menubar.add_cascade(label='设备管理', menu=device_menu)
        
        # ---------- 报警管理菜单 ----------
        alert_menu = tk.Menu(menubar, tearoff=0, bg=COLORS['bg_light'], fg=COLORS['text'])
        alert_menu.add_command(label='报警记录', command=self.show_alert_list)
        menubar.add_cascade(label='报警管理', menu=alert_menu)
        
        # ---------- 系统管理（仅 admin）----------
        if self.role == 'admin':
            user_menu = tk.Menu(menubar, tearoff=0, bg=COLORS['bg_light'], fg=COLORS['text'])
            user_menu.add_command(label='用户管理', command=self.show_user_manage)
            menubar.add_cascade(label='系统管理', menu=user_menu)
        
        menubar.add_command(label='退出', command=self.window.quit)
        self.window.config(menu=menubar)
    
    def create_main_layout(self):
        # 顶部标题栏
        title_frame = tk.Frame(self.window, bg=COLORS['accent'], height=50)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text='温湿度实时监控看板', font=('微软雅黑', 18, 'bold'),
                fg='white', bg=COLORS['accent']).pack(pady=10)

        # 主左右分割
        main_paned = tk.PanedWindow(self.window, orient=tk.HORIZONTAL, bg=COLORS['bg_dark'],
                                    sashrelief='sunken', sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ========== 左侧 ==========
        left_frame = tk.Frame(main_paned, bg=COLORS['bg_dark'])
        main_paned.add(left_frame, width=400)

        gauge_frame = tk.LabelFrame(left_frame, text='实时数据', font=('微软雅黑', 10, 'bold'),
                                    fg=COLORS['text'], bg=COLORS['bg_dark'], relief='ridge', bd=1)
        gauge_frame.pack(fill=tk.X, pady=(0, 10))

        self.temp_label = tk.Label(gauge_frame, text='-- ℃', font=('Arial', 36, 'bold'),
                                    fg=COLORS['danger'], bg=COLORS['bg_dark'])
        self.temp_label.pack(pady=10)
        tk.Label(gauge_frame, text='温度', font=('微软雅黑', 10),
                fg=COLORS['text_dim'], bg=COLORS['bg_dark']).pack()

        self.hum_label = tk.Label(gauge_frame, text='-- %', font=('Arial', 36, 'bold'),
                                fg=COLORS['success'], bg=COLORS['bg_dark'])
        self.hum_label.pack(pady=10)
        tk.Label(gauge_frame, text='湿度', font=('微软雅黑', 10),
                fg=COLORS['text_dim'], bg=COLORS['bg_dark']).pack()

        # 历史趋势
        chart_frame = tk.LabelFrame(left_frame, text='历史趋势', font=('微软雅黑', 10, 'bold'),
                                    fg=COLORS['text'], bg=COLORS['bg_dark'], relief='ridge', bd=1)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        chart_container = tk.Frame(chart_frame, bg=COLORS['bg_dark'])
        chart_container.pack(fill=tk.BOTH, expand=True)

        # 增大底部边距，给时间标签留出空间
        fig = Figure(figsize=(5, 3), dpi=90, facecolor=COLORS['bg_dark'])
        fig.subplots_adjust(left=0.12, right=0.95, top=0.92, bottom=0.25)  
        self.ax = fig.add_subplot(111)
        self.ax.set_facecolor(COLORS['bg_light'])
        self.ax.tick_params(colors=COLORS['text_dim'])
        for spine in self.ax.spines.values():
            spine.set_color(COLORS['text_dim'])

        self.canvas = FigureCanvasTkAgg(fig, master=chart_container)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self.slide_frame = tk.Frame(chart_container, bg=COLORS['bg_dark'])
        self.slide_frame.pack(fill=tk.X, pady=(3,0))
        self.all_chart_data = []
        self.show_count = 25
        self.offset_idx = 0

        self.h_scale = ttk.Scale(self.slide_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                command=self.slide_change)
        self.h_scale.pack(fill=tk.X, padx=5)

        # ========== 右侧 ==========
        right_frame = tk.Frame(main_paned, bg=COLORS['bg_dark'])
        main_paned.add(right_frame, width=900)

        # 底部按钮区域（居中放置）
        btn_frame = tk.Frame(right_frame, bg=COLORS['bg_dark'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=12)
        
        btn_container = tk.Frame(btn_frame, bg=COLORS['bg_dark'])
        btn_container.pack(anchor=tk.CENTER)
        
        tk.Button(btn_container, text='刷新', command=self.load_data,
                bg=COLORS['accent'], fg='white', relief='flat', width=10).pack(side=tk.LEFT, padx=8)
        
        # 删除和修改按钮：仅 admin 和 operator 可见
        if self.role in ('admin', 'operator'):
            tk.Button(btn_container, text='删除', command=self.delete_data,
                    bg=COLORS['danger'], fg='white', relief='flat', width=10).pack(side=tk.LEFT, padx=8)
            tk.Button(btn_container, text='修改', command=self.modify_data,
                    bg=COLORS['warning'], fg='white', relief='flat', width=10).pack(side=tk.LEFT, padx=8)

        # 预警信息
        alert_frame = tk.LabelFrame(right_frame, text='预警信息', font=('微软雅黑', 10, 'bold'),
                                    fg=COLORS['text'], bg=COLORS['bg_dark'], relief='ridge', bd=1)
        alert_frame.pack(fill=tk.X, pady=(0, 10))
        self.alert_panel = AlertPanel(alert_frame)

        # 数据表格区
        data_container = tk.LabelFrame(right_frame, text='历史数据', font=('微软雅黑', 10, 'bold'),
                                            fg=COLORS['text'], bg=COLORS['bg_dark'], relief='ridge', bd=1)
        data_container.pack(fill=tk.BOTH, expand=True)

        # 分页
        page_frame = tk.Frame(data_container, bg=COLORS['bg_dark'])
        page_frame.pack(pady=5)
        tk.Button(page_frame, text='← 上一页', command=self.page_prev,
                bg=COLORS['bg_light'], fg=COLORS['text'], relief='flat').pack(side=tk.LEFT, padx=5)
        self.page_label = tk.Label(page_frame, text=f'第 {self.page_now} 页',
                                    fg=COLORS['text'], bg=COLORS['bg_dark'])
        self.page_label.pack(side=tk.LEFT, padx=10)
        tk.Button(page_frame, text='下一页 →', command=self.page_next,
                bg=COLORS['bg_light'], fg=COLORS['text'], relief='flat').pack(side=tk.LEFT, padx=5)

        # 表格
        self.create_table(data_container)

    def create_table(self, parent):
        scrollbar = ttk.Scrollbar(parent)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(parent, columns=('ID', '设备名', '温度', '湿度', '采集时间'),
                                show='headings', yscrollcommand=scrollbar.set, height=15)
        scrollbar.config(command=self.tree.yview)

        columns_config = [
            ('ID', 50, 'center'),
            ('设备名', 150, 'center'),
            ('温度', 100, 'center'),
            ('湿度', 100, 'center'),
            ('采集时间', 180, 'center')
        ]

        for col, width, anchor in columns_config:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=anchor)

        style = ttk.Style()
        style.theme_use('default')
        style.configure('Treeview', background=COLORS['bg_light'],
                        foreground=COLORS['text'], fieldbackground=COLORS['bg_light'],
                        rowheight=25)
        style.configure('Treeview.Heading', background=COLORS['bg_dark'],
                        foreground=COLORS['text'], font=('微软雅黑', 9, 'bold'))
        style.map('Treeview', background=[('selected', COLORS['accent'])])

        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def refresh_table_only(self):
        """仅刷新表格数据，不执行报警判断"""
        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            offset = (self.page_now - 1) * self.page_size

            cursor.execute("""
                SELECT s.data_id, d.device_name, s.temperature, s.humidity, s.collect_time
                FROM SensorData s
                JOIN Device d ON s.device_id = d.device_id
                ORDER BY s.collect_time DESC
                LIMIT %s OFFSET %s
            """, (self.page_size, offset))
            data_list = cursor.fetchall()

            for row in data_list:
                self.tree.insert('', tk.END, values=row[0:5])

            conn.close()
        except Exception as e:
            messagebox.showerror("错误", f"表格刷新失败：{str(e)}")

    def load_data(self):
        """完整刷新：表格+实时数据+报警判断，只由定时任务调用"""
        self.refresh_table_only()

        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # 查询最新数据
            cursor.execute("""
                SELECT s.data_id, d.device_name, s.temperature, s.humidity, s.collect_time, s.device_id
                FROM SensorData s
                JOIN Device d ON s.device_id=d.device_id
                ORDER BY s.collect_time DESC LIMIT 1
            """)
            latest_one = cursor.fetchone()

            if latest_one:
                dev_name    = latest_one[1]
                temp        = latest_one[2]
                hum         = latest_one[3]
                collect_time= latest_one[4]
                dev_id      = latest_one[5]

                # 更新实时显示
                temp_color = COLORS['danger'] if temp > TEMP_MAX or temp < TEMP_MIN else COLORS['success']
                self.temp_label.config(text=f'{temp:.1f} ℃', fg=temp_color)
                self.hum_label.config(text=f'{hum:.1f} %')

                # 报警判断（去重）
                cursor.execute("""
                    SELECT alert_id FROM Alert 
                    WHERE device_id=%s AND alert_time=%s
                """, (dev_id, collect_time))
                alert_exist = cursor.fetchone()

                if not alert_exist:
                    if temp > TEMP_MAX:
                        alert_type = "温度过高"
                        alert_msg = f'【高温】{dev_name} 温度 {temp:.1f}℃ (上限 {TEMP_MAX}℃)'
                        self.alert_panel.add_alert(alert_msg)
                        cursor.execute("INSERT INTO Alert(device_id,alert_type,alert_value,alert_time,status) VALUES(%s,%s,%s,%s,'未处理')", (dev_id, alert_type, temp, collect_time))
                    if temp < TEMP_MIN:
                        alert_type = "温度过低"
                        alert_msg = f'【低温】{dev_name} 温度 {temp:.1f}℃ (下限 {TEMP_MIN}℃)'
                        self.alert_panel.add_alert(alert_msg)
                        cursor.execute("INSERT INTO Alert(device_id,alert_type,alert_value,alert_time,status) VALUES(%s,%s,%s,%s,'未处理')", (dev_id, alert_type, temp, collect_time))
                    if hum > HUM_MAX:
                        alert_type = "湿度过高"
                        alert_msg = f'【高湿】{dev_name} 湿度 {hum:.1f}% (上限 {HUM_MAX}%)'
                        self.alert_panel.add_alert(alert_msg)
                        cursor.execute("INSERT INTO Alert(device_id,alert_type,alert_value,alert_time,status) VALUES(%s,%s,%s,%s,'未处理')", (dev_id, alert_type, hum, collect_time))
                    if hum < HUM_MIN:
                        alert_type = "湿度过低"
                        alert_msg = f'【低湿】{dev_name} 湿度 {hum:.1f}% (下限 {HUM_MIN}%)'
                        self.alert_panel.add_alert(alert_msg)
                        cursor.execute("INSERT INTO Alert(device_id,alert_type,alert_value,alert_time,status) VALUES(%s,%s,%s,%s,'未处理')", (dev_id, alert_type, hum, collect_time))
                conn.commit()

                # 绘制趋势图
                cursor.execute("SELECT temperature,humidity,collect_time FROM SensorData ORDER BY collect_time DESC LIMIT 500")
                self.all_chart_data = cursor.fetchall()[::-1]
                total_data_num = len(self.all_chart_data)
                max_slide_val = max(0, total_data_num - self.show_count)
                self.h_scale.config(to=max_slide_val)
                
                now_pos = self.h_scale.get()
                if now_pos > max_slide_val:
                    self.h_scale.set(max_slide_val)
                
                conn.close()
        except Exception as e:
            messagebox.showerror("错误", f"加载失败：{str(e)}")
    
    def page_prev(self):
        if self.page_now > 1:
            self.page_now -= 1
            self.page_label.config(text=f'第 {self.page_now} 页')
            self.refresh_table_only()
    
    def page_next(self):
        self.page_now += 1
        self.page_label.config(text=f'第 {self.page_now} 页')
        self.refresh_table_only()
    
    def delete_data(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的数据")
            return
        if messagebox.askyesno("确认", "确定删除选中的数据吗？"):
            self.is_operating = True
            data_id = self.tree.item(selected[0])['values'][0]
            try:
                conn = pymysql.connect(**DB_CONFIG)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM SensorData WHERE data_id=%s", (data_id,))
                conn.commit()
                conn.close()
                self.load_data()
                messagebox.showinfo("成功", "数据已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除失败：{str(e)}")
            self.is_operating = False
    
    def modify_data(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要修改的数据")
            return
        self.is_operating = True
        values = self.tree.item(selected[0])['values']
        # 传入角色，以便窗口内根据角色禁用保存按钮（虽然只有admin/operator能打开此窗口）
        AddDataWindow(self.window, values[0], values[2], values[3], lambda: (self.load_data(), setattr(self,"is_operating",False)), self.role)
    
    def set_threshold_win(self):
        # 阈值设置只允许 admin/operator 打开（菜单已限制，这里再防护一次）
        if self.role not in ('admin', 'operator'):
            messagebox.showerror("权限不足", "您没有权限修改阈值！")
            return
        top = tk.Toplevel(self.window)
        top.title("阈值设置")
        top.geometry("360x300")
        top.configure(bg=COLORS['bg_dark'])
        
        entries = []
        
        def save():
            global TEMP_MAX, TEMP_MIN, HUM_MAX, HUM_MIN
            try:
                TEMP_MAX = float(entries[0].get())
                TEMP_MIN = float(entries[1].get())
                HUM_MAX = float(entries[2].get())
                HUM_MIN = float(entries[3].get())
                messagebox.showinfo("成功", "阈值已保存")
                top.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效数字")
        
        labels = [('温度上限 (℃)', TEMP_MAX), ('温度下限 (℃)', TEMP_MIN),
                ('湿度上限 (%)', HUM_MAX), ('湿度下限 (%)', HUM_MIN)]
        
        for i, (label, default) in enumerate(labels):
            tk.Label(top, text=label, fg=COLORS['text'], bg=COLORS['bg_dark']).grid(row=i, column=0, pady=8, padx=10)
            entry = tk.Entry(top, width=15, bg=COLORS['bg_light'], fg=COLORS['text'], insertbackground='white')
            entry.insert(0, str(default))
            entry.grid(row=i, column=1, pady=8)
            entries.append(entry)
        
        tk.Button(top, text="保存", command=save, bg=COLORS['accent'], fg='white', relief='flat', width=15).grid(row=4, column=0, columnspan=2, pady=15)
    
    def slide_change(self, val):
        if not self.all_chart_data:
            return
        self.offset_idx = int(float(val))
        total_len = len(self.all_chart_data)
        end_idx = self.offset_idx + self.show_count
        end_idx = min(end_idx, total_len)
        
        slice_data = self.all_chart_data[self.offset_idx:end_idx]
        temps = [x[0] for x in slice_data]
        hums = [x[1] for x in slice_data]
        times = [str(x[2])[5:16] for x in slice_data]
        x_index = list(range(len(slice_data)))

        self.ax.clear()
        self.ax.set_facecolor(COLORS['bg_light'])
        self.ax.tick_params(colors=COLORS['text_dim'], labelsize=8)
        for spine in self.ax.spines.values():
            spine.set_color(COLORS['text_dim'])
        self.ax.plot(x_index, temps, 'o-', linewidth=1.5, markersize=3, label='温度', color=COLORS['danger'])
        self.ax.plot(x_index, hums, 's-', linewidth=1.5, markersize=3, label='湿度', color=COLORS['success'])
        self.ax.set_xticks(x_index)
        self.ax.set_xticklabels(times, rotation=45)
        
        self.ax.legend(loc='upper left', facecolor=COLORS['bg_light'], edgecolor=COLORS['text_dim'])
        self.ax.set_xlabel('时间', color=COLORS['text_dim'])
        self.ax.set_ylabel('数值', color=COLORS['text_dim'])

        self.canvas.draw()

    # 以下方法均传入 role，以便子窗口根据权限限制操作
    def show_data_query(self): QueryWindow(self.window)
    def show_data_add(self): AddDataWindow(self.window, callback=self.load_data, role=self.role)
    def show_data_stats(self): StatsWindow(self.window)
    def show_device_list(self): DeviceWindow(self.window)
    def show_device_edit(self): DeviceEditWindow(self.window, self.role)
    def show_alert_list(self): AlertWindow(self.window, self.role)
    def show_user_manage(self): UserWindow(self.window)


# ================== 只读或受权限控制的子窗口 ==================

class QueryWindow:
    def __init__(self, parent):
        self.window = tk.Toplevel(parent)
        self.window.title('历史查询')
        self.window.geometry('600x400')
        tk.Label(self.window, text='日期查询', font=('微软雅黑',14)).pack(pady=10)
        frame = tk.Frame(self.window)
        frame.pack(pady=10)
        tk.Label(frame, text='开始').grid(row=0,column=0)
        self.s = tk.Entry(frame,width=15)
        self.s.grid(row=0,column=1,padx=5)
        tk.Label(frame, text='结束').grid(row=0,column=2)
        self.e = tk.Entry(frame,width=15)
        self.e.grid(row=0,column=3,padx=5)
        tk.Button(frame,text='查询',command=self.q).grid(row=0,column=4)
        self.tree = ttk.Treeview(self.window,columns=('设备','温度','湿度','时间'),show='headings')
        self.tree.heading('设备',text='设备')
        self.tree.heading('温度',text='温度')
        self.tree.heading('湿度',text='湿度')
        self.tree.heading('时间',text='时间')
        self.tree.pack(fill=tk.BOTH,expand=1,padx=10,pady=10)
    def q(self):
        for i in self.tree.get_children():self.tree.delete(i)
        conn=pymysql.connect(**DB_CONFIG)
        cur=conn.cursor()
        cur.execute("""SELECT d.device_name,s.temperature,s.humidity,s.collect_time
                       FROM SensorData s JOIN Device d ON s.device_id=d.device_id
                       WHERE DATE(s.collect_time) BETWEEN %s AND %s ORDER BY s.collect_time DESC""",
                    (self.s.get(),self.e.get()))
        for row in cur.fetchall():
            self.tree.insert('',tk.END,values=row)
        conn.close()


class AddDataWindow:
    def __init__(self, p, data_id=None, t=None, h=None, callback=None, role='viewer'):
        self.w = tk.Toplevel(p)
        self.w.title('数据录入/修改')
        self.w.geometry('400x300')
        self.data_id = data_id
        self.callback = callback
        self.role = role
        
        tk.Label(self.w, text='数据录入', font=('微软雅黑',14)).pack(pady=10)
        f = tk.Frame(self.w)
        f.pack(pady=20)
        tk.Label(f, text='设备：').grid(row=0, column=0)
        self.c = ttk.Combobox(f, width=20)
        self.c.grid(row=0, column=1)
        self.load_dev()
        tk.Label(f, text='温度：').grid(row=1, column=0)
        self.t = tk.Entry(f)
        self.t.grid(row=1, column=1)
        if t: self.t.insert(0, str(t))
        tk.Label(f, text='湿度：').grid(row=2, column=0)
        self.h = tk.Entry(f)
        self.h.grid(row=2, column=1)
        if h: self.h.insert(0, str(h))
        
        # 保存按钮：如果角色不是 admin/operator，则禁用
        self.save_btn = tk.Button(self.w, text='保存', command=self.save)
        self.save_btn.pack(pady=20)
        if self.role not in ('admin', 'operator'):
            self.save_btn.config(state=tk.DISABLED)
            tk.Label(self.w, text='您没有权限修改数据', fg='red').pack()
    
    def load_dev(self):
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT device_id, device_name FROM Device")
        self.devs = cur.fetchall()
        self.c['values'] = [f"{a}-{b}" for a,b in self.devs]
        conn.close()
    
    def save(self):
        did = int(self.c.get().split('-')[0])
        t = float(self.t.get())
        h = float(self.h.get())
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        if self.data_id:
            cur.execute("UPDATE SensorData SET temperature=%s,humidity=%s WHERE data_id=%s", (t, h, self.data_id))
        else:
            cur.execute("INSERT INTO SensorData(device_id,temperature,humidity,collect_time) VALUES(%s,%s,%s,NOW())", (did, t, h))
        conn.commit()
        conn.close()
        messagebox.showinfo('成功','保存完成')
        if self.callback:
            self.callback()
        self.w.destroy()


class StatsWindow:
    def __init__(self, p):
        self.w = tk.Toplevel(p)
        self.w.title('统计')
        self.w.geometry('500x400')
        tk.Label(self.w, text='统计', font=('微软雅黑',14)).pack(pady=10)
        self.txt = tk.Text(self.w, width=60, height=20)
        self.txt.pack(pady=10)
        self.calc()
    def calc(self):
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""SELECT d.device_name,ROUND(AVG(s.temperature),2),
                       ROUND(MAX(s.temperature),2),ROUND(MIN(s.temperature),2),
                       ROUND(AVG(s.humidity),2) FROM SensorData s
                       JOIN Device d ON s.device_id=d.device_id GROUP BY d.device_id""")
        for row in cur.fetchall():
            self.txt.insert(tk.END, f"设备：{row[0]}\n 平均{row[1]}℃ 最高{row[2]} 最低{row[3]} 湿度{row[4]}%\n\n")
        conn.close()


class DeviceWindow:
    def __init__(self, p):
        self.w = tk.Toplevel(p)
        self.w.title('设备列表')
        self.w.geometry('600x400')
        self.tree = ttk.Treeview(self.w, columns=('ID','名称','位置','IP','状态'), show='headings')
        for c in ('ID','名称','位置','IP','状态'): self.tree.heading(c, text=c)
        self.tree.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT device_id, device_name, location, ip_address, status FROM Device")
        for row in cur.fetchall():
            self.tree.insert('', tk.END, values=row)
        conn.close()


class DeviceEditWindow:
    def __init__(self, p, role):
        if role not in ('admin', 'operator'):
            messagebox.showerror("权限不足", "您没有权限编辑设备！")
            return
        self.w = tk.Toplevel(p)
        self.w.title('设备编辑')
        self.w.geometry('500x400')
        f = tk.Frame(self.w)
        f.pack(pady=20)
        self.entries = {}
        for i, (t, k) in enumerate([('名称','name'),('位置','loc'),('IP','ip'),('状态','sta')]):
            tk.Label(f, text=t).grid(row=i, column=0)
            if k == 'sta':
                self.entries[k] = ttk.Combobox(f, values=['在线','离线','故障'], width=17)
            else:
                self.entries[k] = tk.Entry(f, width=20)
            self.entries[k].grid(row=i, column=1)
        tk.Button(self.w, text='添加', command=self.add).pack(pady=10)
        self.tree = ttk.Treeview(self.w, columns=('ID','名称','状态'), show='headings', height=6)
        self.tree.heading('ID', text='ID')
        self.tree.heading('名称', text='名称')
        self.tree.heading('状态', text='状态')
        self.tree.pack(pady=10)
        self.ref()
    def ref(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT device_id, device_name, status FROM Device")
        for row in cur.fetchall():
            self.tree.insert('', tk.END, values=row)
        conn.close()
    def add(self):
        n = self.entries['name'].get()
        l = self.entries['loc'].get()
        i = self.entries['ip'].get()
        s = self.entries['sta'].get()
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("INSERT INTO Device(device_name,location,ip_address,status) VALUES(%s,%s,%s,%s)", (n, l, i, s))
        conn.commit()
        conn.close()
        self.ref()
        messagebox.showinfo('成功','添加成功')


class AlertWindow:
    def __init__(self, p, role):
        self.w = tk.Toplevel(p)
        self.w.title('报警记录')
        self.w.geometry('800x500')
        self.role = role
        self.tree = ttk.Treeview(self.w, columns=('ID','设备','类型','数值','状态','时间'), show='headings')
        for c in ('ID','设备','类型','数值','状态','时间'): self.tree.heading(c, text=c)
        self.tree.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)
        
        # 标记已处理按钮：仅 admin/operator 可用
        self.mark_btn = tk.Button(self.w, text='标记已处理', command=self.mark)
        self.mark_btn.pack(pady=10)
        if self.role not in ('admin', 'operator'):
            self.mark_btn.config(state=tk.DISABLED)
        
        self.load()
    
    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("""SELECT a.alert_id,d.device_name,a.alert_type,a.alert_value,a.status,a.alert_time
                       FROM Alert a JOIN Device d ON a.device_id=d.device_id ORDER BY a.alert_time DESC""")
        for row in cur.fetchall():
            self.tree.insert('', tk.END, values=row)
        conn.close()
    
    def mark(self):
        s = self.tree.selection()
        if s:
            aid = self.tree.item(s[0])['values'][0]
            conn = pymysql.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("UPDATE Alert SET status='已处理',handle_time=NOW() WHERE alert_id=%s", (aid,))
            conn.commit()
            conn.close()
            self.load()


class UserWindow:
    def __init__(self, p):
        self.w = tk.Toplevel(p)
        self.w.title('用户管理')
        self.w.geometry('600x500')
        f = tk.Frame(self.w)
        f.pack(pady=10)
        tk.Label(f, text='用户').grid(row=0, column=0)
        self.u = tk.Entry(f, width=15)
        self.u.grid(row=0, column=1)
        tk.Label(f, text='密码').grid(row=0, column=2)
        self.p = tk.Entry(f, width=15, show='*')
        self.p.grid(row=0, column=3)
        tk.Label(f, text='角色').grid(row=0, column=4)
        self.r = ttk.Combobox(f, values=['admin','operator','viewer'], width=10)
        self.r.grid(row=0, column=5)
        tk.Button(f, text='添加', command=self.add).grid(row=0, column=6)
        self.tree = ttk.Treeview(self.w, columns=('ID','用户','角色','时间'), show='headings')
        for c in ('ID','用户','角色','时间'): self.tree.heading(c, text=c)
        self.tree.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)
        self.load()
    
    def load(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, role, created_time FROM User")
        for row in cur.fetchall():
            self.tree.insert('', tk.END, values=row)
        conn.close()
    
    def add(self):
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("INSERT INTO User(username,password,role) VALUES(%s,%s,%s)",
                    (self.u.get(), self.p.get(), self.r.get()))
        conn.commit()
        conn.close()
        self.load()
        messagebox.showinfo('成功','已添加')


if __name__ == '__main__':
    LoginWindow()
    