#!/usr/bin/python
"""
mqsubmit.py: submits a maxquant job to the cloud based automation pipeline
"""
import os
import optparse
import sys
import random
import re
import yaml
import boto3
import botocore
import mqEC2worker
import xml.etree.ElementTree as ET


def adjustConfig(mqconfig, mqdir, mqparams):
    """
    Takes the MaxQuant GUI generated XML configuration file and updates the data and fasta file paths so they
    are changed from where they where when created, to where they are going to be on the Cloud server. It also
    sets the mumber threads that will be used on the cloud server to run the job.
    It returns a list of the datafiles and a list of the fasta files for the purpose of the S3 uploads
    """
    tree = ET.parse(mqconfig)
    root = tree.getroot()

    # Get list of datafiles (mzXML and RAW) and fix the file paths
    datafiles = []
    for filePaths in root.findall('filePaths'):
        files = filePaths.findall('string')
        for d in files:
            dfile = (d.text).split('\\')[-1]
            datafiles.append(dfile)
            dpath = mqdir + dfile
            d.text = dpath 

    # Get list of fasta files and fix the file paths
    fastas = []
    for fastaFiles in root.findall('fastaFiles'):
        fasta = fastaFiles.findall('string')
        for f in fasta:
            ffile = (f.text).split('\\')[-1]
            fastas.append(ffile) 
            fpath = mqdir + ffile
            f.text = fpath 
    
    # how many threads should the job use
    threads = pickInstanceType(filePaths)[1]
    cthreads = root.find('numThreads')
    cthreads.text = threads 

    # re-write the updated configuration with the updated path and thread changes
    tree.write(mqconfig)

    # MaxQuant is a Windows program after all
    os.popen("/usr/bin/unix2dos %s >> /dev/null 2>&1" % mqconfig)
    return datafiles, fastas


def pickInstanceType(mzxmlFiles):
    """
    Determine which type of EC2 instance should be used and how many threads to use 
    based on the number of datafiles the job has.
    """
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
    """
    Determine the total size of the data files in this job. This information is used to
    calculate the size of the EBS volume attached to the job server.
    """
    total_size = 0 
    for f in datafiles:
        if os.path.isfile(f):
            total_size += os.path.getsize(f)
    return total_size / 1000 / 1000 / 1000


def passwordGen(plength):
    """
    Generate a random string suitable for use as a password. This is used later to generate a password for the
    local Administrator account on the job server. 
    """
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
        s3.Object(mqBucket, "{0}/mqpar.xml".format(jobFolder)).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            exists = False
        else:
            raise e
    else:
        exists = True
    return exists

def uploadS3(mqBucket, jobFolder, mqparams, mqconfig):
    """
    Upload the datafiles, fastafiles, configuration file, etc... needed by the job to
    the job folder in the maxquant-jobs S3 bucket
    """
    client = boto3.client('s3', 'us-west-2')
    transfer = boto3.s3.transfer.S3Transfer(client)
    print("\nUploading data file(s)...")
    for f in mqparams['mzxmlFiles']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    print("\nUploading FASTA file(s)...".format(mqconfig))
    for f in mqparams['fastaFiles']:
        sys.stdout.write("\tUploading: {0}...".format(f))
        transfer.upload_file(f, mqBucket, "{0}/{1}".format(jobFolder, f))
        print(" Done!")
    sys.stdout.write("\nUploading configuration file...")
    transfer.upload_file(mqconfig, mqBucket, "{0}/{1}".format(jobFolder, "mqpar.xml"))
    print(" Done!")

    # If a custom database was provided, upload it to the job folder in S3
    if 'database' in mqparams:
        sys.stdout.write("\nUploading custom databases.xml file...")
        transfer.upload_file(mqparams['database'], mqBucket, "{0}/{1}".format(jobFolder, mqparams['database']))
        print(" Done!")

    # If a custom modifications file was provided, upload it to the job folder in S3
    if 'modifications' in mqparams:
        sys.stdout.write("\nUploading custom modifications.xml file...")
        transfer.upload_file(mqparams['modifications'], mqBucket, "{0}/{1}".format(jobFolder, mqparams['modifications']))
        print(" Done!")

    sys.stdout.write("\nSetting Job Ready Flag...")
    # Create a file object that contains metadata about the job
    client.put_object(Body="{0},{1},{2}".format(mqparams['jobName'], mqparams['department'], mqparams['contactEmail']), Bucket = mqBucket, Key="{0}/jobCtrl/jobinfo.txt".format(jobFolder))
    # Create a file object signaling that the job is ready to run
    client.put_object(Body="ready", Bucket = mqBucket, Key="{0}/jobCtrl/ready.txt".format(jobFolder))
    # Precalcuate and generate a temp url to the not yet created results and save it in a text file to use when job is complete 
    resultsUrl = genTempUrl(mqBucket, jobFolder).strip()
    client.put_object(Body = resultsUrl, Bucket = mqBucket, Key="{0}/jobCtrl/resultsUrl.txt".format(jobFolder))
    print(" Done!")

def startWorker(mqBucket, mqparams):
    """
    Create an job server in AWS/EC2. This process creates the server, installs maxquant and starts running the job (via user data script)
    """
    region = 'us-west-2'
    securityGroups = ['sg-a2dd8dc6']
    instanceType = mqparams['instanceType']
    subnetId = 'subnet-a95a0ede'
    # The volume should be twice the size of the datafiles (room for resutls) and padded 50GB for the OS.
    volumeSize = (getDataSize(mqparams['mzxmlFiles']) * 2) + 50 
    password = passwordGen(15)
    UserData = mqEC2worker.UserData.format(bucket = mqBucket, jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName']), jobContact = mqparams['contactEmail'], password = password)
    image_id = mqEC2worker.find_image(region)
    #image_id = 'ami-59ba7139'  # hack until ThermoFisher MSFileReader can be packaged, when fixed delete this and uncomment line above
    instanceID = mqEC2worker.create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams)
    return instanceID, password

def genTempUrl(mqBucket, jobFolder):
    """
    Generate a temporary signed URL to the results bundle
    """
    client = boto3.client('s3')
    expiresIn = 2937600 # 34 days
    resultsBundleFile = "maxquant-{0}-results-combined.zip".format(jobFolder)
    url = client.generate_presigned_url('get_object', Params = {'Bucket': mqBucket, 'Key': "{0}/{1}".format(jobFolder, resultsBundleFile)}, ExpiresIn = expiresIn)
    return url


def checkfiles(files):
    """
    Check to see if the files exists before attempting to upload
    """
    missing = []
    for f in files:
        if not os.path.isfile(f):
            missing.append(f)
    if missing:
        print("Error: the following files were not found in the job directory:")
        for m in missing:
            print("\t{0}".format(m))
        sys.exit(1)


def main(parms):
    """
    Program execution starts and is driven from this function
    """
    mqparams = {}
    # Store the job metadata provided via command-line parameters in the mqparams dict that will hold all info about the job
    mqparams['jobName'] = parms.jobname.strip().replace(' ','')
    mqparams['department'] = parms.department.strip().replace(' ','')
    mqparams['contactEmail'] = parms.contact.strip().replace(' ','')

    # If a custom 'databases.xml' file is found in the job submission directory, include it.
    if os.path.isfile("databases.xml"):
        print("Found custom 'databases.xml' file...")
        mqparams['database'] = "databases.xml"

    # If a custom 'modifications.xml' file is found in the job submission directory, include it.
    if os.path.isfile("modifications.xml"):
        print("Found custom 'modifications.xml' file...")
        mqparams['modifications'] = "modifications.xml"

    # This is the top-level S3 bucket that all job folders will live under
    mqBucket = "fredhutch-maxquant-jobs"
    # The job files will be uploaded and run in this directory on the job server
    mqdir = "c:\\mq-job\\"
    # The job folder in S3 that will hold the data/results (child of the maxquant jobs bucket)
    jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName'])
    
    sys.stdout.write("Adjusting MaxQuant configuration file: {0}...".format(parms.mqconfig))
    
    # Adjust the config file (update paths, threads)
    datafiles, fastas = adjustConfig(parms.mqconfig, mqdir, mqparams)
    print(" Done!")

    # Check to see that the data and fasta files listed in the maxquant configuration file (XML) are located in the job directory
    checkfiles(datafiles)
    checkfiles(fastas)

    # Store the file inventory and calculated instance type in the mq job dictionary
    mqparams['mzxmlFiles'] = [e.strip() for e in datafiles]
    mqparams['fastaFiles'] = [e.strip() for e in fastas]
    mqparams['instanceType'] = pickInstanceType(mqparams['mzxmlFiles'])[0]

    # Make sure that this is a uniqe job (department + jobname) so a previous jobs files in S3 don't get overwritten
    if checkJobAlreadyExists(mqBucket, jobFolder):
        print("\nThere is already an existing job named '{0}' for the '{1}' department/lab; choose a different job name and try again".format(mqparams['jobName'], mqparams['department']))
        sys.exit(1)

    # Upload all the jobs files to the S3 job folder
    uploadS3(mqBucket, jobFolder, mqparams, parms.mqconfig)
    
    # Fetch information about the job server to provide conection infomation if job summitted with the --connect option
    instanceID, password = startWorker(mqBucket, mqparams)
    instanceIP = mqEC2worker.getInstanceIP('us-west-2', instanceID)

    print("\nYour MaxQuant job has been successfully submitted. An email will be sent to {0} when complete with a link to download the results".format(mqparams['contactEmail']))

    # If they specified they want server connection info (-c or --connect), print it.
    if parms.connect:
        print("\nIf you would like to RDP into the running MaxQuant instance to watch (do not interupt) the progress of your job, here is the information you need:")
        print("\tServer: {0}".format(instanceIP))
        print("\tUsername: {0}".format("Administrator"))
        print("\tDomain: {0}".format("None - leave blank"))
        print("\tPassword: {0}".format(password))
        print("\tStatus files: {0}".format('C:\\mq-job\\combined\\proc\\*'))


def checkRequiredArguments(parms, p):
    """
    Check to make sure all required parameters where provided and the data/fasta file defined in the maxquant
    configuration are in the job directy.
    """
    missing_options = []
    for option in p.option_list:
        if re.match(r'^\[REQUIRED\]', option.help) and eval('parms.' + option.dest) == None:
            missing_options.extend(option._long_opts)
    
    if len(missing_options) > 0:
        p.error('Missing REQUIRED parameters: ' + str(missing_options))
    
    if not os.path.isfile(parms.mqconfig):
        p.error("Can't find specified MaxQuant configuration file {0}".format(parms.mqconfig))


if __name__ == "__main__":
    p = optparse.OptionParser()
    
    # Get the filename of the XML formated maxquant configuration file that was generated by the MaxQuant GUI
    p.add_option('-m', '--mqconfig',  action='store', type='string', dest='mqconfig', help='[REQUIRED] Filename of the MaxQuant .XML configuration file')
    
    # get the name of the maxquant job
    p.add_option('-n', '--jobname',  action='store', type='string', dest='jobname', help='[REQUIRED] The name of the maxquant job you are running')
    
    # get the name of their department/lab
    p.add_option('-d', '--department',  action='store', type='string', dest='department', help='[REQUIRED] The name of your department or lab')
    
    # get their email address so you can email them links to the results
    p.add_option('-e', '--email',  action='store', type='string', dest='contact', help='[REQUIRED] Your email address; needed so you can receive a results link')
    
    # If this flag is used it will print the information needed to connect to the remote maxquant server.
    p.add_option('-c', '--connect',  action='store_true', dest='connect', help='[OPTIONAL] Prints connection information so you can check on the running job')
    
    # the connect option is off by default 
    p.set_defaults(connect=False)
    
    parms, args = p.parse_args()

    # Check to see ensure that the requried parameters where provided and that the datafiles exist in the job directory
    checkRequiredArguments(parms, p)

    # AWS API key for maxquant IAM user
    os.environ["AWS_ACCESS_KEY_ID"] = "your api key goes here"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "your secret key goes here"

    # Start the job
    main(parms)
