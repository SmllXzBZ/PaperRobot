import sys
import logging
import argparse
import datetime
from config import *
from src.util import banner, count_status_key_year, save_file
from src.app import get_one_pdf, run_years, get_pdf_from_google, get_pdf_from_url, run_bibtex


def parser_error(errmsg):
    banner()
    logging.info(("Usage: python " + sys.argv[0] + " [Options] use -h for help"))
    logging.error(("Error: " + errmsg))
    show_example()
    sys.exit()


# TODO
def check_configs(args):
    if not (args.conference or args.bibtex or args.title or args.url or args.all):
        errmsg = "参数设置错误"
        parser_error(errmsg)
        sys.exit()


def show_example():
    logging.info("使用示例:")
    logging.warning("""
                        基于Title下载论文
                            python run.py -t "A Large-scale Analysis of Email Sender Spoofing Attacks"
                        基于URL下载论文
                            python run.py -u "https://www.usenix.org/conference/usenixsecurity21/presentation/shen-kaiwen"
                        基于bib下载论文
                            python run.py -b bibtex/example.bib
                        获取NDSS 2021会议论文
                            python run.py -c ndss -s 2021 -e 2022
                        获取NDSS 2001-2021会议论文
                            python run.py -c ndss -s 2001 -e 2022
                        获取所有会议的bibtex文件
                            python run.py  --all bibtex
                        获取所有会议的pdf文件
                            python run.py  --all bibtex
                """)


def count_key_year(key, year):
    result = count_status_key_year(key, year)
    bibtex_num = len(result['bibtex'])
    pdf_num = len(result['pdf'])
    fail_num = len(result['fail'])
    for f in result['fail']:
        logging.debug("[-] 下载失败的论文:{}".format(f))
    return bibtex_num, pdf_num, fail_num


def show_key_years(key, year_start, year_end):
    total_bibtex = 0
    total_pdf = 0
    total_fail = 0
    name = LIB[key]
    for y in range(year_start, year_end):
        bibtex_num, pdf_num, fail_num = count_key_year(key, y)
        if bibtex_num == 0:
            logging.debug("[-] 会议{} {} 年度没有找到论文".format(name, y))
            continue
        logging.info(
            "[+] {} {}: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(name, y, bibtex_num, pdf_num,
                                                          fail_num))
        total_bibtex += bibtex_num
        total_pdf += pdf_num
        total_fail += fail_num
    logging.info(
        "[+] {} {}->{}: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(name, year_start, year_end, total_bibtex, total_pdf,
                                                          total_fail))
    return total_bibtex, total_pdf, total_fail


def show_all(year_start, year_end):
    total_bibtex = 0
    total_pdf = 0
    total_fail = 0
    for key in LIB:
        name = LIB[key]
        bibtex_num, pdf_num, fail_num = show_key_years(key, year_start, year_end)
        if bibtex_num == 0:
            logging.debug("[-] 会议{} 不存在， 没有找到论文".format(name))
            continue
        total_bibtex += bibtex_num
        total_pdf += pdf_num
        total_fail += fail_num
    logging.info(
        "[+] 所有下载: 共有{}篇论文\t成功下载:{}\t失败数量:{}".format(total_bibtex, total_pdf, total_fail))
    return total_bibtex, total_pdf, total_fail


def run():
    args = parse_args()
    check_configs(args)
    banner()
    if args.year_start is None:
        year_start = 2001
    else:
        year_start = int(args.year_start)

    if args.year_end is None:
        today = datetime.datetime.today()
        year_end = int(today.year)
    else:
        year_end = int(args.year_end)

    if args.mode == 's':
        if args.conference is None:
            show_all(year_start, year_end)
        else:
            show_key_years(args.conference, year_start, year_end)
    elif args.conference:
        run_years(args.conference, year_start, year_end)
    elif args.bibtex:
        bibtex_path = os.path.join(DATA_DIR, args.bibtex)
        get_one_pdf(bibtex_path)
    elif args.title:
        title = args.title
        logging.info("[+] 使用Google搜索该论文，获取对应pdf")
        result = get_pdf_from_google(title)
        if result:
            tmp_path = DATA_DIR + '/tmp/' + result['url'].split('/')[-1].replace('-', '_').replace('.pdf', '') + '.pdf'
            save_file(tmp_path, result['pdf'])
            logging.debug("[+] PDF Title: {}\t下载链接: {}".format(title, result['url']))
            logging.info("[+] 谷歌搜索获取成功\t Title:{}\t保存路径:{}".format(title, tmp_path))
            return result
        else:
            logging.warning("[-] 谷歌搜索获取失败...{}".format(title))
    elif args.url:
        url = args.url
        logging.info("[+] 基于URL获取对应pdf")
        result = get_pdf_from_url(url)
        if result:
            tmp_path = DATA_DIR + '/tmp/' + result['url'].split('/')[-1].replace('-', '_').replace('.pdf', '') + '.pdf'
            save_file(tmp_path, result['pdf'])
            logging.debug("[+] PDF URL: {}\t下载链接: {}".format(url, result['url']))
            logging.info("[+] 基于URL获取成功\t URL:{}\t保存路径:{}".format(url, tmp_path))
            return result
        else:
            logging.warning("[-] 基于URL获取失败...{}".format(url))
    elif args.all:
        # 下载所有
        if args.all == 'bibtex':
            for key in LIB:
                run_bibtex(key, year_start, year_end)
        elif args.all == 'pdf':
            for key in LIB:
                run_years(key, year_start, year_end)
    logging.info("[+] 已完成所有任务!")


# get_key_year_pdf
def parse_args():
    # parse the arguments
    parser = argparse.ArgumentParser(
        epilog='\tExample: \r\npython ' + sys.argv[0] + " ")
    parser.error = parser_error
    parser._optionals.title = "OPTIONS"
    # mode 下载模式
    # 下载的会议
    papers_choices = list(LIB.keys())
    parser.add_argument(
        '-m', '--mode', dest="mode", choices=['d', 's'], default='d', help="s:show info, d: download")
    parser.add_argument(
        '-c', '--conference', dest="conference", choices=papers_choices, default=None, help="The target conference.")
    parser.add_argument(
        '-s', '--year_start', dest="year_start", default=None, help="The start year of paper.")
    parser.add_argument(
        '-e', '--year_end', dest="year_end", default=None, help="The end year of paper.")
    parser.add_argument(
        '-b', '--bibtex', dest="bibtex", default=None, help="Download with bibtex file.")
    parser.add_argument(
        '-t', '--title', dest="title", default=None, help="Download with Google search.")
    parser.add_argument(
        '-u', '--url', dest="url", default=None, help="Dowanload with url.")
    # TODO 为了考虑不被banip 目前没考虑多进程+协程池。 如需请参考: https://moxiaoxi.info/python/2019/03/12/python/
    parser.add_argument(
        '--all', dest="all", choices=['bibtex', 'pdf'], default=None,
        help="Download all bibbex or papers，2001-2022 by default")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    run()
