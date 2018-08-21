#!/usr/local/bin/python3.6
#-*- coding: utf-8 -*-

from subprocess import Popen, PIPE
import time
from multiprocessing import Pool, Queue, Manager
from threading import Thread, Timer, Lock
import string, os, fcntl
from configparser import ConfigParser

CMD = 'fping -l -i 1 -e '
TargetIpSet = []
THREAD_NUM = 5
QUEUESIZE = 0  # 在读取配置文件后再赋值

config = {
    'cf_hostname' : None,
    'cf_srcfile': None,
    'cf_outpath': None,
    'cf_psize': None,
    'cf_interval': None,
    'cf_minrowsize': None
}

# 将从标准错误输出的读取设置成非阻塞
def nonBlockRead(output):
    fd = output.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
    try:
        return str(output.read())
    except:
        return ''

# 加载配置文件
def LoadConfig(conf='config.ini'):
    cp = ConfigParser()
    cp.read(conf)
    global config
    global QUEUESIZE
    config['cf_hostname'] = cp.get('config', 'hostname')
    config['cf_srcfile'] = cp.get('config', 'srcfile')
    config['cf_outpath'] = cp.get('config', 'outpath')
    config['cf_psize'] = int(cp.get('config', 'psize'))
    config['cf_interval'] = int(cp.get('config', 'interval'))
    config['cf_minrowsize'] = int(cp.get('config', 'minrowsize'))
    QUEUESIZE = config['cf_psize'] * THREAD_NUM
    # print(config)

# 加载ip文件到内存
def LoadData(fname='accip_1w.csv'):
    global TargetIpSet
    with open(fname) as fin:
        for line in fin.readlines():
            TargetIpSet.append(line.strip())

# 写文件线程， 每小时写一次
def Write(fname, points, lock, sizeQueue, minQueue):
    now = time.strftime("%Y%m%d%H%M%S", time.localtime())
    filename = "{}_{}.csv".format(fname, now)
    lock.acquire()
    with open(filename, 'a') as fw:
        # 找到本线程的列数的最小值
        minrowsize = 99999
        for key, value in points.items():
            length = len(value)
            if (length < (config['cf_minrowsize'])):
                continue
            else:
                if length < minrowsize:
                    minrowsize = length
        lock.release()
        print('come here 0, minrowsize: ', minrowsize)
        # 发送到主线程中， 集中求出所有线程的最小值
        sizeQueue.put(minrowsize)
        minimum = 0
        print('come here 1')
        # 
        while True:
            if not minQueue.empty():
                minimum = minQueue.get()
                break
        print('come here 2, minimum', minimum)
        lock.acquire()
        for key, value in points.items():
            if len(value) < minimum:
                #line = "{}, {}\n".format(key, ", ".join(value))
                continue
            else:
                line = "{}, {}\n".format(key, ", ".join(value[0:minimum]))
            #print(line)
            fw.write(line)
            fw.flush()   
    timer = Timer(config['cf_interval'], Write, args=(fname, points, lock, sizeQueue, minQueue))
    timer.start()
    points.clear()
    lock.release()

def Ping(sizeQueue, minQueue, kwds):
    start = kwds['start']
    end = kwds['end']
    filename = kwds['filename']
    lock = kwds['lock']
    # fout = open(filename, "w")
    # if not fout:
    #     print('open {} failed!'.format(filename))
    print('[Ping]start:', start, 'end:', end)
    argIps = ' '.join(TargetIpSet[start : end])
    cmd = CMD + argIps
    subp = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    # print(subp.stdout.readline())
    # print('flag1')
    points = {}
    timerSetup = Timer(config['cf_interval'], Write, args=(filename, points, lock, sizeQueue, minQueue))
    timerSetup.start()

    while subp.poll() is None:
        resStr = ''
        errStr = ''
        # t1 = time()
        resStr = str(subp.stdout.readline())
        errStr = nonBlockRead(subp.stderr)

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
       
        rtt = resStr[pos+7 : npos].strip()
        # now = time.strftime("%Y%m%d%H", time.localtime())
        key = "{}, {}".format(config['cf_hostname'], ip)
        lock.acquire()
        points[key] = points.get(key, [])
        points[key].append(rtt)
        # print(point)
        errkey = None
        if errStr:
            pos = errStr.find("from ")
            if pos != -1:
                npos = errStr.find(" for")
                if npos != -1:
                    ip = errStr[pos+5 : npos]
                    errkey = "{}, {}".format(config['cf_hostname'], ip)
        if errkey:
            points[errkey] = points.get(errkey, [])
            points[errkey].append(rtt)
        lock.release()
        #     logger.info(errkey)
        # logger.info(point)
        # if i == 10000:
        #     break
        # else:
        #     i += 1
    # print(subp.returncode)

def Process(kwds):
    start = kwds['start']
    end = kwds['end']
    outfile = kwds['outfile']
    sizeQue = kwds['sizeQue']
    minQue = kwds['minQue']
    fname = config['cf_outpath'] + outfile
    print('P : start:{}, end:{}, outfile:{}'.format(start, end, fname))
    gap = int((end - start) / THREAD_NUM)
    taskList_t = []
    pointLock = Lock()
    for i in range(THREAD_NUM):
        filename = fname + str(i+1)
        if i == (THREAD_NUM - 1):            
            taskList_t.append({'start':start+i*gap, 'end':end, 'filename':filename, 'lock':pointLock})
        else:
            taskList_t.append({'start':start+i*gap, 'end':start+(i+1)*gap, 'filename':filename, 'lock':pointLock})
    thds = []
    for task in taskList_t:
        t = Thread(target=Ping, args=(sizeQue, minQue, task))
        thds.append(t)
        t.start()
        # print(t, " start...")
    for t in thds:
        t.join()
        # print(t, ' join...')
    # exit(0)
    
def sizemanager(sizeQueue, minQueue):
    while True:
        if sizeQueue.full():
            minimum = sizeQueue.get()
            while not sizeQueue.empty():
                size = sizeQueue.get()
                if size < minimum:
                    minimum = size
            print('[sizemanager] minimum:{}'.format(minimum))
            for i in range(QUEUESIZE):
                minQueue.put(minimum)     
        # time.sleep(0.001)    
            

def main():
    LoadConfig()
    LoadData(config['cf_srcfile'])
    pSize = config['cf_psize']
    length = len(TargetIpSet)
    print('file length:'+str(length))
    rangeGroups = []
    gap = int(length / pSize)
    for i in range(pSize):
        if i == (pSize - 1):
            rangeGroups.append((i*gap, length))
        else:
            rangeGroups.append((i*gap, (i+1)*gap))
    p = Pool(pSize)
    taskList = []
    sizeQueue = Manager().Queue(QUEUESIZE)
    minQueue = Manager().Queue(QUEUESIZE)
    print('queuesize: {}', QUEUESIZE)
    sizemanager_t = Thread(target=sizemanager, args=(sizeQueue, minQueue))
    sizemanager_t.start()
    i = 1
    t1 = time.time()
    for s, t in rangeGroups:
        filename = "result_" + str(i)
        taskList.append({'start':s, 'end':t, 'outfile':filename, 'sizeQue':sizeQueue, 'minQue':minQueue})
        i += 1
    print(taskList)
    result = p.map_async(Process, taskList)
    result.get()
    print('Waiting for all processes done...')
    p.close()
    p.join()
    print('All subprocesses done.')
    sizemanager_t.join()
    print("total: {}".format(time.time()-t1))
    
if __name__ == '__main__':
    main()