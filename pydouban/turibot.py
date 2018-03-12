# coding=utf-8
import requests
import json  
import logging
import logging.handlers
import random
import traceback
import os
import time
import codecs
import jieba
import jieba.analyse

fool_words_file = u'./static/fool.txt'
jieba_conf = u'./static/jieba.txt'

class appkey_turi():
    def __init__(self):
        self.turi_id = 0
        #turing robot appkey list, each one surpose 5000 req every day
        self.appkey = [u'8b005db5f57556fb96dfd98fbccfab84', u'6273c87d40ee4a379eb9033a909d093c', u'444b0bd6b525439db08382dce5819965', u'aeee9e3c5b4d4a8ba6a105f1b2625d57', u'2264c67beed4472498761e78cb9cd93b']

    def get_next_appkey(self):
        self.turi_id = (self.turi_id + 1) % len(self.appkey)
        return self.appkey[self.turi_id]



class chat_turi():
    def __init__(self):
        self.appkey_turi = appkey_turi()
        self.api_key = self.appkey_turi.get_next_appkey()

        self.content=[u'沙发', u'顶顶顶, 不错不错', u'挽尊',]

        self.session = requests.Session()
        self.session.headers = {
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
                "Origin": "http://www.tuling123.com/openapi/api",
                }

        self.cousin = [u'请叫我顶贴狂魔', u'机器人也很寂寞...你又不找我聊天', u'"你叫我做浮夸吧, 加几声嘘声也不怕"', u'进来刷刷存在感，请不要讨厌我']

        self.__load_fool_words()
        jieba.load_userdict(jieba_conf)

        logging.info("chat_turi init success...")

    def __load_fool_words(self):
        self.fool_words = {}
        f = codecs.open(fool_words_file, 'r', encoding='utf-8')
        line = f.readline().rstrip()
        while line:
            self.fool_words[line] = True
            line = f.readline().rstrip()
        f.close()

    def check_msg(self, info):
        if isinstance(info, bytes):
            info = info.decode('utf-8')
        chat_msg = None
        if ('到处' in info or '哪' in info)  and '都' in info:
            chat_msg = random.choice(self.cousin)
        elif ('老是' in info or '总是' in info) and ('看' in info or '有' in info):
            chat_msg = random.choice(self.cousin)
        elif ('基本' in info or '每个' in info)  and '都' in info:
            chat_msg = random.choice(self.cousin)
        elif '表妹' in info and '都' in info :
            chat_msg = random.choice(self.cousin)

        return chat_msg

    #info must be utf-8
    def __get_chat(self, info, userid=1001, fool=True):
        if isinstance(info, str):
            info = info.encode('utf-8')
        try:
            post_data = {'info':info, 'key':self.api_key, 'userid':userid}
            r = self.session.post(u'http://www.tuling123.com/openapi/api', data=post_data, cookies=self.session.cookies.get_dict())
            dic_res = json.loads(r.text)
            if not dic_res or (dic_res['code'] != 100000 and dic_res['code']!=200000 and dic_res['code']!=302000 and dic_res['code'] != 40002):
                self.api_key = self.appkey_turi.get_next_appkey()

                logging.error("chat_turi got error response:%s"%(str(r.text)))
                chat_msg = random.choice(self.content)
            elif 'url' in dic_res:
                chat_msg = dic_res['text'] + ',  ' + dic_res['url']
            else:
                chat_msg = dic_res['text']
                if fool:
                    for word in self.fool_words:
                        if word in chat_msg:
                            chat_msg = None
                            break

        except Exception as e:
            logging.error("chat_turi send fail, err:%s"%(traceback.format_exc()))
            chat_msg = random.choice(self.content)
        return chat_msg

    def get_chat(self, info, userid=1001):
        chat_msg = self.check_msg(info)
        if chat_msg:
            return chat_msg

        chat_msg = self.__get_chat(info, userid)
        if chat_msg:
            return chat_msg

        if isinstance(info, bytes):
            info = info.decode('utf-8')

        hchat = codecs.open('chat.txt', 'a', encoding='utf-8')
        cut_words = jieba.analyse.extract_tags(info, topK=10)
        for word in cut_words:
            if word == '广州':
                continue
            chat_msg = self.__get_chat(word, userid)
            if chat_msg:
                print('word:',word, chat_msg)

                hchat.write('info:'+info+'\n')
                hchat.write('tags:'+' '.join(cut_words)+'\n')
                hchat.write('word:'+word+'\n')
                hchat.write('chat:'+chat_msg+'\n\n')
                hchat.close()
                return chat_msg

        chat_msg = self.__get_chat(info, userid, fool=False)
        hchat.write('info:'+info+'\n')
        hchat.write('chat:'+chat_msg+'\n\n')
        return chat_msg


    def rand_chat(self):
        return random.choice(self.content)

if __name__ == '__main__':  
    log_dir = 'log/'
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(level=logging.INFO,
            format='[%(asctime)s %(name)-12s %(levelname)-s] %(message)s',
            datefmt='%m-%d %H:%M:%S',
            #filename=time.strftime('log/turibot.log'),
            filemode='a')

    htimed = logging.handlers.TimedRotatingFileHandler("log/turibot.log", 'D', 1, 0)
    htimed.suffix = "%Y%m%d-%H%M"
    htimed.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s %(name)-12s %(levelname)-s] %(message)s', datefmt='%m-%d %H:%M:%S')
    htimed.setFormatter(formatter)

    logging.getLogger('').addHandler(htimed)

    turi1 = chat_turi()
    while True:
        msg = input("i: ")
        chat_msg = turi1.get_chat(msg)
        print('turi:%s'%(chat_msg))



