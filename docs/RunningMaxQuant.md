# Conducting and Analysis with MaxQuant

This document shows how to manually run a small analysis job using MaxQuant.

## Preparing the data

Running a MaxQuant job requires mass spectrometry data in *.mzXML format. In this example we'll be conducting an analysis on two files:

* **JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F01.mzXML**
* **JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F02.mzXML**

In addition to the mzXML files, you'll also need a FASTA formatted sequence file. In this example we'll use the following sequence file:

* **uniprot_taxonomy_9606_Reviewed.fasta**

For this analysis all of the above files are in a directory structure that looks like the following:

```
C:\MQ-EXAMPLE
+---Fasta
|       uniprot_taxonomy_9606_Reviewed.fasta
|
\---MZXML
        JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F01.mzXML
        JK042415_042415_RadOnc_01_10Gy_SS_BRP_IMAC_F02.mzXML
```

***NOTE:*** *It's not necessary for all the files to be in a directory structure like this, but it makes it easier to document and show the results for the purposes of this documentation.*    

After you have the mass spec data (mzXML) and the sequence file (FASTA) that you want to use in place, you are ready to start MaxQuant and configure your analysis and run it.


## Configuring and Running MaxQuant

[[/docs/RunningMaxQuant/maxquant-open.png]]

[[/docs/RunningMaxQuant/maxquant-load-mzxml.png]]

[[/docs/RunningMaxQuant/maxquant-type.png]]

[[/docs/RunningMaxQuant/maxquant-digestion.png]]

[[/docs/RunningMaxQuant/maxquant-modifications.png]]


[[/docs/RunningMaxQuant/maxquant-misc.png]]


[[/docs/RunningMaxQuant/maxquant-seq-loaded.png]]


[[/docs/RunningMaxQuant/maxquant-load-seq.png]]


[[/docs/RunningMaxQuant/maxquant-protein-quant.png]]


[[/docs/RunningMaxQuant/maxquant-running.png]]

[[/docs/RunningMaxQuant/maxquant-threads-start.png]]

[[/docs/RunningMaxQuant/maxquant-running-status-files.png]]











