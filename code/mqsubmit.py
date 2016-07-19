#!/usr/bin/python
"""
mqsubmit.py: submits a maxquant job to the cloud based automation pipeline
"""
import os
import sys
import random
import yaml
import boto3
import botocore
import mqEC2worker
import xml.etree.ElementTree as ET

def parseConfig(config):
    """
    Parses a YAML formated MaxQuant job configuration file, formats the text of
    the variables and returns the configuration parameters in a dictionary
    """
    try:
        with open(config, 'r') as f:
            mqparams = yaml.load(f)

        # Parse and format the list of imput mzXML files. As returns the formated 'experiments', 'fractions' and 'paramGroupIndices' parameters
        mqparams['jobName'] = mqparams['jobName'].strip()
        mqparams['department'] = mqparams['department'].strip()
        mqparams['contactEmail'] = mqparams['contactEmail'].strip()

        # return a dictionary of formated MQ parameters.
        return mqparams
    except:
        raise Exception("Error opening or parsing configuration file: {0}".format(config) )

def adjustConfig(mqconfig, mqdir, mqparams):
    tree = ET.parse(mqconfig)
    root = tree.getroot()

    datafiles = []
    for filePaths in root.findall('filePaths'):
        files = filePaths.findall('string')
        for d in files:
            dfile = (d.text).split('\\')[-1]
            datafiles.append(dfile)
            dpath = mqdir + dfile
            d.text = dpath 

    fastas = []
    for fastaFiles in root.findall('fastaFiles'):
        fasta = fastaFiles.findall('string')
        for f in fasta:
            ffile = (f.text).split('\\')[-1]
            fastas.append(ffile) 
            fpath = mqdir + ffile
            f.text = fpath 
    
    threads = pickInstanceType(filePaths)[1]
    cthreads = root.find('numThreads')
    cthreads.text = threads 

    tree.write(mqconfig)
    os.popen("/usr/bin/unix2dos %s >> /dev/null 2>&1" % mqconfig)
    return datafiles, fastas


def pickInstanceType(mzxmlFiles):
    fileCount = len(mzxmlFiles)
    if fileCount <= 2:
        instanceType = "c4.large"
        threads = str(fileCount)
    elif fileCount <= 4:
        instanceType = "c4.xlarge"
        threads = str(fileCount)
    elif fileCount <= 8:
        instanceType = "c4.2xlarge"
        threads = str(fileCount)
    elif fileCount <= 16:
        instanceType = "c4.4xlarge"
        threads = str(fileCount)
    elif fileCount >= 17:
        instanceType = "c4.8xlarge"
        if fileCount <= 36:
            threads = str(fileCount)
        else:
            threads = "36"
    return instanceType, threads

def getDataSize(datafiles):
    total_size = 0 
    for f in datafiles:
        if os.path.isfile(f):
            total_size += os.path.getsize(f)
    return total_size / 1000 / 1000 / 1000

def passwordGen(plength):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!'
    p = []
    for char in range(plength):
        p.append(random.choice(chars))
    return(''.join(p))


def checkJobAlreadyExists(mqBucket, jobFolder):
    """
    Check to see if the job already exists to avoid overwritting it
    """
    s3 = boto3.resource('s3', 'us-west-2')
    exists = False
    try:
        s3.Object(mqBucket, "{0}/mq-job.xml".format(jobFolder)).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            exists = False
        else:
            raise e
    else:
        exists = True
    return exists

def uploadS3(mqBucket, jobFolder, mqparams, mqconfig):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    print("\nUploading data file(s)...")
    for f in mqparams['mzxmlFiles']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    print("\nUploading FASTA file(s)...".format(configIn))
    for f in mqparams['fastaFiles']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    sys.stdout.write("\nUploading configuration file...")
    transfer.upload_file(mqconfig, mqBucket, "{0}/{1}".format(jobFolder, mqconfig))
    print(" Done!")

    # If a custom database was provided, upload it to the job folder in S3
    if 'database' in mqparams:
        sys.stdout.write("\nUploading custom databases.xml file...")
        transfer.upload_file(mqparams['database'], mqBucket, "{0}/{1}".format(jobFolder, mqparams['database']))
        print(" Done!")

    sys.stdout.write("\nSetting Job Ready Flag...")
    client.put_object(Body="{0},{1},{2}".format(mqparams['jobName'], mqparams['department'], mqparams['contactEmail']), Bucket = mqBucket, Key="{0}/jobCtrl/jobinfo.txt".format(jobFolder))
    client.put_object(Body="ready", Bucket = mqBucket, Key="{0}/jobCtrl/ready.txt".format(jobFolder))
    resultsUrl = genTempUrl(mqBucket, jobFolder).strip()
    client.put_object(Body = resultsUrl, Bucket = mqBucket, Key="{0}/jobCtrl/resultsUrl.txt".format(jobFolder))
    print(" Done!")

def startWorker(mqBucket, mqparams):
    region = 'us-west-2'
    securityGroups = ['sg-a2dd8dc6']
    instanceType = mqparams['instanceType']
    subnetId = 'subnet-a95a0ede'
    #volumeSize = 100
    volumeSize = (getDataSize(mqparams['mzxmlFiles']) * 2) + 50 
    password = passwordGen(15)
    UserData = mqEC2worker.UserData.format(bucket = mqBucket, jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName']), jobContact = mqparams['contactEmail'], password = password)
    image_id = mqEC2worker.find_image(region)
    instanceID = mqEC2worker.create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams)
    return instanceID, password

def genTempUrl(mqBucket, jobFolder):
    client = boto3.client('s3')
    expiresIn = 2937600 # 34 days
    resultsBundleFile = "maxquant-{0}-results-combined.zip".format(jobFolder)
    url = client.generate_presigned_url('get_object', Params = {'Bucket': mqBucket, 'Key': "{0}/{1}".format(jobFolder, resultsBundleFile)}, ExpiresIn = expiresIn)
    return url

def main(configIn, mqconfig):
    """
    When run stand-alone (not imported), execution starts here
    """
    sys.stdout.write("Parsing job configuration file: {0}...".format(configIn))
    mqparams = parseConfig(configIn)
    print(" Done!")

    # If a custom 'databases.xml' file is found alongside the job, include it.
    if os.path.isfile("databases.xml"):
        print("Found custom 'databases.xml' file...")
        mqparams['database'] = "databases.xml"


    mqBucket = "fredhutch-maxquant-jobs"
    mqdir = "c:\\mq-job\\"
    jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName'])
    
    sys.stdout.write("Adjusting MaxQuant configuration file: {0}...".format(mqconfig))
    datafiles, fastas = adjustConfig(mqconfig, mqdir, mqparams)
    print(" Done!")

    mqparams['mzxmlFiles'] = [e.strip() for e in datafiles]
    mqparams['fastaFiles'] = [e.strip() for e in fastas]
    mqparams['instanceType'] = pickInstanceType(mqparams['mzxmlFiles'])[0]

    if checkJobAlreadyExists(mqBucket, jobFolder):
        print("\nThere is already an existing job named '{0}' for the '{1}' department/lab; choose a different job name and try again".format(mqparams['jobName'], mqparams['department']))
        sys.exit(1)
    uploadS3(mqBucket, jobFolder, mqparams, mqconfig)
    instanceID, password = startWorker(mqBucket, mqparams)
    instanceIP = mqEC2worker.getInstanceIP('us-west-2', instanceID)
    print("\nYour MaxQuant job has been successfully submitted. An email will be sent to {0} when complete with a link to download the results".format(mqparams['contactEmail']))
    print("\nIf you would like to RDP into the running MaxQuant instance to watch (do not interupt) the progress of your job, here is the information you need:")
    print("\tServer: {0}".format(instanceIP))
    print("\tUsername: {0}".format("Administrator"))
    print("\tDomain: {0}".format("None - leave blank"))
    print("\tPassword: {0}".format(password))
    print("\tStatus files: {0}".format('C:\\mq-job\\combined\\proc\\*'))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: mqsubmit <inputYAMLconfigFile>")
        sys.exit(1)
    else:
        configIn = sys.argv[1].strip()
        mqconfig = 'mqpar.xml'
        main(configIn, mqconfig)
