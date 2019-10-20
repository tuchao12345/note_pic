#!/usr/local/python27/bin/python
# -*- coding: utf-8 -*-
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import parseaddr, formataddr
import pymysql,datetime

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkess.request.v20140828.ExecuteScalingRuleRequest import ExecuteScalingRuleRequest
from aliyunsdkcms.request.v20180308.QueryMetricLastRequest import QueryMetricLastRequest


def _format_addr(s):
    name, addr = parseaddr(s)
    return formataddr(( \
        Header(name, 'utf-8').encode(), \
        addr.encode('utf-8') if isinstance(addr, unicode) else addr))

# 邮件发送
def send_mail(info):
    mail_host = "smtp.163.com"
    mail_user = "pythondevp@163.com"
    mail_pass = "lku3qFk8lb5lb8"
    from_addr = 'pythondevp@163.com'
    to_addr = ['1183710107@qq.com']

    msg = MIMEText(info, 'plain', 'utf-8')
    msg['From'] = _format_addr(u'阿里云自定义弹性伸缩 <%s>' % from_addr)
    msg['To'] = _format_addr(u'管理员 <%s>' % to_addr)
    msg['Subject'] = Header(u'阿里云自定义弹性告警', 'utf-8').encode()

    smtpObj = smtplib.SMTP_SSL(mail_host,465)
    smtpObj.login(mail_user,mail_pass)
    smtpObj.sendmail(from_addr, to_addr, msg.as_string())


def calc_cpu_average(r_list):
    r_list = json.loads(str(r_list))
    aver_sum = float(0)
    divisor = 0
    for i in r_list:
        aver_sum += float(i.get('Average'))
        divisor += 1
    return int(aver_sum / divisor)

# 阿里云验证信息
client = AcsClient('LTAIt2msIBEOR6YT', '3jczEGwwbK5u6Re58OYFZL1HXfHhir', 'cn-hangzhou')



def get_aliyun_host_info(host_id_list):
    host_instance = []

    for host_id in host_id_list:
        host_instance.append({'instanceId':host_id})

    request = QueryMetricLastRequest()
    request.set_accept_format('json')

    request.set_Dimensions(str(host_instance))
    request.set_Project("acs_ecs_dashboard")
    request.set_Period("60")
    request.set_Metric("CPUUtilization")

    response = client.do_action_with_exception(request)
    r_list = json.loads(response).get('Datapoints')
    return r_list


def excute_aliyun_elastic_rule(rule_identifier):
    request = ExecuteScalingRuleRequest()
    request.set_accept_format('json')

    request.set_ScalingRuleAri(rule_identifier)

    response = client.do_action_with_exception(request)
    print(response)


class OP_DB():

    def __init__(self,elastic_name):
        self.elastic_name = elastic_name
        self.conn = pymysql.connect(host='114.215.169.104',user='jump_user',password='Mckiw2mdKsjU90sL',db='jumpserver',port=8066)

    def get_mysql_data(self):
        cur = self.conn.cursor()
        sql = 'select * from elastic_auto where elastic_name="%s"' % self.elastic_name
        cur.execute(sql)
        elastic_data = cur.fetchone()
        return {'elastic_name':elastic_data[1],'datetime':elastic_data[2],'count':elastic_data[3]}

    def update_record_count(self,count):
        sql = 'update elastic_auto set count=%d where elastic_name="%s"' % (count,self.elastic_name)
        cur = self.conn.cursor()
        cur.execute(sql)
        self.conn.commit()

    def update_record_time(self,now_time):
        sql = 'update elastic_auto set run_time=%s where elastic_name=%s'
        value = []
        value.append(now_time)
        value.append(self.elastic_name)
        cur = self.conn.cursor()
        cur.execute(sql,value)
        self.conn.commit()

    def mysql_conn_close(self):
        self.conn.close()


def cooltime(db_dic):
    cool_time = datetime.datetime.now() - db_dic.get('datetime')
    if cool_time.seconds > 900:
        return 0;
    else:
        return 1;



peiyin = {}
# 项目主机 ID
peiyin['host_id_list'] = ['i-bp1167an2zljwss3wrn8','i-bp1acq02ar70xx9lr60q']
# 弹性伸缩规则标识,peiyin_night_add
peiyin['rule_identifier'] = 'ari:acs:ess:cn-hangzhou:1614280259182296:scalingrule/asr-bp16h6tatimbo6breo5k'
# 弹性组名称
peiyin['elastic_name'] = 'peiyin_elastic3'


children = {}
# 项目主机 ID
children['host_id_list'] = ['i-bp1ah56mmzvacn2k69w5','i-bp19hcysthc28banwgul']
# 弹性伸缩规则标识
children['rule_identifier'] = 'ari:acs:ess:cn-hangzhou:1614280259182296:scalingrule/asr-bp10ssdhwhi3f1nu5l6l'
# 弹性组名称
children['elastic_name'] = 'children_elastic3'



def to_work(project_dic):
    r_list = get_aliyun_host_info(project_dic.get('host_id_list'))
    cpu_aver_val = calc_cpu_average(r_list)
    print('cpu_aver_val:',cpu_aver_val)

# 判断 cpu 使用率情况
    if cpu_aver_val > 75:
        db = OP_DB(project_dic.get('elastic_name'))
        db_dic = db.get_mysql_data()
        if db_dic.get('count') < 3:
            '''发邮件通知'''
            info = 'python customs elastic report %s' % project_dic.get('elastic_name')
            send_mail(info)
        if cooltime(db_dic) == 0:
            '''触发弹性启动规则'''
            excute_aliyun_elastic_rule(rule_identifier=project_dic.get('rule_identifier'))
            now = datetime.datetime.now()
            now_time = now.strftime("%Y-%m-%d %H:%M:%S")
            '''更新冷却时间'''
            db.update_record_time(now_time=now_time)

        count = int(db_dic.get('count')+1)
        db.update_record_count(count=count)
        db.mysql_conn_close()


to_work(project_dic=peiyin)

to_work(project_dic=children)

