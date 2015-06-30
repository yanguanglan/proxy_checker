# coding=utf-8
# __author__ = 'maston'

import threading
import time
import tkinter
import requests
import requests.exceptions
import requests.adapters
import maston
import datetime
import queue
import re


def update_gui():
    global g_all_statu, g_lab_processing, g_text_valided_proxies
    while g_btn_Valid_proxies.cget("state") == "disabled":
        try:
            time.sleep(0.8)
            g_all_statu["lab_processing"]["num_thread"] = 0
            for each_thread in threading.enumerate():
                if each_thread.name.find("Verify_Proxy_") == 0:
                    g_all_statu["lab_processing"]["num_thread"] += 1

            valided_num = len(proxies_valided_list)
            already_done_num = len(proxies_unvalided_list) - g_proxy_queue.qsize()
            successful_rate = len(proxies_valided_list) * 100.0 / (already_done_num + 0.1)  # 加0.1为了最初时不会被0除
            speed = already_done_num / ((datetime.datetime.now() - g_start_time).seconds + 0.01)
            g_all_statu["lab_processing"]["valided_num"] = valided_num
            g_all_statu["lab_processing"]["already_done_num"] = already_done_num
            g_all_statu["lab_processing"]["successful_rate"] = successful_rate
            g_all_statu["lab_processing"]["speed"] = speed

            g_lab_processing.config(g_lab_processing,
                                    text=maston.now() + "  有效{0} 已验{1} 有效率{2:.1f} 速度{3:.1f} 线程数{4}".format(
                                        g_all_statu["lab_processing"]["valided_num"],
                                        g_all_statu["lab_processing"]["already_done_num"],
                                        g_all_statu["lab_processing"]["successful_rate"],
                                        g_all_statu["lab_processing"]["speed"],
                                        g_all_statu["lab_processing"]["num_thread"]))
            g_text_valided_proxies.insert(1.0, "".join(g_all_statu["text_proxy_valid_append"]))
            g_all_statu["text_proxy_valid_append"] = ""
        except Exception as e:
            print("GUI ERROR:\n" + repr(e) + "\n")
        finally:
            redraw_gui_event_finished.set()

def get_a_proxy():
    global g_b_stop, g_all_statu, g_proxy_queue, lock_get_proxy
    if g_b_stop:  # 如果有全局停止的信号，则返回空字符串让各个线程退出
        return ""
    lock_get_proxy.acquire()
    try:
        proxy_now = re.sub("[^\d:\.].+", "", str(g_proxy_queue.get(block=False)))
    except Exception:
        proxy_now = ""
    lock_get_proxy.release()
    return proxy_now

def valid_proxy(check_site_info, success_try):
    global lock_valided_list, g_tree_proxies, g_all_statu
    i_error_limit = success_try[1] - success_try[0]
    if i_error_limit < 0:
        i_error_limit = 0
    i_error_now = 0
    proxy_now = get_a_proxy()
    while proxy_now != "":
        test_num = 0
        for each_check_site in check_site_info:  # 用每个站点来测试代理
            # each_check_site内容为{'url':string, 'keyword':string, 'timeout':int}
            i_error_now = 0
            proxy_speed_recorder = {each_check_site: []}
            for iCounter in range(0, success_try[1]):  # 循环若干次测试代理，如错误超过上限，退出测试
                test_num += 1
                if (datetime.datetime.now() - g_gui_last_update_time).seconds > g_gui_update_interval:
                    redraw_gui_event_finished.clear()
                redraw_gui_event_finished.wait()  # 如果需要处理GUI，等待处理完成后再继续
                try:
                    read_timeout = int(check_site_info[each_check_site]['timeout'])
                    connect_timeout = read_timeout / 2
                    if connect_timeout < 2:
                        connect_timeout = 2
                    start_test_time = time.time()
                    req_headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0",
                        "Referer": check_site_info[each_check_site]['url']}
                    req_result = requests.get(check_site_info[each_check_site]['url'],
                                              timeout=(connect_timeout, read_timeout),
                                              proxies={'http': proxy_now, 'https': proxy_now}, headers=req_headers)
                    used_time_seconds = (time.time() - start_test_time) * 1000
                    # html_result = str(req_result.text.encode(req_result.encoding))
                    html_result = req_result.text
                except Exception as e:
                    used_time_seconds = -1
                    html_result = ""
                    print("\nError in proxy %s:\n%r" % (proxy_now, e))
                if html_result.find(check_site_info[each_check_site]['keyword']) < 0:
                    i_error_now += 1
                    if i_error_now > i_error_limit:
                        print(('!' * 10 + maston.now() + '!' * 10 + '\nInvalided proxy: ' + proxy_now))
                        break  # 对应的是  for iCounter in range(0, success_try[1]): 即不再进行该测试站点的余下测试了
                else:
                    proxy_speed_recorder[each_check_site].append((iCounter, used_time_seconds))
                    # 成功的尝试次数大于等于要求即表明通过该站点的测试
                    if iCounter + 1 - i_error_now >= success_try[0]:
                        break
            if i_error_now > i_error_limit:
                break  # 对应的是  for each_check_site in check_site_info:  即不再进行余下测试站点的测试了，该代理不合格
        print("Proxy: " + proxy_now + " test number:" + str(test_num))
        if i_error_now <= i_error_limit:
            # 计算该代理的平均速度
            all_used_time = 0
            all_test_time = 0
            for each_check_site in proxy_speed_recorder:
                for each_test in proxy_speed_recorder[each_check_site]:
                    all_used_time += each_test[1]
                    all_test_time += 1
            avarge_time = round(all_used_time / all_test_time)
            lock_valided_list.acquire()
            proxies_valided_list.append((proxy_now, avarge_time))
            try:
                g_all_statu["text_proxy_valid_append"] += proxy_now + "&" + str(avarge_time) + "\n"  # 显示在text中
                g_tree_proxies.add_data_treeview([(proxy_now, avarge_time)], skip_datebase=True)  # 同时写入treeview中
            except Exception as e2:
                print("""g_all_statu["text_proxy_valid_append"] is wrong:\n""" + repr(e2))
            lock_valided_list.release()
        time.sleep(1)
        proxy_now = get_a_proxy()
    print("Finish, thread exit")


def thread_monitor(check_site_info, success_try, th_num):
    # 准备待查proxies的队列
    for each_proxy in proxies_unvalided_list:
        g_proxy_queue.put(each_proxy)

    th_gui = threading.Thread(target=update_gui)
    th_gui.setDaemon(True)
    th_gui.start()

    ths_verify = []
    for iCounter in range(0, th_num):
        t = threading.Thread(target=valid_proxy, args=(check_site_info, success_try))
        t.setDaemon(True)
        t.setName("Verify_Proxy_" + str(iCounter))
        t.start()
        ths_verify.append(t)

    for iCounter in range(0, th_num):
        ths_verify[iCounter].join()

        # 隔几秒检查一次所有线程是否alive，如果全部退出了，就monitor退出，否则打印当前线程数量
        # num_thread_now = th_num
        # time.sleep(10)
        # while num_thread_now > 0:
        #     num_thread_now = 0
        #     for iCounter in range(0, th_num):
        #         if ths_verify[iCounter].isAlive():
        #             num_thread_now += 1
        #     if num_thread_now > 0:
        #         print "*" * 20 + "\n" * 3 + maston.now() + "  : " + str(num_thread_now) + "\n" * 3
        #         g_all_statu["lab_processing"]["num_thread"] = num_thread_now
        #         # g_lab_processing.config(g_lab_processing, text=maston.now() + "  : " + str(num_thread_now))
        #         time.sleep(5)
        #     else:
        #         print "*" * 20 + "\n\n All finished."


def check_proxy(proxies_list, check_site_info, success_try, threads,
                lab_processing, text_valided_proxies, btn_valided_proxies, tree_proxies):
    """
    输入proxies_list(待检测的代理列表)和check_site_info(检测用网站的信息字典），检测标准为元组success_try(成功次数，总尝试次数），
    运行线程数量为：threads, 运行的进度显示在lab_processing中，结果也显示在tree_proxies表格中。
    check_site_info格式为：{'site1_name':{'url':string, 'keyword':string, 'timeout':int}, ...}
    返回proxies_valided_list(测试可用的代理列表)
    :param proxies_list: 待检测的代理列表
    :param check_site_info: 检测用网站的信息字典
    :param success_try: 元组(成功次数，总尝试次数）
    :param threads: 运行线程数量
    :param lab_processing: 显示检测进度的lable
    :param tree_proxies: 显示代理的表格
    :return:
    """
    global proxies_unvalided_list, g_lab_processing, proxies_valided_list, g_text_valided_proxies, g_btn_Valid_proxies
    global g_proxy_list_pointer, g_start_time, g_tree_proxies

    proxies_unvalided_list = proxies_list
    g_lab_processing = lab_processing
    g_text_valided_proxies = text_valided_proxies
    g_btn_Valid_proxies = btn_valided_proxies
    g_tree_proxies = tree_proxies
    proxies_valided_list = []
    g_start_time = datetime.datetime.now()
    g_btn_Valid_proxies.config(state=tkinter.DISABLED)

    thread_monitor(check_site_info, success_try, threads)

    # proxies_valided_list = list(set(proxies_valided_list))  # 返回前去重
    g_btn_Valid_proxies.config(state=tkinter.NORMAL)
    g_proxy_list_pointer = -1
    return proxies_valided_list


g_tree_proxies = None
g_proxy_queue = queue.Queue(0)
lock_valided_list = threading.Lock()
lock_get_proxy = threading.Lock()
redraw_gui_event_finished = threading.Event()
proxies_unvalided_list = []
proxies_valided_list = []

g_gui_last_update_time = datetime.datetime.now()
g_gui_update_interval = 1

g_lab_processing = None
g_text_valided_proxies = None
g_btn_Valid_proxies = None
g_b_stop = False
g_start_time = datetime.datetime.now()
g_all_statu = {"text_proxy_valid_append": "",
               "lab_processing": {"valided_num": 0, "already_done_num": 0, "successful_rate": 0, "speed": 0,
                                  "num_thread": 0}}


def main():
    pass


if __name__ == "__main__":

 main()
