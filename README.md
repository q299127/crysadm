我只是搬运工
==============================================================================
2016.03.01 17:00

升级了开免费宝箱功能
收水晶改为6小时收一次

==============================================================================

此版本增加了自动提现功能

此版本加了环境安装脚本，安装脚本支持ubuntu 14.04，debian 8，kali 2.0，实测可用

用法：

进入系统后先升级源，输入命令sudo apt-get update，等一会自动下载，输入命令 sudo apt-get install -y git，如果出现“bash: sudo: command not found”错误，并且提示符是“#”，说明是root权限，直接输入命令apt-get update，完成后输入apt-get install -y sudo git，
用 cd 命令进入任意可写权限文件夹，输入命令 sudo git clone https://github.com/sanzuwu/crysadm.git ，等待下载完成，输入命令
cd crysadm  && sudo chmod +x setup.sh && ./setup.sh,此时等待安装，完成后会自动启动云监工。

其中run.sh是运行脚本，down.sh是停止脚本，setup.sh是安装环境脚本。

剩下的就是设置自启动，隔一段时间自动重启程序，还有时区设置问题，自行百度。
