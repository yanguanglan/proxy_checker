# coding=utf-8

__author__ = 'maston'

import tkinter
import threading
import maston
import re
import tkinter.scrolledtext
import configparser
import check_proxy
import tkinter.ttk as ttk
import tkinter.font as tkfont
import pyperclip
import os
import sqlite3
import requests


class TreeProxies(object):
    def __init__(self, frame):
        self.frame_tree = frame
        self.treeview_proxies = ttk.Treeview(frame_tree, columns=("代理IP:Port", "延时"), show="headings", height=14)
        self.scroll_tree_v = ttk.Scrollbar(frame_tree, orient="vertical", command=self.treeview_proxies.yview)
        self.scroll_tree_h = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.treeview_proxies.xview)
        if os.path.exists("proxy.db"):
            self.conn = sqlite3.connect("proxy.db")
            self.cu = self.conn.cursor()
        else:
            self.conn = sqlite3.connect("proxy.db")
            self.cu = self.conn.cursor()
            self.cu.execute("CREATE TABLE proxy_valided_list (proxy_port VARCHAR(21), speed INTEGER) ")
            self.cu.execute("CREATE TABLE proxy_get_list (proxy_port VARCHAR(21)) ")
        self.cu.execute("PRAGMA synchronous=OFF")

    def init_treeview(self, treeview_head):
        self.treeview_proxies.config(yscrollcommand=self.scroll_tree_v.set, xscrollcommand=self.scroll_tree_h.set)
        self.treeview_proxies.grid(sticky="sew")
        self.scroll_tree_v.grid(row=0, column=1, sticky="ns")
        self.scroll_tree_h.grid(row=1, column=0, sticky="we")
        for col in treeview_head:
            self.treeview_proxies.heading(col, anchor="w", text=col,
                                          command=lambda c=col: self.sort_treeview(c, 0))
            self.treeview_proxies.column(col, width=tkfont.Font().measure(col))
        self.treeview_proxies.column(0, width=115)
        self.treeview_proxies.column(1, width=40)
        self.treeview_proxies.bind("<Button-3>", self.right_click)

    def add_data_treeview(self, list_data, skip_datebase=False):
        for each_proxy in list_data:
            if len(each_proxy) != 2:
                continue
            self.treeview_proxies.insert("", 0, value=each_proxy)
            col_size_now = self.treeview_proxies.column(0)['width']
            col_size_need = tkfont.Font().measure(each_proxy[0]) - 20  # 测试表明系统计算出的数据过大，修正一下
            if col_size_need > col_size_now:
                self.treeview_proxies.column(0, width=col_size_need)
            col_size_now = self.treeview_proxies.column(1)['width']
            col_size_need = tkfont.Font().measure(str(each_proxy[1])) + 10  # 测试表明系统计算出的数据过小，修正一下
            if col_size_need > col_size_now:
                self.treeview_proxies.column(1, width=col_size_need)
        if not skip_datebase:
            self.cu.executemany("INSERT INTO proxy_valided_list VALUES (?, ?)", list_data)
            self.conn.commit()

    def delete_treeview(self):
        self.treeview_proxies.delete(*self.treeview_proxies.get_children(""))
        self.cu.execute("DROP TABLE proxy_valided_list")
        self.cu.execute("CREATE TABLE proxy_valided_list (proxy_port VARCHAR(21), speed INTEGER) ")
        self.conn.commit()

    def sort_treeview(self, col, direct):
        try:
            data = [(int(self.treeview_proxies.set(node, col)), node) for node in
                    self.treeview_proxies.get_children("")]
        except ValueError:
            data = [(self.treeview_proxies.set(node, col), node) for node in self.treeview_proxies.get_children("")]
        data.sort(reverse=direct)
        for new_index, item in enumerate(data):
            self.treeview_proxies.move(item[1], "", new_index)
        self.treeview_proxies.heading(col, command=lambda c=col: self.sort_treeview(c, int(not direct)))

    def right_click(self, event):
        iid = self.treeview_proxies.identify_row(event.y)
        if iid:
            pyperclip.copy(self.treeview_proxies.item(iid)["values"][0])
            pass
        else:
            pass

    def read_db(self):
        self.cu.execute("SELECT * FROM proxy_valided_list")
        return self.cu.fetchall()


def get_proxy(this_site_info):
    global get_proxies_list
    try_count = 3
    proxies_this_list = []
    while try_count:
        try:
            # html_content =
            # str(maston.multi_urlopen(this_site_info['url'], this_site_info['post_data'], retryTime=2).read())
            req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0",
                           "Referer": this_site_info['url']}
            if this_site_info['post_data']:
                html_content = requests.post(this_site_info['url'], this_site_info['post_data'],
                                             headers=req_headers).text
            else:
                html_content = requests.get(this_site_info['url'], headers=req_headers).text
            proxies_this_list_pre = re.findall(this_site_info['regular'], html_content)
            for each_proxy in proxies_this_list_pre:
                proxies_this_list.append(each_proxy[0] + ":" + each_proxy[1])
            if len(proxies_this_list) < 2:
                print("The site: " + this_site_info['url'] + " have nothing!\n")
            try_count = 0
        except Exception as e:
            print("\nget proxy list error:\n%s\n%s" % (this_site_info['url'], repr(e)))
            try_count -= 1
    global proxies_list_locker
    proxies_list_locker.acquire()
    get_proxies_list = list(set(proxies_this_list + get_proxies_list))
    proxies_list_locker.release()


def start_get_proxy_thread():
    btn_start_get.config(state=tkinter.DISABLED)
    th_getproxy = []
    global leech_site_info
    for this_site_name in leech_site_info:
        this_site_info = {"site_name": this_site_name, "url": "", "regular": "", "post_data": None, "cookie": ""}
        for each_para in leech_site_info[this_site_name]:
            this_site_info[each_para] = leech_site_info[this_site_name][each_para]
        t = threading.Thread(target=get_proxy, args=(this_site_info,))
        t.start()
        th_getproxy.append(t)

    for th_each in th_getproxy:
        th_each.join()
    text_proxies_get.delete(1.0, tkinter.END)
    text_proxies_get.insert(1.0, "\n".join(get_proxies_list) + "\n")
    lab_proxy_get.config(text="获取的代理列表（" + str(len(get_proxies_list)) + "）：")
    btn_start_get.config(state=tkinter.NORMAL)


def btn_start_get_click():
    global leech_site_info
    leech_site_info = maston.get_ini_raw("leech_site_info.ini")
    th_getproxy = threading.Thread(target=start_get_proxy_thread)
    th_getproxy.start()


def btn_start_valid_click():
    global get_proxies_list
    get_proxies_list = re.split("[\s]+", text_proxies_get.get(1.0, tkinter.END))
    if "" in get_proxies_list:
        get_proxies_list.remove("")
    if text_proxies_valided.get(1.0, tkinter.END).strip() == "":
        tree_proxies.delete_treeview()
    th_check = threading.Thread(target=check_proxy.check_proxy,
                                args=(get_proxies_list, check_site_info, (2, 3), num_valid_thread,
                                      lab_verify_process, text_proxies_valided, btn_start_valid, tree_proxies)
                                # args=(函数名， 检测用站点字典，(至少成功次数，总尝试次数)，验证线程数，
                                # 显示验证进度的lab， 显示验证结果的TEXT，开始验证的按钮（控制disable/enable）)
                                )
    # th_check.setDaemon(True)
    th_check.setDaemon(True)
    th_check.start()


def window_closing():
    check_proxy.g_b_stop = True
    get_proxies_to_save = text_proxies_get.get(1.0, tkinter.END)
    valied_proxies_to_save = text_proxies_valided.get(1.0, tkinter.END)
    global proxy_ini
    proxy_ini.set("get_proxy", "proxies_list", get_proxies_to_save)
    proxy_ini.set("valied_proxy", "proxies_list", valied_proxies_to_save)
    with open("proxy.ini", "w") as f_save_proxy:
        proxy_ini.write(f_save_proxy)

    allproxies_timeout = []
    for temp_proxy in re.split("\s+", valied_proxies_to_save):
        temp_temp = re.split("&", temp_proxy)
        try:
            allproxies_timeout.append((temp_temp[0], int(temp_temp[1])))
        except Exception:
            pass
    tree_proxies.delete_treeview()
    tree_proxies.add_data_treeview(allproxies_timeout)
    root.destroy()


check_site_info = maston.get_ini_raw("check_info.ini")
# 格式为{'site1_name':{'url':string, 'keyword':string, 'timeout':int}, ...}
leech_site_info = {}

proxies_list_locker = threading.Lock()
proxy_ini = configparser.ConfigParser()
proxy_checker_ini = configparser.ConfigParser()

try:
    proxy_checker_ini.read("proxy_checker.ini")
    num_valid_thread = int(proxy_checker_ini.get("system", "check_thread_num"))
except Exception:
    num_valid_thread = 100

root = tkinter.Tk()
top = tkinter.Frame()
lab_proxy_get = tkinter.Label(top, text="获取的代理列表：")
lab_proxy_valided = tkinter.Label(top, text="已验证代理列表（" + str(num_valid_thread) + "线程）：")
lab_space = tkinter.Label(top, text=" ")
text_proxies_get = tkinter.scrolledtext.ScrolledText(top, width=24, height=24)
text_proxies_valided = tkinter.scrolledtext.ScrolledText(top, width=28, height=24)
# lab_proxy_count = Tkinter.Label(top, text="代理数量：")
lab_verify_process = tkinter.Label(top, text="验证进度：未开始")
btn_start_get = tkinter.Button(top, text="     开始获取    ", command=btn_start_get_click)
btn_start_valid = tkinter.Button(top, text="     开始验证    ", command=btn_start_valid_click)

frame_tree = ttk.Frame(top, width=50)
tree_proxies = TreeProxies(frame_tree)

lab_proxy_get.grid(row=0, column=0, sticky="W")
lab_proxy_valided.grid(row=0, column=2, sticky="W")
text_proxies_get.grid(row=1, column=0)
lab_space.grid(row=1, column=1, padx=4)
text_proxies_valided.grid(row=1, column=2)

frame_tree.grid(row=1, column=3, sticky="swe")

lab_verify_process.grid(row=2, column=0, columnspan=4, sticky="E")
btn_start_get.grid(row=3, column=0, columnspan=2)
btn_start_valid.grid(row=3, column=2, columnspan=2)

proxy_ini.read("proxy.ini")
get_proxies_list = re.split("[\s]+", proxy_ini.get("get_proxy", "proxies_list"))


# allproxies = re.split("[\s]+", proxy_ini.get("valied_proxy", "proxies_list"))
allproxies = tree_proxies.read_db()
valied_proxies_list = allproxies

# allproxies_timeout = []
# for temp_proxy in allproxies:
#     allproxies_timeout.append(re.split("&", temp_proxy))
tree_proxies.init_treeview(("代理IP:Port", "延时"))
tree_proxies.add_data_treeview(allproxies, skip_datebase=False)

text_proxies_get.insert(1.0, "\n".join(get_proxies_list))
temp_text = ""
for each_item in valied_proxies_list:
    temp_text += each_item[0] + "&" + str(each_item[1]) + "\n"
text_proxies_valided.insert(1.0, temp_text[:-1])
lab_proxy_get.config(text="获取的代理列表（" + str(len(get_proxies_list)) + "）：")
lab_verify_process.config(lab_verify_process, text="验证数量：" + str(len(valied_proxies_list)))

maston.center_screen(root, top, 20)
root.title("代理测试工具 V0.33")
root.protocol("WM_DELETE_WINDOW", window_closing)
root.mainloop()
