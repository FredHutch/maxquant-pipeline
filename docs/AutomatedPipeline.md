# MaxQuant Automated Pipeline

## Overview 

The MaxQuant Automated Pipeline can help you take the load off of your workstation or any other local system and push it out to a server in the cloud. Each job that you submit via the automated MaxQuant pipeline is assigned its own dedicated server instance that only lives for the life of the MaxQuant job. This means that you can run several jobs in parallel to increase your lab's proteomics throughput to meet any research tempo.

To submit a MaxQuant job to the pipeline you simply put your data in a job directory, use the MaxQuant GUI application to configure your job like you would typically, but rather than starting the job via the MaxQuant GUI, you save the job configuration to your job directory then submit the job via the "mqsumit" command that is available on the Rhino HPC systems.

The pipeline automatically selects the appropriate server size (CPU count, RAM and SSD volume size) based on the size of the job that you submit. The current smallest server utilized by the pipeline is 2 CPU cores (2.9 GHz Intel Xeon E5-2666 v3 Haswell) with 4GB of RAM and the largest server instance is 36 CPU cores with 60GB of RAM.

The diagram below provides a high-level view of how the automated pipeline works:

![](/docs/AutomatedPipeline/maxquant-automation-pipeline-s.png)


## Preparing to Run an Automated MaxQuant Job

The first thing that you'll need to do is create a job directory on a filesystem that is accessible via both the Rhino HPC nodes and available via a mapped drive on your local MaxQuant Workstation. The automated pipeline is currently using MaxQuant version 1.5.5.1 so it's important that you use the same version to generate the configuration for submission to the pipeline.

***Note:*** *A local copy of MaxQuant is not needed to run the job, but is needed generate a job configuration file and create a custom sequence database if required. If you don't have access to a Windows system running MaxQuant, you can use your HutchNetID to RDP (remote desktop) into the system named* "***maxquant-config.fhcrc.org***".

In the following example I'm going to create a job folder named "**maxquant-job01**" on the **Fast File** storage system. Once this folder has been created, copy your data files (mzXML or RAW) and sequence files (fasta) to this directory.

After your data and sequence files are in place, go to your MaxQuant workstation and ensure that you can access the job directory. In this example, my MaxQuant workstation can access my job folder via the path "**X:\fast\mcdermott_r\maxquant-job01**".

Next, start MaxQuant (version 1.5.5.1) and load the datafiles that are located in your job folder:

![](/docs/AutomatedPipeline/datafiles-path.png)

Next, load the sequence files:

![](/docs/AutomatedPipeline/fasta-file-path.png)

After the desired data and sequence files are selected, configure the rest of the MaxQuant configuration options, labels, digestion, modifications, etc... to suit the needs of your job. When you are done configuring your job. Click on the blue button in the upper left of MaxQuant GUI to reveal a menu that allows you to save your configured job parameters:

![](/docs/AutomatedPipeline/save-parameters.png)

Save your job configuration to your MaxQuant job folder, X:\fast\mcdermott_r\maxquant-job01 in this example:

![](/docs/AutomatedPipeline/save-parameters-dialog.png)


If you are using a sequence file (fasta) that is not included in the default MaxQuant sequence database, you will need to add it to the sequence database configuration. You can do this via the MaxQuant GUI like this:

![](/docs/AutomatedPipeline/modify-seq-databases.png)

Next, you will need to copy the customized "databases.xml" file from the MaxQuant application directory to your job directory. In this example, my custom databases.xml file was located at ***C:\Maxquant\bin\conf\databases.xml***: 

![](/docs/AutomatedPipeline/databases-file.png)

If you have created a custom modification, you can copy the modified "modifications.xml" file to your job directory using the exact same procedure used for custom databases (above).

After your data files, sequence files, MaxQuant configuration file, databases.xml file (optional) and modifications.xml (optional) are in a job folder that's accessible via the Rhino HPC systems, you are ready to submit your job.

## Submitting your MaxQuant Job to the pipeline

At this point all of your files and configuration are in place and you are ready to submit your job. 

First, SSH to one of the Rhino nodes then change the working directory to your job directory:

```
[rhino03]$ cd /fh/fast/mcdermott_r/maxquant-job01/
```

Here is what the contents of my job directory looks like when ready to submit the job: 

```
[rhino3]$ ls

mqpar.xml
databases.xml
JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F01.mzXML
JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F02.mzXML
uniprot_taxonomy_9606_Reviewed.fasta
```

To submit the job you will need to use the "mqsubmit" command. Just type "mqsubmit" without any parameters to make sure that it's in your path and to see the required parameters:

```
[rhino3]$ mqsubmit
Usage: mqsubmit.py [options]

mqsubmit.py: error: Missing REQUIRED parameters: ['--mqconfig', '--jobname', '--department', '--email']
```

For more detailed information on the usage of mqsubmit and it's parameters, both required and optional, run the command "mqsubmit --help":

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


OK, we are ready to submit this job. I want to name this job "job01", my department/lab is "scicomp" and I want the results link from this job to be emailed to me at "me@fredhutch.org". Here is how to submit this job: 

```
[rhino3]$ mqsubmit --mqconfig mqpar.xml --jobname job01 --department scicomp --email me@fredhutch.org 
```

After submitting the job, you will see some output of the progress of the job submission. The data files will be uploaded to the cloud during this process, so it could take some time depending on how many files you are uploading or the current load on the Center's internet connection. Here is the ouput that I received after submitting this example job:

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

After your job is submitted, you are free to submit several other jobs in the same manner (make sure to use a unique combination of job name and department for each job). When your job is complete an email message will be sent to the email address you provided (--email parameter) when you submitted the job.

If you don't like the idea of waiting for an email when the job is complete, it's possible to connect to the cloud server and watch the progress of your job by looking at the files in the "C:\mq-job\combined\proc\" directory. To get connection information, simply provide the "--connect" parameter when submitting the job, like the following:

```
[rhino3]$ mqsubmit --mqconfig mqpar.xml --jobname job01 --department scicomp --email me@fredhutch.org --connect
```

If you provided the optional "--connect" parameter, the job submission output will provide additional information that looks like this:

```
...

If you would like to RDP into the running MaxQuant instance to watch (do not interrupt) the progress of your job, here is the information you need:
	
    Server: 172.17.64.99
    Username: Administrator
    Domain: None - leave blank
    Password: rKNccAVT9yPUdaK
    Status files: C:\mq-job\combined\proc\*
```

The additional information provided by the --connect parameter can now be use to RDP (Remote Desktop) into the running MaxQuant server. The server will likely be very busy (CPU utilization 95-100%), so your RDP session will likely be very slow. ***Note:*** *Don't interfere with the MaxQuant job. The MaxQuant GUI will not be visible; the only way to see the progress is via the text files in the "C:\mq-job\combined\proc\" directory.* 

## Retrieving Job Results

After your job is complete, you will get an email to the address you provided that contains a link to download the results. This link is temporary but can be used to retrieve the results bundle for up to 30 days after completion. Here is what the email will look like:

```
From: maxquant-do-not-reply@fredhutch.org
To:   me@fredhutch.org
Date: 20 Jul 2016 20:20:08 +0000
Subject: Maxquant Job Results for job: scicomp-rhinov03 (30 day download link)


Your MaxQuant job results are available for download:

https://fredhutch-maxquant-jobs.s3.amazonaws.com/scicomp-job01/maxquant-scicomp-job01-results-combined.zip?AWSAccessKeyId=AKIAJXDAQMSHTP4UGB3A&Expires=1471893494&Signature=390amTOrCli6mxne54x5POPy07c%3D

This link will expire on 08/19/2016 20:20:08
```

When you click on the provided link (or right-click it and "save as"), it will download a results bundle to your computer. If you go the "right-click/save-as" route you can save the results bundle directly to the job directory via a mapped drive and avoid and extra copying step. In the example job that I ran, my results bundle was named **"maxquant-scicomp-job01-results-combind.zip"**.

After results bundle is download and copied to your job directory, extract it and rename the extracted directory to "combined" and your job directory will look just like it would if you had run the job locally.
