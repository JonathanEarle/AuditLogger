"""List of stand alone utility functions"""

import os
import psycopg2
from configparser import ConfigParser

#TODO: Couple generic errors together with a success status and error code (Can be place in a separate exception hadler)

#Generic errors used to prevent data leakage
DATABASE_ERROR = "Database Error"
INTERNAL_ERROR = "Internal Server Error"


"""Capture the configuration details stored in a file location stored in the DATABASE_INI environment variable"""
def config(filename=os.getenv('DATABASE_INI'), section='postgresql') -> dict:
    parser = ConfigParser()
    parser.read(filename)

    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
    return db

"""
Connect to the database 
@returns tuple[conection,cursor]
"""
def connect(config: dict):
    conn = psycopg2.connect(**config)
    cur = conn.cursor()
    return(conn,cur) 

"""
Disconnect from the database
@param conn: connection
@param cur: cursor
"""
def disconnect(conn,cur):
    cur.close()
    conn.close()


"""Places each element of a tuple in a list of tuples into a dictionary where the keys are based on the labels list"""
def label_rows(labels:list, rows:list[tuple]):
    labeled = []
    for row in rows:
        tmp ={}
        for i,j in zip(labels,row):
            tmp[i]=j
        labeled.append(tmp)
    return labeled

"""Dictionary update method where the updated dictionary is returned"""
def update(values:dict, updates:dict):
    values.update(updates)
    return values
