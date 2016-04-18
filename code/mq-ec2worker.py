#!/usr/bin/python
"""
mq-ec2worker.py: create, bootstrap a MaxQuant EC2 instance and start a job
"""
import boto3
import base64
import time

region = 'us-west-2'
ami = 'ami-1719f677'
securityGroups = ['sg-a2dd8dc6']
instanceType = "t2.small"
subnetId = 'subnet-a95a0ede'
volumeSize = 75

UserData = """<powershell>
# Set the local Administrator password
$ComputerName = $env:COMPUTERNAME
$user = [adsi]"WinNT://$ComputerName/Administrator,user"
$user.setpassword("********")
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
</powershell>
"""

def create_ec2worker():
    """
    Creates, tags, and starts a MaxQuant worker instance
    """

    # Connect to AWS
    print("Connecting to AWS EC2 Region {0}".format(region))
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))

    # Create an EC2 instance
    print("Creating EC2 instance")
    res = ec2.create_instances(
        ImageId = ami,
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
        Tags=[{'Key': 'Name', 'Value': 'maxquant-aws'},
            {'Key': 'technical_contact', 'Value': 'rmcdermo@fredhutch.org'},
            {'Key': 'billing_contact', 'Value': 'cloudops@fredhutch.org'},
            {'Key': 'description', 'Value': 'Maxquant worker node'},
            {'Key': 'owner', 'Value': '_adm/scicomp'},
            {'Key': 'sle', 'Value': 'hours=variable / grant=no / phi=no / pii=no / public=no'}
            ])


def main():
    create_ec2worker()

if __name__ == "__main__":
    main()
