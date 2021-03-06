__RCSID__ = "$Id$"

# FIXME: if it requires a dirac.cfg it is not a unit test and should be moved to tests directory

from DIRAC.Core.Base.Script import parseCommandLine
parseCommandLine()

import unittest
from DIRAC.Resources.Storage.StorageFactory import StorageFactory

class StorageFactoryTestCase( unittest.TestCase ):
  """ Base class for the StorageFactory test cases
  """

  """
  def test_getStorageName(self):
    factory = StorageFactory()
    initialName = 'RAWFileDestination'
    res = factory.getStorageName(initialName)
    self.assert_(res['OK'])
    self.assertEqual(res['Value'],'CERN-tape')
  """

  def test_getStorage( self ):

    storageDict = {}
    storageDict['StorageName'] = 'IN2P3-disk'
    storageDict['PluginName'] = 'SRM2'
    storageDict['Protocol'] = 'srm'
    storageDict['Host'] = 'ccsrmtestv2.in2p3.fr'
    storageDict['Port'] = '8443'
    storageDict['WSUrl'] = '/srm/managerv2?SFN='
    storageDict['Path'] = '/pnfs/in2p3.fr/data'
    storageDict['SpaceToken'] = 'LHCb_FAKE'
    factory = StorageFactory( vo = 'lhcb' )
    res = factory.getStorage( storageDict )
    self.assert_( res['OK'] )
    storageStub = res['Value']
    parameters = storageStub.getParameters()
    self.assertEqual( parameters, storageDict )

    res = storageStub.getTransportURL( '/lhcb/user' )
    self.assert_( res['OK'] )
    self.assertEqual( res['Value']['Successful']['/lhcb/user'], 'srm://ccsrmtestv2.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/user' )

  def test_getStorages( self ):
    factory = StorageFactory( vo = 'lhcb' )
    storageName = 'IN2P3-disk'
    protocolList = ['SRM2']
    res = factory.getStorages( storageName, protocolList )
    self.assert_( res['OK'] )
    storageStubs = res['Value']['StorageObjects']
    storageStub = storageStubs[0]

    storageDict = {}
    storageDict['StorageName'] = 'IN2P3-disk'
    storageDict['PluginName'] = 'SRM2'
    storageDict['Protocol'] = 'srm'
    storageDict['Host'] = 'ccsrm02.in2p3.fr'
    storageDict['Port'] = '8443'
    storageDict['WSUrl'] = '/srm/managerv2?SFN='
    storageDict['Path'] = '/pnfs/in2p3.fr/data/lhcb'
    storageDict['SpaceToken'] = ''
    parameterDict = storageStub.getParameters()
    self.assertEqual( parameterDict, storageDict )

    res = storageStub.getTransportURL( '/lhcb/production/DC06/test.file' )
    self.assert_( res['OK'] )
    self.assertEqual( res['Value'], 'srm://ccsrm02.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/production/DC06/test.file' )

    res = storageStub.removeFile( 'srm://ccsrm02.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/production/DC06/test.file' )
    listOfDirs = ['srm://ccsrm02.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/production/DC06/v1-lumi2/00001368/DIGI']
    res = storageStub.listDirectory( listOfDirs )

    #directoryPath = 'srm://ccsrmtestv2.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/production/DC06/v1-lumi2/1368'
    #res = storageStub.removeDir(directoryPath)

    destFile = 'srm://ccsrmtestv2.in2p3.fr:8443/srm/managerv2?SFN=/pnfs/in2p3.fr/data/lhcb/production/DC06/v1-lumi2/1368/dirac_directory.7'
    res = storageStub.putFile( destFile )
    print res

    res = storageStub.getFile( destFile )

if __name__ == '__main__':
  suite = unittest.defaultTestLoader.loadTestsFromTestCase( StorageFactoryTestCase )
  #suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(CreateFTSReqCase))
  testResult = unittest.TextTestRunner( verbosity = 2 ).run( suite )
