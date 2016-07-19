#!/usr/bin/python
import boto3

def getEc2Info(region, instanceID):
    # Connect to AWS
    ec2 = boto3.resource('ec2', region_name = "{0}".format(region))

    # Get instance object
    i = ec2.Instance(instanceID)

    # Print some info about the instance
    print("State: {0}".format(i.state['Name']))
    print("Private IP: {0}".format(i.private_ip_address))
    print("Launch time: {0}".format(i.launch_time))

def main():
    region = 'us-west-2'
    instanceID = 'i-f9837f6d'
    getEc2Info(region, instanceID) 

if __name__ == "__main__":
    main()
