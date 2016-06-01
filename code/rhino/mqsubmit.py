#!/usr/bin/python
"""
mqconfig.py: Converts YAML MaxQaunt job configuration to an XML configuration format suitable for running a job
"""
import os
import sys
import random
import yaml
import boto3
import botocore
import mqEC2worker

def parseConfig(config):
    """
    Parses a YAML formated MaxQuant job configuration file, formats the text of
    the variables and returns the configuration parameters in a dictionary
    """
    try:
        with open(config, 'r') as f:
            mqparams = yaml.load(f)

        # Parse and format the list of imput mzXML files. As returns the formated 'experiments', 'fractions' and 'paramGroupIndices' parameters
        mzxmlFiles = [e.strip() for e in mqparams['mzxmlFiles'].split(',')]
        mqparams['mzxmlFilesRaw'] = [e.strip() for e in mqparams['mzxmlFiles'].split(',')]
        mqparams['mzxmlFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>C:/mq-job/{0}</string>".format(x), mzxmlFiles))
        mqparams['experiments'] = "\n".join(map(lambda x: " " * 8 + "<string/>", mzxmlFiles))
        mqparams['fractions'] = "\n".join(map(lambda x: " " * 8 + "<short>32767</short>", mzxmlFiles))
        mqparams['paramGroupIndices'] = "\n".join(map(lambda x: " " * 8 + "<int>0</int>", mzxmlFiles))

        # Parse and format the list of fasta files.
        fastaFiles = [e.strip() for e in mqparams['fastaFiles'].split(',')]
        mqparams['fastaFilesRaw'] = [e.strip() for e in mqparams['fastaFiles'].split(',')]
        mqparams['fastaFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>C:/mq-job/{0}</string>".format(x), fastaFiles))

        # Parse and format the heavy labels.
        heavyLabels = ";".join([e.strip() for e in mqparams['heavyLabels'].split(',')])
        mqparams['heavyLabels'] = " " * 12 + "<string>{0}</string>".format(heavyLabels)

        # Parse and format the variable modifications.
        variableModifications = [e.strip() for e in mqparams['variableModifications'].split(',')]
        mqparams['variableModifications'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), variableModifications))

        # Parse and format the enzymes.
        enzymes = [e.strip() for e in mqparams['enzymes'].split(',')]
        mqparams['enzymes'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), enzymes))

        # Parse and format the fixed modifications.
        fixedModifications = [e.strip() for e in mqparams['fixedModifications'].split(',')]
        mqparams['fixedModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), fixedModifications))

        # Parse and format the restriction modifications.
        restrictionModifications = [e.strip() for e in mqparams['restrictionModifications'].split(',')]
        mqparams['restrictionModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), restrictionModifications))

        mqparams['multiplicity'] = str(mqparams['multiplicity']).strip()
        mqparams['threads'] = pickInstanceType(mqparams['mzxmlFilesRaw'])[1]
        mqparams['instanceType'] = pickInstanceType(mqparams['mzxmlFilesRaw'])[0]
        mqparams['jobName'] = mqparams['jobName'].strip()
        mqparams['department'] = mqparams['department'].strip()
        mqparams['contactEmail'] = mqparams['contactEmail'].strip()

        # return a dictionary of formated MQ parameters.
        return mqparams
    except:
        raise Exception("Error opening or parsing configuration file: {0}".format(config) )

def pickInstanceType(mzxmlFilesRaw):
    fileCount = len(mzxmlFilesRaw)
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

def createMqConfig(mqparams, template):
    """
    Takes a dictionary of decorated MaxQuant job parameters and renders and
    returns a MaxQuant job configuration in the requried XML format
    """
    mqconfig = template.format(**mqparams)
    return mqconfig


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

def uploadS3(mqBucket, jobFolder, mqparams, configOut):
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    print("\nUploading MZXML file(s)...".format(configIn))
    for f in mqparams['mzxmlFilesRaw']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    print("\nUploading FASTA file(s)...".format(configIn))
    for f in mqparams['fastaFilesRaw']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    sys.stdout.write("\nUploading configuration file...")
    transfer.upload_file(configOut, mqBucket, "{0}/{1}".format(jobFolder, configOut))
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
    volumeSize = (getDataSize(mqparams['mzxmlFilesRaw']) * 2) + 50 
    password = passwordGen(15)
    UserData = mqEC2worker.UserData.format(bucket = mqBucket, jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName']), jobContact = mqparams['contactEmail'], password = password)
    image_id = mqEC2worker.find_image(region)
    mqEC2worker.create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams)

def genTempUrl(mqBucket, jobFolder):
    client = boto3.client('s3')
    expiresIn = 2937600 # 34 days
    resultsBundleFile = "maxquant-{0}-results-combined.zip".format(jobFolder)
    url = client.generate_presigned_url('get_object', Params = {'Bucket': mqBucket, 'Key': "{0}/{1}".format(jobFolder, resultsBundleFile)}, ExpiresIn = expiresIn)
    return url

def main(configIn, template):
    """
    When run stand-alone (not imported), execution starts here
    """
    sys.stdout.write("Parsing job configuration file: {0}...".format(configIn))
    mqparams = parseConfig(configIn)
    print(" Done!")
    configOut = "mq-job.xml"
    sys.stdout.write("Generating MaxQuant configuration file: {0}...".format(configOut))
    template = open(template).read()
    mqconfig = createMqConfig(mqparams, template)
    with open(configOut, 'w') as out:
        out.write(mqconfig)
    print(" Done!")
    mqBucket = "fredhutch-maxquant-jobs"
    jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName'])
    if checkJobAlreadyExists(mqBucket, jobFolder):
        print("\nThere is already an existing job named '{0}' for the '{1}' department/lab; choose a different job name and try again".format(mqparams['jobName'], mqparams['department']))
        sys.exit(1)
    uploadS3(mqBucket, jobFolder, mqparams, configOut)
    startWorker(mqBucket, mqparams)
    print("\nYour MaxQuant job has been successfully submitted. An email will be sent to {0} when complete with a link to download the results".format(mqparams['contactEmail']))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: mqsubmit <inputYAMLconfigFile>")
        sys.exit(1)
    else:
        configIn = sys.argv[1].strip()
        template = '/app/maxquant/0.1/mqpar.xml.template'
        os.environ["AWS_ACCESS_KEY_ID"] = "AKIAJXDAQMSHTP4UGB3A"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "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"
        main(configIn, template)
