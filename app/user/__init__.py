#正对用户业务逻辑处理的初始化
from flask import Blueprint
user=Blueprint("user",__name__)

from . import views

