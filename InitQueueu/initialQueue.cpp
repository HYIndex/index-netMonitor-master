#include "../Include/taskqueue.hpp"
#include <string>
#include <iostream>
#include <fstream>
#include <set>

using namespace std;
const int TestCount = 1000;
bool FilterIpList(string filename, set<string> & ipSet);

int main(void)
{
    string filename;
    set<string> ipSet;
    TaskQueue::initConfig();
    filename = TaskQueue::sSourceFile;

    if (!FilterIpList(filename, ipSet))
    {
        return 0;
    }

    TaskQueue * producer = new TaskQueue();
    if (!producer->connect())
    {
        delete producer;
        return 0;
    }
    for (set<string>::iterator iter = ipSet.begin(); iter != ipSet.end(); iter++)
    {
        producer->push(*iter);
    }
    delete producer;

    return 0;
}

//数据预处理，过滤ip前24位相同的并push到任务队列
bool FilterIpList(string filename, set<string> & ipSet)
{
    ifstream fin(filename.c_str(), ios::in);
    if (!fin.is_open())
    {
        cout << "open student_ip.csv fialed!\n";
        return false;
    }
    string line, ip;
    int pos;

    int count = 1;
    while (getline(fin, line))
    {        
        pos = line.rfind('.');
        ip = line.substr(0, pos);
        ipSet.insert(ip);
        if (count++ == TestCount) {
            break;
        }
        // 测试读取数据
        // cout << "Raw Ip: *" << line << '*' << ", After split: *" << ip << '*' << endl;
    }

    return true;
}