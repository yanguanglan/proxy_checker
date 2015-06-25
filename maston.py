# coding=utf-8
# !/usr/bin/env python

import urllib.request, urllib.error, urllib.parse
import urllib.request, urllib.parse, urllib.error
import http.cookiejar
import re
import time
import configparser

__author__ = 'maston'

def get_ini_raw(ini_filename):
    """
    以字典的形式返回ini文件内容：
    {'site1':{'url':网址, 'regular':正则式}, 'site2':{'url':网址, 'regular':正则式, 'post':post_data, 'cookie':cookie_data}, ...}
    """
    config_ini = {}
    get_ini = configparser.RawConfigParser()
    get_ini.read(ini_filename)
    sections = get_ini.sections()
    for this_section in sections:
        all_options = get_ini.items(this_section)
        this_site_para = list_or_tuple_to_dict(all_options)
        config_ini[this_section] = this_site_para
    return config_ini

def list_or_tuple_to_dict(source_list_or_tuple):
    """
    将符合格式的元组或列表转字典
    :param source_list_or_tuple: 输入格式类似[(name1, value1), (name2, value2),...]的列表或元组
    :return: 返回格式为{name1:value1, name2:value2, ...}的字典
    """
    result_dict = {}
    for each_item in source_list_or_tuple:
        result_dict[each_item[0]] = each_item[1]
    return result_dict

def center_screen(top_root, top_frame, pad=20):
    """
    将Tkinter的窗口屏幕居中，并通过设置frame边界的方式防止控件贴边
    :param top_root: 主窗口
    :param top_frame: 主框架
    :param pad: frame的边距
    :return: 无
    """
    top_root.withdraw()
    top_frame.grid(row=1, column=1, padx=pad, pady=pad)
    top_frame.update_idletasks()

    w = top_root.winfo_screenwidth()
    h = top_root.winfo_screenheight() - 100
    size = tuple(int(_) for _ in top_root.geometry().split('+')[0].split('x'))
    x = w/2 - size[0]/2
    y = h/2 - size[1]/2
    top_root.geometry("%dx%d+%d+%d" % (size + (x, y)))
    top_root.resizable(width=False, height=False)
    top_root.deiconify()

def postdata_prepare(str_post):
    """按HA复制的数据的格式POTS生成编码后的POST数据字符串"""
    post_list = re.split(r"[\r\n]+", str_post)
    post_dict = {}
    for one_para in post_list:
        if one_para == "":
            continue
        split_para = re.split(r"[\s]+", one_para)
        if len(split_para) == 1:
            split_para.append("")
        post_dict[split_para[0]] = split_para[1]
    return urllib.parse.urlencode(post_dict)

def postdata2dict(str_post):
    """将一行类似login=1&m_p_l=1&channel=200&position=102的字符串转换为Dict格式便于urlencode"""
    post_dict = {}
    paras = re.split("&", str_post)
    for one_para in paras:
        if len(one_para) == 0:
            continue
        post_dict[one_para.split("=")[0]] = one_para.split("=")[1]
    return post_dict

def postdata_prepare2(str_post):
    """按一行字符串的格式生成编码后的POST数据字符串"""
    step1 = re.sub('[\r\n]+', '', str_post.replace('&', "', '"), )
    step2 = step1.replace('=', "': '")
    step3 = "{'" + step2 + "'}"
    step4 = eval(step3)
    return urllib.parse.urlencode(step4)

def makeCookie(name, value, domain=None, path="/"):
    complete_cookie = http.cookiejar.Cookie(
        version=None,
        name=name,
        value=value,
        port=None,
        port_specified=None,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=False,
        path=path,
        path_specified=None,
        secure=False,
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rest=None)
    # import Cookie
    # s_cookie = Cookie.SimpleCookie()
    # s_cookie[name] = value
    # s_cookie[name]["path"] = path
    # if domain is not None:
    #     s_cookie[name]["domain"] = domain
    return complete_cookie

def custom_cookiejar(str_cookies, str_domain, path='/', str_spliter="="):
    """将以指定符号（支持正则，默认为"="）分隔name和value的cookie字符串整合为一个cookiejar并返回
    :param str_cookies:
    :param str_domain:
    :param path:
    :param str_spliter:
    """
    myCookieJar = http.cookiejar.CookieJar()
    stra_cookie = re.split(r"[\r\n;]+\s*", str_cookies)
    for str_onecookie in stra_cookie:
        if str_onecookie == "":
            continue
        ParaList_onecookie = re.split("[(" + str_spliter + ")]+", str_onecookie)
        try:
            myCookieJar.set_cookie(makeCookie(ParaList_onecookie[0], ParaList_onecookie[1], str_domain, path))
        except Exception as ec:
            print(("Cookie Error:\r\n%s" % str(ec)))
    return myCookieJar

def now():
    return time.strftime('%m-%d %H:%M:%S', time.localtime(time.time()))

def multi_urlopen(str_Url, Post_Data=None, timeout=30, retryTime=3, proxy="", debug_flag=False):
    """最多尝试retryTime次以get或post方式读取指定网址,Post_Data数据无需urlencode编码"""
    for i_multi in range(0, retryTime):
        try:
            # opener1 = urllib2.build_opener()
            if Post_Data is None:
                request = urllib.request.Request(str_Url)
                request.add_header("User-Agent",
                                   "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0)\ Gecko/20100101 Firefox/38.0")
                request.add_header("Referer", str_Url)
                if str(proxy) != "":
                    request.set_proxy(str(proxy), "http")
                response_content = urllib.request.urlopen(request, timeout=timeout)
                # re_addinfourl = opener1.open(str_Url, timeout=timeout)
            else:
                request = urllib.request.Request(str_Url)
                request.add_header("User-Agent",
                                   "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:38.0)\ Gecko/20100101 Firefox/38.0")
                request.add_header("Referer", str_Url)
                if proxy != "":
                    request.set_proxy(proxy, "http")
                response_content = urllib.request.urlopen(request, urllib.parse.urlencode(postdata2dict(Post_Data)), timeout=timeout)
        except Exception as e_m:
            if debug_flag:
                print("Open ", str_Url, " error at ", str(i_multi + 1), "time(s). Error info:\r\n", str(
                e_m), "\r\ntry again...\r\n")
        else:
            return response_content
    return None  # 运行到这表明耗尽了试错循环还没有得到正确的响应，返回空。
