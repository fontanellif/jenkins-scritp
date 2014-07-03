#!/usr/bin/python

import os, os.path
import sys, getopt
import sys, commands, fcntl, errno
import shutil
import glob
import subprocess
import re
import time
from datetime import datetime, timedelta

#
# Dev elopement variable
#

debug = True
trace = True

#=============================================
#=            					Global variables							    =
#=============================================

g_app_name = None 				# executed application name
g_build_dir_path = None			# Absolute path of build directory

g_created_output_file = False		#Enable or disable the creation of output file
g_outputfile = None				# Absolute path plus name of the output file
g_fd_out = None					# Output file descriptor

g_enable_check_log = False		# Enable or disable the process of check inside the stdout and stderr of the application tests
g_check_log_filter = ['ERROR','WARNING']

# Catch the current execution dir
g_current_dir = os.path.dirname(os.path.realpath(__file__))

#=============================================
#=            					Utility functions							    =
#=============================================

def checking_exit(exit_state = 0):
	sys.exit(exit_state)

########################

def trim(str):
	return str.strip(' \t\n\r')

########################

def mkdir_p(path):
	try:
		os.makedirs(path)
	except OSError as exc: # Python >2.5
		if exc.errno == errno.EEXIST:
			pass
		else: raise

########################

def file_exists(path):
	if os.path.isfile(path) and os.access(path, os.W_OK):
		return True
	else:
		return False

########################

def exe_exists(path):
	if os.path.isfile(path) and os.access(path, os.X_OK):
		return True
	else:
		return False

########################

def help(exit_state=0):
	print 'check_log.py -i <appname> -d<builddirectory> -o <outputfile>'
	sys.exit(exit_state)
	pass


#=============================================
#=           				 Command line  functions			                =
#=============================================

def parse_command_line_option(argv):
	global g_app_name
	global g_build_dir_path
	global g_outputfile
	global g_enable_check_log
	global g_check_log_filter

	if trace: print 'TRACE: Parsing command line option'

	if debug:
		print 'Number of arguments:', len(sys.argv), 'arguments.'
		print 'Argument List:', str(sys.argv)
		pass

	try:
		opts, args = getopt.getopt(argv,"lhi:d:o:",["enable_check_log=","app_name=","build_dir=","output_file="])
	except getopt.GetoptError:
		help(2)

	for opt, arg in opts:
		if opt == '-h':
			help()
		elif opt in ("-i", "--app_name"):
			g_app_name = trim(arg)
		elif opt in ("-d", "--build_dir"):
			g_build_dir_path = trim(arg)
		elif opt in ("-o", "--output_file"):
			g_outputfile = trim(arg)
		elif opt in ("-l", "--enable_check_log"):
			g_enable_check_log = True

	if ( (g_app_name == None)  or (g_build_dir_path == None) ):
		print ' ERROR: Missing some mandatory parameters'
		help(1)
		pass

	if debug:
		print 'App name is "', g_app_name
		print 'Build directory is ', g_build_dir_path
		print 'Output file is "', g_outputfile
		if g_enable_check_log:
			print 'Enabled check log'
			print 'Check filter:', g_check_log_filter
			pass
	pass

########################

def check_paramenters():
	global g_app_name
	global g_build_dir_path
	global g_outputfile
	global g_enable_check_log
	global g_check_log_filter
	global g_current_dir

	print g_current_dir
	print g_app_name

	if trace: print 'TRACE: Checking parameters'


	if not g_build_dir_path.endswith('/') :
		if debug : print 'Fix end character of build directory path'
		g_build_dir_path = g_build_dir_path + '/'
		pass

	if not g_build_dir_path.startswith('/') and not g_build_dir_path.startswith('.') :
		if debug : print 'Fix start character of build directory path'
		g_build_dir_path = g_current_dir + '/' + g_build_dir_path
		pass

	if not exe_exists(g_build_dir_path+g_app_name):
		print 'ERROR: Missing exe file: ', g_build_dir_path+g_app_name
		checking_exit(1)
		pass

	if debug : print g_build_dir_path+g_app_name

	pass

#=============================================
#=           				 Output file  functions				                =
#=============================================

def open_output_file():
	global g_outputfile
	global g_fd_out
	current_time = time.time()
	print 'current_time:' , current_time
	try:
		g_fd_out = open(g_outputfile, "w")
	except IOError:
		print "ERROR: Unable to create file on disk." , g_outputfile
		checking_exit(2)
	pass

########################

def close_output_file():
	global g_fd_out
	g_fd_out.close()
	pass

########################

def print_output_file(text):
	global g_created_output_file
	global g_fd_out

	if not g_created_output_file:  create_output_file()
	try:
		g_fd_out.write(text)
	except IOError:
		print "ERROR: Unable to write in file.", g_outputfile
		checking_exit(2)
	pass


#=============================================
#=           				 Test application  functions			                =
#=============================================

def test_application(options = None):
	global g_app_name
	global g_build_dir_path

	if options == None:
		print "ERROR: Missing application options"
		checking_exit(2)

	ret = {}
	proc = None
	pid = None
	cmd = None

	cmd = '.' + g_build_dir_path + g_app_name + ' ' + options
	if trace: print 'TRACE: Exe command: ' , cmd
	try:
		proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
		ret['pid'] = proc.pid
		(ret['stdout'], ret['stderr']) = proc.communicate()
		ret['exit_code'] = proc.returncode
	except Exception as e:
		print "ERROR: ",e
	pass

	return ret
	pass

#=============================================
#=           				 		Main functions 				                =
#=============================================

def main(argv):
	global g_app_name
	global g_build_dir_path
	global g_outputfile

	output_test = None

	if trace: print 'TRACE: Start checking process'

	parse_command_line_option(argv)
	check_paramenters()
	output_test =  test_application('--version')
	if output_test['exit_code'] != 0 :
		print output_test
	output_test =  test_application('-h')
	if output_test['exit_code'] != 0 :
		print output_test


#=============================================
# Do not remove

if __name__ == "__main__":
   main(sys.argv[1:])

