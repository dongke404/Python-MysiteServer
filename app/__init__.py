# coding=UTF-8
#对整个应用做初始化
#主要工作
# 构建Flasks应用和各种配置
# 构建sqlalcemy应用


from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql
import  threading
from app.config import MYSQLHOST
from app.spiderTools.getNews import getNews
pymysql.install_as_MySQLdb()
db=SQLAlchemy()

#获取新闻数据存入redis
getNews= getNews()
t1=threading.Thread(target=getNews.getsideimg,daemon=True)
t2=threading.Thread(target=getNews.getbanner,daemon=True)
t3=threading.Thread(target=getNews.getHotevent,daemon=True)
t1.start()
t2.start()
t3.start()

def create_app():
    app=Flask(__name__)
    #配置启动模式为调试模式
    app.config["DEBUG"]=False
    #配置数据库连接
    app.config['SQLALCHEMY_DATABASE_URI'] = MYSQLHOST
    #配置数据库自动提交
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
    # session配置key
    app.config["SECRET_KEY"] = "sessionkey"
    #数据库初始化
    db.init_app(app)
    # 将main蓝图程序与APP关联到一起

    from .main  import main as main_blueprint
    app.register_blueprint(main_blueprint)
    # 将user蓝图程序与APP关联到一起
    from .user import user as user_blueprint
    app.register_blueprint(user_blueprint)
    return app


