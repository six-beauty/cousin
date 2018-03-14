# -*- coding: utf-8 -*-

import requests
import logging
import traceback
import json
import urllib
import base64
from PIL import Image
import pytesseract
import os
import re

WHITE = (255,255,255)
BLACK = (0,0,0)

#对图片做预处理，去除背景
def pre_concert(img, threshold):
    width,height = img.size

    for i in range(0,width):
        for j in range(0,height):
            p = img.getpixel((i,j))#抽取每个像素点的像素
            r,g,b = p
            if r > threshold or g > threshold or b > threshold:
                img.putpixel((i,j),WHITE)
            else:
                img.putpixel((i,j),BLACK)

    img_points = []
    for item in img.getdata():
        r,g,b = item
        if r > threshold or g > threshold or b > threshold:
            img_points.append(WHITE)
        else:
            img_points.append(BLACK)

    return img_points

#横向扫描, 获取最大边界大小. 除去小于最大噪点大小的面积.
def remove_noise(img, points, max_noisy):
    # 噪点大小

    width, height = img.size
    # 标记位置, 初始化都是0, 未遍历过
    flag_list = []
    for i in range(width * height):
        flag_list.append(0)

    # 遍历
    for index, value in enumerate(points):
        _y = index // width
        _x = index - _y * width
        # print _x, _y
        if flag_list[index] == 0 and value == BLACK:
            flag_list[index] = 1
            _tmp_list = [index]
            recursion_scan_black_point(_x, _y, width, height, _tmp_list, flag_list, points)
            if len(_tmp_list) <= max_noisy:
                for x in _tmp_list:
                    points[x] = WHITE

        else:
            flag_list[index] = 1

def recursion_scan_black_point(x, y, width, height, tmp_list, flag_list, points):
    # 左上
    if 0 <= (x - 1) < width and 0 <= (y - 1) < height:
        _x = x - 1
        _y = y - 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 上
    if 0 <= (y - 1) < height:
        _x = x
        _y = y - 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 右上
    if 0 <= (x + 1) < width and 0 <= (y - 1) < height:
        _x = x + 1
        _y = y - 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 左
    if 0 <= (x - 1) < width:
        _x = x - 1
        _y = y
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 右
    if 0 <= (x + 1) < width:
        _x = x + 1
        _y = y
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 左下
    if 0 <= (x - 1) < width and 0 <= (y + 1) < height:
        _x = x - 1
        _y = y + 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 下
    if 0 <= (y + 1) < height:
        _x = x
        _y = y + 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

    # 右下
    if 0 <= (x + 1) < width and 0 <= (y + 1) < height:
        _x = x + 1
        _y = y + 1
        _inner_recursion(_x, _y, width, height, tmp_list, flag_list, points)

def _inner_recursion(new_x, new_y, width, height, tmp_list, flag_list, points):
    _index = new_x + width * new_y
    if flag_list[_index] == 0 and points[_index] == BLACK:
        tmp_list.append(_index)
        flag_list[_index] = 1
        recursion_scan_black_point(new_x, new_y, width, height, tmp_list, flag_list, points)
    else:
        flag_list[_index] = 1

def split_fig(img):
    frame = img.load()
    img_new = img.copy()
    frame_new = img_new.load()

    width,height = img.size
    line_status = None
    pos_x = []
    for x in range(width):
        pixs = []
        for y in range(height):
            pixs.append(frame[x,y])

        if len(set(pixs)) == 1:
            _line_status = 0
        else:
            _line_status = 1

        if _line_status != line_status:
            if _line_status != None:
                if _line_status == 0:
                    _x = x
                elif _line_status == 1:
                    _x = x - 1

                pos_x.append(_x)

                #辅助线
                for _y in range(height):
                    frame_new[x,_y] = BLACK

        line_status = _line_status

    i = 0
    divs = []
    boxs = []
    while True:
        try:
            x_i = pos_x[i]
            x_j = pos_x[i+1]
        except:
            break

        i = i + 2
        boxs.append([x_i,x_j])

    fixed_boxs = []
    i = 0
    while i < len(boxs):
        box = boxs[i]
        if box[1] - box[0] < 10:
            try:
                box_next = boxs[i+1]
                fixed_boxs.append([box[0],box_next[1]])
                i += 2
            except Exception:
                break
        else:
            fixed_boxs.append(box)
            i += 1

    for box in fixed_boxs:
        div = img.crop((box[0],0,box[1],height))
        try:
            #divs.append(format_div(div,size=(20,40)))
            divs.append(div)
        except:
            divs.append(div)

    #过滤掉非字符的切片
    _divs = []
    for div in divs:
        width,heigth = div.size
        if width < 5:
            continue

        frame = div.load()
        points = 0
        for i in range(width):
            for j in range(heigth):
                p = frame[i,j]
                if p == BLACK:
                    points += 1

        if points <= 5:
            continue

        #new_div = format_div(div)
        new_div = div
        _divs.append(new_div)
    return _divs


def image_to_string(img,config='-psm 8'):
    result = pytesseract.image_to_string(img, lang='eng', config=config)
    result = result.strip()
    return result.lower()


def recognize_image(captcha, threshold=45, max_noisy=25):
    img = Image.open(captcha)
    img_points = pre_concert(img, threshold)
    #img.save("imgs/black.png")

    remove_noise(img, img_points, max_noisy)
    img.putdata(img_points)
    #img1 = split_fig(img)
    img.save("imgs/rebuild.png")
    vcode = image_to_string(img,config='-psm 8')
    return vcode

class Captcha():
    def __init__(self):
        self.session = requests.session()
        self.session.header = {"Content-Type":"application/x-www-form-urlencoded"}

        self.token = self.baidubce_token()

        if not os.path.isdir('imgs/'):
            os.makedirs('imgs/')

    def baidubce_token(self):
        req_data = {"grant_type":"client_credentials", "client_id":"GmFZoZKX4N9y6o3huUZqb1GO", "client_secret":"oj9SM6QSseATsyukkLSaPpOHQjIwskog"}

        #url = 'https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id=DilGKoUGT7MhK3yPeSGQwvNC&client_secret=yePTFhz5EPG0OM7229mYGugg1EkL7alh'
        r = self.session.get('https://aip.baidubce.com/oauth/2.0/token', params=req_data)

        if r.status_code != 200:
            logging.error('baidubce_token req fail,')
            return None

        try:
            #print(r.text)
            token_json = json.loads(r.text)
        except Exception as e:
            logging.error('baidubce_token json loads r.text fail， %s', traceback.format_exc())
            return None
        if not token_json:
            logging.error('baidubce_token json loads fail..')
            return None

        if 'error' in token_json:
            logging.error('baidubce_token token req err:%s, %s', token_json['error'], token_json['error_description'])
            return None

        return token_json['access_token']


    def captcha_juhe(self, captcha_url):
        capt_data = urllib.request.urlopen(captcha_url, data=None, timeout=3).read()
        open('imgs/captcha.png', 'wb').write(capt_data)
        
        vcode2 = recognize_image('imgs/captcha.png', 45, 10)

        vcode = self.webimage_check(captcha_url)
        if vcode:
            vcode = self.eng_word(vcode)
            if vcode:
                logging.info('webimage captcha:%s', vcode)
                return vcode

        #先判断webimage_check的
        if vcode2:
            vcode2 = self.eng_word(vcode2)
            if vcode2:
                logging.info('recognize captcha:%s', vcode2)
                return vcode2

        #may None
        return None

    def webimage_check(self, captcha_url):
        capt_data = open('imgs/rebuild.png','rb').read()

        captcha = base64.b64encode(capt_data).decode('utf-8')
        req_data = {'image':captcha, "detect_language":True}

        r = self.session.post('https://aip.baidubce.com/rest/2.0/ocr/v1/webimage?access_token='+self.token, data=req_data)
        if r.status_code != 200:
            logging.error('webimage_check req fail,')
            return None

        try:
            capt_json = json.loads(r.text)
        except Exception as e:
            logging.error('webimage_check json loads r.text fail， %s', traceback.format_exc())
            return None
        if not capt_json:
            logging.error('webimage_check json loads fail..')
            return None

        if 'error_code' in capt_json and capt_json['error_code'] != 0:
            logging.error('webimage_check decode fail, code:%s, %s', capt_json['error_code'], capt_json['error_msg'])
            #Access token invalid or no longer valid
            if capt_json['error_code'] == 110:
                self.token = self.baidubce_token()
                return self.webimage_check(captcha_url)
            return None

        if not capt_json['words_result'] or not len(capt_json['words_result'])>0:
            logging.error('webimage_check got words_result fail:%s', r.text)
            return None

        words_result = capt_json['words_result']
        vcode = words_result[0]['words']

        return vcode

    def eng_word(self, vcode):
        #尝试去掉空格、标点等字符
        vcode1 = re.sub('[^A-Za-z]','', vcode)
        vcode1 = self.eng_word2(vcode1)
        if vcode1:
            return vcode1

        #尝试分割
        vcode_split = vcode.split()
        for vcode in vcode_split:
            vcode = re.sub('[^A-Za-z]','', vcode)
            if len(vcode) <= 4:
                #豆瓣验证码一般大于4个单词
                continue

            vcode = self.eng_word2(vcode)
            if vcode:
                return vcode

        return None

    def eng_word2(self, vcode):
        r = self.session.get('https://api.shanbay.com/bdc/search/?word=%s'%vcode)
        if r.status_code != 200:
            logging.error('eng_word check req fail,')
            return None
        try:
            capt_json = json.loads(r.text)
        except Exception as e:
            logging.error('eng_word check json loads r.text fail， %s', traceback.format_exc())
            return None
        if not capt_json:
            logging.error('eng_word check json loads fail..')
            return None

        if capt_json['status_code'] != 0:
            logging.error('eng_word check decode fail, code:%s, %s', capt_json['status_code'], capt_json['msg'])
            return None

        return capt_json['data']['content']


if __name__ == '__main__':
    captcha = Captcha()
    capt2 = captcha.captcha_juhe('http://120.24.59.86:9903/static/imgs/captcha_2.png')
    print(capt2)
    '''
    captlist = os.listdir('imgs/')
    for capt in captlist:
        captcha = Captcha()
        capt2 = captcha.captcha_juhe('http://120.24.59.86:9903/static/imgs/%s'%capt)
        print(capt2)
    '''
