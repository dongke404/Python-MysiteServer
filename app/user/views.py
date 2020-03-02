

from . import user

@user.route("/user")
def userindex():
    return "这个是user首页"