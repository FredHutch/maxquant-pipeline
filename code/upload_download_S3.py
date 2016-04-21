#!/usr/bin/python
"""
mq-ec2worker.py: create, bootstrap a MaxQuant EC2 instance and start a job
"""
import boto3

mqBucket = "fredhutch-maxquant-jobs"
jobName = "rmcdermo484848"

def main():
    upload2(mqBucket, jobName)
    #download2(mqBucket, jobName)

def upload(mqBucket, jobName):
    s3 = boto3.resource('s3', "us-west-2")
    bucket = s3.Bucket(mqBucket)
    bucket.upload_file('test.xml', "{0}/test.xml".format(jobName))

def download(mqBucket, jobName):
    s3 = boto3.resource('s3', "us-west-2")
    bucket = s3.Bucket(mqBucket)
    bucket.download_file("{0}/test.xml".format(jobName), 'test-copy.xml')
    
def upload2(mqBucket, jobName):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    transfer.upload_file('myfile.bin', mqBucket, "{0}/myfile.bin".format(jobName))

def download2(mqBucket, jobName):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    transfer.download_file(mqBucket, "{0}/myfile.bin".format(jobName), 'myfile2.bin')

if __name__ == "__main__":
    main()