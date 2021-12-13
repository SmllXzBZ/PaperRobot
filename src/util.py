import os
import logging
import requests
import difflib
import time
import random
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bparser import BibTexParser
from config import LOG_PATH,HEADERS,S_THRESHOLD,BASE_DIR,FAIL_PATH,DATA_DIR,LIB,USERNAME,PASSWORD
from src.log import init_log
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

init_log(LOG_PATH)


def banner():
    my_banner = ("""%s
              
          o__ __o                                                         
         <|     v\                                                        
         / \     <\                                                       
         \o/     o/   o__ __o/  \o_ __o      o__  __o   \o__ __o    __o__ 
          |__  _<|/  /v     |    |    v\    /v      |>   |     |>  />  \  
          |         />     / \  / \    <\  />      //   / \   < >  \o     
         <o>        \      \o/  \o/     /  \o    o/     \o/         v\    
          |          o      |    |     o    v\  /v __o   |           <\   
         / \         <\__  / \  / \ __/>     <\/> __/>  / \     _\o__</   
                                \o/                                       
                                 |                                        
                                / \                                       \
                                                                        %s%s
                                                                  moxiaoxi
                                                            # Version: 2.0%s

        """ % ('\033[91m', '\033[0m', '\033[93m', '\033[0m'))
    print(my_banner)
    # logging.info(my_banner)


def check_login(url, cookies, succ_flag='University'):
    try:
        response = requests.get(url, headers=HEADERS, cookies=cookies,
                                verify=False)
        assert response.status_code == 200
        flag = succ_flag in response.text
        if flag == True:
            logging.debug("COOKIE LOGIN SUCC: {}".format(url))
            return True
    except Exception as e:
        logging.error(e)
    logging.warning("COOKIE LOGIN ERROR: {}".format(url))
    return False


# 保存文件
def save_file(path, data):
    out_file_dir = os.path.split(path)[0]
    if not os.path.isdir(out_file_dir):
        os.makedirs(out_file_dir)
    with open(path, 'wb') as f:
        f.write(data)
    return True


# 读取文件
def read_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    return data


# 检查文件是否存在
def check_exist(path):
    if os.path.exists(path):
        return True
    return False


# 清洗一些干扰字符
def clean_string(s):
    # 对于xxx - xxx后置位的东西都删了
    if " - " in s:
        # print(s)
        s = s[:s.find(" - ")]
        # print(s)
    # 清洗字符串, 如果是xxx:  xxx xxx  一个单词加: 的title，直接清洗掉
    if ":" in s.split(' ')[0]:
        s = ' '.join(s.split(' ')[1:])
    s = s.lower().replace(":", '').replace('-', '').replace('.', '').replace('}', '').replace('{', '')
    return s


# 计算字符串相似度
def string_similar(s1, s2):
    # 变小写,字符消去
    s1 = clean_string(s1)
    s2 = clean_string(s2)
    # # 若互为子字符串，则说明一致
    # if s1 in s2 or s2 in s1:
    #     # print(s1,s2)
    #     return True
    # 相似度大于0.85判定为同一个论文
    # google会忽略一部分字符串，所以我们取前缀/后缀计算相似度
    l = max(35, min(len(s1), len(s2))) - 10
    i1 = difflib.SequenceMatcher(None, s1[:l], s2[:l]).quick_ratio()
    i2 = difflib.SequenceMatcher(None, s1[-l:], s2[-l:]).quick_ratio()
    if i1 > S_THRESHOLD or i2 > S_THRESHOLD:
        return True
    return False


# 随机等待一段时间
def random_sleep(min=1, max=5):
    t = random.randint(min, max)
    time.sleep(t)


# 得到某个路径下所有[end]文件 .bib
def get_all_path(dir_path, endwith='.bib'):
    dir_path = BASE_DIR + dir_path
    end = os.listdir(dir_path)
    paths = []
    for e in end:
        if e.endswith(endwith):
            paths.append(e)
    return paths


# 读取bibtex
def read_bibtex(path):
    with open(path, 'rb') as bibfile:
        parser = BibTexParser(common_strings=False)
        parser.ignore_nonstandard_types = False
        parser.homogenise_fields = False
        bibdata = bibtexparser.load(bibfile, parser=parser)
        return bibdata


# 写bibtex
def write_bibtex(path, data):
    path = DATA_DIR + path
    writer = BibTexWriter()
    writer.indent = '    '
    s = bibtexparser.dumps(data, writer=writer).encode()
    return save_file(path, s)


# 记录失败的信息
def save_fails(info):
    fail_path = FAIL_PATH
    with open(fail_path, 'a+') as f:
        f.write(info + '\r\n')
    return


# 利用webdriver维持cookie
def get_cookies_with_institution_login(login_url, username=USERNAME, password=PASSWORD, succ_flag='University'):
    # base_url = "https://" +login_url.split('//')[1].split('/')[0]
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    # driver.get(base_url)
    driver.get(login_url)
    u_button = driver.find_element_by_xpath('//*[@id="i_user"]')
    u_button.send_keys(username)
    pwd_button = driver.find_element_by_xpath('//*[@id="i_pass"]')
    pwd_button.send_keys(password)
    l_button = driver.find_element_by_xpath('//*[@id="theform"]/div[4]/a')
    l_button.click()
    while True:
        if succ_flag in driver.page_source:
            logging.debug('[+] login Succ...')
            results = {}
            cookies = driver.get_cookies()
            for c in cookies:
                results[c['name']] = c['value']
            driver.close()
            return results
        time.sleep(1)
        logging.debug('[-] waiting...')


# 统计某年的下载情况
def count_status_key_year(key, year):
    name = LIB[key]
    # count bib
    dir_path = "{}/bibtex/{}/{}/".format(DATA_DIR, name, year)

    bpaths = []
    try:
        end = os.listdir(dir_path)
        for e in end:
            if e.endswith('.bib'):
                p = dir_path + e
                bpaths.append(p)
    except Exception as e:
        logging.warning(e)

    ppaths = []
    try:
        # count pdf
        pdf_path = "{}/pdf/{}/{}/".format(DATA_DIR, name, year)
        end = os.listdir(pdf_path)
        for e in end:
            if e.endswith('.pdf'):
                p = pdf_path + e
                ppaths.append(p)
    except Exception as e:
        logging.warning(e)

    fails = []
    try:
        # check fails
        for p in bpaths:
            path = p.replace('bibtex','pdf').replace('.bib','.pdf')
            if path not in ppaths:
                fails.append(p)
    except Exception as e:
        logging.debug(e)
        fails = bpaths
    results = {'bibtex': bpaths, 'pdf': ppaths, 'fail': fails}
    return results


# 统计目录下所有文件
def count_paths(dir_path):
    end = os.listdir(dir_path)
    d_paths = []
    for e in end:
        if '.' not in e:
            path = "{}/{}".format(dir_path, e)
            d_paths.append(path)
    return d_paths


