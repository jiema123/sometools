# 服务介绍

## 1. 服务功能原理

使用python 的 selenium 模拟浏览器 获取cookie 去调用公众号的获取文章接口实现公众号文章的采集,程序会自动刷新cookie, 每次调用search 接口时也会刷新一次cookie

a. 启动服务， 打开接口 xxxx:8900/index 会自动唤起Chrome浏览器并找开 https://mp.weixin.qq.com/ 微信公众号

b.用户使用微信扫码登录，保持浏览器在线状态不要关闭

c.调用接口 xxxx:8900/search 接口就可以获取到公众号文章了


## 2. 服务配置启动
chromediver 下载地址 https://chromedriver.chromium.org/downloads


基于python 依赖以下类包

```
lxml
Flask
selenium
requests
```

需要Chrom浏览器 （版本 123.0.6312.107） 跟selenium   Chromedriver插件


```angular2html
docker 相关操作

打包
docker build -t webselenium-app .


启动
docker run -v /Applications/Google\ Chrome.app/Contents:/usr/bin/google-chrome -e FLASK_PORT=8900 -p 8900:8900 webselenium-app




```





python 源代码
```python
import logging
from flask import Flask, request, jsonify
from selenium import webdriver
import requests
import time
from urllib.parse import urlencode
import asyncio
from lxml import etree
from urllib.parse import unquote

app = Flask(__name__)
service = None
driver = None

@app.route('/heartbeat', methods=['GET'])
def heartbeat():
return "OK"

@app.route('/index', methods=['GET'])
def index():
global service, driver
if (service != None or driver != None):
driver.refresh()
return "running"
# 创建全局浏览器实例
service = webdriver.chrome.service.Service(executable_path='/Users/fangjiefeng/Dev/tools/chromedriver_mac64/chromedriver')
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
app.run(debug=True, host='0.0.0.0', port=8900)

```



# 接口说明

### 1. /heartbeat GET 用户检测服务是否正常

http://10.39.150.6:8900/heartbeat
```
返回值
OK
```


### 2./index GET 用户启动浏览器

http://10.39.150.6:8900/index
```
返回
running
同时调用本二Chrome 浏览器打开微信公众号后台
```

### 3. /search GET 用于查询公众号文章

| 字段名                                | 是否必填                        | 说明                      | 例子      |
|------------------------------------|-----------------------------|-------------------------|---------|
| query |  是 |  公众号名字 或 公众号id  | 360安全云盘 、iyunpan
| url | 否 | 公众号文章链接  优先级高于query 如果有url 优先取url中的公众号id | https://mp.weixin.qq.com/s/kCS03qeqjA3GkGLovJ6c9Q）需要urlencode|
|type | 否 | 固定用法填写 fakeyinfo  只返回公众号信息 |fakeyinfo |

普通用法

http://10.39.150.6:8900/search?query=iyunpan

```
返回
{
"app_msg_cnt": 267,
"app_msg_list": [
{
"aid": "2652432579_1",
"album_id": "0",
"appmsg_album_infos": [],
"appmsgid": 2652432579,
"author_name": "",
"checking": 0,
"copyright_type": 0,
"cover": "https://mmbiz.qlogo.cn/sz_mmbiz_jpg/ZFrCRptJLdicJNj4xFaJoMGPthGZRtxzJR5lCQ20mRAa6pyeG3CDjCeAG4dgOTEunvwKOpZkEHznFmFuHicDgvicg/0?wx_fmt=jpeg",
"create_time": 1709782301,
"digest": "聆听用户声音，提升更优质的服务～",
"has_red_packet_cover": 0,
"is_pay_subscribe": 0,
"item_show_type": 0,
"itemidx": 1,
"link": "http://mp.weixin.qq.com/s?__biz=MjM5NTAyMTgyMA==&mid=2652432579&idx=1&sn=b4f4ef892e401987a0601dc4fd9e4f9f&chksm=bd129e508a6517461f1ec12ceab4207bda976278b814377c19ccb83bf13196b9cf001c81dcb9#rd",
"media_duration": "0:00",
"mediaapi_publish_status": 0,
"pay_album_info": {
"appmsg_album_infos": []
},
"tagid": [],
"title": "叮，您有一份《360安全云盘满意度小调研》，请查收！",
"update_time": 1709782300
},
{
"aid": "2652432579_2",
"album_id": "0",
"appmsg_album_infos": [],
"appmsgid": 2652432579,
"author_name": "",
"checking": 0,
"copyright_type": 0,
"cover": "https://mmbiz.qlogo.cn/sz_mmbiz_jpg/ZFrCRptJLdicJNj4xFaJoMGPthGZRtxzJxYEazfdq4xoEDvfqhKeIiaFxuJ3mAHofUR7EEmHQB4oNic5jbk8LXBSQ/0?wx_fmt=jpeg",
"create_time": 1709782301,
"digest": "点亮大模型时代的智能文档云之光",
"has_red_packet_cover": 0,
"is_pay_subscribe": 0,
"item_show_type": 0,
"itemidx": 2,
"link": "http://mp.weixin.qq.com/s?__biz=MjM5NTAyMTgyMA==&mid=2652432579&idx=2&sn=97d32d7cb6c7adc583ba634b3281a62c&chksm=bd129e508a651746162e538988d1c255f5a12ba6cd6dcee784bbfc19fdb9c1c60bd62dcf4cb2#rd",
"media_duration": "0:00",
"mediaapi_publish_status": 0,
"pay_album_info": {
"appmsg_album_infos": []
},
"tagid": [],
"title": "360亿方云发布智能文档云，引领大模型时代下的知识管理革命",
"update_time": 1709782300
}
],
"base_resp": {
"err_msg": "ok",
"ret": 0
},
"fakey_info": {
"alias": "iyunpan",
"fakeid": "MjM5NTAyMTgyMA==",
"nickname": "360安全云盘",
"round_head_img": "http://mmbiz.qpic.cn/mmbiz_png/ZFrCRptJLdib5zbJJ8W6AGZCwJF0ZoVchtuu1B25cKQibxK6tkQ2aQTAPm8TBXvIjmmibpwRFn2XNCpIp7LVBk8Bg/0?wx_fmt=png",
"service_type": 2,
"signature": "360安全云盘，随时随地存储和移动办公。",
"weixin_id": "iyunpan"
}
}

```
通过url 获取公众号链接

http://10.39.150.6:8900/search?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2FkCS03qeqjA3GkGLovJ6c9Q
```
返回值
{
"app_msg_cnt": 209,
"app_msg_list": [
{
"aid": "2247492395_1",
"album_id": "0",
"appmsg_album_infos": [],
"appmsgid": 2247492395,
"author_name": "疯批",
"checking": 0,
"copyright_type": 1,
"cover": "https://mmbiz.qlogo.cn/sz_mmbiz_jpg/3WriciczIQJomvh78RGUUFgDbBcnD847SVDP40iaXdvZJyGTjzOMia5hh95TIRibBCLkwU6t8RtjsE5JukCzzpr0NeQ/0?wx_fmt=jpeg",
"create_time": 1712727425,
"digest": "“明月几时有？”这句古诗中的名句，无数中国人耳熟能详。而将这种月夜的美景与家国情怀结合起来的歌曲《十五的月亮》，让无数人为之动容。",
"has_red_packet_cover": 0,
"is_pay_subscribe": 0,
"item_show_type": 0,
"itemidx": 1,
"link": "http://mp.weixin.qq.com/s?__biz=MzkxNDU3Mzc5OA==&mid=2247492395&idx=1&sn=adc429241b5e395b5781e4c8eb317ceb&chksm=c16ef3a2f6197ab4f451a5192799c497805eaa4a60c4fda679425e154b1e8ff8fbbe45915a7e#rd",
"media_duration": "0:00",
"mediaapi_publish_status": 0,
"pay_album_info": {
"appmsg_album_infos": []
},
"tagid": [],
"title": "“中国民歌天后”董文华传来最新消息！与赖昌星百万之夜究竟发生了什么？",
"update_time": 1712727425
},
{
"aid": "2247492395_2",
"album_id": "0",
"appmsg_album_infos": [],
"appmsgid": 2247492395,
"author_name": "疯批",
"checking": 0,
"copyright_type": 1,
"cover": "https://mmbiz.qlogo.cn/sz_mmbiz_jpg/3WriciczIQJomvh78RGUUFgDbBcnD847SVHic7pgpeXC3DpicwgRB7E5VBFXrNT8ujyuYWia68bFwWjOc2ibNB4MTYuw/0?wx_fmt=jpeg",
"create_time": 1712727425,
"digest": "2004年，小香玉与王为念的婚姻走到了尽头。这段情感的终结，对王为念来说，是一段长时间难以平复的心伤。",
"has_red_packet_cover": 0,
"is_pay_subscribe": 0,
"item_show_type": 0,
"itemidx": 2,
"link": "http://mp.weixin.qq.com/s?__biz=MzkxNDU3Mzc5OA==&mid=2247492395&idx=2&sn=2c38f4debdc4b4d52da8acaadc1972d2&chksm=c16ef3a2f6197ab4316eb541d759d89cf21fce7a914bdab37395a15aa60d65b0c27cfc788d13#rd",
"media_duration": "0:00",
"mediaapi_publish_status": 0,
"pay_album_info": {
"appmsg_album_infos": []
},
"tagid": [],
"title": "离婚18年后，再看王为念、小香玉的各自境遇，夫妻差距一目了然",
"update_time": 1712727425
}
],
"base_resp": {
"err_msg": "ok",
"ret": 0
},
"fakey_info": {
"alias": "",
"fakeid": "MzkxNDU3Mzc5OA==",
"nickname": "娱乐新瓜疯批",
"round_head_img": "http://mmbiz.qpic.cn/sz_mmbiz_png/3WriciczIQJomLUWibbicdZnDTrBnMia99xur7Svgxg31sSn5BZeibnoAtpbZ09Ot9FGuErSwNg1yTjviawjS5MPTbvbw/0?wx_fmt=png",
"service_type": 1,
"signature": "谢谢关注",
"weixin_id": "gh_4fab7866524f"
}
}
```

获取公众号信息

http://10.39.150.6:8900/search?query=iyunpan&type=fakeyinfo

http://10.39.150.6:8900/search?url=https%3A%2F%2Fmp.weixin.qq.com%2Fs%2FkCS03qeqjA3GkGLovJ6c9Q&type=fakeyinfo

```
{
"alias": "",
"fakeid": "MzkxNDU3Mzc5OA==",
"nickname": "娱乐新瓜疯批",
"round_head_img": "http://mmbiz.qpic.cn/sz_mmbiz_png/3WriciczIQJomLUWibbicdZnDTrBnMia99xur7Svgxg31sSn5BZeibnoAtpbZ09Ot9FGuErSwNg1yTjviawjS5MPTbvbw/0?wx_fmt=png",
"service_type": 1,
"signature": "谢谢关注",
"weixin_id": "gh_4fab7866524f"
}

```