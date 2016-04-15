#!/usr/bin/python
import yaml


def parseConfig(config):
    with open(config, 'r') as f:
        mqparams = yaml.load(f)
    mzxmlFiles = [e.strip() for e in mqparams['mzxmlFiles'].split(',')]
    mqparams['mzxmlFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), mzxmlFiles))
    mqparams['experiments'] = "\n".join(map(lambda x: " " * 8 + "<string/>", mzxmlFiles))
    mqparams['fractions'] = "\n".join(map(lambda x: " " * 8 + "<short>32767</short>", mzxmlFiles))
    mqparams['paramGroupIndices'] = "\n".join(map(lambda x: " " * 8 + "<int>0</int>", mzxmlFiles))
    
    fastaFiles = [e.strip() for e in mqparams['fastaFiles'].split(',')]
    mqparams['fastaFiles'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), fastaFiles))
    
    heavyLabels = ";".join([e.strip() for e in mqparams['heavyLabels'].split(',')])
    mqparams['heavyLabels'] = " " * 12 + "<string>{0}</string>".format(heavyLabels)
    
    variableModifications = [e.strip() for e in mqparams['variableModifications'].split(',')]
    mqparams['variableModifications'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), variableModifications))
    
    enzymes = [e.strip() for e in mqparams['enzymes'].split(',')]
    mqparams['enzymes'] = "\n".join(map(lambda x: " " * 12 + "<string>{0}</string>".format(x), enzymes))
    
    fixedModifications = [e.strip() for e in mqparams['fixedModifications'].split(',')]
    mqparams['fixedModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), fixedModifications))
    
    restrictionModifications = [e.strip() for e in mqparams['restrictionModifications'].split(',')]
    mqparams['restrictionModifications'] = "\n".join(map(lambda x: " " * 8 + "<string>{0}</string>".format(x), restrictionModifications))
    
    return mqparams

def createMqConfig(mqparams, template):
    mqconfig = template.format(**mqparams)
    return mqconfig

def main(config, template):
    mqparams = parseConfig(config)
    #print(mqparams)
    template = open(template).read()
    mqconfig = createMqConfig(mqparams, template)
    print(mqconfig)

if __name__ == "__main__":
    config = 'mqjob.yaml'
    template = 'mqpar.xml.template'
    main(config, template)