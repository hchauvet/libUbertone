#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
File: UbertoneMysql.py
Author: Hugo Chauvet
Description: Create a bridge between ubertone data and mysql using sqlalchemy   

version: 21.05.2013
'''

from libUbertone import Data
from libUbertone import Section as ubSection
from sqlalchemy import *
from sqlalchemy.orm import *
from datetime import datetime
from dateutil.parser import parse #pour parser les dates au format text
from glob import glob
from pylab import array, vstack, reshape, shape

def array2str( array ):
    """ 
    @param 1darray: on dimensional array or list
    @return RETURN: a string with data separated by a comma
    """
    
    return  ','.join([ str(b) for b in array ]) 

#init an empty class to map on the database
class Section(object):
    pass
class Profile(object):
    pass
class Profile_data(object):
    pass
class Volume_data(object):
    pass


class SectionManager():
    """

        Class pour gerer le pont entre les donnees de l'ublab et MySQL

    """
    def __init__(self,section_id=None,dbpass='PASSWD',dbuser='USER',dbname='Ubertone',dbserv='localhost'):
        """
        
        section_id
        ----------
            id de la section dans mysql, laisser None pour creer une nouvelle
            section

        dbpass
        ------
            mot de passe de mysql

        dbuser
        ------
            utilisateur de mysql

        dbname
        ------
            nom de la base de donnees

        """

        #init connexion with mysql and map object with sqlalchemy
        #create the connexion
        self.db = create_engine('mysql://'+dbuser+':'+dbpass+'@'+dbserv+'/'+dbname)
        
        #get the name etc from the database
        #metadata = BoundMetaData(db)
        metadata = MetaData(self.db)
        
        sections = Table( 'Section_info', metadata, autoload=True )
        profiles = Table( 'Profile', metadata, autoload=True )
        profiles_data = Table( 'Profile_data', metadata, autoload=True )
        
        
        #Try to delete all mappers to be sure we can open a new connexion
        try:
            clear_mappers()
        except:
            pass
            
        #map the database and python objects
        mapper(Section,sections)
        mapper(Profile,profiles)
        mapper(Profile_data,profiles_data)
        
        
        #start the session
        self.session = create_session()

        #chargement de la section si un id est donné
        if section_id != None:

            #get the section from mysql
            try:
                self.section = self.session.query(Section).filter( Section.id == int(section_id)).one()    
            except:
                print "[ ERROR ]: No section with this id in MySQL"
                self.section = None

    def set_id(self,id_in):
        """
        Function to set self.section with the given id
        """
         #get the section from mysql
        try:
            self.section = self.session.query(Section).filter( Section.id == int(id_in)).one()    
        except:
            print "[ ERROR ]: No section with this id in MySQL"
            self.section = None

    def new_section(self,name,comment):
        """docstring for add_section
        
        This function allow to create a new section in the database

        name
        ----
        
        name of this section

        comment
        -------

        a usefull comment

        """
    
        #create an empty section object
        new_section = Section()
       
        new_section.name = name
        new_section.comment = comment
        new_section.date = datetime.now() #the current datetime

        #Add the section to mysql
        self.session.add(new_section)
        self.session.flush()

        #Select the created section as the current one
        try:
            self.section = self.session.query(Section).filter( Section.date == new_section.date ).one()
        except:
            print '[ ERROR ] Something wrong ...'
            self.section = None

    def add_profile(self,ublab_data,position):
        """
        docstring for add_profile
        
        """

        #Get existing positions
        existing_pos = self.list_positions().tolist()
        
        if position not in existing_pos:
            #loop over datetime
            for i in xrange(len(ublab_data.datetime)):
                
                
                
                #test if we the datetime already exist (it should not !)
                #print ublab_data.datetime[i]
                crapy = self.session.query(Profile).filter( Profile.id_section == self.section.id ).filter( Profile.date_time == str(ublab_data.datetime[i]) ).all()
                
                
                
                if not crapy:
                    #create a temporary profile, profile_data, volume_data

                    prf = Profile()
                    #prf_data = Profile_data()
                    #vol_data = Volume_data()
                    #fill profile info
                    prf.id_section = self.section.id
                    prf.position = position
                    prf.date_time = str(ublab_data.datetime[i])
                    prf.profondeur = ublab_data.fond[i]
                    prf.adv_configuration = str(ublab_data.config_file)

                    #Update this profile to mysql
                    self.session.add(prf)
                    self.session.flush()

                    #retrive the curent profile from mysql
                    cur_prf = self.session.query(Profile).filter( Profile.id_section == self.section.id ).filter( Profile.date_time == prf.date_time ).one() 


                    prf_data = Profile_data()
                    prf_data.id_profile = cur_prf.id
                    prf_data.depth = array2str(ublab_data.profondeur)
                    prf_data.velocity = array2str(ublab_data.vitesse[i])
                    prf_data.amplitude = array2str(ublab_data.amplitude[i])
                    prf_data.doppler_correlation = array2str(ublab_data.dopplerCorrelation[i])
                    prf_data.turbi = array2str(ublab_data.turbi[i])

                    
                    prf_data.Doppler_X = array2str(ublab_data.dopplerX)
                    prf_data.Doppler_I = array2str(ublab_data.dopplerI[i])
                    prf_data.Doppler_Q = array2str(ublab_data.dopplerQ[i])

                
                    #Add all to mysql
                    self.session.add(prf_data)
                    self.session.flush()
                else:
                    print('[ERROR!] This datetime already exist in mysql please create a new section or remove them!')
                    break
                
        else:
            print("[ERROR!] This position already exist in mysql")
            
    def get_profiles(self,position):
        """
        docstring for get_profile
        
        return all profiles for a given position in the section
        """

        #seclect
        print("Get profiles")
        profiles = self.session.query(Profile).filter( and_( Profile.position == str(position), Profile.id_section == str(self.section.id) ) ).order_by(Profile.date_time).all()
        
        #data
        print("Get profiles data")
        res = self.db.execute("SELECT D.* FROM Profile_data as D JOIN Profile as I ON D.id_profile = I.id WHERE I.position="+str(position)+" AND I.id_section = "+str(self.section.id))
        prf_data = res.fetchall()


        data_by_prof = []
        new_data = Data()

        print("Parse arrays")
        #La profondeur et la meme pour ts les profils 
        new_data.profondeur = array( prf_data[0].depth.split(',') ).astype(float)
        new_data.dopplerX = array( prf_data[0].Doppler_X.split(',')).astype(float)

        #le fond et le datetime
        new_data.fond = array( [ prof.profondeur for prof in profiles ] ).astype(float)
        new_data.datetime = array( [ parse(prof.date_time) for prof in profiles ] )
        new_data.config_file = array( [ prof.adv_configuration for prof in profiles ] )

        #init table 
        size2d_vitesse = (len(new_data.datetime), len(new_data.profondeur))
        size2d_doppler = (len(new_data.datetime), len(new_data.dopplerX))
        #print(size2d_vitesse)
    
        #print len(prf_data)
        #vitesse
        new_data.vitesse = reshape( [data.velocity.split(',') for data in prf_data] , size2d_vitesse).astype(float)

        #L'amplitude
        new_data.amplitude = reshape([ data.amplitude.split(',') for data in prf_data], size2d_vitesse ).astype(float)

        #la turbi
        new_data.turbi = reshape([ data.turbi.split(',') for data in prf_data],size2d_vitesse ).astype(float)

        #la correlation doppler
        new_data.dopplerCorrelation = reshape([ data.doppler_correlation.split(',') for data in prf_data ], size2d_vitesse ).astype(float)
        #Doppler real
        new_data.dopplerQ = reshape([ data.Doppler_Q.split(',') for data in prf_data], size2d_doppler ).astype(float)
 
        #Doppler imag
        new_data.dopplerI = reshape([ data.Doppler_I.split(',') for data in prf_data ],size2d_doppler ).astype(float)

        #print new_data.amplitude

        return new_data

    def delete_profile(self,position):
        """docstring for delete_profile
        
        delete all data for a given position

        """
        
        
        #seclect 
        profiles = self.session.query(Profile).filter( Profile.position == str(position) ).filter( Profile.id_section == str(self.section.id) ).all()
        
        #data
        prf_data = self.session.query(Profile_data).filter( Profile_data.id_profile == Profile.id ).filter( Profile.position == str(position) ).filter( Profile.id_section == str(self.section.id) ).all()
        
        #delete
        for p in prf_data:
            self.session.delete(p)
        for prof in profiles:
            self.session.delete(prof)

        #flush the session to propagate things
        self.session.flush()

        print("Delete done on mysql!")

    def list_positions(self):
        """
        Function to get all positions of the section
        """

        pos = self.session.query(Profile.position).filter( Profile.id_section == self.section.id ).distinct().all()

        return array( [float(p[0]) for p in pos ] ) 
        

    def get_all_profiles(self):
        """
            Function to get all profiles for this section
        """

        positions = self.list_positions()

        data = {}
        for p in positions:
            data[p] = self.get_profiles(p)

        return data, positions

    def get_section(self):
        """
        Fonction pour charger les donees mysql dans une classe section
        """
        positions = self.list_positions()
        sec = ubSection()
        for p in positions:
            sec.add( self.get_profiles(p), p)
            sec.profiles[-1].to_radial() #force le calcul des vitesse radiales
        return sec
        
if __name__ == '__main__':

    aa = SectionManager(6)
    data_test = aa.get_profiles(1)
    data_test.plot()
    #print data_test.config_file    
    #data, pos = aa.get_all_profiles()

    #print pos
    #print data_test.profondeur
    #print data_test.dopplerCorrelation
    
    #aa.new_section('Test','creation depuis python')
    #get data from dl files
    #test_data = Data()
    #test_data.load_folder('test')
    #Load data
    #for f in glob('/home/chauvet/Téléchargements/*.udt'):    
    #    test_data.load_from_udt(f)

    #aa.add_profile(test_data,1)

    #print test_data.dopplerI


