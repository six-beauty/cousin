# -*- coding: utf-8 -*-

import requests
import requests.utils
import pickle
import codecs
import re
import os
import random
import logging
import logging.handlers
import time
import bs4 
import turibot
import redis
import queue
import urllib
import json
import traceback
import threading
import captcha
import correct

#send_mail
import smtplib  
import email.mime.multipart  
import email.mime.text  
import email.utils

class captcha_mail:
    def __init__(self):
        self.from_addr = 'sanyue9394@126.com'
        self.from_passwd = 'sanyue214008'
        self.to_addr = ['sanyue9394@126.com']

        self.smtp=smtplib.SMTP()  
        self.smtp.connect('smtp.126.com','25')  
        self.smtp.login(self.from_addr, self.from_passwd)  

    def __del__(self):
        self.smtp.quit()  

    def send_mail(self, post_url, captcha_url):
        content = """
        -----------------begin---------------------------
        douban work, post_url: %s

        captcha url: %s

        captcha code input: http://120.24.59.86:9903/
        ------------------end----------------------------
        """%(post_url, captcha_url)

        mail_msg=email.mime.multipart.MIMEMultipart()  
        mail_msg['From']=self.from_addr
        mail_msg['To']=email.utils.COMMASPACE.join(self.to_addr)
        mail_msg['Subject']='captcha new notify'  
        mail_msg['Date'] = email.utils.formatdate(localtime=True)
        text=email.mime.text.MIMEText(content, 'plain', 'utf-8')  
        mail_msg.attach(text)  

        self.smtp.sendmail(self.from_addr, self.to_addr, mail_msg.as_string())  
##send_mail

redis_port=52021
COOKIES_FILE = 'data/cookies.txt'
emoji_re = re.compile(u'('
        u'\ud83c[\udf00-\udfff]|'
        u'\ud83d[\udc00-\ude4f\ude80-\udeff]|'
        u'[\u2600-\u26FF\u2700-\u27BF])+', 
        re.UNICODE)

#self answer mail
self_mail = [122619569, 54451019]
#self topics不回复
my_topics = [106547648,111516608, 112933822, 112932149, 112933816, 112933934, 113515127, 113515502]
#ignore topics
ignore_topics = [106547305, 106547516, 106551311]
lokiok=52272009

#不回复的豆瓣id
ignore_topic_douban_id = [102393339, 167730677, ]
#雪亭
#ignore_topic_douban_id.append(52272009)

alive=False
class DoubanRobot:
    '''
    A simple robot for douban.com
    '''
    def __init__(self, account_id, password, douban_id, hotReload=False):
        self.ck = None

        #turing
        self.turi = turibot.chat_turi()
        #redis
        self.redis = redis.StrictRedis(host='localhost', port=redis_port)    

        #itchat thread
        self.capt_queue = queue.Queue(1)
        self.sofa_queue = queue.Queue()

        self.captcha = captcha.Captcha()
        self.captcha_last = time.time()

        self.sofa_dic = {}
        self.doumail_dic = {}
        self.notify_dic = {}
        self.temp_ignore = {}

        #douban robot
        self.douban_id = str(douban_id)
        self.account_id = account_id
        self.password = password
        self.data = {
                "form_email": self.account_id,
                "form_password": self.password,
                "source": "index_nav",
                "remember": "on",
                "user_login": "登录"
                }
        self.session = requests.Session()
        self.login_url = 'https://www.douban.com/accounts/login'
        self.mail_url = "https://www.douban.com/j/doumail/send"

        self.session.headers = {
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36",
                "Origin": "https://www.douban.com",
                }
        # self.session.headers = self.headers
        if not hotReload:
            self.login()
        elif self.load_cookies():
            self.get_ck(None)

    def get_chat(self, msg, uid):
        if '表妹' in msg or '夏文' in msg:
            if msg == '表妹' or msg == '夏文':
                content = [u'你好', u'你是谁', u'在吗']
                msg = random.choice(content)
            else:
                msg = msg.replace('表妹', '你')
                msg = msg.replace('夏文', '你')
        chat_msg = self.turi.get_chat(msg, uid)
        return chat_msg

    def load_cookies(self):
        '''
        load cookies from file.
        '''
        cdir, cbase = os.path.split(COOKIES_FILE)
        if not os.path.isdir(cdir):
            os.makedirs(cdir)
        try:
            with open(COOKIES_FILE, 'rb') as f:
                self.session.cookies = requests.utils.cookiejar_from_dict(pickle.load(f))
            return True
        except Exception as e:
            logging.error('faild to load cookies from file, err:{0}'.format(e))
            return False

    def save_cookies(self, r):
        '''
        save cookies to file.
        '''
        cdir, cbase = os.path.split(COOKIES_FILE)
        if not os.path.isdir(cdir):
            os.makedirs(cdir)
        if r.cookies:
            self.session.cookies.update(r.cookies)
        with open(COOKIES_FILE, 'wb+') as f:
            pickle.dump(requests.utils.dict_from_cookiejar(self.session.cookies), f)
        logging.info('save cookies to file.')

        self.get_ck(r)

    def get_ck(self, r):
        '''
        open douban.com and then get the ck from html.
        '''
        if not r:
            r = self.session.get('https://www.douban.com/accounts/',cookies=self.session.cookies.get_dict())
        cookies = self.session.cookies.get_dict()
        headers = dict(r.headers)
        if 'ck' in cookies:
            self.ck = cookies['ck'].strip('"')
            logging.info("ck:%s" %self.ck)
        elif 'Set-Cookie' in headers:
            logging.info('cookies is end of date, login again')
            self.ck = None
            self.login()
        else:
            logging.error('cannot get the ck. ')
            raise Exception('cannot get the ck. ')

    def input_captcha(self):
        global alive
        if alive:
            return
        alive = True
        try:
            redis_sub = self.redis.pubsub()
            redis_sub.subscribe(['vcode'])
            for item in redis_sub.listen():
                if item['type'] == 'message':
                    vcode = item['data']
                    vcode = vcode.decode('utf-8')
                    self.capt_queue.put(vcode)
                    logging.info('input vcode:%s', vcode)

                    if not vcode in correct.WORDS:
                        correct.WORDS.update(re.findall(r'\w+', vcode))
                        open('static/big.txt', 'a').write('\n%s'%vcode)
                    break
            redis_sub.unsubscribe(['vcode'])
        except:
            logging.error('===input_captcha fail, %s', traceback.format_exc())
        alive = False

    def identify_code_check(self, r, post_url, post_data):
        # 验证码,需要处理
        captcha = re.search('<input type="hidden" name="captcha-id" value="(.+?)"/>', r.text)
        if not captcha:
            captcha = re.search(r"REPLY_FORM_DATA.captcha = {\n\s*id: '(.*?)',", r.text)

        if not captcha:
            return r

        #identify code id
        captcha_id = captcha[1]
        imgurl = "https://www.douban.com/misc/captcha?id={0}&size=s".format(captcha_id)
        logging.info('post_url:%s, captcha url: %s', post_url, imgurl)
 
        if r'/login' in post_url or (self.captcha_last and time.time() - self.captcha_last < 3):
            self.redis.set('captcha', captcha_id)
            capt = captcha_mail()
            capt.send_mail(post_url, imgurl)

            tt = threading.Thread(target=self.input_captcha)
            tt.start()

            vcode=None
            while True:
                try:
                    logging.info('wait for code input:')
                    vcode=self.capt_queue.get(timeout=32*60)
                    logging.info('capt_queue get vcode:%s', vcode)
                    break
                except Exception as e:
                    logging.info('vcode timeout')
                    session = requests.Session()
                    r1 = session.get(imgurl)
                    invalid = re.search(r'<title>页面不存在</title>', r1.text, re.DOTALL)
                    if invalid:
                        #过期
                        logging.info('vcode html expire!!')

                        if r'/login' in post_url:
                            r = self.session.get(post_url, cookies=self.session.cookies.get_dict())
                            captcha = re.search('<input type="hidden" name="captcha-id" value="(.+?)"/>', r.text)
                            if not captcha:
                                logging.info("login captcha check expire.")
                                break
                            else:
                                captcha_id = captcha[1]
                                self.redis.set('captcha', captcha_id)
                                imgurl = "https://www.douban.com/misc/captcha?id={0}&size=s".format(captcha_id)
                                logging.info(r'/login post_url:%s, new captcha url: %s', post_url, imgurl)

                        else:
                            break
        else:
            vcode = self.captcha.captcha_juhe(imgurl)
            logging.info('captcha_juhe get captcha:%s', vcode)

            self.captcha_last = time.time()
            if not vcode:
                #没有，重新进入mail captcha流程
                return self.identify_code_check(r, r.url, post_data)

        if 'misc/sorry' in r.url:
            post_data2 = {}
            post_data2['ck'] = self.ck
            post_data2["captcha-solution"] = vcode
            post_data2["captcha-id"] = captcha_id
            post_data2['original-url'] = "https://www.douban.com/"
            r = self.session.post(r.url, data=post_data2, cookies=self.session.cookies.get_dict())
        else:
            post_data["captcha-solution"] = vcode
            post_data["captcha-id"] = captcha_id
            r = self.session.post(post_url, data=post_data, cookies=self.session.cookies.get_dict())

        save_html('identify.html',r.text)

        logging.info('captcha solution:%s, id:%s, url:%s', vcode, captcha_id, r.url)
        r = self.identify_code_check(r, r.url, post_data)

        return r

    def login_check(self):
        if not self.ck:
            logging.error('ck is invalid!')
            raise Exception('login fail, ck is invalid')

    def login(self):
        '''
        login douban.com and save the cookies to file.
        '''
        self.session.cookies.clear()

        self.session.headers["Referer"] = "https://www.douban.com/"
        r = self.session.post(self.login_url, data=self.data, cookies=self.session.cookies.get_dict())  #核心语句数据从其中传入
        save_html('login.html', r.text)

        # 验证码
        try:
            r=self.identify_code_check(r, self.login_url, self.data)
        except Exception as e:
            logging.error('login identify err:%s, try again!'%(e))
            return 

        #result
        if r.url == 'https://www.douban.com/':
            self.save_cookies(r)
            logging.info('login successfully!')
        else:
            logging.error('Faild to login, check username and password and captcha code. save error.html, url:%s'%(r.url))
            save_html('login_error.html', r.text)

            self.ck = None

            if 'safety/locked’ in r.url':
                logging.info('safety locked, sleep 4 hours')
                time.sleep(3*60*60)

    def get_my_topics(self):
        homepage_url = self.douban_id.join(['https://www.douban.com/group/people/','/publish'])
        r = self.session.get(homepage_url).text
        topics_list = re.findall(r'<a href="https://www.douban.com/group/topic/([0-9]+)/', r)
        return topics_list

    def new_topic(self, group_id, title, content='Post by python'):
        '''
        use the ck pulish a new topic on the douban group.
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return False
        group_url = "https://www.douban.com/group/" + group_id
        post_url = group_url + "/new_topic"
        post_data = {
                'ck':self.ck,
                'rev_title': title ,
                'rev_text': content,
                'rev_submit':'好了，发言',
                }
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())
        # save_html('3.html', r.text)

        # 验证码
        try:
            r=self.identify_code_check(r, post_url, post_data)
        except Exception as e:
            logging.error('new_topic identify err:%s!'%(e))
            return False

        if r.url == post_url:
            logging.info('Okay, new_topic: "%s" post successfully !'%title)
            return True
        return False

    def talk_status(self, content='Hello.it\'s a test message using python.'):
        '''
        talk a status.
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return False

        post_data = {
                'ck' : self.ck,
                'comment' : content,
                }

        self.session.headers["Referer"] = "https://www.douban.com/"
        r = self.session.post("https://www.douban.com/", post_data, cookies=self.session.cookies.get_dict())
        # save_html('3.html', r.text)
        if r.status_code == 200:
            logging.info('Okay, talk_status: "%s" post successfully !'%content)
            return True

    def broadcast_mail(self, m_text):
        '''
        doumail topics
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return 0

        post_data = {
                'ck' : self.ck,
                }
        post_url = "https://www.douban.com/doumail/#topics"
        self.session.headers["Referer"] = post_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())
        #save_html('doumail.html', r.text)

        content = re.findall(r'(<div id="content">.*?)\s*<div id=".*?">', r.text, re.DOTALL)[0]

        soup = bs4.BeautifulSoup(content, "html.parser")
        mail_list = []
        for tag in soup.div.div.div.form.descendants:
            if type(tag) != bs4.element.Tag or tag.name != 'li':
                continue
            mail_list.append(tag)

        for mail in mail_list :
            msg = re.search(r'<a class="url" href="https://www.douban.com/doumail/(\d*)/">', mail.prettify(), re.DOTALL)
            self.send_mail(m_text)

    def answer_unread_mail(self, unread=True):
        '''
        doumail topics
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return 0

        #1. unread mail
        post_data = {
                'ck' : self.ck,
                }
        post_url = "https://www.douban.com/doumail/#topics"
        self.session.headers["Referer"] = post_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

        mail_nums = 0
        # save_html('unread_mail.html', r.text)
        content = re.findall(r'(<div id="content">.*?)\s*<div id=".*?">', r.text, re.DOTALL)[0]
        soup = bs4.BeautifulSoup(content, "html.parser")
        mail_list = []
        for tag in soup.div.div.div.form.descendants:
            if type(tag) != bs4.element.Tag or tag.name != 'li':
                continue
            mail_list.append(tag)

        for mail in mail_list :
            if not 'class' in mail.attrs or mail.attrs['class'][0] != 'state-unread':
                continue

            # unread mail
            msg = re.search(r'<a class="url" href="https://www.douban.com/doumail/(\d*)/">', mail.prettify(), re.DOTALL)

            #system mail, ignore
            if not msg:
                continue
            uid = msg[1]

            #send mail back to uid
            b_ans = self.answer_mail(uid)
            if b_ans:
                mail_nums = mail_nums + 1

            if b_ans and mail_nums % 4 == 0:
                logging.info("unread mail times:%s, sleep 60's", mail_nums)
                time.sleep(60)
            else:
                time.sleep(1)

        #2. redis unread
        uid = self.redis.lpop('unread_mail')
        while uid:
            uid = uid.decode('utf-8')

            #send mail back to uid
            b_ans = self.answer_mail(uid)
            if b_ans:
                mail_nums = mail_nums + 1

            if b_ans and mail_nums % 4 == 0:
                logging.info("rds unread mail times:%s, sleep 60's", mail_nums)
                time.sleep(60)
            else:
                time.sleep(1)
            uid = self.redis.lpop('unread_mail')

        return mail_nums

    def answer_mail(self, uid):
        msg_id = 0
        if uid in self.doumail_dic:
            msg_id = self.doumail_dic[uid]
        else:
            msg_id = self.redis.get('mail:%s'%(uid)) or 0
            self.doumail_dic[uid] = int(msg_id)
        msg_id = int(msg_id)

        #first mail
        if msg_id == 0:
            chat_msg = u'夏文表妹是机器人，如果她在你发的帖下打扰到你，请允许我在这里向你道歉。\n\r  假如你觉得表妹挺有意思的话，不妨多和她聊聊呗。\n\r  豆瓣的接口限制了访问频率，邮件回复可能没办法太快，请多多包涵。\n\r磁力搜索网站已经停止解析，个人地址可以私信表妹:"网站链接".  欢迎下次光临⚆_⚆\n\r'
            send_res = self.send_mail(uid, chat_msg)


        if not self.ck:
            logging.error('ck is invalid!')
            return False

        post_data = {
                'ck' : self.ck,
                }
        post_url = "https://www.douban.com/doumail/{0}/".format(uid)
        self.session.headers["Referer"] = post_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

        mails = re.findall(r'<div class="chat".*?data="(.*?)">.*?<div class="content">.*?<a href="https://www.douban.com/people/(.*?)/">.*?<p>(.*?)</p>', r.text, re.DOTALL)

        max_id, mail_num = msg_id, 0
        for mail in mails:
            mail_id, send_uid, msg = int(mail[0]), mail[1], mail[2]

            #一次不回复太多消息
            if mail_id <= msg_id:
                #logging.info("continue mail_id:%s, msg_id:%s, uid:%s, msg:%s", mail_id, msg_id, send_uid, msg)
                continue

            if send_uid == self.douban_id:
                #self mail
                max_id = max(max_id, mail_id)

                #console
                if 'cmd:stop' == msg:
                    logging.info("stop reply, uid:%s, msg:%s",uid,msg)
                    self.temp_ignore[int(uid)] = time.time()
                    #add self_mail
                    self_mail.append(int(uid))

                    self.send_mail(uid, 'got it, stop reply 60min!')
                elif 'cmd:start' == msg:
                    logging.info("start reply, uid:%s, msg:%s",uid,msg)
                    if int(uid) in self.temp_ignore:
                        del self.temp_ignore[int(uid)]
                    self.send_mail(uid, 'got it, start reply!')

            elif mail_id > msg_id:
                if int(uid) in self.temp_ignore:
                    last_time = self.temp_ignore[int(uid)] or 0
                    #3 min
                    if time.time() - last_time > 3600:
                        del self.temp_ignore[int(uid)]
                    else:
                        max_id = max(max_id, mail_id)
                        continue 
                if mail_num > 3:
                    max_id = max(max_id, mail_id)
                    continue 

                '''
                if '表哥' in msg or '写代码的' in msg or '抠脚' in msg:
                    chat_msg = '同学你好哇，对表妹有什么建议吗，可以联系我微信:sanyue9394。\n\r  假如表妹骚扰到你，深感抱歉。微信告诉我的话，我会修改它的代码。\n\r  假如你对骑行有兴趣的话，很可惜，我也有一年没玩了，不过有兴趣交流的话，不妨message我吧(smile) \n\r   欢迎下次光临⚆_⚆\n\r'
                elif ('表哥' in msg or '大汉' in msg) and '照片' in msg:
                    image_urls = ['https://www.douban.com/photos/photo/2494128984/',]
                    chat_msg = random.choice(image_urls)
                else:
                '''
                #普通聊天消息
                if '网站链接' in msg or '网站地址' in msg or '磁力链接' in msg:
                    chat_msg = '磁力搜索网站链接: http://121.196.207.196:5002 \n\r可以的话，不妨关注一下， 帮忙顶下帖(https://www.douban.com/group/topic/113515502/?start=0, https://www.douban.com/group/topic/113515127/)吧，同学 :)'
                else:
                    chat_msg = self.get_chat(msg, uid)

                if int(uid) in self_mail:
                    max_id = max(max_id, mail_id)
                    continue

                send_res = self.send_mail(uid, chat_msg)

                #send mail fail
                if not send_res:
                    logging.error('send_mail fail, uid:%s, msg:%s, lpush unread_mail', uid, msg)
                    self.redis.lpush('unread_mail', uid)
                else:
                    logging.info("[mail]:%s, mail:%s, answer:%s", uid, msg, chat_msg)
                    max_id = max(max_id, mail_id)
                    mail_num = mail_num + 1

        if max_id > msg_id:
            self.doumail_dic[uid] = int(max_id)
            self.redis.set('mail:%s'%(uid), int(max_id))
        return True

    def mail_switch(self):
        logging.warning('send mail url switch, url:%s', self.mail_url)
        if self.mail_url == "https://www.douban.com/j/doumail/send":
            self.mail_url = "https://www.douban.com/doumail/write"
        else:
            self.mail_url = "https://www.douban.com/j/doumail/send"


    def send_mail(self, uid, content = '测试豆油，keep moving!'):
        '''
        send a doumail to other.
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return False

        post_data = {
                "ck" : self.ck,
                "m_submit" : "好了，寄出去",
                "m_text" : '表妹：' + content,
                "to" : uid,
                }
        self.session.headers["Referer"] = "https://www.douban.com/doumail/"
        post_url = self.mail_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

        # 验证码
        try:
            r=self.identify_code_check(r, post_url, post_data)

            if r.url == "https://www.douban.com/doumail/":
                #doumail/write success
                logging.info('Okay, send_mail: To %s doumail "%s" successfully !', uid, r.url)
            elif r.url == "https://www.douban.com/j/doumail/send":
                res = json.loads(r.text)
                if "error" in res:
                    logging.error('send_mail fail, url:j/doumail/send, got error!!')
                    self.mail_switch()
                    return False
                if "r" in res and res["r"] != 0:
                    logging.error('send_mail fail, url:j/doumail/send, text:%s', r.text)
                    self.login()
                    return False

                logging.info('Okay, send_mail: To %s doumail "%s", %s', uid, r.url, r.text)
            else:
                # save_html('mail_error1.html', r.text)
                logging.error('send_mail fail, to uid:%s, url:%s', uid, r.url)
                self.mail_switch()
                return False
        except Exception as e:
            logging.error('send_mail identify err:%s! not try again', traceback.format_exc() )
            # save_html('mail_error2.html', r.text)
            self.mail_switch()
            return False

        return True


    #topics_list = app.get_my_topics()
    #app.topics_up(topics_list)
    def topics_up(self,
            topics_list,
            content=['顶',
                '顶帖',
                '自己顶',
                'waiting',]
            ):
        '''
        Randomly select a content and reply a topic.
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return False


        # For example --> topics_list = ['22836371','98569169']
        #topics_list = ['22836371','98569169']
        for item in topics_list:
            post_data = {
                    "ck" : self.ck,
                    "rv_comment" : random.choice(content),
                    "start" : "0",
                    "submit_btn" : "加上去"
                    }

            r = self.session.post("https://www.douban.com/group/topic/" + item + "/add_comment#last?", post_data, cookies=self.session.cookies.get_dict())
            if r.status_code == 200:
                logging.info('Okay, already up ' + item + ' topic' )
            logging.info("topic up, sleep 60's")
            time.sleep(60)  # Wait a minute to up next topic, You can modify it to delay longer time
        return True

    # e.g. https://www.douban.com/group/topic/22836371/
    #app.delete_comments('group_topic_url')   
    def delete_comments(self,topic_url):
        topic_id = re.findall(r'([0-9]+)', topic_url)[0]
        content = self.session.get(topic_url).text
        comments_list = re.findall(r'<li class="clearfix comment-item" id="[0-9]+" data-cid="([0-9]+)" >', content)
        # Leave last comment and delete all of the past comments
        for item in comments_list[:-1]:
            post_data = {
                    "ck"  : self.ck,
                    "cid" : item
                    }
            r = self.session.post("https://www.douban.com/j/group/topic/" + topic_id + "/remove_comment", post_data, cookies=self.session.cookies.get_dict())
            if r.status_code == 200:
                logging.info('Okay, already delete ' + topic_id + ' topic' )  # All of them return 200... Even if it is not your comment
            time.sleep(10)  # Wait ten seconds to delete next one
        return True

    def sofa_monitor(self, session, group_id):

        group_url = "https://www.douban.com/group/" + group_id +"/#topics"

        #减少账号连接session请求数
        #r = self.session.get(group_url, cookies=self.session.cookies.get_dict())
        r =session.get(group_url, cookies=session.cookies.get_dict())
        topics = re.findall(r'<a href="https://www.douban.com/group/topic/(\d+?)/" title="(.*?)" class="">.*?"https://www.douban.com/people/(\d+?)/" class="">(.*?)</a></td>', r.text, re.DOTALL)
        #save_html('sofa_%s.html'%group_id, r.text)

        sofa_time = 0
        for item in topics:
            topic_id, title, uid, nickname = item[0], item[1], item[2], item[3]
            exists = topic_id in self.sofa_dic
            if not exists:
                exists = self.redis.exists('sofa:%s'%topic_id)
            else:
                continue

            #过滤
            if int(uid) in ignore_topic_douban_id:
                self.redis.set('sofa:%s'%topic_id, 1)
                self.sofa_dic[topic_id] = True
                return True

            #redis那次的过滤,exists
            self.sofa_dic[topic_id] = True
            if not exists:
                sofa_item = [topic_id, title, uid, nickname]
                self.sofa_queue.put(sofa_item)

                sofa_time = sofa_time + 1

        if sofa_time>0:
            logging.info('%s sofa_monitor event:%s', group_id, sofa_time)

        return sofa_time

    def sofa_qsize(self):
        return self.sofa_queue.qsize()

    def sofa(self, times=0):
        if not self.ck:
            logging.error('ck is invalid!')
            return 0

        if self.sofa_queue.empty():
            return 0

        sofa_time = 0
        while times>0:
            times = times-1
            try:
                sofa_item = self.sofa_queue.get(timeout=1)
            except Exception as e:
                #没有sofa数据了
                break

            topic_id, title, uid, nickname = sofa_item[0], sofa_item[1], sofa_item[2], sofa_item[3]
            post_url = "https://www.douban.com/group/topic/" + topic_id + "/add_comment#last?"

            title = emoji_re.sub(r'', title)
            chat_msg = self.get_chat(title, uid)
            logging.info(u"topic:%s, uid:%s[%s], [%s], up:%s",topic_id, uid, nickname, title, chat_msg)

            post_data = {
                    "ck" : self.ck,
                    "rv_comment" : chat_msg,
                    "start" : "0",
                    "submit_btn" : "加上去"
                    }
            r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())
            #save_html('sofa.html', r.text)

            # 验证码
            try:
                r=self.identify_code_check(r, post_url, post_data)
            except Exception as e:
                logging.error('new_topic identify err:%s!'%(e))
                return sofa_time

            if r.status_code == 200:
                self.redis.set('sofa:%s'%topic_id, uid)
                logging.info('[sofa],https://www.douban.com/group/topic/%s:"%s" successfully!'%(topic_id, chat_msg))
            else:
                #save_html('topic_%s.html'%(topic_id), r.text)
                self.sofa_dic[topic_id] = False
                logging.error('sofa fail, topic id:%s', topic_id)

            sofa_time = sofa_time + 1
            #避免sofa_time一直是4
            time.sleep(3)

        return sofa_time

    def answer_unread_notify(self):
        '''
        doumail topics
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return 0

        post_data = {
                'ck' : self.ck,
                }
        post_url = "https://www.douban.com/notification/"
        self.session.headers["Referer"] = post_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())
        #save_html('notifycation.html', r.text)

        notifys = re.findall(r'<div id="reply_notify_(\d*)" class="item-req ">.*?<a href="https://www.douban.com/group/topic/(\d*)/\?start=(\d*)#(\d*)" target="_blank">.*?</a>(.*?)\n', r.text, re.DOTALL)

        notify_nums = 0
        for notify in notifys:
            notify_id, topic_id, start, cid, msg= notify[0], notify[1], notify[2], notify[3], notify[4]

            if int(topic_id) in my_topics or int(topic_id) in ignore_topics or '赞' in msg:
                continue

            b_ans = self.answer_notify(notify_id, topic_id, start, cid)
            if b_ans:
                notify_nums = notify_nums + 1
            if b_ans and notify_nums % 4 == 0:
                logging.info("answer_notify nums:%s, break and sleep", notify_nums)
                break
            elif b_ans:
                #每个notify直接间隔
                time.sleep(1)

        time.sleep(3)

        return notify_nums

    def answer_notify(self, notify_id, topic_id, start, cid):
        exists = notify_id in self.notify_dic
        if not exists:
            exists = self.redis.exists('notify:%s'%notify_id)
        else:
            return False

        if not exists:
            post_data = { 'ck' : self.ck, }
            post_url = "https://www.douban.com/group/topic/{0}/?start={1}#{2}".format(topic_id, start, cid)
            self.session.headers["Referer"] = post_url
            r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

            topics = re.findall(r'data-cid="{0}".*?<div class="reply-quote">.*?<p class="">(.*?)</p>.*?<div class="operation_div" id="(\d*)">'.format(cid), r.text, re.DOTALL)

            if not topics or len(topics)==0 :
                self.redis.set('notify:%s'%notify_id, 1)
                self.notify_dic[notify_id] = True
                logging.error('answer notify:%s fail, cid:%s', notify_id, cid)
                return False

            topic = topics[0]
            content, uid = topic[0], topic[1]

            #self topic
            if uid == self.douban_id or int(uid) in ignore_topic_douban_id:
                self.redis.set('notify:%s'%notify_id, 1)
                self.notify_dic[notify_id] = True
                return False

            #get turi chat msg
            chat_msg = self.get_chat(content, uid)
            post_data = {
                    "ck" : self.ck,
                    "rv_comment" : chat_msg,
                    "ref_cid" : cid,
                    "start" : start,
                    "submit_btn" : "加上去",
                    "start" : 0,
                    }
            post_url2 = "https://www.douban.com/group/topic/" + str(topic_id) + "/add_comment#last"
            self.session.headers["Referer"] = post_url2
            r = self.session.post(post_url2, post_data, cookies=self.session.cookies.get_dict())
            # 验证码
            try:
                r=self.identify_code_check(r, post_url2, post_data)
            except Exception as e:
                logging.error('new_topic identify err:%s!'%(e))
                return False

            if r.status_code == 200:
                self.redis.set('notify:%s'%notify_id, 1)
                self.notify_dic[notify_id] = True
                logging.info('Okay, [%s] uid:%s, content:%s, notify:"%s" successfully!'%(post_url, uid, content, chat_msg))
            else:
                logging.error('notify fail, topic id:%s', notify_id)
        else:
            self.notify_dic[notify_id] = True
            return False

        return True

    def discuss_spider(self, start_id=0):
        '''
        discuss spider
        '''
        if not self.ck:
            logging.error('ck is invalid!')
            return

        post_data = {
                'ck' : self.ck,
                }
        post_url = "https://www.douban.com/group/GuangZhoulove/discussion?start=%s"%(start_id)
        self.session.headers["Referer"] = post_url
        r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

        notifys = re.findall(r'<td class="title">.*?<a href="https://www.douban.com/group/topic/(\d*)/" title="(.*?)".*?class="time">(.*?)</td>', r.text, re.DOTALL)
        for notify in notifys:
            topic_id, title, topic_time = notify[0], notify[1], notify[2]
            if self.redis.hget('discuss', topic_id) != None:
                logging.error('repeat topic_id:%s, start_id:%s', topic_id, start_id)
                continue 

            post_url = "https://www.douban.com/group/topic/%s/"%(topic_id)
            self.session.headers["Referer"] = post_url
            r = self.session.post(post_url, post_data, cookies=self.session.cookies.get_dict())

            contents = re.findall(r'<div class="topic-content">.*?<p>(.*?)</p>', r.text, re.DOTALL)
            content = ''
            if len(contents)!=0:
                content = contents[0]

            text = {'topic':topic_id, 'title':title, 'content':content, 'time':topic_time}
            with codecs.open('douban/%s.txt'%(topic_id), 'w+', encoding='utf-8') as f:
                f.write(json.dumps(text))

            self.redis.hset('discuss', topic_id, 1)
            time.sleep(3)

def save_html(name, data):
    save_dir='html/'
    if not os.path.isdir(save_dir):
        os.makedirs(save_dir)
    save_path = save_dir+name
    with codecs.open(save_path, 'w', encoding='utf-8') as f:
        f.write(data)

def save_image(imgurl, captcha):
    imgdata = urllib.request.urlopen(imgurl, data=None, timeout=3).read()
    with open(captcha, 'wb') as image:
        image.write(imgdata)


circle_times = 0
def monitor_work(douban, circle_num):
    global circle_times

    logging.info('monitor work start, circle_num:%s', circle_num)
    session = requests.Session()
    session.headers = {
            "Connection": "keep-alive",
            "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
            "Origin": "https://www.douban.com",
            }
    '''
    session.proxies = {
            'http': 'socks5://127.0.0.1:1080',
            'https': 'socks5://127.0.0.1:1080',
            }
    '''
    while circle_times == circle_num:
        try:
            qsize = douban.sofa_qsize()

            sofa_group = ['gz', 'GuangZhoulove', '596537', '613361', 'liveinguangzhou']
            sofa_num = 0
            for group_id in sofa_group:
                size = douban.sofa_monitor(session, group_id)
                sofa_num = sofa_num + size
                time.sleep(3)

            tm = time.localtime()
            if tm.tm_hour >= 3 and tm.tm_hour < 5:
                #凌晨3点到4点， sleep 2.5 hours
                tt = 152*60
            elif tm.tm_hour>=5 and tm.tm_hour <7:
                #凌晨5点到7点， sleep 30 mins
                tt = 30*60
            elif sofa_num < 4 and qsize > 12:
                tt = 6*60
            elif sofa_num > 4 and qsize < 4:
                tt = 60
            else:
                tt = 3*60

            logging.info("monitor_work sofa_num:%s, qsize:%s, sleep %s's", sofa_num, douban.sofa_qsize(), tt)
            time.sleep(tt)
        except Exception as e:
            logging.error("monitor work raise Exception, sleep 15'mins, %s",traceback.format_exc())
            time.sleep(15*60)
            session = requests.Session()
            session.headers = {
                "Connection": "keep-alive",
                "User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.2pre) Gecko/20070215 K-Ninja/2.1.1",
                "Origin": "https://www.douban.com",
                }


def work(hotReload=False):
    global circle_times
    account_id =  '15989010132'    # your account no (E-mail or phone number)
    password   =  'douban214008'    # your account password
    douban_id  =  '161638302'    # your id number

    douban = DoubanRobot(account_id, password, douban_id, hotReload=hotReload)
    tt = threading.Thread(target=monitor_work, args=(douban, circle_times))
    tt.start()

    #app.talk_status('python3 确实很帅，架构决定重搭。豆油已修复，来豆油我吧!')
    while True:
        try:
            douban.login_check()

            #循环处理多少次
            times_unread_mail, times_unread_notify, times_sofa = 5, 3, 3
            while times_unread_mail > 0 or times_unread_notify > 0 or times_sofa > 0:
                if times_unread_mail > 0:
                    len_mail = douban.answer_unread_mail()
                    logging.info('get_mail[%s]:%s', times_unread_mail, len_mail)
                    if len_mail == 0:
                        times_unread_mail = 0
                    else:
                        times_unread_mail = times_unread_mail - 1
  
                if times_unread_notify > 0:
                    len_notify = douban.answer_unread_notify()
                    logging.info('get_notify[%s]:%s', times_unread_notify, len_notify)
                    if len_notify == 0:
                        times_unread_notify = 0
                    else:
                        times_unread_notify = times_unread_notify - 1

                if len_mail > 0 or len_notify > 0 :
                    logging.info("mail:%s, notify:%s, sleep 60's", len_mail, len_notify)
                    time.sleep(60)

                if times_sofa > 0:
                    len_sofa = douban.sofa(4)
                    if len_sofa == 0:
                        times_sofa = 0
                    else:
                        times_sofa = times_sofa - 1
                    if len_sofa > 0:
                        logging.info("get_sofa[%s]:times:%s, sleep 60's", times_sofa, len_sofa)
                        time.sleep(60)

                logging.info('---- while')

            logging.info("work finished, sleep 3*60's")

            tm = time.localtime()
            if tm.tm_hour >= 3 and tm.tm_hour < 5:
                #凌晨3点到4点， sleep 2.5 hours
                time.sleep(152*60)
            elif tm.tm_hour>=5 and tm.tm_hour <7:
                #凌晨5点到7点， sleep 30 mins
                time.sleep(30*60)
            else:
                #3 mins
                time.sleep(3*60)

            logging.info('==== work')
        except Exception as e:
            logging.error("daily work raise exception:%s, sleep 15*60's",traceback.format_exc())

            circle_times = circle_times + 1
            tt.join()

            time.sleep(15*60)
            douban = DoubanRobot(account_id, password, douban_id)
            tt = threading.Thread(target=monitor_work, args=(douban, circle_times))
            tt.start()


if __name__ == '__main__':
    log_dir = 'log/'
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(level=logging.INFO,
            format='[%(asctime)s %(name)-12s %(levelname)-s] %(message)s',
            datefmt='%m-%d %H:%M:%S',
            #filename=time.strftime('log/doubanrobot.log'),
            filemode='a')

    htimed = logging.handlers.TimedRotatingFileHandler("log/doubanrobot.log", 'D', 1, 0)
    htimed.suffix = "%Y%m%d-%H%M"
    htimed.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s %(name)-12s %(levelname)-s] %(message)s', datefmt='%m-%d %H:%M:%S')
    htimed.setFormatter(formatter)

    logging.getLogger('').addHandler(htimed)

    ##bind Port
    import socket

    Port = 8901
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # 绑定端口，端口占用表示程序正在运行
        sock.bind(('127.0.0.1', Port))
        sock.listen(5)
    except:
        logging.error('socket bind(%s) fail, analyze work already start!!', Port)
        os._exit(0)

    import sys
    if len(sys.argv) > 1 and sys.argv[1]=='run':
        work()
    else:
        work(hotReload=True)

