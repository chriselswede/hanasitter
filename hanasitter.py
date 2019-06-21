# -*- coding: utf-8 -*-
from datetime import datetime
from threading import Timer
import sys, time, os, subprocess
from multiprocessing import Pool
import shutil
#import smtplib
#from email.mime.multipart import MIMEMultipart
#from email.mime.text import MIMEText


def printHelp():
    print("                                                                                                                                                    ")    
    print("DESCRIPTION:                                                                                                                                        ")
    print(" The HANA sitter checks regularly (def. 1h) if HANA is online and primary. If so, it starts to track. Tracking includes                             ")
    print(" regularly (def. 1m) checks if HANA is responsive. If it is not, it will record. Recording could include writing call stacks                        ")
    print(" of all active threads and/or record run time dumps and/or indexserver gstacks and/or kernel profiler traces. By default                            ")
    print(" nothing is recorded. If HANA is responsive it will check for too many critical features of HANA. By default this is checking                       ")
    print(" if there are more than 30 active threads. If there is, it will record (see above). After it is done recording it will by                           ")
    print(" default exit, but could also restart, if so wanted.                                                                                                ") 
    print(" After it has concluded that all was good, it will wait (def. 1h) and then start all over to check again if HANA is online                          ")
    print(" and primary. See also SAP Note 2399979.                                                                                                            ")
    print("                                                                                                                                                    ")
    print("PREREQUISITES:                                                                                                                                      ")
    print(" - Executed by <sid>adm                                                                                                                             ")
    print(" - A DB user with proper privileges maintained in hdbuserstore (to be used with the -k flag)                                                        ")
    print(' - In case you run HANASitter on a virtual host the linux command "hostname" have to return the logical host name (not the physical)                ')
    print(" - Should be executed on (one of) the host(s) on which (one of) the HANA node(s) is running                                                         ")
    print(""" - /bin/bash has to return "clean" outputs, e.g.  /bin/bash -i -c "alias cdhdb"  should ONLY return something like  alias cdhdb='cd $DIR_INSTANCE'  """)
    print("                                                                                                                                                    ")
    print("INPUT ARGUMENTS:                                                                                                                                    ")
    print("         *** CHECKS (Pings and/or Feature Checks and/or CPU Checks) ***                                                                             ")
    print(" -oi     online test interval [seconds], time it waits before it checks if DB is online again, default: 3600 seconds                                ")
    print(" -cpu    a 4 items list to control the cpu check: cpu type, number checks, interval, max average CPU in %, default: 0,0,0,100                       ")
    print("         Possible cpu types are: 0 = not used, 1 = user cpu, 2 = system cpu                                                                         ")
    print(" -pt     ping timeout [seconds], time it waits before the DB is considered unresponsive, default: 60 seconds                                        ")           
    print(' -cf     list of features surrounded by two "s; the -cf flag has two modes, 1. One Column Mode and 2. Where Clause Mode                             ')
    print("         1. One Column Mode: any sys.m_* view, a column in that view, the column value (wildcards, *, before and/or after are possible) and         ")
    print("            max number allowed feature occations, i.e.                                                                                              ")
    print('            "<m_view 1>,<feature 1>,<[*]value 1[*]>,<limit 1>,...,<m_view N>,<feature N>,<[*]value N[*]>,<limit N>"                                 ')
    print("         2. Where Clause Mode: any sys.m_* view, the keyword 'WHERE', the where clause and max number allowed feature occations, i.e.               ")
    print('            "<m_view 1>,WHERE,<where clause 1>,<limit 1>,...,<m_view N>,WHERE,<where clause N>,<limit N>"                                           ')
    print('         default: ""                                                                                                                                ')
    print('         Note: <limit> should be an integer, or an integer preceded by < (for maximum allowed) or > (for minumum allowed)                           ')
    print('         Note: If you need a , in critical feature, please use \c instead, e.g. add_seconds(BLOCKED_TIME\c600)                                      ')
    print(" -if     number checks and intervals of checks, every odd item of this list specifies how many times each feature check (see -cf) should be executed")
    print("         and every even item specifies how many seconds it waits between each check, then the <max numbers X> in the -cf flag is the maximum        ")
    print("         allowed average value, e.g. <number checks 1>,<interval [s] 1>,...,<number checks N>,<interval [s] N>, default: [] (not used)              ")
    print(" -tf     feature check time out [seconds], time it waits before the DB is considered unresponsive during a feature check                            ")
    print("         (see -cf), if -if is used this time out will be added to the interval and then multiplied with number checks, default: 60 seconds          ") 
    print(" -lf     log features [true/false], logging ALL information of ALL critical features (beware: could be costly!), default: false                     ")
    print(" -ci     check interval [seconds], time it waits before it checks cpu, pings and check features again, default: 60 seconds                          ") 
    print(" -ar     time to sleep after recording [seconds], if negative it exits, default: -1                                                                 ")
    print("         *** RECORDINGS (GStacks and/or Kernel Profiler Traces and/or Call Stacks and/or RTE dumps) ***                                             ")
    print(" -rm     recording mode [1, 2 or 3], 1 = each requested recording types are done one after each other with the order above,                         ")
    print("                                         e.g. GStack 1, GStack 2, ..., GStack N, RTE 1, RTE 2, ..., RTE N   (this is default)                       ")
    print("                                     2 = the recordings of each requested recording types are done after each other with the                        ")
    print("                                         order above, e.g. GStack 1, RTE 1, Gstack 2, RTE 2, ...                                                    ")
    print("                                     3 = different recording types recorded in parallel threads, e.g. if 2 GStacks and 1 RTE                        ")
    print("                                         requested then GStack 1 and RTE 1 are parallel done, when both done GStack 2 starts                        ")
    print(" -rp     recording priorities [list of 4 integers [1,4]] defines what order the recording modes will be executed for rm = 1 and rm = 2              ")
    print("                                                         # 1 = RTE, # 2 = CallStacks, # 3 = GStacks, # 4 = Kernel Profiler, default: 1,2,3,4        ")
    print(" -hm     host mode [true/false], if true then all critical features are considered per host and the recording is done only for those hosts where    ")
    print("                                 the critical feature is above allowed limit per host, default: false                                               ")
    print("                                 Note: -hm is not supported for gstack (-ng), but for the other recording possibilities (-np, -nc, and -nr)         ")
    print(" -ng     number indexserver gstacks created if the DB is considered unresponsive (Note: gstack blocks the indexserver! See SAP Note 2000000         ")
    print('         "Call stack generation via gstack"), default: 0  (not used)                                                                                ') 
    print(" -ig     gstacks interval [seconds], for -rm = 1: time it waits between each gstack,                                                                ")
    print("                                     for -rm = 2: time it waits after a gstack,                                                                     ")
    print("                                     for -rm = 3: time the thread waits after a gstack,          default: 60 seconds                                ")
    print(" -np     number indexserver kernel profiler traces created if the DB is considered unresponsive: default: 0  (not used)                             ") 
    print(" -dp     profiler duration [seconds], how long time it is tracing, default: 60 seconds   (more info: SAP Note 1804811)                              ")
    print(" -wp     profiler wait time [milliseconds], wait time after callstacks of all running threads have been taken, default 0                            ")
    print(" -ip     profiler interval [seconds], for -rm = 1: time it waits between each profiler trace,                                                       ")
    print("                                      for -rm = 2: time it waits after a profiler trace,                                                            ")
    print("                                      for -rm = 3: time the thread waits after a profiler trace,         default: 60 seconds                        ")
    print(" -nc     number call stacks created if the DB is considered unresponsive: default: 0  (not used)                                                    ") 
    print(" -ic     call stacks interval [seconds], for -rm = 1: time it waits between each call stack,                                                        ")
    print("                                         for -rm = 2: time it waits after a call stack,                                                             ")
    print("                                         for -rm = 3: time the thread waits after a call stack,  default: 60 seconds                                ")
    print(" -nr     number rte dumps created if the DB is considered unresponsive: default: 0    (not used)                                                    ") 
    print("         Note: output is restricted to these folders /tmp, $HOME, $DIR_INSTANCE/work, and $SAP_RETRIEVAL_PATH                                       ")
    print(" -ir     rte dumps interval [seconds], for -rm = 1: time it waits between each rte dump,                                                            ")
    print("                                       for -rm = 2: time it waits after an rte dump,                                                                ")
    print("                                       for -rm = 3: time the thread waits after an rte dump,     default: 60 seconds                                ")
    print(" -mr     rte dump mode [0 or 1], -mr = 0: normal rte dump,                                                                                          ")
    print("                                 -mr = 1: light rte dump mode, only rte dump with STACK_SHORT and THREADS sections, and some M_ views,  default: 0  ")
    print("         *** KILL SESSIONS (use with care!) ***                                                                                                     ")
    print(" -ks     kill session [list of true/false], list of booleans (length must be the same as number of features defined by -cf) that defines if -cf's   ")
    print("         features could indicate that the sessions (connections) are tried to be disconnected or not, default: None (not used)                      ")
    print("         Note: Requires SESSION ADMIN                                                                                                               ")
    print("         *** ADMINS (Output Directory, Logging, Output and DB User) ***                                                                             ")
    print(" -od     output directory, full path of the folder where all output files will end up (if the folder does not exist it will be created),            ")
    print("         default: '/tmp/hanasitter_output'                                                                                                          ")
    print(" -or     output log retention days, hanasitterlogs in the path specified with -od are only saved for this number of days, default: -1 (not used)    ")
    print(" -en     email notification, <sender's email>,<reciever's email>,<mail server>, default:     (not used)                                             ") 
    print("                             example: me@ourcompany.com,you@ourcompany.com,smtp.intra.ourcompany.com                                                ")
    print('         NOTE: For this to work you have to install the linux program "sendmail" and add a line similar to DSsmtp.intra.ourcompany.com in the file  ')
    print("               sendmail.cf in /etc/mail/, see https://www.systutorials.com/5167/sending-email-using-mailx-in-linux-through-internal-smtp/           ")
    print(" -so     standard out switch [true/false], switch to write to standard out, default:  true                                                          ")
    print(" -ff     flag file, full path to a file that contains input flags, each flag in a new line, all lines in the file that does not start with a        ")
    print("         flag are considered comments, if this flag is used no other flags should be given, default: '' (not used)                                  ")
    print(" -ssl    turns on ssl certificate [true/false], makes it possible to use SAP HANA Sitter despite SSL, default: false                                ") 
    print(" -vlh    virtual local host, if hanacleaner runs on a virtual host this has to be specified, default: '' (physical host is assumed)                 ")                
    print(" -k      DB user key, this one has to be maintained in hdbuserstore, i.e. as <sid>adm do                                                            ")               
    print("         > hdbuserstore SET <DB USER KEY> <ENV> <USERNAME> <PASSWORD>                     , default: SYSTEMKEY                                      ")
    print("                                                                                                                                                    ")    
    print("                                                                                                                                                    ")
    print("EXAMPLE (if > 20 THREAD_STATE=Running, or > 30 THREAD_STATE=Semaphore Wait are found 2 RTE dumps and 3 GStacks will be recorded                     ")
    print("         in parallel, i.e. RTE1&GStack1, RTE2&GStack2, GStack3):                                                                                    ")
    print('  > python hanasitter.py -cf "M_SERVICE_THREADS,THREAD_STATE,Running,30,M_SERVICE_THREADS,THREAD_STATE,Semaphore Wait,20" -nr 2 -ng 3 -rm 3         ')
    print("                                                                                                                                                    ")
    print("EXAMPLE (if, on average from 3 checks with 5s interval, > 30 THREAD_STATE=Running, or if any column from the table VARINUM has been unloaded,       ")
    print("         then record two call stacks)                                                                                                               ")    
    print('  > python hanasitter.py -cf "M_SERVICE_THREADS,THREAD_STATE,Running,30,M_CS_UNLOADS,TABLE_NAME,VARINUM,1" -if 3,5,1,0 -nc 2                        ')
    print("                                                                                                                                                    ")
    print("EXAMPLE (Here a where clause is given, if more than 3 active indexserver threads runs longer than about 5 days (duration is in ms))                 ")    
    print('''  > python hanasitter.py -cf "M_SERVICE_THREADS,WHERE,IS_ACTIVE='TRUE' and SERVICE_NAME='indexserver' and DURATION>420000000,3" -nc 2           ''')
    print("                                                                                                                                                    ")
    print("EXAMPLE (if average system CPU >95% or Ping > 30 seconds, 2 Call Stacks are recorded, or else it will try again after 120 seconds, after            ")
    print("         recording it will sleep for one hour before it starts to track again):                                                                     ")                                                
    print("  > python hanasitter.py -cpu 2,5,2,95 -pt 30 -ci 120 -nc 2 -ar 3600                                                                                ")
    print("                                                                                                                                                    ")
    print("EXAMPLE (if there are more then 10 threads from the Application user AUSER123 or from the DB user DUSER123 record 2 RTE dumps):                     ")
    print('  > python hanasitter.py -cf "M_SERVICE_THREADS,APPLICATION_USER_NAME,AUSER123,10,M_SERVICE_THREADS,USER_NAME,DUSER123,10" -nr 2                    ')
    print("                                                                                                                                                    ")
    print("EXAMPLE (if there are more then 5 threads with a thread method that starts with PlanExecutor or with a thread type that                             ")
    print("         includes Attribute or that is executed from any user starting with DUSER12, then 5 GStacks are recorded                                    ") 
    print('  > python hanasitter.py -cf "M_SERVICE_THREADS,THREAD_METHOD,PlanExecutor*,5,M_SERVICE_THREADS,THREAD_TYPE,*Attribute*,5,M_SERVICE_THREADS,USER_NAME,DUSER12*,5" -ng 5 ')
    print("                                                                                                                                                    ")
    print("EXAMPLE (reads a configuration file, but one flag will overwrite what is in the configuration file, i.e. there will be 3 callstacks instead of 2):  ")
    print("  > python hanasitter.py -ff /tmp/HANASitter/hanasitter_configfile.txt -nc 3                                                                        ")
    print("    Where the config file could looks like this:                                                                                                    ")
    print("                                  MY HANASITTER CONFIGURATION FILE                                                                                  ")
    print("                                  If more than 20 threads is in state TREAD_STATE=Running                                                           ")
    print('                                  -cf "M_SERVICE_THREADS,THREAD_STATE,Running,20"                                                                   ')
    print("                                  then 2 call stacks                                                                                                ")
    print("                                  -nc 2                                                                                                             ")
    print("                                  with 30 seconds between them                                                                                      ")
    print("                                  -ic 30                                                                                                            ")
    print("                                  are recorded. This is the key in hdbuserstore that is used:                                                       ")
    print("                                  -k SYSTEMKEY                                                                                                      ")
    print("                                                                                                                                                    ")
    print("CURRENT KNOWN LIMITATIONS (i.e. TODO LIST):                                                                                                         ")
    print(" 1. Record in parallel for different Scale-Out Nodes   (should work for some recording types, e.g. RTE dumps -->  TODO)                             ")
    print(" 2. If a CPU only happens on one Host, possible to record on only one Host                                                                          ")
    print(" 3. CPU should be possible to be checked for BOTH system AND user --> TODO                                                                          ")
    print(" 4. Let HANASitter first check that there is no other hanasitter process running --> refuse to run --> TODO  (but can be done with cron, see slides)")
    print(" 5. Read config file, -ff, after hanasitter slept, so that it will allow dynamic changes                                                            ")
    print(" 6. Make the PING check specific for HOSTS (and only record for that host) ... can be done with ROUTE_TO(<volume_id_1>, ..., <volume_id_n>)         ")
    print("                                                                                                                                                    ")
    print("AUTHOR: Christian Hansen                                                                                                                            ")
    print("                                                                                                                                                    ")
    print("                                                                                                                                                    ")
    os._exit(1)
    
def printDisclaimer():
    print("                                                                                                                                  ")    
    print("ANY USAGE OF HANASITTER ASSUMES THAT YOU HAVE UNDERSTOOD AND AGREED THAT:                                                         ")
    print(" 1. HANASitter is NOT SAP official software, so normal SAP support of HANASitter cannot be assumed                                ")
    print(" 2. HANASitter is open source                                                                                                     ") 
    print(' 3. HANASitter is provided "as is"                                                                                                ')
    print(' 4. HANASitter is to be used on "your own risk"                                                                                   ')
    print(" 5. HANASitter is a one-man's hobby (developed, maintained and supported only during non-working hours)                           ")
    print(" 6  All HANASitter documentations have to be read and understood before any usage:                                                ")
    print("     a) SAP Note 2399979                                                                                                          ")
    print("     b) The .pdf file that can be downloaded at the bottom of SAP Note 2399979                                                    ")
    print("     c) All output from executing                                                                                                 ")
    print("                     python hanasitter.py --help                                                                                  ")
    print(" 7. HANASitter can help you to automize certain monitoring tasks but is not an attempt to teach you how to monitor SAP HANA       ")
    print("    I.e. if you do not know what you want to do, HANASitter cannot help, but if you do know, HANASitter can automitize it         ")
    print(" 8. HANASitter is not providing any recommendations, all flags shown in the documentation (see point 6.) are only examples        ")
    os._exit(1)

############ GLOBAL VARIABLES ##############
emailNotification = None

######################## DEFINE CLASSES ##################################
class RTESetting:
    def __init__(self, num_rtedumps, rtedumps_interval):
        self.num_rtedumps = num_rtedumps
        self.rtedumps_interval = rtedumps_interval
        
class CallStackSetting:
    def __init__(self, num_callstacks, callstacks_interval):
        self.num_callstacks = num_callstacks
        self.callstacks_interval = callstacks_interval
        
class GStackSetting:
    def __init__(self, num_gstacks, gstacks_interval):
        self.num_gstacks = num_gstacks
        self.gstacks_interval = gstacks_interval
        
class KernelProfileSetting:
    def __init__(self, num_kprofs, kprofs_interval, kprofs_duration, kprofs_wait):
        self.num_kprofs = num_kprofs
        self.kprofs_interval = kprofs_interval
        self.kprofs_duration = kprofs_duration
        self.kprofs_wait = kprofs_wait

class EmailNotification:
    def __init__(self, senderEmail, recieverEmail, mailServer, SID):
        self.senderEmail = senderEmail
        #self.senderPassword = senderPassword
        self.recieverEmail = recieverEmail
        self.mailServer = mailServer
        #self.mailServerPort = mailServerPort
        #self.timeout = timeout
        self.SID = SID
    def printEmailNotification(self):
        print "Sender Email: ", self.senderEmail, " Reciever Email: ", self.recieverEmail, " Mail Server: ", self.mailServer 

#### Remember:
#Nameserver port is always 3**01 and SQL port = 3**13 valid for,
#	- System DB in MDC
#
#If indexserver port = 3**03 then SQL port = 3**15 valid for,
#	- Single container in SAP HANA 1.0  and
#	- Default tenant starting SAP HANA 2.0 SPS2
#
#If indexserver port ≥ 3**40 then SQL port is always indexserver port +1, valid for 
#	- All MDC tenants until HANA 2.0 SPS1 and 
#	- Starting HANA 2 SPS2 with second tenant within a MDC system

class Tenant:
    def __init__(self, DBName, indexserverPort, instanceNbr, SID):
        self.DBName = DBName
        self.indexserverPort = int(indexserverPort)
        self.instanceNbr = instanceNbr
        self.SID = SID
        if self.indexserverPort >= int("3"+self.instanceNbr+"40"):
            self.sqlPort = self.indexserverPort + 1
        elif self.indexserverPort == int("3"+self.instanceNbr+"03"):
            self.sqlPort = int("3"+self.instanceNbr+"15")
        else:
            print "ERROR, something went wrong, indexserver port is not according to the rules; "+str(self.indexserverPort)
            os._exit(1)
    def printTenant(self):
        print "TenantDB: ", self.DBName, " Indexserver Port: ", self.indexserverPort, " Sql Port: ", self.sqlPort
    def getIndexserverPortString(self):
        return str(self.indexserverPort)
        
class HDBCONS:
    def __init__(self, local_host, hosts, local_dbinstance, is_mdc, is_tenant, communicationPort, SID, rte_mode, tenantDBName = None):
        self.local_host = local_host
        self.local_dbinstance = local_dbinstance
        self.hosts = hosts
        self.hostsForRecording = hosts # at first assume all, also true unloss host_mode 
        self.is_scale_out = (len(hosts) > 1)
        self.is_mdc = is_mdc
        self.is_tenant = is_tenant
        self.communicationPort = communicationPort
        self.SID = SID
        self.tenantDBName = tenantDBName
        self.rte_mode = rte_mode
        self.temp_host_output_dirs = []
        # SET HDBCONS STRINGS
        self.hdbcons_strings = []
        for host in self.hosts:
            if not self.is_mdc:       # not MDC
                if not self.is_scale_out:
                    self.hdbcons_strings.append('hdbcons "')
                else:
                    self.hdbcons_strings.append('hdbcons "distribute exec '+host+':'+self.communicationPort+' ')                # SAP Note 2222218
            else:                       # MDC (both SystemDB and Tenant)
                self.hdbcons_strings.append('hdbcons -e hdbnameserver "distribute exec '+host+':'+self.communicationPort+' ')   # SAP Notes 2222218 and 2410143
    def create_temp_output_directories(self): # CREATE TEMPORARY OUTPUT DIRECTORIES and SET PRIVILEGES (CHMOD)
        cdtrace_path_local = cdalias('cdtrace', self.local_dbinstance)
        if not self.local_host in cdtrace_path_local:
            print "ERROR, local host, ", self.local_host, ", is not part of cdtrace, ", cdtrace_path_local
            os._exit(1)
        for host in self.hosts:
            
            #NOt NEEDED?
            #generic_folder_path = cdtrace_path_local.replace(self.local_host, host)+"/hanasitter_temp_out/"
            #if os.path.isdir(generic_folder_path):
            #    subprocess.check_output("rm -r "+generic_folder_path, shell=True)
            #subprocess.check_output("mkdir "+generic_folder_path, shell=True)
            #subprocess.check_output("chmod 777 "+generic_folder_path, shell=True)
            #self.temp_host_output_dirs.append(generic_folder_path+"hanasitter_temp_out_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+"/")
            
            self.temp_host_output_dirs.append(cdtrace_path_local.replace(self.local_host, host)+"hanasitter_temp_out_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+"/")
        for path in self.temp_host_output_dirs:
            subprocess.check_output("mkdir "+path, shell=True)
            subprocess.check_output("chmod 777 "+path, shell=True)
    def clear(self):
        for path in self.temp_host_output_dirs:
            if os.path.isdir(path):
                subprocess.check_output("rm -r "+path, shell=True)

        
class CommunicationManager:
    def __init__(self, dbuserkey, out_dir, std_out, hdbsql_string, log_features):
        self.dbuserkey = dbuserkey
        self.out_dir = out_dir
        self.std_out = std_out
        self.hdbsql_string = hdbsql_string
        self.log_features = log_features     
        
class CriticalFeature:
    def __init__(self, view, feature, value, limit, killSession = False):
        self.view = view
        self.feature = feature
        self.maxRepeat = None
        self.whereMode = (self.feature == 'WHERE')
        if self.whereMode:
            self.whereClause = value.replace('\c',',')  # in case , wants to be used in where clause, e.g. CURRENT_TIMESTAMP>=add_seconds(BLOCKED_TIME,600)
        else:
            # IF THERE IS A > THEN TRY TO SPLIT TO A MAX_REPEAT AND A VALUE
            if '>' in value: # to find string before > X number times where X is the integer after >
                self.maxRepeat = value.rsplit('>',1)[1] #rsplit allows other >s in the value
                if is_integer(self.maxRepeat):          #if not, then this > was not intended for repeat 
                    value = value.rsplit('>',1)[0]      #where-clause to find rows where the column 'feature' contains the string 'value' more than 'maxRepeat' times
                    self.whereClause = "length("+feature+") - length(replace("+feature+", '"+value+"', '')) > "+str(int(self.maxRepeat)*len(value))
            # IF NOT MANAGED TO SPLIT THEN FIRST CORRECT WILDCARDS AND THEN CREATE THE WHERE CLAUSE
            if not is_integer(self.maxRepeat):  
                if value[0] == '*' and value[-1] == '*':   #wildcards, "*", before and after
                    value = "'%"+value[1:-1]+"%'"
                elif value[0] == '*':                      #wildcard,  "*", before
                    value = "'%"+value[1:]+"'"
                elif value[-1] == '*':                     #wildcard,  "*", after
                    value = "'"+value[:-1]+"%'"
                else:
                    value = "'"+value+"'"
                if value[1] == '%' or value[-1] == '%':
                    self.whereClause = feature + " like " + value   #where-clause with wildcard(s)
                else:
                    self.whereClause = feature + " = " + value      #where-clause without wildcard(s)     
        self.value = value
        self.limitIsMinimumNumberCFAllowed = (limit[0] == '>') # so default and < then maximum number CF allowed 
        if limit[0] in ['<', '>']:
            limit = limit[1:]
        if not is_integer(limit):
            print "INPUT ERROR: 4th item of -cf must be either an integer or an integer preceded by < or >. Please see --help for more information."
            os._exit(1)
        self.limit = int(limit)
        self.killSession = killSession
        self.whereClauseDescription = self.whereClause
        if is_integer(self.maxRepeat):
            self.whereClauseDescription = "column "+self.feature+" in "+self.view+" contains the string "+self.value+" more than "+self.maxRepeat+" times"
        self.nbrIterations = 1
        self.interval = 0 #[s]
        if self.limitIsMinimumNumberCFAllowed:
            self.cfInfo = "min required = "+str(self.limit)+", check: "+self.whereClauseDescription
        else:
            self.cfInfo = "max allowed = "+str(self.limit)+", check: "+self.whereClauseDescription
    def setKillSession(self, killSession):
        self.killSession = killSession
    def setIterations(self, iterations, interval):
        self.nbrIterations = iterations
        self.interval = interval
        
######################## DEFINE FUNCTIONS ################################

def is_integer(s):
    if s == None:
        return False
    try:
        int(s)
        return True
    except ValueError:
        return False
    
def is_email(s):
    s = s.split('@')
    if not len(s) == 2:
        return False
    return '.' in s[1]
        
def checkAndConvertBooleanFlag(boolean, flagstring):     
    boolean = boolean.lower()
    if boolean not in ("false", "true"):
        print "INPUT ERROR: ", flagstring, " must be either 'true' or 'false'. Please see --help for more information."
        os._exit(1)
    boolean = True if boolean == "true" else False
    return boolean

def is_online(dbinstance, comman):
    process = subprocess.Popen(['sapcontrol', '-nr', dbinstance, '-function', 'GetProcessList'], stdout=subprocess.PIPE)
    out, err = process.communicate()
    number_services = out.count(" HDB ")    
    number_running_services = out.count("GREEN")
    test_ok = (str(err) == "None")
    result = number_running_services == number_services
    printout = "Online Check      , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    ,     -            , "+str(test_ok)+"         , "+str(result)+"       , Number running services: "+str(number_running_services)+" out of "+str(number_services)
    log(printout, comman)
    return result
    
def is_secondary(comman):
    process = subprocess.Popen(['hdbnsutil', '-sr_state'], stdout=subprocess.PIPE)
    out, err = process.communicate() 
    test_ok = (str(err) == "None")
    result = "active primary site" in out   # then it is secondary!
    printout = "Primary Check     , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    ,     -            , "+str(test_ok)+"         , "+str(not result)+"       , " 
    log(printout, comman)
    return result 
    
def ping_db(comman, output):
    with open(os.devnull, 'w') as devnull:  # just to get no stdout in case HANA is offline
        try:
            output[0] = subprocess.check_output(comman.hdbsql_string+''' -j -A -U '''+comman.dbuserkey+''' "select * from dummy"''', shell=True, stderr=devnull)
        except:
            pass
            
def hana_ping(ping_timeout, comman):
    pause = ping_timeout/10.
    lifetime = 0
    pinged = False
    hanging = False
    offline = False
    while not pinged and not hanging and not offline:
        output = [None]
        t = Timer(0.1,ping_db,[comman, output]) # Will not return if HANA is in a hanging situation, if HANA is offline it will return immediately with output[0] still Null
        t.start()
        t.join(ping_timeout)
        hanging = t.is_alive()
        if output[0]:
            pinged = output[0].splitlines(1)[2].replace('|','').replace(' ','').replace('\n','') == 'X'
        if hanging and pinged:
            print "ERROR, it cannot be both pinged and hanging"
            os._exit(1)
        if not pinged and not hanging: # then still investigating if offline
            offline = lifetime > ping_timeout
            if not offline:                        
                time.sleep(pause)          # e.g. if ping timeout is 60 seconds it will retry after 6 seconds if HANA is offline
                lifetime += pause   
    return [hanging, offline]
        
def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def prio_def(prio_number):
    prios = {1:"RTE", 2:"Call Stacks", 3:"G-Stacks", 4:"Kernel Profiler"}
    return prios[prio_number]    

def recording_prio_convert(recording_prio):
    recordings = []
    for rec in recording_prio:
        recordings.append(prio_def(rec))
    return "   ".join(recordings)
    
def file_lines_with_word(file_name, word):
    lines = []
    with open(file_name) as f:
        for line in f:
            if word in line:
                lines.append(line)
    return lines 

def clean_logs(minRetainedLogDays, comman):
    path = comman.out_dir
    nFilesBefore = len([name for name in os.listdir(path) if "hanasitterlog" in name])
    subprocess.check_output("find "+path+"/hanasitterlog* -mtime +"+str(minRetainedLogDays)+" -delete", shell=True)
    nFilesAfter = len([name for name in os.listdir(path) if "hanasitterlog" in name])
    return nFilesBefore - nFilesAfter  

def tenant_names_and_ports(daemon_file):
    tenantDBNames = [] 
    tenantIndexserverPorts = []
    ports_first_halfs = []
    ports_second_halfs = []
    foundNewName = False
    foundFirstPortHalf = False
    foundInstanceIds = False
    with open(daemon_file) as f:
        for line in f:
            if not foundNewName and "[indexserver." in line:
                tenantDBNames.append(line.strip("[indexserver.").strip("\n").strip("]"))
                foundNewName = True
            elif foundNewName and not foundFirstPortHalf and "arguments = -port " in line:
                ports_first_halfs.append(line.strip("arguments = -port ").split("$")[0])
                foundFirstPortHalf = True
            elif foundNewName and not foundInstanceIds and "instanceids = " in line:
                ports_second_halfs.append(line.strip("instanceids = ").strip("\n"))
                foundInstanceIds = True
            elif foundNewName and not line:  # the order of instance ids and arguments are different in SPS03 and SPS04
                if foundFirstPortHalf and foundInstanceIds:
                    foundNewName = False
                    foundFirstPortHalf = False
                    foundInstanceIds = False
                else:
                    print "ERROR, something went wrong while reading the daemon.ini file"
                    os._exit(1)
        tenantIndexserverPorts = [first+second for first, second in zip(ports_first_halfs, ports_second_halfs)]
    return [tenantDBNames, tenantIndexserverPorts]

def cpu_too_high(cpu_check_params, comman):
    if int(cpu_check_params[0]) == 0 or int(cpu_check_params[1]) == 0 or int(cpu_check_params[3]) == 100: # if CPU type is 0 or if number CPU checks is 0 or allowed CPU is 100 then no CPU check
        return False
    start_time = datetime.now()
    command_run = subprocess.check_output("sar -u "+cpu_check_params[1]+" "+cpu_check_params[2], shell=True)
    sar_words = command_run.split()
    cpu_column = 2 if int(cpu_check_params[0]) == 1 else 4
    current_cpu = sar_words[sar_words.index('Average:') + cpu_column]
    if not is_number(current_cpu):
        print "ERROR, something went wrong while using sar. Output = "
        print command_run
        os._exit(1)
    too_high_cpu = float(current_cpu) > int(cpu_check_params[3])
    stop_time = datetime.now()
    cpu_string = "User CPU Check  " if int(cpu_check_params[0]) == 1 else "System CPU Check"
    printout = cpu_string+"  , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         , "+str(not too_high_cpu)+"       , Av. CPU = "+current_cpu+" % (Allowed = "+cpu_check_params[3]+" %) "
    log(printout, comman, sendEmail = too_high_cpu)
    return too_high_cpu

def stop_session(cf, comman):
    heather = subprocess.check_output(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select top 1 * from SYS.'+cf.view+' where '+cf.whereClause+'"', shell=True).splitlines(1)
    heather = heather[0].strip('\n').strip(' ').split('|')
    heather = [h.strip(' ') for h in heather if h != '']
    if 'CONNECTION_ID' in heather:
        connIds = subprocess.check_output(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "select distinct CONNECTION_ID from SYS.'+cf.view+' where '+cf.whereClause+'"', shell=True).splitlines(1)
        connIds = [c.strip('\n').strip('|').strip(' ') for c in connIds]
        for connId in connIds:
            printout = "Will disconnect session "+connId+" due to the check: "+cf.whereClauseDescription
            log(printout, comman)
            subprocess.check_output(comman.hdbsql_string+""" -j -A -U """+comman.dbuserkey+""" "ALTER SYSTEM DISCONNECT SESSION '"""+connId+"""'" """, shell=True)
        

def feature_check(cf, nbrCFsPerHost, critical_feature_info, host_mode, comman):   # cf = critical_feature, # comman = communication manager
    #CHECKS
    viewExists = int(subprocess.check_output(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitors where view_name = '"+cf.view+"'\"", shell=True).strip(' '))
    if not viewExists:
        log("INPUT ERROR, the view given as first entry in the -cf flag, ", cf.view, ", does not exist. Please see --help for more information.", comman)
        os._exit(1)
    if not cf.whereMode:
        columnExists = int(subprocess.check_output(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitor_columns where view_name = '"+cf.view+"' and view_column_name = '"+cf.feature+"'\"", shell=True).strip(' ')) 
        if not columnExists:
            log("INPUT ERROR, the view ", cf.view, " does not have the column ", cf.feature, ". Please see --help for more information.", comman)
            os._exit(1)
    if host_mode:
        hostColumnExists = int(subprocess.check_output(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitor_columns where view_name = '"+cf.view+"' and view_column_name = 'HOST'\"", shell=True).strip(' ')) 
        if not hostColumnExists:
            log("INPUT ERROR, you have specified host mode with -hf, but the view ", cf.view, " does not have a HOST column. Please see --help for more information.", comman)
            os._exit(1)         
    nbrCFSum = {}
    for iteration in range(cf.nbrIterations):
        # EXECUTE
        nCFsPerHost = []
        if host_mode:
            hostsInView = subprocess.check_output(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select distinct HOST from SYS."+cf.view+"\"", shell=True).strip(' ').split('\n')
            hostsInView = [h for h in hostsInView if h != ''] 
            for host in hostsInView:
                nCFsPerHost.append([int(subprocess.check_output(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select count(*) from SYS.'+cf.view+' where '+cf.whereClause+' and HOST = \''+host+'\'"', shell=True).split('|')[5].replace(" ", "")), host])
        else:                
            nCFsPerHost.append([int(subprocess.check_output(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select count(*) from SYS.'+cf.view+' where '+cf.whereClause+'"', shell=True).split('|')[5].replace(" ", "")), ''])
        # COLLECT INFO
        if comman.log_features:  #already prevented that log features (-lf) and host mode (-hm) is not used together
            critical_feature_info[0] = subprocess.check_output(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select * from SYS.'+cf.view+' where '+cf.whereClause+'"', shell=True)
        for cfHost in nCFsPerHost:
            if cfHost[1] in nbrCFSum:
                nbrCFSum[cfHost[1]] += cfHost[0]
            else:
                nbrCFSum[cfHost[1]] = cfHost[0]
        # CRITICAL FEATURE CHECK INTERVALL
        time.sleep(float(cf.interval))       
    # GET AVERAGE
    for h, nCF in nbrCFSum.items():
        nbrCFSum[h] = int ( float(nCF) / float(cf.nbrIterations) )
    nbrCFsPerHost[0] = nbrCFSum  #output 

 
def record_gstack(gstacks_interval, comman):
    pid = subprocess.check_output("pgrep hdbindexserver", shell=True).strip("\n").strip(" ")
    start_time = datetime.now()
    filename = (comman.out_dir+"/gstack_"+pid+"_"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".txt")
    os.system('gstack '+pid+' > '+filename)
    stop_time = datetime.now()
    printout = "GStack Record     , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          ,   -        , "+filename 
    log(printout, comman)
    time.sleep(gstacks_interval)
    return printout
 
def record_kprof(kprofiler, hdbcons, comman):   # SAP Note 1804811
    out_dir = comman.out_dir+"/"
    total_printout = ""
    for hdbcon_string, host, tmp_dir in zip(hdbcons.hdbcons_strings, hdbcons.hosts, hdbcons.temp_host_output_dirs): 
        if host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            filename_cpu = ("kernel_profiler_cpu_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".dot")
            filename_wait = ("kernel_profiler_wait_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".dot")
            filename_kprof_log = ("kernel_profiler_output_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".log")
            start_time = datetime.now()
            os.system(hdbcon_string+'profiler clear" > '+out_dir+filename_kprof_log)
            os.system(hdbcon_string+'profiler start -w '+str(kprofiler.kprofs_wait)+'" > '+out_dir+filename_kprof_log)
            time.sleep(kprofiler.kprofs_duration) 
            os.system(hdbcon_string+'profiler stop" > '+out_dir+filename_kprof_log)    
            os.system(hdbcon_string+'profiler print -o '+tmp_dir+filename_cpu+','+tmp_dir+filename_wait+'" > '+out_dir+filename_kprof_log)
            stop_time = datetime.now()
            if "[ERROR]" in open(out_dir+filename_kprof_log).read():
                printout = "Kernel Profiler   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , False        ,   None     , "+out_dir+filename_kprof_log
            else:
                os.system("mv "+tmp_dir+filename_cpu+" "+out_dir+filename_cpu)
                os.system("mv "+tmp_dir+filename_wait+" "+out_dir+filename_wait)
                printout = "Kernel Profiler   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         ,   -        , "+out_dir+filename_cpu+" and "+out_dir+filename_wait
            log(printout, comman)
            total_printout += printout
    time.sleep(kprofiler.kprofs_interval)
    return total_printout  
 
 
def record_callstack(callstacks_interval, hdbcons, comman):
    total_printout = ""
    for hdbcon_string, host in zip(hdbcons.hdbcons_strings, hdbcons.hosts):
        if host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            filename = (comman.out_dir+"/callstack_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".txt")
            start_time = datetime.now()
            os.system(hdbcon_string+'context list -s" > '+filename)
            stop_time = datetime.now()
            printout = "Call Stack Record , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          ,   -        , "+filename 
            log(printout, comman)
            total_printout += printout
    time.sleep(callstacks_interval)
    return total_printout 
 
def record_rtedump(rtedumps_interval, hdbcons, comman):
    total_printout = ""
    for hdbcon_string, host in zip(hdbcons.hdbcons_strings, hdbcons.hosts):
        if host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            start_time = datetime.now()
            if hdbcons.rte_mode == 0: # normal rte dump
                filename = (comman.out_dir+"/rtedump_normal_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".trc")
                os.system(hdbcon_string+'runtimedump dump -c" > '+filename)   # have to dump to std with -c and then to a file with >    since in case of scale-out  -f  does not work
            elif hdbcons.rte_mode == 1: # light rte dump 
                filename = (comman.out_dir+"/rtedump_light_"+host+"_"+hdbcons.SID+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".trc")
                os.system(hdbcon_string+'runtimedump dump -c -s STACK_SHORT,THREADS" > '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_JOBEXECUTORS_" >> '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_DEV_JOBEX_THREADGROUPS" >> '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_DEV_JOBEXWAITING" >> '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_DEV_CONTEXTS" >> '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_CONNECTIONS" >> '+filename)
                os.system(hdbcon_string+'statreg print -h -n M_DEV_SESSION_PARTITIONS" >> '+filename)
            stop_time = datetime.now()
            printout = "RTE Dump Record   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         ,   -        , "+filename   # if an [ERROR] happens that will be inside the file, hanasitter will not know it
            log(printout, comman)
            total_printout += printout
    time.sleep(rtedumps_interval)
    return total_printout 
 
def record(recording_mode, rte, callstack, gstack, kprofiler, recording_prio, hdbcons, comman):
    if recording_mode == 1:
        for p in recording_prio:
            if p == 1:
                for i in range(rte.num_rtedumps):
                    record_rtedump(rte.rtedumps_interval, hdbcons, comman)
            if p == 2:
                for i in range(callstack.num_callstacks):
                    record_callstack(callstack.callstacks_interval, hdbcons, comman) 
            if p == 3:
                for i in range(gstack.num_gstacks): 
                    record_gstack(gstack.gstacks_interval, comman)        
            if p == 4:                    
                for i in range(kprofiler.num_kprofs):    
                    record_kprof(kprofiler, hdbcons, comman)    
    elif recording_mode == 2:  
        max_nbr_recordings = max(gstack.num_gstacks, kprofiler.num_kprofs, callstack.num_callstacks, rte.num_rtedumps)
        for i in range(max_nbr_recordings):
            for p in recording_prio:
                if p == 1:
                    if i < rte.num_rtedumps:
                        record_rtedump(rte.rtedumps_interval, hdbcons, comman)
                if p == 2:
                    if i < callstack.num_callstacks:
                        record_callstack(callstack.callstacks_interval, hdbcons, comman)
                if p == 3:
                    if i < gstack.num_gstacks:
                        record_gstack(gstack.gstacks_interval, comman)                 
                if p == 4:    
                    if i < kprofiler.num_kprofs:
                        record_kprof(kprofiler, hdbcons, comman)
    else:
        record_in_parallel(rte, callstack, gstack, kprofiler, hdbcons, comman)
    return True

def record_in_parallel(rte, callstack, gstack, kprofiler, hdbcons, comman):    
    max_nbr_recordings = max(gstack.num_gstacks, kprofiler.num_kprofs, callstack.num_callstacks, rte.num_rtedumps)
    for i in range(max_nbr_recordings):    
        nbr_recording_types = sum(x > i for x in [rte.num_rtedumps, callstack.num_callstacks, gstack.num_gstacks, kprofiler.num_kprofs])
        pool = Pool(nbr_recording_types)  # need as many threads as number of recording types
        rec_types = []
        if rte.num_rtedumps > i:
            rec_types.append((1, rte, hdbcons, comman))         # 1 = RTE 
        if callstack.num_callstacks > i:
            rec_types.append((2, callstack, hdbcons, comman))   # 2 = CallStacks
        if gstack.num_gstacks > i:
            rec_types.append((3, gstack, hdbcons, comman))      # 3 = GStacks
        if kprofiler.num_kprofs > i:
            rec_types.append((4, kprofiler, hdbcons, comman))   # 4 = Kernel Profiler
        results = pool.map(parallel_recording_wrapper, rec_types)
        if comman.std_out:
            for j in range(len(results)):
                log(results[j], comman)
        pool.close() 
        pool.join()
        
def parallel_recording_wrapper(rec_types):     
    return parallel_recording(*rec_types)

def parallel_recording(record_type, recorder, hdbcons, comman):
    if record_type == 1:
        return record_rtedump(recorder.rtedumps_interval, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, False, comman.hdbsql_string, comman.log_features))
    elif record_type == 2:
        return record_callstack(recorder.callstacks_interval, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, False, comman.hdbsql_string, comman.log_features))
    elif record_type == 3:
        return record_gstack(recorder.gstacks_interval, CommunicationManager(comman.dbuserkey, comman.out_dir, False, comman.hdbsql_string, comman.log_features))
    else:
        return record_kprof(recorder, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, False, comman.hdbsql_string, comman.log_features))

def tracker(ping_timeout, check_interval, recording_mode, rte, callstack, gstack, kprofiler, recording_prio, critical_features, feature_check_timeout, cpu_check_params, minRetainedLogDays, host_mode, comman, hdbcons):   
    recorded = False
    offline = False
    while not recorded:
        # CPU CHECK
        if cpu_too_high(cpu_check_params, comman): #first check CPU with 'sar' (i.e. without contacting HANA) if it is too high, record without pinging or feature checking
            recorded = record(recording_mode, rte, callstack, gstack, kprofiler, recording_prio, hdbcons, comman)
        if not recorded:
            # PING CHECK - to find either hanging or offline situations
            start_time = datetime.now()
            [hanging, offline] = hana_ping(ping_timeout, comman)
            stop_time = datetime.now()
            if offline:            
                comment = "DB is offline, will exit the tracker without recording (if DB is online, check that the key can be used with hdbsql)"
            elif hanging:
                comment = "No response from DB within "+str(ping_timeout)+" seconds"
            else:
                comment = "DB responded faster than "+str(ping_timeout)+" seconds"
            log("Ping Check        , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          , "+str(not hanging and not offline)+"       , "+comment, comman, sendEmail = hanging or offline) 
            if hanging:
                recorded = record(recording_mode, rte, callstack, gstack, kprofiler, recording_prio, hdbcons, comman)
            if offline:
                return [recorded, offline]    # exit the tracker if HANA turns offline during tracking
        if not recorded:
            # FEATURE CHECK - only done if recording has not already been done from either the CPU check or from the Ping check
            chid = 0
            for cf in critical_features:
                if not recorded:    #No hang situation or critical feature situation happened yet, so check for a critical feature
                    nbrCFsPerHost = [-1]
                    critical_feature_info = [""]
                    hostsWithWrongNbrCFs = []
                    chid += 1
                    start_time = datetime.now()
                    t = Timer(0.1,feature_check,[cf, nbrCFsPerHost, critical_feature_info, host_mode, comman])
                    t.start()
                    t.join((feature_check_timeout + cf.interval)*cf.nbrIterations)
                    stop_time = datetime.now()
                    hanging = t.is_alive()
                    if hanging:
                        info_message = "Hang situation during feature-check detected"
                        printout = "Feature Check "+str(chid)+"   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , "+str(not hanging)+"         , "+str(not hanging)+"       , "+info_message
                        log(printout, comman, sendEmail = hanging)
                    else: 
                        for host, nCFs  in nbrCFsPerHost[0].items():
                            wrong_number_critical_features = (cf.limitIsMinimumNumberCFAllowed and nCFs < cf.limit) or (not cf.limitIsMinimumNumberCFAllowed and nCFs > cf.limit)    
                            info_message = "# CFs = "+str(nCFs)+" for "+host+", "+cf.cfInfo
                            printout = "Feature Check "+str(chid)+"   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , "+str(not hanging)+"         , "+str(not wrong_number_critical_features)+"       , "+info_message
                            log(printout, comman, sendEmail = wrong_number_critical_features)
                            if wrong_number_critical_features:
                                hostsWithWrongNbrCFs.append(host)
                    if comman.log_features:
                        log(critical_feature_info[0], CommunicationManager(comman.dbuserkey, comman.out_dir, False, comman.hdbsql_string, comman.log_features), "criticalFeatures")
                    if hanging or len(hostsWithWrongNbrCFs):
                        if cf.killSession:
                            stop_session(cf, comman)
                        if host_mode:
                            hdbcons.hostsForRecording = hostsWithWrongNbrCFs
                        recorded = record(recording_mode, rte, callstack, gstack, kprofiler, recording_prio, hdbcons, comman)
        if not recorded:
            time.sleep(check_interval)
            if minRetainedLogDays >= 0:   # automatic house keeping of hanasitter logs
                nCleaned = clean_logs(minRetainedLogDays, comman)
                log(str(nCleaned)+" hanasitter daily log files were removed", comman)
    return [recorded, offline]
            
def cdalias(alias, local_dbinstance):   # alias e.g. cdtrace, cdhdb, ...
    command_run = subprocess.check_output(['/bin/bash', '-i', '-c', "alias "+alias]).split("alias")[1]
    pieces = command_run.strip("\n").strip(" "+alias+"=").strip("'").strip("cd ").split("/")
    path = ''
    for piece in pieces:
        if piece and piece[0] == '$':
            piece = (subprocess.check_output(['/bin/bash', '-i', '-c', "echo "+piece])).strip("\n")
        path = path + '/' + piece + '/'
    path = path.replace("[0-9][0-9]", local_dbinstance) # if /bin/bash shows strange HDB[0-9][0-9] we force correct instance on it
    return path    
        
def log(message, comman, file_name = "", sendEmail = False):
    if comman.std_out:
        print message
    if file_name == "":
        file_name = "hanasitterlog"
    logfile = open(comman.out_dir+"/"+file_name+"_"+datetime.now().strftime("%Y-%m-%d"+".txt").replace(" ", "_"), "a")
    logfile.write(message+"\n")   
    logfile.flush()
    logfile.close()
    global emailNotification
    if sendEmail and emailNotification:  #sends email IF this call of log() wants it AND IF -en flag has been specified        
        #MAILX (https://www.systutorials.com/5167/sending-email-using-mailx-in-linux-through-internal-smtp/):
        mailstring = 'echo "'+message+'" | mailx -s "Message from HANASitter about '+emailNotification.SID+'" -S smtp=smtp://'+emailNotification.mailServer+' -S from="'+emailNotification.senderEmail+'" '+emailNotification.recieverEmail
        #print mailstring
        output = subprocess.check_output(mailstring, shell=True)
    
def main():
    #####################  CHECK PYTHON VERSION ###########
    if sys.version_info[0] != 2 or sys.version_info[1] != 7:
        print "VERSION ERROR: hanacleaner is only supported for Python 2.7.x. Did you maybe forget to log in as <sid>adm before executing this?"
        os._exit(1)

    #####################   DEFAULTS   ####################
    online_test_interval = 3600 #seconds
    ping_timeout = 60 #seconds
    check_interval = 60 #seconds
    recording_mode = 1 # either 1, 2 or 3
    recording_prio = ['1', '2', '3', '4']   # 1=RTE, 2=CallStacks, 3=GStacks, 4=Kernel Profiler
    host_mode = "false"
    num_rtedumps = 0 #how many rtedumps?
    rtedumps_interval = 60 #seconds
    rte_mode = 0 # either 0 or 1 
    num_callstacks = 0 #how many call stacks?
    callstacks_interval = 60 #seconds
    num_gstacks = 0  #how many call stacks?
    gstacks_interval = 60 #seconds
    num_kprofs = 0  #how many kernel profiler traces?
    kprofs_interval = 60 #seconds
    kprofs_duration = 60 #seconds
    kprofs_wait = 0 #milliseconds
    feature_check_timeout = 60 #seconds
    #critical_features = ['M_SERVICE_THREADS','IS_ACTIVE','TRUE','30']  #one critical feature state with max allowed 30
    critical_features = [] # default: don't use critical feature check
    kill_session = [] # default: do not kill any session
    intervals_of_features = [] #default only one check per feature
    after_recorded = -1 #default: exits after recorded
    std_out = "true" #print to std out
    out_dir = "/tmp/hanasitter_output"
    minRetainedLogDays = -1 #automatic cleanup of hanasitterlog
    flag_file = ""    #default: no configuration input file
    log_features = "false"
    email_notification = None
    ssl = "false"
    virtual_local_host = "" #default: assume physical local host
    dbuserkey = 'SYSTEMKEY' # This KEY has to be maintained in hdbuserstore  
                            # so that   hdbuserstore LIST    gives e.g. 
                            # KEY SYSTEMKEY
                            #     ENV : mo-fc8d991e0:30015
                            #     USER: SYSTEM
    cpu_check_params = ['0', '0','0','100'] # by default no cpu check
    
    #####################  CHECK INPUT ARGUMENTS #################
    if len(sys.argv) == 1:
        print "INPUT ERROR: hanasitter needs input arguments. Please see --help for more information."
        os._exit(1) 
    if len(sys.argv) != 2 and len(sys.argv) % 2 == 0:
        print "INPUT ERROR: Wrong number of input arguments. Please see --help for more information."
        os._exit(1)
    for i in range(len(sys.argv)):
        if i % 2 != 0:
            if sys.argv[i][0] != '-':
                print "INPUT ERROR: Every second argument has to be a flag, i.e. start with -. Please see --help for more information."
                os._exit(1)    
    
    
    #####################   PRIMARY INPUT ARGUMENTS   ####################     
    if '-h' in sys.argv or '--help' in sys.argv:
        printHelp()   
    if '-d' in sys.argv or '--disclaimer' in sys.argv:
        printDisclaimer() 
    if '-ff' in sys.argv:
        flag_file = sys.argv[sys.argv.index('-ff') + 1]
     
    ############ CONFIGURATION FILE ###################
    if flag_file:
        with open(flag_file, 'r') as fin:
            for line in fin:
                firstWord = line.strip(' ').split(' ')[0]  
                if firstWord[0:1] == '-':
                    flagValue = line.strip(' ').split('"')[1].strip('\n').strip('\r') if line.strip(' ').split(' ')[1][0] == '"' else line.strip(' ').split(' ')[1].strip('\n').strip('\r')
                    if firstWord == '-oi':
                        online_test_interval = flagValue
                    if firstWord == '-pt': 
                        ping_timeout = flagValue
                    if firstWord == '-ci': 
                        check_interval = flagValue
                    if firstWord == '-rm': 
                        recording_mode = flagValue
                    if firstWord == '-rp': 
                        recording_prio = [x for x in flagValue.split(',')]
                    if firstWord == '-hm': 
                        host_mode = flagValue
                    if firstWord == '-nr': 
                        num_rtedumps = flagValue
                    if firstWord == '-ir': 
                        rtedumps_interval = flagValue
                    if firstWord == '-mr': 
                        rte_mode = flagValue
                    if firstWord == '-ks': 
                        kill_session = [x.strip('"') for x in flagValue.split(',')]
                    if firstWord == '-nc': 
                        num_callstacks = flagValue
                    if firstWord == '-ic': 
                        callstacks_interval = flagValue
                    if firstWord == '-ng': 
                        num_gstacks = flagValue
                    if firstWord == '-ig': 
                        gstacks_interval = flagValue
                    if firstWord == '-np': 
                        num_kprofs = flagValue
                    if firstWord == '-ip': 
                        kprofs_interval = flagValue
                    if firstWord == '-dp': 
                        kprofs_duration = flagValue
                    if firstWord == '-wp': 
                        kprofs_wait = flagValue
                    if firstWord == '-cf': 
                        critical_features = [x.strip('"') for x in flagValue.split(',')]
                    if firstWord == '-if': 
                        intervals_of_features = [x.strip('"') for x in flagValue.split(',')]
                    if firstWord == '-tf': 
                        feature_check_timeout = flagValue
                    if firstWord == '-ar': 
                        after_recorded = flagValue
                    if firstWord == '-od': 
                        out_dir = flagValue
                    if firstWord == '-or':
                        minRetainedLogDays = flagValue
                    if firstWord == '-lf': 
                        log_features = flagValue
                    if firstWord == '-en': 
                        email_notification = [x for x in flagValue.split(',')]
                    if firstWord == '-so': 
                        std_out = flagValue
                    if firstWord == '-ssl': 
                        ssl = flagValue
                    if firstWord == '-vlh':
                        virtual_local_host = flagValue
                    if firstWord == '-k': 
                        dbuserkey = flagValue
                    if firstWord == '-cpu': 
                        cpu_check_params = [x for x in flagValue.split(',')]
     
    #####################   INPUT ARGUMENTS (these would overwrite whats in the configuration file)  ####################     
    if '-oi' in sys.argv:
        online_test_interval = sys.argv[sys.argv.index('-oi') + 1]
    if '-pt' in sys.argv:
        ping_timeout = sys.argv[sys.argv.index('-pt') + 1]
    if '-ci' in sys.argv:
        check_interval = sys.argv[sys.argv.index('-ci') + 1]
    if '-rm' in sys.argv:
        recording_mode = sys.argv[sys.argv.index('-rm') + 1]
    if '-rp' in sys.argv:
        recording_prio = [x for x in sys.argv[  sys.argv.index('-rp') + 1   ].split(',')]
    if '-hm' in sys.argv:
        host_mode = sys.argv[sys.argv.index('-hm') + 1]
    if '-nr' in sys.argv:
        num_rtedumps = sys.argv[sys.argv.index('-nr') + 1]
    if '-ir' in sys.argv:
        rtedumps_interval = sys.argv[sys.argv.index('-ir') + 1]
    if '-mr' in sys.argv:
        rte_mode = sys.argv[sys.argv.index('-mr') + 1]
    if '-ks' in sys.argv:
        kill_session = [x.strip('"') for x in sys.argv[  sys.argv.index('-ks') + 1   ].split(',')] 
    if '-nc' in sys.argv:
        num_callstacks = sys.argv[sys.argv.index('-nc') + 1]
    if '-ic' in sys.argv:
        callstacks_interval = sys.argv[sys.argv.index('-ic') + 1]
    if '-ng' in sys.argv:
        num_gstacks = sys.argv[sys.argv.index('-ng') + 1]
    if '-ig' in sys.argv:
        gstacks_interval = sys.argv[sys.argv.index('-ig') + 1]
    if '-np' in sys.argv:
        num_kprofs = sys.argv[sys.argv.index('-np') + 1]
    if '-ip' in sys.argv:
        kprofs_interval = sys.argv[sys.argv.index('-ip') + 1]
    if '-dp' in sys.argv:
        kprofs_duration = sys.argv[sys.argv.index('-dp') + 1]
    if '-wp' in sys.argv:
        kprofs_wait = sys.argv[sys.argv.index('-wp') + 1]
    if '-cf' in sys.argv:
        critical_features = [x.strip('"') for x in sys.argv[  sys.argv.index('-cf') + 1   ].split(',')] 
        if critical_features == ['']:   # allow no critical feature with -cf ""
            critical_features = []      # make the length 0 in case of -cf ""
    if '-if' in sys.argv:
        intervals_of_features = [x.strip('"') for x in sys.argv[  sys.argv.index('-if') + 1   ].split(',')] 
    if '-tf' in sys.argv:
        feature_check_timeout = sys.argv[sys.argv.index('-tf') + 1]
    if '-ar' in sys.argv:
        after_recorded = sys.argv[sys.argv.index('-ar') + 1]
    if '-od' in sys.argv:
        out_dir = sys.argv[sys.argv.index('-od') + 1]
    if '-or' in sys.argv:
        minRetainedLogDays = sys.argv[sys.argv.index('-or') + 1]
    if '-lf' in sys.argv:
        log_features = sys.argv[sys.argv.index('-lf') + 1]
    if '-so' in sys.argv:
        std_out = int(sys.argv[sys.argv.index('-so') + 1])
    if '-en' in sys.argv:
        email_notification = [x for x in sys.argv[  sys.argv.index('-en') + 1   ].split(',')] 
    if '-ssl' in sys.argv:
        ssl = sys.argv[sys.argv.index('-ssl') + 1]
    if '-vlh' in sys.argv:
        virtual_local_host = sys.argv[sys.argv.index('-vlh') + 1]
    if '-k' in sys.argv:
        dbuserkey = sys.argv[sys.argv.index('-k') + 1]
    if '-cpu' in sys.argv:
        cpu_check_params = [x for x in sys.argv[  sys.argv.index('-cpu') + 1   ].split(',')]    
     
    ############ GET LOCAL HOST, LOCAL SQL PORT, LOCAL INSTANCE and SID ##########
    local_host = subprocess.check_output("hostname", shell=True).replace('\n','') if virtual_local_host == "" else virtual_local_host
    key_environment = subprocess.check_output('''hdbuserstore LIST '''+dbuserkey, shell=True) 
    if "NOT FOUND" in key_environment:
        print "ERROR, the key ", dbuserkey, " is not maintained in hdbuserstore."
        os._exit(1)
    ENV = key_environment.split('\n')[1].replace('  ENV : ','').split(',')
    key_hosts = [env.split(':')[0] for env in ENV] 
    if not local_host in key_hosts and not 'localhost' in key_hosts:
        #Turned out this check was not needed. A user that executed HANASitter from a non-possible future master with virtual host name virt2 only wanted
        #possible future masters in the hdbuserstore:   virt1:30413,virt3:30413,virt4:30413, so he executed HANASitter on virt2 with  -vlh virt2  --> worked fine
        #print "ERROR, local host, ", local_host, ", should be one of the hosts specified for the key, ", dbuserkey, ", in case of virtual use -vlh."
        #os._exit(1)
        #Instead of Error, just do Warning (consider to remove Warning...)
        print "WARNING, local host, ", local_host, ", should be one of the hosts specified for the key. It is not, so will assume the SQL port of the first one. Continue on own risk!"
        local_host_index = 0
    elif not local_host in key_hosts and 'localhost' in key_hosts:
        local_host_index = 0
    else:
        local_host_index = key_hosts.index(local_host)       
        
    key_sqlports = [env.split(':')[1] for env in ENV]    
    local_sqlport = key_sqlports[local_host_index]             
    dbinstances = [port[1:3] for port in key_sqlports]
    if not all(x == dbinstances[0] for x in dbinstances):
        print "ERROR: The hosts provided with the user key, "+dbuserkey+", does not all have the same instance number"
        os._exit(1)
    local_dbinstance = dbinstances[local_host_index]
    SID = subprocess.check_output('whoami', shell=True).replace('\n','').replace('adm','').upper()
    
    ### MDC or not, SystemDB or Tenant ###    
    tenantIndexserverPorts = [] # First assume non-mdc, if it finds tenant ports then it is mdc 
    output = subprocess.check_output('HDB info', shell=True).splitlines(1)   
    tenantIndexserverPorts = [line.split(' ')[-1].strip('\n') for line in output if "hdbindexserver -port" in line]
    tenantDBNames = [line.split(' ')[0].replace('adm','').upper() for line in output if "hdbindexserver -port" in line]  # only works if high-isolated
    is_mdc = len(tenantIndexserverPorts) > 0
    output = subprocess.check_output('ls -l '+cdalias('cdhdb', local_dbinstance)+local_host+'/lock', shell=True).splitlines(1)
    nameserverPort = [line.split('@')[1].replace('.pid','') for line in output if "hdbnameserver" in line][0].strip('\n') 
    
    ### TENANT NAMES for NON HIGH-ISOLATED MDC ###
    if is_mdc:
        if tenantDBNames.count(tenantDBNames[0]) == len(tenantDBNames) and tenantDBNames[0] == SID:   # if all tenant names are equal and equal to SystemDB's SID, then it is non-high-isolation --> get tenant names using daemon instead
            [tenantDBNames, tenantIndexserverPorts] = tenant_names_and_ports(cdalias('cdhdb', local_dbinstance)+local_host+"/daemon.ini") # if non-high isolation the tenantIndexserverPorts from HDB info could be wrong order

    
    ####### COMMUNICATION PORT (i.e. nameserver port if SystemDB at MDC, or indexserver port if TenantDB and if non-MDC) ########
    communicationPort = "-1"
    tenantDBName = None
    is_tenant = False
    if is_mdc:
        for dbname, port in zip(tenantDBNames, tenantIndexserverPorts):
            testTenant = Tenant(dbname, port, local_dbinstance, SID)
            if testTenant.sqlPort == int(local_sqlport):                           # then the sql port provided in hdbuserstore key is a tenant                   
                tenantDBName = testTenant.DBName
                is_tenant = True
                communicationPort = testTenant.getIndexserverPortString()          # indexserver port for the tenant
        if not is_tenant:
            communicationPort = nameserverPort                                     # nameserver port for SystemDB
    else:
        communicationPort = "3"+local_dbinstance+"03"                              # indexserver port for non-MDC
        if local_sqlport != "3"+local_dbinstance+"15":
            print "ERROR: The sqlport provided with the user key, "+dbuserkey+", is wrong. For non-MDC it must be 3<inst-nbr>15, but it is "+local_sqlport+".\nNOTE: MDC systems must show hdbindexserver -port when HDB info is executed, otherwise it is not supported by HANASitter."
            os._exit(1)
            
    ### SCALE OUT or Single Host ###
    hosts_worker_and_standby = subprocess.check_output('sapcontrol -nr '+local_dbinstance+' -function GetSystemInstanceList', shell=True).splitlines(1)
    hosts_worker_and_standby = [line.split(',')[0] for line in hosts_worker_and_standby if ("HDB" in line or "HDB|HDB_WORKER" in line or "HDB|HDB_STANDBY" in line)] #Should we add HDB|HDB_XS_WORKER also?
    for aHost in key_hosts:  #Check that hosts provided in hdbuserstore are correct
        if not aHost in hosts_worker_and_standby and not aHost in ['localhost']:
            print "ERROR: The host, "+aHost+", provided with the user key, "+dbuserkey+", is not one of the worker or standby hosts: ", hosts_worker_and_standby
            os._exit(1)
            
    ### HOST(S) USED BY THIS DB ###
    used_hosts = []
    for potential_host in hosts_worker_and_standby:        
        if '@'+communicationPort in subprocess.check_output('ls -l '+cdalias('cdhdb', local_dbinstance)+potential_host+'/lock', shell=True):
            used_hosts.append(potential_host)

    ############# OUTPUT DIRECTORY #########
    out_dir = out_dir.replace(" ","_")
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
 
    ############ CHECK AND CONVERT INPUT PARAMETERS FOR COMMUNICATION MANAGER ################     
    log("\nHANASitter executed "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" with \n"+" ".join(sys.argv)+"\nas "+dbuserkey+": "+key_environment, CommunicationManager(dbuserkey, out_dir, True, "", False))  
    ### std_out, -so
    std_out = checkAndConvertBooleanFlag(std_out, "-so")
    ### ssl, -ssl
    ssl = checkAndConvertBooleanFlag(ssl, "-ssl")
    hdbsql_string = "hdbsql "
    if ssl:
        hdbsql_string = "hdbsql -e -ssltrustcert -sslcreatecert "
    ### log_features, -lf
    log_features = checkAndConvertBooleanFlag(log_features, "-lf")
    if log_features and len(critical_features) == 0:
        log("INPUT ERROR: -lf is True even though -cf is empty, i.e. no critical feature specified. This does not make sense. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, std_out, hdbsql_string, False))
        os._exit(1) 
        
    ############# COMMUNICATION MANAGER ##############
    comman = CommunicationManager(dbuserkey, out_dir, std_out, hdbsql_string, log_features)        
        
    ############ CHECK AND CONVERT THE REST OF THE INPUT PARAMETERS ################
    ### online_test_interval, -oi  
    if not is_integer(online_test_interval):
        log("INPUT ERROR: -oi must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    online_test_interval = int(online_test_interval)
    ### ping_timeout, -pt
    if not is_integer(ping_timeout):
        log("INPUT ERROR: -pt must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    ping_timeout = int(ping_timeout)
    if  ping_timeout < 0:
        log("INPUT ERROR: -pt cannot be negative. Please see --help for more information.", comman)
        os._exit(1)
    ### check_interval, -ci
    if not is_integer(check_interval):
        log("INPUT ERROR: -ci must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    check_interval = int(check_interval)
    ### recording_mode, -rm
    if not is_integer(recording_mode):
        log("INPUT ERROR: -rm must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    recording_mode = int(recording_mode)
    if not recording_mode in [1, 2, 3]:
        print "INPUT ERROR: The -rm flag must be either 1, 2, or 3. Please see --help for more information."
        os._exit(1)           
    ### recording_prio, -rp
    if not len(recording_prio) == 4:
        print "INPUT ERROR: The -rp flag must be followed by 4 items, seperated by comma. Please see --help for more information."
        os._exit(1)
    if not (recording_prio[0].isdigit() or recording_prio[1].isdigit() or recording_prio[2].isdigit() or recording_prio[3].isdigit()):
        print "INPUT ERROR: The -rp flag must be followed by positive integers, seperated by commas. Please see --help for more information."
        os._exit(1)
    recording_prio = [int(rec) for rec in recording_prio]
    if not (recording_prio[0] in [1,2,3,4] or recording_prio[1] in [1,2,3,4] or recording_prio[2] in [1,2,3,4] or recording_prio[3] in [1,2,3,4]):
        print "INPUT ERROR: The -rp flag must be followed by integers of the values withing [1-4]. Please see --help for more information."
        os._exit(1)     
    if [rec for rec in recording_prio if recording_prio.count(rec) > 1]:
        print "INPUT ERROR: The -rp flag must not contain dublicates. Please see --help for more information."
        os._exit(1)  
    ### host_mode, -hm
    host_mode = checkAndConvertBooleanFlag(host_mode, "-hm")
    if host_mode and not (len(hosts_worker_and_standby) > 1):
        log("WARNING: INPUT ERROR: -hm is True even though this is not a scale-out. This does not make sense. Please see --help for more information.", comman)
        log("Will now change -hm to False", comman)
        host_mode = False
    if host_mode and log_features:
        log("INPUT ERROR, it is not supported to log features (-lf) if host mode (-hm) is used. Please see --help for more information.", comman)
        os._exit(1)    
    if host_mode and num_gstacks:
        log("INPUT ERROR, gstack recording (-ng) is not supported in host mode (-hm). Please see --help for more information.", comman)
        os._exit(1)   
    ### num_rtedumps, -nr
    if not is_integer(num_rtedumps):
        log("INPUT ERROR: -nr must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    num_rtedumps = int(num_rtedumps)
    ### rtedumps_interval, -ir
    if not is_integer(rtedumps_interval):
        log("INPUT ERROR: -ir must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    rtedumps_interval = int(rtedumps_interval)
    ### rte_mode, -mr
    if not is_integer(rte_mode):
        log("INPUT ERROR: -mr must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    rte_mode = int(rte_mode)
    if not rte_mode in [0, 1]:
        print "INPUT ERROR: The -mr flag must be either 0 or 1. Please see --help for more information."
        os._exit(1)      
    ### num_callstacks, -nc
    if not is_integer(num_callstacks):
        log("INPUT ERROR: -nc must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    num_callstacks = int(num_callstacks)
    ### callstacks_interval, -ic
    if not is_integer(callstacks_interval):
        log("INPUT ERROR: -ic must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    callstacks_interval = int(callstacks_interval)    
    ### num_gstacks, -ng
    if not is_integer(num_gstacks):
        log("INPUT ERROR: -ng must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    num_gstacks = int(num_gstacks)
    ### gstacks_interval, -ig
    if not is_integer(gstacks_interval):
        log("INPUT ERROR: -ig must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    gstacks_interval = int(gstacks_interval)
    ### num_kprofs, -np
    if not is_integer(num_kprofs):
        log("INPUT ERROR: -np must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    num_kprofs = int(num_kprofs)
    ### kprofs_interval, -ip
    if not is_integer(kprofs_interval):
        log("INPUT ERROR: -ip must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    kprofs_interval = int(kprofs_interval)    
    ### kprofs_duration, -dp
    if not is_integer(kprofs_duration):
        log("INPUT ERROR: -dp must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    kprofs_duration = int(kprofs_duration)
    ### kprofs_wait, -wp
    if not is_integer(kprofs_wait):
        log("INPUT ERROR: -wp must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    kprofs_wait = int(kprofs_wait)
    ### feature_check_timeout, -tf
    if not is_integer(feature_check_timeout):
        log("INPUT ERROR: -tf must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    feature_check_timeout = int(feature_check_timeout)    
    ### after_recorded, -ar
    if not is_integer(after_recorded):
        log("INPUT ERROR: -ar must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    after_recorded = int(after_recorded)
    ### minRetainedLogDays, -or
    if not is_integer(minRetainedLogDays):
        log("INPUT ERROR: -or must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    minRetainedLogDays = int(minRetainedLogDays)
    ### critical_features, -cf
    if len(critical_features)%4: # this also allow empty list in case just only ping check without feature check; -cf ""
        log("INPUT ERROR: -cf must be a list with the length of multiple of 4. Please see --help for more information.", comman)
        os._exit(1)
    critical_features = [critical_features[i*4:i*4+4] for i in range(len(critical_features)/4)]
    critical_features = [CriticalFeature(cf[0], cf[1], cf[2], cf[3]) for cf in critical_features] #testing cf[3] is done in the class
    ### kill_session, -ks
    if kill_session:
        if not len(kill_session) == len(critical_features):
            log("INPUT ERROR: -ks must be a list with the same length as number features specified with -cf. Please see --help for more information.", comman)
            os._exit(1)
        kill_session = [checkAndConvertBooleanFlag(ks, "-ks") for ks in kill_session]
        for i in range(len(kill_session)):
            critical_features[i].setKillSession(kill_session[i])
    ### intervals_of_features, -if
    if intervals_of_features:
        if len(intervals_of_features)%2:
            log("INPUT ERROR: -if must be a list with the length of multiple of 2. Please see --help for more information.", comman)
            os._exit(1)
        intervals_of_features = [intervals_of_features[i*2:i*2+2] for i in range(len(intervals_of_features)/2)]
        if not len(intervals_of_features) == len(critical_features):
            log("INPUT ERROR: -if must specify as many intervals as number of critical feature. Please see --help for more information.", comman)
            os._exit(1)
        for i in range(len(intervals_of_features)):
            if not is_integer(intervals_of_features[i][0]) or not is_integer(intervals_of_features[i][1]):
                log("INPUT ERROR: -if must have two integers as input. Please see --help for more information.", comman)
                os._exit(1)
            critical_features[i].setIterations(int(intervals_of_features[i][0]), int(intervals_of_features[i][1]))
    ### cpu_check_params, -cpu
    if not len(cpu_check_params) == 4:
        log("INPUT ERROR: The -cpu flag must be followed by 4 items, seperated by comma. Please see --help for more information.", comman)
        os._exit(1)
    if not (cpu_check_params[0].isdigit() or cpu_check_params[1].isdigit() or cpu_check_params[2].isdigit() or cpu_check_params[3].isdigit()):
        log("INPUT ERROR: The -cpu flag must be followed by positive integers, seperated by commas. Please see --help for more information.", comman)
        os._exit(1)
    if int(cpu_check_params[3]) > 100:
        log("INPUT ERROR: The fourth element of the -cpu flag is in %, i.e. [0,100]. Please see --help for more information.", comman)
        os._exit(1)
    if not (int(cpu_check_params[0]) in [0,1,2]):
        log("INPUT ERROR: CPU checks type has to be either 0, 1 or 2. Please see --help for more information.", comman)
        os._exit(1)
    if (int(cpu_check_params[0]) > 0) and (int(cpu_check_params[1]) == 0):
        log("INPUT ERROR: If cpu checks with this cpu type are to be done the number of checks cannot be zero. Please see --help for more information.", comman)
        os._exit(1)
    if (int(cpu_check_params[0]) > 0) and (int(cpu_check_params[2]) == 0):
        log("INPUT ERROR: If cpu checks with this cpu type are to be done the interval cannot be zero. Please see --help for more information.", comman)
        os._exit(1)
    if (int(cpu_check_params[1]) > 0) and (int(cpu_check_params[0]) == 0):
        log("INPUT ERROR: If this number of cpu checks are to be done the cpu type cannot be zero. Please see --help for more information.", comman)
        os._exit(1)
    if (int(cpu_check_params[2]) > 0) and (int(cpu_check_params[0]) == 0):
        log("INPUT ERROR: If cpu checks with this intervall are to be done the cpu type cannot be zero. Please see --help for more information.", comman)
        os._exit(1)
    ### num_rtedumps, -nr, num_callstacks, -nc, num_gstacks, -ng, num_kprofs, -np, log_features, -lf
    if not kill_session:
        if (num_rtedumps <= 0 and num_callstacks <= 0 and num_gstacks <= 0 and num_kprofs <= 0 and log_features == False):
            log("INPUT ERROR: No kill-session and no recording is specified (-nr, -nc, -ng, and -np are all <= 0, or none of them are specified and -lf = false). It then makes no sense to run hanasitter. Please see --help for more information.", comman)
            os._exit(1)
    ### email_notification, -en
    if email_notification:
        if not len(email_notification) == 3:
            log("INPUT ERROR: -en requires 3 elements, seperated by a comma only. Please see --help for more information.", comman)
            os._exit(1)
        if not is_email(email_notification[0]) or not is_email(email_notification[1]):
            log("INPUT ERROR: first and second element of -en have to be valid emails. Please see --help for more information.", comman)
            os._exit(1)

    ############# EMAIL NOTIFICATION ##############
    if email_notification:
        global emailNotification
        emailNotification = EmailNotification(email_notification[0], email_notification[1], email_notification[2], SID)

    ### FILL HDBCONS STRINGS ###
    hdbcons = HDBCONS(local_host, used_hosts, local_dbinstance, is_mdc, is_tenant, communicationPort, SID, rte_mode, tenantDBName)

    ################ START #################
    if is_mdc:
        if is_tenant:
            printout = "Host = "+str(local_host)+", SID = "+SID+", DB Instance = "+str(local_dbinstance)+", MDC tenant = "+tenantDBName+", Indexserver Port = "+str(communicationPort)
        else:
            printout = "Host = "+str(local_host)+", SID = "+SID+", DB Instance = "+str(local_dbinstance)+", MDC SystemDB, Nameserver Port = "+str(communicationPort)
    else:
        printout = "Host = "+str(local_host)+", SID = "+SID+", DB Instance = "+str(local_dbinstance)            
    if (len(hosts_worker_and_standby) > 1):
        printout += "\nScale Out DB System with hosts: "+", ".join([h for h in hosts_worker_and_standby])
        if is_mdc:
            if is_tenant:        
                printout += "\nTenant DB "+tenantDBName+"@"+SID+" uses host(s): "+", ".join([h for h in used_hosts])
            else:
                printout += "\nSystemDB@"+SID+" uses host(s): "+", ".join([h for h in used_hosts])
    log(printout, comman)       
    log("Online, Primary and Not-Secondary Check: Interval = "+str(online_test_interval)+" seconds", comman)
    log("Ping Check: Interval = "+str(check_interval)+" seconds, Timeout = "+str(ping_timeout)+" seconds", comman)
    log("Feature Checks: Interval "+str(check_interval)+" seconds, Timeout = "+str(feature_check_timeout)+" seconds", comman)
    if host_mode:
        log("Host Mode: Yes, i.e. all critical features below is PER HOST, and recording is done only for those hosts where a critical feature was found crossing allowed limit", comman)
    chid = 0
    for cf in critical_features:
        chid += 1
        printout = "Feature Check "+str(chid)
        if cf.limitIsMinimumNumberCFAllowed:
            printout += " requires at least "+str(cf.limit)+" times that "+cf.whereClauseDescription
        else:
            printout += " allows only "+str(cf.limit)+" times that "+cf.whereClauseDescription
        if cf.nbrIterations > 1:
            printout += " as an average from "+str(cf.nbrIterations)+" checks with "+str(cf.interval)+" seconds intervals" 
        log(printout, comman)
    if log_features:
        log("All information for all features that are in one of the above critical feature states is recorded in the "+comman.out_dir+"/criticalFeatures log", comman)
    log("Recording mode: "+str(recording_mode), comman)
    log("Recording Type      , Number Recordings   ,   Intervals [seconds] ,   Durations [seconds]      ,    Wait [milliseconds]", comman)  
    log("GStack              , "+str(num_gstacks)+"                   ,   "+str(gstacks_interval)+"                  ,   ", comman)
    log("Kernel Profiler     , "+str(num_kprofs)+"                   ,   "+str(kprofs_interval)+"                  ,   "+str(kprofs_duration)+"                       ,    "+str(kprofs_wait), comman)
    log("Call Stack          , "+str(num_callstacks)+"                   ,   "+str(callstacks_interval)+"                  ,   ", comman)
    if rte_mode == 0:
        log("RTE Dumps (normal)  , "+str(num_rtedumps)+"                   ,   "+str(rtedumps_interval)+"                  ,   ", comman)
    else: # change if more modes are added
        log("RTE Dumps (light)   , "+str(num_rtedumps)+"                   ,   "+str(rtedumps_interval)+"                  ,   ", comman)
    log("Recording Priority: "+recording_prio_convert(recording_prio), comman)
    if int(cpu_check_params[0]) > 0:
        cpu_string = "User CPU Check:     " if int(cpu_check_params[0]) == 1 else "System CPU Check: "
        log(cpu_string+", Every "+cpu_check_params[2]+" seconds, Number CPU Checks = "+cpu_check_params[1]+", Max allowed av. CPU = "+cpu_check_params[3]+" %", comman)
    if after_recorded < 0:
        log("After Recording: Exit", comman)
    else:
        log("After Recording: Sleep "+str(after_recorded)+" seconds", comman)
    log(" - - - - - Start HANASitter - - - - - - ", comman)
    log("Action            , Timestamp              , Duration         , Successful   , Result     , Comment ", comman)
    rte = RTESetting(num_rtedumps, rtedumps_interval)
    callstack = CallStackSetting(num_callstacks, callstacks_interval)
    gstack = GStackSetting(num_gstacks, gstacks_interval)
    kprofiler = KernelProfileSetting(num_kprofs, kprofs_interval, kprofs_duration, kprofs_wait)
    try:
        if num_kprofs: #only if we write kernel profiler dumps will we need temporary output folders
            hdbcons.create_temp_output_directories() #create temporary output folders
        while True: 
            if is_online(local_dbinstance, comman) and not is_secondary(comman):
                [recorded, offline] = tracker(ping_timeout, check_interval, recording_mode, rte, callstack, gstack, kprofiler, recording_prio, critical_features, feature_check_timeout, cpu_check_params, minRetainedLogDays, host_mode, comman, hdbcons)
                if recorded:
                    if after_recorded < 0: #if after_recorded is negative we want to exit after a recording
                        hdbcons.clear()    #remove temporary output folders before exit
                        sys.exit()
                    time.sleep(float(after_recorded))  # after recorded call stacks and/or rte dumps it sleeps a bit and then continues tracking if HANA is online
            else:
                log("\nOne of the online checks found out that this HANA instance is not online. HANASitter will now have a "+str(online_test_interval)+" seconds break.\n", comman)
                time.sleep(float(online_test_interval))  # wait online_test_interval seconds before again checking if HANA is running
    #except:           
    except Exception as e:
        print "HANASitter stopped with the exception: ", e
        hdbcons.clear()    #remove temporary output folders before exit
        sys.exit()
    except KeyboardInterrupt:   # catching ctrl-c
        print "HANASitter was stopped with ctrl-c"
        hdbcons.clear()    #remove temporary output folders before exit
        sys.exit()
          
              
if __name__ == '__main__':
    main()
                        

