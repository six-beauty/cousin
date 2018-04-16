# coding=utf-8
import flask
import redis
import gevent.wsgi

web_host='0.0.0.0'
web_port=9903

app = flask.Flask(__name__)
rds = redis.StrictRedis(host='127.0.0.1',port=52021,password='sany')

@app.route('/')
@app.route('/index')
def index():
    captcha_id = rds.get('captcha') or b''
    return flask.render_template("homepage.html", captcha_id=captcha_id.decode('utf-8'))

@app.route('/captcha')
def captcha():
    search = flask.request.args.get("search")
    rds.publish('vcode', search)

    return flask.redirect(flask.url_for('index'))

http_server = gevent.wsgi.WSGIServer((web_host, web_port), app)

if __name__ == '__main__':
    http_server.serve_forever()

