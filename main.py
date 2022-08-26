#!/usr/bin/env python
#coding=utf-8
import os
import yaml
import json
import logging
import logging.config
import urllib.request
from datetime import datetime
from aliyunsdkcore.client import AcsClient
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from apscheduler.schedulers.blocking import BlockingScheduler

# 日志配置
logging.basicConfig(filename="./ddns.log", level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

LOGGING = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s %(message)s',
            'datefmt': '%m/%d/%Y %I:%M:%S %p'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'success': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'debug.log'),
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,
            'formatter': 'default'
        }
    },
    'loggers': {
        'mylogger': {
            'handlers': ['console', 'success'],
            'level': 'INFO',
            'propagate': False
        },
    }
}

logging.config.dictConfig(LOGGING)
logger2 = logging.getLogger("mylogger")
logger2.info('test config load')

class AliyunDDNS:
    def __init__(self, access_key_id, access_secret, region_id, domain, **kwargs):
        self.access_key_id = access_key_id
        self.access_secret = access_secret
        self.domain = domain
        self.client = AcsClient(self.access_key_id, self.access_secret, region_id)
        self.record_id = ''

    def record_search(self, record_name):
        request = DescribeDomainRecordsRequest()
        request.set_accept_format('json')
        request.set_DomainName(self.domain)
        request.set_SearchMode("EXACT")
        request.set_KeyWord(record_name)
        response = self.client.do_action_with_exception(request)
        return json.loads(response)['DomainRecords']['Record'][0]['RecordId']

    def update(self, record_name, record_type, ipaddr):
        self.record_id = self.record_search(record_name)
        request = UpdateDomainRecordRequest()
        request.set_RecordId(self.record_id)
        request.set_accept_format('json')
        request.set_Value(ipaddr)
        request.set_Type(record_type)
        request.set_RR(record_name)
        request.set_RecordId(self.record_id)
        try:
            response = self.client.do_action_with_exception(request)
            print("域名更新成功！")
        except Exception as e:
            estr = str(e)
            exists_code = estr.count("HTTP Status: 400 Error:DomainRecordDuplicate The DNS record already exists.")
            if exists_code:
                logging.info("无需更新，公网ip未发生改变")
                print("无需更新，公网ip未发生改变")
                return 'OK'
            logging.error("更新失败！日志：")
            print("更新失败！日志：")


def config_loader():
    curPath = os.path.dirname(os.path.realpath(__file__))
    yamlPath = os.path.join(curPath, "ddns.yaml")

    with open(yamlPath, 'r', encoding='utf-8') as f:
        d = yaml.safe_load(f.read())
    data = {
        "access_key_id": d['aliyun']['access_key_id'],
        "access_secret": d['aliyun']['access_secret'],
        "region_id": d['aliyun']['region_id'],
        "domain": d['aliyun']['domain'],
        "update_list": d['update_list']
    }
    return data


if __name__ == '__main__':
    def main_func():
        params = config_loader()
        my = AliyunDDNS(**params)
        for i in params['update_list']:
            my.update(
                record_name=i['name'],
                record_type=i['type'],
                ipaddr='1.22.33.44'
            )

    scheduler = BlockingScheduler(timezone='Asia/Shanghai')  # 阻塞
    scheduler.add_job(main_func, 'cron', minute="*/5", hour='*')
    scheduler.start()
