import re
import sys
import argparse
from src.util import *
from src.app import *

# 测试功能正常与否
def test_get_volume_papers():
    key = 'uss'
    year = 2019
    papers = get_volume_papers(key, year)
    assert len(papers) == 113


def test_get_key_year_bibtex():
    key = 'uss'
    year = 2019
    result = get_key_year_bibtex(key, year)
    assert result == True


def test_get_one_pdf():
    bibtex_path = "bibtex/DSN/2019/0.bib"
    result = get_one_pdf(bibtex_path)
    assert result == True


def test_get_key_year_pdf():
    key = 'uss'
    year = 2019
    result = get_key_year_pdf(key, year)
    assert result == True

def get_cookies(login_url):
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(options=chrome_options)

    # driver.get("https://dl.acm.org/")
    # sign_in = driver.find_element_by_xpath('//*[@id="pb-page-content"]/div/header/div[1]/div[1]/div[2]/div/ul/li[4]/div/ul/li[1]/a')
    # sign_in.click()
    # driver.implicitly_wait(10)
    # button = driver.find_element_by_xpath('//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721con"]').click()
    # button.click()
    # driver.implicitly_wait(10)
    # driver.find_element_by_xpath('//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721"]/section/div/div/div/a/span').click()
    # driver.implicitly_wait(10)
    # choose = driver.find_element_by_xpath('//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721"]/section/div/div/div/ul/li[2]/input')
    # choose.send_keys('Tsinghua University')
    #
    # driver.find_element_by_xpath('//*[@id="pane-0552177a-9137-4ca8-90d3-10b23a0c57c721"]/section/div/div/div/ul/ul/li[329]/a/span').click()
    driver.get(login_url)

    u_button = driver.find_element_by_xpath('//*[@id="i_user"]')
    u_button.send_keys(USERNAME)
    pwd_button = driver.find_element_by_xpath('//*[@id="i_pass"]')
    pwd_button.send_keys(PASSWORD)
    l_button = driver.find_element_by_xpath('//*[@id="theform"]/div[4]/a')
    l_button.click()

    while True:
        if 'Tsinghua University' in driver.page_source:
            print('login Succ...')
            results = {}
            cookies = driver.get_cookies()
            for c in cookies:
                results[c['name']] = c['value']
            driver.close()
            return results
        time.sleep(1)
        print('waiting...')


def get_pdf():
    login_url = "https://sp.springer.com/saml/login?idp=https://idp.tsinghua.edu.cn/openathens&targetUrl=https://link.springer.com/chapter/10.1007/978-3-030-00470-5_12"
    # login_url = "https://dl.acm.org/action/ssostart?idp=https%3A%2F%2Fidp.tsinghua.edu.cn%2Fopenathens&redirectUri=https%3A%2F%2Fdl.acm.org%2F"
    # login_url = "https://ieeexplore.ieee.org/servlet/wayf.jsp?entityId=https://idp.tsinghua.edu.cn/idp/shibboleth&url=https%3A%2F%2Fieeexplore.ieee.org%2FXplore%2Fhome.jsp"
    cookies = get_cookies(login_url)
    # url = 'https://dl.acm.org/doi/pdf/10.1145/1102120.1102137'
    url = 'https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=5504717&ref='
    res = requests.get(url, cookies=cookies)
    print(res.headers['Content-Type'])


def login_download():
    target_url = "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber=5504717&ref=aHR0cHM6Ly9pZWVleHBsb3JlLmllZWUub3JnL2RvY3VtZW50LzU1MDQ3MTc="
    result = get_raw_pdf(target_url)


# get_key_year_pdf
def parse_args():
    # parse the arguments
    parser = argparse.ArgumentParser(
        epilog='\tExample: \r\npython ' + sys.argv[0] + " -m s -id case_a1")
    parser._optionals.title = "OPTIONS"
    parser.add_argument(
        '-t', '--test', default='x', help="")

    args = parser.parse_args()
    return args


def test_springer():
    url = 'https://doi.org/10.1007/3-540-45474-8_9'
    url = "https://link.springer.com/chapter/10.1007%2F3-540-45474-8_9"
    result = get_pdf_from_springer(url)
    print(result['url'])
    assert result is not None

def retry():
    path = './log/fails.txt'
    data = read_file(path).decode()
    # print(data)
    bibs = re.compile(r'bibtex/[a-zA-Z]{1,10}/[0-9]{3,5}/[0-9]*.bib', re.S).findall(data)
    bibs = list(set(bibs))
    for i in range(0, len(bibs) - 1):
        bibtex_path = bibs[i]
        pdf_path = bibtex_path.replace("bibtex", "pdf").replace('.bib', '.pdf')
        if check_exist(pdf_path):
            logging.info("[-] {} 已经存在，继续...".format(pdf_path))
            continue
        logging.info("[-] {} 重试下载...".format(bibtex_path))
        get_one_pdf(bibs[i])


def show_status():
    # 一共有多少篇，下载成功多少篇
    # 会议一共多少篇，成功多少篇
    # 会议某年
    year_start = 2001
    year_end = 2020
    total_bibtex = 0
    total_pdf = 0
    toal_fail = 0
    for key in LIB:
        name = LIB[key]
        bibtex_num = 0
        pdf_num = 0
        fail_num = 0
        for y in range(year_start, year_end):
            result = count_status_key_year(key,y)
            bibtex = len(result['bibtex'])
            if bibtex == 0:
                logging.debug("[-] 会议{} {} 年度没有找到论文".format(name, y))
                continue
            pdf = len(result['pdf'])
            fail = len(result['fail'])
            for f in result['fail']:
                logging.debug("[-] 下载失败的论文:{}".format(f))
            logging.info("[+] {} {}: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(name, y, bibtex, pdf, fail))
            bibtex_num += bibtex
            pdf_num += pdf
            fail_num += fail
        logging.warning("[+] {} {}->{}: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(name, year_start, year_end, bibtex_num, pdf_num, fail_num))
        total_bibtex += bibtex_num
        total_pdf += pdf_num
        toal_fail += fail_num
    logging.warning(
        "[+] {}->{}: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(year_start, year_end, total_bibtex, total_pdf, toal_fail))


def test_pdf():
    pdf_paths = []
    path = 'pdf/'
    for dirpath, dirnames,filenames in os.walk(path):
        for f in filenames:
            if f.endswith('pdf'):
                path = dirpath + '/' + f
                pdf_paths.append(path)
    pdf_paths = sorted(pdf_paths)
    for p in pdf_paths:
        data = read_file(p)
        print(p)
        mediaBox = re.compile(b'\[\ ?0 0 [0-9\.]{1,9} [0-9\.]{1,9}\ ?\]').findall(data)[0].decode()
        # mediaBox = data.split(b'MediaBox')[1].split(b']')[0].strip().decode()
        result = mediaBox.split(' ')
        width = float(result[2])
        height = float(result[3].strip(']'))
        l = width/height
        print(p,l)


# just for debug
if __name__ == '__main__':
    args = parse_args()
    func = args.test
    locals()[func]()
