"""
Project     : 帝星传说
Filename    : robots.py
Author      : zhancc
CreateDate  : 2018/11/26 ‏‎11:53:47
ModifyDate  : 2018/12/13 ‏‎21:49:00
Description : 创建大量机器人玩家进入game服匹配，进入match服战斗

robots.ini
[server]
host=39.105.63.243
port=8250

[robots]
join_interval=1
robots_name_prefix=test
robots_index_min=1
robots_index_max=2
"""

import time
import random
import sys
import socket
import zlib
import struct
import threading
import multiprocessing
import configparser


SERVER = dict()
try:
    conf = configparser.ConfigParser()
    conf.read('robots.ini')
    SERVER['host'] = conf.get('server', 'host')
    SERVER['port'] = conf.getint('server', 'port')
    JOIN_INTERVAL = conf.getfloat('robots', 'join_interval')
    ROBOTS_NAME_PREFIX = conf.get('robots', 'robots_name_prefix')
    ROBOTS_INDEX_MIN = conf.getint('robots', 'robots_index_min')
    ROBOTS_INDEX_MAX = conf.getint('robots', 'robots_index_max')
except Exception as e:
    print('配置文件错误')
    print(e)
    sys.exit()


class Robots(object):
    def __init__(self, userName):
        self.cache = b''
        self.game_res_queue = multiprocessing.Queue()
        self.match_res_queue = multiprocessing.Queue()
        self.game_server = SERVER
        self.userName = userName
        self.game_session = self.__connect__(self.game_server)
        self.game_sessionId = ''
        self.pics = ['wendi', 'laohuangdi', 'nianqinghuangdi']
        self.playerName = ''
        self.playerId = 0
        self.certificate = ''
        self.worldId = ''
        self.match_server = {}
        self.match_session = None
        self.match_sessionId = ''
        self.match_response_queue_flag = True
        self.canDiscussAffairs = False
        self.game_functions = {
            'user@login': self.user_login_handler,
            'player@getRoleList': self.player_getRoleList_handler,
            'player@getRandomRoleNames': self.player_getRandomRoleNames_handler,
            'player@createRole': self.player_createRole_handler,
            'push@player': self.push_player_handler,
            'login@playerlogin': self.login_playerlogin_handler,
            'player@getRoleInfo2': self.player_getRoleInfo2_handler,
            'player@doMatch': self.player_doMatch_handler,
            'push@gameInfo': self.push_gameInfo_handler
        }
        self.match_functions = {
            'match@login': self.match_login_handler,
            'push@discussAffairs': self.match_push_discussAffairs_handler,
            'push@destroyCity': self.match_push_destroyCity_handler,
            'push@player': self.match_push_player_handler,
            'push@wEnd': self.match_push_wEnd_handler,
            'push@world': self.match_push_world_handler
        }

    def __connect__(self, server):
        """
        :function: 连接游戏服
        :return: socket对象
        """
        session = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            session.connect((server['host'], server['port']))
        except ConnectionRefusedError as e:
            self.logging('[error] {0}.{1} {2} {3}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                'socket.connect refused', e))
        return session

    @staticmethod
    def __package__(interface, parameters):
        """
        :function: 打包接口名称和参数
        :param interface: 接口名称，例如：player@login
        :param param: 接口参数，例如：playerId=12345
        :return: 返回byte类型数据
        """
        length = 32 + 4 + len(parameters)
        data = struct.pack(">i32si%ss" % (len(parameters)), length, interface, 1, parameters)
        return data

    def __send__(self, session, interface, parameters):
        """
        :function: 向接口发送打包好的数据
        :param session: socket对象
        :param interface: 接口名称
        :param parameter: 接口参数
        :return: 不返回数据
        """
        self.logging('[send] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
            sys._getframe().f_code.co_name, interface, parameters))
        data = self.__package__(interface.encode('utf-8'), parameters.encode('utf-8'))
        session.send(data)

    def send(self, *args, **kwargs):
        """
        :function: 接收参数，解析为socket对象，接口名和参数，是Robots.__send__()的上层封装
        :param args: socket对象，接口名称
        :param kwargs: 参数，可以为空
        :return: 不返回数据
        """
        parameter = ''
        for kw in kwargs:
            parameter += '{0}={1}&'.format(kw, kwargs[kw])
        parameter = parameter.strip('&')
        session, interface = args[0], args[1]
        self.__send__(session, interface, parameter)

    def __receive__(self, session, size):
        """
        :function: 接收socket数据
        :param session: socket对象
        :param size: 接收字节长度
        :return: 接收到的byte数据
        """
        if session:
            try:
                buff = session.recv(size)
            except Exception as e:
                self.logging('[error] {0}.{1} {2} {3}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                    'socket.recv error', e))
                return b''
        else:
            return b''
        return buff

    def receive(self, session):
        """
        :function: 接收socket数据
        :param session: game服或者match服的socket对象
        :return: 接口名称，状态码，消息数据
        """
        if not session:
            return None
        while len(self.cache) < 4:
            buff = self.__receive__(session, 4)
            if buff is None:
                return None
            self.cache += buff
        ret = struct.unpack(">i", self.cache[0:4])
        response_length = int(ret[0])
        while len(self.cache) < (4 + response_length):
            buff = self.__receive__(session, response_length)
            if buff is None:
                return None
            self.cache = self.cache + buff
        try:
            response = struct.unpack(">32si%ds" % (response_length - 4 - 32), self.cache[4:response_length + 4])
        except Exception as e:
            self.logging('[error] {0}.{1} {2} {3}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                'struct.unpack error', e))
            return None
        interface = response[0].decode().strip("\x00")
        state = response[1]
        message = zlib.decompress(response[2])
        message = message.decode('utf-8')
        message = message.replace('null', 'None').replace('false', 'False').replace('true', 'True')
        message = eval(message)
        self.cache = self.cache[response_length + 4:]
        return interface, state, message

    def game_response_gather(self):
        """
        :function: game服的接收消息队列
        :return: 不返回数据
        """
        while self.game_session:
            self.logging('[hint] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                sys._getframe().f_code.co_name, 'game session exist',self.game_session))
            res = self.receive(self.game_session)
            if res:
                self.game_res_queue.put(res)
                self.logging('[recv] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'game session', res))
            else:
                self.logging('[warning] {0}.{1} {2}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'receive None'))
                # 如果收不到消息，则睡眠
                time.sleep(3)
                self.system_heartbeat(self.game_session)

    def match_response_gather(self):
        """
        :function: match服的接收消息队列
        :return: 不返回数据
        """
        while self.match_response_queue_flag:
            res = self.receive(self.match_session)
            if res:
                self.match_res_queue.put(res)
                self.logging('[recv] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'match session', res))
            else:
                self.logging('[warning] {0}.{1} {2}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'receive None'))
                # 如果收不到消息，则睡眠
                time.sleep(3)

    def game_queue_manager(self):
        """
        :function: game服队列处理
        :return: 不返回数据
        """
        while self.game_session:
            self.logging('[hint] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                sys._getframe().f_code.co_name, 'game session exist', self.game_session))
            try:
                res = self.game_res_queue.get(block=True, timeout=5)
                self.logging('[queue] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'handling',res[0]))
                func = self.game_handler_selector(res[0])
                if func:
                    func(res[2])
            except Exception as e:
                self.logging('[warning] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'get None', e))
            # 如果拿不到消息则睡眠
            time.sleep(1)

    def match_queue_manager(self):
        """
        :function: match服队列处理
        :return: 不返回数据
        """
        while self.match_response_queue_flag:
            try:
                res = self.match_res_queue.get(block=True, timeout=5)
                self.logging('[queue] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'handling',res[0]))
                func = self.match_handler_selector(res[0])
                if func:
                    func(res[2])
            except Exception as e:
                self.logging('[warning] {0}.{1} {2} {3}'.format(self.__class__.__name__,\
                    sys._getframe().f_code.co_name, 'get None', e))
            # 如果拿不到消息则睡眠
            time.sleep(1)


    def game_handler_selector(self, interface):
        """
        :funtion: game服事件处理函数选择器
        :param interface: 接口名称
        :return: 返回处理函数
        """
        if self.game_functions.get(interface):
            return self.game_functions[interface]
        else:
            return None

    def match_handler_selector(self, interface):
        """
        :funtion: match服事件处理函数选择器
        :param interface: 接口名称
        :return: 返回处理函数
        """
        if self.match_functions.get(interface):
            return self.match_functions[interface]
        else:
            return None

    def logging(self, msg):
        """
        :function: 控制台日志输出
        :param msg: 消息
        :return: 不返回数据
        """
        log = "{t} {userName} {msg}".format(t=time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()), \
                                            userName=self.userName, msg=msg)
        with open('log.txt', 'a') as f:
            f.write(log+'\n')
        print(log)

    def run(self):
        """
        :function: 创建一个机器人玩家，进入游戏
        :return: 不返回数据
        """
        self.user_login(self.userName, password='123')
        threads = list()
        game_response_gather_thread = threading.Thread(target=self.game_response_gather)
        match_response_gather_thread = threading.Thread(target=self.match_response_gather)
        game_queue_manager_thread = threading.Thread(target=self.game_queue_manager)
        match_queue_manager_thread = threading.Thread(target=self.match_queue_manager)
        threads.append(game_response_gather_thread)
        threads.append(match_response_gather_thread)
        threads.append(game_queue_manager_thread)
        threads.append(match_queue_manager_thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def system_heartbeat(self, session):
        """
        :function: 心跳包
        :return: None
        """
        self.send(session, "system@heartbeat")

    def user_login(self, userName, password):
        """
        :function: 用户登陆 userName=zcc3&password=123
        :param userName: 玩家名
        :param password: 玩家密码
        :return: 不返回数据
        """
        self.send(self.game_session, "user@login", userName=userName, password=password)

    def login_playerlogin(self, platform='ANDROID'):
        """
        :function: 登陆game服，真正进入游戏
            playerId=9101&sessionId=C2665D79E3FF85D09A7872F76E9FBE67&platform=ANDROID
        :param platform: 游戏运行平台
        :return: 不返回数据
        """
        self.send(self.game_session, "login@playerlogin", playerId=self.playerId,
                            sessionId=self.game_sessionId, platform=platform)

    def player_getRoleList(self):
        """
        :function: 获取角色列表
        :return: 不返回数据
        """
        self.send(self.game_session, "player@getRoleList")

    def player_getRandomRoleNames(self, male):
        """
        :function: 获取角色任意名称 male=2
        :param male: 是否男性
        :return: 不返回数据
        """
        self.send(self.game_session, "player@getRandomRoleNames", male=male)

    def player_createRole(self, playerName, pic):
        """
        :function: 创建角色 playerName=武则天pic=nvhuangdi
        :param playerName: 玩家姓名
        :param pic: 玩家头像图片
        :return: 不返回数据
        """
        self.send(self.game_session, "player@createRole", playerName=playerName, pic=pic)

    def player_getRoleInfo2(self):
        """
        :function: 获取游戏角色当前所有状态
        :return: 不返回数据
        """
        self.send(self.game_session, "player@getRoleInfo2")

    def playerTask_ackNotice(self, *notice):
        """
        :function: 完成任务
        :param notice: 任务名称，例如：notice=ackIntroduceBuildImperialKitchen
        :return: 不返回数据
        """
        if len(notice) == 0:
            self.send(self.game_session, "playerTask@ackNotice")
        elif len(notice) == 1:
            self.send(self.game_session, "playerTask@ackNotice", notice=notice[0])
        else:
            raise ValueError()

    def player_doMatch(self, campId):
        """
        :function: 进入选择的剧本开始匹配
        :param campId: 剧本id，例如：campId=1
        :return: 不返回数据
        """
        self.send(self.game_session, "player@doMatch", campId=campId)

    def gm_command(self, cmd):
        """
        :function: 高能接口
        :param cmd: 议题id cmd=跳过引导 f0012 cmd=奖励 vitality:200
        :return: 不返回数据
        """
        self.send(self.game_session, "gm@command", cmd=cmd)

    def match_login(self):
        """
        :function: 登陆match
        :param playerId: 玩家id，例如：playerId=9101
        :param worldId: 世界id，例如：worldId=2_29
        :param certificate: 准入凭证，例如：certificate=9d119c78e8205a9df7c89f1920f5af7d
        :return: 不返回数据
        """
        self.logging('[state] {0}.{1} {2} {3}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
            'match session exists', self.match_session))
        if self.match_session:
            self.send(self.match_session, "match@login", playerId=self.playerId,
                            worldId=self.worldId, certificate=self.certificate)

    def match_playerTask_ackNotice(self, *notice):
        """
        :function: 完成任务
        :param notice: 任务名称，例如：notice=qibing
        :return: 不返回数据
        """
        if len(notice) == 0:
            self.send(self.match_session, "playerTask@ackNotice")
        elif len(notice) == 1:
            self.send(self.match_session, "playerTask@ackNotice", notice=notice[0])
        else:
            raise ValueError()

    def match_player_getInfo(self):
        """
        :function: 进入match后，获取状态信息，是match服推送消息的标志
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "player@getInfo")

    def match_affairs_beginDiscuss(self):
        """
        :function: 开始议政
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "affairs@beginDiscuss")

    def match_affairs_accept(self, affairsId):
        """
        :function: 议政提案 affairsId=-1
        :param affairsId: 提案id
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "affairs@accept", affairsId=affairsId)

    def match_city_plunder(self, cityId):
        """
        :function: 搜刮城池 cityId=3
        :param cityId: 城池id
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.game_session, "city@plunder", cityId=cityId)

    def match_world_antiArmy(self, jianshou):
        """
        :function: 敌人来袭，是否坚守？
        :param jianshou: 1是坚守；2是出击 jianshou=1
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "world@antiArmy", jianshou=jianshou)

    def match_playerTreasure_use(self, tid):
        """
        :function: 使用宝物
        :param tid: 宝物id tid='1'
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "playerTreasure@use", tid=tid)

    def match_affairs_acceptAttackAgain(self, affairsId):
        """
        :function: 继续进攻 affairsId=126
        :param affairsId: 议题id
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "affairs@acceptAttackAgain", affairsId=affairsId)

    def user_login_handler(self, res):
        """
        :function: user@login处理函数
        :param res: user@login接口返回数据
        :return: 不返回数据
        """
        self.game_sessionId = res['data']['sessionId']
        self.player_getRoleList()

    def player_getRoleList_handler(self, res):
        """
        :function: player@getRoleList处理函数
        :param res: player@getRoleList接口返回数据
        :return: 不返回数据
        """
        if res['data']['playerList']:
            self.playerId = int(res['data']['playerList'][0]['playerId'])
            self.logging('[hint] {0}.{1} {2}'.format(self.__class__.__name__,\
                sys._getframe().f_code.co_name, 'begin login'))
            self.login_playerlogin()
        else:
            self.player_getRandomRoleNames(1)

    def player_getRandomRoleNames_handler(self, res):
        """
        :function: player@getRandomRoleNames处理函数
        :param res: player@getRandomRoleNames接口返回数据
        :return: 不返回数据
        """
        self.playerName = res['data']['playerNames'][0]
        self.player_createRole(self.playerName, random.choice(self.pics))

    def player_createRole_handler(self, res):
        """
        :function: player@createRole处理函数
        :param res: player@createRole接口返回数据
        :return: 不返回数据
        """
        self.playerId = res['data']['playerId']
        self.login_playerlogin()

    def push_player_handler(self, res):
        """
        :function: push@player处理函数
        :param res: player@createRole接口返回数据
        :return: 不返回数据
        """
        if res['data'].get('login') == self.playerId:
            self.logging('[hint] {0}.{1} {2}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                'login game server successfully'))
            self.gm_command('跳过引导 f0011')
            self.gm_command('奖励 vitality:1')
            self.player_doMatch(2)

    def login_playerlogin_handler(self, res):
        """
        :function: login@playerlogin处理函数
        :param res: login@playerlogin接口返回数据
        :return: 不返回数据
        """
        self.logging('[hint] {0}.{1} {2}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
            'login game server successfully'))
        if res['state'] == 1 and res['data']['msg'] == '':
            self.gm_command('跳过引导 f0011')
            self.gm_command('奖励 vitality:1')
            self.player_doMatch(2)

    def player_doMatch_handler(self, res):
        """
        :function: player@doMatch处理函数
        :param res: player@doMatch接口返回数据
        :return: 不返回数据
        """
        self.player_getRoleInfo2()

    def player_getRoleInfo2_handler(self, res):
        """
        :function: player@getRoleInfo2处理函数
        :param res: player@getRoleInfo2接口返回数据
        :return: 不返回数据
        """
        if res['data']['taskList']:
            taskList = res['data']['taskList']
            for task in taskList:
                if task['oneTaskInfo'].get('notice'):
                    self.playerTask_ackNotice(task['oneTaskInfo']['notice'])
        if res['data']['info'].get('state') == 3:
            worldRoom = res['data']['info'].get('worldRoom')
            if worldRoom:
                self.worldId = worldRoom.get('worldId')
                self.certificate = worldRoom.get('cert')
                self.match_server.update({
                    'host': worldRoom['matchServer']['host'],
                    'port': int(worldRoom['matchServer']['port'])
                    })
            self.match_session = self.__connect__(self.match_server)
            self.logging('[hint] {0}.{1} {2} '.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                'match session setup, game session destroyed'))
            self.match_login()

    def push_gameInfo_handler(self, res):
        """
        :function: push@gameInfo处理函数
        :param res: push@gameInfo接口返回数据
        :return: 不返回数据
        """
        if res['data']['info'].get('state') == 3:
            worldRoom = res['data']['info'].get('worldRoom')
            if worldRoom:
                self.worldId = worldRoom.get('worldId')
                self.certificate = worldRoom.get('cert')
                self.match_server.update({
                    'host': worldRoom['matchServer']['host'],
                    'port': int(worldRoom['matchServer']['port'])
                    })
            self.match_session = self.__connect__(self.match_server)
            self.logging('[hint] {0}.{1} {2} '.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
                'match session setup, game session destroyed'))
            self.match_login()
        elif res['data']['info']['state'] == 0:
            self.gm_command('奖励 vitality:1')
            self.player_doMatch(2)

    def match_login_handler(self, res):
        """
        :function: match@login处理函数
        :param res: match@login接口返回数据
        :return: 不返回数据
        """
        self.match_sessionId = res['data']['sessionId']
        self.game_session = None
        self.logging('[hint] {0}.{1} {2} {3}'.format(self.__class__.__name__, sys._getframe().f_code.co_name,\
            'game session destroyed', '#'*100))
        self.match_playerTask_ackNotice('qibing')
        self.match_player_getInfo()

    @staticmethod
    def get_affairs(lists):
        """
        :function: 从列表中随机选择一半的元素，不重复
        :param lists: 议题列表
        :return: 返回一半的议题
        """
        temp_list = []
        for i in range(len(lists) // 2):
            x = random.choice(lists)
            temp_list.append(x['id'])
            del lists[lists.index(x)]
        return temp_list

    def match_push_discussAffairs_handler(self, res):
        """
        :function: push@discussAffairs处理函数
        :param res: push@discussAffairs接口返回数据
        :return: 不返回数据
        """
        if res['data'].get('time'):
            self.canDiscussAffairs = res['data']['time']['canDiscussAffairs'] == 'START'
            if self.canDiscussAffairs:
                self.match_affairs_beginDiscuss()
        info = res['data']['info']
        if info and info.get('playerId') == self.playerId:
            if info.get('attackAgain') == 1 and random.random() > 0.5:
                self.match_affairs_accept(info['affairsList'][0]['id'])
            else:
                self.match_affairs_beginDiscuss()
                affairList = self.get_affairs(info['affairsList'])
                for index in affairList:
                    self.match_affairs_accept(index)

    def match_push_destroyCity_handler(self, res):
        """
        :function: push@destroyCity处理函数
        :param res: push@destroyCity接口返回数据
        :return: 不返回数据
        """
        for index in range(len(res['data']['reward']['plunderids'])):
            self.match_city_plunder(res['data']['reward']['cityId'])

    def match_push_player_handler(self, res):
        """
        :function: match服 push@player处理函数
        :param res: match服 push@player接口返回数据
        :return: 不返回数据
        """
        if res['data'].get('worldEnd'):
            self.match_session = None
            return 'worldEnd'

    def match_push_wEnd_handler(self, res):
        """
        :function: 游戏失败并结束
        :return: 不返回数据
        """
        print(res)
        self.match_session = None
        self.match_response_queue_flag = False

    def match_push_world_handler(self, res):
        """
        :function:游戏胜利且结束
        :res:
        :return: 不返回数据
        """
        destroy = res['data'].get('destroy')
        if destroy and destroy.get('winnerId') == self.playerId:
            self.match_session = None
            self.match_response_queue_flag = False

    def match_gm_gmcommand(self, cmd):
        """
        :function: 高能接口
        :param cmd: cmd=议事信息
        :return: 不返回数据
        """
        if self.match_session:
            self.send(self.match_session, "gm@gmcommand", cmd=cmd)

    @staticmethod
    def generate(max_number):
        index_number = 0
        while index_number < max_number:
            yield index_number
            index_number += 1
            time.sleep(0.1)


if __name__ == '__main__':
    processes = list()
    for index in range(ROBOTS_INDEX_MIN, ROBOTS_INDEX_MAX):
        robot = Robots(ROBOTS_NAME_PREFIX + str(index))
        process = multiprocessing.Process(target=robot.run)
        processes.append(process)
    for process in processes:
        process.start()
        time.sleep(JOIN_INTERVAL)
    for process in processes:
        process.join()
        time.sleep(JOIN_INTERVAL)


