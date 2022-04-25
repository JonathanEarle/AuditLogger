import os
import psycopg2
from configparser import ConfigParser

DATABASE_ERROR = "Database Error"
INTERNAL_ERROR = "Internal Server Error"


def config(filename=os.getenv('DATABASE_INI'), section='postgresql'):
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

def connect(config):
    conn = psycopg2.connect(**config)
    cur = conn.cursor()
    return(conn,cur) 

def disconnect(conn,cur):
    cur.close()
    conn.close()

def label_rows(labels:list, rows:list):
    labeled = []
    for row in rows:
        tmp ={}
        for i,j in zip(labels,row):
            tmp[i]=j
        labeled.append(tmp)
    return labeled

def update(values:dict, updates:dict):
    values.update(updates)
    return values
