# coding=utf-8
import requests
import logging
import json
import traceback

if __name__=='__main__':
    words = open('big.txt', 'r').read().split()

    session = requests.session()
    word_dict = {}
    for word in words:
        r = session.get('https://api.shanbay.com/bdc/search/?word=%s'%word)
        if r.status_code != 200:
            logging.error('captcha_juhe word req fail,')
            continue
        try:
            capt_json = json.loads(r.text)
        except Exception as e:
            logging.error('captcha_juhe word json loads r.text fail， %s', traceback.format_exc())
            continue
        if not capt_json:
            logging.error('captcha_juhe word json loads fail..')
            continue

        if capt_json['status_code'] != 0:
            logging.error('captcha_juhe word decode fail, code:%s, %s', capt_json['status_code'], capt_json['msg'])
            continue
        word = capt_json['data']['content']
        word_dict[word] = True

    hbig = open('big.txt','w')
    for word in word_dict:
        hbig.write(word)
        hbig.write('\n')
    hbig.close()
        

