""" The Script class provides a simple way for users to specify an executable
    or file to run (and is also a simple example of a workflow module).
"""

import os
import sys
import re
import stat
import distutils.spawn #pylint: disable=no-name-in-module,no-member,import-error

from DIRAC.Core.Utilities.Subprocess    import shellCall
from DIRAC                              import gLogger

from DIRAC.Workflow.Modules.ModuleBase  import ModuleBase

class Script( ModuleBase ):
  """ Module for running executable
  """

  #############################################################################
  def __init__( self ):
    """ c'tor
    """
    self.log = gLogger.getSubLogger( 'Script' )
    super( Script, self ).__init__( self.log )

    # Set defaults for all workflow parameters here
    self.executable = ''
    self.applicationName = ''
    self.applicationVersion = ''
    self.applicationLog = ''
    self.arguments = ''
    self.workflow_commons = None
    self.step_commons = None

    self.environment = None
    self.callbackFunction = None
    self.bufferLimit = 52428800

  #############################################################################

  def _resolveInputVariables( self ):
    """ By convention the workflow parameters are resolved here.
    """
    super( Script, self )._resolveInputVariables()
    super( Script, self )._resolveInputStep()

    self.arguments = self.step_commons.get( 'arguments', self.arguments )
    if not self.arguments.strip():
      self.arguments = self.workflow_commons.get('arguments', self.arguments)

  #############################################################################

  def _initialize( self ):
    """ simple checks
    """
    if not self.executable:
      raise RuntimeError( 'No executable defined' )

  def _setCommand( self ):
    """ set the command that will be executed
    """
    self.command = self.executable
    if os.path.exists( os.path.basename( self.executable ) ):
      self.executable = os.path.basename( self.executable )
      if not os.access( '%s/%s' % ( os.getcwd(), self.executable ), 5 ):
        os.chmod( '%s/%s' % ( os.getcwd(), self.executable ), stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH )
      self.command = '%s/%s' % ( os.getcwd(), self.executable )
    elif re.search( '.py$', self.executable ):
      self.command = '%s %s' % ( sys.executable, self.executable )
    elif distutils.spawn.find_executable( self.executable ): #pylint: disable=no-member
      self.command = self.executable

    if self.arguments:
      self.command = '%s %s' % ( self.command, self.arguments )

    self.log.info( 'Command is: %s' % self.command )

  def _executeCommand( self ):
    """ execute the self.command (uses shellCall)
    """
    failed = False

    outputDict = shellCall( 0, self.command,
                            env = self.environment,
                            callbackFunction = self.callbackFunction,
                            bufferLimit = self.bufferLimit )
    if not outputDict['OK']:
      failed = True
      self.log.error( 'Shell call execution failed:', '\n' + str( outputDict['Message'] ) )
    status, stdout, stderr = outputDict['Value'][0:3]
    if status:
      failed = True
      self.log.error( "Non-zero status while executing", "%s: %s" % ( status, self.command ) )
    else:
      self.log.info( "%s execution completed with status %s" % ( self.executable, status ) )

    self.log.verbose( stdout )
    self.log.verbose( stderr )
    if os.path.exists( self.applicationLog ):
      self.log.verbose( 'Removing existing %s' % self.applicationLog )
      os.remove( self.applicationLog )
    fopen = open( '%s/%s' % ( os.getcwd(), self.applicationLog ), 'w' )
    fopen.write( "<<<<<<<<<< %s Standard Output >>>>>>>>>>\n\n%s " % ( self.executable, stdout ) )
    if stderr:
      fopen.write( "<<<<<<<<<< %s Standard Error >>>>>>>>>>\n\n%s " % ( self.executable, stderr ) )
    fopen.close()
    self.log.info( "Output written to %s, execution complete." % ( self.applicationLog ) )

    if failed:
      raise RuntimeError( "'%s' Exited With Status %s" % ( os.path.basename( self.executable ).split('_')[0], status ) )


  def _finalize( self ):
    """ simply finalize
    """
    applicationString = os.path.basename( self.executable ).split('_')[0]
    if self.applicationName and self.applicationName.lower() != 'unknown':
      applicationString += ' (%s %s)' % ( self.applicationName, self.applicationVersion )
    status = "%s successful" % applicationString

    super( Script, self )._finalize( status )
