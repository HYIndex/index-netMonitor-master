#!/usr/local/bin/python3.6
#-*- coding: utf-8 -*-

from subprocess import Popen, PIPE
from influxdb import InfluxDBClient
from time import time
from multiprocessing import pool
import string, os
from configparser import ConfigParser

CMD = 'fping -l -e '
TargetIpSet = []

config = {
    'db_host': None,
    'db_port': None,
    'db_dbname': None,
    'db_mmt': None,
    'cf_srcfile': None,
    'cf_pszie': None
}

class DBManager(object):
    '''a manager of influxdb for create db or insert points'''
    def __init__(self, host='localhost', port=8086, dbname='PingResult'):
        self.user = 'root'
        self.__passwd = 'root'
        self.client = InfluxDBClient(host, port, self.user, self.__passwd, dbname)
        self.client.create_database(dbname)
        print('create database: {}'.format(dbname))
    
    def addPoint(self, mmt='result_1', ip='0.0.0.0', rtt=0.0):
        '''add point to influxdb, measurement is mmt'''
        body_json = [
            {
                "measurement": mmt,
                "tags": {
                    "ip": ip,
                },
                "fields": {
                    "rtt": rtt,
                }
            }
        ]
        self.client.write_points(body_json)
    
    def query(self, sql):
        return self.client.query(sql)

    def dropDb(self, dbname):
        self.client.drop_database(dbname)

def LoadConfig(conf='config.ini'):
    cp = ConfigParser()
    cp.read(conf)
    global config
    config['db_host'] = cp.get('influxdb', 'host')
    config['db_port'] = int(cp.get('influxdb', 'port'))
    config['db_dbname'] = cp.get('influxdb', 'dbname')
    config['db_mmt'] = cp.get('influxdb', 'measurement')
    config['cf_srcfile'] = cp.get('config', 'srcfile')
    config['cf_psize'] = int(cp.get('config', 'psize'))

# 加载ip文件到内存
def LoadData(fname='accip_1w.csv'):
    global TargetIpSet
    with open(fname) as fin:
        for line in fin.readlines():
            TargetIpSet.append(line.strip())

def Ping(kwds):
    start = kwds['start']
    end = kwds['end']
    mmt = kwds['mmt']
    # create and initial database
    dbm = DBManager(config['db_host'], config['db_port'], config['db_dbname'])
    if dbm:
        print('success create dbm at: {}:{}'.format(config['db_host'], config['db_port']))
    measurement = mmt
    # exectue cmd
    print('start:{}, end:{}'.format(start, end))
    argIps = ' '.join(TargetIpSet[start : end])
    cmd = CMD + argIps
    subp = Popen(cmd, shell=True, stdout=PIPE)
    # get result and add to database
    while subp.poll() is None:
        resStr = ''
        resStr = str(subp.stdout.readline())
        # print(resStr)
        pos = resStr.find("'")
        if pos == -1:
            continue
        npos = resStr.find(" ", pos + 1)
        if npos == -1:
            continue
        ip = resStr[pos+1 : npos]
        pos = resStr.find("bytes, ", npos)
        if pos == -1:
            continue
        npos = resStr.find(" ms")
        try:
            rtt = float(resStr[pos+7 : npos].strip())
        except Exception as e:
            print('Exception:', e)
        dbm.addPoint(measurement, ip, rtt)

    print(subp.returncode)

def main():
    LoadConfig()
    LoadData(config['cf_srcfile'])
    pSize = config['cf_psize']
    length = len(TargetIpSet)
    # print('file length:'+str(length))
    rangeGroups = []
    gap = int(length / pSize)
    for i in range(pSize):
        if i == (pSize - 1):
            rangeGroups.append((i*gap, length))
        else:
            rangeGroups.append((i*gap, (i+1)*gap))
    p = pool.Pool(pSize)
    taskList = []
    for s, t in rangeGroups:
        taskList.append({'start':s, 'end':t, 'mmt':config['db_mmt']})

    p.map_async(Ping, taskList)
    print('Waiting for all processes done...')
    p.close()
    p.join()
    print('All subprocesses done.')

if __name__ == '__main__':
    main()