#!/usr/local/bin/python3.6
#-*- coding: utf-8 -*-

from subprocess import Popen, PIPE
import time
from multiprocessing import Pool
from threading import Thread
import string, os, fcntl
from configparser import ConfigParser
import logging
import logging.handlers

CMD = 'fping -l -i 1 -e '
TargetIpSet = []
THREAD_NUM = 6

config = {
    'cf_hostname' : None,
    'cf_srcfile': None,
    'cf_outpath': None,
    'cf_psize': None
}

def nonBlockRead(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return str(output.read())
    except:
        return ''

def LoadConfig(conf='config.ini'):
    cp = ConfigParser()
    cp.read(conf)
    global config
    config['cf_hostname'] = cp.get('config', 'hostname')
    config['cf_srcfile'] = cp.get('config', 'srcfile')
    config['cf_outpath'] = cp.get('config', 'outpath')
    config['cf_psize'] = int(cp.get('config', 'psize'))
    print(config)

# 加载ip文件到内存
def LoadData(fname='accip_1w.csv'):
    global TargetIpSet
    with open(fname) as fin:
        for line in fin.readlines():
            TargetIpSet.append(line.strip())

def createLogger(prefix):
    # logging.basicConfig()
    logger = logging.getLogger(prefix)
    logger.setLevel(logging.INFO)
    # 定义日志输出格式
    formatter  = logging.Formatter('%(message)s')
    # 创建TimedRotatingFileHandler处理对象
    # 间隔5(S)创建新的名称为myLog%Y%m%d_%H%M%S.log的文件，并一直占用Log文件。
    fileshandle = logging.handlers.TimedRotatingFileHandler(prefix+".log", when='D', interval=1)
    # 设置日志文件后缀，以当前时间作为日志文件后缀名。
    fileshandle.suffix = "%Y%m%d_%H%M%S.log"
    # 设置日志输出级别和格式
    fileshandle.setLevel(logging.INFO)
    fileshandle.setFormatter(formatter)
    logger.addHandler(fileshandle)
    return logger

def Ping(kwds):
    start = kwds['start']
    end = kwds['end']
    filename = kwds['filename']
    # fout = open(filename, "w")
    logger = createLogger(filename)
    # if not fout:
    #     print('open {} failed!'.format(filename))
    # exectue cmd
    # print('start:', start, 'end', end)
    argIps = ' '.join(TargetIpSet[start : end])
    cmd = CMD + argIps
    subp = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    # print(subp.stdout.readline())
    # print('flag1')
    i = 1
    ctlCount = 1
    while subp.poll() is None:
        resStr = ''
        errStr = ''
        # t1 = time()
        resStr = str(subp.stdout.readline())
        if ctlCount == 100:
            errStr = nonBlockRead(subp.stderr)
            ctlCount = 1
        else:
            ctlCount += 1
        # t2 = time()
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
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        point = "{}, {}, {}, {}(ms)".format(config['cf_hostname'], ip, now, rtt)
        # print(point)
        errpoint = None
        if errStr:
            pos = errStr.find("from ")
            if pos != -1:
                npos = errStr.find(" for")
                if npos != -1:
                    ip = errStr[pos+5 : npos]
                    errpoint = "{}, {}, {}, {}(ms)".format(config['cf_hostname'], ip, now, -1)
        if errpoint:
            logger.info(errpoint)
        logger.info(point)
        if i == 1000:
            break
        else:
            i += 1
    # print(subp.returncode)

def Process(kwds):
    start = kwds['start']
    end = kwds['end']
    outfile = kwds['outfile']
    fname = config['cf_outpath'] + outfile
    print('P : start:{}, end:{}, outfile:{}'.format(start, end, fname))
    gap = int((end - start) / THREAD_NUM)
    taskList_t = []
    for i in range(THREAD_NUM):
        filename = fname + str(i+1)
        if i == (THREAD_NUM - 1):            
            taskList_t.append({'start':start+i*gap, 'end':end, 'filename':filename})
        else:
            taskList_t.append({'start':start+i*gap, 'end':start+(i+1)*gap, 'filename':filename})
    thds = []
    for task in taskList_t:
        t = Thread(target=Ping, args=(task,))
        thds.append(t)
        t.start()
        # print(t, " start...")
    for t in thds:
        t.join()
        # print(t, ' join...')
    # exit(0)
    

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
    p = Pool(pSize)
    taskList = []
    i = 1
    t1 = time.time()
    for s, t in rangeGroups:
        filename = "result_" + str(i)
        taskList.append({'start':s, 'end':t, 'outfile':filename})
        i += 1
    # print(taskList)
    p.map_async(Process, taskList)
    print('Waiting for all processes done...')
    p.close()
    p.join()
    print('All subprocesses done.')
    print("total: {}".format(time.time()-t1))
if __name__ == '__main__':
    main()