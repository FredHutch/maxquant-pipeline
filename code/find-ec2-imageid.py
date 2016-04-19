# Find the latest Windows 2012R2 Amazon supported AMI
import boto3

ec2 = boto3.resource('ec2', region_name = 'us-west-2')
#images = ec2.images.all()

images = ec2.images.filter(
    Owners=[
        'amazon'
    ],
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

print(ami)
