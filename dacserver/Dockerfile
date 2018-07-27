FROM ubuntu:16.04

RUN apt-get update -y && \
    apt-get install fping -y

RUN apt-get install python3 -y && \
    apt-get install python3-pip -y && \
    pip3 install influxdb

ADD . /usr/local/dacserver

WORKDIR /usr/local/dacserver

#CMD ["sleep","9000000000"]
CMD ["python3", "/usr/local/dacserver/ParaPing.py"]
