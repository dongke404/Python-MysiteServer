#主业务逻辑中的视图和路由的定义
from flask import request,jsonify
#导入蓝图程序，用于构建路由
from . import main
#导入db，用于操作数据库
from .. import db
from manage import mongo
#导入实体类，用于操作数据库
from ..models import *
import json
import datetime
import os
import re
import html2text
import redis
from flask_cors import CORS
from app.config import REDISHOST
CORS(main, supports_credentials=True)

# 生产环境
# baseurl="/api"
# picBasedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

#开发环境
baseurl=""
picBasedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# 数据库重载
# @main.route(baseurl+'/creatdb')
# def creatdb():
#     db.drop_all()
#     db.create_all()
#     return "ok"

#注册
@main.route(baseurl+'/reg',methods=["GET","POST"])
def reg():
    #动态用户名验证
    if request.method == "GET":
        loginname = request.args.get("loginname")
        #检验重复
        checkRe= db.session.query(User).filter((User.loginname == loginname)).first()
        if checkRe:
            return json.dumps({
                "status": 1,
                "msg": "此用户已存在"
            })
        else:
            return json.dumps({
                "status": 0,
                "msg": "用户名可用"
            })

    else:
        try:

            data=request.get_json(silent=True)
            loginname= data.get("loginname")
            password=data.get("password")
            email=data.get("email")
            nickname=data.get("nickname")
            checkRename = db.session.query(User).filter((User.loginname == loginname)).first()
            checkReemail=db.session.query(User).filter((User.email == email)).first()
            if checkRename or checkReemail:
                return json.dumps(
                    {
                        "status": 1,
                        "msg": "用户名或邮箱地址已存在"
                    }
                )

            else:
                userinfo = User()
                userinfo.loginname=loginname
                userinfo.password = password
                userinfo.email=email
                userinfo.nickname=nickname

                db.session.add(userinfo)
                Userinfo = db.session.query(User).filter(User.loginname == loginname).first()
                id = Userinfo.id
                db.session.commit()
                return jsonify ({
                        "status": 0,
                        "data": {
                            "id":id,
                            "loginname": loginname,
                            "nickname": nickname,
                            "email": email,
                                }
                })
        except Exception as e:
            print(e)
            return json.dumps(
                {
                    "status": 1,
                    "msg": "未知错误"
                }
            )

#登录验证
@main.route(baseurl+'/login',methods=["POST"])
def login():
    data = request.get_json(silent=True)
    loginname = data.get("loginname")
    password = data.get("password")
    remember=data.get("remember")
    checkUser=db.session.query(User).filter(User.loginname==loginname,User.password==password ).first()
    if checkUser:
        id=checkUser.id
        loginname=checkUser.loginname
        email=checkUser.email
        nickname=checkUser.nickname
        head_link=checkUser.head_link
        return json.dumps({
            "status": 0,
            "data": {
                "id":id,
                "loginname": loginname,
                "nickname": nickname,
                "email": email,
                "head_link":head_link
            }
        })
    else:
        return  json.dumps({
            "status": 1,
            "msg":"用户名密码错误"

        })




#帖子上传
@main.route(baseurl+'/uploadtopic',methods=["POST"])
def uploadtopic():
    try:
        data = request.get_json(silent=True)
        user_id=data.get("user_id")
        title = data.get("title")
        content=data.get("content")
        read_num=0
        #正则取图片链接
        regex= re.compile(r'<img src="(.*?)"', re.S)
        img_list = regex.findall(content)

        topic = Topic()
        topic.user_id = user_id
        topic.title=title
        topic.pub_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        topic.content = content
        topic.images=str(img_list)
        topic.read_num = 0
        db.session.add(topic)
        db.session.commit()

        return jsonify({
            "status":0,
        })
    except Exception as e:
        return jsonify({
            "status":1,
        })


#主页帖子内容
@main.route(baseurl+'/reqtopic')
def reqtopic():
    data= request.args
    page=int(data.get("page")) #传送第页内容
    pageNum=int(data.get("pageNum")) #每页显示的数量
    # print(page,pageNum)
    total =db.session.query(Topic).count()
    # print(total)
    topics=db.session.query(Topic).order_by(Topic.id.desc()).slice((page-1)*pageNum,page*pageNum).all() # 按最新排序

    #提取文本
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    data=[]
    for topic in topics:
        obj={}
        obj["id"]=topic.id
        obj["title"] = topic.title[:30] #限制显示字数
        obj["read_num"] = topic.read_num
        content=h.handle(topic.content)[:100] #限制显示字数
        obj["content"] = content
        obj["pub_date"]=str(topic.pub_date)
        #user信息
        obj["user"]={}
        obj["user"]["id"] = topic.user.id
        obj["user"]["nickname"] = topic.user.nickname
        obj["user"]["head_link"] = topic.user.head_link
        obj["user"]["email"] = topic.user.email
        images=eval(topic.images)
        obj["images"] =images
        #评论数
        comments = db.session.query(Comment).filter(Comment.topic_id==topic.id).all()
        commentTotal=0
        replysTotal=0
        for comment in comments:
            commentTotal+=1
            replys=db.session.query(Reply).filter(Reply.comment_id==comment.id).all()
            replysNum=len(replys)
            replysTotal+=replysNum
        obj["replytotal"]=commentTotal+replysTotal
        data.append(obj)
        # print(data)

    return jsonify({
        "status":0,
        "total":int(total),
        "data":data,
    })

#帖子内容
@main.route(baseurl+'/reqpostdetail')
def reqPostDetail():
    topicId = request.args.get("id")
    topic = db.session.query(Topic).filter(Topic.id ==topicId ).first()
    #浏览量+1
    topic.read_num+=1

    theme={}
    theme["title"] = topic.title
    theme["content"] = topic.content
    theme["pub_date"] = str(topic.pub_date)
    theme["user"] = topic.user.nickname
    theme["head_link"]=topic.user.head_link

    commentlist= db.session.query(Comment).filter(Comment.topic_id ==topicId ).all()
    comments=[]
    for commentobj in commentlist:
        comment={}
        comment["id"]=commentobj.id
        comment["comment"] = commentobj.comment
        comment["date"] = str(commentobj.comment_time)


        # 评论里添加用户信息
        userobj=commentobj.user
        comment["user"]={}
        user =comment["user"]
        user["id"]= userobj.id
        user["nickname"] = userobj.nickname
        user["head_link"] = userobj.head_link
        comments.append(comment)

        #评论里添加回复信息
        replysobjList=commentobj.replys.all()
        comment["replys"] = []
        replyList=comment["replys"]
        for replyobj in replysobjList:
            reply={}
            reply["id"]=replyobj.id
            reply["author"]=replyobj.user.nickname
            reply["author_id"]=replyobj.user.id
            reply["authorHead"]=replyobj.user.head_link
            reply["to_id"] = replyobj.to_uid
            toUserobj=db.session.query(User).filter(User.id == replyobj.to_uid).first()
            reply["to_nickname"]=toUserobj.nickname
            reply["reply_content"] = replyobj.reply_content
            reply["datatime"] = str(replyobj.reply_time)
            replyList.append(reply)
    return jsonify({
        "status": 0,
        "theme": theme,
        "comments":comments
    })

#图片上传
@main.route(baseurl+'/img/upload',methods=["POST"])
def imgupload():
    img = request.files['upfile']
    path = picBasedir+'/static/images/uploadImg/'
    filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + (img.filename[-8:])#图片防止重复
    file_path = path + filename
    img.save(file_path)
    #返回预览图
    return json.dumps({'errno':0, 'data': ['/static/images/uploadImg/'+filename]})

#头像上传
@main.route(baseurl+'/uploadhead',methods=["POST"])
def uploadhead():
    try:
        img=request.files["avatar"]
        id=request.form.get("id")
        savepath=picBasedir+'/static/images/uploadHead/'
        filename = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f") + (img.filename[-8:])  # 图片防止重复
        file_path = savepath + filename
        img.save(file_path)
        user=db.session.query(User).filter(User.id == id).first()
        getimgpath='/static/images/uploadHead/'+filename
        user.head_link=getimgpath
        return jsonify(
            {'status': 0,
             'data': [getimgpath]}
        )
    except Exception as e:
        print(e)
        return jsonify(
            {'status': 0,
             'msg':"请求失败"}
        )


#评论存储
@main.route(baseurl+'/upComment',methods=["POST"])
def upComment():
    data = request.get_json(silent=True)
    user_id = data.get("user_id")
    topic_id = data.get("topic_id")
    comment = data.get("comment")
    commentobj=Comment()
    commentobj.user_id=user_id
    commentobj.topic_id=topic_id
    commentobj.comment=comment
    commentobj.comment_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    db.session.add(commentobj)
    db.session.commit()
    return jsonify(
        {'status': 0 }
                   )

#回复处理
@main.route(baseurl+'/pbReply',methods=["POST"])
def pbReply():
    data = request.get_json(silent=True)
    from_uid=data.get("from_uid")
    to_uid=data.get("to_uid")
    comment_id=data.get("comment_id")
    reply_content=data.get("reply_content")
    replyObj=Reply()
    replyObj.from_uid=from_uid
    replyObj.to_uid =to_uid
    replyObj.comment_id =comment_id
    replyObj.reply_content=reply_content
    replyObj.reply_time=datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    db.session.add(replyObj)
    db.session.commit()
    return jsonify(
        {'status': 0}
    )


#获取头像
@main.route(baseurl+'/reqhead')
def reqhead():
    try:
        id = request.args.get("id")
        user = db.session.query(User).filter(User.id == id).first()
        id = user.id
        loginname = user.loginname
        email = user.email
        nickname = user.nickname
        head_link = user.head_link
        return json.dumps({
            "status": 0,
            "data": {
                "id": id,
                "loginname": loginname,
                "nickname": nickname,
                "email": email,
                "head_link": head_link
            }
        })
    except Exception as e:
        print(e)
        return jsonify(
            {'status': 1,
             'msg':"更新头像失败" }
        )

#获取新闻内容
@main.route(baseurl+'/reqNews')
def reqNews():
    r = redis.StrictRedis(host=REDISHOST, port=6379, db=0,password='Python19921112')
    data={}
    #优化 可封装函数
    #获取横幅消息
    data["banner"] = []
    for key in r.keys("banner*"):
        banner = {}
        for i,name in enumerate(["title","imgUrl","newsUrl"]):
            value=r.lindex(key,i)
            banner[name]=value.decode()
        data["banner"].append(banner)

    #获取侧边栏信息
    data["sideimg"] = []
    for key1 in r.keys("sideimg*"):

        sideimg = {}
        for i, name in enumerate(['sidetitle', 'sideImgUrl', 'sideUrl']):
            value = r.lindex(key1, i)
            sideimg[name] = value.decode()
        data["sideimg"].append(sideimg)

    # 获取热点信息
    data["hotevent"] = []
    for key2 in sorted(r.keys("Hotevent*"),key=lambda x:int(x.decode().split('Hotevent')[1])):
        hotevent = {}
        for i, name in enumerate(['title', 'link']):  # 0 :title  1 imgUrl  2 url

            value = r.lindex(key2, i)

            hotevent[name] = value.decode()
        data["hotevent"].append(hotevent)

    # print(data)
    return jsonify(
            {'status': 0,
             "data":data,
             }
        )

#获取小说列表

@main.route(baseurl+'/story')
def reqStory():
    params = request.args
    # params = request.args
    stype=params.get("stype")
    if   stype=="全部小说" or (not stype)  :
        bookList= db.session.query(Story).all()
    else:
        bookList=db.session.query(Story).filter(Story.type == stype).all()
    data=[]

    for bookobj in  bookList:
        book={}
        book["id"]=bookobj.id
        book["name"] = bookobj.name
        book["author"] = bookobj.author
        book["type"] = bookobj.type

        book["introduction"] = bookobj.introduction[0:50]

        book["images"] = bookobj.images
        data.append(book)
    return jsonify(
            {'status': 0,
             "data":data,
             }
        )

@main.route(baseurl+'/storyTypeList')
def reqStoryTypeList():
    typelist=db.session.query(Story.type).distinct().all()
    data=[]
    for i in typelist:
        data.append(i[0])
    return jsonify(
            {
             'status': 0,
             "data":data
             }
        )



#获取小说目录
@main.route(baseurl+'/storydirs')
def reqStoryDirs():
    params = request.args
    id=params.get("storyid")
    storyobj=db.session.query(Story).filter(Story.id == id).first()
    data = {}
    data["id"] = storyobj.id
    data["name"] = storyobj.name
    data["author"] = storyobj.author
    data["type"] = storyobj.type
    data["introduction"] = storyobj.introduction
    storyContents=storyobj.StoryContents.all()
    dirs=[]
    for storyContent in storyContents:
        _ = {}
        _["id"]=storyContent.id
        _["dir"]=storyContent.story_dir
        _["path"]=storyContent.content_path
        dirs.append(_)
    data["dirs"] =dirs
    return jsonify(
            {'status': 0,
             "data":data
             }
        )

#获取小说内容
storyBasedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
@main.route(baseurl+'/storyContent')
def reqStoryContent():
    # params = request.get_json(silent=True)
    params = request.args
    story_id=params.get("storyid")
    path=params.get("path")
    storyContentobj=db.session.query(StoryContent).filter(StoryContent.content_path == path,StoryContent.story_id==story_id).first()
    storytext=storyContentobj.dir_flag
    storyobj=storyContentobj.Story
    with open(storyBasedir+"/qxs5200_SimpleSpider/storys/{}/{}.txt".format(storyobj.name,storytext),encoding="utf-8") as f:
        text=f.read()
    data={}
    data["type"]=storyobj.type
    data["dir"] =storyContentobj.story_dir
    data["name"] =storyobj.name
    data["storyid"] = storyobj.id
    data["text"]=text
    return jsonify(
            {
                'status': 0,
                "data":data
             }
        )

#获取下一页
@main.route(baseurl+'/storyNextPage')
def reqStoryNextPage():
    # params = request.get_json(silent=True)
    params = request.args
    story_id=params.get("storyid")
    path=params.get("path")
    storyContentobj=db.session.query(StoryContent).filter(StoryContent.content_path == path,StoryContent.story_id==story_id).first()
    nextdir_flag=storyContentobj.dir_flag+1
    nextstoryContentobj=db.session.query(StoryContent).filter(StoryContent.dir_flag == nextdir_flag,StoryContent.story_id==story_id).first()
    if not nextstoryContentobj:
        return jsonify(
            {
                'status': 1,
                "msg":"没有更多了"
            }
        )
    storytext=nextstoryContentobj.dir_flag
    storyobj=nextstoryContentobj.Story
    with open(storyBasedir+"/qxs5200_SimpleSpider/storys/{}/{}.txt".format(storyobj.name,storytext),encoding="utf-8") as f:
        text=f.read()
    data={}
    data["type"]=storyobj.type
    data["dir"] =nextstoryContentobj.story_dir
    data["name"] =storyobj.name
    data["storyid"] = storyobj.id
    data["text"]=text
    data["path"] = nextstoryContentobj.content_path
    print(data["path"])
    return jsonify(
            {
                'status': 0,
                "data":data
             }
        )


#获取分类列表
@main.route(baseurl+'/imagesTypes')
def reqImagesTypes():
    typeList=db.session.query(ImageType).all()
    data=[]
    for typeobj in typeList:
        imagetype={}
        imagetype["id"]=typeobj.id
        imagetype["type"] = typeobj.type
        data.append(imagetype)
    return jsonify(
        {
            'status': 0,
            'data':data
        }
    )


#获取图片内容
@main.route(baseurl+'/imagesInfo')
def reqImagesInfo():
    params = request.args
    type_id = params.get("typeId")
    curPage=params.get("curPage")
    print(type_id,curPage)
    typeobj=db.session.query(ImageType).filter(ImageType.id==type_id).first()
    images=typeobj.images.limit(50).offset((int(curPage) - 1) * 50).all()
    if images:
        data=[]
        for imageobj in images:
            image={}
            image["id"]=imageobj.id
            image["describe"] = imageobj.describe
            image["imageSize"] = imageobj.imageSize
            image["imageUrl"] = imageobj.imageUrl

            data.append(image)
        return jsonify(
            {
                'status': 0,
                'data':data
            }
        )
    return jsonify(
        {
            'status':1,
            'msg': "已经没有更多了"
        }
    )



@main.route(baseurl+'/reqMovies')
def reqMovies():
    set=mongo.db.movieInfo
    data=[]
    for x in set.find({},{ "_id": 0,"introduce":1,'subject.id':1,'subject.actors':1,'subject.rate':1,'subject.duration':1,'subject.types':1,'subject.title':1,'subject.region':1,'subject.short_comment.content':1}):
        name=x["subject"]["title"]
        name=name.split()[0]
        x["name"]=name
        data.append(x)
    return jsonify(
        {
            'status':0,
            'data':data
        }
    )


# @main.route(baseurl+'/test/<string:age>')
# def test(age):
#     mongo.db.movie.insert({'age': age})
#     return "ok"
