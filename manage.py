# -*- coding: UTF-8 -*-
#启动和管理项目
from app import create_app
from app.config import MONGODBHOST
from flask_pymongo import  PyMongo
from gevent.pywsgi import WSGIServer

app = create_app()
mongo=PyMongo(app, uri=MONGODBHOST)


if __name__ == '__main__':
    server = WSGIServer(("127.0.0.1", 5000), app)
    server.serve_forever()



