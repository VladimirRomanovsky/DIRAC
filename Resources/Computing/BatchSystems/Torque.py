#########################################################################################
# $HeadURL$
# Torque.py
# 10.11.2014
# Author: A.T.
#########################################################################################

""" Torque.py is a DIRAC independent class representing Torque batch system.
    Torque objects are used as backend batch system representation for
    LocalComputingElement and SSHComputingElement classes 
"""

__RCSID__ = "$Id$"

import commands, os

class Torque( object ):

  def submitJob( self, **kwargs ):
    """ Submit nJobs to the Torque batch system
    """
    
    resultDict = {}
    
    MANDATORY_PARAMETERS = [ 'Executable', 'OutputDir', 'ErrorDir',
                             'Queue', 'SubmitOptions' ]

    for argument in MANDATORY_PARAMETERS:
      if not argument in kwargs:
        resultDict['Status'] = -1
        resultDict['Message'] = 'No %s' % argument
        return resultDict
    
    nJobs = kwargs.get( 'NJobs' )
    if not nJobs:
      nJobs = 1
    
    jobIDs = []
    status = -1
    for _i in range( int(nJobs) ):
      cmd = "qsub -o %(OutputDir)s -e %(ErrorDir)s -q %(Queue)s -N DIRACPilot %(SubmitOptions)s %(Executable)s" % kwargs
      status,output = commands.getstatusoutput(cmd)
      if status == 0:
        jobIDs.append(output)
      else:
        break                                                         
  
    if jobIDs:
      resultDict['Status'] = 0
      resultDict['Jobs'] = jobIDs
    else:
      resultDict['Status'] = status
      resultDict['Message'] = output
    return resultDict
    
  def getJobStatus( self, **kwargs ):
    """ Get the status information for the given list of jobs
    """
    
    resultDict = {}
    
    MANDATORY_PARAMETERS = [ 'JobIDList' ]
    for argument in MANDATORY_PARAMETERS:
      if not argument in kwargs:
        resultDict['Status'] = -1
        resultDict['Message'] = 'No %s' % argument
        return resultDict   
      
    jobIDList = kwargs['JobIDList']  
    if not jobIDList:
      resultDict['Status'] = -1
      resultDict['Message'] = 'Empty job list'
      return resultDict
    
    jobDict = {}
    for job in jobIDList:
      if not job:
        continue
      jobNumber = job.split( '.' )[0]
      jobDict[jobNumber] = job

    cmd = 'qstat ' + ' '.join( jobIDList )
    status, output = commands.getstatusoutput( cmd )
    
    if status != 0:
      resultDict['Status'] = status
      resultDict['Output'] = output
      return resultDict

    statusDict = {}
    output = output.replace( '\r', '' )
    lines = output.split( '\n' )
    for job in jobDict:
      statusDict[jobDict[job]] = 'Unknown'
      for line in lines:
        if line.find( job ) != -1:
          if line.find( 'Unknown' ) != -1:
            statusDict[jobDict[job]] = 'Unknown'
          else:
            torqueStatus = line.split()[4]
            if torqueStatus in ['E', 'C']:
              statusDict[jobDict[job]] = 'Done'
            elif torqueStatus in ['R']:
              statusDict[jobDict[job]] = 'Running'
            elif torqueStatus in ['S', 'W', 'Q', 'H', 'T']:
              statusDict[jobDict[job]] = 'Waiting'

    # Final output
    status = 0
    resultDict['Status'] = 0
    resultDict['Jobs'] = statusDict 
    return resultDict   
  
  def getCEStatus( self, **kwargs ):

    """ Get the overall CE status
    """
  
    resultDict = {}
  
    user = kwargs.get( 'User' )
    if not user:
      user = os.environ.get( 'USER' )
    if not user:
      resultDict['Status'] = -1
      resultDict['Message'] = 'No user name'
      return resultDict
  
    cmd = 'qselect -u %s -s WQ | wc -l; qselect -u %s -s R | wc -l' % ( user, user )
    status, output = commands.getstatusoutput( cmd )
  
    if status != 0:
      resultDict['Status'] = status
      resultDict['Output'] = output
      return resultDict
  
    waitingJobs, runningJobs = output.split()[:2]
  
    # Final output
    resultDict['Status'] = 0
    resultDict["Waiting"] = waitingJobs
    resultDict["Running"] = runningJobs
    return resultDict
  
  def killJob( self, **kwargs ):
    """ Kill all jobs in the given list
    """
    
    resultDict = {}
    
    MANDATORY_PARAMETERS = [ 'JobIDList' ]
    for argument in MANDATORY_PARAMETERS:
      if not argument in kwargs:
        resultDict['Status'] = -1
        resultDict['Message'] = 'No %s' % argument
        return resultDict   
      
    jobIDList = kwargs['JobIDList']  
    if not jobIDList:
      resultDict['Status'] = -1
      resultDict['Message'] = 'Empty job list'
      return resultDict
    
    successful = []
    failed = []
    for job in jobIDList:
      status, output = commands.getstatusoutput( 'qdel %s' % job )
      if status != 0:
        failed.append( job )
      else:
        successful.append( job )  
    
    resultDict['Status'] = 0
    if failed:
      resultDict['Status'] = 1
      resultDict['Message'] = output
    resultDict['Successful'] = successful
    resultDict['Failed'] = failed
    return resultDict
  
  def getJobOutputFiles( self, jobStamp, outputDir, errorDir ):
    """ Get output file names for the specific CE 
    """
    output = '%s/DIRACPilot.o%s' % ( outputDir, jobStamp )
    error = '%s/DIRACPilot.e%s' % ( errorDir, jobStamp )
    return ( output, error )  
  