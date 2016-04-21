#!/usr/bin/python
"""
mqconfig.py: Converts YAML MaxQaunt job configuration to an XML configuration format suitable for running a job
"""
import yaml

def parseConfig(config):
    """
    Parses a YAML formated MaxQuant job configuration file, formats the text of
    the variables and returns the configuration parameters in a dictionary
    """
    try:
        with open(config, 'r') as f:
            mqparams = yaml.load(f)

        # Parse and format the list of imput mzXML files. As returns the formated 'experiments', 'fractions' and 'paramGroupIndices' parameters
        mzxmlFiles = [e.strip() for e in mqparams['mzxmlFiles'].split(',')]
        mqparams['mzxmlFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), mzxmlFiles))
        mqparams['experiments'] = "\n".join(map(lambda x: " " * 8 + "<string/>", mzxmlFiles))
        mqparams['fractions'] = "\n".join(map(lambda x: " " * 8 + "<short>32767</short>", mzxmlFiles))
        mqparams['paramGroupIndices'] = "\n".join(map(lambda x: " " * 8 + "<int>0</int>", mzxmlFiles))

        # Parse and format the list of fasta files.
        fastaFiles = [e.strip() for e in mqparams['fastaFiles'].split(',')]
        mqparams['fastaFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), fastaFiles))

        # Parse and format the heavy labels.
        heavyLabels = ";".join([e.strip() for e in mqparams['heavyLabels'].split(',')])
        mqparams['heavyLabels'] = " " * 12 + "<string>{0}</string>".format(heavyLabels)

        # Parse and format the variable modifications.
        variableModifications = [e.strip() for e in mqparams['variableModifications'].split(',')]
        mqparams['variableModifications'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), variableModifications))

        # Parse and format the enzymes.
        enzymes = [e.strip() for e in mqparams['enzymes'].split(',')]
        mqparams['enzymes'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), enzymes))

        # Parse and format the fixed modifications.
        fixedModifications = [e.strip() for e in mqparams['fixedModifications'].split(',')]
        mqparams['fixedModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), fixedModifications))

        # Parse and format the restriction modifications.
        restrictionModifications = [e.strip() for e in mqparams['restrictionModifications'].split(',')]
        mqparams['restrictionModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), restrictionModifications))

        mqparams['jobName'] = mqparams['jobName'].strip()
        mqparams['department'] = mqparams['department'].strip()
        mqparams['contactEmail'] = mqparams['contactEmail'].strip()

        # return a dictionary of formated MQ parameters.
        return mqparams
    except:
        raise Exception("Error opening or parsing configuration file: {0}".format(config) )

def createMqConfig(mqparams, template):
    """
    Takes a dictionary of decorated MaxQuant job parameters and renders and
    returns a MaxQuant job configuration in the requried XML format
    """
    mqconfig = template.format(**mqparams)
    return mqconfig


def uploadS3(bucket, folder):
    pass


def main(configIn, configOut, template):
    """
    When run stand-alone (not imported), execution starts here
    """
    mqparams = parseConfig(configIn)
    template = open(template).read()
    mqconfig = createMqConfig(mqparams, template)
    with open(configOut, 'w') as out:
        out.write(mqconfig)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: ./{} <inputYAMLconfigFile> <outputXMLconfigFile>".format(sys.argv[0]))
        sys.exit(1)
    else:
        configIn = sys.argv[1].strip()
        configOut = sys.argv[2].strip()
        template = 'mqpar.xml.template'
        main(configIn, configOut, template)
