#!/usr/bin/python
"""
mq-ec2worker.py: create, bootstrap a MaxQuant EC2 instance and start a job
"""
import boto3
import sys
import time

region = 'us-west-2'
securityGroups = ['sg-a2dd8dc6']
instanceType = "m4.large"
subnetId = 'subnet-a95a0ede'
volumeSize = 100

UserData = """<powershell>
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
Send-MailMessage -SmtpServer "mx.fhcrc.org" -From "maxquant-do-not-reply@fredhutch.org" -Body "Your MaxQuant job results are available for download:`n`n$resultsURL`n`nThis link will expire on $ExpirationDate" -Subject "Maxquant Job Results for job: $jobFolder (30 day download link)" -To $jobContact
Write-Host "All Done! Shutting down server..."
Stop-Computer -Force -Confirm:$false
}}
else {{
Write-Host -ForegroundColor Red "bucket not found"
}}
</powershell>
"""

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


def main():
    image_id = find_image(region)
    create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams)

if __name__ == "__main__":
    main()
