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

debug = False
trace = False

#########################################################
#=            					Global variables							    =
#########################################################

g_exit = 0							#Final exit state

g_app_name = None 				# executed application name
g_build_dir_path = None			# Absolute path of build directory
g_test_options = ['--version','-h']


g_created_output_file = False		#Enable or disable the creation of output file
g_outputfile = None				# Absolute path plus name of the output file
g_fd_out = None					# Output file descriptor


g_enable_check_log = False		# Enable or disable the process of check inside the stdout and stderr of the application tests
g_check_log_filter = ['ERROR','WARNING']
g_check_log_to_skip = [	'license',
							'no error',
							'ERROR: *',
							'WARNING: No interfaces available']
# Catch the current execution dir
g_current_dir = os.getcwd()

#test new features
g_tests = [ {'option' : "--version", "filter" : ['ERROR','WARNING'] , 'to_skip': ['license'] } ,
			{'option' : "-h", "filter" : ['ERROR','WARNING'] , 'to_skip': ['license'] }  ]

#########################################################
#=            					Utility functions							    =
#########################################################

def checking_exit(exit_state = 0):
	print "DEBUG: Exit code:", exit_state
	sys.exit(exit_state)

########################

def trim(str):
	return str.strip(' \t\n\r')

########################

def print_list_error(p_list):
	for x in p_list:
		print x
		pass

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

	print 'test.py -i <appname> -d<builddirectory>'
	print '           -l 	|	 -- enable_check_log			| enable_check_log'
	print '           -o 	| 	--output_file <todo>  		| create log file'
	print '           -v 	| 	--verbose			    			| verbose mode'
	sys.exit(exit_state)
	pass

########################

def getCmd(app_name=None, options =None):
	if (app_name == None) or (options == None):
		return ''
	else:
		return './' + app_name + ' ' + options
		pass
	pass

########################

def grep(m,s,v=[]):
	l_lines = s.splitlines()
	l_found = []

	for line in l_lines:
		l_to_skip = False

		for less in v:
			if (less in line):
				l_to_skip = True
				continue

		if l_to_skip: continue

		if (m.lower() in line) or (m.upper() in line): l_found.append(line)

	return l_found


#########################################################
#=           				 Command line  functions			                =
#########################################################

def parse_command_line_option(argv):
	global g_app_name
	global g_build_dir_path
	global g_outputfile
	global g_enable_check_log
	global g_check_log_filter
	global debug

	if trace: print 'TRACE: Parsing command line option'

	if debug:
		print 'DEBUG: Number of arguments:', len(sys.argv), 'arguments.'
		print 'DEBUG:  Argument List:', str(sys.argv)
		pass

	try:
		opts, args = getopt.getopt(argv,"vlhi:d:o:",["--verbose","enable_check_log=","app_name=","build_dir=","output_file="])
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
		elif opt in ("-v", "--verbose"):
			debug = True

	if ( (g_app_name == None)  or (g_build_dir_path == None) ):
		print ' ERROR: Missing some mandatory parameters'
		help(1)
		pass

	if debug:
		print 'DEBUG: App name is ', g_app_name
		print 'DEBUG: Build directory is ', g_build_dir_path
		print 'DEBUG: Output file is ', g_outputfile
		if g_enable_check_log:
			print 'DEBUG: Enabled check log'
			print 'DEBUG: Check filter:', g_check_log_filter
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

	if debug : print 'DEBUG: ' + g_build_dir_path+g_app_name

	pass

#########################################################
#=           				 Output file  functions				                =
#########################################################

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


#########################################################
#=           				 Test application  functions			                =
#########################################################

def test_application(options = None):
	global g_app_name
	global g_build_dir_path
	global g_current_dir


	if options == None:
		print "ERROR: Missing application options"
		checking_exit(2)

	ret = {}
	proc = None
	pid = None
	cmd = None

	cmd = getCmd(g_app_name, options)

	os.chdir(g_build_dir_path)

	if trace: print 'TRACE: Go to build directory  ' , g_build_dir_path
	if debug: print 'DEBUG: Directory [Actual: ' + os.getcwd() + ', Script: ' + g_current_dir
	if trace: print 'TRACE: Exe command: ' , cmd

	try:
		proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
		ret['pid'] = proc.pid
		(ret['stdout'], ret['stderr']) = proc.communicate()
		ret['exit_code'] = proc.returncode
	except Exception as e:
		print "ERROR: ",e
	pass

	os.chdir(g_current_dir)

	return ret
	pass


def check_log_output(p_output_test):
	global g_exit
	if g_enable_check_log:

			for filter_str in g_check_log_filter:
				if debug: print "DEBUG: grep ", filter_str
				p_output_test['error'] = 0
				p_output_test['check_log'] = grep(filter_str, p_output_test['stdout'], g_check_log_to_skip)

				if p_output_test['check_log']:
					p_output_test['error'] = 1
					g_exit = 1
				pass


			if p_output_test['error'] == 0:
				print 'OK: Success checking log.'
			else:
				print 'ERROR: Error checking log, found: ' , filter_str
				print_list_error(p_output_test['check_log'])

	return p_output_test
	pass


def do_test():

	global g_check_log_to_skip
	global g_test_options

	tests = []

	for test in g_test_options:
		output_test = None

		print '\nTEST: ' + test
		output_test =  test_application(test)

		if output_test['exit_code'] == 0 :
			print 'OK: Success test.'
		else:
			print 'ERROR: Error test, return code = ', output_test['exit_code']

		output_test = check_log_output(output_test)
		tests.append(output_test)

	return tests
	pass

#########################################################
#=           				 		Main functions 				                =
#########################################################

def main(argv):
	global g_app_name
	global g_build_dir_path
	global g_outputfile
	global g_exit


	if trace: print 'TRACE: Start checking process'

	parse_command_line_option(argv)
	check_paramenters()
	do_test()
	checking_exit(g_exit)

	if trace: print 'TRACE: End checking process'

	pass


#########################################################
# Do not remove

if __name__ == "__main__":
   main(sys.argv[1:])

