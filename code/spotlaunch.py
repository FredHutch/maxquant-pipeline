import boto3
import datetime

client = boto3.client('ec2')
response = client.request_spot_instances(
    DryRun=False,
    SpotPrice='0.193',
    ClientToken='maxquant',
    InstanceCount=1,
    Type='one-time',
    LaunchSpecification={
        'ImageId': 'ami-2827f548',
        'KeyName': 'rmcdermo-fredhutch_key',
        'InstanceType': 'c4.large',
        'SubnetId': 'subnet-a95a0ede',
        'Placement': {
            'AvailabilityZone': 'us-west-2a',
        },
        'BlockDeviceMappings': [
            {
                'DeviceName': '/dev/sda1',
                'Ebs': {
                        'VolumeSize': 50,
                        'DeleteOnTermination': False,
                        'VolumeType': 'gp2'
                        }
            }
        ],
        'Monitoring': {
            'Enabled': True
        },
        'SecurityGroupIds': [
            'sg-a2dd8dc6'
        ]
    }
)
