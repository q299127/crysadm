__author__ = 'powergx'
import config, socket, redis
import time
from login import login
from datetime import datetime, timedelta
from multiprocessing import Process
from multiprocessing.dummy import Pool as ThreadPool
import threading

conf = None
if socket.gethostname() == 'GXMBP.local':
    conf = config.DevelopmentConfig
elif socket.gethostname() == 'iZ23bo17lpkZ':
    conf = config.ProductionConfig
else:
    conf = config.TestingConfig

redis_conf = conf.REDIS_CONF
pool = redis.ConnectionPool(host=redis_conf.host, port=redis_conf.port, db=redis_conf.db, password=redis_conf.password)
r_session = redis.Redis(connection_pool=pool)

from api import *

# 获取用户数据
def get_data(username):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_data')

    start_time = datetime.now()
    try:
        for user_id in r_session.smembers('accounts:%s' % username):
            
            account_key = 'account:%s:%s' % (username, user_id.decode('utf-8'))
            account_info = json.loads(r_session.get(account_key).decode('utf-8'))

            if not account_info.get('active'): continue

            if DEBUG_MODE:            
                print("start get_data with userID:", user_id)

            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')
            cookies = dict(sessionid=session_id, userid=str(user_id))

            mine_info = get_mine_info(cookies)
            if is_api_error(mine_info):
                if DEBUG_MODE:
                    print('get_data:', user_id, mine_info, 'error')
                return

            if mine_info.get('r') != 0:

                success, account_info = __relogin(account_info.get('account_name'), account_info.get('password'), account_info, account_key)
                if not success:
                    print('get_data:', user_id, 'relogin failed')
                    continue
                session_id = account_info.get('session_id')
                user_id = account_info.get('user_id')
                cookies = dict(sessionid=session_id, userid=str(user_id))
                mine_info = get_mine_info(cookies)

            if mine_info.get('r') != 0:
                print('get_data:', user_id, mine_info, 'error')
                continue

            device_info = ubus_cd(session_id, user_id, 'get_devices', ["server", "get_devices", {}], '&action=%donResponse' % int(time.time()*1000))
            red_zqb = device_info['result'][1]

            account_data_key = account_key + ':data'
            exist_account_data = r_session.get(account_data_key)
            if exist_account_data is None:
                account_data = dict()
                account_data['privilege'] = get_privilege(cookies)
            else:
                account_data = json.loads(exist_account_data.decode('utf-8'))

            if account_data.get('updated_time') is not None:
                last_updated_time = datetime.strptime(account_data.get('updated_time'), '%Y-%m-%d %H:%M:%S')
                if last_updated_time.hour != datetime.now().hour:
                    account_data['zqb_speed_stat'] = get_speed_stat('1', cookies)
                    account_data['old_speed_stat'] = get_speed_stat('0', cookies)
            else:
                account_data['zqb_speed_stat'] = get_speed_stat('1', cookies)
                account_data['old_speed_stat'] = get_speed_stat('0', cookies)

            account_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            account_data['mine_info'] = mine_info
            account_data['device_info'] = red_zqb.get('devices')
            account_data['income'] = get_income_info(cookies)
            account_data['produce_info'] = get_produce_stat(cookies)

            if is_api_error(account_data.get('income')):
                print('get_data:', user_id, 'income', 'error')
                return

            r_session.set(account_data_key, json.dumps(account_data))
            if not r_session.exists('can_drawcash'):
                r = get_can_drawcash(cookies=cookies)
                if r.get('r') == 0:
                    r_session.setex('can_drawcash', r.get('is_tm'), 60)

        if start_time.day == datetime.now().day:
            save_history(username)

        r_session.setex('user:%s:cron_queued' % username, '1', 60)
        if DEBUG_MODE:
            print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'successed')        
    except Exception as ex:
        print(username.encode('utf-8'), 'failed', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ex)

# 保存历史数据
def save_history(username):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'save_history')
    str_today = datetime.now().strftime('%Y-%m-%d')
    key = 'user_data:%s:%s' % (username, str_today)
    b_today_data = r_session.get(key)
    today_data = dict()

    if b_today_data is not None:
        today_data = json.loads(b_today_data.decode('utf-8'))

    today_data['updated_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_data['pdc'] = 0
    today_data['last_speed'] = 0
    today_data['deploy_speed'] = 0
    today_data['balance'] = 0
    today_data['income'] = 0
    today_data['speed_stat'] = list()
    today_data['pdc_detail'] = []
    today_data['giftbox_pdc'] = 0
    today_data['produce_stat'] = [] 

    for user_id in r_session.smembers('accounts:%s' % username):
        # 获取账号所有数据
        account_data_key = 'account:%s:%s:data' % (username, user_id.decode('utf-8'))
        b_data = r_session.get(account_data_key)
        if b_data is None:
            continue
        data = json.loads(b_data.decode('utf-8'))

        if datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S') + timedelta(minutes=1) < datetime.now() or \
                        datetime.strptime(data.get('updated_time'), '%Y-%m-%d %H:%M:%S').day != datetime.now().day:
            continue
        today_data.get('speed_stat').append(dict(mid=data.get('privilege').get('mid'),
                                                 dev_speed=data.get('zqb_speed_stat') if data.get(
                                                     'zqb_speed_stat') is not None else [0] * 24,
                                                 pc_speed=data.get('old_speed_stat') if data.get(
                                                     'old_speed_stat') is not None else [0] * 24))
        this_pdc = data.get('mine_info').get('dev_m').get('pdc') + \
                   data.get('mine_info').get('dev_pc').get('pdc')

        today_data['pdc'] += this_pdc
        today_data.get('pdc_detail').append(dict(mid=data.get('privilege').get('mid'), pdc=this_pdc))

        today_data['balance'] += data.get('income').get('r_can_use')
        today_data['income'] += data.get('income').get('r_h_a')
        today_data['giftbox_pdc'] += data.get('mine_info').get('td_box_pdc')
        today_data.get('produce_stat').append(dict(mid=data.get('privilege').get('mid'), hourly_list=data.get('produce_info').get('hourly_list')))
        for device in data.get('device_info'):
            today_data['last_speed'] += int(int(device.get('dcdn_upload_speed')) / 1024)
            today_data['deploy_speed'] += int(device.get('dcdn_download_speed') / 1024)

    r_session.setex(key, json.dumps(today_data), 3600 * 24 * 35)
    save_income_history(username, today_data.get('pdc_detail'))

# 获取保存的历史数据
def save_income_history(username, pdc_detail):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'save_income_history')
    now = datetime.now()
    key = 'user_data:%s:%s' % (username, 'income.history')
    b_income_history = r_session.get(key)
    income_history = dict()

    if b_income_history is not None:
        income_history = json.loads(b_income_history.decode('utf-8'))

    if now.minute < 50:
        return

    if income_history.get(now.strftime('%Y-%m-%d')) is None:
        income_history[now.strftime('%Y-%m-%d')] = dict()

    income_history[now.strftime('%Y-%m-%d')][now.strftime('%H')] = pdc_detail

    r_session.setex(key, json.dumps(income_history), 3600 * 72)

# 重新登录
def __relogin(username, password, account_info, account_key):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), username.encode('utf-8'), 'relogin')

    login_result = login(username, password, conf.ENCRYPT_PWD_URL)

    if login_result.get('errorCode') != 0:
        account_info['status'] = login_result.get('errorDesc')
        account_info['active'] = False
        r_session.set(account_key, json.dumps(account_info))
        return False, account_info

    account_info['session_id'] = login_result.get('sessionID')
    account_info['status'] = 'OK'
    r_session.set(account_key, json.dumps(account_info))
    return True, account_info

# 获取在线用户数据
def get_online_user_data():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_online_user_data')
    if r_session.exists('api_error_info'):
        return

    pool = ThreadPool(processes=5)

    pool.map(get_data, (u.decode('utf-8') for u in r_session.smembers('global:online.users')))
    pool.close()
    pool.join()

# 执行自动提现的函数
def prc_background_drawcash(cookies):
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'prc_background_drawcash()')
    xunlei_api_exec_getCash2(cookies=cookies, limits=10)

# 获取离线用户数据
def get_offline_user_data():
    if DEBUG_MODE:
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'get_offline_user_data')
    if r_session.exists('api_error_info'):
        return

    if datetime.now().minute < 50:
        return

    offline_users = []
    for b_user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in r_session.sdiff('users', *r_session.smembers('global:online.users'))]):
        user_info = json.loads(b_user.decode('utf-8'))

        username = user_info.get('username')

        if not user_info.get('active'): continue

        every_hour_key = 'user:%s:cron_queued' % username
        if r_session.exists(every_hour_key): continue

        offline_users.append(username)

    pool = ThreadPool(processes=5)

    pool.map(get_data, offline_users)
    pool.close()
    pool.join()

# 从在线用户列表中清除离线用户
def clear_offline_user():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'clear_offline_user')
    for b_username in r_session.smembers('global:online.users'):
        username = b_username.decode('utf-8')
        if not r_session.exists('user:%s:is_online' % username):
            r_session.srem('global:online.users', username)

# 刷新选择自动任务的用户
def select_auto_task_user():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'select_auto_task_user')
    auto_collect_accounts = []
    auto_giftbox_accounts = []
    auto_cashbox_accounts = []
    auto_searcht_accounts = []
    auto_getaward_accounts = []
    for b_user in r_session.mget(*['user:%s' % name.decode('utf-8') for name in r_session.smembers('users')]):
        user_info = json.loads(b_user.decode('utf-8'))
        if not user_info.get('active'): continue
        username = user_info.get('username')
        account_keys = ['account:%s:%s' % (username, user_id.decode('utf-8')) for user_id in r_session.smembers('accounts:%s' % username)]
        if len(account_keys) == 0: continue
        for b_account in r_session.mget(*account_keys):
            account_info = json.loads(b_account.decode('utf-8'))
            if not (account_info.get('active')): continue
            session_id = account_info.get('session_id')
            user_id = account_info.get('user_id')
            cookies = json.dumps(dict(sessionid=session_id, userid=user_id))
            if user_info.get('auto_collect'): auto_collect_accounts.append(cookies)
            if user_info.get('auto_giftbox'): auto_giftbox_accounts.append(cookies)
            if user_info.get('auto_cashbox'): auto_cashbox_accounts.append(cookies)
            if user_info.get('auto_searcht'): auto_searcht_accounts.append(cookies)
            if user_info.get('auto_getaward'): auto_getaward_accounts.append(cookies)
    r_session.delete('global:auto.collect.cookies')
    r_session.sadd('global:auto.collect.cookies', *auto_collect_accounts)
    r_session.delete('global:auto.giftbox.cookies')
    r_session.sadd('global:auto.giftbox.cookies', *auto_giftbox_accounts)
    r_session.delete('global:auto.cashbox.cookies')
    r_session.sadd('global:auto.cashbox.cookies', *auto_cashbox_accounts)
    r_session.delete('global:auto.searcht.cookies')
    r_session.sadd('global:auto.searcht.cookies', *auto_searcht_accounts)
    r_session.delete('global:auto.getaward.cookies')
    r_session.sadd('global:auto.getaward.cookies', *auto_getaward_accounts)

# 执行收取水晶函数
def check_collect(cookies):
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_collect')
    try:
        mine_info = get_mine_info(cookies)
        if mine_info.get('r') == 0 and mine_info.get('td_not_in_a') > 1000:
            collect(cookies)
    except requests.exceptions.RequestException as e:
        return

# 执行免费宝箱函数
def check_giftbox(cookies):
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_giftbox')
    try:
        box_info = api_giftbox(cookies)
        if box_info is None: return
        for box in box_info:
            #开宝箱
            #direction = 开启方向
            #   左切 = 1；竖切=2；右切=3
            #box.get('cnum') = 开宝箱的费用,0为免费宝箱
            if box.get('cnum') == 0:
                api_openStone(cookies=cookies, giftbox_id=box.get('id'), direction='3')
    except Exception as e:
        return

# 执行收费宝箱函数
def check_cashbox(cookies):
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_cashbox')
    try:
        box_info = api_giftbox(cookies)
        if box_info is None: return
        for box in box_info:
            #开宝箱
            #direction = 开启方向
            #   左切 = 1；竖切=2；右切=3
            #box.get('cnum') = 开宝箱的费用,0为免费宝箱
            api_openStone(cookies=cookies, giftbox_id=box.get('id'), direction='3')
    except Exception as e:
        return

# 执行秘银进攻函数
def check_searcht(cookies):
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_searcht')
    try:
        r = api_searcht_steal(cookies)
        if r.get('r') != 0:
            print('体力值不足')
        else:
            time.sleep(2)
            t = api_searcht_collect(cookies=cookies, searcht_id=r.get('sid'))
            time.sleep(1)
            api_summary_steal(cookies=cookies, searcht_id=r.get('sid'))
            print('进攻成功,获得:%s' % t.get('s'))
    except Exception as e:
        return

# 执行幸运转盘函数
def check_getaward(cookies):
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'check_getaward')
    try:
        t = api_getconfig(cookies)
        if t.get('rd') != 'ok':
            print('%s' % t.get('rd'))
        else:
            if t.get('cost') != 5000:
                print('所需秘银大于5000,不执行转动')
            else:
                api_getaward(cookies)
                print('开始执行转动')
    except Exception as e:
        return

# 收取水晶
def collect_crystal():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'collect_crystal')
    for cookie in r_session.smembers('global:auto.collect.cookies'):
        check_collect(json.loads(cookie.decode('utf-8')))

# 免费宝箱
def giftbox_crystal():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'giftbox_crystal')
    for cookie in r_session.smembers('global:auto.giftbox.cookies'):
        check_giftbox(json.loads(cookie.decode('utf-8')))

# 收费宝箱
def cashbox_crystal():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'cashbox_crystal')
    for cookie in r_session.smembers('global:auto.cashbox.cookies'):
        check_cashbox(json.loads(cookie.decode('utf-8')))

# 秘银进攻
def searcht_crystal():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'searcht_crystal')
    for cookie in r_session.smembers('global:auto.searcht.cookies'):
        check_searcht(json.loads(cookie.decode('utf-8')))

# 幸运转盘
def getaward_crystal():
    if DEBUG_MODE: 
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'getaward_crystal')
    for cookie in r_session.smembers('global:auto.getaward.cookies'):
        check_getaward(json.loads(cookie.decode('utf-8')))

# 计时器函数，定期执行某个线程，时间单位为秒
def timer(func, seconds):   
    while True:
        Process(target=func).start()
        time.sleep(seconds)


if __name__ == '__main__':
    # 如有任何疑问及Bug欢迎加入L.k群讨论
    # 执行收取水晶时间，单位为秒，默认为30秒。
    # 每6小时检测一次收取水晶
    threading.Thread(target=timer, args=(collect_crystal, 21600)).start()
    # 执行免费宝箱时间，单位为秒，默认为300秒。
    # 每20分钟检测一次免费宝箱
    threading.Thread(target=timer, args=(giftbox_crystal, 60*5)).start()
    # 执行收费宝箱时间，单位为秒，默认为40秒。
    # 每40分钟检测一次收费宝箱
    threading.Thread(target=timer, args=(cashbox_crystal, 40)).start()
    # 执行秘银进攻时间，单位为秒，默认为50秒。
    # 每50分钟检测一次秘银进攻
    threading.Thread(target=timer, args=(searcht_crystal, 50*60)).start()
    # 执行幸运转盘时间，单位为秒，默认为60秒。
    # 每60分钟检测一次幸运转盘
    threading.Thread(target=timer, args=(getaward_crystal, 60*60)).start()
    # 刷新在线用户数据，单位为秒，默认为30秒。
    # 每30秒刷新一次在线用户数据
    threading.Thread(target=timer, args=(get_online_user_data, 30)).start()
    # 刷新离线用户数据，单位为秒，默认为60秒。
    # 每30分钟刷新一次离线用户数据
    threading.Thread(target=timer, args=(get_offline_user_data, 1800)).start()
    # 从在线用户列表中清除离线用户，单位为秒，默认为60秒。
    # 每分钟检测离线用户
    threading.Thread(target=timer, args=(clear_offline_user, 60)).start()
    # 刷新选择自动任务的用户，单位为秒，默认为10分钟
    threading.Thread(target=timer, args=(select_auto_task_user, 60)).start()
    while True:
        time.sleep(1)
