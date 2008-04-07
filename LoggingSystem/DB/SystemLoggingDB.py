# $Header: /tmp/libdirac/tmp.stZoy15380/dirac/DIRAC3/DIRAC/LoggingSystem/DB/SystemLoggingDB.py,v 1.13 2008/04/07 18:53:16 mseco Exp $
__RCSID__ = "$Id: SystemLoggingDB.py,v 1.13 2008/04/07 18:53:16 mseco Exp $"
""" SystemLoggingDB class is a front-end to the Message Logging Database.
    The following methods are provided

    insertMessageIntoSystemLoggingDB()
    getMessagesByDate()
    getMessagesByFixedText()
    getMessages()
"""    

import re, os, sys, string
import time
import threading

from DIRAC.Core.Utilities.ClassAd.ClassAdLight import ClassAd
from types                                     import *
from DIRAC                                     import gLogger, gConfig, S_OK, S_ERROR
from DIRAC.Core.Base.DB import DB
from DIRAC.Core.Utilities import Time, dateTime, hour, date, week, day, fromString, toString
from DIRAC.LoggingSystem.private.LogLevels import LogLevels

###########################################################
class SystemLoggingDB(DB):

  def __init__(self, maxQueueSize=10):
    """ Standard Constructor
    """
    DB.__init__( self, 'SystemLoggingDB', 'Logging/SystemLoggingDB',
                 maxQueueSize)

  def __buildCondition(self, condDict, older=None, newer=None ):
    """ build SQL condition statement from provided condDict
        and other extra conditions
    """
    from types import ListType, StringTypes
    condition = ''
    conjonction = ''

    if condDict:
      for attrName, attrValue in condDict.items():
        preCondition = ''
        conjonction = ''
        if type( attrValue ) in StringTypes:
          attrValue = [ attrValue ]
        elif not type( attrValue ) is ListType:
          errorString = 'The values of conditions should be strings or lists'
          errorDesc = 'The type provided was: %s' % type ( attrValue )
          gLogger.error( errorString, errorDesc )
          return S_ERROR( '%s: %s' % ( errorString, errorDesc ) )
        
        for attrVal in attrValue:
          preCondition = "%s%s %s='%s'" % ( preCondition,
                                             conjonction,
                                             str( attrName ),
                                             str( attrVal ) )
          conjonction = " OR"

        if condition:
          condition += " AND" 
        condition += ' (%s )' % preCondition

      conjonction = " AND"
      
    if older:
      condition = "%s%s MessageTime<'%s'" % ( condition,
                                                conjonction,
                                                str( older ) )
      conjonction = " AND"

    if newer:
      condition = "%s%s MessageTime>'%s'" % ( condition,
                                                conjonction,
                                                str( newer ) )

    if condition:
      condition = " WHERE%s" % condition
      
    return S_OK(condition)

  def _buildConditionTest(self, condDict, olderDate = None, newerDate = None ):
    """ a wrapper to the private function __buildCondition so test programs
        can access it
    """
    return self.__buildCondition( condDict, older = olderDate,
                                  newer = newerDate )

  def __removeVariables( self, fieldList ):
    """ Auxiliar function of __buildTableList. It substitutes all the
        variables that share the same table by just one of them.
    """
    addTimeKey = True
    addOwnerKey = True
    addIPkey = True

    internalList = self.__uniq( list( set( fieldList ) ) )

    if internalList.count( 'MessageTime' ): addTimeKey = False
    if internalList.count( 'VariableText' ):
      internalList.remove( 'VariableText' )
      if addTimeKey:
        internalList.append( 'MessageTime' )
        addTimeKey = False

    if internalList.count( 'LogLevel' ):
      internalList.remove( 'LogLevel' )
      if addTimeKey:
        internalList.append( 'MessageTime' )

    if internalList.count( 'OwnerDN' ): addOwnerKey = False
    if internalList.count( 'OwnerGroup' ):
      internalList.remove( 'OwnerGroup' )
      if addOwnerKey:
        internalList.append( 'OwnerDN' )

    if internalList.count( 'ClientIPNumberString' ): addIPKey = False
    if internalList.count( 'ClientFQDN' ):
      internalList.remove( 'ClientFQDN' )
      if addIPKey:
        internalList.append( 'ClientIPNumberString' )

    return internalList 

  def __uniq( self, array ):
    """http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52560
    """

    arrayLength = len( array )
    if arrayLength == 0:
        return []

    sortDictionary = {}

    for key in array:
      sortDictionary[ key ] = 1
    return sortDictionary.keys()

      
  def __buildTableList( self, showFieldList ):
    """ build the SQL list of tables needed for the query
        from the list of variables provided
    """
    import re
    iDpattern = re.compile( r'ID' )   
    tableDict = { 'MessageTime':'MessageRepository',
                  'FixedTextString':'FixedTextMessages',
                  'SystemName':'Systems', 'SubSystemName':'SubSystems',
                  'OwnerDN':'UserDNs',  
                  'ClientIPNumberString':'ClientIPs', 'SiteName':'Sites'}

    conjunction = ' NATURAL JOIN '

    if len(showFieldList):
      fieldList=self.__removeVariables( showFieldList )

      if len(fieldList) == 1:
        tableString = tableDict[fieldList[0]]
      else:
        if fieldList.count('MessageTime'):
          fieldList.remove('MessageTime')
        tableString = 'MessageRepository'

        for field in fieldList:
          if not iDpattern.search( field):
            tableString = '%s%s%s' % ( tableString, conjunction,
                                       tableDict[ field ] )

    else:
      tableString = conjunction.join( tableDict.values() )

    return tableString

  def __queryDB( self, showFieldList=None, condDict=None,
                 older=None, newer=None, count=False ):
    """ This function composes the SQL query from the conditions provided and
        the desired columns and queries the SystemLoggingDB.
        If no list is provided the default is to use all the meaninful
        variables of the DB
    """
    result = self.__buildCondition( condDict, older, newer )
    if not result['OK']: return result
    condition = result['Value']
    
    if not showFieldList:
      showFieldList = ['MessageTime', 'LogLevel', 'FixedTextString',
                     'VariableText', 'SystemName', 
                     'SubSystemName', 'OwnerDN', 'OwnerGroup',
                     'ClientIPNumberString','SiteName']
    elif type( showFieldList ) in StringTypes:
      showFieldList = [ showFieldList ]

    tableList = self.__buildTableList(showFieldList)
    if count:
      showFieldList = [ 'count(*)' ]
      
    cmd = 'SELECT %s FROM %s %s' % (','.join(showFieldList),
                                    tableList, condition)

    return self._query(cmd)

  def __DBCommit( self, tableName, outFields, inFields, inValues ):
    """  This is an auxiliary function to insert values on a
         satellite Table if they do not exist and returns
         the unique KEY associated to the given set of values
    """
    result = self._getFields( tableName, outFields, inFields, inValues )
    if not result['OK']:
      return S_ERROR('Unable to query the database')
    elif result['Value']==():
      result = self._insert( tableName, inFields, inValues )
      if not result['OK']:
        return S_ERROR( 'Could not insert the data into %s table' % tableName )

      result = self._getFields( tableName, outFields, inFields, inValues )
      if not result['OK']:
        return S_ERROR( 'Unable to query the database' )

    return S_OK( int( result['Value'][0][0] ) )
      
  def _insertMessageIntoSystemLoggingDB( self, message, site, nodeFQDN, 
                                         userDN, userGroup, remoteAddress ):
    """ This function inserts the Log message into the DB
    """
    messageDate = Time.toString( message.getTime() )
    messageDate = messageDate[:messageDate.find('.')]
    messageName = message.getName()
    messageSubSystemName = message.getSubSystemName()
    
    fieldsList = [ 'MessageTime', 'VariableText' ]
    messageList = [ messageDate, message.getVariableMessage() ]

    inValues = [ userDN, userGroup ]
    inFields = [ 'OwnerDN', 'OwnerGroup' ]
    outFields = [ 'UserDNID' ]
    result = self.__DBCommit( 'UserDNs', outFields, inFields, inValues)
    if not result['OK']:
      return result
    messageList.append(result['Value'])
    fieldsList.extend( outFields )
      
    inValues = [ remoteAddress, nodeFQDN ]
    inFields = [ 'ClientIPNumberString', 'ClientFQDN' ]
    outFields = [ 'ClientIPNumberID' ]
    result = self.__DBCommit( 'ClientIPs', outFields, inFields, inValues)
    if not result['OK']:
      return result
    messageList.append(result['Value'])
    fieldsList.extend( outFields )

    if not site:
      site = 'Unknown'
    inFields = [ 'SiteName' ]
    inValues = [ site ]
    outFields = [ 'SiteID' ]
    result = self.__DBCommit( 'Sites', outFields, inFields, inValues)
    if not result['OK']:
      return result
    messageList.append(result['Value'])
    fieldsList.extend( outFields )

    messageList.append(message.getLevel())
    fieldsList.append( 'LogLevel' )
    
    inFields = [ 'FixedTextString' ]
    inValues = [ message.getFixedMessage() ]
    outFields = [ 'FixedTextID' ]
    result = self.__DBCommit( 'FixedTextMessages', outFields, inFields,
                              inValues)
    if not result['OK']:
      return result
    messageList.append( result['Value'] )
    fieldsList.extend( outFields )

    if not messageName:
      messageName = 'Unknown'
    inFields = [ 'SystemName' ]
    inValues = [ messageName ]
    outFields = [ 'SystemID' ]
    result = self.__DBCommit( 'Systems', outFields, inFields, inValues)
    if not result['OK']:
      return result
    messageList.append(result['Value'])
    fieldsList.extend( outFields )

    if not messageSubSystemName:
      messageSubSystemName = 'Unknown'
    inFields = [ 'SubSystemName' ]
    inValues = [ messageSubSystemName ]
    outFields = [ 'SubSystemID' ]
    result = self.__DBCommit( 'SubSystems', outFields, inFields, inValues )
    if not result['OK']:
      return result
    messageList.append(result['Value'])
    fieldsList.extend( outFields )

    return self._insert( 'MessageRepository', fieldsList, messageList )

  def _insertDataIntoAgentTable(self, agentName, data):
    """Insert the persistent data needed by the agents running on top of
       the SystemLoggingDB.
    """
    outFields = ['AgentID']
    inFields = [ 'AgentName' ]
    inValues = [ agentName ]
    result = self._getFields('AgentPersitentData', outFields, inFields, inValues)
    if not result ['OK']:
      return result
    elif result['Value'] == ():
      inFields = [ 'AgentName', 'AgentData' ]
      inValues = [ agentName, data]
      result=self._insert( 'AgentPersitentData', inFields, inValues )
      if not result['OK']:
        return result
    escapeData = self._escapeString( data )
    cmd = "UPDATE LOW PRIORITY AgentPersitentData SET AgentData='%s' WHERE AgentID=%s" % \
          ( agentName, result['Value'] )
    return self._query(update)
    
    
  def getMessagesByDate(self, initialDate = None, endDate = None):
    """ Query the database for all the messages between two given dates.
        If no date is provided then the records returned are those generated
        during the last 24 hours.
    """
    from DIRAC.Core.Utilities import dateTime, day

    if not (initialDate or endDate):
      initialDate= dateTime() - 1 * day 
      
    return self.__queryDB( newer = initialDate, older = endDate )

  def getMessagesByFixedText( self, texts, initialDate = None, endDate = None ):
    """ Query the database for all messages whose fixed part match 'texts'
        that were generated between initialDate and endDate
    """
    return self.__queryDB( condDict = {'FixedTextString': texts},
                           older = endDate, newer = initialDate )
    
  def getMessagesBySite(self, site, initialDate = None, endDate = None ):
    """ Query the database for all messages generated by 'site' that were
        generated between initialDate and endDate     
    """
    return self.__queryDB( condDict = { 'SiteName':  site},
                           older = endDate, newer = initialDate )
 
  def getMessagesByUser(self, userDN, initialDate = None, endDate = None ):
    """ Query the database for all messages generated by the user: 'userDN' 
        that were generated between initialDate and endDate     
    """
    return self.__queryDB( condDict = { 'OwnerDN':  userDN},
                           older = endDate, newer = initialDate )
 
  def getMessagesByGroup(self, group, initialDate = None, endDate = None ):
    """ Query the database for all messages generated by the group 'Group'
        that were generated between initialDate and endDate     
    """
    return self.__queryDB( condDict = { 'OwnerGroup':  group},
                           older = endDate, newer = initialDate )

  def getMessagesBySiteNode(self, node, initialDate = None, endDate = None ):
    """ Query the database for all messages generated at 'node' that were
        generated between initialDate and endDate     
    """
    return self.__queryDB( condDict = { 'ClientFDQN':  node},
                           older = endDate, newer = initialDate )

  def getMessages(self, showFields = [], conds = {} , initialDate = None,
                  endDate = None ):
    """ Query the database for all messages satisfying 'conds' that were 
        generated between initialDate and endDate
    """
    return self.__queryDB( showFieldList = showFields, condDict = conds,
                           older = endDate, newer = initialDate )


  def getCountMessages( self, conds = {}, initialDate = None, 
                        endDate = None ):
    """ Query the database for the number of messages that match 'conds' and
        were generated between initialDate and endDate. If no condition is
        provided it returns the total number of messages present in the
        database
    """
    if conds:
      fieldList = conds.keys()
      fieldList.append( 'MessageTime' )
    else:
      fieldList = {}

    returnValue = self.__queryDB( showFieldList = fieldList, condDict = conds, 
                                  older = endDate, newer = initialDate, 
                                  count = True )
    if not returnValue['OK']:
      return returnValue
    
    return S_OK(returnValue['Value'][0][0])

  def getSites( self ):
    return self.__queryDB( showFieldList = [ 'SiteName' ] )
  
  def getSystems( self ):
    return self.__queryDB( showFieldList = [ 'SystemName' ] )
  
  def getSubSystems( self ):
    return self.__queryDB( showFieldList = [ 'SubSystemName' ] )

  def getGroups( self ):
    return self.__queryDB( showFieldList = [ 'OwnerGroup' ] )

  def getFixedTextStrings( self ):
    return self.__queryDB( showFieldList = [ 'FixedTextString' ] )
