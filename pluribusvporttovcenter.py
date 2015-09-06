#!/usr/bin/python

# Based on getallvms.py

"""
Python program for listing the vms with all IP's and MAC address combination on an ESX / vCenter host if the VM is up
The Python Program then also programs the VM Name, Guest OS in the Pluribus vPORT Endpoint MetaData Database
The Code has some additional things to expand the code for complex VMware deployments
"""

from optparse import OptionParser, make_option
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl
from pyVmomi import vim

import pyVmomi
import textwrap
import argparse
import atexit
import sys
import re
import subprocess
import requests
import shlex
requests.packages.urllib3.disable_warnings()

import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

i = 0
#net = pyVmomi.types.vim.vm.GuestInfo.NicInfo()

#print net

def GetArgs():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description='Process args for retrieving all the Virtual Machines')
   parser.add_argument('-s', '--host', required=True, action='store', help='Remote host to connect to')
   parser.add_argument('-o', '--port', default=443,   action='store', help='Port to connect on')
   parser.add_argument('-u', '--user', required=True, action='store', help='User name to use when connecting to host')
   parser.add_argument('-p', '--password', required=True, action='store', help='Password to use when connecting to host')
   parser.add_argument('-n', '--nodes', default='10.9.31.31', action='store', help='IP Address of the vPort SWITCH')
   args = parser.parse_args()
   return args

def printLevel(text, level):

   # indent print, with tree levels
   n = 0
   while n <= level:
      print "\b    ",
      n += 1
   print " I am in print Level Print"
   print text

def iterateTree(item, level):
   """
   Iterate through VM Folders and VirtualApp objects,
   Then print out VM information
   """
   nlevel = level + 1
   # Check for VM folders
   if type(item) == pyVmomi.types.vim.Folder:
      printLevel("`-Folder Name : %s" % (item.name), level)
      # Iterate through objects in that Folder
      for cItem in item.childEntity:
         iterateTree(cItem, nlevel)

   # Check for vApps
   elif type(item) == pyVmomi.types.vim.VirtualApp:
      printLevel("`-vApp Name : %s" % (item.name), level)
      # Iterate through VM in that vApp
      for cItem in item.vm:
         iterateTree(cItem, nlevel)

   else:
      PrintVmInfo(item, level)

def PrintVmInfo(vm, level):
   """
   Print information for a particular virtual machine.
   """
   summary = vm.summary
   GuestOS = ''.join(e for e in summary.config.guestFullName if e.isalnum())
   vm_networks = vm.guest.net
   for net in vm_networks:
       if net.macAddress:
           macadd = net.macAddress
           if net.ipAddress:
               getipv4 = net.ipAddress
               args = GetArgs()
               nodes = args.nodes
               print '#' * 150
               print "vCenter Information: IP is: " + getipv4[0] + " mac is: " + net.macAddress + " vm name is: " + summary.config.name + " OS type is: " + GuestOS
               print '#' * 150
               print "                                                      Before Updating vPORT Database"
               print '#' * 150
               vportshow = '/usr/bin/cli --quiet --host ' + nodes + ' --user network-admin:test123 vport-show mac ' + macadd
               cmd = shlex.split(vportshow)
               print '#' * 150
               p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
               out, err = p.communicate();
               if out:
                   print(out)
               if err:
                   print ("ERROR found")
                   print (err)
               print '#' * 150
               print "                                                      Updating vPORT Database"
               print '#' * 150
               vportshow1 = 'cli --quiet --host ' + nodes + ' --user network-admin:test123 vport-modify vlan 222 mac ' + net.macAddress + ' ip ' + getipv4[0]  + '  hostname ' + summary.config.name + ' os ' + GuestOS
               cmd1 = shlex.split(vportshow1)
               p = subprocess.Popen(cmd1, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
               out, err = p.communicate();
               #if out:
                #   print(out)
               #if err:
                #   print ("ERROR found")
                 #  print (err)
               print "                                                      After Updating vPORT Database"
               print '#' * 150
               vportshow = '/usr/bin/cli --quiet --host ' + nodes + ' --user network-admin:test123 vport-show mac ' + macadd
               cmd = shlex.split(vportshow)
               p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
               out, err = p.communicate();
               if out:
                   print(out)
               if err:
                   print ("ERROR found")
                   print (err)
       else:
           print "No MAC or IP found"

def main():
   """
   Simple command-line program for listing the virtual machines on a system.
   """
   args = GetArgs()
   try:
      si = None
      try:
         si = SmartConnect(
            host  = args.host,
            user  = args.user,
            pwd   = args.password,
            port  = int(args.port)
         )
      except IOError, e:
        pass
      if not si:
         print "Could not connect to the specified host using specified username and password"
         return -1

      atexit.register(Disconnect, si)

      content = si.RetrieveContent()
      datacenter = content.rootFolder.childEntity[0]
      vmFolder = datacenter.vmFolder
      vmFolderList = vmFolder.childEntity

      for curItem in vmFolderList:
         iterateTree(curItem, 0)

   except vmodl.MethodFault, e:
      print "Caught vmodl fault : " + e.msg
      return -1
   except Exception, e:
      print "Caught exception : " + str(e)
      return -1

   return 0

# Start program
if __name__ == "__main__":
   main()
