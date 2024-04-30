import logging
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests
import time
from urllib.parse import urlencode
import asyncio
from lxml import etree
from urllib.parse import unquote
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import uuid

app = Flask(__name__)
flask_port = os.environ.get('FLASK_PORT', 8900)
service = None
driver = None
service_web = None
driver_web = None

service_webcut = None
driver_webcut = None

if os.name == "posix":  # POSIX是类Unix系统，包括macOS和Linux
    screenshot_dir = os.path.expanduser("/tmp/localimage/")
    chromediver_path = os.environ.get('CHROME_DRIVER_PATH', r'/Users/fangjiefeng/Dev/tools/chromedriver_mac64/chromedriver')
else:  # 针对Windows系统
    screenshot_dir = os.path.expandvars("C:\\Users\\Public\\tmp\\localimage\\")
    chromediver_path = os.environ.get('CHROME_DRIVER_PATH', r'C:\Users\Public\python\chromedriver.exe')


@app.route('/webcut', methods=['GET'])
def webcut():
    global driver_webcut, service_webcut
    url = request.args.get('url')
    filepath = None
    if url:
        try:
            if (driver_webcut == None or service_webcut == None):
                chrome_options = Options()
                chrome_options.add_argument("--headless")  # 无头模式，不打开浏览器界面
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument('--ignore-certificate-errors')
                chrome_options.add_argument("--window-size=1280,720")
                service_webcut = webdriver.chrome.service.Service(executable_path=chromediver_path)
                driver_webcut = webdriver.Chrome(service=service_webcut, options=chrome_options)
            driver_webcut.get(url)

            WebDriverWait(driver_webcut, 10).until(
                lambda driver_webcut: driver_webcut.execute_script("return document.readyState;") == "complete"
            )
            driver_webcut.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            # 使用 JavaScript 获取页面的实际宽度和高度
            page_width = driver_webcut.execute_script("return document.body.scrollWidth;")
            page_height = driver_webcut.execute_script("return document.body.scrollHeight;")

            if (page_width < 600):
                zoom_time = 4
            else:
                zoom_time = 1

            page_width = page_width * zoom_time
            page_height = page_height * zoom_time
            # 设置浏览器窗口大小为页面的实际宽度和高度

            driver_webcut.execute_script("document.body.style.zoom = '" + str(zoom_time) + "';")
            driver_webcut.set_window_size(page_width, page_height)
            new_uuid = str(uuid.uuid4())
            filepath = screenshot_dir + f"screenshot_{new_uuid}.png"
            driver_webcut.save_screenshot(filepath)

        except Exception as e:
            logging.error(f'Error in webcut: {url} exception:{e}')


        return jsonify({'status': 'ok', 'file': filepath, 'file_size': os.path.getsize(filepath), 'resolution': str(page_width) + "x" + str(page_height)})

@app.route('/detail', methods=['GET'])
def detail():
    global driver_web, service_web
    url = request.args.get('url')
    result = {}
    if url:
        if (driver_web == None or service_web == None):
            service_web = webdriver.chrome.service.Service(executable_path=chromediver_path)
            driver_web = webdriver.Chrome(service=service_web)
        driver_web.get(url)

        image_url = driver_web.execute_script('return msg_cdn_url')
        if image_url == None:
            image_url = driver_web.find_elements(by=By.TAG_NAME, value='img')[0].get_attribute('src')
        title = driver_web.find_elements(by=By.XPATH, value="//*[contains(@class, 'rich_media_title')]")[0].text.strip().replace("\n", "")
        content = driver_web.find_elements(by=By.XPATH, value="//*[contains(@class, 'rich_media_content')]")[0].text.strip().replace("\n", "")
        content_len = len(content)
        weixin_name = driver_web.execute_script("return nickname")
        result['image_url'] = image_url
        result['title'] = title
        result['content'] = content
        result['content_len'] = content_len
        result['link_url'] = url
        result['weixin_name'] = weixin_name

    return jsonify(result)
@app.route('/heartbeat', methods=['GET'])
def heartbeat():
    return "OK"

@app.route('/index', methods=['GET'])
def index():
    global service, driver
    if (service != None or driver != None):
        try :
            driver.refresh()
        except:
            driver = None
            service = None
        return "running"

    # 创建全局浏览器实例
    service = webdriver.chrome.service.Service(executable_path=chromediver_path)
    driver = webdriver.Chrome(service=service)
    driver.get('https://mp.weixin.qq.com/')
    asyncio.run(main(driver))
    return "running"
# 定义搜索接口
@app.route('/search', methods=['GET'])
def search():
    global driver
    query = request.args.get('query')
    page_size = request.args.get('page_size', default=6, type=int)
    page_num = request.args.get('page_num', default=0, type=int)
    url = request.args.get('url')
    type = request.args.get('type', default='all', type=str)

    #异步调用刷新cookie
    if (driver!= None):
        driver.refresh()

    # 获取当前登录的Cookie
    cookies = driver.get_cookies()
    cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
    logging.debug(f'[Current Cookies]: {cookie_dict}')
    # 如查传了公众号url 我们可以直接从url中来获取公众号id
    if url:
        response = requests.get(unquote(url))
        data = response.content.decode('utf-8')
        root = etree.HTML(data)
        query = root.xpath('//*[@id="js_profile_qrcode"]/div/p[1]/span')[0].text
        logging.debug(f'from Weixin Official Accounts url get [Query]: {query}')

    content = driver.execute_script("return window.wx.commonData;")
    logging.debug(f'[commonData] {content}')


    token = content['data']['param'];
    logging.debug(f'[Token]: {token}')
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    # 构建搜索接口URL
    search_url = f'https://mp.weixin.qq.com/cgi-bin/searchbiz?action=search_biz&query={query}&begin=0&count=3&f=json&ajax=1&{token}'

    # 调用搜索接口
    response = requests.get(search_url, cookies=cookie_dict, headers=headers)
    data = response.json()
    logging.debug(f'[Search API Response]: {data}')

    # 解析数据获取fakeid
    fakeid = data['list'][0]['fakeid']
    data['list'][0]['weixin_id'] = query
    fakeid_encoded = urlencode({'fakeid': fakeid}, encoding='utf-8')

    if type == 'fakeyinfo':
        return jsonify(data['list'][0])

    start_page = 0
    if page_num > 0:
        start_page = page_size * page_num - 1
    # 构建第二个接口URL
    article_url = f'https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&{fakeid_encoded}&query=&begin={start_page}&count={page_size}&type=9&need_author_name=1&f=json&ajax=1&{token}'

    # 调用第二个接口
    article_response = requests.get(article_url, cookies=cookie_dict, headers=headers)
    article_data = article_response.json()
    logging.debug(f'[Article API Response]: {article_data}')
    article_data['fakey_info'] = data['list'][0]

    return jsonify(article_data)

async def reflush_cookie(driver):
    while True:
        driver.refresh()
        logging.debug(f'[Refreshed Cookie time]: %s', time.time())
        await asyncio.sleep(60)

async def main(driver):
    # 创建一个任务，不关心其结果
    await asyncio.create_task(reflush_cookie(driver))

if __name__ == '__main__':
    # 配置日志记录
    logging.basicConfig(level=logging.DEBUG)
    logging.debug(f'[Start flask time]: %s', time.time())
    app.run(debug=True, host='0.0.0.0', port=flask_port)



