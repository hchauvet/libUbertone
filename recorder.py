#!/usr/bin/python
# -*- coding: utf-8 -*-

# Script to create a recorder for Ub-lab
'''
File: recorder.py
Author: Hugo Chauvet
Description: Create a simple recorder for ub-Lab
version: 21.08.2013 20:58:57
'''

import libUbertone as ub
from glob import glob

#create a cli interface using clint
from clint import args
from clint.textui import puts, colored, columns, progress
import time, sys, os, select #to manage input
import Tkinter as Tk #for the timer
import datetime
import beeper #pour le bip

#Init an ub-lab
#ublab = ub.Ublab()
from multiprocessing import Process #pour les requettes mysql dans un thread.

class Recorder(object):
    """docstring for Recorder
    
    A simple recorder for a section measurement and mysql storage
    """

    def __init__(self,use_mysql=True, *sqlargs, **sqlkeys):
        
        #init ublab 
        self.ublab = ub.Ublab()

        #init a dictionnay for data
        self.data = {}

        #init a section object
        self.section = ub.Section()
        
        if use_mysql:
            import UbertoneMysql as ub_sql

            #init mysql project manager
            self.sql = ub_sql.SectionManager(*sqlargs, **sqlkeys)

        self.use_sql = use_mysql

    def new(self,name,comment):
        """docstring for new
        
        Start a new section measurement with a given name and comment
        """
        
        #create a new section in mysql
        self.sql.new_section(name,comment)

        #print the section id
        puts( colored.red("Section created with the id=%i"%self.sql.section.id) )
      
    def recover(self,id=None):
        """
        recover
        =======

        Function to set the recorder to an existing profile in mysql and
        continue to add data to this profile.

        id
        --
            default: None

            mysql id (table section_info)

            if the id is None this function display all the section saved in
                mysql

        """
       
        #set the id
        if id != None:
            self.sql.set_id(id)
            puts( colored.red("Section selected:\nid: %i\nname: %s\ncomment: %s" % ( self.sql.section.id, self.sql.section.name, self.sql.section.comment ) ) )

    def start(self, delay='1', save_type='advanced', timer=None, temperaturefile=None):
        """
        start
        =====
        
        start a new record on ublab, you can specify the delay between two
        records and the type of files stored.
        
        temperaturefile: if a file name is given the temperature is recorded from DTM
        """
        try:
            self.ublab.start_recording(delay,save_type)
        except:
            puts( colored.red("Error sending the command to ublab!" ) )
            
        if temperaturefile:
            #self.tempflag = True #flag for the temperature
            from ubertone.recordtemp import Recorder as temprec
            self.trec = temprec(temperaturefile)
            self.trec.start()
        else:
            self.trec = False
            
        if timer:
            Timer(timer)
            

    def stop(self):
        """
        stop
        ====

        stop the current recording

        """

        self.ublab.stop_recording()
        if self.trec:
            self.trec.stop()
            self.trec.receiver.close() #end the thread
            
    def save(self,position):
        """
        save
        ====

        Save and upload to mysql the current measurement at a given position.

        position
        --------
            position in the section 
        """

        #first download the data
        self.ublab.data_on_ublab(download=True)

        #then save files to a new directory
        self.ublab.data_files.save_all(str(position))

        #init a new ublab data object from libUbertone
        cur_data = ub.Data()

        #read them and upload them to mysql
        puts(colored.blue("Load data from files"))
        for f in progress.bar(glob(str(position)+"/*")):
            cur_data.load_from_udt(f)

        #upload to mysql
        if self.use_sql:
            puts(colored.blue("Start uploading to mysql"))
            p = Process(target=self.sql.add_profile, args=(cur_data, position))
            #self.sql.add_profile(cur_data,position)
            p.start()

        #remove from ublab
        puts(colored.blue("Remove on ublab"))
        self.ublab.delete_all_data()

        #Add this data to the section object
        self.section.add( cur_data, position )
        
    def get(self,position):
        """
        get
        ===

        get the data for a given positions

        """
        
        if self.use_sql:
            out = self.sql.get_profiles(position)
        else:
            out = ub.Data()
            out.load_folder(position)

        return out


    def delete(self,position):
        """
        del
        ===

        delete all data for the given position in mysql
        """

        if self.use_sql:
            puts(colored.red("Delete %s from mysql"%str(position)))
            p = Process(target=self.sql.delete_profile, args=(position,))
            p.start()
            #self.sql.delete_profile(position)



class Timer():
    
    """
        Class for setup a timer 
    """

    def __init__(self, tend):
        """
            Class Timer to set  a timer 
            
            tend is the total time in second
        """
    
        self.maxT = tend
        self.currentT = 0
        self.startT = datetime.datetime.now()
        
        #The small Tk windows
        self.root = Tk.Tk()
        self.label = Tk.Label(text="", width=22, font=("Helvetica", 32))
        self.label.pack()
        self.update_clock()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.mainloop()
    
    def quit(self):
        self.root.destroy()
        self.root.quit()
    
    def update_clock(self):
        """
            Function to run the timer
        """
        
        if self.currentT <= self.maxT:
            self.currentT += 1.0
            tnow = datetime.datetime.now() 
            self.label.configure(text="%s"%( str( tnow - self.startT ) ))
            
            #Beep each 
            self.root.after(1000, self.update_clock)
            if (self.maxT - self.currentT) <= 20:
                beeper.beeper( 440, length=500 )
        else:
            #Close the box
            self.root.destroy()
        
        

