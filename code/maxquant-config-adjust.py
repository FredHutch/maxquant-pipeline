import xml.etree.ElementTree as ET

def adjustConfig(configFile, configFileOut, jobdir):
    tree = ET.parse(configFile)
    root = tree.getroot()

    datafiles = []
    for filePaths in root.findall('filePaths'):
        files = filePaths.findall('string')
        for d in files:
            datafiles.append(d.text) 
            dpath = jobdir + (d.text).split('/')[-1]
            d.text = dpath 

    fastas = []
    for fastaFiles in root.findall('fastaFiles'):
        fasta = fastaFiles.findall('string')
        for f in fasta:
            fastas.append(f.text) 
            fpath = jobdir + (f.text).split('/')[-1]
            f.text = fpath 

    tree.write(configFileOut)
    return datafiles, fastas


if __name__ == "__main__":
    jobdir = 'c:/mq-job/'
    configFile = 'mq-job-in.xml'
    configFileOut = 'mq-job-out.xml'

    x = adjustConfig(configFile, configFileOut, jobdir)
