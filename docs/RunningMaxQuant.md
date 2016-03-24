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

### Loading Raw Data

After starting MaxQuant, the first thing that you'll need to do is load the mzXML data that you prepared in the section above. In MaxQuant, click on the **"RAW files"** tab then the **"Load"** sub-tab as shown below:

![](/docs/RunningMaxQuant/maxquant-open.png)

In the resulting file open dialog shown below, navigate to the location where the mzXML files are located *(C:\MQ-EXAMPLE\MZXML in this example)*, change the file type selector to **"MzXml file (*.mzxml)"**, select the files and then click "Open" to load them.

![](/docs/RunningMaxQuant/maxquant-load-mzxml.png)


### Selecting the analysis type 

Select the **"Group-specific parameters"** tab, then the **"Type"** sub-tab. Make the following selections:

- **Multiplicity**: 2
- **Light Labels**: nothing selected
- **Heavy Labels**: Arg10 and Lys8

MaxQuant should now look like the following:
 
![](/docs/RunningMaxQuant/maxquant-type.png)


### Selecting the digestion enzymes

Select the **"Group-specific parameters"** tab, then the **"Digestion"** sub-tab. Remove everything from the right selection box and add the **"Trypsin"** enzyme. MaxQuant should look like the following:

![](/docs/RunningMaxQuant/maxquant-digestion.png)


### Setting the modification variables

Select the **"Group-specific parameters"** tab, then the **"Modifications"** sub-tab.  Remove everything from the right selection box and add the **"Oxidation (M)"** and **"Phospho (STY)"** modification variables. When complete MaxQuant should like like the following:
  
![](/docs/RunningMaxQuant/maxquant-modifications.png)


### Miscellaneous parameters

Select the **"Group-specific parameters"** tab, then the **"Misc."** sub-tab. Check the **"Re-quantify"** checkbox and set **"Match type"** to **"Match from and to"**. MaxQuant should look like the following:

![](/docs/RunningMaxQuant/maxquant-misc.png)


### Loading reference Sequence and fixed modifications

The reference sequence (FASTA) must be loaded and fixed modifications selected. Select the **"Global parameters"** tab, then the **"Sequences"** sub-tab. In the **"Fixed modifications"** section, remove everything from the right selection box and add the **"Carbamidomethyl (C)"**. Click the **"Add file"** button. In the resulting file open dialog, navigate to the location where the FASTA sequence file is located (C:\MQ-EXAMPLE\FASTA in this example), select the FASTA file and then click "Open" to load it.

![](/docs/RunningMaxQuant/maxquant-seq-loaded.png)

In the resulting file open dialog shown below, navigate to the location where the FASTA sequence file is located *(C:\MQ-EXAMPLE\FASTA in this example)*, select the FASTA file and then click "Open" to load it.

![](/docs/RunningMaxQuant/maxquant-load-seq.png)


### Protein quantification

Select the **"Global parameters"** tab, then the **"Protein quantification"** sub-tab. Remove everything from the right selection box and add the **"Oxidation (M)"** and **"Phospho (STY)"** modifications. When complete MaxQuant should like like the following:

![](/docs/RunningMaxQuant/maxquant-protein-quant.png)


### Thread selection and Starting MaxQuant

You are almost ready to start the the analysis. Select the number of threads equal to the number of mzXML files you are analyzing up to the number of logical CPU cores in the system where where MaxQuant is running. For example if you are are analyzing 4 files on a system with 8 logical CPU cores, you would select 4 threads. If you are analyzing 64 mzXML files on a system with 32 logical CPU cores, you would select 32 thread. There is one more consideration; memory. Each thread requires 2GB of RAM, So in the last example (64 files, 32 logical CPU cores) if the server only had 16GB of *available* RAM then you would select select 8 threads even though you have 32 logical CPU cores. If you don't take memory constraints into consideration the system will either run out of RAM or start swapping (bringing the analysis to a crawl).

Once you have determined the correct number of threads, enter the number into the **"Number of threads"** field and then click the **"Start"** button.     
 
![](/docs/RunningMaxQuant/maxquant-threads-start.png)


### Monitoring Progress

To view the status of the analysis while it's running, select the **"Performance"** tab. This will show you the tasks/stages that are in progress. If you want to see the status of of everything including tasks/stages that have completed, click on the **"Show all activities"**. The image below shows MaxQuant with running tasks: 

![](/docs/RunningMaxQuant/maxquant-running.png)


![](/docs/RunningMaxQuant/Maxquant-done-with-dialog.png)


![](/docs/RunningMaxQuant/Maxquant-view-results.png)

![](/docs/RunningMaxQuant/Maxquant-result-files.png)

![](/docs/RunningMaxQuant/results-excel.png)

![](/docs/RunningMaxQuant/Maxquant-status-n-timing-files.png)



