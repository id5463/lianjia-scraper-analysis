"""
链家二手房爬虫模块

用法一（命令行）：
    python scrape_lianjia.py --city pds --count 99

用法二（模块导入）：
    from scrape_lianjia import crawl
    result = crawl(city='pds', count=99)

参数说明：
    city  : 链家城市拼音缩写，如 pds / bj / sh / sz ...
    count : 目标爬取条数，默认 99
"""

import time
import re
import csv
import winsound
import ctypes
import os
import argparse
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── 验证码处理 ──────────────────────────────────────────────

user32 = ctypes.windll.user32
VK_MENU = 0x12


def wait_alt_key():
    print('(等待按 Alt 键继续...)')
    while not (user32.GetAsyncKeyState(VK_MENU) & 1):
        time.sleep(0.3)


def check_captcha(text):
    return bool(re.search(
        r'\u9a8c\u8bc1|\u5b89\u5168\u9a8c\u8bc1|captcha|\u9a8c\u8bc1\u7801|verify|\u4eba\u673a',
        text, re.I
    ))


def handle_captcha(driver):
    body = driver.find_element(By.TAG_NAME, 'body').text
    if not check_captcha(body):
        return
    for _ in range(5):
        winsound.Beep(880, 300)
        time.sleep(0.2)
    print('[验证码] 检测到验证码！请在浏览器中手动通过验证，然后按 Alt 键。')
    wait_alt_key()
    time.sleep(3)
    body = driver.find_element(By.TAG_NAME, 'body').text
    if check_captcha(body):
        print('[验证码] 仍然被拦截，请再次验证，然后按 Alt 键。')
        wait_alt_key()
        time.sleep(3)

# ── 核心爬取函数 ─────────────────────────────────────────────

def crawl(city='pds', count=99):
    """
    爬取链家指定城市的二手房数据。

    参数：
        city  : 链家城市拼音，如 'pds'（平顶山）、'bj'（北京）
        count : 目标条数

    返回：
        dict: {"csv_path": str, "records": int}
    """
    # ── 自动生成不覆盖的 CSV 文件名 ──
    base_dir = os.path.dirname(os.path.abspath(__file__))
    base_name = f'{city}_houses'
    csv_path = os.path.join(base_dir, f'{base_name}.csv')

    if os.path.exists(csv_path):
        # 查找已有编号文件，确定下一个编号
        existing = glob.glob(os.path.join(base_dir, f'{base_name}_*.csv'))
        max_n = 0
        for fpath in existing:
            fname = os.path.basename(fpath)
            m = re.search(rf'{re.escape(base_name)}_(\d+)\.csv$', fname)
            if m:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
        csv_path = os.path.join(base_dir, f'{base_name}_{max_n + 1}.csv')

    fieldnames = ['floor', 'year', 'area', 'layout', 'price']

    # 新建文件并写表头
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
    print(f'[输出文件] {csv_path}')

    # ── 启动浏览器 ──
    opt = Options()
    opt.binary_location = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
    opt.add_argument('--disable-blink-features=AutomationControlled')
    opt.add_experimental_option('excludeSwitches', ['enable-automation'])
    opt.add_experimental_option('useAutomationExtension', False)

    svc = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=svc, options=opt)

    # ── 开始爬取 ──
    rows = 0
    pn = 1

    while rows < count:
        if pn == 1:
            url = f'https://{city}.ke.com/ershoufang/'
        else:
            url = f'https://{city}.ke.com/ershoufang/pg{pn}/'

        print(f'\n[翻页 {pn}] {url}')
        driver.get(url)
        time.sleep(4)

        handle_captcha(driver)

        items = driver.find_elements(By.CSS_SELECTOR, '.sellListContent > li')
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, '[class*="info clear"]')

        page_had_items = False
        for it in items:
            if rows >= count:
                break
            try:
                it.find_element(By.CSS_SELECTOR, '.title a')
            except:
                continue

            page_had_items = True
            item_data = {'floor': '', 'year': '', 'area': '', 'layout': '', 'price': ''}

            # ── 从 houseInfo 提取所有字段 ──
            # 典型格式（竖线分隔 6~7 段）：
            #   户型 | 面积 | 朝向 | 装修 | 楼层 | 年份 | 建筑类型
            #   例: "2室1厅 | 87.12平米 | 西 | 其他 | 中楼层(共6层) | 2010年 | 板塔结合"
            try:
                hi = it.find_element(By.CSS_SELECTOR, '.houseInfo')
                segs = [s.strip() for s in hi.text.split('|')]
                n = len(segs)

                if n >= 6:
                    # ── 链家格式 (bj.lianjia.com) ──
                    # 户型 | 面积 | 朝向 | 装修 | 楼层 | 年份 | 建筑类型
                    m = re.search(r'(\d+)室(\d+)厅', segs[0])
                    if m:
                        item_data['layout'] = str(int(m.group(1)) + int(m.group(2)))
                    m = re.search(r'(\d+(?:\.\d+)?)平米', segs[1])
                    if m:
                        item_data['area'] = m.group(1)
                    m = re.search(r'共(\d+)层', segs[4])
                    if m:
                        item_data['floor'] = m.group(1)
                    m = re.search(r'(\d{4})年', segs[5])
                    if m:
                        item_data['year'] = m.group(1)

                elif n >= 4 and re.search(r'^\d{4}年$', segs[1]):
                    # ── 贝壳格式A：楼层 | 年份 | 户型 | 面积 | 朝向 ──
                    m = re.search(r'共(\d+)层', segs[0])
                    if m:
                        item_data['floor'] = m.group(1)
                    m = re.search(r'(\d{4})年', segs[1])
                    if m:
                        item_data['year'] = m.group(1)
                    m = re.search(r'(\d+)室(\d+)厅', segs[2])
                    if m:
                        item_data['layout'] = str(int(m.group(1)) + int(m.group(2)))
                    m = re.search(r'(\d+(?:\.\d+)?)平米', segs[3])
                    if m:
                        item_data['area'] = m.group(1)

                else:
                    # ── 贝壳格式B：楼层+户型 | 面积 | 朝向 ──
                    m = re.search(r'共(\d+)层', segs[0])
                    if m:
                        item_data['floor'] = m.group(1)
                    m = re.search(r'(\d+)室(\d+)厅', segs[0])
                    if m:
                        item_data['layout'] = str(int(m.group(1)) + int(m.group(2)))
                    if n > 1:
                        m = re.search(r'(\d+(?:\.\d+)?)平米', segs[1])
                        if m:
                            item_data['area'] = m.group(1)
            except:
                pass

            # ── 总价 → 纯数字 (61.8万 → 61.8)
            try:
                pe = it.find_element(By.CSS_SELECTOR, '.totalPrice')
                raw = pe.text.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                m = re.search(r'(\d+(?:\.\d+)?)', raw)
                if m:
                    item_data['price'] = m.group(1)
            except:
                pass

            # 跳过无年份数据的房源（转用MICE插补，此处改为保留）
            # 所有数据都保留，包括无年份的

            rows += 1

            with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
                w = csv.DictWriter(f, fieldnames=fieldnames)
                w.writerow(item_data)

            print(f'  #{rows}: {item_data["layout"]} | {item_data["area"]} | {item_data["floor"]} | {item_data["year"]} | {item_data["price"]}')

        if not page_had_items:
            print('[结束] 本页无数据，停止爬取。')
            break

        pn += 1

    driver.quit()
    print(f'\n[完成] 共 {rows} 条，保存至: {csv_path}')
    return {'csv_path': csv_path, 'records': rows}


# ── 命令行入口 ──────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='链家二手房爬虫')
    parser.add_argument('--city', default='pds', help='城市拼音缩写，如 pds / bj / sh (默认: pds)')
    parser.add_argument('--count', type=int, default=99, help='目标爬取条数 (默认: 99)')
    args = parser.parse_args()
    crawl(city=args.city, count=args.count)
