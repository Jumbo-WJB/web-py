#coding=utf8

import sys
import json
import logging
import logging.handlers as handlers
import TexasPub

#此文件主要用来做配置，就不另写配置xml/ini等

#DB配置
DB_HOST = "10.8.8.96"
DB_PORT = 3306
DB_USER = "mdzpk_rw"
DB_PASS = "GtXQpjifDykLGzDtypJH"
DB_DATABASE = "mdzpkweb"
DB_ENABLE = True

#redis配置
REDIS_HOST ="10.8.8.112"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_SESSION_DB = 1

#游戏服务器配置
GAME_HOST = "42.62.40.186"
GAME_PORT = 8888

#日志服务器配置
LOG_SVR_HOST = '127.0.0.1'
LOG_SVR_PORT = 20001

#JSS服务配置
JSS_HOST = "52.74.83.194:8000"
JSS_HOST_ANDROID = "52.74.83.194:8000"
JSS_HOST_IOS = "52.74.83.194:8000"
JSS_BUYVIP_URL = "/jss/mbuserbuyvip?userId=%s&viptype=%d"
JSS_ADDSCORE_URL = "/jss/mbuseraddscore?userId=%s&type=%d&score=%d"

#DBService服务
DBSERVER_HOST = "10.8.8.190"
DBSERVER_PORT = 6000

#渠道配置
CHANNEL_DEMO = "demo"

PROMPT_INFO = "{\"title\":\"提示信息\", \"prompt\":\"系统正在维护，请您稍候登录\", \"btn\":\"退出\", \"action\":\"exit\"}"

#定义平台ID
PLATFORMID_MACHINEID	= 0
PLATFORMID_TENCENTWEIBO	= 1
PLATFORMID_TEST			= 10
PLATFORMID_DEMO			= 11

#支付宝通知URL
ALIPAY_NOTIFY_URL = ""

#360支付平台URL通知
ICHANNEL360_NOTIFY_URL = ""

#爱贝通知URL
IAPPPAY_NOTIFY_URL = ""

#游戏服务器的一些配置，web从那边读取
SERVER_CONF_FILE = "/etc/aow/server.conf"
#动态更新的配置文件位置
UPDATE_CONF_JSONFILE = "./dyncfg.json"

#设备类型
DEVICE_TYPE_UNKNOWN = 0
DEVICE_TYPE_ANDROID = 1
DEVICE_TYPE_IPHONE = 2
DEVICE_TYPE_IPAD = 3
DEVICE_TYPE_PC = 4

#充值相关
SHOP_FIRSTCHARGE_ENABLE = False

g_dictGameSvr = {}
g_dictConnectSvr = {}
#加载游戏服务器配置，主要是解析出各个游戏服务器地址
def LoadServerConf():
    global g_dictGameSvr
    global g_dictConnectSvr

    try:
        print("read server conf:" + SERVER_CONF_FILE)
        file = open(SERVER_CONF_FILE, "r")
        strServerConf = file.read()
        file.close()

        dictConf = json.loads(strServerConf)
        g_dictGameSvr = dictConf["game_svr"]
        g_dictConnectSvr = dictConf["connect_svr"]

        return True
    except Exception, e:
        print("LoadServerConf exception:" + str(sys.exc_info()[0]) + "," + str(sys.exc_info()[1]))
        return False

#用户名分配算法
def GetUserIndex(strUserID):
    nLen = len(strUserID)
    nIndex = (ord(strUserID[nLen-1]) << 24) | (ord(strUserID[nLen-2]) << 16) | (ord(strUserID[nLen-3]) << 8) | (ord(strUserID[nLen-4]))
    return nIndex

#根据用户ID确定其在哪台游戏服务器
def GetGameServerFromUserID(strUserID):
    global g_dictGameSvr

    if len(g_dictGameSvr) == 0:
        return None
    nIndex = GetUserIndex(strUserID) % len(g_dictGameSvr)
    dictSvr = g_dictGameSvr[nIndex]["mgmt"]
    print("user:" + strUserID + ",host:" + dictSvr["host"] + ",port:" + str(dictSvr["port"]))
    return (dictSvr["host"], dictSvr["port"])

#根据用户ID确定其在哪台连接服务器
def GetConnectServerFromUserID(strUserID):
    global g_dictConnectSvr

    if len(g_dictConnectSvr) == 0:
        return None
    dictSvr = g_dictConnectSvr[0]["mgmt"]
    return (dictSvr["host"], dictSvr["port"])

g_strUptCfg = ""
#加载需要更新的json文件
def LoadUpdateConf():
    global g_strUptCfg
    try:
        print("read update conf:" + UPDATE_CONF_JSONFILE)
        file = open(UPDATE_CONF_JSONFILE, "r")
        g_strUptCfg = file.read()
        file.close()

        return True
    except Exception, e:
        print("LoadUpdateConf exception:" + str(sys.exc_info()[0]) + "," + str(sys.exc_info()[1]))
        return False

#根据版本和用户本地时间取更新配置文件
def GetUpdateConfigJson(nTimeCfg, nVer):
    global g_strUptCfg
    if len(g_strUptCfg) == 0:
        return "{\"code\":-1}"

    return g_strUptCfg

#取得日志处理器
def GetSocketLogger(name):
    return getSocketLogger(name, logging.DEBUG, host = LOG_SVR_HOST, port = LOG_SVR_PORT, memoryCapacity = 0)

def getSocketLogger(name, level, host, port, memoryCapacity):
    target = handlers.SocketHandler(host, port)
    if memoryCapacity > 0:

        hdlr = handlers.MemoryHandler(memoryCapacity,
                                       logging.ERROR, # 此参数是指遇到此级别时，马上flush
                                       target)
    else:
        hdlr = target

    hdlr.setLevel(level)
    logger = logging.getLogger(name)
    logger.addHandler(hdlr)
    logger.setLevel(level)
    return logger

#定义某个版本需要的操作类型
VERSION_NONE = 0
VERSION_UPDATE = 11
VERSION_UPDATE_FORBIDDEN = 12
VERSION_PROMPT = 13
VERSION_PROMPT_FORBIDDEN = 14
#分渠道更新，指定不同更新URL
def ConfigFromChannel(strChannel, nDeviceType, nVer):
    # print("channel:" + strChannel + ",device:" + str(nDeviceType) + ",ver:" + str(nVer))

    strPrompt220 = "2.2.0版更新内容：\n1、全新的保险玩法；\n2、创新的任务活动模式；\n3、优化游戏进程。"
    strPromptParamida = ""

    #此处配置了每个渠道的最小允许版本、更新URL地址、提示信息、提示类型，注意苹果官方渠道App Store现在是单独处理的
    dictChannel = {
    #苹果渠道
    "App Store":{"minver-iPhone":"1.0.0", "url-iPhone":"itms-apps://itunes.apple.com/cn/app/de-zhou-ke/id633399763?mt=8", "prompt-iPhone":strPrompt220,  "type-iPhone":VERSION_UPDATE,
    "minver-iPad":"1.0.0", "url-iPad":"https://itunes.apple.com/cn/app/lian-zhong-de-zhou-pu-ke/id491856427?mt=8", "prompt-iPad":strPrompt220,  "type-iPad":VERSION_UPDATE},#App Store
    
    #国内渠道
    "thran":{"minver":"1.0.0", "url":"http://pw.lianzhong.com/Mobile/Download.html", "prompt":strPrompt220,  "type":VERSION_UPDATE},#联众移动中心
    
    #海外印尼渠道
    "paramida-gp":{"minver":"1.0.0", "url":"http://gp", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-04":{"minver":"1.0.0", "url":"http://04", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-06":{"minver":"1.0.0", "url":"http://06", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-09":{"minver":"1.0.0", "url":"http://09", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-10":{"minver":"1.0.0", "url":"http://10", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-11":{"minver":"1.0.0", "url":"http://11", "prompt":strPromptParamida, "type":VERSION_UPDATE},
    "paramida-12":{"minver":"1.0.0", "url":"http://12", "prompt":strPromptParamida, "type":VERSION_UPDATE}
    }

    strUrl = None
    strPrompt = ""
    nType = VERSION_NONE
    if dictChannel.has_key(strChannel):#根据渠道判断是否需要更新
        dChannelInfo = dictChannel[strChannel]
        if strChannel == "App Store":#AppStore渠道要单独处理
            if nDeviceType == DEVICE_TYPE_IPHONE:
                if nVer < TexasPub.Version2Int(dChannelInfo["minver-iPhone"]):#需要更新
                    strUrl = dChannelInfo["url-iPhone"]
                    strPrompt = dChannelInfo["prompt-iPhone"]
                    nType = dChannelInfo["type-iPhone"]
            elif nDeviceType == DEVICE_TYPE_IPAD:
                if nVer < TexasPub.Version2Int(dChannelInfo["minver-iPad"]):#需要更新
                    strUrl = dChannelInfo["url-iPad"]
                    strPrompt = dChannelInfo["prompt-iPad"]
                    nType = dChannelInfo["type-iPad"]
        else:
            if nVer < TexasPub.Version2Int(dChannelInfo["minver"]):#需要更新
                strUrl = dChannelInfo["url"]
                strPrompt = dChannelInfo["prompt"]
                nType = dChannelInfo["type"]
    if nType == VERSION_NONE:#找不到对应渠道的信息或者版本已不需要做任何处理
        return None

    UPDATE_INFO_FMT = "{\"prompt\":\"%s\", \"url\":\"%s\"}"
    strPromptJson = UPDATE_INFO_FMT % (strPrompt, strUrl)
    return {"type":nType, "promptjson":strPromptJson}

def GetJssHost(nDevieType):
    if nDeviceType == DEVICE_TYPE_IPHONE or nDeviceType == DEVICE_TYPE_IPAD:
        return JSS_HOST_IOS
    else:
        return JSS_HOST_ANDROID

#取得支付渠道类型，可用与操作 0：没有支付；1：官方支付；2：本地支付；3：官方和本地支付
def GetPayChannel(strChannel, strMarket):
    if strChannel == "paramida":
        if strMarket == "paramida-gp":
            return 3
        else:
            return 2
    else:
        return 0

#import时先加载一些配置
# LoadServerConf()
LoadUpdateConf()

if __name__ == "__main__":
    print(GetUserIndex("s074798b778141cf53fd9e386a5a8a36"))
    # GetSocketLogger("detail")
    # pairSvr = GetGameServerFromUserID("")
    # if pairSvr != None:
    #     print(pairSvr[0])
    #     print(pairSvr[1])
