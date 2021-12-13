import urllib3
import json
import random, time
from src.util import check_login, read_file, get_cookies_with_institution_login, save_file
from config import COOKIE_PATH,KEEP_PATH
from src.log import init_log
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# logger = init_log(KEEP_FILE)

def sleep():
    m = random.randint(1, 5)
    wait_time = m * 30
    print("[+] This test is finished, waiting for the next round...")
    for i in range(wait_time):
        print("[+] The next round is %d seconds later..." % (wait_time - i))
        time.sleep(1)



print("[+] Start Keeping Cookies....")
# init
data = read_file(COOKIE_PATH)
if len(data):
    cookies = json.loads(data)
else:
    cookies = {}
print("[+] Init Succ....")

while True:
    update = False
    url = "https://ieeexplore.ieee.org/Xplore/home.jsp"
    if 'ieee' in cookies and check_login(url, cookies['ieee']):
        print('[+] IEEE COOKIE Succ!')
    else:
        print('[-] IEEE COOKIE Fail, updating....')
        login_url = "https://ieeexplore.ieee.org/servlet/wayf.jsp?entityId=https://idp.tsinghua.edu.cn/idp/shibboleth&url=https%3A%2F%2Fieeexplore.ieee.org%2FXplore%2Fhome.jsp"
        cookies['ieee'] = get_cookies_with_institution_login(login_url)
        update = True
        print('[+] IEEE COOKIE Updating succ....')

    url = "https://dl.acm.org/magazines"
    if 'acm' in cookies and check_login(url, cookies['acm']):
        print('[+] ACM COOKIE Succ!')
    else:
        print('[-] ACM COOKIE Fail, updating....')
        login_url = "https://dl.acm.org/action/ssostart?idp=https%3A%2F%2Fidp.tsinghua.edu.cn%2Fopenathens&redirectUri=https%3A%2F%2Fdl.acm.org%2F"
        cookies['acm'] = get_cookies_with_institution_login(login_url)
        update = True
        print('[+] ACM COOKIE Updating succ....')

    url = "https://link.springer.com/chapter/10.1007/3-540-45474-8_11"
    if 'springer' in cookies and check_login(url, cookies['springer'], succ_flag='Download'):
        print("[+] Springer COOKIE Succ!")
    else:
        print('[-] Springer COOKIE Fail, updating....')
        login_url = "https://sp.springer.com/saml/login?idp=https://idp.tsinghua.edu.cn/openathens&targetUrl=https://link.springer.com/chapter/10.1007/978-3-030-00470-5_12"
        cookies['springer'] = get_cookies_with_institution_login(login_url)
        update = True
        print('[+] Springer COOKIE Updating succ....')
    if update:
        data = json.dumps(cookies).encode()
        save_file(COOKIE_PATH, data)
    sleep()
