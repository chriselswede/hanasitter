# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from threading import Timer
import sys, time, os, subprocess
from multiprocessing import Pool
import traceback
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
    print("         Possible cpu types are: 0 = not used, 1 = user cpu, 2 = system cpu, 3 = both user and system                                               ")
    print(" -pt     ping timeout [seconds], time it waits before the DB is considered unresponsive (select * from dummy), if set to 0 the ping test will       ")
    print("         not be done, default: 60 seconds                                                                                                           ")           
    print(' -cf     list of features surrounded by two "s; the -cf flag has two modes, 1. One Column Mode and 2. Where Clause Mode                             ')
    print("         1. One Column Mode: any sys.m_* view, a column in that view, the column value (wildcards, *, before and/or after are possible) and         ")
    print("            max number allowed feature occations, i.e.                                                                                              ")
    print('            "<m_view 1>,<feature 1>,<[*]value 1[*]>,<limit 1>,...,<m_view N>,<feature N>,<[*]value N[*]>,<limit N>"                                 ')
    print("         2. Where Clause Mode: any sys.m_* view, the keyword 'WHERE', the where clause and max number allowed feature occations, i.e.               ")
    print('            "<m_view 1>,WHERE,<where clause 1>,<limit 1>,...,<m_view N>,WHERE,<where clause N>,<limit N>"                                           ')
    print('         default: ""                                                                                                                                ')
    print('         Note: <limit> should be an integer, or an integer preceded by < (for maximum allowed) or > (for minumum allowed)                           ')
    print('         Note: If you need a , in critical feature, please use \c instead, e.g. add_seconds(BLOCKED_TIME\c600)                                      ')
    print(' -ct     critical feature text [list with comma separated strings], this list must be the same length as number of critical features, specified by  ')
    print('         -cf and instead of a space there must be an underscore: _ . This text will be provided in the output (and in emails) when the              ')
    print('         corresponding feature is critical.                                                                 default: [] (not used)                  ')
    print(' -cd     critical feature deliminiter mode, 1 = the deliminiter of -cf is ,  2 = the deliminiter of -cf is ;     default: 1 (backward compatible)   ')
    print('         Note: Sometimes it is needed to have a , in the SQL of the WHERE clause for -cf, e.g. ADD_SECONDS(CURRENT_TIME, -60), then use -cd 2       ')
    print(" -if     number checks and intervals of checks, every odd item of this list specifies how many times each feature check (see -cf) should be executed")
    print("         and every even item specifies how many seconds it waits between each check, then the <max numbers X> in the -cf flag is the maximum        ")
    print("         allowed average value, e.g. <number checks 1>,<interval [s] 1>,...,<number checks N>,<interval [s] N>,                                     ")  
    print("         default: [] (not used) so if you only require one check per feature, do not use -if                                                        ")
    print(" -tf     feature check time out [seconds], time it waits before the DB is considered unresponsive during a feature check                            ")
    print("         (see -cf), if -if is used this time out will be added to the interval and then multiplied with number checks, default: 60 seconds          ")
    print(" -sc     sql cache check min diff pct [%], this specifies the minimum difference in percentage in average execution duration of a statement compared")
    print("         to that same statement after it changed the execution engine, i.e. if difference is above this, this could be considered a potential       ")
    print("         critical engine change     (note: the sql cache check will only be executed if recording has not already been done from either the         ")
    print("         CPU check, Ping check or Feature Check),                               default: -1  (the sql cache check is not executed)                  ")  
    print(" -spi    use plan id change instead of engine change [true/false], if this is true the -sc check will be done for each Plan ID change instead of    ")
    print("         only Execution Engine change (as per default), default: false                                                                              ")
    print('         Note: Use with care! If HANASitter stops with the exception "Argument list too long" stop using -spi or restrict more with -scc, -sct, -scd') 
    print(" -scc    min execution count to be considered in the sql cache check,   default: 0     (consider even if only executed once after engine change)    ")
    print(" -sct    min total execution time [minutes] to be considered in the sql cache check, default: 0  (consider even if total execution time is almost 0)")
    print(" -scp    number hours printed before and after the max snapshot time of a potential critical engine change, default: 0    (nothing will be printed) ")
    print("         Note: If nothing is printed try to increase -scp so that it will include an engine change                                                  ")
    print("         Note: It might be better to do your own investigation on HOST_SQL_PLAN_CACHE after you got the potential critical engine changes from -sc  ")
    print(" -scn    only negative changes [false/true], if true will only show engine changes that made performance worse, default: false                      ")
    print(" -scx    number characters of the sql text printed together with the outputs defined by -scp, default: 0                                            ")
    print(" -scpa   number characters of the application source printed together with the outputs defined by -scp, default: 0                                  ")
    print(" -scd    number of days to take into account, this specifies how many days back we want to include from the SQL plan cache to look for changes      ")
    print("         in the engine (-sc) and/or changes in the plan id (-spi) default: the whole SQL plan cache is taken into account                           ")
    print(" -scs    number of days to take into account for statistics, this specified how many days back we want to include from the SQL plan cache to        ")
    print("         calculate average difference in percentage of execution duration, to compare with limit provided by -sc,                                   ")
    print("         default: the whole SQL plan cache is taken into account                                                                                    ")
    print(" -lf     log features [true/false], logging ALL information of ALL critical features (beware: could be costly!), default: false                     ")
    print("         Note: For safety reasons, -lf is not available anymore, unless you enable it yourself in the python code.                                  ")
    print(" -ci     check interval [seconds], time it waits before it checks cpu, pings and check features again,                                              ")
    print("         if set to 0 HANASitter will not continue even if it does not find any reason to record,                          default: 60 seconds       ") 
    print(" -ar     time to sleep after recording [seconds], if negative it exits, default: -1                                                                 ")
    print("         *** RECORDINGS (GStacks and/or Kernel Profiler Traces and/or Call Stacks and/or RTE dumps and/or Output from Custom SQL) ***               ")
    print(" -sv     services [indexserver, nameserver, compileserver, preprocessor, docstore, dpserver, scriptserver, xsengine, diserver, and/or webdispatcher]")
    print("         the service(s) that hdbcons will connect to for recording,    default = ''   (connect to the SQL port in the key)                          ")
    print("         Note: for only recording from an indexserver or nameserver it is better simply specify the port(s) in the key(s), i.e. then do not use -sv ")
    print("         Note: see SAP Notes 2222218 and 2410143 for more info                                                                                      ")
    print(" -svp    print found services [true/false], the ports of the services requested by -sv must be found using trace files (cannot use SQL since cannot ")
    print("         assume HANA is up), if no proper trace file is found that service will be ignored, therefore it could be useful to print all the found     ")
    print("         services and respective ports, default: false                                                                                              ")
    print(" -rm     recording mode [1, 2 or 3], 1 = each requested recording types are done one after each other with the order above,                         ")
    print("                                         e.g. GStack 1, GStack 2, ..., GStack N, RTE 1, RTE 2, ..., RTE N   (this is default)                       ")
    print("                                     2 = the recordings of each requested recording types are done after each other with the                        ")
    print("                                         order above, e.g. GStack 1, RTE 1, Gstack 2, RTE 2, ...                                                    ")
    print("                                     3 = different recording types recorded in parallel threads, e.g. if 2 GStacks and 1 RTE                        ")
    print("                                         requested then GStack 1 and RTE 1 are parallel done, when both done GStack 2 starts                        ")
    print(" -rp     recording priorities [list of 6 integers [1,6]] defines what order the recording modes will be executed for rm = 1 and rm = 2              ")
    print("                # 1 = RTE, # 2 = CallStacks, # 3 = GStacks, # 4 = Kernel Profiler, # 5 = Custom SQL, # 6 = Customer Query     default: 1,2,3,4,5,6  ")
    print(" -hm     host mode [true/false], if true then all critical features are considered per host and the recording is done only for those hosts where    ")
    print("                                 the critical feature is above allowed limit per host, default: false                                               ")
    print("                                 Note: -hm is not supported for gstack (-ng), but for the other recording possibilities (-np, -nc, and -nr)         ")
    print(" -ng     number indexserver gstacks created if the DB is considered unresponsive (Note: gstack blocks the indexserver! See SAP Note 2000000         ")
    print('         "Call stack generation via gstack"), default: 0  (not used)                                                                                ') 
    print(" -ig     gstacks interval [seconds], for -rm = 1: time it waits after a gstack,                                                                     ")
    print("                                     for -rm = 2: time it waits after a gstack,                                                                     ")
    print("                                     for -rm = 3: time the thread waits after a gstack,          default: 60 seconds                                ")
    print(" -np     number indexserver kernel profiler traces created if the DB is considered unresponsive: default: 0  (not used)                             ") 
    print(" -dp     profiler duration [seconds], how long time it is tracing, default: 60 seconds   (more info: SAP Note 1804811)                              ")
    print(" -wp     profiler wait time [milliseconds], wait time after callstacks of all running threads have been taken, default 0                            ")
    print(" -ip     profiler interval [seconds], for -rm = 1: time it waits after a profiler trace,                                                            ")
    print("                                      for -rm = 2: time it waits after a profiler trace,                                                            ")
    print("                                      for -rm = 3: time the thread waits after a profiler trace,         default: 60 seconds                        ")
    print(" -nc     number call stacks created if the DB is considered unresponsive: default: 0  (not used)                                                    ") 
    print(" -ic     call stacks interval [seconds], for -rm = 1: time it waits after a call stack,                                                             ")
    print("                                         for -rm = 2: time it waits after a call stack,                                                             ")
    print("                                         for -rm = 3: time the thread waits after a call stack,  default: 60 seconds                                ")
    print(" -nr     number rte dumps created if the DB is considered unresponsive, default: 0    (not used)                                                    ") 
    print("         Note: output is restricted to these folders /tmp, $HOME, $DIR_INSTANCE/work, and $SAP_RETRIEVAL_PATH                                       ")
    print(" -ir     rte dumps interval [seconds], for -rm = 1: time it waits after an rte dump,                                                                ")
    print("                                       for -rm = 2: time it waits after an rte dump,                                                                ")
    print("                                       for -rm = 3: time the thread waits after an rte dump,     default: 60 seconds                                ")
    print(" -mr     rte dump mode [0 or 1], -mr = 0: normal rte dump,                                                                                          ")
    print("                                 -mr = 1: light rte dump mode, only rte dump with STACK_SHORT and THREADS sections, and some M_ views,  default: 0  ")
    print(" -pr     profile for section restriction, see hdbcons -->  help runtimedump --> -p and SAP Note 2400007 #14 for more info, default ''               ")
    print(" -ns     number custom select outputs provided if the DB is considered in a potential critical situation,  default: 0 (not used)                    ")
    print(" -is     custom select interval [seconds], for -rm = 1: time it waits after a custom select,                                                        ")
    print("                                           for -rm = 2: time it waits after a custom select,                                                        ")
    print("                                           for -rm = 3: time the thread waits after a custom select,     default: 60 seconds                        ")
    print(" -cs     custom sql, this SELECT statement defines the output (see the -cs example below),     default: ''  (not used)                              ")
    print(" -cq     custom queries, a list of queries that will be executed (-cd decides deliminiter mode also for -cq),              default: '' (not used)   ")
    print(" -iq     custom query waits [comma seperated list (same length as -cq) of integers = seconds],                                                      ")
    print("                                           for -rm = 1: time it waits after a custom query,             default: none, it must be defined           ")
    print("                                           for -rm = 2: time it waits after a custom query,             default: none, it must be defined           ")
    print("                                           for -rm = 3: -iq and -cq are not supported for -rm = 3                                                   ")
    print("         *** KILL SESSIONS (use with care!) ***                                                                                                     ")
    print(' -ks     kill session [list of "0","C", or "D"], list of the characters 0, C, or D (length of the list must be the same as number of features       ')
    print("         defined by -cf) that defines if -cf's features could indicate that the sessions (connections) should be tried to be cancelled (C), or      ")
    print("         disconnected (D) or not (0), default: None (not used)                                                                                      ")
    print("         Note: Requires SESSION ADMIN                                                                                                               ")
    print("         *** ADMINS (Output Directory, Logging, Output and DB User) ***                                                                             ")
    print(" -od     output directory, full path of the folder where output files will end up (if the folder does not exist it will be created),                ")
    print("         default: '/tmp/hanasitter_out'   (i.e. same as for -ol)                                                                                    ")
    print(" -odr    output retention days, output files in the path specified with -od are only saved for this number of days, default: -1 (not used)          ")
    print("         NOTE: -od and -odr holds for hanasitter logs also if -ol and -olr are not specified.                                                       ")
    print(" -ol     log output directory, full path of the folder where HANASitter log files will end up (if the folder does not exist it will be created),    ")
    print("         default: '/tmp/hanasitter_out'   (i.e. same as for -od)                                                                                    ")
    print(" -olr    log retention days, hanasitterlogs in the path specified with -ol are only saved for this number of days, default: -1 (not used)           ")
    print(" -oc     output configuration [true/false], logs all parameters set by the flags and where the flags were set, i.e. what flag file                  ")
    print("         (one of the files listed in -ff) or if it was set via a flag specified on the command line, default = false                                ")
    print(" -en     email notification, <receiver 1's email>,<receiver 2's email>,... default:          (not used)                                             ")
    print("         Note: If you recieve an email from this                                                                                                    ")
    print('                             echo "Text in email" | mailx -s "subject" <your email address>                                                         ')
    print("         then there is no need for any of the below -en* flags. Contact your Linux expert for more information.                                     ")
    print(" -enc    email client, to explicitly specify the email client (e.g mail, mailx, mutt, ...,), only useful if -en if used, default: mailx             ") 
    print(" -ens    sender's email, to explicitly specify sender's email address, only useful if -en if used, default:    (sender's email configured used)     ")
    print(" -enm    mail server, to explicitly specify mail server, only useful if -en is used, default:                  (mail server configured used)        ")
    print('         NOTE: For this to work you have to install the linux program "sendmail" and add a line similar to DSsmtp.intra.ourcompany.com in the file  ')
    print("               sendmail.cf in /etc/mail/, see https://www.systutorials.com/5167/sending-email-using-mailx-in-linux-through-internal-smtp/           ")
    print(" -so     standard out switch [true/false], switch to write to standard out, default:  true                                                          ")
    print(" -or     output run commands [true/false], prints out most run commands, default: false                                                             ")
    print(" -ff     flag file(s), a comma seperated list of full paths to a files that contain input flags, each flag in a new line, all lines in the file     ")
    print("         that do not start with a flag (a minus) are considered comments, default: '' (not used)                                                    ")
    print(" -ssl    turns on ssl certificate [true/false], makes it possible to use SAP HANA Sitter despite SSL, the following string is added to the hdbsql   ")
    print("         command:    -e -ssltrustcert -sslcreatecert  , default: false                                                                              ") 
    print(" -encr   turns on encryption [true/false], adds only  -e   to the hdbsql commend, default: false                                                    ") 
    print(" -sslk   sslkeystore, to provide the name, with full path, of the ssl key store, default: '' (not used)                                             ")
    print(" -sslt   ssltruststore, to provide the name, with full path, of the ssl trust store, default: '' (not used)                                         ")
    print(" -sslp   sslprovider, to provide the name of the ssl provider, default: '' (not used)                                                               ")
    print(" -ssln   sslhostnameincert, to provide the full name of the ssl certificate for the host,  default: '' (not used)                                   ")
    print(" -vlh    virtual local host, if hanacleaner runs on a virtual host this has to be specified, default: '' (physical host is assumed)                 ")
    print(" -hc     host checking [true/false], checks if the host is the same as in cdtrace and provided in hdbuserkey, might be necessary to turn to false   ")
    print("         e.g. if you for some reason must provide full host name in hdbuserkey (it will still give warnings though), default: true                  ")
    print(" -hi     high isolation [true/false], normally HANASitter detect if you have High Isolation, but if it doesn't and you claim you have               ")
    print("         high isolation, can force HANASitter beliving you have with   -hi true    , default: false                                                 ")
    print(" -sh     shell, default: /bin/bash                                                                                                                  ")   
    print(" -hev    hdbsql environment variable, for any environment variable that should be added to the hdbsql command, do not include the $ sign, it will   ")
    print("         added automatically, e.g. -hev SSL_OPTIONS, default: ''                                                                                    ")             
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
    print("EXAMPLE (use -cd 2 to use ; as deliminiter of -cf instead of ,)                                                                                     ")
    print('''> python hanasitter.py -cf "M_SERVICE_THREADS;WHERE;IS_ACTIVE='TRUE' and SERVICE_NAME='indexserver';3" -nc 1 -cd 2                              ''')
    print("                                                                                                                                                    ")
    print("EXAMPLE (if at least one of the two tables didn't have a delta merge started at least 5 minutes ago,                                                ")
    print("         an email will be send and a call stack will be written)                                                                                    ")
    print('''> python hanasitter.py -cf "M_DELTA_MERGE_STATISTICS;WHERE;SCHEMA_NAME = 'DMM260' and TABLE_NAME in ('QUALITY', 'TESTSCORES') and               ''')
    print('''  SECONDS_BETWEEN(TO_TIMESTAMP(START_TIME,'YYYY-MM-DD HH24:MI:SS.FF7'),CURRENT_TIMESTAMP)<300;>2" -cd 2 -en christian.hansen01@sap.com          ''')
    print('''  -ct "The_last_deltamerge_on_the_two_tables_are_older_than_5_min" -nc 1 -k T1KEY                                                               ''')
    print("                                                                                                                                                    ")
    print("EXAMPLE (if > 30 THREAD_STATE=Running, or if a configuration parameter was changed today, then a call stack will be dumped and an email will be send")
    print("         with dedicated text)                                                                                                                       ")
    print('  > python hanasitter.py -cf "M_SERVICE_THREADS,THREAD_STATE,Running,30,M_INIFILE_CONTENT_HISTORY,WHERE,TO_DATE(TIME)=CURRENT_DATE,0" -nc 1         ')
    print('                         -ct "Too_many_running_threads,At_least_one_configuration_parameter_was_changed_today" -en chris@du.my                      ')
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
    print("EXAMPLE (if hana is unresponsible for over 10 seconds or if there are more than 500 active but not running threads, then the output dump of )       ")
    print("         a certain custom made SELECT statement (here: SELECT on the view M_DEV_TRANSACTIONIS_HISTORY_ 4 hours back) is provided as a result file   ")
    print('''> python hanasitter.py -k <key> -pt 10 -cf "M_SERVICE_THREADS,WHERE,IS_ACTIVE='TRUE' AND THREAD_STATE<>'Running',500"                           ''')
    print('''  -ns 1 -cs "SELECT * from SYS.M_DEV_TRANSACTIONS_HISTORY_ WHERE PORT = '31003' AND START_TIME >= ADD_SECONDS (CURRENT_TIMESTAMP, -14400)"      ''')
    print("                                                                                                                                                    ")
    print("EXAMPLE (If the average execution time changes more than 6 percent after an engine change (where both engine possibilities were executed more than  ")
    print("         5 times there will be printouts from the SQL plan cache ±5 hours around the engine changes, and an email will be send)                     ")
    print("  > python hanasitter.py -sc 6 -scc 5 -scp 5 -en christian.hansen01@sap.com -k T1KEY                                                                ")
    print("                                                                                                                                                    ")
    print("EXAMPLE (if there is any user with more threads than 5, then record a call stack)                                                                   ")
    print('  > python hanasitter.py -k T1KEY -cf "M_SERVICE_THREADS,WHERE,USER_NAME <> '' group by USER_NAME,5" -nc 1                                          ')
    print("                                                                                                                                                    ")
    print("CURRENT KNOWN LIMITATIONS (i.e. TODO LIST):                                                                                                         ")
    print(" 1. Record in parallel for different Scale-Out Nodes   (should work for some recording types, e.g. RTE dumps -->  TODO)                             ")
    print(" 2. If a CPU only happens on one Host, possible to record on only one Host --> not possible to do this with SAR                                     ")                                   
    print(" 4. Let HANASitter first check that there is no other hanasitter process running --> refuse to run --> TODO  (but can be done with cron, see slides)")
    print(" 5. Read config file, -ff, after hanasitter slept, so that it will allow dynamic changes                                                            ")
    print(" 6. Make the PING check specific for HOSTS (and only record for that host) --> not possible! Could be done hint ROUTE_TO(<volume_id_1>, ...)        ")
    print("              BUT to get the volume_id I must read M_VOLUMES with SQL and to rely on SQL before the PING check destroys the purpose of this check   ")
    print(" 7. Force -ks prior to data collection for certain critical features                                                                                ")
    print(" 8. Average of CPU checks                                                                                                                           ")
    print(" 9. Add flags with possible sentences to add in the email messages  ... different flags for different checks ...                                    ")
    print("                                                                                                                                                    ")
    print("AUTHOR: Christian Hansen                                                                                                                            ")
    print("                                                                                                                                                    ")
    print("                                                                                                                                                    ")
    os._exit(1)
    
def printDisclaimer():
    print("                                                                                                                                  ")    
    print("ANY USAGE OF HANASITTER ASSUMES THAT YOU HAVE UNDERSTOOD AND AGREED THAT:                                                         ")
    print(" 1. HANASitter is NOT SAP official software! NO support of HANASitter can be assumed!                                             ")
    print(" 2. HANASitter is open source                                                                                                     ") 
    print(' 3. HANASitter is provided "as is"                                                                                                ')
    print(' 4. HANASitter is to be used on "your own risk"                                                                                   ')
    print(" 5. HANASitter is a one-man's hobby (developed, maintained and supported only during non-working hours)                           ")
    print(" 6  All HANASitter documentations have to be read and understood before any usage:                                                ")
    print("     a) The .pdf file that can be downloaded from https://github.com/chriselswede/hanasitter                                      ")
    print("     b) All output from executing                                                                                                 ")
    print("                     python hanasitter.py --help                                                                                  ")
    print(" 7. HANASitter can help you to automize certain monitoring tasks but is NOT an attempt to teach you how to monitor SAP HANA       ")
    print("    I.e. if you do not know what you want to do, HANASitter cannot help, but if you do know, HANASitter can maybe automitize it   ")
    print(" 8. HANASitter is not providing any recommendations, all flags shown in the documentation (see point 6.) are only examples        ")
    os._exit(1)

############ GLOBAL VARIABLES ##############
emailNotification = None

######################## DEFINE CLASSES ##################################
class RTESetting:
    def __init__(self, num_rtedumps, rtedumps_interval, profile_for_section_restriction):
        self.num_rtedumps = num_rtedumps
        self.rtedumps_interval = rtedumps_interval
        self.profile = profile_for_section_restriction
        
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

class CustomSQLSetting:
    def __init__(self, num_custom_sql_recordings, custom_sql_interval, custom_sql_recording):
        self.num_custom_sql_recordings = num_custom_sql_recordings
        self.custom_sql_interval = custom_sql_interval
        self.custom_sql_recording = custom_sql_recording

class CustomQuerySetting:
    def __init__(self, custom_queries, custom_query_waits):
        self.custom_queries = custom_queries
        self.custom_query_waits = custom_query_waits

class EmailNotification:
    def __init__(self, receiverEmails, emailClient, senderEmail, mailServer, SID):
        self.senderEmail = senderEmail
        self.emailClient = emailClient
        self.receiverEmails = receiverEmails
        self.mailServer = mailServer
        self.SID = SID
    def printEmailNotification(self):
        print("Email Client: ", self.emailClient)
        if self.senderEmail:
            print("Sender Email: ", self.senderEmail)
        else:
            print("Configured sender email will be used.")
        if self.mailServer:
            print("Mail Server: ", self.mailServer)
        else:
            print("Configured mail server will be used.")
        print("Reciever Emails: ", self.recieverEmails)

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
            print("ERROR, something went wrong, indexserver port is not according to the rules; "+str(self.indexserverPort))
            os._exit(1)
    def printTenant(self):
        print("TenantDB: ", self.DBName, " Indexserver Port: ", self.indexserverPort, " Sql Port: ", self.sqlPort)
    def getIndexserverPortString(self):
        return str(self.indexserverPort)
        
class HdbconsManager:
    def __init__(self, local_host, used_hosts, local_dbinstance, is_tenant, communicationPort, SID, rte_mode, tenantDBName = None, shell = '/bin/bash'):
        self.local_host = local_host
        self.used_hosts = used_hosts
        self.local_dbinstance = local_dbinstance
        self.is_tenant = is_tenant
        self.communicationPort = communicationPort
        self.SID = SID
        self.rte_mode = rte_mode
        self.tenantDBName = tenantDBName
        self.shell = shell
        self.hostsForRecording = used_hosts # at first assume all, also true unless host_mode 
        # Below lists must have the same length, since they will get zipped
        self.hdbcons_hosts = []
        self.hdbcons_ports = []
        self.hdbcons_services = []
        self.hdbcons_strings = []
        self.hdbcons_temp_output_dirs = []
    def create_hdbcons_string(self, host, port, service):
        self.hdbcons_hosts.append(host)
        self.hdbcons_ports.append(port)
        self.hdbcons_services.append(service)                  # SAP Notes 2222218 and 2410143
        self.hdbcons_strings.append('hdbcons -e hdbnameserver "distribute exec '+host+':'+port+' ')  # we need this in case of scale-out, to reach other hosts, but for scale_up, see below 
    def create_hdbcons_string_scale_up(self, host, port, service):
        self.hdbcons_hosts.append(host)
        self.hdbcons_ports.append(port)
        self.hdbcons_services.append(service)                  # SAP Note 2222218
        if self.tenantDBName:
            self.hdbcons_strings.append('hdbcons -e hdb'+service+' -d '+self.tenantDBName+' "')
        elif not self.is_tenant:
            self.hdbcons_strings.append('hdbcons -e hdbnameserver "')  #hdbcons developers: "in case of a problem it is more likely to get useful results by connecting directly"
        else:
            self.hdbcons_strings.append('hdbcons "')   #hdbcons developers: "in case of a problem it is more likely to get useful results by connecting directly" (default is indexserver)
    def print_service_host_ports(self):
        print("Services to record from:")
        print("Host:                         Service:                      Port:                         Host:Port")
        for host, service, port in zip(self.hdbcons_hosts, self.hdbcons_services, self.hdbcons_ports):
            print(host+' '*(30-len(host)) + service+' '*(30-len(service)) + port+' '*(30-len(port)) + host+":"+port+' '*(30-len(host+":"+port)))
    def create_temp_output_directories(self, host_check): # CREATE TEMPORARY OUTPUT DIRECTORIES and SET PRIVILEGES (CHMOD) only if we write kernel profiler
        cdtrace_path_local = cdalias('cdtrace', self.local_dbinstance, self.shell)
        if not self.local_host in cdtrace_path_local:
            if host_check:
                print("ERROR, local host, ", self.local_host, ", is not part of cdtrace, ", cdtrace_path_local)
                os._exit(1)
            else:
                print("WARNING, local host: ", self.local_host, ", should be part of cdtrace: ", cdtrace_path_local, ". It is not. Continue at your own risk!")
        for hdbcons_host, hdbcons_port, hdbcons_service in zip(self.hdbcons_hosts, self.hdbcons_ports, self.hdbcons_services):
            if len(self.local_host.split('.')) > 1:
                replace_host = hdbcons_host
            else:
                replace_host = hdbcons_host.split('.')[0]
            self.hdbcons_temp_output_dirs.append(cdtrace_path_local.replace(self.local_host, replace_host)+"_"+hdbcons_port+"_"+hdbcons_service+"_hanasitter_temp_out_"+datetime.now().strftime("%Y-%m-%d")+"/")
        for path in self.hdbcons_temp_output_dirs:
            if not os.path.exists(path):
                dummyout = run_command("mkdir "+path)
            dummyout = run_command("chmod 777 "+path)
    def clear(self):
        for path in self.hdbcons_temp_output_dirs:
            if os.path.isdir(path):
                dummout = run_command("rm -r "+path)
        
class CommunicationManager:
    def __init__(self, dbuserkey, out_dir, log_dir, std_out, hdbsql_string, log_features, out_run_command):
        self.dbuserkey = dbuserkey
        self.out_dir = out_dir
        self.log_dir = log_dir
        self.std_out = std_out
        self.hdbsql_string = hdbsql_string
        self.log_features = log_features
        self.out_run_command = out_run_command
        
class CriticalFeature:
    def __init__(self, view, feature, value, limit, killSession = '0'):
        self.text = ""
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
            if self.view == 'M_ACTIVE_STATEMENTS':              # to avoid finding itself:
                self.whereClause += " and STATEMENT_STRING not like '%M_ACTIVE_STATEMENTS%'"   
        self.value = value
        self.limitIsMinimumNumberCFAllowed = (limit[0] == '>') # so default and < then maximum number CF allowed 
        if limit[0] in ['<', '>']:
            limit = limit[1:]
        if not is_integer(limit):
            print("INPUT ERROR: 4th item of -cf must be either an integer or an integer preceded by < or >. Please see --help for more information.")
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
    def setText(self, text):
        self.text = text

class HashCache:
    def __init__(self, hash, engines, avg_exec_ms, exec_count, tot_exec_minutes, max_snp_time, only_negative_changes):
        self.hash = hash
        self.engines = [engines]
        self.avg_exec_ms = [avg_exec_ms]
        self.diff_avg_exec_pct = [0.0]
        self.exec_count = [exec_count]
        self.tot_exec_time_minutes = [tot_exec_minutes]
        self.max_snp_time = [max_snp_time]
        self.only_negative_changes = only_negative_changes
    def add_a_hashcache(self, engines, avg_exec_ms, exec_count, tot_exec_minutes, max_snp_time):
        self.engines.append(engines)
        self.avg_exec_ms.append(avg_exec_ms)
        self.diff_avg_exec_pct.append(0.0)
        self.exec_count.append(exec_count)
        self.tot_exec_time_minutes.append(tot_exec_minutes)
        self.max_snp_time.append(max_snp_time)
        self.update_diff()
    def max_diff_avg_exec_pct(self):
        return max(self.diff_avg_exec_pct)
    def update_diff(self):
        min_exec_time = min(self.avg_exec_ms)
        index_min = min(range(len(self.avg_exec_ms)), key=self.avg_exec_ms.__getitem__)
        for i in range(len(self.avg_exec_ms)):
            diff_avg_exec_pct = round((self.avg_exec_ms[i] - min_exec_time)/self.avg_exec_ms[i]*100, 1)
            if self.only_negative_changes and self.max_snp_time[i] < self.max_snp_time[index_min]:
                diff_avg_exec_pct = 0
            self.diff_avg_exec_pct[i] = diff_avg_exec_pct
    def getLists(self):
        lists = []
        for i in range(len(self.engines)):
            lists.append([self.hash, self.engines[i], self.avg_exec_ms[i], self.diff_avg_exec_pct[i], self.exec_count[i], self.tot_exec_time_minutes[i], self.max_snp_time[i]])
        return lists
    def printHashCache(self):
        for i in range(len(self.engines)):
            print("Hash: ", self.hash, "  Engines: ", self.engines[i], "  Average Execution Time [ms]: ", self.avg_exec_ms[i], "  Diff of Avg Exec Time [%]: ", self.diff_avg_exec_pct[i], "  Execution Count:", self.exec_count[i], "   Total Execution Time [m]", self.tot_exec_time_minutes[i], "  Max snapshot time: ", self.max_snp_time[i])
        
class SCCManager:
    def __init__(self, min_avg_exec_time_diff_pct, plan_id_changes, min_exec_counts, min_tot_exec_time_minutes, h_print_engine_changes, only_negative_changes, sql_text_len, app_source_len, nbrDaysToTakeIntoAcount, nbrDaysToTakeIntoAcountForStat):
        self.min_avg_exec_time_diff_pct = min_avg_exec_time_diff_pct
        self.plan_id_changes = plan_id_changes
        self.min_exec_counts = min_exec_counts
        self.min_tot_exec_time_minutes = min_tot_exec_time_minutes
        self.h_print_engine_changes = h_print_engine_changes
        self.only_negative_changes = only_negative_changes
        self.sql_text_len = sql_text_len
        self.app_source_len = app_source_len
        self.nbrDaysToTakeIntoAcount = nbrDaysToTakeIntoAcount
        self.nbrDaysToTakeIntoAcountForStat = nbrDaysToTakeIntoAcountForStat

######################## DEFINE FUNCTIONS ################################

def run_command(cmd, out_run_command = False):
    if sys.version_info[0] == 2:
        if out_run_command:
            print("Will execute  subprocess.check_output(cmd, shell=True)  where cmd = \n", cmd)   
        out = subprocess.check_output(cmd, shell=True).strip("\n")
    elif sys.version_info[0] == 3:
        if out_run_command:
            print("Will execute  subprocess.run(cmd, shell=True, capture_output=True, text=True)  where cmd = \n", cmd)  
        out = subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip("\n") 
    else:
        print("ERROR: Wrong Python version")
        os._exit(1)
    return out

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
        print("INPUT ERROR: ", flagstring, " must be either 'true' or 'false'. Please see --help for more information.")
        os._exit(1)
    boolean = True if boolean == "true" else False
    return boolean

def checkIfAcceptedFlag(word):
    if not word in ["-h", "--help", "-d", "--disclaimer", "-ff", "-oi", "-pt", "-ci", "-rm", "-rp", "-hm", "-nr", "-ir", "-mr", "-pr", "-ns", "-is", "-cs", "-cq", "-iq", "-ks", "-nc", "-ic", "-ng", "-ig", "-np", "-ip", "-dp", "-wp", "-cf", "-ct", "-cd", "-if", "-tf", "-ar", "-sv", "-svp", "-od", "-odr", "-ol", "-olr", "-oc", "-sc", "-spi", "-scc", "-sct", "-scp", "-scn", "-scx", "-scpa", "-scd", "-scs", "-lf", "-en", "-enc", "-ens", "-enm", "-so", "-or", "-ssl", "-encr", "-sslk", "-sslt", "-sslp", "-ssln", "-vlh", "-hc", "-hi", "-sh", "-hev", "-k", "-cpu"]:
        print("INPUT ERROR: ", word, " is not one of the accepted input flags. Please see --help for more information.")
        os._exit(1)

def is_online(dbinstance, comman): #Checks if all services are GREEN and if there exists an indexserver (if not this is a Stand-By)         
    process = subprocess.Popen(['sapcontrol', '-nr', dbinstance, '-function', 'GetProcessList'], stdout=subprocess.PIPE)
    out, err = process.communicate()
    out = out.decode()
    number_services = out.count(" HDB ") + out.count(" Local Secure Store")   
    number_running_services = out.count("GREEN")
    number_indexservers = int(out.count("hdbindexserver")) # if not indexserver this is Stand-By
    test_ok = (str(err) == "None")
    result = (number_running_services == number_services) and (number_indexservers != 0)
    printout = "Online Check      , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    ,     -            , "+str(test_ok)+"         , "+str(result)+"       , # index services: "+str(number_indexservers)+", # running services: "+str(number_running_services)+" out of "+str(number_services)
    log(printout, comman)
    return result

def print_table(header_list, values_lists):
    values_lists_strings = []
    for vl in values_lists:  
        values_lists_strings.append(list(map(str, vl)))
    lengths = [len(header) for header in header_list]
    for vl in values_lists_strings:
        lengths = [max(lle, len(vle)) for lle, vle in zip(lengths, vl)]
    row_format = ""
    for length in lengths:
        row_format = row_format + "{:<"+str(length+2)+"}"
    string_out = row_format.format(*header_list)+"\n"
    for row in values_lists_strings:
        string_out += row_format.format(*row)+"\n"
    return string_out
    
def is_secondary(comman):
    process = subprocess.Popen(['hdbnsutil', '-sr_state'], stdout=subprocess.PIPE)
    out, err = process.communicate()
    out = out.decode()
    test_ok = (str(err) == "None")
    result = "active primary site" in out   # then it is secondary!
    printout = "Primary Check     , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    ,     -            , "+str(test_ok)+"         , "+str(not result)+"       , " 
    log(printout, comman)
    return result 

def is_multitenant_database_container(local_dbinstance, shell):
    is_mdc = False
    global_ini = cdalias('cdcoc', local_dbinstance, shell)+"/global.ini"
    with open(global_ini) as gf:
        is_mdc = 'mode = multidb' in gf.read()
    return is_mdc

def ping_db(comman, output):
    with open(os.devnull, 'w') as devnull:  # just to get no stdout in case HANA is offline
        try:
            output[0] = run_command(comman.hdbsql_string+''' -j -A -U '''+comman.dbuserkey+''' "select * from dummy"''', comman.out_run_command) #this might be a problem ... from https://docs.python.org/3/library/subprocess.html#subprocess.getoutput : 
            #The stdout and stderr arguments may not be supplied at the same time as capture_output. If you wish to capture and combine both streams into one, use stdout=PIPE and stderr=STDOUT instead of capture_output.
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
            print("ERROR, it cannot be both pinged and hanging")
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
    prios = {1:"RTE", 2:"Call Stacks", 3:"G-Stacks", 4:"Kernel Profiler", 5:"Custom SELECT Output", 6:"Custom Queries"}
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

def clean_outputs(minRetainedOutputDays, comman):
    path = comman.out_dir
    nFilesBefore = len([name for name in os.listdir(path)])
    dummyout = run_command("find "+path+"/* -mtime +"+str(minRetainedOutputDays)+" -delete", comman.out_run_command)
    nFilesAfter = len([name for name in os.listdir(path)])
    return nFilesBefore - nFilesAfter 

def clean_logs(minRetainedLogDays, comman):
    path = comman.log_dir
    nFilesBefore = len([name for name in os.listdir(path) if "hanasitterlog" in name])
    dummyout = run_command("find "+path+"/hanasitterlog* -mtime +"+str(minRetainedLogDays)+" -delete", comman.out_run_command)
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
            if not line[0] == '#':  #starting with SPS08 there are strange comments lines in the daemon.ini file, lets ignore those lines
                if not foundNewName and "[indexserver." in line:
                    tenantDBNames.append(line.strip("[indexserver.").strip("\n").strip("]"))
                    foundNewName = True
                elif foundNewName and not foundFirstPortHalf and "arguments = -port " in line:
                    ports_first_halfs.append(line.strip("arguments = -port ").split("$")[0])
                    foundFirstPortHalf = True
                elif foundNewName and not foundInstanceIds and "instanceids = " in line:
                    ports_second_halfs.append(line.strip("instanceids = ").strip("\n"))
                    foundInstanceIds = True
                elif foundNewName and not line.strip("\n"):  # the order of instance ids and arguments are different in SPS03 and SPS04
                    if foundFirstPortHalf and foundInstanceIds:
                        foundNewName = False
                        foundFirstPortHalf = False
                        foundInstanceIds = False
                    else:
                        print("ERROR, something went wrong while reading the daemon.ini file")
                        os._exit(1)
        tenantIndexserverPorts = [first+second for first, second in zip(ports_first_halfs, ports_second_halfs)]
    return [tenantDBNames, tenantIndexserverPorts]

def getParameterFromFile(flag, flag_string, flag_value, flag_file, flag_log, parameter):
    if flag == flag_string:
        parameter = flag_value
        flag_log[flag_string] = [flag_value, flag_file]
    return parameter

def getParameterListFromFile(flag, flag_string, flag_value, flag_file, flag_log, parameter, delimeter = ','):
    if flag == flag_string:
        parameter = [x for x in flag_value.split(delimeter)]
        flag_log[flag_string] = [flag_value, flag_file]
    return parameter

def getParameterFromCommandLine(sysargv, flag_string, flag_log, parameter):
    if flag_string in sysargv:
        flag_value = sysargv[sysargv.index(flag_string) + 1]
        parameter = flag_value
        flag_log[flag_string] = [flag_value, "command line"]
    return parameter

def getParameterListFromCommandLine(sysargv, flag_string, flag_log, parameter, delimeter = ','):
    if flag_string in sysargv:
        parameter = [x for x in sysargv[  sysargv.index(flag_string) + 1   ].split(delimeter)]
        flag_log[flag_string] = [','.join(parameter), "command line"]
    return parameter

def get_host_folder(local_dbinstance, local_host, key_domain, shell):
    output = run_command('ls -l '+cdalias('cdhdb', local_dbinstance, shell)+local_host).splitlines(1)
    if not output and not key_domain:
        print("ERROR: The host folder was not found as \n"+cdalias('cdhdb', local_dbinstance, shell)+local_host+"\nIf that folder contains the domain on your system, then provide the domain in ENV in the Key.")
        os._exit(1)
    elif not output:
        output = run_command('ls -l '+cdalias('cdhdb', local_dbinstance, shell)+local_host+'.'+key_domain).splitlines(1)
        if not output:
            print("ERROR: The host folder was not found neither as \n"+cdalias('cdhdb', local_dbinstance, shell)+local_host+"\n nor as \n"+cdalias('cdhdb', local_dbinstance, shell)+local_host+'.'+key_domain+"\nCheck your key")
            os._exit(1)
        else:
            return cdalias('cdhdb', local_dbinstance, shell)+local_host+'.'+key_domain
    return cdalias('cdhdb', local_dbinstance, shell)+local_host

def cpu_too_high(cpu_check_params, comman):
    any_cpu_too_high = False
    input_cpu_type = int(cpu_check_params[0])
    if input_cpu_type == 0 or int(cpu_check_params[1]) == 0 or int(cpu_check_params[3]) == 100: # if CPU type is 0 or if number CPU checks is 0 or allowed CPU is 100 then no CPU check
        return False
    for cpu_type in [1,2]:
        if cpu_type == input_cpu_type or input_cpu_type == 3:
            start_time = datetime.now()
            command_run = run_command("sar -u "+cpu_check_params[1]+" "+cpu_check_params[2], comman.out_run_command)
            sar_words = command_run.split()
            cpu_column = 2 if cpu_type == 1 else 4 
            current_cpu = sar_words[sar_words.index('Average:') + cpu_column]
            if not is_number(current_cpu):
                print("ERROR, something went wrong while using sar. Output = ")
                print(command_run)
                os._exit(1)
            too_high_cpu = float(current_cpu) > int(cpu_check_params[3])
            if too_high_cpu:
                any_cpu_too_high = True
            stop_time = datetime.now()
            cpu_string = "User CPU Check  " if cpu_type == 1 else "System CPU Check"
            printout = cpu_string+"  , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         , "+str(not too_high_cpu)+"       , Av. CPU = "+current_cpu+" % (Allowed = "+cpu_check_params[3]+" %) "
            log(printout, comman, sendEmail = too_high_cpu)
    return any_cpu_too_high

def stop_session(cf, comman):
    how_to_kill = 'CANCEL' if cf.killSession == 'C' else 'DISCONNECT'    
    connExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitor_columns where VIEW_COLUMN_NAME = 'CONNECTION_ID' and VIEW_NAME = '"+cf.view+"'\"", comman.out_run_command).strip(' '))
    if connExists:
        connIds = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "select distinct CONNECTION_ID from SYS.'+cf.view+' where '+cf.whereClause+'"', comman.out_run_command).splitlines(1)
        connIds = [c.strip('\n').strip('|').strip(' ') for c in connIds]
        for connId in connIds:
            connExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \" select count(*) from sys.m_connections where CONNECTION_ID = '"+connId+"'\"", comman.out_run_command).strip(' '))
            if not connExists:
                log("Connection "+connId+" was already disconnected before HANASitter got to it", comman)
            else:
                log("Will "+how_to_kill+" session "+connId+" due to the check: "+cf.whereClauseDescription, comman)
                try:
                    dummyout = run_command(comman.hdbsql_string+""" -j -A -U """+comman.dbuserkey+""" "ALTER SYSTEM """+how_to_kill+""" SESSION '"""+connId+"""'" """, comman.out_run_command)
                    connExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \" select count(*) from sys.m_connections where CONNECTION_ID = '"+connId+"'\"", comman.out_run_command).strip(' '))
                    if connExists:
                        log("WARNING, statement \n    ALTER SYSTEM "+how_to_kill+" SESSION '"+connId+"'\nwas executed but the connection "+connId+" is still there. It might take some time until it actually disconnects.", comman)
                    else:
                        log("Succesfully disconnected session "+connId, comman)
                except:
                    log("Session "+connId+" got disconnected by itself before HANASitter tried", comman)
    else:
        log("WARNING, the view in the Critical Feature has no CONNECTION_ID column, so the session for this Critical Feature cannot be killed", comman)
            
        

def feature_check(cf, nbrCFsPerHost, critical_feature_info, host_mode, comman):   # cf = critical_feature, # comman = communication manager
    #CHECKS
    viewExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitors where view_name = '"+cf.view+"'\"", comman.out_run_command).strip(' '))
    if not viewExists:
        log("INPUT ERROR, the view given as first entry in the -cf flag, "+cf.view+", does not exist. Please see --help for more information.", comman)
        os._exit(1)
    if not cf.whereMode:
        columnExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitor_columns where view_name = '"+cf.view+"' and view_column_name = '"+cf.feature+"'\"", comman.out_run_command).strip(' ')) 
        if not columnExists:
            log("INPUT ERROR, the view "+cf.view+" does not have the column "+cf.feature+". Please see --help for more information.", comman)
            os._exit(1)
    if host_mode:
        hostColumnExists = int(run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select count(*) from sys.m_monitor_columns where view_name = '"+cf.view+"' and view_column_name = 'HOST'\"", comman.out_run_command).strip(' ')) 
        if not hostColumnExists:
            log("INPUT ERROR, you have specified host mode with -hf, but the view "+cf.view+" does not have a HOST column. Please see --help for more information.", comman)
            os._exit(1)         
    nbrCFSum = {}
    for iteration in range(cf.nbrIterations):
        # EXECUTE
        nCFsPerHost = []
        if host_mode:
            hostsInView = run_command(comman.hdbsql_string+" -j -A -a -x -Q -U "+comman.dbuserkey+" \"select distinct HOST from SYS."+cf.view+"\"", comman.out_run_command).strip(' ').split('\n')
            hostsInView = [h for h in hostsInView if h != ''] 
            for host in hostsInView:
                nCFsPerHost.append([int(run_command(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select count(*) from SYS.'+cf.view+' where '+cf.whereClause+' and HOST = \''+host+'\'"', comman.out_run_command).split('|')[5].replace(" ", "")), host])
        else:                
            nCFsPerHost.append([int(run_command(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select count(*) from SYS.'+cf.view+' where '+cf.whereClause+'"', comman.out_run_command).split('|')[5].replace(" ", "")), ''])
        # COLLECT INFO
        if comman.log_features:  #already prevented that log features (-lf) and host mode (-hm) is not used together
            critical_feature_info[0] = run_command(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "select * from SYS.'+cf.view+' where '+cf.whereClause+'"', comman.out_run_command)
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

def sqlCacheCheck(sccmanager, comman):
    start_time = datetime.now()
    if sccmanager.plan_id_changes:
        change_type = 'PLAN_ID'
        change_type_description = 'plan id changes'
        change_title = 'Plan ID'
    else:
        change_type = 'EXECUTION_ENGINE'
        change_type_description = 'engine changes'
        change_title = 'Engines'
    oldestDayToTakeIntoAccount = datetime.now() + timedelta(days = -int(sccmanager.nbrDaysToTakeIntoAcount))
    oldestDayToTakeIntoAccountForStat = datetime.now() + timedelta(days = -int(sccmanager.nbrDaysToTakeIntoAcountForStat))
    hashes_with_engine_change = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "select STATEMENT_HASH from (select STATEMENT_HASH, '+change_type+' from _SYS_STATISTICS.HOST_SQL_PLAN_CACHE where SERVER_TIMESTAMP > \''+oldestDayToTakeIntoAccount.strftime('%Y-%m-%d')+' 00:00:00\' group by STATEMENT_HASH, '+change_type+' order by STATEMENT_HASH) group by STATEMENT_HASH having count(*) > 1"').splitlines(1)
    nbr_hashes_with_engine_change = len(hashes_with_engine_change)
    if nbr_hashes_with_engine_change > 0:
        hashes_with_engine_change = [hash.strip('\n').strip('|').strip(' ') for hash in hashes_with_engine_change]
        hashes_with_engine_change = "', '".join(hashes_with_engine_change)
        select_string = "select MAX(RPAD(TO_VARCHAR(SERVER_TIMESTAMP, 'YYYY/MM/DD HH24:MI:SS'), 20)) MAX_SNP_TIME, STATEMENT_HASH HASH,  LPAD(TO_DECIMAL(SUM(TOTAL_EXECUTION_TIME)/SUM(EXECUTION_COUNT)/1000, 10, 2), 11) AVG_EXEC_MS, LPAD(SUM(EXECUTION_COUNT), 11) EXEC_COUNT, "+change_type+", LPAD(TO_DECIMAL(SUM(TOTAL_EXECUTION_TIME)/1000/1000/60, 10, 0), 11) TOT_EXEC_MINUTES from _SYS_STATISTICS.HOST_SQL_PLAN_CACHE where SERVER_TIMESTAMP > '"+oldestDayToTakeIntoAccountForStat.strftime('%Y-%m-%d')+" 00:00:00' and STATEMENT_HASH in ('"+hashes_with_engine_change+"') group by STATEMENT_HASH, "+change_type+" order by STATEMENT_HASH"
        output_table = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "'+select_string+'"', comman.out_run_command).splitlines(1)
        HashCaches = {}
        for table_row in output_table:
            table_row = table_row.strip('\n').strip('|').split('|')
            hash = table_row[1].strip(' ')
            avg_exec_ms = table_row[2].strip(' ')
            if not is_number(avg_exec_ms):
                print("ERROR, something went wrong while getting execution time, avg_exec_ms is not a number: ", avg_exec_ms)
                os._exit(1)
            avg_exec_ms = float(avg_exec_ms)
            engines = table_row[4].strip(' ')
            max_snp_time = table_row[0].strip(' ')
            exec_count = table_row[3].strip(' ')
            tot_exec_minutes = table_row[5].strip(' ')
            if int(exec_count) >= sccmanager.min_exec_counts and int(tot_exec_minutes) >= sccmanager.min_tot_exec_time_minutes:
                if hash in HashCaches:
                    HashCaches[hash].add_a_hashcache(engines, avg_exec_ms, exec_count, tot_exec_minutes, max_snp_time)
                else:
                    HashCaches[hash] = HashCache(hash, engines, avg_exec_ms, exec_count, tot_exec_minutes, max_snp_time, sccmanager.only_negative_changes)
        hasches_to_delete = [hash for hash in HashCaches if HashCaches[hash].max_diff_avg_exec_pct() < sccmanager.min_avg_exec_time_diff_pct] #not of interest
        for hash in hasches_to_delete:
            del HashCaches[hash]
        hash_header_list = ["Hash", change_title, "Avg Exec Time [ms]", "Diff Avg Exec Time [%]", "Execution Count", "Total Exec Time [m]", "Max snapshot time"]
        hash_values_lists = []
        for h,hc in HashCaches.items():
            hash_values_lists.extend(hc.getLists())
        nbr_hashes_with_critical_engine_change = len(HashCaches)
        if nbr_hashes_with_critical_engine_change > 0:
            table_printout = print_table(hash_header_list, hash_values_lists)
            if sccmanager.h_print_engine_changes:
                for h,hc in HashCaches.items():
                    for max_snp_time in hc.max_snp_time:
                        select_string = "select RPAD(TO_VARCHAR(SERVER_TIMESTAMP, 'YYYY/MM/DD HH24:MI:SS'), 20) SNP_TIME, STATEMENT_HASH HASH, LPAD(TO_DECIMAL(TOTAL_EXECUTION_TIME/EXECUTION_COUNT/1000, 10, 2), 11) AVG_EXEC_MS, LPAD(EXECUTION_COUNT, 11) EXEC_COUNT, "+change_type+" from _SYS_STATISTICS.HOST_SQL_PLAN_CACHE where SERVER_TIMESTAMP > '"+oldestDayToTakeIntoAccountForStat.strftime('%Y-%m-%d')+" 00:00:00' and STATEMENT_HASH = '"+h+"' and SERVER_TIMESTAMP > ADD_SECONDS(TO_TIMESTAMP('"+max_snp_time+"', 'YYYY/MM/DD HH24:MI:SS'), -"+str(sccmanager.h_print_engine_changes)+"*3600) and SERVER_TIMESTAMP < ADD_SECONDS(TO_TIMESTAMP('"+max_snp_time+"', 'YYYY/MM/DD HH24:MI:SS'), "+str(sccmanager.h_print_engine_changes)+"*3600)"
                        output_table = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "'+select_string+'"', comman.out_run_command).splitlines(1)
                        header_list = ["Max snapshot time", "Hash", "Avg Exec Time [ms]", "Execution Count", change_title]
                        sql_text = ''
                        if sccmanager.sql_text_len > 0:
                            select_string = "select top 1 LPAD(STATEMENT_STRING, "+str(sccmanager.sql_text_len)+") SQL_TEXT from _SYS_STATISTICS.HOST_SQL_PLAN_CACHE where STATEMENT_HASH = '"+h+"'"
                            sql_text = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "'+select_string+'"', comman.out_run_command).strip(' ').strip('|').strip(' ')
                        if sql_text: 
                            header_list.append("SQL Text")
                        app_source_name = ''
                        if sccmanager.app_source_len > 0:
                            select_string = "select top 1 LPAD(APPLICATION_SOURCE, "+str(sccmanager.app_source_len)+") SQL_TEXT from _SYS_STATISTICS.HOST_SQL_PLAN_CACHE where STATEMENT_HASH = '"+h+"'"
                            app_source_name = run_command(comman.hdbsql_string+' -j -A -a -x -U '+comman.dbuserkey+' "'+select_string+'"', comman.out_run_command).strip(' ').strip('|').strip(' ')
                        if app_source_name: 
                            header_list.append("App Source")
                        values_lists = []
                        for table_row in output_table:
                            table_row = table_row.strip('\n').strip('|').split('|')
                            table_row = [table_row[0].strip(' '), table_row[1].strip(' '), table_row[2].strip(' '), table_row[3].strip(' '), table_row[4].strip(' ')]
                            if sql_text:
                                table_row.append(sql_text)
                            if app_source_name:
                                table_row.append(app_source_name)
                            values_lists.append(table_row)
                        engine_change_at_least_once = any([values_lists[i][4] != values_lists[i+1][4] for i in range(len(values_lists) - 1)])
                        if engine_change_at_least_once: # if no engine change found here, nothing will be printed, then try increasing -scp
                            table_printout += "\n"+print_table(header_list, values_lists)
            stop_time = datetime.now()
            printout = "SQL Cache Check   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         , False      , There are hashes with potential critical "+change_type_description+" "
            log(printout+"\n\n"+table_printout, comman, sendEmail = True)
            return nbr_hashes_with_critical_engine_change
    stop_time = datetime.now()
    printout = "SQL Cache Check   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         , True       , There are no critical "+change_type_description+" "
    log(printout, comman)
    return 0
 
def record_gstack(gstacks_interval, comman):
    pid = run_command("pgrep hdbindexserver", comman.out_run_command).strip("\n").strip(" ")
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
    for hdbcons_string, hdbcons_host, hdbcons_service, hdbcons_port, hdbcons_tmp_dir in zip(hdbcons.hdbcons_strings, hdbcons.hdbcons_hosts, hdbcons.hdbcons_services, hdbcons.hdbcons_ports, hdbcons.hdbcons_temp_output_dirs): 
        if hdbcons_host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            filename_cpu = ("kernel_profiler_cpu_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".dot")
            filename_wait = ("kernel_profiler_wait_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".dot")
            filename_kprof_log = ("kernel_profiler_output_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".log")
            start_time = datetime.now()
            os.system(hdbcons_string+'profiler clear" > '+out_dir+filename_kprof_log)
            os.system(hdbcons_string+'profiler start -w '+str(kprofiler.kprofs_wait)+'" > '+out_dir+filename_kprof_log)
            time.sleep(kprofiler.kprofs_duration) 
            os.system(hdbcons_string+'profiler stop" > '+out_dir+filename_kprof_log)    
            os.system(hdbcons_string+'profiler print -o '+hdbcons_tmp_dir+filename_cpu+','+hdbcons_tmp_dir+filename_wait+'" > '+out_dir+filename_kprof_log)
            os.system(hdbcons_string+'profiler clear" > '+out_dir+filename_kprof_log) # added to avoid an entry in M_KERNEL_PROFILER 
            stop_time = datetime.now()
            if "[ERROR]" in open(out_dir+filename_kprof_log).read():
                printout = "Kernel Profiler   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , False        ,   None     , "+out_dir+filename_kprof_log
            else:
                os.system("mv "+hdbcons_tmp_dir+filename_cpu+" "+out_dir+filename_cpu)
                os.system("mv "+hdbcons_tmp_dir+filename_wait+" "+out_dir+filename_wait)
                printout = "Kernel Profiler   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         ,   -        , "+out_dir+filename_cpu+" and "+out_dir+filename_wait
            log(printout, comman)
            total_printout += printout
    time.sleep(kprofiler.kprofs_interval)
    return total_printout  

def record_callstack(callstacks_interval, hdbcons, comman):
    total_printout = ""
    for hdbcons_string, hdbcons_host, hdbcons_service, hdbcons_port in zip(hdbcons.hdbcons_strings, hdbcons.hdbcons_hosts, hdbcons.hdbcons_services, hdbcons.hdbcons_ports):
        if hdbcons_host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            filename = (comman.out_dir+"/callstack_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".txt")
            start_time = datetime.now()
            os.system(hdbcons_string+'context list -s" > '+filename)
            stop_time = datetime.now()
            printout = "Call Stack Record , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          ,   -        , "+filename 
            log(printout, comman)
            total_printout += printout
    time.sleep(callstacks_interval)
    return total_printout 
 
def record_rtedump(rtedumps_interval, profile_for_section_restriction, hdbcons, comman):
    total_printout = ""
    profile_string = ""
    if profile_for_section_restriction:
        profile_string = " -p "+profile_for_section_restriction
    for hdbcons_string, hdbcons_host, hdbcons_service, hdbcons_port in zip(hdbcons.hdbcons_strings, hdbcons.hdbcons_hosts, hdbcons.hdbcons_services, hdbcons.hdbcons_ports):
        if hdbcons_host in hdbcons.hostsForRecording:
            tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
            start_time = datetime.now()
            if hdbcons.rte_mode == 0: # normal rte dump
                filename = (comman.out_dir+"/rte_norm_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".trc")
                cmd = hdbcons_string+'runtimedump dump -c'+profile_string+'" > '+filename
                if comman.out_run_command:
                    print("Will execute  os.system(cmd)  where cmd = \n", cmd)   
                os.system(cmd)   # have to dump to std with -c and then to a file with >    since in case of scale-out  -f  does not work
            elif hdbcons.rte_mode == 1: # light rte dump 
                filename = (comman.out_dir+"/rtedump_light_"+hdbcons_host+"_"+hdbcons.SID+"_"+hdbcons_service+"_"+hdbcons_port+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".trc")
                os.system(hdbcons_string+'runtimedump dump -c -s STACK_SHORT,THREADS'+profile_string+'" > '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_JOBEXECUTORS_" >> '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_DEV_JOBEX_THREADGROUPS" >> '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_DEV_JOBEXWAITING" >> '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_DEV_CONTEXTS" >> '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_CONNECTIONS" >> '+filename)
                os.system(hdbcons_string+'statreg print -h -n M_DEV_SESSION_PARTITIONS" >> '+filename)
            stop_time = datetime.now()
            printout = "RTE Dump Record   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , True         ,   -        , "+filename   # if an [ERROR] happens that will be inside the file, hanasitter will not know it
            log(printout, comman)
            total_printout += printout
    time.sleep(rtedumps_interval)
    return total_printout 

def record_customsql(customsql, hdbcons, comman):   # for this record option -sv makes no sense since hdbcons is not used
    tenantDBString = hdbcons.tenantDBName+"_" if hdbcons.is_tenant else ""
    filename = comman.out_dir+"/custom_sql_"+hdbcons.SID+"_"+hdbcons.communicationPort+"_"+tenantDBString+datetime.now().strftime("%Y-%m-%d_%H-%M-%S")+".txt"
    customsql_output_file = open(filename, "a")
    start_time = datetime.now()
    customsql_output = run_command(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "'+customsql.custom_sql_recording+'"', comman.out_run_command)
    customsql_output_file.write(customsql_output)   
    customsql_output_file.flush()
    customsql_output_file.close()
    stop_time = datetime.now()
    printout = "Custom SQL Record , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          ,   -        , "+filename 
    log(printout, comman)
    time.sleep(customsql.custom_sql_interval)
    return printout 

def record_customquer(custom_query, custom_query_wait, comman):  # for this record option -sv makes no sense since hdbcons is not used
    start_time = datetime.now()
    customquer_output = run_command(comman.hdbsql_string+' -j -A -U '+comman.dbuserkey+' "'+custom_query+'"', comman.out_run_command)
    stop_time = datetime.now()
    printout = "Custom Query      , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   ,   -          ,   -        , "+custom_query+"   -->   Will now wait "+str(custom_query_wait)+" seconds"
    log(printout, comman)
    time.sleep(custom_query_wait)
    return printout 

def record(recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, hdbcons, comman):
    if recording_mode == 1:
        for p in recording_prio:
            if p == 1:
                for i in range(rte.num_rtedumps):
                    record_rtedump(rte.rtedumps_interval, rte.profile, hdbcons, comman)
            if p == 2:
                for i in range(callstack.num_callstacks):
                    record_callstack(callstack.callstacks_interval, hdbcons, comman) 
            if p == 3:
                for i in range(gstack.num_gstacks): 
                    record_gstack(gstack.gstacks_interval, comman)        
            if p == 4:                    
                for i in range(kprofiler.num_kprofs):    
                    record_kprof(kprofiler, hdbcons, comman)    
            if p == 5:                    
                for i in range(customsql.num_custom_sql_recordings):    
                    record_customsql(customsql, hdbcons, comman)
            if p == 6:
                for i in range(len(customquer.custom_queries)):
                    record_customquer(customquer.custom_queries[i], customquer.custom_query_waits[i], comman)    
    elif recording_mode == 2:  
        max_nbr_recordings = max(gstack.num_gstacks, kprofiler.num_kprofs, callstack.num_callstacks, rte.num_rtedumps, customsql.num_custom_sql_recordings, len(customquer.custom_queries))
        for i in range(max_nbr_recordings):
            for p in recording_prio:
                if p == 1:
                    if i < rte.num_rtedumps:
                        record_rtedump(rte.rtedumps_interval, rte.profile, hdbcons, comman)
                if p == 2:
                    if i < callstack.num_callstacks:
                        record_callstack(callstack.callstacks_interval, hdbcons, comman)
                if p == 3:
                    if i < gstack.num_gstacks:
                        record_gstack(gstack.gstacks_interval, comman)                 
                if p == 4:    
                    if i < kprofiler.num_kprofs:
                        record_kprof(kprofiler, hdbcons, comman)
                if p == 5:    
                    if i < customsql.num_custom_sql_recordings:
                        record_customsql(customsql, hdbcons, comman)
                if p == 6:    
                    if i < len(customquer.custom_queries):
                        record_customquer(customquer.custom_queries[i], customquer.custom_query_waits[i], comman)
    else: #for rm=3 customquer cannot be used since it has different statements
        record_in_parallel(rte, callstack, gstack, kprofiler, customsql, hdbcons, comman)
    return True

def record_in_parallel(rte, callstack, gstack, kprofiler, customsql, hdbcons, comman):    
    max_nbr_recordings = max(gstack.num_gstacks, kprofiler.num_kprofs, callstack.num_callstacks, rte.num_rtedumps, customsql.num_custom_sql_recordings)
    for i in range(max_nbr_recordings):    
        nbr_recording_types = sum(x > i for x in [rte.num_rtedumps, callstack.num_callstacks, gstack.num_gstacks, kprofiler.num_kprofs, customsql.num_custom_sql_recordings])
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
        if customsql.num_custom_sql_recordings > i:
            rec_types.append((5, customsql, hdbcons, comman))   # 5 = Custom SELECT Output
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
        return record_rtedump(recorder.rtedumps_interval, recorder.profile, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command))
    elif record_type == 2:
        return record_callstack(recorder.callstacks_interval, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command))
    elif record_type == 3:
        return record_gstack(recorder.gstacks_interval, CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command))
    elif record_type == 4:
        return record_kprof(recorder, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command))
    else:
        return record_customsql(recorder, hdbcons, CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command))

def tracker(ping_timeout, check_interval, recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, critical_features, feature_check_timeout, cpu_check_params, sccmanager, minRetainedLogDays, minRetainedOutputDays, host_mode, local_dbinstance, comman, hdbcons):   
    recorded = False
    offline = False
    hanging = False
    while not recorded:
        # Host online check
        if not is_online(local_dbinstance, comman):
            comment = "HOST is offline, will exit the tracker without recording"
            return [False, False]
        # CPU CHECK
        if cpu_too_high(cpu_check_params, comman): #first check CPU with 'sar' (i.e. without contacting HANA) if it is too high, record without pinging or feature checking
            recorded = record(recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, hdbcons, comman)
        if not recorded:
            if ping_timeout != 0:   # possible to turn off PING check with -pt 0
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
                    recorded = record(recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, hdbcons, comman)
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
                            info_message = "# CFs = "+str(nCFs)+" "+host+", "+cf.cfInfo
                            if wrong_number_critical_features and cf.text:
                                info_message = info_message + "\n" + cf.text
                            printout = "Feature Check "+str(chid)+"   , "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+"    , "+str(stop_time-start_time)+"   , "+str(not hanging)+"         , "+str(not wrong_number_critical_features)+"       , "+info_message
                            log(printout, comman, sendEmail = wrong_number_critical_features)
                            if wrong_number_critical_features:
                                hostsWithWrongNbrCFs.append(host)
                    if comman.log_features:
                        log(critical_feature_info[0], CommunicationManager(comman.dbuserkey, comman.out_dir, comman.log_dir, False, comman.hdbsql_string, comman.log_features, comman.out_run_command), "criticalFeatures")
                    if hanging or len(hostsWithWrongNbrCFs):
                        if host_mode:
                            hdbcons.hostsForRecording = hostsWithWrongNbrCFs
                        recorded = record(recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, hdbcons, comman)
                        if cf.killSession != '0':
                            stop_session(cf, comman)
        if not recorded:
        # SQL CACHE ENGINE CHANGE Test - only done if recording has not already been done from either the CPU check, Ping check or Feature Check
            if sccmanager.min_avg_exec_time_diff_pct >= 0:
                nbr_hashes_with_critical_engine_change = sqlCacheCheck(sccmanager, comman)
                if nbr_hashes_with_critical_engine_change > 0:
                    recorded = record(recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, hdbcons, comman)
        if not recorded:
            if check_interval == 0:
                log("HANASitter did not find any reason to record. Will now exit tracker since -ci = 0", comman, sendEmail = hanging or offline) 
                return [False, False]
            log("HANASitter did not find any reason to record. Will now sleep for "+str(check_interval)+" seconds (-ci)", comman, sendEmail = hanging or offline) 
            time.sleep(check_interval)
        #house keeping
        if minRetainedLogDays >= 0:   # automatic house keeping of hanasitter logs
            nCleaned = clean_logs(minRetainedLogDays, comman)
            log(str(nCleaned)+" hanasitter daily log files were removed", comman)
        if minRetainedOutputDays >= 0:   # automatic house keeping of hanasitter output files
            nCleaned = clean_outputs(minRetainedOutputDays, comman)
            log(str(nCleaned)+" hanasitter output files were removed", comman)
    return [recorded, offline]
            
def cdalias(alias, local_dbinstance, shell):   # alias e.g. cdtrace, cdhdb, ...
    #command_run = subprocess.check_output(['/bin/bash', '-i', '-c', "alias "+alias]).split("alias")[1]
    process = subprocess.Popen([shell, '-i', '-c', "alias "+alias], stdout=subprocess.PIPE)
    out, err = process.communicate()
    out = out.decode().split("alias")[1]
    pieces = out.strip("\n").strip(" "+alias+"=").strip("'").strip("cd ").split("/")
    path = ''
    for piece in pieces:
        if piece and piece[0] == '$':
            #piece = (subprocess.check_output(['/bin/bash', '-i', '-c', "echo "+piece])).strip("\n")
            echo = subprocess.Popen([shell, '-i', '-c', "echo "+piece], stdout=subprocess.PIPE)
            out, err = echo.communicate()
            piece = out.decode().strip("\n")
        path = path + '/' + piece + '/'
    path = path.replace("[0-9][0-9]", local_dbinstance) # if /bin/bash shows strange HDB[0-9][0-9] we force correct instance on it
    path = path.replace("executing .customer.sh.....\n", '')  #removing strange stuff 
    path = path.replace("DISPLAY set to localhost:10.0\n", '')  #removing strange stuff
    return path    
        
def log(message, comman, file_name = "", sendEmail = False):
    if comman.std_out:
        print(message)
    if file_name == "":
        file_name = "hanasitterlog"
    logfile = open(comman.log_dir+"/"+file_name+"_"+datetime.now().strftime("%Y-%m-%d"+".txt").replace(" ", "_"), "a")
    logfile.write(message+"\n")   
    logfile.flush()
    logfile.close()
    global emailNotification
    if sendEmail and emailNotification:  #sends email IF this call of log() wants it AND IF -en flag has been specified        
        message = 'Hi Team, \nAn odd event reported on the server. Here below are the details:\n'+message
        mailstring = 'echo "'+message+'" | '+emailNotification.emailClient+' -s "Message from HANASitter about '+emailNotification.SID+'" '
        if emailNotification.mailServer:
            mailstring += ' -S smtp=smtp://'+emailNotification.mailServer+' '
        if emailNotification.senderEmail:
            mailstring += ' -S from="'+emailNotification.senderEmail+'" '
        mailstring += ",".join(emailNotification.receiverEmails)
        output = run_command(mailstring, comman.out_run_command)

def getServiceHostPort(hdbconsservice, hdbconshost, tenantDBName, local_dbinstance, shell):
    # Must find port (communication port, not the SQL port) of service, to be used for hdbcons
    # Cannot use SQL to find the port (like in first suggestion of SAP Note 2410143) since HANA could be down --> find port based on trace files
    cdtrace_pathes = []
    cdtrace_pathes.append(cdalias('cdtrace', local_dbinstance, shell))
    if tenantDBName:
        cdtrace_pathes.append(cdtrace_pathes[0]+"/DB_"+tenantDBName)
    for tracepath in cdtrace_pathes:
        tracefile = run_command("ls "+tracepath+"/"+hdbconsservice+"_"+hdbconshost+".* | head -n 1 ")
        if tracefile:
            portnumber = tracefile.split(hdbconsservice+"_"+hdbconshost+".")[1].split(".")[0]
            if not portnumber == '00000': # sometimes nameserver can have strange trace files
                return portnumber
    return '-1'  # then did not succeed to find portnumber
    
def main():
    #####################  CHECK PYTHON VERSION ###########
    if sys.version_info[0] != 2 and sys.version_info[0] != 3:
        if sys.version_info[1] != 7:
            print("VERSION ERROR: hanasitter is only supported for Python 2.7.x (for HANA 2 SPS05 and lower) and for Python 3.7.x (for HANA 2 SPS06 and higher). Did you maybe forget to log in as <sid>adm before executing this?")
            os._exit(1)

    #####################   DEFAULTS   ####################
    online_test_interval = 3600 #seconds
    ping_timeout = 60 #seconds
    check_interval = 60 #seconds
    recording_mode = 1 # either 1, 2 or 3
    recording_prio = ['1', '2', '3', '4', '5', '6']   # 1=RTE, 2=CallStacks, 3=GStacks, 4=Kernel Profiler, 5=Custom SELECT Output, 6=Custom Query
    host_mode = "false"
    num_rtedumps = 0 #how many rtedumps?
    rtedumps_interval = 60 #seconds
    rte_mode = 0 # either 0 or 1 
    profile_for_section_restriction = ''
    num_custom_sql_recordings = 0  #how many custom sqls?
    custom_sql_interval = 60 #seconds
    custom_sql_recording = '' #custom sql dump
    custom_queries = [] # default: no custom queries
    custom_query_waits =  []
    num_callstacks = 0 #how many call stacks?
    callstacks_interval = 60 #seconds
    num_gstacks = 0  #how many call stacks?
    gstacks_interval = 60 #seconds
    num_kprofs = 0  #how many kernel profiler traces?
    kprofs_interval = 60 #seconds
    kprofs_duration = 60 #seconds
    kprofs_wait = 0 #milliseconds
    feature_check_timeout = 60 #seconds
    critical_features = [] # default: don't use critical feature check
    cf_texts = [] # default: no text
    kill_session = [] # default: do not kill any session
    intervals_of_features = [] #default only one check per feature
    after_recorded = -1 #default: exits after recorded
    hdbconsservices = []
    hdbconsservices_print = "false"
    std_out = "true" #print to std out
    out_run_command = "false" #print all run commands
    out_dir = "/tmp/hanasitter_out"
    log_dir = "/tmp/hanasitter_out"
    minRetainedOutputDays = -1 #automatic cleanup of hanasitter output files
    minRetainedLogDays = -1 #automatic cleanup of hanasitterlog
    out_config = "false"
    flag_files = []    #default: no configuration input file
    min_avg_exec_time_diff_pct = "-1"
    plan_id_changes = "false"
    min_exec_counts = "0"
    min_tot_exec_time_minutes = "0"
    h_print_engine_changes = "0"
    only_negative_changes = "false"
    sql_text_len = "0"
    app_source_len = "0"
    nbrDaysToTakeIntoAcount = "9999"
    nbrDaysToTakeIntoAcountForStat = "9999"
    log_features = "false"
    receiver_emails = None
    email_client = ''   #default email client, mailx, will be specifed later if -enc not provided
    senders_email = None
    mail_server = None
    ssl = "false"
    encryption = "false" 
    sslk = ''
    sslt = ''
    sslp = ''
    ssln = ''
    virtual_local_host = "" #default: assume physical local host
    host_check = "true"
    claim_high_isolation = "false"
    shell = "/bin/bash"
    hdbsql_env_variable = ''
    dbuserkey = 'SYSTEMKEY' # This KEY has to be maintained in hdbuserstore  
                            # so that   hdbuserstore LIST    gives e.g. 
                            # KEY SYSTEMKEY
                            #     ENV : mo-fc8d991e0:30015
                            #     USER: SYSTEM
    cpu_check_params = ['0', '0','0','100'] # by default no cpu check
    
    #####################  CHECK INPUT ARGUMENTS #################
    if len(sys.argv) == 1:
        print("INPUT ERROR: hanasitter needs input arguments. Please see --help for more information.")
        os._exit(1) 
    if len(sys.argv) != 2 and len(sys.argv) % 2 == 0:
        print("INPUT ERROR: Wrong number of input arguments. Please see --help for more information.")
        os._exit(1)
    for i in range(len(sys.argv)):
        if i % 2 != 0:
            if sys.argv[i][0] != '-':
                print("INPUT ERROR: Every second argument has to be a flag, i.e. start with -. Please see --help for more information.")
                os._exit(1)    
    
    
    #####################   PRIMARY INPUT ARGUMENTS   #################### 
    flag_log = {}    
    if '-h' in sys.argv or '--help' in sys.argv:
        printHelp()   
    if '-d' in sys.argv or '--disclaimer' in sys.argv:
        printDisclaimer() 
    flag_files = getParameterListFromCommandLine(sys.argv, '-ff', flag_log, flag_files)
    if flag_files:
        print("Make sure the configuration file only contains ascii characters!")
     
    ############ CONFIGURATION FILE ###################
    for flag_file in flag_files:
        with open(flag_file, 'r') as fin:
            for line in fin:
                firstWord = line.strip(' ').split(' ')[0]  
                if firstWord[0:1] == '-':
                    checkIfAcceptedFlag(firstWord)
                    flagValue = line.strip(' ').split('"')[1].strip('\n').strip('\r') if line.strip(' ').split(' ')[1][0] == '"' else line.strip(' ').split(' ')[1].strip('\n').strip('\r')
                    online_test_interval                = getParameterFromFile(firstWord, '-oi', flagValue, flag_file, flag_log, online_test_interval)
                    ping_timeout                        = getParameterFromFile(firstWord, '-pt', flagValue, flag_file, flag_log, ping_timeout)
                    check_interval                      = getParameterFromFile(firstWord, '-ci', flagValue, flag_file, flag_log, check_interval)
                    recording_mode                      = getParameterFromFile(firstWord, '-rm', flagValue, flag_file, flag_log, recording_mode)
                    recording_prio                      = getParameterListFromFile(firstWord, '-rp', flagValue, flag_file, flag_log, recording_prio)
                    host_mode                           = getParameterFromFile(firstWord, '-hm', flagValue, flag_file, flag_log, host_mode)
                    num_rtedumps                        = getParameterFromFile(firstWord, '-nr', flagValue, flag_file, flag_log, num_rtedumps)
                    rtedumps_interval                   = getParameterFromFile(firstWord, '-ir', flagValue, flag_file, flag_log, rtedumps_interval)
                    rte_mode                            = getParameterFromFile(firstWord, '-mr', flagValue, flag_file, flag_log, rte_mode)
                    profile_for_section_restriction     = getParameterFromFile(firstWord, '-pr', flagValue, flag_file, flag_log, profile_for_section_restriction)
                    num_custom_sql_recordings           = getParameterFromFile(firstWord, '-ns', flagValue, flag_file, flag_log, num_custom_sql_recordings)
                    custom_sql_interval                 = getParameterFromFile(firstWord, '-is', flagValue, flag_file, flag_log, custom_sql_interval)
                    custom_sql_recording                = getParameterFromFile(firstWord, '-cs', flagValue, flag_file, flag_log, custom_sql_recording)
                    deliminiter_mode = '1' # default: deliminiter is , 
                    deliminiter_mode                    = getParameterFromFile(firstWord, '-cd', flagValue, flag_file, flag_log, deliminiter_mode)
                    if deliminiter_mode == '2':    
                        custom_queries                  = getParameterListFromFile(firstWord, '-cq', flagValue, flag_file, flag_log, custom_queries, ';')
                    else:
                        custom_queries                  = getParameterListFromFile(firstWord, '-cq', flagValue, flag_file, flag_log, custom_queries)
                    if custom_queries == ['']:   # allow no custom queries with -cq ""
                        custom_queries = []      # make the length 0 in case of -cq ""
                    custom_query_waits                  = getParameterListFromFile(firstWord, '-iq', flagValue, flag_file, flag_log, custom_query_waits)
                    kill_session                        = getParameterListFromFile(firstWord, '-ks', flagValue, flag_file, flag_log, kill_session)
                    num_callstacks                      = getParameterFromFile(firstWord, '-nc', flagValue, flag_file, flag_log, num_callstacks)
                    callstacks_interval                 = getParameterFromFile(firstWord, '-ic', flagValue, flag_file, flag_log, callstacks_interval)
                    num_gstacks                         = getParameterFromFile(firstWord, '-ng', flagValue, flag_file, flag_log, num_gstacks)
                    gstacks_interval                    = getParameterFromFile(firstWord, '-ig', flagValue, flag_file, flag_log, gstacks_interval)
                    num_kprofs                          = getParameterFromFile(firstWord, '-np', flagValue, flag_file, flag_log, num_kprofs)
                    kprofs_interval                     = getParameterFromFile(firstWord, '-ip', flagValue, flag_file, flag_log, kprofs_interval)
                    kprofs_duration                     = getParameterFromFile(firstWord, '-dp', flagValue, flag_file, flag_log, kprofs_duration)
                    kprofs_wait                         = getParameterFromFile(firstWord, '-wp', flagValue, flag_file, flag_log, kprofs_wait)
                    if deliminiter_mode == '2':    
                        critical_features               = getParameterListFromFile(firstWord, '-cf', flagValue, flag_file, flag_log, critical_features, ';')
                    else:
                        critical_features               = getParameterListFromFile(firstWord, '-cf', flagValue, flag_file, flag_log, critical_features)
                    cf_texts                            = getParameterListFromFile(firstWord, '-ct', flagValue, flag_file, flag_log, cf_texts)
                    intervals_of_features               = getParameterListFromFile(firstWord, '-if', flagValue, flag_file, flag_log, intervals_of_features)
                    feature_check_timeout               = getParameterFromFile(firstWord, '-tf', flagValue, flag_file, flag_log, feature_check_timeout)
                    after_recorded                      = getParameterFromFile(firstWord, '-ar', flagValue, flag_file, flag_log, after_recorded)
                    hdbconsservices                     = getParameterListFromFile(firstWord, '-sv', flagValue, flag_file, flag_log, hdbconsservices)
                    hdbconsservices_print               = getParameterFromFile(firstWord, '-svp', flagValue, flag_file, flag_log, hdbconsservices_print)
                    out_dir                             = getParameterFromFile(firstWord, '-od', flagValue, flag_file, flag_log, out_dir)
                    minRetainedOutputDays               = getParameterFromFile(firstWord, '-odr', flagValue, flag_file, flag_log, minRetainedOutputDays)
                    log_dir                             = getParameterFromFile(firstWord, '-ol', flagValue, flag_file, flag_log, log_dir)
                    minRetainedLogDays                  = getParameterFromFile(firstWord, '-olr', flagValue, flag_file, flag_log, minRetainedLogDays)
                    out_config                          = getParameterFromFile(firstWord, '-oc', flagValue, flag_file, flag_log, out_config)
                    min_avg_exec_time_diff_pct          = getParameterFromFile(firstWord, '-sc', flagValue, flag_file, flag_log, min_avg_exec_time_diff_pct)
                    plan_id_changes                     = getParameterFromFile(firstWord, '-spi', flagValue, flag_file, flag_log, plan_id_changes)
                    min_exec_counts                     = getParameterFromFile(firstWord, '-scc', flagValue, flag_file, flag_log, min_exec_counts)
                    min_tot_exec_time_minutes           = getParameterFromFile(firstWord, '-sct', flagValue, flag_file, flag_log, min_tot_exec_time_minutes)
                    h_print_engine_changes              = getParameterFromFile(firstWord, '-scp', flagValue, flag_file, flag_log, h_print_engine_changes)
                    only_negative_changes               = getParameterFromFile(firstWord, '-scn', flagValue, flag_file, flag_log, only_negative_changes)
                    sql_text_len                        = getParameterFromFile(firstWord, '-scx', flagValue, flag_file, flag_log, sql_text_len)
                    app_source_len                      = getParameterFromFile(firstWord, '-scpa', flagValue, flag_file, flag_log, app_source_len)
                    nbrDaysToTakeIntoAcount             = getParameterFromFile(firstWord, '-scd', flagValue, flag_file, flag_log, nbrDaysToTakeIntoAcount)
                    nbrDaysToTakeIntoAcountForStat      = getParameterFromFile(firstWord, '-scs', flagValue, flag_file, flag_log, nbrDaysToTakeIntoAcountForStat)
                    log_features                        = getParameterFromFile(firstWord, '-lf', flagValue, flag_file, flag_log, log_features)
                    receiver_emails                     = getParameterListFromFile(firstWord, '-en', flagValue, flag_file, flag_log, receiver_emails)
                    email_client                        = getParameterFromFile(firstWord, '-enc', flagValue, flag_file, flag_log, email_client)
                    senders_email                       = getParameterFromFile(firstWord, '-ens', flagValue, flag_file, flag_log, senders_email)
                    mail_server                         = getParameterFromFile(firstWord, '-enm', flagValue, flag_file, flag_log, mail_server)
                    std_out                             = getParameterFromFile(firstWord, '-so', flagValue, flag_file, flag_log, std_out)
                    out_run_command                     = getParameterFromFile(firstWord, '-or', flagValue, flag_file, flag_log, out_run_command)
                    ssl                                 = getParameterFromFile(firstWord, '-ssl', flagValue, flag_file, flag_log, ssl)
                    encryption                          = getParameterFromFile(firstWord, '-encr', flagValue, flag_file, flag_log, encryption)
                    sslk                                = getParameterFromFile(firstWord, '-sslk', flagValue, flag_file, flag_log, sslk)
                    sslt                                = getParameterFromFile(firstWord, '-sslt', flagValue, flag_file, flag_log, sslt)
                    sslp                                = getParameterFromFile(firstWord, '-sslp', flagValue, flag_file, flag_log, sslp)
                    ssln                                = getParameterFromFile(firstWord, '-ssln', flagValue, flag_file, flag_log, ssln)
                    virtual_local_host                  = getParameterFromFile(firstWord, '-vlh', flagValue, flag_file, flag_log, virtual_local_host)
                    host_check                          = getParameterFromFile(firstWord, '-hc', flagValue, flag_file, flag_log, host_check)
                    claim_high_isolation                = getParameterFromFile(firstWord, '-hi', flagValue, flag_file, flag_log, claim_high_isolation)
                    shell                               = getParameterFromFile(firstWord, '-sh', flagValue, flag_file, flag_log, shell)
                    hdbsql_env_variable                 = getParameterFromFile(firstWord, '-hev', flagValue, flag_file, flag_log, hdbsql_env_variable)
                    dbuserkey                           = getParameterFromFile(firstWord, '-k', flagValue, flag_file, flag_log, dbuserkey)
                    cpu_check_params                    = getParameterListFromFile(firstWord, '-cpu', flagValue, flag_file, flag_log, cpu_check_params)
     
    #####################   INPUT ARGUMENTS (these would overwrite whats in the configuration file(s))  #################### 
    for word in sys.argv:
        if word[0:1] == '-':
            checkIfAcceptedFlag(word)
    online_test_interval                = getParameterFromCommandLine(sys.argv, '-oi', flag_log, online_test_interval)
    ping_timeout                        = getParameterFromCommandLine(sys.argv, '-pt', flag_log, ping_timeout)
    check_interval                      = getParameterFromCommandLine(sys.argv, '-ci', flag_log, check_interval)
    recording_mode                      = getParameterFromCommandLine(sys.argv, '-rm', flag_log, recording_mode)
    recording_prio                      = getParameterListFromCommandLine(sys.argv, '-rp', flag_log, recording_prio)
    host_mode                           = getParameterFromCommandLine(sys.argv, '-hm', flag_log, host_mode)
    num_rtedumps                        = getParameterFromCommandLine(sys.argv, '-nr', flag_log, num_rtedumps)
    rtedumps_interval                   = getParameterFromCommandLine(sys.argv, '-ir', flag_log, rtedumps_interval)
    rte_mode                            = getParameterFromCommandLine(sys.argv, '-mr', flag_log, rte_mode)
    profile_for_section_restriction     = getParameterFromCommandLine(sys.argv, '-pr', flag_log, profile_for_section_restriction)
    num_custom_sql_recordings           = getParameterFromCommandLine(sys.argv, '-ns', flag_log, num_custom_sql_recordings)
    custom_sql_interval                 = getParameterFromCommandLine(sys.argv, '-is', flag_log, custom_sql_interval)
    custom_sql_recording                = getParameterFromCommandLine(sys.argv, '-cs', flag_log, custom_sql_recording)
    deliminiter_mode = '1'       # default: deliminiter is , 
    deliminiter_mode                    = getParameterFromCommandLine(sys.argv, '-cd', flag_log, deliminiter_mode)
    if deliminiter_mode == '2':    
        custom_queries                  = getParameterListFromCommandLine(sys.argv, '-cq', flag_log, custom_queries, ';')
    else:
        custom_queries                  = getParameterListFromCommandLine(sys.argv, '-cq', flag_log, custom_queries)
    if custom_queries == ['']:   # allow no custom queries with -cq ""
        custom_queries = []      # make the length 0 in case of -cq ""
    custom_query_waits                  = getParameterListFromCommandLine(sys.argv, '-iq', flag_log, custom_query_waits)
    kill_session                        = getParameterListFromCommandLine(sys.argv, '-ks', flag_log, kill_session)
    num_callstacks                      = getParameterFromCommandLine(sys.argv, '-nc', flag_log, num_callstacks)
    callstacks_interval                 = getParameterFromCommandLine(sys.argv, '-ic', flag_log, callstacks_interval)
    num_gstacks                         = getParameterFromCommandLine(sys.argv, '-ng', flag_log, num_gstacks)
    gstacks_interval                    = getParameterFromCommandLine(sys.argv, '-ig', flag_log, gstacks_interval)
    num_kprofs                          = getParameterFromCommandLine(sys.argv, '-np', flag_log, num_kprofs)
    kprofs_interval                     = getParameterFromCommandLine(sys.argv, '-ip', flag_log, kprofs_interval)
    kprofs_duration                     = getParameterFromCommandLine(sys.argv, '-dp', flag_log, kprofs_duration)
    kprofs_wait                         = getParameterFromCommandLine(sys.argv, '-wp', flag_log, kprofs_wait)
    if deliminiter_mode == '2':    
        critical_features               = getParameterListFromCommandLine(sys.argv, '-cf', flag_log, critical_features, ';')
    else:
        critical_features               = getParameterListFromCommandLine(sys.argv, '-cf', flag_log, critical_features)
    if critical_features == ['']:   # allow no critical feature with -cf ""
        critical_features = []      # make the length 0 in case of -cf ""
    cf_texts                            = getParameterListFromCommandLine(sys.argv, '-ct', flag_log, cf_texts)
    intervals_of_features               = getParameterListFromCommandLine(sys.argv, '-if', flag_log, intervals_of_features)
    feature_check_timeout               = getParameterFromCommandLine(sys.argv, '-tf', flag_log, feature_check_timeout)
    after_recorded                      = getParameterFromCommandLine(sys.argv, '-ar', flag_log, after_recorded)
    hdbconsservices                     = getParameterListFromCommandLine(sys.argv, '-sv', flag_log, hdbconsservices)
    hdbconsservices_print               = getParameterFromCommandLine(sys.argv, '-svp', flag_log, hdbconsservices_print)
    out_dir                             = getParameterFromCommandLine(sys.argv, '-od', flag_log, out_dir)
    minRetainedOutputDays               = getParameterFromCommandLine(sys.argv, '-odr', flag_log, minRetainedOutputDays)
    log_dir                             = getParameterFromCommandLine(sys.argv, '-ol', flag_log, log_dir)
    minRetainedLogDays                  = getParameterFromCommandLine(sys.argv, '-olr', flag_log, minRetainedLogDays)
    out_config                          = getParameterFromCommandLine(sys.argv, '-oc', flag_log, out_config)
    min_avg_exec_time_diff_pct          = getParameterFromCommandLine(sys.argv, '-sc', flag_log, min_avg_exec_time_diff_pct)
    plan_id_changes                     = getParameterFromCommandLine(sys.argv, '-spi', flag_log, plan_id_changes)
    min_exec_counts                     = getParameterFromCommandLine(sys.argv, '-scc', flag_log, min_exec_counts)
    min_tot_exec_time_minutes           = getParameterFromCommandLine(sys.argv, '-sct', flag_log, min_tot_exec_time_minutes)   
    h_print_engine_changes              = getParameterFromCommandLine(sys.argv, '-scp', flag_log, h_print_engine_changes)
    only_negative_changes               = getParameterFromCommandLine(sys.argv, '-scn', flag_log, only_negative_changes)
    sql_text_len                        = getParameterFromCommandLine(sys.argv, '-scx', flag_log, sql_text_len)
    app_source_len                      = getParameterFromCommandLine(sys.argv, '-scpa', flag_log, app_source_len)
    nbrDaysToTakeIntoAcount             = getParameterFromCommandLine(sys.argv, '-scd', flag_log, nbrDaysToTakeIntoAcount)
    nbrDaysToTakeIntoAcountForStat      = getParameterFromCommandLine(sys.argv, '-scs', flag_log, nbrDaysToTakeIntoAcountForStat)
    log_features                        = getParameterFromCommandLine(sys.argv, '-lf', flag_log, log_features)
    receiver_emails                     = getParameterListFromCommandLine(sys.argv, '-en', flag_log, receiver_emails)
    email_client                        = getParameterFromCommandLine(sys.argv, '-enc', flag_log, email_client)
    senders_email                       = getParameterFromCommandLine(sys.argv, '-ens', flag_log, senders_email)
    mail_server                         = getParameterFromCommandLine(sys.argv, '-enm', flag_log, mail_server)
    std_out                             = getParameterFromCommandLine(sys.argv, '-so', flag_log, std_out)
    out_run_command                     = getParameterFromCommandLine(sys.argv, '-or', flag_log, out_run_command)
    ssl                                 = getParameterFromCommandLine(sys.argv, '-ssl', flag_log, ssl)
    encryption                          = getParameterFromCommandLine(sys.argv, '-encr', flag_log, encryption)
    sslk                                = getParameterFromCommandLine(sys.argv, '-sslk', flag_log, sslk)
    sslt                                = getParameterFromCommandLine(sys.argv, '-sslt', flag_log, sslt)
    sslp                                = getParameterFromCommandLine(sys.argv, '-sslp', flag_log, sslp)
    ssln                                = getParameterFromCommandLine(sys.argv, '-ssln', flag_log, ssln)
    virtual_local_host                  = getParameterFromCommandLine(sys.argv, '-vlh', flag_log, virtual_local_host)
    host_check                          = getParameterFromCommandLine(sys.argv, '-hc', flag_log, host_check)
    claim_high_isolation                = getParameterFromCommandLine(sys.argv, '-hi', flag_log, claim_high_isolation)
    shell                               = getParameterFromCommandLine(sys.argv, '-sh', flag_log, shell)
    hdbsql_env_variable                 = getParameterFromCommandLine(sys.argv, '-hev', flag_log, hdbsql_env_variable)
    dbuserkey                           = getParameterFromCommandLine(sys.argv, '-k', flag_log, dbuserkey)
    cpu_check_params                    = getParameterListFromCommandLine(sys.argv, '-cpu', flag_log, cpu_check_params)  
     
    ############ GET LOCAL HOST, LOCAL SQL PORT, LOCAL INSTANCE and SID ##########
    local_host = run_command("hostname").replace('\n','') if virtual_local_host == "" else virtual_local_host
    key_environment = run_command('''hdbuserstore LIST '''+dbuserkey)
    if "NOT FOUND" in key_environment:
        print("ERROR, the key ", dbuserkey, " is not maintained in hdbuserstore.")
        os._exit(1)
    if "DATABASE" in key_environment:
        DATABASE = key_environment.split('\n')[3].split('  DATABASE: ')[1]
    else:
        DATABASE = ""
    key_environment = key_environment.split('\n')
    key_environment = [ke for ke in key_environment if ke and not ke == 'Operation succeed.']
    ENV = key_environment[1].replace('  ENV : ','').replace(';',',').split(',')
    key_hosts = [env.split(':')[0].split('.')[0] for env in ENV]  #if full host name is specified in the Key, only the first part is used
    key_domains = [env.split(':')[0].split('.')[1:] for env in ENV]
    key_domains = ['.'.join(kd) for kd in key_domains] 
    if not all(kd==key_domains[0] for kd in key_domains):
        print("ERROR, the key ", dbuserkey, " is defining ENV with different host domains. They should be all equal.")
        os._exit(1)
    key_domain = key_domains[0]  #this is empty if domains not specified in the key
    if not local_host in key_hosts and not 'localhost' in key_hosts:
        #Turned out this check was not needed. A user that executed HANASitter from a non-possible future master with virtual host name virt2 only wanted
        #possible future masters in the hdbuserstore:   virt1:30413,virt3:30413,virt4:30413, so he executed HANASitter on virt2 with  -vlh virt2  --> worked fine
        # --> Instead of Error, just do Warning if -vlh is not used
        if not virtual_local_host:
            print("WARNING, local host, ", local_host, ", should be one of the hosts specified for the key. It is not, so will assume the SQL port of the first one. Continue on own risk!")
        local_host_index = 0
    elif not local_host in key_hosts and 'localhost' in key_hosts:
        local_host_index = 0
    else:
        local_host_index = key_hosts.index(local_host)       
    ### host_check, -hc
    host_check = checkAndConvertBooleanFlag(host_check, "-hc")
    key_sqlports = [env.split(':')[1] for env in ENV]    
    local_sqlport = key_sqlports[local_host_index]             
    dbinstances = [port[1:3] for port in key_sqlports]
    if not all(x == dbinstances[0] for x in dbinstances):
        if host_check:
            print("ERROR: The hosts provided with the user key, "+dbuserkey+", do not all have the same instance number")
            os._exit(1)
        else:
            print("WARNING: The hosts provided with the user key, "+dbuserkey+", do not all have the same instance number. They should. Continue on your own risk!")
    local_dbinstance = dbinstances[local_host_index]
    SID = run_command('whoami').replace('\n','').replace('adm','').upper()
    ### claim_high_isolation, -hi
    claim_high_isolation = checkAndConvertBooleanFlag(claim_high_isolation, "-hi")

    ############# OUTPUT DIRECTORIES #########
    out_dir = out_dir.replace(" ","_")
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
    log_dir = log_dir.replace(" ","_")
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
 
    ############ CHECK AND CONVERT INPUT PARAMETERS FOR COMMUNICATION MANAGER and OLINE TEST ################
    ### out_config, -oc
    out_config = checkAndConvertBooleanFlag(out_config, "-oc") 
    if out_config:
        parameter_string = "\n".join("{}\t{}".format(k, "= "+v[0]+" from "+v[1]) for k, v in flag_log.items())
        startstring = "**************************************************************************************\nHANASitter started "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" with\n"+parameter_string+"\nas "+dbuserkey+": "+'\n'.join(key_environment)+"\n\n ANY USAGE OF HANASITTER ASSUMES THAT YOU HAVE READ AND UNDERSTOOD THE DISCLAIMER!\n    python hanasitter.py --disclaimer\n\n**************************************************************************************"
    else:
        startstring = "**************************************************************************************\nHANASitter started "+datetime.now().strftime("%Y-%m-%d %H:%M:%S")+" with \n"+" ".join(sys.argv)+"\nas "+dbuserkey+": "+'\n'.join(key_environment)+"\n\n ANY USAGE OF HANASITTER ASSUMES THAT YOU HAVE READ AND UNDERSTOOD THE DISCLAIMER!\n    python hanasitter.py --disclaimer\n\n**************************************************************************************"
    log(startstring, CommunicationManager(dbuserkey, out_dir, log_dir, True, "", False, False))    
    ### std_out, -so
    std_out = checkAndConvertBooleanFlag(std_out, "-so")
    ### out_run_command, -or
    out_run_command = checkAndConvertBooleanFlag(out_run_command, "-or")
    ### ssl, -ssl
    ssl = checkAndConvertBooleanFlag(ssl, "-ssl")
    hdbsql_string = "hdbsql "
    if ssl:
        hdbsql_string = "hdbsql -e -ssltrustcert -sslcreatecert "
    ### encryption, -encr
    encryption = checkAndConvertBooleanFlag(encryption, "-encr")
    if encryption:
        hdbsql_string = hdbsql_string + " -e "
    ### hdbsql_env_variable, -hev
    if hdbsql_env_variable:
        hdbsql_string = hdbsql_string + " $" + hdbsql_env_variable
    ### sslk, -sslk
    if sslk:
        hdbsql_string = hdbsql_string + " -sslkeystore " + sslk
    ### sslt, -sslt
    if sslt:
        hdbsql_string = hdbsql_string + " -ssltruststore " + sslt
    ### sslp, -sslp
    if sslp:
        hdbsql_string = hdbsql_string + " -sslprovider " + sslp
    ### ssln, -ssln
    if ssln:
        hdbsql_string = hdbsql_string + " -sslhostnameincert " + ssln
    ### min_avg_exec_time_diff_pct, -sc
    if not is_integer(min_avg_exec_time_diff_pct):
        log("INPUT ERROR: -sc must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    min_avg_exec_time_diff_pct = int(min_avg_exec_time_diff_pct)
    ### plan_id_changes, -spi
    plan_id_changes = checkAndConvertBooleanFlag(plan_id_changes, "-spi")
    if plan_id_changes and min_avg_exec_time_diff_pct < 0:
        log("INPUT ERROR: -spi is specified but not -sp. This makes no sense. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    ### min_exec_counts, -scc
    if not is_integer(min_exec_counts):
        log("INPUT ERROR: -scc must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    min_exec_counts = int(min_exec_counts)
    ### min_tot_exec_time_minutes, -sct
    if not is_integer(min_tot_exec_time_minutes):
        log("INPUT ERROR: -sct must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    min_tot_exec_time_minutes = int(min_tot_exec_time_minutes)
    ### h_print_engine_changes, -scp
    if not is_integer(h_print_engine_changes):
        log("INPUT ERROR: -scp must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    h_print_engine_changes = int(h_print_engine_changes)
    ### only_negative_changes, -scn
    only_negative_changes = checkAndConvertBooleanFlag(only_negative_changes, "-scn")
    ### sql_text_len, -scx
    if not is_integer(sql_text_len):
        log("INPUT ERROR: -scx must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    sql_text_len = int(sql_text_len)
    if sql_text_len and not h_print_engine_changes:
        log("INPUT ERROR: -scx is more then 0 while -scp is not, this makes no sense. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1) 
    ### app_source_len, -scpa
    if not is_integer(app_source_len):
        log("INPUT ERROR: -scpa must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    app_source_len = int(app_source_len)
    if app_source_len and not h_print_engine_changes:
        log("INPUT ERROR: -scpa is more then 0 while -scp is not, this makes no sense. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1) 
    ### nbrDaysToTakeIntoAcount, -scd
    if not is_integer(nbrDaysToTakeIntoAcount):
        log("INPUT ERROR: -scd must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    nbrDaysToTakeIntoAcount = int(nbrDaysToTakeIntoAcount)
    ### nbrDaysToTakeIntoAcountForStat, -scs
    if not is_integer(nbrDaysToTakeIntoAcountForStat):
        log("INPUT ERROR: -scs must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    nbrDaysToTakeIntoAcountForStat = int(nbrDaysToTakeIntoAcountForStat)
    ########## SQL Cache Check Manager #################
    sccmanager = SCCManager(min_avg_exec_time_diff_pct, plan_id_changes, min_exec_counts, min_tot_exec_time_minutes, h_print_engine_changes, only_negative_changes, sql_text_len, app_source_len, nbrDaysToTakeIntoAcount, nbrDaysToTakeIntoAcountForStat)
    ### log_features, -lf
    log_features = checkAndConvertBooleanFlag(log_features, "-lf")
    if log_features:
        log("SAFETY ERROR: -lf is not supported anymore. If you really need it you must enable it yourself (by e.g. removing next line). Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1) 
    if log_features and len(critical_features) == 0:
        log("INPUT ERROR: -lf is True even though -cf is empty, i.e. no critical feature specified. This does not make sense. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1) 
    ### online_test_interval, -oi  
    if not is_integer(online_test_interval):
        log("INPUT ERROR: -oi must be an integer. Please see --help for more information.", CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, False, False))
        os._exit(1)
    online_test_interval = int(online_test_interval)
        
    ############# COMMUNICATION MANAGER ##############
    comman = CommunicationManager(dbuserkey, out_dir, log_dir, std_out, hdbsql_string, log_features, out_run_command)   

    ### First Online-Check ###
    wasOnline = True
    while not is_online(local_dbinstance, comman):
        log("\nOne of the online checks found out that this HANA instance is not online and/or not primary. HANASitter will now have a "+str(online_test_interval)+" seconds break.\n", comman, sendEmail = wasOnline)
        wasOnline = False
        time.sleep(float(online_test_interval))  # wait online_test_interval seconds before again checking if HANA is running

    ### MDC or not, SystemDB or Tenant ### 
    if not is_multitenant_database_container(local_dbinstance, shell):
        log("COMPATIBILITY ERROR: This is not MDC. Is this HANA 1? HANA 1 is not supported as of May 2021.", comman)
        os._exit(1)

    tenantIndexserverPorts = []  
    output = run_command('HDB info').splitlines(1)
    tenantIndexserverPorts = [line.split(' ')[-1].strip('\n') for line in output if "hdbindexserver -port" in line]
    tenantDBNames = [line.split(' ')[0].replace('adm','').replace('usr','').upper() for line in output if "hdbindexserver -port" in line]  # only works if high-isolated (below we get the names in case of low isolated)
    host_folder = get_host_folder(local_dbinstance, local_host, key_domain, shell)
    lock_content = run_command('ls -l '+host_folder+'/lock').splitlines(1)
    nameserverPort = [line.split('@')[1].replace('.pid','') for line in lock_content if "hdbnameserver" in line][0].strip('\n') 
    if not tenantDBNames:
        print("WARNING: Something went wrong, it passed online tests but still no tenant names were found. Is this HANA 1? HANA 1 is not supported as of May 2021.")
        #os._exit(1)
    ### TENANT NAMES for NON HIGH-ISOLATED MDC ###
    high_isolation = not (tenantDBNames.count(tenantDBNames[0]) == len(tenantDBNames) and tenantDBNames[0] == SID) or claim_high_isolation
    if not high_isolation:   # if all tenant names are equal and equal to SystemDB's SID, then it is non-high-isolation --> get tenant names using daemon instead
        [tenantDBNames, tenantIndexserverPorts] = tenant_names_and_ports(host_folder+"/daemon.ini") # if non-high isolation the tenantIndexserverPorts from HDB info could be wrong order

    ####### COMMUNICATION PORT (i.e. nameserver port if SystemDB at MDC, or indexserver port if TenantDB and if non-MDC) ########
    communicationPort = "-1"
    tenantDBName = None
    is_tenant = False
    for dbname, port in zip(tenantDBNames, tenantIndexserverPorts):
        testTenant = Tenant(dbname, port, local_dbinstance, SID)
        if testTenant.sqlPort == int(local_sqlport) or testTenant.DBName == DATABASE:     # then the sql port provided in hdbuserstore key is a tenant, or we checking the database name                   
            tenantDBName = testTenant.DBName
            is_tenant = True
            communicationPort = testTenant.getIndexserverPortString()          # indexserver port for the tenant
    if not is_tenant:
        communicationPort = nameserverPort                                     # nameserver port for SystemDB

    ### SCALE OUT or Single Host ###
    hosts_worker_and_standby = run_command('sapcontrol -nr '+local_dbinstance+' -function GetSystemInstanceList').splitlines(1)
    hosts_worker_and_standby = [line.split(',')[0] for line in hosts_worker_and_standby if ("HDB" in line or "HDB|HDB_WORKER" in line or "HDB|HDB_STANDBY" in line)] #Should we add HDB|HDB_XS_WORKER also?
    hosts_worker_and_standby_short = [host.split('.')[0] for host in hosts_worker_and_standby] # to deal with HSR and virtual host names (from Marco)
    for aHost in key_hosts:  #Check that hosts provided in hdbuserstore are correct
        if not aHost in hosts_worker_and_standby and not aHost.split('.')[0] in hosts_worker_and_standby_short and not aHost in ['localhost']:
            if host_check:
                print("ERROR: The host, "+aHost+", provided with the user key, "+dbuserkey+", is not one of the worker or standby hosts: ", hosts_worker_and_standby)
                os._exit(1)
            else:
                print("WARNING: The host, "+aHost+", provided with the user key, "+dbuserkey+", is not one of the worker or standby hosts: ", hosts_worker_and_standby)

    ### HOST(S) USED BY THIS DB ###
    used_hosts = []
    for potential_host in hosts_worker_and_standby:        
        if '@'+communicationPort in run_command('ls -l '+cdalias('cdhdb', local_dbinstance, shell)+potential_host+'/lock') or '@'+communicationPort in run_command('ls -l '+cdalias('cdhdb', local_dbinstance, shell)+potential_host+'.'+key_domain+'/lock'):
            used_hosts.append(potential_host) 
    ############ CHECK AND CONVERT THE REST OF THE INPUT PARAMETERS ################
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
        print("INPUT ERROR: The -rm flag must be either 1, 2, or 3. Please see --help for more information.")
        os._exit(1)           
    ### recording_prio, -rp
    if not len(recording_prio) == 6:
        print("INPUT ERROR: The -rp flag must be followed by 6 items, seperated by comma. Please see --help for more information.")
        os._exit(1)
    if not (recording_prio[0].isdigit() or recording_prio[1].isdigit() or recording_prio[2].isdigit() or recording_prio[3].isdigit() or recording_prio[4].isdigit() or recording_prio[5].isdigit()):
        print("INPUT ERROR: The -rp flag must be followed by positive integers, seperated by commas. Please see --help for more information.")
        os._exit(1)
    recording_prio = [int(rec) for rec in recording_prio]
    if not (recording_prio[0] in [1,2,3,4,5,6] or recording_prio[1] in [1,2,3,4,5,6] or recording_prio[2] in [1,2,3,4,5,6] or recording_prio[3] in [1,2,3,4,5,6] or recording_prio[4] in [1,2,3,4,5,6] or recording_prio[5] in [1,2,3,4,5,6]):
        print("INPUT ERROR: The -rp flag must be followed by integers of the values withing [1-6]. Please see --help for more information.")
        os._exit(1)     
    if [rec for rec in recording_prio if recording_prio.count(rec) > 1]:
        print("INPUT ERROR: The -rp flag must not contain dublicates. Please see --help for more information.")
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
        log("INPUT ERROR: The -mr flag must be either 0 or 1. Please see --help for more information.", comman)
        os._exit(1)
    ### num_custom_sql_recordings, -ns
    if not is_integer(num_custom_sql_recordings):
        log("INPUT ERROR: -ns must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    num_custom_sql_recordings = int(num_custom_sql_recordings)
    ### custom_sql_interval, -is
    if not is_integer(custom_sql_interval):
        log("INPUT ERROR: -is must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    custom_sql_interval = int(custom_sql_interval)
    ### custom_sql_recording, -cs
    if custom_sql_recording:
        if not num_custom_sql_recordings:
            log("INPUT ERROR: The -cs flag specifies something allthough -ns is not. This makes no sense. Please see --help for more information.", comman)
            os._exit(1)
        if not custom_sql_recording[0:6].upper() == 'SELECT':
            log('INPUT ERROR: The -cs flag must be a SELECT statement. Please see --help for more information.', comman) 
            os._exit(1)
    ### custom_query_waits, -iq
    if len(custom_query_waits) != len(custom_queries):
        log('INPUT ERROR: The -iq flag must be of the same length as -cq. Please see --help for more information.', comman)
        os._exit(1)
    for i in range(len(custom_query_waits)):
        if not is_integer(custom_query_waits[i]):
            log('INPUT ERROR: -iq must only contain integers. Please see --help for more information', comman)
            os._exit(1)
        custom_query_waits[i] = int(custom_query_waits[i])
    if len(custom_query_waits) and recording_mode == 3:
        log('INPUT ERROR: -cq and -iq are not supported for -rm = 3. Please see --help for more information', comman)
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
    ### hdbconsservices, -sv 
    if hdbconsservices:
        if not all(service in ['nameserver', 'indexserver', 'compileserver', 'preprocessor', 'docstore', 'dpserver', 'scriptserver', 'xsengine', 'diserver', 'webdispatcher'] for service in hdbconsservices):
            log("INPUT ERROR: One of the elements of -sv is not one of the valid values. Please see --help for more information.", comman)
            os._exit(1)
        if num_custom_sql_recordings:
            log("INPUT ERROR: Both -sv and -ns are specified, this makes no sense. Please see --help for more information.", comman)
            os._exit(1)
        if custom_queries:
            log("INPUT ERROR: Both -sv and -cq are specified, this makes no sense. Please see --help for more information.", comman)
            os._exit(1)
    ### hdbconsservices_print, -svp
    hdbconsservices_print = checkAndConvertBooleanFlag(hdbconsservices_print, "-svp")
    if hdbconsservices_print and not hdbconsservices:
        log("INPUT ERROR: -svp is true allthough -sv is not specified, this makes no sense. Please see --help for more information.", comman)
        os._exit(1)
    ### minRetainedOutputDays, -odr
    if not is_integer(minRetainedOutputDays):
        log("INPUT ERROR: -odr must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    minRetainedOutputDays = int(minRetainedOutputDays)
    ### minRetainedLogDays, -olr
    if not is_integer(minRetainedLogDays):
        log("INPUT ERROR: -olr must be an integer. Please see --help for more information.", comman)
        os._exit(1)
    minRetainedLogDays = int(minRetainedLogDays)
    ### critical_features, -cf
    if len(critical_features)%4: # this also allow empty list in case just only ping check without feature check; -cf ""
        log("INPUT ERROR: -cf must be a list with the length of multiple of 4. Please see --help for more information.", comman)
        os._exit(1)
    if sys.version_info[0] == 2:
        critical_features = [critical_features[i*4:i*4+4] for i in range(len(critical_features)/4)]    # / is integer division in Python 2
    elif sys.version_info[0] == 3:
        critical_features = [critical_features[i*4:i*4+4] for i in range(len(critical_features)//4)]   # // is "integer division" in Python 3
    else:
        print("ERROR: Wrong Python version")
        os._exit(1)    
    critical_features = [CriticalFeature(cf[0], cf[1], cf[2], cf[3]) for cf in critical_features] #testing cf[3] is done in the class
    ### cf_texts, -ct
    if cf_texts:
        if not len(cf_texts) == len(critical_features): 
            log("INPUT ERROR: -ct must be a list with the length same as number of critical features. Please see --help for more information.", comman)
            os._exit(1)
        cf_texts = [ct.replace("_", ' ') for ct in cf_texts]
        for i in range(len(critical_features)):
            critical_features[i].setText(cf_texts[i])
    ### kill_session, -ks
    if kill_session:
        if not len(kill_session) == len(critical_features):
            log("INPUT ERROR: -ks must be a list with the same length as number features specified with -cf. Please see --help for more information.", comman)
            os._exit(1)
        if any(e not in ['0', 'C', 'D'] for e in kill_session):
            log("INPUT ERROR: -ks must be a list with the elements either 0, C or D. Please see --help for more information.", comman)
            os._exit(1)
        for i in range(len(kill_session)):
            critical_features[i].setKillSession(kill_session[i])
    ### intervals_of_features, -if
    if intervals_of_features:
        if len(intervals_of_features)%2:
            log("INPUT ERROR: -if must be a list with the length of multiple of 2. Please see --help for more information.", comman)
            os._exit(1)
        intervals_of_features = [intervals_of_features[i*2:i*2+2] for i in range(int(len(intervals_of_features)/2))]
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
    if not (int(cpu_check_params[0]) in [0,1,2,3]):
        log("INPUT ERROR: CPU checks type has to be either 0, 1, 2 or 3. Please see --help for more information.", comman)
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
    ### receiver_emails, -en
    if receiver_emails:
        if any(not is_email(element) for element in receiver_emails):
            log("INPUT ERROR: some element(s) of -en is/are not email(s). Please see --help for more information.", comman)
            os._exit(1)
    ### num_rtedumps, -nr, num_callstacks, -nc, num_gstacks, -ng, num_kprofs, -np, num_custom_sql_recordings, -ns, log_features, -lf, receiver_emails, -en, custom_queries, -cq
    if not kill_session:
        if (num_rtedumps <= 0 and num_callstacks <= 0 and num_gstacks <= 0 and num_kprofs <= 0 and num_custom_sql_recordings <= 0 and log_features == False and not receiver_emails and not custom_queries):
            log("INPUT ERROR: No kill-session and no recording is specified (-nr, -nc, -ng, -np, and -ns are all <= 0, or none of them are specified and -lf = false) and no email receiver nor custom query is specified. It then makes no sense to run hanasitter. Please see --help for more information.", comman)
            os._exit(1)
    ### email_client, -enc
    if email_client:
        if not receiver_emails:
            log("INPUT ERROR: -enc is specified although -en is not, this makes no sense. Please see --help for more information.", comman)
            os._exit(1)
    if receiver_emails:
        if not email_client:
            email_client = 'mailx'
        if email_client not in ['mailx', 'mail', 'mutt']:
            print("INPUT ERROR: The -enc flag does not specify any of the email clients mailx, mail, or mutt. If you are using another email client that can send emails with the command ")
            print('             <message> | <client> -s "<subject>" \n please let me know.')
            os._exit(1)
    ### senders_email, -ens
    if senders_email:
        if not receiver_emails:
            log("INPUT ERROR: -ens is specified although -en is not, this makes no sense. Please see --help for more information.", comman)
            os._exit(1)
        if not is_email(senders_email):
            log("INPUT ERROR: -ens is not an email. Please see --help for more information.", comman)
            os._exit(1)
    ### mail_server, -enm
    if mail_server:
        if not receiver_emails:
            log("INPUT ERROR: -enm is specified although -en is not, this makes no sense. Please see --help for more information.", comman)
            os._exit(1)
    ### shell, -sh
    if not shell in ['/bin/bash', '/bin/sh', '/bin/csh']:
        log("INPUT ERROR: -sh must be a shell. If I forgot one, please let me know. Please see --help for more information.", comman)
        os._exit(1)

    ############# EMAIL NOTIFICATION ##############
    if receiver_emails:
        global emailNotification
        emailNotification = EmailNotification(receiver_emails, email_client, senders_email, mail_server, SID)

    ### CREATE HDBCONS MANGER ###
    hdbcons = HdbconsManager(local_host, used_hosts, local_dbinstance, is_tenant, communicationPort, SID, rte_mode, tenantDBName, shell)
    ### FILL HDBCONS STRINGS ###
    if hdbconsservices:  # Then -sv is set with requested services
        for hdbconsservice in hdbconsservices:
            for hdbconshost in used_hosts:
                hdbconsport = getServiceHostPort(hdbconsservice, hdbconshost, tenantDBName, local_dbinstance, shell)
                if not hdbconsport == '-1':
                    if len(hosts_worker_and_standby) > 1 or high_isolation:    #SAP Note 2410143 says high isolation must use  distribute e
                        hdbcons.create_hdbcons_string(hdbconshost, hdbconsport, hdbconsservice)
                    else:
                        hdbcons.create_hdbcons_string_scale_up(hdbconshost, hdbconsport, hdbconsservice)
        if hdbconsservices_print:
            hdbcons.print_service_host_ports()
    else:  # then -sv is not set --> hdbcons opens in nameserver, i.e. SDB, and dumps based on the SQL port specified in the key, 
           # that could be an indexserver or the nameserver, i.e. -d, see SAP Note 2222218, is not used   
        for hdbconshost in used_hosts:
            hdbconsservice = "indexserver" if is_tenant else "nameserver"
            if len(hosts_worker_and_standby) > 1 or high_isolation:     #SAP Note 2410143 says high isolation must use  distribute e
                hdbcons.create_hdbcons_string(hdbconshost, communicationPort, hdbconsservice)
            else:
                hdbcons.create_hdbcons_string_scale_up(hdbconshost, communicationPort, hdbconsservice)

    ################ START #################
    if is_tenant:
        printout = "Host = "+str(local_host)+", SID = "+SID+", DB Instance = "+str(local_dbinstance)+", MDC tenant = "+tenantDBName+", Indexserver Port = "+str(communicationPort)
    else:
        printout = "Host = "+str(local_host)+", SID = "+SID+", DB Instance = "+str(local_dbinstance)+", MDC SystemDB, Nameserver Port = "+str(communicationPort)           
    if (len(hosts_worker_and_standby) > 1):
        printout += "\nScale Out DB System with hosts: "+", ".join([h for h in hosts_worker_and_standby])
        if is_tenant:        
            printout += "\nTenant DB "+tenantDBName+"@"+SID+" uses host(s): "+", ".join([h for h in used_hosts])
        else:
            printout += "\nSystemDB@"+SID+" uses host(s): "+", ".join([h for h in used_hosts])
    log(printout, comman)       
    log("Online, Primary and Not-Secondary Check: Interval = "+str(online_test_interval)+" seconds", comman)
    if ping_timeout == 0:
        log("Ping Check: None", comman)
    elif check_interval == 0:
        log("Ping Check: Timeout = "+str(ping_timeout)+" seconds, If nothing is found HANASitter will exit since -ci = 0", comman)
    else:
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
        log("All information for all features that are in one of the above critical feature states is recorded in the "+comman.log_dir+"/criticalFeatures log", comman)
    log("Recording mode: "+str(recording_mode), comman)
    log("Recording Type      , Number Recordings   ,   Intervals [seconds] ,   Durations [seconds]      ,    Wait [milliseconds]", comman)  
    log("GStack              , "+str(num_gstacks)+"                   ,   "+str(gstacks_interval)+"                  ,   ", comman)
    log("Kernel Profiler     , "+str(num_kprofs)+"                   ,   "+str(kprofs_interval)+"                  ,   "+str(kprofs_duration)+"                       ,    "+str(kprofs_wait), comman)
    log("Call Stack          , "+str(num_callstacks)+"                   ,   "+str(callstacks_interval)+"                  ,   ", comman)
    if rte_mode == 0:
        log("RTE Dumps (normal)  , "+str(num_rtedumps)+"                   ,   "+str(rtedumps_interval)+"                  ,   ", comman)
    else: # change if more modes are added
        log("RTE Dumps (light)   , "+str(num_rtedumps)+"                   ,   "+str(rtedumps_interval)+"                  ,   ", comman)
    log("Custom SQL          , "+str(num_custom_sql_recordings)+"                   ,   "+str(custom_sql_interval)+"                  ,   ", comman)
    if custom_sql_recording:
        log("Custom SELECT Output: "+custom_sql_recording, comman)
    if custom_queries:
        for i in range(len(custom_queries)):
            log('Custom Query: "'+custom_queries[i]+'" with wait: '+str(custom_query_waits[i])+' seconds', comman)
    log("Recording Priority: "+recording_prio_convert(recording_prio), comman)
    if int(cpu_check_params[0]) > 0:
        if int(cpu_check_params[0]) == 1:
            cpu_string = "User CPU Check:            "
        elif int(cpu_check_params[0]) == 2:
            cpu_string = "System CPU Check:          "
        else:
            cpu_string = "User and System CPU Check: "
        log(cpu_string+" Every "+cpu_check_params[2]+" seconds, Number CPU Checks = "+cpu_check_params[1]+", Max allowed av. CPU = "+cpu_check_params[3]+" %", comman)
    if after_recorded < 0:
        log("After Recording: Exit", comman)
    else:
        log("After Recording: Sleep "+str(after_recorded)+" seconds", comman)
    log(" - - - - - Start HANASitter - - - - - - ", comman)
    log("Action            , Timestamp              , Duration         , Successful   , Result     , Comment ", comman)
    rte = RTESetting(num_rtedumps, rtedumps_interval, profile_for_section_restriction)
    callstack = CallStackSetting(num_callstacks, callstacks_interval)
    gstack = GStackSetting(num_gstacks, gstacks_interval)
    kprofiler = KernelProfileSetting(num_kprofs, kprofs_interval, kprofs_duration, kprofs_wait)
    customsql = CustomSQLSetting(num_custom_sql_recordings, custom_sql_interval, custom_sql_recording)
    customquer = CustomQuerySetting(custom_queries, custom_query_waits)
    try:
        if num_kprofs: #only if we write kernel profiler dumps will we need temporary output folders
            hdbcons.create_temp_output_directories(host_check) #create temporary output folders
        wasOnline = True
        while True: 
            if is_online(local_dbinstance, comman) and not is_secondary(comman):
                wasOnline = True
                [recorded, offline] = tracker(ping_timeout, check_interval, recording_mode, rte, callstack, gstack, kprofiler, customsql, customquer, recording_prio, critical_features, feature_check_timeout, cpu_check_params, sccmanager, minRetainedLogDays, minRetainedOutputDays, host_mode, local_dbinstance, comman, hdbcons)
                if recorded:
                    if after_recorded < 0: #if after_recorded is negative we want to exit after a recording
                        hdbcons.clear()    #remove temporary output folders before exit
                        sys.exit()
                    time.sleep(float(after_recorded))  # after recorded call stacks and/or rte dumps it sleeps a bit and then continues tracking if HANA is online
                if not recorded and not offline and check_interval == 0:  
                    hdbcons.clear()    #remove temporary output folders before exit
                    log("\nSince -ci = 0 HANASitter will now stop even if no reson for recording was found.\n", comman)
                    sys.exit()
                if offline:
                    log("\nDuring the tracking hana turned offline. HANASitter will now have a "+str(online_test_interval)+" seconds break.\n", comman, sendEmail = True)
                    time.sleep(float(online_test_interval))  # wait online_test_interval seconds before again checking if HANA is running
            else:
                log("\nOne of the online checks found out that this HANA instance is not online and/or not primary. HANASitter will now have a "+str(online_test_interval)+" seconds break.\n", comman, sendEmail = wasOnline)
                wasOnline = False
                time.sleep(float(online_test_interval))  # wait online_test_interval seconds before again checking if HANA is running
    #except:           
    except Exception as e:
        print("HANASitter stopped with the exception: ", e, "\nHere is the stack trace:\n")
        traceback.print_exception(type(e), e, e.__traceback__)
        hdbcons.clear()    #remove temporary output folders before exit
        sys.exit()
    except KeyboardInterrupt:   # catching ctrl-c
        print("HANASitter was stopped with ctrl-c")
        hdbcons.clear()    #remove temporary output folders before exit
        sys.exit()
          
              
if __name__ == '__main__':
    main()
                        

