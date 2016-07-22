# MaxQuant Automated Pipeline

## Overview 

When running a MaxQuant job on a local workstation, the specifications of the system (CPU speed, CPU core count and RAM) may cause the job to take a really long time to complete. Also, while your workstation is busy running a MaxQuant job you have to wait until it's complete before you can start your next job. You might be able to find another workstation, but you won't easily be able to scale your throughput in this manner. 

The automated MaxQuant pipeline offers the following advantages:

- It runs your MaxQuant job on a server in the cloud so your local workstations are not tied up.
- Run many jobs in parallel, each with their own private server, allowing you to achieve massive throughput
- As new faster servers become available the pipeline can be adjusted to take advantage of them


## Preparing to Run an Automated MaxQuant Job

The first thing that you'll need to do is create a job directory on a filesystem that is accessible via both the Rhino HPC nodes and available via a mapped drive on your local MaxQuant Workstation.

***Note:*** *The MaxQuant workstation is not needed to run the job, but is needed generate a job configuration file and create a custom sequence database if required. If you don't have access to a Windows system running MaxQuant, you can use your HutchNetID to RDP (remote desktop) into the system named* "***maxquant-config.fhcrc.org***".

In this example I'm going to create a job folder named "**maxquant-job01**" on the **Fast File** storage system. Once this folder has been created, copy you data files (mzXML or RAW) and sequence files (fasta) to this directory.

After your data and sequence files are in place, go to your MaxQuant workstation and ensure that you can access the job directory. In this example, my workstation can access my job folder via the path "**X:\fast\mcdermott_r\maxquant-job01**".

Next start MaxQuant and load the datafiles that are located in your job folder:

[[/AutomatedPipeline/datafiles-path.png]] 


Next load the sequence files:

[[/AutomatedPipeline/fasta-file-path.png]]

Configure the rest of the MaxQuant configuration options, labels, digestion, modifications, etc... to suit the needs of your job. When you are done configuring your job. Click on the book button in the upper left of MaxQuant GUI to reveal the menu that allows you to save your configured job parameters:

[[/AutomatedPipeline/save-parameters.png]]

Save your job configuration to your maxquant job folder (X:\fast\mcdermott_r\maxquant-job01 in this example):

[[/AutomatedPipeline/save-parameters-dialog.png]]


If you are using a sequence file (fasta) that is not included in the default MaxQuant sequence database, you will need to add it to the sequence database configuration. You can do this via the MaxQuant GUI like this:

[[/AutomatedPipeline/modify-seq-databases.png]]

Next you will need to copy the customized "databases.xml" file from the MaxQuant application directory to your job directory. In this example, my custom databases.xml file was located at ***C:\Maxquant\bin\conf\databases.xml***: 

[[/AutomatedPipeline/databases-file.png]]

## mqsubmit


```
[rhino03]$ cd /fh/fast/mcdermott_r/maxquant-job01/

[rhino3]$ ls -lh
total 3.5G
-rw-rw-r-- 1 rmcdermo g_rmcdermo  16K May 17 22:14 databases.xml
-rw-r--r-- 1 rmcdermo g_rmcdermo 1.3G May 24 09:03 JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F01.mzXML
-rw-r--r-- 1 rmcdermo g_rmcdermo 1.6G May 24 09:03 JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F02.mzXML
-rwxr-xr-x 1 rmcdermo g_rmcdermo  12K Jul 22 13:16 mqpar.xml
-rw-r--r-- 1 rmcdermo g_rmcdermo  28M May 24 09:06 uniprot_taxonomy_9606_Reviewed.fasta

```


```
[rhino3]$ mqsubmit
Usage: mqsubmit.py [options]

mqsubmit.py: error: Missing REQUIRED parameters: ['--mqconfig', '--jobname', '--department', '--email']
```

```
[rhino3]$ mqsubmit --help
Usage: mqsubmit.py [options]

Options:
  -h, --help            show this help message and exit
  -m MQCONFIG, --mqconfig=MQCONFIG
                        [REQUIRED] Filename of the MaxQuant .XML configuration
                        file
  -n JOBNAME, --jobname=JOBNAME
                        [REQUIRED] The name of the maxquant job you are
                        running
  -d DEPARTMENT, --department=DEPARTMENT
                        [REQUIRED] The name of your department or lab
  -e CONTACT, --email=CONTACT
                        [REQUIRED] Your email address; needed so you can
                        receive a results link
  -c, --connect         [OPTIONAL] Prints connection information so you can
                        check on the running job
```

```
[rhino3]$ mqsubmit --mqconfig mqpar.xml --jobname job01 --department scicomp --email rmcdermo@fredhutch.org 
```

```
Found custom 'databases.xml' file...
Adjusting MaxQuant configuration file: mqpar.xml... Done!

Uploading data file(s)...
	Uploading: JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F01.mzXML... Done!
	Uploading: JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F02.mzXML... Done!

Uploading FASTA file(s)...
	Uploading: uniprot_taxonomy_9606_Reviewed.fasta... Done!

Uploading configuration file... Done!

Uploading custom databases.xml file... Done!

Setting Job Ready Flag... Done!

Finding latest Windows 2012R2 image... Selected ami-26e72546

Connecting to AWS EC2 Region us-west-2... Done!

Creating EC2 instance... Instance i-f2864366 created

Tagging EC2 instance... Done!

Your MaxQuant job has been successfully submitted. An email will be sent to me@fredhutch.org when complete with a link to download the results
```

```
[rhino3]$ mqsubmit --mqconfig mqpar.xml --jobname job01 --department scicomp --email me@fredhutch.org --connect
```

```
...

If you would like to RDP into the running MaxQuant instance to watch (do not interupt) the progress of your job, here is the information you need:
	
    Server: 172.17.64.99
    Username: Administrator
    Domain: None - leave blank
    Password: rKNccAVT9ypUdaK
    Status files: C:\mq-job\combined\proc\*
```

```
From: maxquant-do-not-reply@fredhutch.org
To: me@fredhutch.org
Date: 20 Jul 2016 20:20:08 +0000
Subject: Maxquant Job Results for job: scicomp-rhinov03 (30 day download link)
--------------

Your MaxQuant job results are available for download:

https://fredhutch-maxquant-jobs.s3.amazonaws.com/scicomp-job01/maxquant-scicomp-job01-results-combined.zip?AWSAccessKeyId=AKIAJXDAQMSHTP4UGB3A&Expires=1471893494&Signature=390amTOrCli6mxne54x5POPy07c%3D

This link will expire on 08/19/2016 20:20:08
```