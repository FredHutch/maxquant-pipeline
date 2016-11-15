#!/usr/bin/python
"""
mqsubmit.py: submits a maxquant job to the cloud based automation pipeline
"""
import os
import optparse
import random
import re
import sys
import time
import boto3
import botocore
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
    threads = pickInstanceType(filePaths, mqparams)[1]
    cthreads = root.find('numThreads')
    cthreads.text = threads 

    # re-write the updated configuration with the updated path and thread changes
    tree.write(mqconfig)

    # MaxQuant is a Windows program after all
    os.popen("/usr/bin/unix2dos %s >> /dev/null 2>&1" % mqconfig)
    return datafiles, fastas


def pickInstanceType(fileList, mqparams):
    """
    Determine which type of EC2 instance should be used and how many threads to use 
    based on the number of datafiles the job has.
    """
    fileCount = len(fileList)
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
    elif fileCount <= 126:
        instanceType = "c4.8xlarge"
        if fileCount <= 36:
            threads = str(fileCount)
        else:
            threads = "36"
    elif fileCount >= 127 and mqparams['expedite']:
        instanceType = "x1.32xlarge"
        if fileCount <= 128:
            threads = str(fileCount)
        else:
            threads = "128"
    elif fileCount >= 127:
        instanceType = "c4.8xlarge"
        if fileCount <= 128:
            threads = str(fileCount)
        else:
            threads = "128"
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

def startWorker(mqBucket, mqparams, UserDataScript):
    """
    Create an job server in AWS/EC2. This process creates the server, installs maxquant and starts running the job (via user data script)
    """
    region = 'us-west-2'
    securityGroups = ['sg-a2dd8dc6']
    instanceType = mqparams['instanceType']
    subnetId = 'subnet-a95a0ede'
    # The volume should be twice the size of the datafiles (room for resutls) and padded 50GB for the OS.
    volumeSize = (getDataSize(mqparams['mzxmlFiles']) * 4) + 50 
    password = passwordGen(15)
    UserData = UserDataScript.format(bucket = mqBucket, jobFolder = "{0}-{1}".format(mqparams['department'], mqparams['jobName']), jobContact = mqparams['contactEmail'], password = password)
    image_id = find_image(region)
    #image_id = 'ami-59ba7139'  # hack until ThermoFisher MSFileReader can be packaged, when fixed delete this and uncomment line above
    instanceID = create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams)
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
    mqparams['expedite'] = parms.expedite

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
    mqparams['instanceType'] = pickInstanceType(mqparams['mzxmlFiles'], mqparams)[0]

    # Make sure that this is a uniqe job (department + jobname) so a previous jobs files in S3 don't get overwritten
    if checkJobAlreadyExists(mqBucket, jobFolder):
        print("\nThere is already an existing job named '{0}' for the '{1}' department/lab; choose a different job name and try again".format(mqparams['jobName'], mqparams['department']))
        sys.exit(1)

    # Upload all the jobs files to the S3 job folder
    uploadS3(mqBucket, jobFolder, mqparams, parms.mqconfig)
    
    # Fetch information about the job server to provide conection infomation if job summitted with the --connect option
    instanceID, password = startWorker(mqBucket, mqparams, UserDataScript)
    instanceIP = getInstanceIP('us-west-2', instanceID)

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


def create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams):
    """
    Creates, tags, and starts a MaxQuant worker instance
    """
    # Connect to AWS
    sys.stdout.write("\nConnecting to AWS EC2 Region {0}...".format(region))
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))
    print(" Done!")
    # Create an EC2 instance
    sys.stdout.write("\nCreating EC2 instance...")
    res = ec2.create_instances(
        ImageId = image_id,
        SubnetId = subnetId,
        MinCount = 1,
        MaxCount = 1,
        KeyName = 'rmcdermo-fredhutch_key',
        SecurityGroupIds = securityGroups,
        InstanceType = instanceType,
        Monitoring = {'Enabled': True},
        UserData = UserData,
        BlockDeviceMappings = [
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                        'VolumeSize': volumeSize,
                        'DeleteOnTermination': False,
                        'VolumeType': 'gp2'
                        }
            }],
        IamInstanceProfile={'Arn': 'arn:aws:iam::458818213009:instance-profile/maxquant'}
        )

    instanceId = res[0].id
    print(" Instance {0} created".format(instanceId))


    # Sleep for a bit to make sure the instances are ready to be tagged 
    time.sleep(15)

    # Tag the job server
    sys.stdout.write("\nTagging EC2 instance...")
    ec2.create_tags(Resources=["{0}".format(instanceId)],
        Tags=[{'Key': 'Name', 'Value': "maxquant-{0}-{1}".format(mqparams['department'], mqparams['jobName'])},
            {'Key': 'technical_contact', 'Value': mqparams['contactEmail']},
            {'Key': 'billing_contact', 'Value': mqparams['contactEmail']},
            {'Key': 'description', 'Value': 'Maxquant worker node'},
            {'Key': 'owner', 'Value': mqparams['department']},
            {'Key': 'sle', 'Value': 'hours=variable / grant=no / phi=no / pii=no / public=no'}
            ])
    print(" Done!")
    return instanceId


def getInstanceIP(region, instanceID):
    """
    Determine the IP address of the jobs server
    """
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))
    # Get instance object
    i = ec2.Instance(instanceID)
    # Get instance private IP
    ipAddr = i.private_ip_address
    return ipAddr


def find_image(region):
    """
    Finds the latest Windows 2012R2 offical Amazon AMI and returns the ID
    """
    sys.stdout.write("\nFinding latest Windows 2012R2 image...")
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))
    images = ec2.images.filter(
        Owners=['amazon'],
        Filters=[
            {'Name': 'name','Values': ['Windows_Server-2012-R2_RTM-English-64Bit-Base-*']},
            {'Name': 'state', 'Values': ['available']},
            {'Name': 'architecture', 'Values': ['x86_64']},
            {'Name': 'root-device-type', 'Values': ['ebs']},
            {'Name': 'virtualization-type', 'Values': ['hvm']},
            {'Name': 'platform', 'Values': ['windows']},
            ]
    )
    candidates = {}
    for image in images:
        candidates[image.creation_date] = image.image_id
    cDate = sorted(candidates.keys(), reverse=True)[0]
    ami = candidates[cDate]
    print(" Selected {0}".format(ami))
    return(ami)

"""
UserDataScipt: This is the PowerShell script that will be run on the Windows instance running in EC2. This script is the entire automation of the
remote process including installing software, pulling data, running the maxquant job, saving results and sending email to user.
"""
UserDataScript = """<powershell>
$bucket = '{bucket}'
$jobFolder = '{jobFolder}'
$jobContact = '{jobContact}'
# Set the local Administrator password
$ComputerName = $env:COMPUTERNAME
$user = [adsi]"WinNT://$ComputerName/Administrator,user"
$user.setpassword("{password}")
# Disable the Windows Firewall
Get-NetFirewallProfile | Set-NetFirewallProfile Enabled False -Confirm:$false
# Set the logon banner notice
$LegalNotice = "***  Warning  *** This system is for the exclusive use of authorized Fred Hutchinson Cancer Research Center employees and associates. Anyone using this system without authority, or in excess of their authority, is subject to having all of their activities on this system monitored and recorded by system administration staff. In the course of monitoring individuals improperly using this system, or in the course of system maintenance, the activities of authorized users may also be monitored. Anyone using this system expressly consents to such monitoring and is advised that if such monitoring reveals possible evidence of criminal activity, system administration staff may provide the evidence from such monitoring to law enforcement officials XXX."
[string]$reg = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
Set-ItemProperty -Path $reg -Name disablecad -Value 00000000 -Type DWORD -Force
Set-ItemProperty -Path $reg -Name dontdisplaylastusername -Value 00000001 -Type DWORD -Force
Set-ItemProperty -Path $reg -Name shutdownwithoutlogon -Value 00000000 -Type DWORD -Force
Set-ItemProperty -Path $reg -Name legalnoticecaption -Type STRING -Value "FHCRC Network Access Warning"  -Force
Set-ItemProperty -Path $reg -Name legalnoticetext -Type STRING -Value $LegalNotice -Force
#Rename the computer to match the provided instance name are reboot
Rename-Computer -NewName "maxquant-$jobFolder" -Force
Import-Module AwsPowerShell
Write-Host "Testing to see if bucket $bucket is present"
if (Test-S3Bucket -BucketName $bucket){{
Write-Host "Removing ready flag: $jobFolder/jobCtrl/ready.txt"
Remove-S3Object -BucketName $bucket -Key "$jobFolder/jobCtrl/ready.txt" -Force
Write-Host "Adding running flag: $jobFolder/jobCtrl/running.txt"
Write-S3Object -BucketName $bucket -Key "$jobFolder/jobCtrl/running.txt" -Content "running"
Write-Host "Downloading Thermo Fisher MSFileReader 3.0SP3"
Read-S3Object -BucketName 'fredhutch-maxquant' -Key 'MSFileReader_3.0SP3.msi' -File 'C:/MSFileReader_3.0SP3.msi'
Write-Host "Installing MSFileReader_3.0SP3.msi"
Start-Process "C:/MSFileReader_3.0SP3.msi" /qn -Wait
Write-Host "Downloading MaxQuant application"
Read-S3Object -BucketName 'fredhutch-maxquant' -Key 'MaxQuant_1.5.5.1.zip' -File 'C:/MaxQuant_1.5.5.1.zip'
$BackUpPath = 'C:/MaxQuant_1.5.5.1.zip'
$Destination = 'C:/'
Write-Host "Unzipping MaxQuant application"
Add-Type -assembly "system.io.compression.filesystem"
[io.compression.zipfile]::ExtractToDirectory($BackUpPath, $Destination)
Write-Host "Downloading job data and configuration from S3: $bucket/$jobFolder"
Read-S3Object -BucketName $bucket -KeyPrefix "$jobFolder" -Folder 'C:/mq-job'
if (Test-Path 'C:/mq-job/databases.xml') {{Copy-Item 'C:/mq-job/databases.xml' -Destination 'C:/MaxQuant/bin/conf/'}}
if (Test-Path 'C:/mq-job/modifications.xml') {{Copy-Item 'C:/mq-job/modifications.xml' -Destination 'C:/MaxQuant/bin/conf/'}}
Write-Host "Starting MaxQuant Job"
C:/MaxQuant/bin/MaxQuantCmd.exe C:/mq-job/mqpar.xml
Write-Host "Job complete, uploading job results to S3"
Write-S3Object -BucketName $bucket -KeyPrefix "$jobFolder/combined" -Folder 'C:/mq-job/combined' -Recurse
Write-Host "Removing running flag: $jobFolder/jobCtrl/running.txt"
Remove-S3Object -BucketName $bucket -Key "$jobFolder/jobCtrl/running.txt" -Force
Write-Host "Adding done flag: $jobFolder/jobCtrl/done.txt"
Write-S3Object -BucketName $bucket -Key "$jobFolder/jobCtrl/done.txt" -Content "done"
$resultsBundleFile = "maxquant-${{jobFolder}}-results-combined.zip"
Write-Host "Creating job result bundle: $resultsBundleFile"
$resultsBundlePath = "$env:TEMP/$resultsBundleFile"
Add-Type -assembly "system.io.compression.filesystem"
[io.compression.zipfile]::CreateFromDirectory("C:/mq-job/combined", $resultsBundlePath)
Write-Host "Uploading results bundle to S3: $jobFolder/$resultsBundleFile"
Write-S3Object -BucketName $bucket -Key "$jobFolder/$resultsBundleFile" -File $resultsBundlePath
Write-Host "Sending $jobContact a link to download the results from S3"
$resultsURL = Get-Content -path "C:/mq-job/jobCtrl/resultsUrl.txt"
$ExpirationDate = (Get-Date).AddDays(30)
#$resultsURL = Get-S3PreSignedURL -Verb GET -Expires $ExpirationDate -Bucket $bucket -Key "$jobFolder/$resultsBundleFile"
Send-MailMessage -SmtpServer "smtp.fhcrc.org" -From "maxquant-do-not-reply@fredhutch.org" -Body "Your MaxQuant job results are available for download:`n`n$resultsURL`n`nThis link will expire on $ExpirationDate" -Subject "Maxquant Job Results for job: $jobFolder (30 day download link)" -To $jobContact
Write-Host "All Done! Shutting down server..."
Stop-Computer -Force -Confirm:$false
}}
else {{
Write-Host -ForegroundColor Red "bucket not found"
}}
</powershell>
"""


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

    # If this flag is used it and the job has >= 127 data files, the very large X1 (128CPU, 2TB RAM) instance type will be used; only use if speed is more important than cost
    p.add_option('-x', '--expedite',  action='store_true', dest='expedite', help='[OPTIONAL] If used with a job containing 127+ data files, a very large server (128CPU) will be used; only use if speed is more important than cost')
    # the connect option is off by default 
    p.set_defaults(expedite=False)
    
    parms, args = p.parse_args()

    # Check to see ensure that the requried parameters where provided and that the datafiles exist in the job directory
    checkRequiredArguments(parms, p)

    # AWS API key for maxquant IAM user
    #os.environ["AWS_ACCESS_KEY_ID"] = "KEY GOES HERE"
    #os.environ["AWS_SECRET_ACCESS_KEY"] = "SECRET KEY GOES HERE"

    # Start the job
    main(parms)
