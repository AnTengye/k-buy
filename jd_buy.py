# -*- coding=utf-8 -*-
'''
京东抢购商品程序
通过商品的skuid、地区id抢购
'''
import hashlib
import json
import os
import random
import socket
import sys
import time
import traceback
from io import BytesIO

import ddddocr as ddddocr
import requests
from PIL import Image
from bs4 import BeautifulSoup

from message import message

_dnscache = {}


def parse_json(s):
    begin = s.find('{')
    end = s.rfind('}') + 1
    return json.loads(s[begin:end])


def getconfigMd5():
    with open('configDemo.ini', 'r', encoding='utf-8') as f:
        configText = f.read()
        return hashlib.md5(configText.encode('utf-8')).hexdigest()


def response_status(resp):
    if resp.status_code != requests.codes.OK:
        print('Status: %u, Url: %s' % (resp.status_code, resp.url))
        return False
    return True


def _setDNSCache():
    """
    Makes a cached version of socket._getaddrinfo to avoid subsequent DNS requests.
    """

    def _getaddrinfo(*args, **kwargs):
        global _dnscache
        if args in _dnscache:
            # print(str(args) + " in cache")
            return _dnscache[args]

        else:
            # print(str(args) + " not in cache")
            _dnscache[args] = socket._getaddrinfo(*args, **kwargs)
            return _dnscache[args]

    if not hasattr(socket, '_getaddrinfo'):
        socket._getaddrinfo = socket.getaddrinfo
        socket.getaddrinfo = _getaddrinfo


'''
需要修改
'''
global cookies_String, area, skuidsString, skuids, eid, fp, payment_pwd


def getconfig():
    global cookies_String, area, skuidsString, skuids, eid, fp, payment_pwd
    cookies_String = os.getenv('JD_BUY_COOKIE')
    area = os.getenv('JD_BUY_AREA')
    skuidsString = os.getenv('JD_BUY_SKU')
    payment_pwd = os.getenv('JD_BUY_PW')
    skuids = str(skuidsString).split(',')
    if len(skuids[0]) == 0:
        print('请在configDemo.ini文件中输入你的商品id')
        sys.exit(1)


# 初次
configTime = int(time.time())
getconfig()
configMd5 = getconfigMd5()
message = message()

is_Submit_captcha = False
submit_captcha_rid = ''
submit_captcha_text = ''
encryptClientInfo = ''
submit_Time = 0
session = requests.session()
checksession = requests.session()
session.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Connection": "keep-alive"
}
checksession.headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
    "Connection": "keep-alive"
}
manual_cookies = {}


def get_tag_value(tag, key='', index=0):
    if key:
        value = tag[index].get(key)
    else:
        value = tag[index].text
    return value.strip(' \t\r\n')


def response_status(resp):
    if resp.status_code != requests.codes.OK:
        print(f'Status: {resp.status_code}, Url: {resp.url}')
        return False
    return True


for item in cookies_String.split(';'):
    name, value = item.strip().split('=', 1)
    # 用=号分割，分割1次
    manual_cookies[name] = value
    # 为字典cookies添加内容

cookiesJar = requests.utils.cookiejar_from_dict(manual_cookies, cookiejar=None, overwrite=True)
session.cookies = cookiesJar


def validate_cookies():
    for flag in range(1, 3):
        try:
            targetURL = 'https://order.jd.com/center/list.action'
            payload = {
                'rid': str(int(time.time() * 1000)),
            }
            resp = session.get(url=targetURL, params=payload, allow_redirects=False)
            if resp.status_code == requests.codes.OK:
                print('登录成功')
                return True
            else:
                print(f'第【{flag}】次请重新获取cookie')
                time.sleep(5)
                continue
        except Exception as e:
            print(f'第【{flag}】次请重新获取cookie')
            time.sleep(5)
            continue
    message.sendAny('脚本登录cookie失效了，请重新登录')
    sys.exit(1)


def getUsername():
    userName_Url = 'https://passport.jd.com/new/helloService.ashx?callback=jQuery339448&_=' + str(
        int(time.time() * 1000))
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://order.jd.com/center/list.action",
        "Connection": "keep-alive"
    }
    resp = session.get(url=userName_Url, allow_redirects=True)
    resultText = resp.text
    resultText = resultText.replace('jQuery339448(', '')
    resultText = resultText.replace(')', '')
    usernameJson = json.loads(resultText)
    print('登录账号名称' + usernameJson['nick'])


'''
检查是否有货
'''


def check_item_stock(itemUrl):
    response = session.get(itemUrl)
    if response.text.find('无货') > 0:
        return True
    else:
        return False


'''
取消勾选购物车中的所有商品
'''


def cancel_select_all_cart_item():
    url = "https://cart.jd.com/cancelAllItem.action"
    data = {
        't': 0,
        'outSkus': '',
        'random': random.random()
    }
    resp = session.post(url, data=data)
    if resp.status_code != requests.codes.OK:
        print(f'Status: {resp.status_code}, Url: {resp.url}')
        return False
    return True


'''
勾选购物车中的所有商品
'''


def select_all_cart_item():
    url = "https://cart.jd.com/selectAllItem.action"
    data = {
        't': 0,
        'outSkus': '',
        'random': random.random()
    }
    resp = session.post(url, data=data)
    if resp.status_code != requests.codes.OK:
        print(f'Status: {resp.status_code}, Url: {resp.url}')
        return False
    return True


'''
删除购物车选中商品
'''


def remove_item():
    url = "https://cart.jd.com/batchRemoveSkusFromCart.action"
    data = {
        't': 0,
        'null': '',
        'outSkus': '',
        'random': random.random(),
        'locationId': '19-1607-4773-0'
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.25 Safari/537.36 Core/1.70.37",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://cart.jd.com/cart.action",
        "Host": "cart.jd.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://cart.jd.com",
        "Connection": "keep-alive"
    }
    resp = session.post(url, data=data, headers=headers)
    print('清空购物车')
    if resp.status_code != requests.codes.OK:
        print(f'Status: {resp.status_code}, Url: {resp.url}')
        return False
    return True


'''
购物车详情
'''


def cart_detail():
    url = 'https://cart.jd.com/cart.action'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://order.jd.com/center/list.action",
        "Host": "cart.jd.com",
        "Connection": "keep-alive"
    }
    resp = session.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, "html.parser")

    cart_detail = dict()
    for item in soup.find_all(class_='item-item'):
        try:
            sku_id = item['skuid']  # 商品id
        except Exception as e:
            print('购物车中有套装商品，跳过')
            continue
        try:
            # 例如：['increment', '8888', '100001071956', '1', '13', '0', '50067652554']
            # ['increment', '8888', '100002404322', '2', '1', '0']
            item_attr_list = item.find(class_='increment')['id'].split('_')
            p_type = item_attr_list[4]
            promo_id = target_id = item_attr_list[-1] if len(item_attr_list) == 7 else 0

            cart_detail[sku_id] = {
                'name': get_tag_value(item.select('div.p-name a')),  # 商品名称
                'verder_id': item['venderid'],  # 商家id
                'count': int(item['num']),  # 数量
                'unit_price': get_tag_value(item.select('div.p-price strong'))[1:],  # 单价
                'total_price': get_tag_value(item.select('div.p-sum strong'))[1:],  # 总价
                'is_selected': 'item-selected' in item['class'],  # 商品是否被勾选
                'p_type': p_type,
                'target_id': target_id,
                'promo_id': promo_id
            }
        except Exception as e:
            print(f"商品{sku_id}在购物车中的信息无法解析，报错信息: {e}，该商品自动忽略")

    print(f'购物车信息：{cart_detail}', )
    return cart_detail


'''
修改购物车商品的数量
'''


def change_item_num_in_cart(sku_id, vender_id, num, p_type, target_id, promo_id):
    url = "https://cart.jd.com/changeNum.action"
    data = {
        't': 0,
        'venderId': vender_id,
        'pid': sku_id,
        'pcount': num,
        'ptype': p_type,
        'targetId': target_id,
        'promoID': promo_id,
        'outSkus': '',
        'random': random.random(),
        # 'locationId'
    }
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://cart.jd.com/cart",
        "Connection": "keep-alive"
    }
    resp = session.post(url, data=data)
    return json.loads(resp.text)['sortedWebCartResult']['achieveSevenState'] == 2


'''
添加商品到购物车
'''


def add_item_to_cart(sku_id):
    url = 'https://cart.jd.com/gate.action'
    payload = {
        'pid': sku_id,
        'pcount': 1,
        'ptype': 1,
    }
    resp = session.get(url=url, params=payload)
    if 'https://cart.jd.com/cart.action' in resp.url:  # 套装商品加入购物车后直接跳转到购物车页面
        result = True
    else:  # 普通商品成功加入购物车后会跳转到提示 "商品已成功加入购物车！" 页面
        soup = BeautifulSoup(resp.text, "html.parser")
        result = bool(soup.select('h3.ftx-02'))  # [<h3 class="ftx-02">商品已成功加入购物车！</h3>]

    if result:
        print(f'{sku_id}  已成功加入购物车', )
    else:
        print(f'{sku_id} 添加到购物车失败')


def get_checkout_page_detail():
    """获取订单结算页面信息

    该方法会返回订单结算页面的详细信息：商品名称、价格、数量、库存状态等。

    :return: 结算信息 dict
    """
    url = 'http://trade.jd.com/shopping/order/getOrderInfo.action'
    # url = 'https://cart.jd.com/gotoOrder.action'
    payload = {
        'rid': str(int(time.time() * 1000)),
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://cart.jd.com/cart.action",
        "Connection": "keep-alive",
        'Host': 'trade.jd.com',
    }
    try:
        resp = session.get(url=url, params=payload, headers=headers)
        if not response_status(resp):
            print('获取订单结算页信息失败')
            return '', ''
        if '刷新太频繁了' in resp.text:
            return '刷新太频繁了', ''
        soup = BeautifulSoup(resp.text, "html.parser")
        showCheckCode = get_tag_value(soup.select('input#showCheckCode'), 'value')
        if not showCheckCode:
            pass
        else:
            if showCheckCode == 'true':
                print('提交订单需要验证码')
                global is_Submit_captcha, encryptClientInfo
                encryptClientInfo = get_tag_value(soup.select('input#encryptClientInfo'), 'value')
                is_Submit_captcha = True
        risk_control = get_tag_value(soup.select('input#riskControl'), 'value')

        order_detail = {
            'address': soup.find('span', id='sendAddr').text[5:],  # remove '寄送至： ' from the begin
            'receiver': soup.find('span', id='sendMobile').text[4:],  # remove '收件人:' from the begin
            'total_price': soup.find('span', id='sumPayPriceId').text[1:],  # remove '￥' from the begin
            'items': []
        }

        print(f"下单信息：{order_detail}", )
        return risk_control, order_detail
    except requests.exceptions.RequestException as e:
        print(f'订单结算页面获取异常：{e}')
    except Exception as e:
        print(f'下单页面数据解析异常：{e}')
    return '', ''


'''
商品下柜检测
'''


def item_removed(sku_id):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "http://trade.jd.com/shopping/order/getOrderInfo.action",
        "Connection": "keep-alive",
        'Host': 'item.jd.com',
    }
    url = 'https://item.jd.com/{}.html'.format(sku_id)
    page = requests.get(url=url, headers=headers)
    return '该商品已下柜' not in page.text


'''
购买环节
测试三次
'''


def buyMask(sku_id) -> bool:
    risk_control, detail = get_checkout_page_detail()
    if risk_control == '刷新太频繁了':
        return False
    return submit_order(session, risk_control, detail, sku_id, skuids, submit_Time, encryptClientInfo,
                        is_Submit_captcha,
                        payment_pwd, submit_captcha_text, submit_captcha_rid)


def V3check(skuId):
    select_all_cart_item()
    remove_item()
    validate_cookies()
    print('校验是否还在登录')
    add_item_to_cart(skuId)
    if not item_removed(skuId):
        print(f'[{skuId}]已下柜商品', )
        sys.exit(1)


def V3AutoBuy(inStockSkuid):
    if skuId in inStockSkuid:
        global submit_Time
        submit_Time = int(time.time() * 1000)
        message.send(f"{skuId}有货啦!马上下单")
        if buyMask(skuId):
            sys.exit(1)
        else:
            if item_removed(skuId):
                message.send("商品下单失败，重新处理")
            else:
                print('[%s]已下柜商品', skuId)
                sys.exit(1)


def check_stock(checksession, skuids, area):
    start = int(time.time() * 1000)
    skuidString = ','.join(skuids)
    callback = 'jQuery' + str(random.randint(1000000, 9999999))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://cart.jd.com/cart.action",
        "Connection": "keep-alive",
        "Host": "c0.3.cn"
    }
    #
    url = 'https://c0.3.cn/stocks'
    payload = {
        'type': 'getstocks',
        'skuIds': skuidString,
        'area': area,
        'callback': callback,
        '_': int(time.time() * 1000),
    }
    resp = checksession.get(url=url, params=payload, headers=headers)
    inStockSkuid = []
    nohasSkuid = []
    unUseSkuid = []
    for sku_id, info in parse_json(resp.text).items():
        sku_state = info.get('skuState')  # 商品是否上架
        stock_state = info.get('StockState')  # 商品库存状态
        if sku_state == 1 and stock_state in (33, 40):
            inStockSkuid.append(sku_id)
        if sku_state == 0:
            unUseSkuid.append(sku_id)
        if stock_state == 34:
            nohasSkuid.append(sku_id)
    print(
        f'检测[{len(inStockSkuid)}]个商品有货，[{len(nohasSkuid)}]个商品无货，[{len(unUseSkuid)}]个商品下柜，耗时[{int(time.time() * 1000) - start}]ms')

    if len(unUseSkuid) > 0:
        print(f'[{",".join(unUseSkuid)}]商品已经下柜', )
    return inStockSkuid


'''
提交订单
'''


def submit_order(session, risk_control, detail, sku_id, skuids, submit_Time, encryptClientInfo, is_Submit_captcha,
                 payment_pwd,
                 submit_captcha_text, submit_captcha_rid):
    """

    重要：
    1.该方法只适用于普通商品的提交订单（即可以加入购物车，然后结算提交订单的商品）
    2.提交订单时，会对购物车中勾选✓的商品进行结算（如果勾选了多个商品，将会提交成一个订单）

    :return: True/False 订单提交结果
    """
    url = 'https://trade.jd.com/shopping/order/submitOrder.action'
    # js function of submit order is included in https://trade.jd.com/shopping/misc/js/order.js?r=2018070403091

    data = {
        'overseaPurchaseCookies': '',
        'vendorRemarks': '[]',
        'submitOrderParam.sopNotPutInvoice': 'false',
        'submitOrderParam.trackID': 'TestTrackId',
        'submitOrderParam.ignorePriceChange': '0',
        'submitOrderParam.btSupport': '0',
        'riskControl': risk_control,
        'submitOrderParam.isBestCoupon': 1,
        'submitOrderParam.jxj': 1,
        'submitOrderParam.trackId': '9643cbd55bbbe103eef18a213e069eb0',  # Todo: need to get trackId
        # 'submitOrderParam.eid': eid,
        # 'submitOrderParam.fp': fp,
        'submitOrderParam.needCheck': 1,
    }

    def encrypt_payment_pwd(payment_pwd):
        return ''.join(['u3' + x for x in payment_pwd])

    if len(payment_pwd) > 0:
        data['submitOrderParam.payPassword'] = encrypt_payment_pwd(payment_pwd)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "http://trade.jd.com/shopping/order/getOrderInfo.action",
        "Connection": "keep-alive",
        'Host': 'trade.jd.com',
    }
    for count in range(1, 3):
        print(f'第[{count}/{3}]次尝试提交订单')
        try:
            if is_Submit_captcha:
                captcha_result = page_detail_captcha(session, encryptClientInfo)
                # 验证码服务错误
                if not captcha_result:
                    print('验证码服务异常')
                    continue
                data['submitOrderParam.checkcodeTxt'] = submit_captcha_text
                data['submitOrderParam.checkCodeRid'] = submit_captcha_rid
            resp = session.post(url=url, data=data, headers=headers)
            resp_json = json.loads(resp.text)
            print(f'本次提交订单耗时[{str(int(time.time() * 1000) - submit_Time)}]毫秒')
            # 返回信息示例：
            # 下单失败
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60123, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '请输入支付密码！'}
            # {'overSea': False, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'orderXml': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60017, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '您多次提交过快，请稍后再试'}
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 60077, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '获取用户订单信息失败'}
            # {"cartXml":null,"noStockSkuIds":"xxx","reqInfo":null,"hasJxj":false,"addedServiceList":null,"overSea":false,"orderXml":null,"sign":null,"pin":"xxx","needCheckCode":false,"success":false,"resultCode":600157,"orderId":0,"submitSkuNum":0,"deductMoneyFlag":0,"goJumpOrderCenter":false,"payInfo":null,"scaleSkuInfoListVO":null,"purchaseSkuInfoListVO":null,"noSupportHomeServiceSkuList":null,"msgMobile":null,"addressVO":{"pin":"xxx","areaName":"","provinceId":xx,"cityId":xx,"countyId":xx,"townId":xx,"paymentId":0,"selected":false,"addressDetail":"xx","mobile":"xx","idCard":"","phone":null,"email":null,"selfPickMobile":null,"selfPickPhone":null,"provinceName":null,"cityName":null,"countyName":null,"townName":null,"giftSenderConsigneeName":null,"giftSenderConsigneeMobile":null,"gcLat":0.0,"gcLng":0.0,"coord_type":0,"longitude":0.0,"latitude":0.0,"selfPickOptimize":0,"consigneeId":0,"selectedAddressType":0,"siteType":0,"helpMessage":null,"tipInfo":null,"cabinetAvailable":true,"limitKeyword":0,"specialRemark":null,"siteProvinceId":0,"siteCityId":0,"siteCountyId":0,"siteTownId":0,"skuSupported":false,"addressSupported":0,"isCod":0,"consigneeName":null,"pickVOname":null,"shipmentType":0,"retTag":0,"tagSource":0,"userDefinedTag":null,"newProvinceId":0,"newCityId":0,"newCountyId":0,"newTownId":0,"newProvinceName":null,"newCityName":null,"newCountyName":null,"newTownName":null,"checkLevel":0,"optimizePickID":0,"pickType":0,"dataSign":0,"overseas":0,"areaCode":null,"nameCode":null,"appSelfPickAddress":0,"associatePickId":0,"associateAddressId":0,"appId":null,"encryptText":null,"certNum":null,"used":false,"oldAddress":false,"mapping":false,"addressType":0,"fullAddress":"xxxx","postCode":null,"addressDefault":false,"addressName":null,"selfPickAddressShuntFlag":0,"pickId":0,"pickName":null,"pickVOselected":false,"mapUrl":null,"branchId":0,"canSelected":false,"address":null,"name":"xxx","message":null,"id":0},"msgUuid":null,"message":"xxxxxx商品无货"}
            # {'orderXml': None, 'overSea': False, 'noStockSkuIds': 'xxx', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'cartXml': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': False, 'resultCode': 600158, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': {'oldAddress': False, 'mapping': False, 'pin': 'xxx', 'areaName': '', 'provinceId': xx, 'cityId': xx, 'countyId': xx, 'townId': xx, 'paymentId': 0, 'selected': False, 'addressDetail': 'xxxx', 'mobile': 'xxxx', 'idCard': '', 'phone': None, 'email': None, 'selfPickMobile': None, 'selfPickPhone': None, 'provinceName': None, 'cityName': None, 'countyName': None, 'townName': None, 'giftSenderConsigneeName': None, 'giftSenderConsigneeMobile': None, 'gcLat': 0.0, 'gcLng': 0.0, 'coord_type': 0, 'longitude': 0.0, 'latitude': 0.0, 'selfPickOptimize': 0, 'consigneeId': 0, 'selectedAddressType': 0, 'newCityName': None, 'newCountyName': None, 'newTownName': None, 'checkLevel': 0, 'optimizePickID': 0, 'pickType': 0, 'dataSign': 0, 'overseas': 0, 'areaCode': None, 'nameCode': None, 'appSelfPickAddress': 0, 'associatePickId': 0, 'associateAddressId': 0, 'appId': None, 'encryptText': None, 'certNum': None, 'addressType': 0, 'fullAddress': 'xxxx', 'postCode': None, 'addressDefault': False, 'addressName': None, 'selfPickAddressShuntFlag': 0, 'pickId': 0, 'pickName': None, 'pickVOselected': False, 'mapUrl': None, 'branchId': 0, 'canSelected': False, 'siteType': 0, 'helpMessage': None, 'tipInfo': None, 'cabinetAvailable': True, 'limitKeyword': 0, 'specialRemark': None, 'siteProvinceId': 0, 'siteCityId': 0, 'siteCountyId': 0, 'siteTownId': 0, 'skuSupported': False, 'addressSupported': 0, 'isCod': 0, 'consigneeName': None, 'pickVOname': None, 'shipmentType': 0, 'retTag': 0, 'tagSource': 0, 'userDefinedTag': None, 'newProvinceId': 0, 'newCityId': 0, 'newCountyId': 0, 'newTownId': 0, 'newProvinceName': None, 'used': False, 'address': None, 'name': 'xx', 'message': None, 'id': 0}, 'msgUuid': None, 'message': 'xxxxxx商品无货'}
            # {"orderXml":null,"cartXml":null,"noStockSkuIds":"","reqInfo":null,"hasJxj":false,"overSea":false,"addedServiceList":null,"sign":null,"pin":null,"needCheckCode":true,"success":false,"resultCode":0,"orderId":0,"submitSkuNum":0,"deductMoneyFlag":0,"goJumpOrderCenter":false,"payInfo":null,"scaleSkuInfoListVO":null,"purchaseSkuInfoListVO":null,"noSupportHomeServiceSkuList":null,"msgMobile":null,"addressVO":null,"msgUuid":null,"message":"验证码不正确，请重新填写"}
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'jd_7c3992aa27d1a', 'needCheckCode': False, 'success': False, 'resultCode': 60070, 'orderId': 0, 'submitSkuNum': 0, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': '抱歉，您当前选择的省份无法购买商品星工 KN95商品防雾霾防尘防花粉PM2.5 硅胶鼻垫带阀耳戴透气 工业粉尘防护商品 白色25只独立包装'}
            # 下单成功
            # {'overSea': False, 'orderXml': None, 'cartXml': None, 'noStockSkuIds': '', 'reqInfo': None, 'hasJxj': False, 'addedServiceList': None, 'sign': None, 'pin': 'xxx', 'needCheckCode': False, 'success': True, 'resultCode': 0, 'orderId': 8740xxxxx, 'submitSkuNum': 1, 'deductMoneyFlag': 0, 'goJumpOrderCenter': False, 'payInfo': None, 'scaleSkuInfoListVO': None, 'purchaseSkuInfoListVO': None, 'noSupportHomeServiceSkuList': None, 'msgMobile': None, 'addressVO': None, 'msgUuid': None, 'message': None}
            if resp_json.get('success'):
                message.send(f'订单提交成功! 订单信息：{detail}, 商品：{risk_control}, 订单号：{resp_json.get("orderId")}，请尽快支付')
                return True
            else:
                resultMessage, result_code = resp_json.get('message'), resp_json.get('resultCode')
                if result_code == 0:
                    if '验证码不正确' in resultMessage:
                        resultMessage = resultMessage + '(验证码错误)'
                        print('提交订单验证码[错误]')
                    else:
                        resultMessage = resultMessage + '(下单商品可能为第三方商品，将切换为普通发票进行尝试)'
                elif result_code == 60077:
                    resultMessage = resultMessage + '(可能是购物车为空 或 未勾选购物车中商品)'
                elif result_code == 60123:
                    resultMessage = resultMessage + '(需要在payment_pwd参数配置支付密码)'
                elif result_code == 60070:
                    resultMessage = resultMessage + '(省份不支持销售)'
                    skuids.remove(sku_id)
                    print(f'[{sku_id}]类型商品不支持销售踢出')
                message.send(f'订单提交失败, 错误码：{result_code}, 返回信息：{resultMessage}')
                print(resp_json)
                return False
        except Exception as e:
            print(traceback.format_exc())
            continue
    message.send(f'订单提交失败, 重试失败，详情看日志')
    return False


'''
订单页面验证码
'''


def page_detail_captcha(session, isId):
    url = 'https://captcha.jd.com/verify/image'
    acid = '{}_{}'.format(random.random(), random.random())
    payload = {
        'acid': acid,
        'srcid': 'trackWeb',
        'is': isId,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/531.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
        "Referer": "https://trade.jd.com/shopping/order/getOrderInfo.action",
        "Connection": "keep-alive",
        'Host': 'captcha.jd.com',
    }
    try:
        resp = session.get(url=url, params=payload, headers=headers)
        if not response_status(resp):
            print('获取订单验证码失败')
            return ''
        print('解析验证码开始')
        image = Image.open(BytesIO(resp.content))
        image.save('captcha.jpg')
        result = analysis_captcha(resp.content)
        if not result:
            print('解析订单验证码失败')
            return ''
        global submit_captcha_text, submit_captcha_rid
        submit_captcha_text = result
        submit_captcha_rid = acid
        return result
    except Exception as e:
        print(f'订单验证码获取异常：{e}')
    return ''


def analysis_captcha(pic):
    for i in range(1, 10):
        try:
            ocr = ddddocr.DdddOcr(show_ad=False)
            resp = ocr.classification(pic)
            print(f'解析验证码[{resp}]')
            return resp
        except Exception as e:
            print(traceback.format_exc())
            continue
    return ''


_setDNSCache()
if len(skuids) != 1:
    print('请准备一件商品')
skuId = skuids[0]
flag = 1
while (1):
    try:
        # 初始化校验
        if flag == 1:
            print('当前是V3版本')
            validate_cookies()
            getUsername()
            select_all_cart_item()
            remove_item()
            add_item_to_cart(skuId)
        print(f'第{flag}次')
        flag += 1
        # 检查库存模块
        inStockSkuid = check_stock(checksession, skuids, area)
        # 自动下单模块
        V3AutoBuy(inStockSkuid)
        # 休眠模块
        timesleep = random.randint(10, 30)
        time.sleep(timesleep)
        # 校验是否还在登录模块
        if flag % 100 == 0:
            V3check(skuId)
    except Exception as e:
        print(traceback.format_exc())
        time.sleep(10)
