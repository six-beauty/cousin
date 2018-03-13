# coding=utf-8

import json
import web
import util
import urllib.parse
import traceback
import logging
import re
import MySQLdb
import smtplib  
import email.mime.multipart  
import email.mime.text  
import email.utils

from_addr = 'sanyue9394@126.com'
from_passwd = 'sanyue214008'
to_addr = ['939445950@qq.com']

py_conf = json.loads(open("../conf/config.backend.json").read())
imgs_pay = util.load_pay_imgs('./static/imgs_pay')
my_conn = web.database(dbn='mysql', host=py_conf["mysql"]["host"],
        port=py_conf["mysql"]["port"], user=py_conf["mysql"]["user"], pw=py_conf["mysql"]["pw"]
        , db=py_conf["mysql"]["db"])
'''
rds_conn = redis.Redis(host=py_conf["redis"]["host"], port=py_conf["redis"]["port"], password=py_conf["redis"]["pw"])
'''

render = web.template.render('templates',)
re_phone=re.compile('^0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}')

class order:
    def __init__(self):
        self.smtp=smtplib.SMTP()  
        self.smtp.connect(py_conf['mail']['from_svr'], py_conf['mail']['svr_port'])  
        self.smtp.login(py_conf['mail']['from_addr'], py_conf['mail']['from_passwd'])  

    def send_mail(self, name, phone, wx, male, child, ly_type, room, order_date, retry_time=3):
        if retry_time <= 0:
            logging.err('send_mail fail, phone:%s order_date:%s', phone, order_date)
            return
        try:
            content="""
    -----------------begin---------------------------
    名字:{0}    \t,手机:{1}    \t,微信:{2}    \t,预约时间:{3}    \t,
    -----------------end----------------------------------------------------
    成人:{4}人    \t,儿童:{5}人    \t,预约类型:{6}日游    \t,预约房间:{7}房    \t,
    -----------------end----------------------------------------------------
    """.format(name, phone, wx, order_date, male, child, ly_type, room)
            msg=email.mime.multipart.MIMEMultipart()  
            msg['From']=py_conf['mail']['from_addr']
            msg['To']=email.utils.COMMASPACE.join(py_conf['mail']['to_addr'])
            msg['Subject']='农庄预约订单'  
            msg['Date'] = email.utils.formatdate(localtime=True)
            text=email.mime.text.MIMEText(content, 'plain', 'utf-8')  
            msg.attach(text)  

            self.smtp.sendmail(from_addr, to_addr, msg.as_string())  
        except:
            logging.err('send_mail fail, %s', traceback.format_exc())
            self.smtp=smtplib.SMTP()  
            self.smtp.connect(py_conf['mail']['from_svr'], py_conf['mail']['svr_port'])  
            self.smtp.login(py_conf['mail']['from_addr'], py_conf['mail']['from_passwd'])  

            name = name.decode('utf-8')
            phone = phone.decode('utf-8')
            wx = wx.decode('utf-8')
            self.send_mail(name, phone, wx, male, child, ly_type, room, order_date, retry_time-1)

    def GET(self):
        return render.order('', '')

    def update_sql_order(self, name, phone, wx, male, child, ly_type, room, order_date):
        phone = MySQLdb.escape_string(phone).decode('utf-8')[:12]
        name = MySQLdb.escape_string(name).decode('utf-8')[:32]
        wx  = MySQLdb.escape_string(wx).decode('utf-8')[:64]
        order_date = order_date[:10]

        sql = "insert into eastward_order(phone, name, wx, male, child, ly_type, room, order_date) values('{0}', '{1}', '{2}', {3}, {4}, {5}, {6}, '{7}');".format(phone, name, wx, male, child, ly_type, room, order_date)
        res = my_conn.query(sql)


    def POST(self):
        argv = web.input(name="", phone="", wx="", male=2, child=1, ly_type=2, room=1, order_date='')
        try:
            name, phone, wx = argv['name'], argv['phone'], argv['wx']
            order_date = argv['order_date']
        except:
            logging.error('order parse detail err:%s', traceback.format_exc())
            return render.order('(请输入正确的预定信息)', '')

        phonematch=re_phone.match(phone)
        if phonematch:
            phone = phonematch.group()
        else:
            logging.error('order phone err:%s', phone)
            return render.order('', '(请输出正确的手机号)')

        try:
            male = int(argv['male'])
            child = int(argv['child'])
            ly_type = int(argv['ly_type'])
            room = int(argv['room'])
        except:
            logging.error('order parse err:%s', traceback.format_exc())
            male, child, ly_type, room = 2, 1, 2, 1

        self.update_sql_order(name, phone, wx, male, child, ly_type, room, order_date)

        self.send_mail(name, phone, wx, male, child, ly_type, room, order_date)

        logging.info('order:name:%s, phone:%s, 微信:%s, %d成人%d儿童, %d日游, %d(房), 预定日期:%s', name, phone, wx, male, child, ly_type, room, order_date)

        pay_arg = urllib.parse.urlencode({'male':male, 'child':child, 'ly_type':ly_type, 'room':room})
        return web.redirect('/payorder?'+pay_arg);

class payorder:
    def GET(self):
        argv = web.input(male=2, child=1, ly_type=2, room=1);
        try:
            male = int(argv['male'])
            child = int(argv['child'])
            ly_type = int(argv['ly_type'])
            room = int(argv['room'])
        except:
            logging.error('payorder parse err:%s', traceback.format_exc())
            male, child, ly_type, room = 2, 1, 2, 1
        imgs = '%02d%02d%02d%02d'%(male, child, ly_type, room)
        #没有对应支付
        head2 = util.crt_paytitle(male, child, ly_type, room)
        if imgs not in imgs_pay:
            imgs = 'default'
            pay = util.cal_payment(male, child, ly_type, room)
            head2 = head2 + ', 需支付'+ str(pay) +'元'

        pay_argv={'imgs':imgs, 'head2':head2}
        return render.show(pay_argv)

    def POST(self):
        return self.GET()
