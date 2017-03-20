# libUbertone
This is a set of python codes to interact with the UB-Lab controller of acoustic Doppler profiler from the UBERTON company. It was built for measurement of river transverse section.

# Installation

Their is 3 main files: 

* **libUbertone.py**, contains all main classes to read and write XML data from the UB-Lab and to use the network to directly interact with the UB-Lab interface (view live information, download data, etc...)

* **UbertoneMysql.py**, makes the link between MySQL database and data managed by **libUbertone**

* **Recoder.py**, allows to record measurements for a given amount of time.

* **Ubertone.sql**, contains the MySQL database schema to install the Ubertone database.

## Requirement

The following python libraries are required:

* pylab (numpy/scipy)
* matplotlib
* clint
* BeautifulSoup
* lxml
* sqlalchemy (if you want to store data in MySQL)

## Setup MySQL database 

1. Open mysql terminal and create the Ubertone database 

    ```bash
    mysql -uUSER -p
    create database Ubertone;
    ```
2. Load the database Structure to the Ubertone database 

    ```bash
    mysql -uUSER -pPASSWORD Ubertone < Ubertone.sql
    ```
    
### Database Structure
![Database structure](https://github.com/hchauvet/libUbertone/raw/master/img/baseUbertone.jpg "Schema of mysql database")


# Live view of data 

It is possible to view data acquired from UBLAB directly into matplotlib figure


```python
#Import ubertone library
import libUbertone as ub
   
#Initialise the Ublab class which controls the Ublab
lab = ub.Ublab()

#Start live plot
lab.LivePlot()
```

# Record data for a given period

This code send the record command to the Ub-lab, display a countdown until the end of the record and finally download data from Ub-lab, and optionally send them to MySQL database.

```python

#Import the recorder
from recorder import Recorder

#If we want to import data to mysql we need to set the user and password of mysql server.
rec = Recorder(use_mysql = True, dbuser='toto', dbpass='tata')

#If you don't want to store data to mysql
#rec = Recorder( use_mysql=False )

#If it's a new section of river
rec.new('Name of the river section', 'A useful comment')

#If you want to work on an existing river section (example id=6)
#rec.recover( id=6 )

#To delete a previous position in the section
#rec.delete( position = 0.1 )


#Run the measurement for a given amount of seconds (here 5 mintutes)
rec.start( timer = 5*60 )

#Stop measurement
rec.stop()

#Save the measurement to a given position in the river section
rec.save( position = 0.1 )

#To shutdown the Ublab
rec.ublab.shutdown()
```

# Work with data of a river cross-section

If data are stored in a folder, sub-folder names correspond to the position in the river cross-section. 

```python
import libUbertone as ub

#Path to the folder containing cross-secion data
path = './to/crosssection/folder/'

#Init the ublab section class
sec = ub.Section()

#Load data 
sec.load_section_folder( path )

#We can now print the first vertical velocity profile of the cross-section
print sec.profiles[0].vitesse

#We could also plot them
sec.profiles[0].plot()

#Or print the mean velocity cross-section profile
sec.plot()

#we could get array of these mean velocity
y_position, mean_depth, mean_velocity = sec.process()
```

# Load data stored in a folder to MySQL

Here is an example on how to load data that have been stored to a folder into a MySQL database.

```python
import libUbertone as ub
#Path to the data folder
path = './to/my/crosssection/data'

#Init Section class
sec = ub.Section()

#Load datat from folder
sec.load_section_folder( path )

#Upload the to mysql
#With user 'toto' et passwird 'tata'
sec.UploadToSql( 'Cross-section name',
    'Some comments',
    dbpass='tata',
    dbuser='toto')
```


# Load data from MySQL

```python

from UbertoneMysql import SectionManager

#Start the section Manager class and load river 
#cross-section stored with the id 6
sql_sec = SectionManager( 6, dbuser='toto', dbpass='tata')

#Load the section data to python
sec = sql_sec.get_section()

#Plot the mean velocity of the river cross-section
sec.plot()
```



