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

num_valid_thread = 100


def get_proxy(this_site_info):
    global get_proxies_list
    try:
        html_content = str(maston.multi_urlopen(this_site_info['url'], this_site_info['post_data'], retryTime=2).read())
        proxies_this_list_pre = re.findall(this_site_info['regular'], html_content)
        proxies_this_list = []
        for each_proxy in proxies_this_list_pre:
            proxies_this_list.append(each_proxy[0] + ":" + each_proxy[1])
        global proxies_list_locker
        proxies_list_locker.acquire()
        get_proxies_list = list(set(proxies_this_list + get_proxies_list))
        proxies_list_locker.release()
    except Exception as e:
        print("\nget proxy list error:\n%s\n%s" % (this_site_info['url'], repr(e)))


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
    text_proxies_valided.delete(1.0, tkinter.END)
    th_check = threading.Thread(target=check_proxy.check_proxy,
                                args=(get_proxies_list, check_site_info, (2, 3), num_valid_thread,
                                      lab_verify_process, text_proxies_valided, btn_start_valid)
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
    root.destroy()


check_site_info = maston.get_ini_raw("check_info.ini")
# 格式为{'site1_name':{'url':string, 'keyword':string, 'timeout':int}, ...}
leech_site_info = {}

proxies_list_locker = threading.Lock()
proxy_ini = configparser.ConfigParser()
root = tkinter.Tk()
top = tkinter.Frame()
lab_proxy_get = tkinter.Label(top, text="获取的代理列表：")
lab_proxy_valided = tkinter.Label(top, text="已验证代理列表（" + str(num_valid_thread) + "线程）：")
lab_space = tkinter.Label(top, text=" ")
text_proxies_get = tkinter.scrolledtext.ScrolledText(top, width=24, height=24)
text_proxies_valided = tkinter.scrolledtext.ScrolledText(top, width=24, height=24)
# lab_proxy_count = Tkinter.Label(top, text="代理数量：")
lab_verify_process = tkinter.Label(top, text="验证进度：未开始")
btn_start_get = tkinter.Button(top, text="     开始获取    ", command=btn_start_get_click)
btn_start_valid = tkinter.Button(top, text="     开始验证    ", command=btn_start_valid_click)

frame_tree = ttk.Frame(top)
tree_view = ttk.Treeview(frame_tree, columns=("代理IP:Port", "延时"), show="headings", height=14)
scroll_tree_v = ttk.Scrollbar(frame_tree, orient="vertical", command=tree_view.yview)
scroll_tree_h = ttk.Scrollbar(frame_tree, orient="horizontal", command=tree_view.xview)
tree_view.config(yscrollcommand=scroll_tree_v.set, xscrollcommand=scroll_tree_h.set)
tree_view.grid(sticky="sew")
scroll_tree_v.grid(row=0,column=1, sticky="ns")
scroll_tree_h.grid(row=1,column=0, sticky="we")

lab_proxy_get.grid(row=0, column=0, sticky="W")
lab_proxy_valided.grid(row=0, column=2, sticky="W")
text_proxies_get.grid(row=1, column=0)
lab_space.grid(row=1, column=1, padx=4)
text_proxies_valided.grid(row=1, column=2)

frame_tree.grid(row=1, column=3, sticky="swe")

lab_verify_process.grid(row=2, column=0, columnspan=3, sticky="E")
btn_start_get.grid(row=3, column=0, columnspan=2)
btn_start_valid.grid(row=3, column=2, columnspan=2)

proxy_ini.read("proxy.ini")
get_proxies_list = re.split("[\s]+", proxy_ini.get("get_proxy", "proxies_list"))
valied_proxies_list = re.split("[\s]+", proxy_ini.get("valied_proxy", "proxies_list"))

text_proxies_get.insert(1.0, "\n".join(get_proxies_list))
text_proxies_valided.insert(1.0, "\n".join(valied_proxies_list))
lab_proxy_get.config(text="获取的代理列表（" + str(len(get_proxies_list)) + "）：")
lab_verify_process.config(lab_verify_process, text="验证数量：" + str(len(valied_proxies_list)))




maston.center_screen(root, top, 20)
root.title("代理测试工具 V0.1")
root.protocol("WM_DELETE_WINDOW", window_closing)
root.mainloop()
