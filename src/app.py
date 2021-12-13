import requests
import logging
import random
import time
from src.util import string_similar, read_file, read_bibtex, check_exist, save_file, save_fails, get_all_path
from config import *
from bs4 import BeautifulSoup
from urllib.parse import unquote
import re
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# TODO 使用修饰器重构retry类函数

# 通过doi从sci-hub获取pdf
def get_pdf_from_scihub(doi, retry=0):
    """
    :param doi: doi序列号，论文标识符号
    :param retry: 重试次数
    :return result: {} 表示获取失败， result={'pdf':pdf, 'url':url: 'info': info} info表示获取方式
    """

    # 随机从scihub url中获取一个地址，以防单个sci-hub拉黑我们IP
    scihub_url = SCIHUBS[random.randint(0, len(SCIHUBS) - 1)]
    target_url = scihub_url + doi

    # 重试了MAX_RETRY_TIMES次还是不行，就说明确实获取不到，直接返回None
    if retry > MAX_RETRY_TIMES:
        logging.warning("[-] get_pdf_from_doi 获取pdf失败! {}".format(target_url))
        return None

    cookies = {"_a_d3t6sf": "duqXaQSk6XiLtcot_bKCyL7n", "_ym_uid": "1603075292952182812",
               "session": "dedbc839caee868acb40180ebfe19fed", "_ym_isad": "1", "refresh": "1614235343.6448",
               "_ym_d": "1614235348", "__ddg1": "fOtEA8K4uTWqax8gA3rJ", "__ddg2": "izZ2MImUMd21JnWA"}
    session = requests.Session()

    try:
        # 从sci-hub中获取pdf的下载地址
        res = session.get(target_url, headers=HEADERS, cookies=cookies, verify=False)
        before = """<li><a href = # onclick = "location.href='"""
        after = """'">⇣ save</a></li>"""
        data = res.text

        # pdf下载地址获取失败
        if res.status_code == 404:
            logging.info("[-] 从sci-hub中获取下载地址失败 404，等待一会儿...，重新获取pdf!{}\t {}".format(target_url, retry))
            time.sleep(SLEEP_TIME)
            return get_pdf_from_scihub(doi, retry + 1)

        if before not in data:
            now_url = res.url
            # sci-hub可能会直接帮你重定向到官网，这个时候调用官网的方式
            if scihub_url not in now_url:
                logging.info("[+] SCI-HUB将链接重定向到其他网站....{}\t{}".format(target_url, now_url))
                return get_pdf_from_url(now_url, retry + 1)
            logging.info("[+] SCI-HUB获取下载地址失败，等待一会儿...，重新获取pdf!{}\t{}".format(target_url, retry))
            time.sleep(SLEEP_TIME)
            return get_pdf_from_scihub(doi, retry + 1)

        pdf_url = data.split(before)[1].split(after)[0]
        # 规范化pdf目标地址
        if pdf_url.startswith('//'):
            pdf_url = 'https:' + pdf_url
        elif pdf_url.startswith('/'):
            pdf_url = 'https:/' + pdf_url
        logging.info("[+] 成功获取下载地址:{}\t{}".format(target_url, pdf_url))
        pdf = get_raw_pdf(pdf_url)
        # 有时候获取的pdf链接无法获取了，也需要重新获取链接
        if not pdf:
            logging.warning("[-] SCI-HUB下载仍然失败，重试...{}\t{}".format(target_url, pdf_url))
            return get_pdf_from_scihub(doi, retry + 1)
        logging.info("[+] get_pdf_from_doi 获取pdf成功! {}".format(target_url))
        result = {"url": pdf_url, "pdf": pdf, "info": "get_pdf_from_doi({doi}, {retry})".format(doi=doi, retry=retry)}
        return result
    except Exception as e:
        logging.error("[-] {}".format(e))
        logging.warning("[-] ProxyError...等待一会儿重试 重新尝试获取...{}\t{}".format(target_url, retry))
        time.sleep(SLEEP_TIME)
        return get_pdf_from_scihub(doi, retry + 1)

# 从官网链接上获取pdf
def get_pdf_from_url(url, retry=0):
    """
    :param url: 获取pdf的网站
    :param retry: 重试次数
    :return:
    """
    # 规范化URL
    url = url.replace("\\", "")
    url = unquote(url, 'utf-8')

    # 重试次数判断
    if retry > MAX_RETRY_TIMES:
        logging.warning("[-] get_pdf_from_url 获取pdf失败! {}".format(url))
        return None

    # TODO wp.internetsociety.org 网站目前无法访问跳过
    # if "wp.internetsociety.org" in url:
    # logging.warning("[-] wp.internetsociety.org 网站目前无法访问,跳过....{}".format(url))
    # return None

    # TODO zip后缀的论文直接忽略
    if url.endswith('.zip'):
        logging.info("[-] pdf链接为zip，忽略...{}".format(url))
        return None

    # 有些bibtex的url后缀是pdf，直接获取
    if url.endswith('.pdf'):
        logging.debug("[+] 目标地址为pdf链接，直接访问....{}".format(url))
        pdf = get_raw_pdf(url)
        if not pdf:
            return None
        result = {"url": url, "pdf": pdf, "info": "get_pdf_from_url({url}, {retry})".format(url=url, retry=retry)}
        return result

    session = requests.Session()
    cookies = get_cookies_with_url(url)

    res = session.get(url, headers=HEADERS, cookies=cookies, verify=False, proxies=PROXIES)
    # 可能会重定向，尝试使用新的url获取
    if retry < 1 and url != res.url:
        logging.warning("[-] URL发生重定向 {}  -->  {}".format(url, res.url))
        # IEEE 站点获取
        if 'ieee.org/' in res.url:
            logging.debug("[+] 尝试通过ieee.org获取...")
            result = get_pdf_from_ieee(res.url)
            if result:
                logging.debug("[+] 通过IEEE站点获取pdf成功... {}".format(res.url))
                return result
            logging.debug("[-] 通过IEEE站点获取pdf失败... {}".format(res.url))
            return None
        # dl.acm.org 站点获取方式
        elif ('dl.acm.org' in res.url or 'doi.org' in res.url) and 'citation.cfm' not in res.url:
            logging.debug("[+] 尝试通过dl.acm.org获取...")

            result = get_pdf_from_dl_acm(res.url)
            if result:
                logging.debug("[+] 通过get_pdf_from_dl_acm获取成功...{}\t".format(res.url))
                return result
            logging.info("[-] 通过get_pdf_from_dl_acm获取失败...{}\t ".format(res.url))
            return None
        # springer
        elif 'springer.com' in res.url:
            logging.debug("[+] 尝试通过springer.com获取...")
            result = get_pdf_from_springer(res.url)
            if result:
                logging.debug("[+] 通过get_pdf_from_springer获取成功...{}\t".format(res.url))
                return result
            logging.info("[-] 通过get_pdf_from_springer获取失败...{}\t ".format(res.url))
            return None
        logging.info("[+] 重定向到其他站点...{}".format(res.url))
        url = res.url

    if res.status_code != 200:
        logging.warning("[-] 官网URL访问状态非200,等待一会儿重试..{}\t{}".format(url, retry))
        time.sleep(SLEEP_TIME)
        return get_pdf_from_url(url, retry + 1)

    html = res.text
    soup = BeautifulSoup(html, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        link = a['href']
        if 'pdf' in link:
            if not (link.startswith('https://') or link.startswith('http://')):
                if link.startswith("/") or link.startswith("./"):
                    base_url = "https://" + url.split('//')[1].split('/')[0]
                else:
                    # 得到base url
                    base_url = url[:url.rfind('/') + 1]
                # print(base_url)
                link = base_url + link

            # TODO 先把slide屏蔽, 把错误信息更正的也屏蔽了
            if 'slides' in link or 'slides' in a.text.lower():
                logging.debug("[+] 暂不访问slides: {}".format(link))
                continue
            if '_errata_' in link:
                logging.debug("[+] 暂不访问_errata_数据: {}".format(link))
                continue
            # # 把链接不是官网的删除
            # gov_host = url.split('://')[1].split('/')[0]
            # if gov_host.startswith('www.'):
            #     gov_host = gov_host.split('www.')[1]
            # if gov_host not in link:
            #     # logging.debug(gov_host, link, "非官网链接")
            #     logging.debug("[-] 忽略非官网链接:{}".format(link))
            #     continue
            links.append(link)
    l = len(links)
    # 如果链接超过2个，说明猜测失败
    # assert l <= 2
    if l > 0:
        # TODO 多个链接，取返回值最长的pdf
        pdf = None
        pdf_url = None
        for link in links:
            tmp_pdf = get_raw_pdf(link)
            if tmp_pdf is None:
                continue
            elif pdf is None:
                pdf = tmp_pdf
                pdf_url = link
            elif len(tmp_pdf) > len(pdf):
                pdf = tmp_pdf
                pdf_url = link
        if pdf is None and pdf_url is None:
            logging.warning("[-] 官网获取的多个URL均无法获取PDF...")
            return None
        logging.info("[+] get_pdf_from_url 从官网获取pdf链接成功,url:{}".format(pdf_url))
        result = {"url": pdf_url, "pdf": pdf, "info": "get_pdf_from_url({url}, {retry})".format(url=url, retry=retry)}
        return result
    else:
        # 通过html中的doi来获取
        dois = re.compile(r'doi\.org/10.\d{4,9}/[-._;()/:A-Za-z0-9]+[a-zA-Z0-9]', re.S).findall(html)
        dois = list(set(dois))
        for d in dois:
            doi = d[len('doi.org/'):]
            result = get_pdf_from_scihub(doi, retry + 1)
            # doi 非法，无法从sci-hub获取
            if result:
                logging.info("[+] 通过DOI获取成功...{}\t{}".format(doi, url))
                return result
            logging.warning("[-] 该DOI无法从scihub获取...{}\t{}".format(doi, url))
    logging.warning("[-] get_pdf_from_url {} 获取pdf失败...".format(url))
    return None


def get_pdf_with_doi(doi):
    # 再通过sci-hub 获取
    result = get_pdf_from_scihub(doi)
    # doi 非法，无法从sci-hub获取
    if result:
        logging.info("[+] 通过get_pdf_from_scihub获取成功...{}\t".format(doi))
        return result
    logging.warning("[-] URL中DOI 非法，无法获取...{}".format(doi))
    return None


# 从springer获取pdf
def get_pdf_from_springer(url):
    # url = 'https://doi.org/10.1007/3-540-45474-8_9'
    # url = "https://link.springer.com/chapter/10.1007%2F3-540-45474-8_9"
    # url = "https://link.springer.com/content/pdf/10.1007%2F3-540-45474-8_9.pdf"
    try:
        number = url.split('chapter/')[1]
    except Exception as e:
        number = url.split('/book/')[1]
    base_url = "https://link.springer.com/content/pdf/{}.pdf"
    target_url = base_url.format(number)

    # get_pdf
    pdf = get_raw_pdf(pdf_url=target_url, max_retry_times=1)
    if not pdf:
        logging.warning("[-] 从link.springer获取pdf失败...{}".format(target_url))
        return None
    result = {'pdf': pdf, 'url': target_url, 'info': 'get_pdf_from_springer({url})'.format(url=url)}
    logging.info("[+] 从link.springer获取pdf成功...{}".format(target_url))
    return result


# 从ieee网站获取pdf
def get_pdf_from_ieee(url):
    arnumber = url.split('document/')[1].strip('/')
    base_url = "https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={}&ref=1"
    target_url = base_url.format(arnumber)

    # get_pdf
    pdf = get_raw_pdf(pdf_url=target_url, max_retry_times=1)
    if not pdf:
        logging.warning("[-] 从ieee.org获取pdf失败...{}".format(target_url))
        return None
    result = {'pdf': pdf, 'url': target_url, 'info': 'get_pdf_from_ieee({url})'.format(url=url)}
    logging.info("[+] 从ieee.org获取pdf成功...{}".format(target_url))
    return result


# 从dl.acm网站获取pdf
def get_pdf_from_dl_acm(url):
    doi = re.compile(r'10.\d{4,9}/[-._;()/:A-Za-z0-9]+[a-zA-Z0-9]', re.S).findall(url)[0]
    base_url = "https://dl.acm.org/doi/pdf/"
    # 清华代理
    # base_url = "http://eproxy2.lib.tsinghua.edu.cn/rwt/2/https/MSXC6ZLDNVYG86UH/doi/pdf/"
    target_url = base_url + doi
    # logging.info(target_url)
    pdf = get_raw_pdf(pdf_url=target_url, max_retry_times=1)
    if not pdf:
        logging.warning("[-] 从dl_acm获取pdf失败...{}".format(target_url))
        return None
    result = {'pdf': pdf, 'url': target_url, 'info': 'get_pdf_from_dl_acm({url})'.format(url=url)}
    logging.info("[+] 从dl_acm获取pdf成功...{}".format(target_url))
    return result


# 从Google搜索获取对应pdf
def get_pdf_from_google(title):
    """
    :param url:
    :return:
    """
    session = requests.Session()
    query = "{title} filetype:pdf".format(title=title)
    paramsGet = {"sourceid": "chrome", "q": query, "rlz": "1C5CHFA_enHK852HK852",
                 "oq": query, "aqs": "chrome..69i57.12255j0j7", "ie": "UTF-8"}
    url = 'https://www.google.com/search'
    cookies = get_cookies_with_url(url)
    response = session.get(url, params=paramsGet, headers=HEADERS, cookies=cookies,
                           verify=False)
    # print("Status code:   %i" % response.status_code)
    # print("Response body: %s" % response.content)
    assert response.status_code == 200
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    count = 0
    for g in soup.find_all('div', class_='g'):
        a = g.find('a', href=True)
        link = a['href']

        # TODO 先把slide屏蔽
        if 'slides' in link:
            logging.debug("暂不下载slides:{}".format(link))
            continue
        try:
            span = a.text.split('...')[0].split(' › ')[0]
            # print(link, title, span)
            if string_similar(span, title):
                logging.debug("[+] get_pdf_from_google 获取pdf成功!  {}\t query:{}\tspan:{}\t".format(link, query, span))
                pdf = get_raw_pdf(link)
                if not pdf:
                    logging.debug(
                        "[-] get_pdf_from_google pdf无法抓取.. {}\t query:{}\tspan:{}\t".format(link, query, span))
                    continue
                result = {"url": link, "pdf": pdf,
                          "info": "get_pdf_from_google({title})".format(title=title)}
                return result
        except Exception as e:
            logging.error("get_pdf_from_google {}".format(e))
            continue
        count += 1
        # 只寻找搜索到的前几个pdf
        if count > 5:
            break
    logging.warning("[-] get_pdf_from_google 获取失败! {}".format(query))
    return None


# 依据url获取cookie
def get_cookies_with_url(url):
    data = read_file(COOKIE_PATH)
    cookies = json.loads(data)
    if 'acm.org' in url:
        return cookies['acm']
    elif 'ieee.org' in url:
        return cookies['ieee']
    elif 'springer' in url:
        return cookies['springer']
    elif 'google.com' in url:
        return cookies['google']
    elif 'tsinghua.edu.cn' in url:
        return cookies['tsinghua.edu.cn']
    return {'default': "cookies"}


# 原生的获取pdf代码
def get_raw_pdf(pdf_url, retry=0, max_retry_times=MAX_RETRY_TIMES):
    session = requests.Session()
    cookies = get_cookies_with_url(pdf_url)
    # 忽略重定向多次
    try:
        response = session.get(pdf_url, headers=HEADERS, cookies=cookies, verify=False, proxies=PROXIES)
    except Exception as e:
        logging.error(e)
        return None
    # print(cookies)
    # print(response.headers)
    # 重试三次失败直接返回None
    if retry > max_retry_times:
        logging.warning("[-] get_raw_pdf获取pdf失败...{} ".format(pdf_url))
        return None
    if response.status_code != 200:
        logging.warning("[-] 访问状态码非200，等待一段时间后,重试第{}次...{} ".format(retry, pdf_url))
        time.sleep(SLEEP_TIME)
        return get_raw_pdf(pdf_url, retry + 1)

    content_type = response.headers['Content-Type']
    if '/pdf' not in content_type and 'octet-stream' not in content_type:
        logging.warning("[-] {} 返回数据非PDF格式，等待一段时间后,重试第{}次...".format(pdf_url, retry))
        return get_raw_pdf(pdf_url, retry + 1)

    pdf = response.content
    logging.debug("[+] 成功获取pdf！{}".format(pdf_url))
    return pdf


# 从dblp中获取一个bibtex
def get_one_bibtex_from_url(url):
    session = requests.Session()
    cookies = {"dblp-search-mode": "c", "dblp-dismiss-new-feature-2019-08-19": "5"}
    try:
        res = session.get(url, headers=HEADERS, cookies=cookies, verify=False)
    except Exception as e:
        logging.error("[-] {}".format(e))
        logging.warning("[-] get_one_bibtex ProxyError...等待一会儿重试...")
        time.sleep(SLEEP_TIME)
        logging.warning("[-] 重新尝试获取{}...".format(url))
        return get_one_bibtex_from_url(url)
    data = res.text
    assert res.status_code == 200
    bibtex = re.compile(r'@[in]*proceedings{.*}', re.S).findall(data)[0]
    return bibtex


#  得到一个会议某一年的所有会议信息
def get_volume_papers(key, year):
    # https://dblp.uni-trier.de/search/publ/api?q=toc%3Adb/conf/sp/sp2020.bht%3A&h=1000&format=json
    name = LIB[key]
    session = requests.Session()
    cookies = {"dblp-search-mode": "c", "dblp-dismiss-new-feature-2019-08-19": "1"}
    target_url = "https://dblp.uni-trier.de/search/publ/api?q=toc%3Adb/conf/{key}/{key}{year}.bht%3A&h=1000&format=json".format(
        key=key, year=year)

    # todo 例外处理一下
    if key == 'asiaccs':
        target_url = "https://dblp.uni-trier.de/search/publ/api?q=toc%3Adb/conf/ccs/{key}{year}.bht%3A&h=1000&format=json".format(
            key=key, year=year)
    try:
        #todo retry
        res = session.get(target_url, headers=HEADERS, cookies=cookies, verify=False)
        data = res.content
        assert res.status_code == 200
        papers = json.loads(data)['result']['hits']['hit']
        # 一般最后一个是论文会议总名称，所以数量-1
        papers = papers[:-1]
    except Exception as e:
        logging.error(e)
        logging.warning("[-] 会议列表获取失败... {}\t{}\t{}".format(name, year, target_url))
        return []
    logging.info("[+] {} {} 会议列表获取成功，共{}篇论文...".format(name, year, len(papers)))
    return papers


# 利用crossrefAPI 获取指定标题的DOI
def find_doi_with_crossref_api(title):
    session = requests.Session()
    paramsGet = {"rows": "10", "query.bibliographic": title}
    headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
               "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": "1",
               "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:84.0) Gecko/20100101 Firefox/84.0",
               "Connection": "close", "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
               "Accept-Encoding": "gzip, deflate"}
    response = session.get("https://api.crossref.org/works", params=paramsGet, headers=headers, verify=False)
    # print("Status code:   %i" % response.status_code)
    # print("Response body: %s" % response.content)
    assert response.status_code == 200
    data = json.loads(response.text)
    count = 0
    for item in data['message']['items']:
        # 利用相似度判定是否找到对应的论文
        t = item['title'][0]
        if string_similar(title, t):
            doi = item['DOI']
            info = "[+] 找到对应的论文DOI\t原始Title:{}\t新Title:{}\tDOI:{}\t".format(title, t, doi)
            logging.warning(info)
            return doi
        count += 1
        # 只寻找搜索到的前几个文件
        if count > 5:
            break
    logging.warning("[-] 论文DOI寻找失败,{}".format(title))
    return None


# 利用crossrefAPI 获取指定标题的DOI
def find_links_with_crossref_api(title):
    session = requests.Session()
    paramsGet = {"rows": "6", "query.bibliographic": title}
    headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
               "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": "1",
               "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:84.0) Gecko/20100101 Firefox/84.0",
               "Connection": "close", "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
               "Accept-Encoding": "gzip, deflate"}
    response = session.get("https://api.crossref.org/works", params=paramsGet, headers=headers, verify=False)
    # print("Status code:   %i" % response.status_code)
    # print("Response body: %s" % response.content)
    assert response.status_code == 200
    data = json.loads(response.text)
    links = []
    for item in data['message']['items']:
        # 利用相似度判定是否找到对应的论文
        t = item['title'][0]
        if string_similar(title, t):
            if 'URL' in item:
                links.append(item['URL'])
            if 'link' in item:
                for l in item['link']:
                    links.append(l['URL'])
            info = "[+] 找到对应的论文links\t原始Title:{}\t新Title:{}\t links:{}".format(title, t, links)
            logging.warning(info)
            return links
    logging.warning("[-] 论文DOI寻找失败,{}".format(title))
    return None


# 通过UI界面来搜索获取数据
def find_url_with_crossref_ui(title):
    query = title
    session = requests.Session()
    paramsGet = {"q": query, "from_ui": "yes"}
    headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
               "Cache-Control": "no-cache", "Upgrade-Insecure-Requests": "1",
               "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:86.0) Gecko/20100101 Firefox/86.0",
               "Connection": "close", "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
               "Accept-Encoding": "gzip, deflate", "Pragma": "no-cache"}
    cookies = {"_pk_id.17.755c": "ce558e6a502a7f2e.1616243541.",
               "rack.session": "bac47113a590129facedb4e75533c66983714473043264719e936b80d46b59f7",
               "_pk_ses.17.755c": "1"}
    response = session.get("https://search.crossref.org/", params=paramsGet, headers=headers, cookies=cookies,
                           verify=False)

    # print("Status code:   %i" % response.status_code)
    # print("Response body: %s" % response.content)
    assert response.status_code == 200
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    count = 0
    for d in soup.find_all('td', class_="item-data"):
        info = d.find('p', class_='lead').text.strip()
        a = d.find('a', href=True)
        href = a['href']
        if string_similar(title, info):
            info = "[+] 找到对应的论文URL\t 原始Title:{}\t新Title:{}\tURL:{}".format(title, info, href)
            logging.warning(info)
            return href
        count += 1
        # 只寻找搜索到的前几个文件
        if count > 5:
            break
    logging.warning("[-] 论文URL寻找失败,{}".format(title))
    return None


def get_pdf_based_bibtex(bibdata):
    b = bibdata.entries[0]
    title = b['title'].replace('\n', '').replace('\\', '')
    doi = None
    url = None
    if 'url' in b:
        url = b['url']

    if 'doi' in b:
        doi = b['doi']

    if url and not doi:
        url = b['url']
        dois = re.compile(r'10.\d{4,9}/[-._;()/:A-Za-z0-9]+[a-zA-Z0-9]', re.S).findall(url)
        if len(dois):
            doi = dois[0]

    if url:
        # 尝试官网获取
        logging.debug("[+] 尝试通过官网获取...{}".format(url))
        result = get_pdf_from_url(url)
        if result:
            logging.info("[+] 官网获取成功...{}".format(url))
            return result
        else:
            logging.warning("[-] 官网获取失败...{}".format(url))
    else:
        logging.warning("[-] 该bibdata无url，跳过...")

    if not doi:
        logging.warning("[-] 未找到doi, 尝试通过crossref_doi获取...{}".format(title))
        doi = find_doi_with_crossref_api(title)

    # 基于doi获取
    if doi:
        logging.debug("[+] 尝试通过DOI获取...{}".format(doi))
        result = get_pdf_with_doi(doi)
        if result:
            logging.info("[+] DOI获取成功...{}".format(doi))
            return result
        else:
            logging.warning("[-] DOI获取失败...{}".format(doi))
    else:
        logging.warning("[+] 该bibdata没找到doi序列，跳过...")

    # 通过谷歌搜索获取
    logging.debug("[+] 尝试通过谷歌搜索获取...{}".format(title))
    result = get_pdf_from_google(title)
    if result:
        logging.info("[+] 谷歌搜索获取成功...{}".format(title))
        return result
    else:
        logging.warning("[-] 谷歌搜索获取失败...{}".format(title))

    # 通过crossref_ui 获取
    logging.debug("[+] 尝试通过crossref_ui获取...{}".format(title))
    new_url = find_url_with_crossref_ui(title)
    if new_url and new_url != url:
        logging.debug("[+] 获取url成功...{} {}".format(title, new_url))
        logging.debug("[+] 再次尝试通过官网获取...{}".format(new_url))
        result = get_pdf_from_url(new_url)
        if result:
            logging.info("[+] 官网获取成功...{}".format(new_url))
            return result
        else:
            logging.warning("[-] 官网获取失败...{}".format(new_url))
    else:
        logging.warning("[-] 获取url失败...{}".format(title))

    # 准确率不高，暂时废弃
    # # 通过crossref_api 获取link
    # logging.warning("[+] 尝试通过crossref_links获取...{}".format(title))
    # links = find_links_with_crossref_api(title)
    # if links:
    #     logging.warning("[+] 获取links成功...{}".format(links))
    #     for l in links:
    #         logging.warning("[+] 再次尝试通过官网获取...{}".format(l))
    #         result = get_pdf_from_url(l)
    #         if result:
    #             logging.warning("[+] 官网获取成功...{}".format(l))
    #             return result
    #         else:
    #             logging.warning("[-] 官网获取失败...{}".format(l))
    # else:
    #     logging.warning("[-] crossref_links获取失败...{}".format(title))

    info = "[-] 尝试了所有方法，该论文仍然无法获取\t标题:{}".format(title)
    logging.warning(info)
    return None


# 得到某个会议，某年度的所有bibtex
def get_key_year_bibtex(key, year):
    name = LIB[key]
    papers = get_volume_papers(key, year)
    if not len(papers):
        logging.warning("[+] {}会议没有{}年度的会议".format(name, year))
        return False
    for i in range(len(papers)):
        #  从dblp获取bibtex内容
        bibtex_url = papers[i]['info']['url'] + '.html?view=bibtex'
        bibtex_path = DATA_DIR + '/bibtex/{name}/{year}/{num}.bib'.format(name=name, year=year, num=i)
        if check_exist(bibtex_path):
            logging.debug("[-] {} bib 已存在! 继续...".format(bibtex_path))
            continue
        logging.debug("[+] 尝试获得 {}!".format(bibtex_path))
        one_bibtex = get_one_bibtex_from_url(bibtex_url)
        logging.debug("[+] 获取成功！等待{}秒...".format(SLEEP_TIME))
        save_file(bibtex_path, one_bibtex.encode())
        time.sleep(SLEEP_TIME)
    return True




def get_one_pdf(bibtex_path):
    pdf_path = bibtex_path.replace("bibtex", "pdf").replace('.bib', '.pdf')
    info_path = bibtex_path.replace('bibtex', 'info').replace('.bib', '.txt')
    logging.debug("[+] 尝试获取pdf: {}...".format(bibtex_path))
    # read title
    bibdata = read_bibtex(bibtex_path)
    b = bibdata.entries[0]
    title = b['title'].replace('\n', '').replace('\\', '')

    result = get_pdf_based_bibtex(bibdata)
    if result:
        pdf = result['pdf']
        info = {'pdf_url': result['url'], 'title': title, 'pdf_path': pdf_path, 'info_path': info_path,
                'bibtex_path': bibtex_path, 'info': result['info']}
        save_file(info_path, json.dumps(info).encode())
        save_file(pdf_path, pdf)
        logging.debug("[+] 获取成功... bib: {}\tpdf_path: {}".format(bibtex_path, pdf_path))
        return True
    else:
        info = "[-] 论文无法获取，请人工获取...\t bib路径:{}\t PDF路径:{}\t".format(bibtex_path, pdf_path)
        logging.warning(info)
        save_fails(info)
    return False


# 基于本地的bibtex获取对应的pdf
def get_key_year_pdf(key, year):
    name = LIB[key]
    dir_path = 'bibtex/{name}/{year}/'.format(name=name, year=year)
    end = get_all_path(dir_path)
    for i in end:
        bibtex_path = dir_path + i
        pdf_path = bibtex_path.replace("bibtex", "pdf").replace('.bib', '.pdf')
        if check_exist(pdf_path):
            logging.debug("[-] {} 已经存在，继续...".format(pdf_path))
            continue
        get_one_pdf(bibtex_path)
    return True


# 下载对应会议的论文pdf和bibtex
def run_years(key, year_start, year_end):
    for i in range(year_start, year_end):
        run_one_year(key, i)


def get_one_bibtex(url, bibtex_path):
    #  从dblp获取bibtex内容
    bibtex_url = url + '.html?view=bibtex'
    if check_exist(bibtex_path):
        logging.debug("[-] {} bib 已存在! 继续...".format(bibtex_path))
        return
    logging.debug("[+] 尝试获得bib: {}!".format(bibtex_path))
    one_bibtex = get_one_bibtex_from_url(bibtex_url)
    logging.debug("[+] 获取成功！等待{}秒...".format(SLEEP_TIME))
    save_file(bibtex_path, one_bibtex.encode())


def run_one_year(key, year):
    name = LIB[key]
    logging.info("[+] 尝试获取{}会议{}年度的Bibtex".format(name, year))
    papers = get_volume_papers(key, year)
    if not len(papers):
        logging.error("[-] {}会议没有{}年度的会议".format(name, year))
        return False
    for i in range(len(papers)):
        bibtex_path = DATA_DIR + '/bibtex/{name}/{year}/{num}.bib'.format(name=name, year=year, num=i)
        get_one_bibtex(papers[i]['info']['url'], bibtex_path)
        get_one_pdf(bibtex_path)


# 获取所有的bibtex
def run_bibtex(key, year_start, year_end):
    name = LIB[key]
    for i in range(year_start, year_end):
        logging.info("[+] 尝试获取Bibtex... {} {}".format(name, i))
        if get_key_year_bibtex(key, i):
            logging.info("[+] Bibtex获取成功... {} {} ".format(name, i))
