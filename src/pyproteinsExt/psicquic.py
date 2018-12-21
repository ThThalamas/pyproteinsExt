# coding: utf8
import urllib2
from bs4 import BeautifulSoup
import re
import xml.etree.ElementTree as ET
import pyproteinsExt.uniprot
import json
import os
import numpy as np

import multiprocessing

PYTHONIOENCODING='utf-8'


def parse_worker(input):
    print 'Worker^^ ' + str(len (input['bufferArray']))
    #for f in input:
    #    print f
    #return []
    bufferRecords = []

    looseChk = False
    if 'looseChk' in input:
        if input['looseChk'] :
            looseChk = True

    for line in input['bufferArray']:
        if len(line) == 0 or line.startswith("#"):
            continue
        if 'encoder' in input:
                #print "==>" + kwargs['encoder']
            datum = PSQDATA( line.decode(input['encoder']) )
        else:
            datum = PSQDATA(line)
            #if _checkPsqData(input['self'], datum) or looseChk:
        bufferRecords.append(datum)

    return bufferRecords

def _checkPsqData (self, psqDataObj):
    pmid = psqDataObj['pmid']
    source = psqDataObj['source']
    if not pmid in self.registredPublications:
        self.registredPublications[pmid] = source
        return True

    if self.registredPublications[pmid] == source:
        return True
    else:
            #print "Warning publication " + pmid + " provided by " + source + " has already been fetched from " + self.registredPublications[pmid]
        return False



#from pkg_resources import resource_stream, Requirement
#

PSQ_FIELDS= ["idA", "idB", "altA", "altB", "aliasA", "aliasB", "interactionDetectionMethod", "firstAuthor", "pubid", "taxidA", "taxidB",
            "interactionTypes", "sourceDatabases", "interactionIdentifiers", "confidenceScore", "complexExpansion", "biologicalRoleA"
            , "biologicalRoleB", "experimentalRoleA", "experimentalRoleB", "interactorTypeA", "interactorTypeB", "xRefA", "xRefB",
            "xRefInteraction", "annotationA", "annotationB", "annotationInteraction", "taxidHost", "parameters", "creationDate",
            "updateDate", "checksumA", "checksumB", "negative", "featuresA", "featuresB", "stoichiometryA", "stoichiometryB",
            "identificationMethodA", "identificationMethodB"]

# BEWARE will have to move from SOAP to REST at 1st Oct 2016
# http://www.ebi.ac.uk/ols/roadmap.html
class OLS():

    def __init__(self, ontology="mi"):

        self.cOntology = ontology
        self.restApi = 'http://www.ebi.ac.uk/ols/api/ontologies/' + self.cOntology + '/'
        self.lineage = {}

    def _parse (self, url):
        response = urllib2.urlopen(self.restApi + url)
        data = json.load(response)
        return data

    def isSonOf(self, childId=None, parentId=None):
        if not childId or not parentId:
            return None
        self._getLineage(childId)
        if parentId in self.lineage[childId]: return True
        return False

    def _getLineage(self, termId):
        u = termId.replace(":", "_")
        req = self._parse("terms/http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252F" + u + "/hierarchicalAncestors")
        self.lineage[termId] = [ k['obo_id'] for k in req["_embedded"]["terms"] if  k['obo_id'] ]
        print self.lineage[termId]

    def getTermById(self, termId=None):
        ans = self.restApi + 'terms?obo_id=' + termId
        print ans
        if ans == termId:
            print "id term failed"
            return None


def _convert(psqDataObj, biogridMapper):
    for i in range(0,2):
        if psqDataObj.data[i].data[0].type == 'uniprotkb:':
            continue

        tmp = str(psqDataObj.data[i].data[0])
        v = psqDataObj.data[i + 2]['biogrid']
        if not v:
            break
        u = biogridMapper(biogridId=v[0])
        if not u:
            break

        nP = PSQFIELD('uniprotkb:' + u)
        psqDataObj.data[i] = nP
        psqDataObj.data[i + 2].data.append(PSQFIELD(tmp))


class PSICQUIC(object):
    mitabLvls = ["25", "27"]
    olsWebService = OLS()

    def read(self, fileName, **kwargs):
        with open(fileName, 'r') as f:
           # print 'toto2'
            s = f.read()
        #return
        #if n > 1:

        #else:
            self._parseString(s, **kwargs)


    def convert(self, biogrid=None): #  bioigrid is a reference to a BIOGRID mapper object
        if biogrid:
            for psqData in self:
                _convert(psqData, biogrid)
    #returns a subset of the current PSICQUIC data, create a new PSICQUIC object
    #For now, psicquic datum are never modified, we therefore simply copy by reference
    def clone(self, **kwargs):
        cloneSelf = PSICQUIC()
        if not kwargs:
            cloneSelf.records = records
        #if 'partnerPairs' in kwargs:


    def __len__(self):
        return len (self.records)

    def __init__(self, registryUrl="http://www.ebi.ac.uk/Tools/webservices/psicquic/registry/registry?action=STATUS&format=xml", mode='STRICT', offLine=False):
        self.records = []
        self.mode = mode # or 'LOOSE'
        self.registredPublications = {} # { "pubid" : "sourceDatabase" }

        if not offLine:
            self.registry = self.getRegistry(registryUrl)
            if not self.registry:
                self.registry = registry()

    def __repr__(self):
        string = "\n".join(map(str, self.records))
        return string

    def __getitem__(self, i):
        return self.records[i]

    def __iter__(self):
        for record in self.records:
            yield record

    def clear(self):
        self.records = []
        self.registredPublications = {}

    def json(self, file=None):
        jsonString = '{"type" : "mitabResult", "data" : [' + ','.join([ psqData.json for psqData in self ]) + '] }'

        if file:
            with open(file, 'w') as f:
                f.write(jsonString)
        return jsonString

    def dump(self, file=None):
        if file:
            with open(file, 'w') as f:
                f.write(self.__repr__())
        #else:
        #    print self.__repr__()
        return self.__repr__()
    def load(self, mitabStream):
        if not mitabStream:
            print "You must provide a mitab input"
            return
        bufferStr = ""

        for line in mitabStream:
            bufferStr = bufferStr + line
        self._parseString(bufferStr)

# Receives a 2 tuple of uniprot identifiers (h1,h2)
# Performs two requests with OR combination of w/ each set, and a AND combination of the two set
# eg : ((xxx,yyy),(uuu,vvv)) -> miql1 : idA:(xxx OR yyy) AND idB:(uuu OR vvv)
#                               miql2 : idB:(xxx OR yyy) AND idA:(uuu OR vvv)
    def zQuerySlow(self, hArray, **kwargs):
        #FS='%20'+'OR%20'
        param = kwargs
        param['erasePrevious'] = False

        for p1 in hArray[0]:
            for p2 in hArray[1]:
                if p1 == p2:
                    self.query(raw='idA:' + p1 + '%20'+'AND%20idB:' + p2, **kwargs)
                else:
                    self.query(pair=(p1, p2), **kwargs)
        #miqlStringOne = 'idA:(%20' + FS.join(hArray[0]) + '%20)%'+ '20AND%20' + 'idB:(%20' + FS.join(hArray[1]) + '%20)'
        #miqlStringTwo = 'idA:(%20' + FS.join(hArray[1]) + '%20)%'+ '20AND%20' + 'idB:(%20' + FS.join(hArray[0]) + '%20)'
        #print miqlStringOne
        #print miqlStringTwo

        #self.query(raw=miqlStringOne, **kwargs)


        #self.query(raw=miqlStringTwo, **param)

    # Must be put on two separated threads
    # Must deal w/ autointeraction
    def zQuery(self, hArray, **kwargs):
        #FS='%20'+'OR%20'
        param = kwargs
        param['erasePrevious'] = False

        cloneOne = PSICQUIC()
        cloneOne.registry

        chunks = [hArray[0][x:x+50] for x in xrange(0, len(hArray[0]), 50)]

        for p1 in chunks:
            cloneOne.query(uniprotId=p1,**kwargs)


        chunks = [hArray[1][x:x+50] for x in xrange(0, len(hArray[1]), 50)]
        cloneTwo = PSICQUIC()
        cloneTwo.registry
        for p2 in chunks:
            cloneTwo.query( uniprotId=p2, **kwargs)


        print '**************'
        print len (cloneOne)
        print len (cloneTwo)

       # with open('/Users/guillaumelaunay/toto_1.txt', 'w') as f:
       #     f.write(cloneOne.dump())
       # with open('/Users/guillaumelaunay/toto_2.txt', 'w') as f:
       #     f.write(cloneTwo.dump())
        #print '####'
        #print cloneTwo.dump()

        bufRecords = set(cloneOne.records) & set(cloneTwo.records)
        self.records = list(bufRecords)
        print len(self)

    def query(self, **kwargs):

        if 'providers' in kwargs:
            providers = kwargs['providers']
        else:
            providers = ["dip"]

        if 'mitabLvl' in kwargs:
            mitabLvl = kwargs['mitabLvl']
        else:
            mitabLvl="25"

        if 'erasePrevious' in kwargs:
            erasePrevious = kwargs['erasePrevious']
        else:
            erasePrevious = True

        if providers[0] == '*':
            providers = self.registry

        if erasePrevious:
            self.clear()

        if mitabLvl not in self.mitabLvls:
            print "invalid mitab level " + mitabLvl
            return None

        parameterSet = ('uniprotId', 'seeds', 'pair', 'species')
        if set(parameterSet) | set(kwargs.keys()) == 0:
            raise ValueError('Missing one parameter : ' + str(parameterSet))

        miqlString = ''
        if 'raw' in kwargs:
            miqlString = kwargs['raw']
        else :
            miqlParam = []

            for k, v in kwargs.iteritems():
                if k in  ['pair', 'uniprotId', 'seeds']:
                    field = "id:"
                elif k == 'species':
                    field = "species:"
                else :
                    continue

                if k == "pair":
                    miqlParam.append(field + '(' + ('%20'+'AND%20').join(v) + ')')
                elif isinstance(v, list):
                    miqlParam.append(field + '(' + ('%20'+'OR%20').join(v) + ')')
                else :
                    miqlParam.append(field + v)

            miqlString = ('%20' + 'AND%20').join(miqlParam)

        for provider in providers:
# psicquic members
            if not provider in self.registry:
                print "provider is no registred database"
                continue
            miql = self.registry[provider] + 'query/' + miqlString
            #print miql
            ans, encoder = self._ping(miql + "?format=tab" + mitabLvl)
            if ans == 0:
                ans, encoder = self._ping(miql + "?format=tab25")
            if ans:
                self.parseString(ans, encoder=encoder)
            else:
                continue

        if not erasePrevious:
           # print "b4 NR " + str(len(self))
            self.makeNR()
           # print "AftR NR " + str(len(self))

    def _ping(self, url):
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError as error:
            if error.code == 406:
                print url
                print "mitab Level may not be supported retrying w/ 2.5"
                return 0
            print url + "\nHTTP ERROR " + str(error.code)
            return None
        except urllib2.URLError as error:
            print url + "\n" + str(error.reason)
            return None
        raw = response.read()

        encoder = response.headers['content-type'].split('charset=')[1] if len(response.headers['content-type'].split('charset=')) > 1 else 'utf-8'


        #Content-Type:text/plain; charset=utf-8

        response.close()
        return (raw, encoder)

    def getRegistry(self, url):
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError as error:
            print "Unable to contact registry at " + url
            print "Loading default"
            return registry()

        raw = response.read()
        response.close()
        return registry(raw)

    # mode = LOOSE and mprocess, encoder, have to be passed a kwargs
    def _parseString(self, raw, **kwargs):
        bufferArray = [ line for line in raw.split("\n") ]
        if 'n' in kwargs:
            if kwargs['n'] > 1 :
                    print 'Distributing parsing of ' +  str(len(bufferArray)) + ' mitab lines over ' + str(kwargs['n']) + ' processes'
                    inputs =  [ { 'bufferArray' : x.tolist() }for x in np.array_split(bufferArray, kwargs['n']) ]
                    #if __name__ == '__main__':
                    for d in inputs:
                        if 'encoder' in kwargs:
                            d['encoder'] = kwargs['encoder']
                        d['looseChk'] = True if self.mode is 'LOOSE' else False
                       # d['self'] = self
                    pool = multiprocessing.Pool(processes=kwargs['n'])
    # map the list of lines into a list of result dict
                    res = pool.map(parse_worker, inputs)
                    for r in res:
                        self.records += r
                    pool.close()
                    pool.join()
                    return

        self._parse(bufferArray)

    def _parse(self, bufferArray, **kwargs):
        print 'parser'
        bufferRecords = []
        for line in bufferArray:
            if len(line) == 0 or line.startswith("#"):
                continue
            if 'encoder' in kwargs:
                #print "==>" + kwargs['encoder']
                bufferRecords.append( PSQDATA( line.decode(kwargs['encoder']) ) )
            else:
                bufferRecords.append(PSQDATA(line))
        if self.mode is "LOOSE":
            self.records += bufferRecords
        else:
            self.records += [data for data in bufferRecords if _checkPsqData(self, data)]

    def analyse(self):
        if len(self) == 0: return None
        data = {
            "stats" : self.statInteractionMethods(),
            "pmids" : self.countPmid()
        }
        return data

    def countPmid(self):
        knownPmids = []
        for record in self.records:
            if record['pmid'] not in knownPmids:
                knownPmids.append(record['pmid'])
        return knownPmids

    def statInteractionMethods(self, opt=None):
        if opt :
            stats = opt
        else :
            stats = {
                "MI:0401" : { "name" : "biochemical", "count" : 0},
                "MI:0013" : { "name" : "biophysical", "count" : 0},
                "MI:0254" : {"name":"genetic interference","count" : 0},
                "MI:0428" : { "name" : "imaging technique", "count" : 0},
                "MI:1088" : { "name" : "phenotype-based detection assay", "count" : 0},
                "MI:0255" : { "name" : "post transcriptional interference", "count" : 0},
                "MI:0090" : {"name":"protein complementation assay","count":0},
                "MI:0362" : { "name" : "inference", "count" : 0},
                "MI:0063" : {"name":"interaction prediction","count":0},
                "MI:0686" : { "name" : "unspecified method", "count" : 0}
            }
        stillExperimental = 0
        for psqDataObj in self:
            detectMeth = psqDataObj["interactionDetectionMethod"]
            boolT = False
            if detectMeth in stats:
                stats[detectMeth]['count'] = stats[detectMeth]['count'] + 1
                continue
            for id in stats:
                if self.olsWebService.isSonOf(detectMeth, id):
                    stats[id]['count'] = stats[id]['count'] + 1
                    boolT = True
                    break
            if not boolT:
                if detectMeth == "MI:0045":
                    stillExperimental = stillExperimental + 1
                else:
                    print "Warning " + detectMeth + " was not cast"

        stats["experimental"] = stillExperimental
        #print stats
        #print "\tstill Experimental => " + str(stillExperimental)
        return stats



    def topology(self, type='uniprotID'): # We should register alias of interactors too
        nodes = []
        edges = {}
        for p in self:
            t = p['uniprotPair']
            if not t:
                continue
            nodes += [ n for n in t if n not in nodes ]
            if t not in edges:
                edges[t] = [p]
            else :
                edges[t].append(p)

        return (nodes,edges)

    def makeNR(self):
        self.records = list(set(self.records))


    def getBiomolecules(self, type='uniprot'):
        if type == 'uniprot':
            l = []
            for p in self:
                up = p['uniprotPair']
                if up:
                    l += up
            return list(set(l))

# Returns another instance of PSQ with filter data elements
    def filter(self, **kwargs):
        target = PSICQUIC()
        buf = kwargs['uniprot']
        # For now we dont look into alias uniprot identifiers
        if 'uniprot' in kwargs:
            if isinstance(kwargs['uniprot'], list):
                buf = set(kwargs['uniprot'])
            elif isinstance(kwargs['uniprot'], basestring):
                buf = set(kwargs['uniprot'])
#            elif isinstance(kwargs['uniprot'], set):

            for psqData in self:
                up = psqData['uniprotPair']
                if not up:
                    continue
               # print up
               # print buf
                if set(up) & buf :
                    #print str(up) + ' <===> ' + str(buf)
                    target.records.append(psqData)

        return target

# This is the main interface we try to define smart __getitem__() access keys
class PSQDATA():
    def __eq__(self, other):
        if hash(self) == hash(other):
            return True
        return False
    def __hash__(self):
        return hash(self.data[0].data[0].value + self.data[1].data[0].value + self["interactionDetectionMethod"] + self["pmid"])

    def __init__(self, raw):
        self.raw = raw
        self.data = [PSQDATUM(column) for column in re.split(r'\t+', raw)]#raw.split("\t") ] #if column

        if len(self.data) != 15 and len(self.data) != 42:
            for i,e in enumerate(self.data):
                print '[' + str(i) + '] ' + str(e)
            raise ValueError ("Uncorrect number of tabulated fields on input [" +
                str(len(self.data)) + "] at:\n" + str(raw) )

    def __repr__(self):
        string = "\t".join(map(str,self.data))
        return string
    def __getitem__(self, key):
        if key is "pmid":
            for field in self.data[8].data:
                if field.type == "pubmed:":
                    return field.value
            return self.data[8].data[0].value
        if key is "source":
            if self.data[12].data[0].annotation:
                return self.data[12].data[0].annotation
            return self.data[12].data[0].value
        if key is "interactionDetectionMethod":
            return self.data[6].data[0].value
        if key is "species":
            return (self.data[9].data[0].value, self.data[10].data[0].value)
        if key is 'uniprotPair':
            a = pyproteinsExt.uniprot.capture(self.data[0].data[0].value) if pyproteinsExt.uniprot.capture(self.data[0].data[0].value) else pyproteinsExt.uniprot.capture(self.data[2].data[0].value)
            b = pyproteinsExt.uniprot.capture(self.data[1].data[0].value) if pyproteinsExt.uniprot.capture(self.data[1].data[0].value) else pyproteinsExt.uniprot.capture(self.data[3].data[0].value)
            if a and b:
                (a,b) = (b,a) if b < a else (a,b)
                return (a, b)
            return None

    @property
    def json(self):

        #for k,d in zip(PSQ_FIELDS, self.data):

            #print k
            #print d
            #print d.data
            #print map(str,d.data)

            #print [ x.replace('"', r'\\') for x in map(str,d.data)]

        #return '{' + ','.join([ '"' + k  + '" : [' + ','.join([ '"' + x.replace('"', r'\"') + '"' for x in map(str,d.data) ]) + ']' for k,d in zip(PSQ_FIELDS, self.data) ]) + '}'
        #print { k : str(d) for k,d in zip(PSQ_FIELDS, self.data) }
        #return json.dumps( { k : str(d) for k,d in zip(PSQ_FIELDS, self.data) } )

      #  return '{' + ','.join([ '"' + k + '"' + ' : ' + str(d) for k,d in zip(PSQ_FIELDS, self.data) ]) + '}'
        #return '{' + ','.join([ '"' + k + '"' + ' : "' + str(d).replace('"','\"') + '"' for k,d in zip(PSQ_FIELDS, self.data) ]) + '}'


        return json.dumps({ k : str(d)for k,d in zip(PSQ_FIELDS, self.data) })
        #return json.dumps([ str(d) for d in self.data ] )
    @property
    def interactors(self):
        datum = (self.data[0].content + self.data[2].content, self.data[1].content + self.data[3].content )
        #print datum
        return  datum

    def hasInteractors(self, mode='STRICT'):
    #    for psqDatum in [ self.data[0].content + self.data[]
        pass

    def getNames(self):
        pass

    def getPartners(self):
        pass
            # Ask for partners
            # Extract uniprot id
            # fill a 'p->{ m_0, m_1, ..., m_n,}, where m's are uniprot match

class PSQDATUM():
    def __init__(self, string):
        self.raw = string
        self.data = [ PSQFIELD(field) for field in string.split('|')]
    def __repr__(self):
        string = '|'.join(map(str,self.data))
        return string

    def __iter__(self):
        for psqFieldObj in self.data:
            yield psqFieldObj

    def __getitem__(self, key):
        hits = []
        for psqFieldObj in self.data:
            if psqFieldObj.type == key + ':':
                hits.append(psqFieldObj.value)
        return hits

    @property
    def content(self):
        return [ (e.type, e.value) for e in self.data ]



class PSQFIELD():
    fieldParser = re.compile('^([^:^"]+:){0,1}"{0,1}([^"\(]+)"{0,1}\({0,1}([^\)]+){0,1}\){0,1}$')
    def __init__(self, raw):
        m = re.match(self.fieldParser, raw)
        self._raw = raw
        if not m:
            #print "warning following field causes problem to parse\n" + raw
            self.value = raw
            self.type = None
            self.annotation = None
        else:
            self.type = m.groups()[0]
            self.value = m.groups()[1]
            self.annotation = m.groups()[2]
   # def __repr__(self):
        #if isinstance(self.value, basestring):
   #     if not isinstance(self.value, unicode):
    #        string = unicode(self.value, 'utf-8')
    #    else :
    #        string = self.value

    #    if self.type: string = self.type + string
    #    if self.annotation: string = string + "(" + self.annotation + ")"
    #    return string

    def __str__(self):
        return self._raw

        try :
            string = self.value.decode('ascii')
        except UnicodeDecodeError:
        #    print "Decode error" + self.value
            string = self.value.decode('utf8')
        except UnicodeEncodeError:
            #print "UTF ENCODING"
            string = self.value.encode('utf8')
        #string = self.value

        if self.type is 'comment':
            return self.raw

        if self.type:
            string = self.type + string
        if self.annotation:

            try :
                str_annot = self.annotation.decode('ascii')
            except UnicodeDecodeError:
                #print "OUPS ANNNOT"
                str_annot = self.annotation.decode('utf8')
            except UnicodeEncodeError:
                #print "OUPSS EEECC"
                str_annot = self.annotation.encode('utf8')
        #    string = string + "(" + str(str_annot) + ")"
            string = string + "(" + str(self.annotation) + ")"
        else:
            pass

        return string



class registry():
    data = {
        'dip' : "http://imex.mbi.ucla.edu/psicquic-ws/webservices/current/search/",
        'intact' : "http://www.ebi.ac.uk/Tools/webservices/psicquic/intact/webservices/current/search/",
        'mint' : "http://www.ebi.ac.uk/Tools/webservices/psicquic/mint/webservices/current/search/",
        'innatedb_imex' : "http://www.ebi.ac.uk/Tools/webservices/psicquic/innatedb/webservices/current/search/",
        'matrixdb' : "http://matrixdb.ibcp.fr:8080/psicquic/webservices/current/search/",
        'innatedb' : "http://psicquic.curated.innatedb.com/webservices/current/search/"
    }

    def __init__(self, raw):
        if raw:
            #print raw
            try:
                root = ET.fromstring(raw)
            except:
                print "Registry Remote XML parsing error, using local file as registry"
#                resource_stream(Requirement.parse("pyproteinsExt=="), "restez/httpconn.py")

                path =  os.path.abspath(__file__)
                dir_path = os.path.dirname(path)
                tree = ET.parse(dir_path + '/static/psicquicRegistryDefault.xml')
                root = tree.getroot()
            #else:


            for child in root:
                name = ""
                url = ""
                for subT in child:
                    if subT.tag == "{http://hupo.psi.org/psicquic/registry}restUrl":
                        url = subT.text
                    if subT.tag == "{http://hupo.psi.org/psicquic/registry}name":
                        name = subT.text
                name = name.lower().replace("-","_")
                self.data[name] = url

                '''
                if not line:
                    continue
                #print line
                field = line.split("=")
                name = field[0].lower().replace("-","_")
                self.data[name] = field[1]
                '''

    def __getitem__(self,index):
        if not index in self.data:
            return None
        return self.data[index]

    def __repr__(self):
        string = ""
        for db in self.data:
            string = string + db + " : " + self.data[db] + "\n"
        return string

    def __iter__(self):
        for db in self.data:
            yield db
