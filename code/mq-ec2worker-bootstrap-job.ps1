# The system must be configured to allow running powershell scripts
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Force -Confirm:$false

# Import the AWS PowserShell module
Import-Module AwsPowerShell

# Test to see that the bucket exists
Test-S3Bucket -BucketName 'fredhutch-maxquant'

# Create a text object the bucket
Write-S3Object -BucketName 'fredhutch-maxquant' -Key 'jobctrl/running.txt' -Content "job 43 running"

# Download MaxQuant application
Read-S3Object -BucketName 'fredhutch-maxquant' -Key 'MaxQuant_1.5.3.30.zip' -File 'C:\MaxQuant_1.5.3.30.zip'

# Unzip the MaxQuant Application
$BackUpPath = 'C:\MaxQuant_1.5.3.30.zip'
$Destination = 'C:\'
#Add-Type -assembly “system.io.compression.filesystem”
[io.compression.zipfile]::ExtractToDirectory($BackUpPath, $destination)

# Download the maxquant job data
Read-S3Object -BucketName 'fredhutch-maxquant' -KeyPrefix 'DATA.dist' -Folder 'c:\mq-job43'

# start the MaxQuant job
C:\MaxQuant\bin\MaxQuantCmd.exe C:\mq-job43\mqpar.xml

# Upload the results to the orginating S3 bucket
Write-S3Object -BucketName 'fredhutch-maxquant-jobs' -KeyPrefix 'combined' -Folder 'C:\mq-job43\combined' -Recurse

# Delete and object from the bucket
Remove-S3Object -BucketName 'fredhutch-maxquant' -Key 'jobctrl/running.txt' -Force
