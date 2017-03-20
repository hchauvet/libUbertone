#!/usr/bin/python
# -*- coding: utf-8 -*-

# Library to deal with UB-LAB
#
# Author: Hugo Chauvet 
#
# Version: 29.08.2013 2

import pylab as m
from BeautifulSoup import BeautifulSoup #to play with xml files
from xml.dom.minidom import Document #to create xml files
import httplib
import urllib2
from datetime import datetime
from glob import glob
from dateutil import parser
import os
from time import sleep

#with progress bar
from clint.textui import progress

class TimeSerie():
    """docstring for TimeSerie

    store all data, allow to manipulate time series like get mean values
    """

    def __init__(self):

        #Init list to store data objects
        self.timedata = [] 

    def add(self,new_data):
        """
        add a data object to the timedata list
        """
        self.timedata.append(new_data)

    def mean(self):
        """
            Compute the mean for the velocity
        """

        return m.mean(self.velo_array(),0)

    def velo_array(self):
        """docstring for velo_array

        Compute a 2D array with all velocity profiles
        """

        return m.vstack([data.vitesse_inst for data in self.timedata])

class Section():
    """docstring for Section
    
    This class is for manage data for a section measurement
    
    """
 
    def __init__(self, verbeux=False):

        #init list of profiles
        self.profiles = []
        #list of positions of each profiles
        self.positions = []
        self.verbeu = verbeux

    def add(self,prof_data,position):
        """docstring for Add
        
        Use this function to add a Data object to the profiles list
        """

        self.profiles.append( prof_data )
        self.positions.append( position )


    def save_last(self,name_out):
        """
        save the last profile
        
        """
        pass
        
    def save(self,name_out,fmt='xml'):
        """docstring for save
        
        save the section to a file 

        fmt
        ---

        * 'xml' (default)
          allow to save as an xml file

        """

        def a2str(array):
            """docstring for A2str
            
            Transform numpy array to nice string

            """
            

            if array != None:
                if len(m.shape(array)) == 2:
                    tmp = '\n'.join([str(array[i,:]).replace('[','').replace(']','').replace('\n','') for i in xrange(m.shape(array)[0])])
                else:
                    tmp = str(array).replace('[','').replace(']','').replace('\n','')

            else:
                tmp = str(None)
           
            return tmp
    
        #Create the document
        out_doc = Document()

        body = out_doc.createElement('body')
        out_doc.appendChild(body)

        #Create a loop on profiles list
        for prof,pos in zip(self.profiles,self.positions):
            
            ######## INIT XML KEYS #######################

            #create the profile element
            xml_prof = out_doc.createElement('profile')
            body.appendChild(xml_prof)

            #create keys for all datas
            xml_data = {}
            for i in ['position','advp-config','vitesse','amplitude','profondeur','datetime','fond','turbi','dopplerCorrelation','dopplerX','dopplerI','dopplerQ','dopplerX']:

                #create the element in the dict
                xml_data[i] = out_doc.createElement(i)
                xml_prof.appendChild(xml_data[i])
                
                if i not in ['position','advp-config','datetime']:
                    xml_data[i].appendChild(out_doc.createTextNode(a2str(getattr(prof,i))))

            ##############################################

            #Store exeptions data
            xml_data['position'].appendChild(out_doc.createTextNode(str(pos)))
            xml_data['advp-config'].appendChild(out_doc.createTextNode(str(prof.config_file)))

            #for datetime
            xml_data['datetime'].appendChild(out_doc.createTextNode('\n'.join([str(d) for d in prof.datetime])))
        if name_out == '':
            print out_doc.toprettyxml(indent='    ')
        else:
            f = open(name_out,'w')
            f.write(out_doc.toprettyxml(indent='  '))
            f.close()

    def load_section_folder ( self, section_folder, return_delimiter='r' ):
        """ Function doc 
        #Function to load a folder containing severals subfolder for each positions in the cross-section

        - return delimiter:
            if a given sign is given for wayback measurement lire 'r'. 
            expl:
                0.01r 
            
            This tels the function to remove the return_delimiter char.
            
        ## Exemple of folder organisation
            /My_section
                |- 0.01/
                |- 0.25/
                
           Folder names 0.01 and 0.25 are the positions. They cointain xml files of ublab for each measurements.
           
           To load this section
           
           sec = Section()
           sec.load_section_folder('./My_section')
           
        """
        
        #list all subfolders 
        for f in glob( section_folder+"*" ):
            if os.path.isdir( f ):
				posi = f.split('/')[-1]
				if self.verbeu:
					print posi
                #remove the return sign
				if return_delimiter in posi:
					posi = posi[:-len(return_delimiter)]
				
				data = Data()
				data.load_folder( f )
				
				self.add( data, posi )
				

    def process(self, projected=False):
        """
            process data to get a 2d masked array with velocity
        """
        
        #mask data
        for data in self.profiles:
            data.mask_below_bottom()
            
        #sort postions
        isort = m.argsort( self.positions )

        #sort data and position lists
        ndata = m.array(self.profiles)[ isort ]
        npos = m.array(self.positions)[ isort ].astype(float) 
        
        
        #merge all data in one table
        if not projected:
            all_velo = m.ma.vstack([ m.mean(d.vitesse_radial, 0) for d in ndata]).T
            fond = m.array( [ m.mean(d.fond_radial) for d in ndata  ] )
        else:
            all_velo = m.ma.vstack([ m.mean(d.vitesse,0) for d in ndata]).T
            fond = m.array( [ m.mean(d.fond) for d in ndata  ] )
            
        return npos, fond, all_velo
        
    def plot(self, projected = False):
        """
            Plot the section 
        """
        
        
        npos, fond, all_velo = self.process(projected)
        
        m.figure()
        m.pcolormesh(npos, -self.profiles[0].profondeur,all_velo)
        m.colorbar()
        m.plot(npos, -fond, 'k-', lw=2)
        m.axis('equal')
    
    def clean_and_mask(self):
        
        for data in self.profiles:
            data.clean_zeros()
            data.mask_below_local_botom()
        print("[Data cleaned] remove values between -1e-4 bnd 1e-4")
    
    def UploadToSql(self, nom, description, *sql_args, **sql_keys):
        """ 
            Fonction pour charger une section entiere dans MySQL
            Avec le nom et la description
            
            **kwargs pour gerer les options de connexions sql
        """
        import UbertoneMysql as ub_sql

        #init mysql project manager
        sql = ub_sql.SectionManager(*sql_args, **sql_keys)
        
        #creation de la nouvelle section
        sql.new_section( nom, description)
        print("Section created with the id=%i"%sql.section.id)
        #Sort by position 
        ii = m.argsort( self.positions )
        
        #Load each profiles
        for data, pos in zip(m.array(self.profiles)[ii], m.array(self.positions)[ii]):
            print("Upload position %s"%pos)
            sql.add_profile( data, float(pos) )
            
class Data():
    """Class to store data of UB-LAB"""

    def __init__(self,xmlfile=None):

        #init variables
        self.vitesse = None
        self.amplitude = None
        self.profondeur = None
        self.dopplerI = None
        self.dopplerQ = None
        self.dopplerCorrelation = None
        self.dopplerX = None
        self.turbi = None
        self.fond = None
        self.datetime = None
        
        #Data for conversion to radial coordinate
        self.vitesse_radial = None
        self.fond_radial = None
        self.profondeur_radial = None
        
        #Config variable
        self.config_file = None

        #Open the file and parse them if a name is given
        if xmlfile != None:
            self.file_in = xmlfile
            self.parse_from_xml()
            

    def parse_from_xml(self):
        """
        docstring for parse_from_xml

        Parse single file from UB-LAB    
        """

        #f = open(self.file_in,'r')
        parsed_data = BeautifulSoup(self.file_in)
        #f.close()

        #La profondeur 
        self.fond = float(parsed_data.level.contents[0])

        #le temps
        self.mesure_time = parsed_data.date.contents[0]

        #Les donnees de vitessses
        temp = m.vstack( [ m.fromstring(s,sep='\t') for s in
            parsed_data.profile.contents[0].split('\n') if s != '' ] )

        self.profondeur = temp[:,0]
        self.vitesse_moy = temp[:,1]
        self.vitesse_inst = temp[:,2]
        self.amplitude = temp[:,3]

        #Les donnees doppler
        temp = m.vstack( [ m.fromstring(s,sep='\t') for s in
            parsed_data.profile.contents[0].split('\n') if s != '' ] )

        self.dopplerX = temp[:,0]
        self.dopplerI = temp[:,1]
        self.dopplerQ = temp[:,2]

    def load_from_udt(self,udtfile):
        """Load data from dir 
        
        Load downloaded data from a given dir
        """
        

        if ".udt" in udtfile:
        
            #load txt file
            tmp_data = m.loadtxt(udtfile,delimiter='\t',dtype='S')
            
            #need to add comments line (the first one) 
            com = open(udtfile,'r').readline()
            com = m.array( com.strip().split('\t') )

            tmp_data = m.vstack( [ com, tmp_data ] )

            #Vrai pour ts les fichiers
            #Le temps
            if self.datetime == None:  
                if 'level-mean' not in udtfile:
                    self.datetime = [ parser.parse( s[0]+'-'+s[1] ) for s in tmp_data[1:,:2] ]
    
            #for velocity file
            if 'velocity' in udtfile:
                
                #first line and skip the two first rows and you get the measurements
                #levels
                if self.profondeur == None:
                    self.profondeur = m.array( [ float(s) for s in tmp_data[0,2:] ] )
    
                #les vitesses
                self.vitesse = m.vstack( tmp_data[1:,2:].astype('float32') )
    
            if 'amplitude' in udtfile:
    
                #Si pas de profondeur deja chargé
                if self.profondeur == None:
                    self.profondeur = m.array( [ float(s) for s in tmp_data[0,2:] ] )
    
                self.amplitude = m.vstack( tmp_data[1:,2:].astype('float32') )
    
            if 'level-mean' in udtfile:
    
                self.fond = tmp_data[1:,3].astype('float32')
    
            if 'turbi' in udtfile:
                
                self.turbi = m.vstack( tmp_data[1:,2:].astype('float32') )
    
            if 'r0_' in udtfile:
    
                self.dopplerCorrelation = m.vstack( tmp_data[1:,2:].astype('float32') )
    
            if 'q_' in udtfile:
    
                if self.dopplerX == None:
                    self.dopplerX = m.array( [ float(s) for s in tmp_data[0,2:] ] )
    
                self.dopplerQ = m.vstack( tmp_data[1:,2:].astype('float32') )
    
            if 'i_' in udtfile:
                if not 'turbi_' in udtfile:

                    if self.dopplerX == None:
                        self.dopplerX = m.array( [ float(s) for s in tmp_data[0,2:] ] )
        
                    self.dopplerI = m.vstack( tmp_data[1:,2:].astype('float32') )

        #pour la configuration
        if '.ucf' in udtfile:
            tmp = open(udtfile,'r')
            self.config_file = tmp.read()
            tmp.close()

    def to_radial( self ):
        """ 
        Function to project data to radial velocity and correct bottom and profondeur
        """
        
        #get the angle given used to project the velocity
        phi = self.get_angle()
        
        #Project velocity
        self.vitesse_radial = m.cos( m.deg2rad( phi ) ) * self.vitesse.copy()
        
        #Project bin mapping and bottom
        self.profondeur_radial = self.profondeur.copy() / m.sin( m.deg2rad( phi ) )
        self.fond_radial = self.fond.copy() / m.sin( m.deg2rad( phi ) )
        
    def plot(self, component='vitesse', projected=False, autoshow=True):
        """docstring for plot
        
        plot the data

        autoshow
        --------
         if true add m.show() at the end 

         if false return the figure object
        """
       
        #Manage data to be plotted
        
        timeserie = getattr(self,component).copy()

        f = m.figure(figsize=(12,4))
        
        #axe pour le profil vertical
        ax1 = m.axes([0.1,0.15,0.2,0.8])
        #axe pour les donnees en temps
        ax2 = m.axes([0.4,0.15,0.56,0.8])
        
        ax1.set_xlabel(component+' moyenne')
        ax1.set_ylabel('profondeur')

        ax2.set_xlabel('temps')
        ax2.set_ylabel(component)
        
        #for ticks display
        #ax1.locator_params(nbins=4)

        if not projected:
            #On converti les donnees
            self.to_radial()

            if component == 'vitesse':
                data = self.vitesse_radial
            else:
                data = timeserie
                
            z_beam = self.profondeur_radial
            fond_beam = self.fond_radial
            
        else:
            data = timeserie
            z_beam = self.profondeur
            fond_beam = self.fond

        ax1.errorbar(m.mean(data,0), -z_beam, xerr=m.std(data,0)/m.sqrt(len(self.datetime)), fmt='ro--', ms=10, picker=5)
        tserie, = ax2.plot_date(self.datetime,data[:,0],'b-',lw=2)
        cur_selected, = ax1.plot([],[],'ko',ms=10)

        if self.fond != None and m.mean(self.fond)!= 0.:

            #check if angle is there
            if not projected:
                fond_m_beam = m.mean( self.fond_radial )
            else:
                fond_m_beam = m.mean(self.fond)

            ax1.plot(ax1.get_xlim(),[-fond_m_beam,-fond_m_beam],'k--',lw=2,label='fond',picker=5)
            #print self.fond
            ax1.set_ylim(-(fond_m_beam+0.1*fond_m_beam), 0)

        def onpick(evt):
            #test si on clique sur une ligne
            if isinstance(evt.artist, m.Line2D):
                #print evt.artist.get_label()

                if evt.artist.get_label() == 'fond':
                    tserie.set_data(self.datetime,fond_beam)
                    ax2.set_ylim(min(fond_beam),max(fond_beam))
                    ax2.set_xlim(self.datetime[0],self.datetime[-1])

                else:
                    ind = max(evt.ind)
                    tserie.set_data(self.datetime,data[:,ind])
                    ax2.set_ylim(min(data[:,ind]),max(data[:,ind]))
                    ax2.set_xlim(self.datetime[0],self.datetime[-1])
                

                    cur_selected.set_data(m.mean(data,0)[ind],-z_beam[ind])

                ax1.figure.canvas.draw()
                ax2.figure.canvas.draw()
                #print(self.vitesse[:,ind],ind)

        f.canvas.mpl_connect('pick_event',onpick)

        if autoshow:
            m.show()
        else:
            return f

    def get_angle(self):
        """
        Function return the angle set to record velocities. 
        """
        angle = None

        if self.config_file != None:
            XML = BeautifulSoup(self.config_file[0])
            angle = float(XML.meca.beta_tr1.contents[0])
        
        return angle

    def load_folder(self,folder_name):
        
        #Reset all variables 
        self.__init__()

        for f in glob(folder_name+'/*'):
            self.load_from_udt( os.path.abspath(f) )

        #load the configuration file
        self.config_file = []
        for c in glob(folder_name+'/*.ucf'):
            conf = open( os.path.abspath(c) ,'r').read()
            self.config_file.append(conf)

        #convert to radial velocity
        self.to_radial()
        
    def plot_quality(self):
        """
            Function to plot 'quality' of doppler signal

            I = sqrt( dopplercorr / |ampl - dopplercorr|)

            I < 1 : Not good (see ublab data.js)
        """

        m.figure()

        m.pcolormesh( m.array(range(len(self.datetime))), -self.profondeur, m.ma.masked_less_equal( m.sqrt( self.dopplerCorrelation ) / abs( self.amplitude - m.sqrt( self.dopplerCorrelation ) ), 1 ).T )
        m.colorbar()

        m.show()

    def mask_below_bottom(self):
        """ 
        
        #Function to mask data which are below the river bottom.
        It return a masked array of data
            
        """
        
        #test if there is a bottom in the data
        if self.fond != None:
            #create local bottom mask 
            self.mask_below_local_botom()
            
            #Find indices where profondeur is less than mean bottom and mask it
            
            pp, tt = m.meshgrid( self.profondeur, m.zeros( m.shape(self.datetime) ) )
            
            #for the velocity
            self.vitesse = m.ma.masked_where( pp > m.mean( self.fond ), self.vitesse, copy=True )
            
            #for the doppler
            self.amplitude = m.ma.masked_where( pp > m.mean( self.fond ), self.amplitude, copy=True )
            
            #for the profondeur 
            self.profondeur = m.ma.masked_where( self.profondeur > m.mean( self.fond ), self.profondeur, copy=True )
            
            if self.vitesse_radial != None:
                pp, tt = m.meshgrid( self.profondeur_radial, m.zeros( m.shape(self.datetime) ) )
                self.vitesse_radial = m.ma.masked_where( pp > m.mean( self.fond_radial ), self.vitesse_radial, copy=True )
                
            if self.profondeur_radial != None:
                self.profondeur_radial = m.ma.masked_where( self.profondeur_radial > m.mean( self.fond ), self.profondeur, copy=True )
                
        else:
            print("No bottom found!")

    def mask_below_local_botom(self):
        """
            Function to mask data below the local (not time averaged) bottom value
        """
        mask = m.zeros_like( self.vitesse ) 
        mask_radial = m.zeros_like( self.vitesse_radial )
         
        for i in xrange( len(self.datetime) ):
            mask[i, m.find(self.profondeur<= self.fond[i])] = 1
            if self.vitesse_radial != None:
                mask_radial[i, m.find(self.profondeur_radial <= self.fond[i]) ] = 1
                
        #Apply masks    
        self.vitesse = m.ma.masked_where( mask == 0, self.vitesse, copy=True)
        self.amplitude = m.ma.masked_where( mask == 0, self.amplitude, copy=True )
        
        if self.vitesse_radial != None:
           self.vitesse_radial = m.ma.masked_where( mask_radial == 0, self.vitesse_radial, copy=True )
 
    def clean_zeros(self):
        """
            mask all zeros values
        """
        pval = 1e-4
        mval = -1e-4
        
        self.vitesse = m.ma.masked_inside( self.vitesse, mval, pval,  copy=True)
        self.amplitude = m.ma.masked_inside( self.amplitude, mval, pval, copy=True )
        if self.vitesse_radial != None:
           self.vitesse_radial = m.ma.masked_inside( self.vitesse_radial, mval, pval, copy=True )
           
class FileManager():
    """docstring for FileManager
    
    Class to manage recorded files on the ub-lab

    xml_file
    --------

    XML content from the ub-lab containing the file tree

    """
    
    def __init__(self,xml_file=None):
        
        if xml_file != None:

            #Use beautifulsoup to parse the xml data
            self.fileXML = BeautifulSoup(xml_file)

            #build file tree
            self.from_xml()
        
    def from_xml(self):
        """    
        Create list of files from .xml file download from ub-lab
        """
        
        #Extract dir name on the ub-lab
        self.dir_name = self.fileXML.dir['name']
        
        #init list of files dict {'name','date','size'}
        self.files = []
        for f in self.fileXML.findAll('file'):
            tmp_name = f['name']
            self.files.append({'name':tmp_name,'date':'0000','size':f['size']})

    
    def download_one (self,file_dict):
        """
            Function to download the given file_dict
        """

        #start connexion
        conn = httplib.HTTPConnection('192.168.88.1:8080')
        #the request
        conn.request("GET", self.dir_name[2:]+file_dict['name'])
        r1 = conn.getresponse()


        if r1.status == 200:
            data = r1.read()
        else:
            data = None
            print r1.status, r1.reason

        #Close the connexion
        conn.close()

        file_dict['content'] = data

    def download_all(self):
        """
            download_all

            Function to download all data present on the ub-lab and set
            self.files.content with each file content (no save)

            To save file to disk, use the save_all function
        """

        kb_tot = m.sum([float(f['size'][:-2]) for f in self.files])

        print("Download %i files | %0.2f"%(len(self.files),kb_tot))
        for f in progress.bar(self.files):
            #print('download file %s'%f['name'])
            self.download_one(f)

    def save_all(self,folder):
        """
            Function to save all contents of self.files to a given folder

            folder
            ------
            
            name or path/name of folder where you want to save files. If it
            does not exist, it is created.
        """

        if not os.path.exists(folder):
            
            #create the directory
            os.makedirs(folder)
            print("Save files content to folder %s"%folder)
            for f in progress.bar(self.files):
                out = open(folder+'/'+f['name'],'wb')
                out.write(f['content'])
                out.close()

class Ublab():
    """docstring for Ublab

    Class to connect to an UB-LAB

    TODO
    ----
    - Sent configuration file 
    - start record #Done self.start_recording() H. Chauvet

    """

    def __init__(self, url='192.168.88.1:8080'):

        self.url = url

        #refresh rate (sur l'interface www vaut 2000)
        self.refresh_rate = 2000

    def get_from_www(self,page):
        """docstring for get_from_www
        
        Retrive data from ub-lab www interface
        """
        
        #start connexion
        conn = httplib.HTTPConnection(self.url)
        #the request
        conn.request("GET", page)
        r1 = conn.getresponse()


        if r1.status == 200:
            data = r1.read()
        else:
            data = None
            print r1.status, r1.reason

        #Close the connexion
        conn.close()

        return data

    def send_to_www(self,page,data):
        """
        Send xml data to ubertone www app
        """
        
        #request
        req = urllib2.Request('http://'+self.url+page,data)
        req.add_header("Content-type","text/xml ; charset=utf-8")

        #connexion
        post = urllib2.urlopen(req)
        #print post.read()
        post.close()

        #h = httplib.HTTPConnection(self.url)

        #headers = {"Content-type": "text/xml ; charset=utf-8"}

        #h.request('POST', page, data, headers)

        #r = h.getresponse()

        #print r.read()
        #get the server response
        #rep = conn.getresponse()
        #print rep.status, rep.reason
        #close connexion
        #conn.close()

    def GetData(self,time):
        """docstring for GetData

        Allow to get xml data for a given time

        time
        ----

        time is a str time format DD/MM/YYYY-HH/MM/SS
        """

        tmp = self.get_from_www("/data/measurements.ucf?"+time)

        if  tmp != None:
            self.data = Data(tmp)
        else:
            self.data = None


    def GetConfig(self):
        """docstring for GetConfig

        Get the configuration file from ub-lab www
        data/config.ucf
        """

        tmp = self.get_from_www("/data/config.ucf")
        if tmp != None:
            #parse the xml file with beautifulsoup
            self.config = BeautifulSoup(tmp)
        else:
            self.config = None

        if self.config != None:

            #store beta (angle between vproj(beam axis) et v
            self.config_beta1 = float(self.config.meca.beta_tr1.contents[0])
            
            #Savoir si on doit detecter le fond
            if self.config.h_detect.contents[0] == "true":
                self.config_fond_detect = True
            else:
                self.config_fond_detect = False


    def LivePlot(self):
        """
        LivePlot
        ========

        Use this function to plot live measurement of UB-LAB
        """

        #Get the config file
        self.GetConfig()

        #Init the figure
        fig = m.figure()
        velo_m, = m.plot([],[],'r--',label='V proj moy')
        velo_i, = m.plot([],[],'ro',label='V proj inst')
        ampli, = m.plot([],[],'c-',label='Amplitude')
        
        print self.config_fond_detect
        if self.config_fond_detect:
            prof, = m.plot([],[],'k--',label='Fond')
        
        velo_bm, = m.plot([],[],'g--',label='V beam moy')
        velo_bi, = m.plot([],[],'go',label='V beam inst')
        velo_total_mean, = m.plot([],[],'b',lw=2,label='moyenne de V en temps')

        m.legend(loc="upper center",ncol=3)
        tt = TimeSerie()

        #Update figure
        def update_plot(axes):
            print "updating"

            #create a timestanp
            t = datetime.now()
            #creation de la requeste temporelle
            t_request = t.strftime('%d/%m/%Y-%H/%M/%S')
            print t_request
            self.GetData(time=t_request)

            if self.data != None:
                #Update Time serie
                tt.add(self.data)
                
                if self.config_fond_detect:
                    i_lim = m.find(self.data.profondeur < self.data.fond)[-1] + 1

                else:
                    i_lim = len(self.data.profondeur)

                velo_m.set_data(self.data.vitesse_moy[:i_lim],self.data.profondeur[:i_lim])
                velo_i.set_data(self.data.vitesse_inst[:i_lim],self.data.profondeur[:i_lim])

                velo_bm.set_data(self.data.vitesse_moy[:i_lim]*m.cos(m.deg2rad(self.config_beta1)),self.data.profondeur[:i_lim])
                velo_bi.set_data(self.data.vitesse_inst[:i_lim]*m.cos(m.deg2rad(self.config_beta1)),self.data.profondeur[:i_lim])

                velo_total_mean.set_data(tt.mean()[:i_lim],self.data.profondeur[:i_lim])

                ampli.set_data(self.data.amplitude,self.data.profondeur)
                lims = (min([min(i) for i in [self.data.vitesse_inst,self.data.vitesse_moy]]),max([max(i) for i in [self.data.vitesse_inst,self.data.vitesse_moy]]))

                if self.config_fond_detect:
                    prof.set_data(lims,(self.data.fond,self.data.fond))

                axes.set_xlim(lims)
    
                if self.config_fond_detect:
                    axes.set_ylim(0,self.data.fond+0.3*self.data.fond)

                axes.set_title(self.data.mesure_time)
                axes.figure.canvas.draw()

        # Create a new timer object. Set the interval 500 milliseconds (1000 is default)
        # and tell the timer what function should be called.
        timer = fig.canvas.new_timer(interval=self.refresh_rate)
        timer.add_callback(update_plot, m.gca())
        timer.start()
        m.show()

    def get_recording_status(self):
        """
        Function to get the status of the recording from  ub-lab www
        """

        tmp = self.get_from_www("data/save.ucf")
        if tmp != None:
            self.saveXML = BeautifulSoup(tmp)
        else:
            self.saveXML = None

        #print self.saveXML
        #Set recording status
        if 'no' in self.saveXML.saving.contents[0]:
            self.recording = False
        else: 
            self.recording = True

    def start_recording(self, delay='1', save_type='advanced'):
        """
        StartRecording
        ==============

        Function to start recording on Ub-Lab with the current configuration

        delay
        -----
            the time between two records, minimum is 1

        save_type
        ---------
            set the measurement type 
                advanced, medium, basic

        """
        
        #dumb check
        if int(delay) < 1:
            delay = '1'

        if save_type not in ['basic','medium','advanced']:
            print("unknow save_type %s. I put save_type=basic for you"%save_type)
            save_type = 'basic'

        #Check recording status
        self.get_recording_status()
        
        #Change config to start
        #print self.saveXML.saving.contents[0]
        if not self.recording:
            #set saving to yes
            self.saveXML.saving.contents[0].replaceWith(u'yes')
        
            #set recording
            self.saveXML.interval.contents[0].replaceWith(u'%s'%delay)

            #set type
            self.saveXML.type.contents[0].replaceWith(u'%s'%save_type)
        

        print self.saveXML

        #On envoie la demande d'enregistrement
        self.send_to_www("/data/save.ucf",str(self.saveXML).replace('\n',''))
        

    def stop_recording(self):
        """

        Stop the curent record
        """

        #get the recording status
        self.get_recording_status()

        if self.recording:
            self.saveXML.saving.contents[0].replaceWith(u'no')

        #Send the request
        self.send_to_www("/data/save.ucf",str(self.saveXML).replace('\n',''))


    def data_on_ublab (self,download=False):
        """
        Function to retrieve recorded data list from ub-lab www
        """
        
        tmp = self.get_from_www("dir_list.ucf")
        
        #print tmp 

        if tmp != None:
            self.data_files = FileManager(tmp)
        else:
            self.data_files = None

        if self.data_files != None and download:

            self.data_files.download_all()              

    def get_space_left(self):
        """
            get space left on ub-lab
        """
        tmp = self.get_from_www("size.ucf")

        #print tmp
        if tmp != None:
            tmp = BeautifulSoup(tmp)
            self.space_left = tmp.space_left.contents[0]
        else: 
            self.space_left = None


    def delete_all_data(self):
        """
        Delete all data on the ub-lab

        need to have a self.data_files.fileXML
        """

        #we just have to change <dir name="./record/"> to <div name="record/trash">
        self.data_files.fileXML.dir['name'] = u'record/trash'

        #then send to ub-lab
        #print str(self.data_files.fileXML)

        #Need to check xml file and to build one like test_file_for_trash
        self.send_to_www('/data/trash.ucf',str(self.data_files.fileXML).replace('\n',''))

        #get the site
        tmp = self.get_from_www('/trash.ucf')

        #if tmp != None:
         #   print tmp

    def shutdown(self):
        """
        Function to shutdown the ublab correctly

        """

        #need the file system.ucf
        tmp = self.get_from_www('data/system.ucf')

        if tmp != None:
            
            #parse the file
            tmpXML = BeautifulSoup(tmp)

            #set command to halt
            tmpXML.command.contents[0].replaceWith(u'halt')

            print tmpXML

            #send the halt command
            self.send_to_www('/data/system.ucf',str(tmpXML))
            
            print("Attendez en gros une minute avant de débranche l'instrument")

            for i in progress.dots(xrange(60)):
                sleep(1)

            print("Vous pouvez débrancher l'ublab")
            
if __name__ == '__main__':

    def Testplot(data):

        m.plot(data.vitesse_inst,data.profondeur,'ro')
        m.plot(data.vitesse_moy,data.profondeur,'b--')
        m.plot(data.amplitude,data.profondeur,'g-') 
        "Ajout du fond"
        lims = m.xlim()
        m.plot(lims,(data.fond,data.fond),'k--')

        m.title(data.mesure_time)

        m.figure()
        m.plot(data.dopplerX,data.dopplerI)
        m.plot(data.dopplerX,data.dopplerQ)

    def test1():
        file_name = '/home/chauvet/developpement/ubertone/test_data.xml'

        test = Data(open(file_name,'r').read())

        Testplot(test)


    def test2():
        test = Ublab()

        test.GetData(time='')

        Testplot(test.data)

    def test3():
        test = Ublab()
        test.LivePlot()
    
    def test4():
        #TEST de lecture des fichiers de donnees

        #Load data
        test = Data()
        for f in glob('./0.001/*'): 
            test.load_from_udt(f)

            
        #Add a section point
        #sec = Section()
        #for x in xrange(10):
        #    sec.add(test,x)

        #sec.save('test.xml')
        #print test.config_file
        test.plot()


    def test5():
        test = Ublab()
        test.data_on_ublab(download=True)
        #test.data_files.save_all("test")
        test.get_space_left()
        print test.space_left
        
        #test.shutdown()
        #test de la supression
        #test.delete_all_data()

    test5()

  
