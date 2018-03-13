# coding=utf-8

import json
import web
import logging
import logging.handlers
import os

urls = (
        '/order', 'order.order',
        '/payorder', 'order.payorder',
        '/phoneorder', 'phoneorder',
        '/login', 'query.login',
        )

py_conf = json.loads(open("../conf/config.backend.json").read())

'''
my_conn = web.database(dbn='mysql', host=py_conf["mysql"]["host"],
        port=py_conf["mysql"]["port"], user=py_conf["mysql"]["user"], pw=py_conf["mysql"]["pw"]
        , db=py_conf["mysql"]["db"])
'''

render = web.template.render('templates',)

class phoneorder:
    def GET(self):
        return render.phoneorder()

    def POST(self):
        input_data = web.input();
        print('phoneorder:', input_data)
        return render.phoneorder()


if __name__=='__main__':
    log_dir = py_conf['log']
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logging.basicConfig(level=logging.INFO,
            format='[%(asctime)s %(name)-12s %(levelname)-s] %(message)s',
            datefmt='%m-%d %H:%M:%S',
            #filename=time.strftime(log_dir+'/pyweb.log'),
            filemode='a')

    htimed = logging.handlers.TimedRotatingFileHandler(log_dir+"/pyweb.log", 'D', 1, 0)
    htimed.suffix = "%Y%m%d-%H%M"
    htimed.setLevel(logging.INFO)
    formatter = logging.Formatter('[%(asctime)s %(name)-12s %(levelname)-s] %(message)s', datefmt='%m-%d %H:%M:%S')
    htimed.setFormatter(formatter)

    logging.getLogger('').addHandler(htimed)

    app = web.application(urls, globals())
    app.run()

