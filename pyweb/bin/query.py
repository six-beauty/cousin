# coding=utf-8

import json
import web
import logging

py_conf = json.loads(open("../conf/config.backend.json").read())

'''
my_conn = web.database(dbn='mysql', host=py_conf["mysql"]["host"],
        port=py_conf["mysql"]["port"], user=py_conf["mysql"]["user"], pw=py_conf["mysql"]["pw"]
        , db=py_conf["mysql"]["db"])
'''

render = web.template.render('templates',)

class login:
    def GET(self):
        return render.login('')

    def POST(self):
        input_data = web.input(admin="", passwd= "");
        if input_data.admin == "" or input_data.passwd == "":
            return render.login("(非法账号或密码)")

        logging.info('input admin:%s, passwd:%s', input_data.admin, input_data.passwd)

        return web.redirect('/order');
