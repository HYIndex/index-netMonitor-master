/*
    Filename: monitor.cpp
    Author: zhang haiyang
    Mail: haiyang.zhang@duobei.com
    Datetime: 2018-7-10 13：33
*/

#include <iostream>
#include <string>
#include <sys/time.h>
#include <fstream>
#include <sstream>
#include <boost/uuid/uuid.hpp>
#include <boost/uuid/uuid_io.hpp>
#include <boost/uuid/uuid_generators.hpp>
#include <hiredis/hiredis.h>
#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#include "../Include/taskqueue.hpp"

using namespace std;

boost::uuids::uuid uid = boost::uuids::random_generator()();
const string uid_str = boost::uuids::to_string(uid);
const string accessible = TaskQueue::sOutDir + "AccIp_" + uid_str + ".csv";
const string unaccessible = TaskQueue::sOutDir + "UnaccIp_" + uid_str + ".csv";
const int TestSize = 5;
void PingOne(string ip_netnum, ofstream & fout_acc, ofstream & fout_unacc);

int main(void)
{
    TaskQueue::initConfig();
    string path = TaskQueue::sOutDir;
    ofstream fout_acc, fout_unacc;
    DIR * dp = NULL;
    //如果目录不存在则创建
    if (NULL == (dp = opendir(path.c_str())))
    {
        string cmd = "mkdir -p " + path;
        system(cmd.c_str());
    }
    else
    {
        closedir(dp);
    }
    // string cmd = "touch " + path + accessible;
    // system(cmd.c_str());
    fout_acc.open(path + accessible);
    //cout << path + accessible << endl;
    if (!fout_acc.is_open())
    {
        cout << "open accfile failed!" << endl; 
        return 0;
    }
    fout_unacc.open(path + unaccessible);
    if (!fout_unacc.is_open())
    {
        cout << "open unaccfile failed!" << endl; 
        return 0;
    }
    string getip;
    TaskQueue * customer = new TaskQueue();
    if (!customer->connect())
    {
        delete customer;
        return 0;
    }
    cout << "Start...\n";
    int count = 0;
    while (!(getip = customer->pop()).empty())
    {
        if (count == TestSize)
        {
            break;
        }
        count++;
        PingOne(getip, fout_acc, fout_unacc);
    }
    fout_acc.close();
    fout_unacc.close();

    return 0;
}

//ping以ip_netnum开头的所有256个ip
void PingOne(string ip_netnum, ofstream & fout_acc, ofstream & fout_unacc)
{
    //在网络号后加上主机号
    int index;
    string ip_addr, ip_hostnum, cmd;
    cmd = "fping -a";
    char * cmd_cstr;
    FILE * fp;
    char buffer[16];
    for (index = 0; index < 256; index++)
    {
        stringstream ss;
        ss << index;
        ss >> ip_hostnum;
        ip_addr = ip_netnum + '.' + ip_hostnum;
        cmd += ' ';
        cmd += ip_addr;
    }
    cmd_cstr = (char *)malloc(sizeof(char) * cmd.size());
    strcpy(cmd_cstr, cmd.c_str());
    //cout << cmd_cstr << endl;
    fp = popen(cmd_cstr, "r");
    int flag = 0;
    if (fp == NULL)
    {
        cout << "execute command failed!" << endl;
        return;
    }
    else
    {
        //cout << 1111 << endl;
        string tmp = ip_netnum + ".0/24";
        char * find;
        while (fgets(buffer, sizeof(buffer), fp))
        {
            flag = 1;
            find = strchr(buffer, '\n');
            if (find) {
                *find = '\0';
            }
            //printf("#%s#\n", buffer);
            if (strlen(buffer) == 0) {
                continue;
            }
            tmp += ", ";
            tmp += buffer;
            strcpy(buffer, "");
        }
        if (flag)
        {        
            tmp += "\n";
            //cout << "accessible: " << tmp << endl;
            fout_acc << tmp;
        }
        else
        {
            string tmp = ip_netnum + ".0/24\n";
            //cout << "unaccessible: " << tmp << endl;
            fout_unacc << tmp;
        }
    }
    // gettimeofday(&end, NULL);
    // timer = 1000000 * (end.tv_sec-start.tv_sec) + end.tv_usec - start.tv_usec;
    // printf("time cost: %ld us\n", timer);
    pclose(fp);
    free(cmd_cstr);
}

