#ifndef _TASKQUEUE_H_
#define _TASKQUEUE_H_
 
#include <iostream>
#include <fstream>
#include <sstream>
#include <string.h>
#include <string>
#include <stdio.h> 
#include <hiredis/hiredis.h>

using namespace std;
const int timeout = 5;
 
class TaskQueue
{
public:
 
    TaskQueue(){
        this->_connect = NULL;
        this->_reply = NULL;
    }
 
    ~TaskQueue()
    {
        redisFree(this->_connect);
        this->_connect = NULL;
        this->_reply = NULL;         
    }
 
    bool connect(string host = TaskQueue::sHost, int port = sPort)
    {
        //cout << "break1" << endl;
        this->_connect = redisConnect(host.c_str(), port);
        if(this->_connect != NULL && this->_connect->err)
        {
            printf("connect error: %s\n", this->_connect->errstr);
            return false;
        }
        //cout << "break2" << endl;
        return true;
    }
 
    string pop()
    {
        //cout << "p1" << endl;
        this->_reply = (redisReply*)redisCommand(this->_connect, "BRPOP %s %d", TaskQueue::sKeyName.c_str(), timeout);
        //cout << "p2" << endl;
        //cout << "this->_reply:" << this->_reply << endl;
        string str = "";
        if (this->_reply)
        {
            switch(this->_reply->type)
            {
                case 1:
                    str = this->_reply->str;
                    break;
                case 2:
                    str = this->_reply->element[1]->str;
                    break;
                default:
                    //cout << "End: TaskQueue Is Empty!\n";
                    break;
            }
            //printf("%s type:%d\n", this->_reply->str, this->_reply->type);
        }
        //cout << "p3" << endl;
        freeReplyObject(this->_reply);
        return str;
    }
 
    void push(string value)
    {
        this->_reply = (redisReply*)redisCommand(this->_connect, "LPUSH %s %s", TaskQueue::sKeyName.c_str(), value.c_str());
        //printf("push res: %s %lld\n", this->_reply->str, this->_reply->integer);
    }

    static void initConfig()
    {
        ifstream infile; 
        infile.open("../config.txt"); 
        //assert(infile.is_open());
        string s;
        while(getline(infile,s))
        {
            int pos, npos;
            if (-1 != (pos = s.find("sourcefile")))
            {
                npos = s.rfind("\"");
                TaskQueue::sSourceFile = s.substr(pos + 12, npos-(pos+12));
            }
            else if (-1 != (pos = s.find("host")))
            {
                npos = s.rfind("\"");
                TaskQueue::sHost = s.substr(pos + 6, npos-(pos+6));
            }
            else if (-1 != (pos = s.find("port")))
            {
                npos = s.rfind("\"");
                istringstream iss(s.substr(pos + 6, npos-(pos+6)));
                int tmp;
                iss >> tmp;
                TaskQueue::sPort = tmp;
            }
            else if (-1 != (pos = s.find("keyname")))
            {
                npos = s.rfind("\"");
                TaskQueue::sKeyName = s.substr(pos + 9, npos-(pos+9));
            }
            else if (-1 != (pos = s.find("outdir")))
            {
                npos = s.rfind("\"");
                TaskQueue::sOutDir = s.substr(pos + 8, npos-(pos+8));
            }
            else
            {
                //
            }
            s = "";            
        }        
        infile.close();
    }
    
private:
 
    redisContext* _connect;
    redisReply* _reply;

public:

    static string sSourceFile;
    static string sHost; 
    static int sPort;
    static string sKeyName;
    static string sOutDir;
};

string TaskQueue::sSourceFile = "";
string TaskQueue::sHost = "";
int TaskQueue::sPort = 0;
string TaskQueue::sKeyName = "";
string TaskQueue::sOutDir = "";

#endif  //_TASKQUEUE_H_

