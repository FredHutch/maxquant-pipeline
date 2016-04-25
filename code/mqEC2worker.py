#!/usr/bin/python
"""
mq-ec2worker.py: create, bootstrap a MaxQuant EC2 instance and start a job
"""
import boto3
import time

region = 'us-west-2'
securityGroups = ['sg-a2dd8dc6']
instanceType = "m4.large"
subnetId = 'subnet-a95a0ede'
volumeSize = 100

UserData = """<powershell>
# Set the local Administrator password
$ComputerName = $env:COMPUTERNAME
$user = [adsi]"WinNT://$ComputerName/Administrator,user"
$user.setpassword("password goes here")
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
# Rename the computer to match the provided instance name are reboot
Rename-Computer -NewName maxquant-aws -Force
Import-Module AwsPowerShell
Test-S3Bucket -BucketName 'fredhutch-maxquant'
Write-S3Object -BucketName 'fredhutch-maxquant' -Key 'jobctrl/running.txt' -Content "job 43 running"
Read-S3Object -BucketName 'fredhutch-maxquant' -Key 'MaxQuant_1.5.3.30.zip' -File 'C:/MaxQuant_1.5.3.30.zip'
$BackUpPath = 'C:/MaxQuant_1.5.3.30.zip'
$Destination = 'C:/'
Add-Type -assembly "system.io.compression.filesystem"
[io.compression.zipfile]::ExtractToDirectory($BackUpPath, $Destination)
Read-S3Object -BucketName 'fredhutch-maxquant' -KeyPrefix 'DATA.dist' -Folder 'c:\mq-job'
C:/MaxQuant/bin/MaxQuantCmd.exe C:/mq-job/mq-job.xml
Write-S3Object -BucketName 'fredhutch-maxquant-jobs' -KeyPrefix 'combined' -Folder 'C:/mq-job/combined' -Recurse
Remove-S3Object -BucketName 'fredhutch-maxquant' -Key 'jobctrl/running.txt' -Force
Write-S3Object -BucketName 'fredhutch-maxquant' -Key 'jobctrl/done.txt' -Content "done"
Stop-Computer -Force -Confirm:$false
</powershell>
"""

def create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData, mqparams):
    """
    Creates, tags, and starts a MaxQuant worker instance
    """

    # Connect to AWS
    print("Connecting to AWS EC2 Region {0}".format(region))
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))

    # Create an EC2 instance
    print("Creating EC2 instance")
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
    print("Instance created: {0}".format(instanceId))


    # Tag the EC2 instance
    time.sleep(10)
    print("Tagging EC2 instance")
    ec2.create_tags(Resources=["{0}".format(instanceId)],
        Tags=[{'Key': 'Name', 'Value': "maxquant-{0}-{1}".format(mqparams['department'], mqparams['jobName'])},
            {'Key': 'technical_contact', 'Value': mqparams['contactEmail']},
            {'Key': 'billing_contact', 'Value': mqparams['contactEmail']},
            {'Key': 'description', 'Value': 'Maxquant worker node'},
            {'Key': 'owner', 'Value': mqparams['department']},
            {'Key': 'sle', 'Value': 'hours=variable / grant=no / phi=no / pii=no / public=no'}
            ])

def find_image(region):
    """
    Finds the latest Windows 2012R2 offical Amazon AMI and returns the ID
    """
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
    return(ami)

def main():
    image_id = find_image(region)
    create_ec2worker(region, image_id, securityGroups, instanceType, subnetId, volumeSize, UserData)

if __name__ == "__main__":
    main()
