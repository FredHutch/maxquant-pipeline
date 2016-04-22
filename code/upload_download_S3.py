#!/usr/bin/python
import boto3

mqBucket = "fredhutch-maxquant-jobs"
jobFolder = "rmcdermo484848"

def main():
    upload2(mqBucket, jobFolder)
    download2(mqBucket, jobFolder)

# standard single part, single thread upload
def upload(mqBucket, jobFolder):
    s3 = boto3.resource('s3', "us-west-2")
    bucket = s3.Bucket(mqBucket)
    bucket.upload_file('test.xml', "{0}/test.xml".format(jobFolder))

# standard single part, single thread download
def download(mqBucket, jobFolder):
    s3 = boto3.resource('s3', "us-west-2")
    bucket = s3.Bucket(mqBucket)
    bucket.download_file("{0}/test.xml".format(jobFolder), 'test-copy.xml')

# multipart, parallel upload
def upload2(mqBucket, jobFolder):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    transfer.upload_file('myfile.bin', mqBucket, "{0}/myfile.bin".format(jobFolder))

# multipart, parallel download
def download2(mqBucket, jobFolder):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    transfer.download_file(mqBucket, "{0}/myfile.bin".format(jobFolder), 'myfile2.bin')

if __name__ == "__main__":
    main()
