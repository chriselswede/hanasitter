# SAP HANASitter
A monitoring script to automatically create dump files at certain scenarios for SAP HANA 

### DESCRIPTION:  
The HANA sitter checks regularly (def. 1h) if HANA is online and primary. If so, it starts to track. Tracking includes regularly (def. 1m) checks if HANA is responsive. If it is not, it will record. Recording could include writing call stacks of all active threads and/or record run time dumps and/or indexserver gstacks and/or kernel profiler traces. By default nothing is recorded. If HANA is responsive it will check for too many critical features of HANA. By default this is checking if there are more than 30 active threads. If there is, it will record (see above). After it is done recording it will by default exit, but could also restart, if so wanted. After it has concluded that all was good, it will wait (def. 1h) and then start all over to check again if HANA is online and primary. See also SAP Note [2399979](https://launchpad.support.sap.com/#/notes/2399979).

### DISCLAIMER  
ANY USAGE OF HANASITTER ASSUMES THAT YOU HAVE UNDERSTOOD AND AGREED THAT:  
1. HANASitter is NOT SAP official software, so normal SAP support of HANASitter cannot be assumed   
2. HANASitter is open source   
3. HANASitter is provided "as is"  
4. HANASitter is to be used on "your own risk"  
5. HANASitter is a one-man's hobby (developed, maintained and supported only during non-working hours)   

6. All HANASitter documentations have to be read and understood before any usage:    
    * SAP Note [2399979](https://launchpad.support.sap.com/#/notes/2399979)   
    * The .pdf file hanasitter.pdf    
    * All output from executing     `python hanasitter.py --help`    
    
7. HANASitter can help you to automize certain monitoring tasks but is not an attempt to teach you how to monitor SAP HANA  
I.e. if you do not know what you want to do, HANASitter cannot help, but if you do know, HANASitter can automitize it    
   
8. HANASitter is not providing any recommendations, all flags shown in the documentation (see point 6.) are only examples
