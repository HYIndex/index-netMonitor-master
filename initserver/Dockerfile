FROM ubuntu:16.04

RUN mkdir -p /var/duobei/result/ && \
    apt-get update -y && \
    apt-get install make -y && \
    apt-get install g++ -y && \
    apt-get install git -y && \
    apt-get install fping -y

RUN cd /usr/local/ && \
    apt-get install libboost-dev -y && \
    git clone https://github.com/redis/hiredis && \
    cd hiredis/ && \
    make  && \
    make install 

ADD . /usr/local/initserver

RUN echo "/usr/local/lib" >> /etc/ld.so.conf && \
    /sbin/ldconfig && \
#    ls /usr/local/netmtrserver/ && \
    cd /usr/local/initserver/InitQueue && \
    make

WORKDIR /usr/local/initserver/InitQueue

#CMD ["sleep","9000000000"]
CMD ["/usr/local/initserver/InitQueue/initialQueue"]
