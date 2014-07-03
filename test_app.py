#!/usr/bin/python

import os, os.path
import sys, getopt
import sys, commands, fcntl, errno
import shutil
import glob
import subprocess as sub
import re
import time
from datetime import datetime, timedelta
import threading


#
# Dev elopement variable
#

debug = False

#########################################################
#=            					Default values 								    =
#########################################################

g_test_options = ['--version','-h']
g_check_log_to_find = ['ERROR','WARNING']
g_check_log_to_skip = [ ]

#########################################################
#=            					Global variables							    =
#########################################################

g_exit = 0							#Final exit state

g_app_name = None 				# executed application name
g_build_dir_path = None			# Absolute or relative path of build directory
g_test_file = None					# Absolute path of test file. It must contains 1 option (--version or -h) for each line

g_created_output_file = False		#Enable or disable the creation of output file
g_outputfile = None				# Absolute path plus name of the output file
g_fd_out = None					# Output file descriptor

g_enable_check_log = False		# Enable or disable the process of check inside the stdout and stderr of the application tests

# Catch the current execution dir
g_current_dir = os.getcwd()

#########################################################
#=           				 		RunCmd class 	 				                =
#########################################################

class RunCmd(threading.Thread):
	def __init__(self, cmd, timeout):
		threading.Thread.__init__(self)
		self.cmd = cmd
		self.timeout = timeout
		self.stdout = None
		self.stderr = None
		self.exit_code = None

	def run(self):
		self.p = sub.Popen(self.cmd, stdout=sub.PIPE,stderr=sub.PIPE, shell=True)
		self.pid = self.p.pid
		self.p.wait()

	def Run(self):
		self.start()
		self.join(self.timeout)

		if self.is_alive():
			self.p.terminate()      #use self.p.kill() if process needs a kill -9
			self.join()

		(self.stdout , self.stderr) = self.p.communicate()
		self.exit_code = self.p.returncode

#########################################################
#=            					Utility functions							    =
#########################################################

def checking_exit(exit_state = 0):
	print "\nTEST: Exit code:", exit_state
	sys.exit(exit_state)

########################

def read_file_to_list(path):
	content = []

	if file_exists(path):
		with open(path) as f:
    			content = f.readlines()
    		content = [x.strip('\n') for x in content]

    	return content
    	pass

  ########################

def conf_file_exists(path):
	if os.path.isfile(path) and os.access(path, os.R_OK):
		return True
	else:
		print 'ERROR: Unable to find/read: ', path
		checking_exit(1)
		pass

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

	print 'test.py -i <appname> -d<app directory>'
	print ' -t 	| Test file'
	print ' -f	| Find file'
	print ' -s	| Skip file'
	print ' -l 	| Enable_check_log'
	print ' -v 	| Verbose mode'
	print ' -h 	| This help'
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
	global g_check_log_to_find
	global g_test_file
	global g_find_file
	global g_skip_file
	global debug

	try:
		opts, args = getopt.getopt(argv,"vlhi:d:f:s:t:")
	except getopt.GetoptError:
		help(2)

	for opt, arg in opts:
		if opt == '-h':
			help()
		elif opt in "-i":
			g_app_name = trim(arg)
		elif opt in "-d":
			g_build_dir_path = trim(arg)
		elif opt in "-t":
			g_test_file = trim(arg)
			conf_file_exists(g_test_file)
		elif opt in "-f":
			g_find_file = trim(arg)
			conf_file_exists(g_find_file)
		elif opt in "-s":
			g_skip_file = trim(arg)
			conf_file_exists(g_skip_file)
		elif opt in "-l":
			g_enable_check_log = True
		elif opt in "-v":
			debug = True

	if ( (g_app_name == None)  or (g_build_dir_path == None) ):
		print ' ERROR: Missing some mandatory parameters'
		help(1)
		pass

	pass

########################

def check_paramenters():
	global g_app_name
	global g_build_dir_path
	global g_outputfile
	global g_enable_check_log
	global g_check_log_to_find
	global g_check_log_to_skip
	global g_current_dir
	global g_test_options
	global g_test_file
	global g_find_file
	global g_skip_file


	if not g_build_dir_path.endswith('/') :
		# if debug : print 'DEBUG: Fix end character of build directory path'
		g_build_dir_path = g_build_dir_path + '/'
		pass

	if not g_build_dir_path.startswith('/') and not g_build_dir_path.startswith('.') :
		# if debug : print 'DEBUG: Fix start character of build directory path'
		g_build_dir_path = g_current_dir + '/' + g_build_dir_path
		pass

	if not exe_exists(g_build_dir_path+g_app_name):
		print 'ERROR: Missing exe file: ', g_build_dir_path+g_app_name
		checking_exit(1)
		pass

	if g_test_file != None:
		g_test_options = read_file_to_list(g_test_file)
		if debug : print 'DEBUG: Test => ' , g_test_options

	if g_find_file != None:
		g_check_log_to_find = read_file_to_list(g_find_file)
		if debug : print 'DEBUG: Find => ' , g_check_log_to_find

	if g_skip_file != None:
		g_check_log_to_skip = read_file_to_list(g_skip_file)
		if debug : print 'DEBUG: Skip => ' , g_check_log_to_skip

	if debug  : print 'DEBUG: Cmq =>   ' + g_build_dir_path+g_app_name


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

	# if debug:
		# print 'DEBUG: Go to build directory  ' , g_build_dir_path
	 	# print 'DEBUG: Directory [Actual: ' + os.getcwd() + ', Script: ' + g_current_dir

	print 'Cmd:' , cmd

	x = RunCmd(cmd, 30)
	x.Run()
	ret['pid'] = x.pid
	ret['stdout'] = x.stdout
	ret['stderr'] = x.stderr
	ret['exit_code'] = x.exit_code

	if debug:
		print 'Start process information'
		print x.pid
		print x.stdout
		print x.stderr
		print x.exit_code
		print 'End process information'

	os.chdir(g_current_dir)

	return ret
	pass


def check_log_output(p_output_test):
	global g_exit

	l_output_test = p_output_test
	error_found = False
	if g_enable_check_log:

			for filter_str in g_check_log_to_find:

				l_output_test['error'] = 0
				l_output_test['check_log'] = grep(filter_str, l_output_test['stdout'], g_check_log_to_skip)

				if l_output_test['check_log']:
					l_output_test['error'] = 1
					g_exit = 1
				pass


				if l_output_test['error'] == 0:
					print 'OK: Success checking log for', filter_str
				else:
					print 'ERROR: Error checking log, found: ' , filter_str
					print_list_error(l_output_test['check_log'])

	return l_output_test
	pass


def do_test():

	global g_check_log_to_skip
	global g_test_options
	global g_exit

	tests = []

	for test in g_test_options:
		output_test = None

		print '\nTEST: ' + test
		output_test =  test_application(test)

		if output_test['exit_code'] == 0 :
			print 'OK: Success test.'
		else:
			print 'ERROR: Error test, return code = ', output_test['exit_code']
			g_exit = 1

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

	parse_command_line_option(argv)
	check_paramenters()

	do_test()

	checking_exit(g_exit)

	pass


#########################################################
# Do not remove

if __name__ == "__main__":
   main(sys.argv[1:])

