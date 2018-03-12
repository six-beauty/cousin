# coding=utf-8

import requests
import logging
import traceback
import json
import urllib
import base64


class Captcha():
    def __init__(self):
        self.session = requests.session()
        self.session.header = {"Content-Type":"application/x-www-form-urlencoded"}

        self.token = self.baidubce_token()

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
        captcha = base64.b64encode(capt_data).decode('utf-8')
        req_data = {'image':captcha, "detect_language":True}

        r = self.session.post('https://aip.baidubce.com/rest/2.0/ocr/v1/webimage?access_token='+self.token, data=req_data)
        if r.status_code != 200:
            logging.error('captcha_juhe req fail,')
            return None

        try:
            capt_json = json.loads(r.text)
        except Exception as e:
            logging.error('captcha_juhe json loads r.text fail， %s', traceback.format_exc())
            return None
        if not capt_json:
            logging.error('captcha_juhe json loads fail..')
            return None

        print(capt_json)
        if 'error_code' in capt_json and capt_json['error_code'] != 0:
            logging.error('captcha_juhe decode fail, code:%s, %s', capt_json['error_code'], capt_json['error_msg'])
            #Access token invalid or no longer valid
            if capt_json['error_code'] == 110:
                self.token = self.baidubce_token()
                return self.captcha_juhe(captcha_url)
            return None

        if not capt_json['words_result'] or not len(capt_json['words_result'])>0:
            logging.error('captcha_juhe got words_result fail:%s', r.text)
            return None

        print(capt_json['words_result'])
        words_result = capt_json['words_result']
        vcode = words_result[0]['words']

        r = self.session.get('https://api.shanbay.com/bdc/search/?word=%s'%vcode)
        if r.status_code != 200:
            logging.error('captcha_juhe word req fail,')
            return None
        try:
            capt_json = json.loads(r.text)
        except Exception as e:
            logging.error('captcha_juhe word json loads r.text fail， %s', traceback.format_exc())
            return None
        if not capt_json:
            logging.error('captcha_juhe word json loads fail..')
            return None

        if capt_json['status_code'] != 0:
            logging.error('captcha_juhe word decode fail, code:%s, %s', capt_json['status_code'], capt_json['msg'])
            return None

        return vcode

if __name__ == '__main__':
    captcha = Captcha()
    capt = captcha.captcha_juhe('https://www.douban.com/misc/captcha?id=QaNtcfp4BfSFpFLt5hYQZQTy:en&size=s')
    print(capt)
