﻿# 如有任何疑问及Bug欢迎加入L.k群讨论
# @爱转角遇到了谁 大力更新,请尊重作者
# 为了您的云监工安全,请立马修改config.py[SECRET_KEY] Key！请不要使用默认的
api.py更新日记:
更新用户提现接口
更新MINE信息接口
新增免费宝箱接口
新增放弃宝箱接口
新增秘银进攻接口
新增幸运转盘接口

crysadm_helper.py更新日记:
删除老式矿机变量
新增自动用户提现函数
新增自动免费宝箱函数
新增自动秘银进攻函数
新增自动幸运转盘函数

excavator.py更新日记:
添加设备升级函数
添加设备定位函数
添加出厂设置函数
添加设备管理函数
添加单个账号提现
添加单个账号进攻
添加单个账号转盘
添加所有账号提现
添加所有账号进攻
添加所以账号转盘

admin.py更新日记:
添加自动用户提现变量
添加自动开免费宝箱变量
添加自动秘银进攻变量
添加自动幸运转盘变量
更改最高迅雷账号上限:100

ueer.py更新日记:
添加自动用户提现变量
添加自动开免费宝箱变量
添加自动秘银进攻变量
添加自动幸运转盘变量
更改注册后迅雷账号上限:20

web_common.py更新日记:
更换类型返回信息
删除老式矿机变量

register.html更新日记:
添加注册成功提示框

excavator.html更新日记:
删除老式矿机信息
删除雇佣矿机信息
添加秘银数量信息
添加今日产值信息
添加设备升级按钮
添加设备定位按钮
添加出厂设置按钮
添加设备管理按钮
更换设备显示类型
添加设备固件版本显示
添加设备端口映射显示
添加单个账号进攻按钮
添加单个账号转盘按钮
添加所有账号进攻按钮
添加所以账号转盘按钮

profile.html更新日记:
添加自动提现开关
添加免费宝箱开关
添加秘银进攻开关
添加幸运转盘开关

user_management.html更新日记:
添加自动提现开关
添加免费宝箱开关
添加秘银进攻开关
添加幸运转盘开关

运行环境 python3.3+ , redis
crysadm 启动web服务
config 配置redis server
crysadm_helper 启动后台服务

安装后访问 /install 生成管理员账号
config.py.example 改名为config.py 使用