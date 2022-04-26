from events import Event
from psycopg2 import DatabaseError
from utils import connect,disconnect,label_rows,update,DATABASE_ERROR


class EntityType(Event):
    ENTITY_TYPE_NAME = 'audit_metadata'
    ENTITY_INSTANCE_NAME = 'main_entity_editor'

    def __init__(self, db_config, user):
        super().__init__(db_config, user)

    def add_entity_type(self, data):
        name = data.get('name')
        event_details = {'event_type':'create_entity','entity_type':self.ENTITY_TYPE_NAME,'success':False,'attrs':data,'entity_name':self.ENTITY_INSTANCE_NAME}
        
        mssg = 'Missing entity name parameter'
        self._validate_event_parameter(name,mssg,update(event_details,{'notes':mssg}))

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("""INSERT INTO entity_types(name,creator) VALUES(%s,%s)
            ON CONFLICT ON CONSTRAINT entity_types_name_creator_key DO NOTHING RETURNING id""",(name,self._user))

            mssg = "Entity {0} Already Exists".format(name)
            self._validate_event_parameter(cur.fetchone(),mssg,update(event_details,{'notes':mssg}))

            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        return self.add(update(event_details,{'notes':"Entity Added",'success':True}))
           

    def edit_entity_events(self, entity_type_name, data):  
        to_add = data.get('to_add') or []
        to_remove = data.get('to_remove') or []
        invalid_adds = 0

        event_details = {'event_type':'edit_entity_events','entity_type':self.ENTITY_TYPE_NAME,'success':False,'invalid_adds':0,'to_add':to_add,'to_remove':to_remove,'entity_name':self.ENTITY_INSTANCE_NAME}

        if not (isinstance(to_add,list) or isinstance(to_add,list)):
            mssg = "Events must be in a comma separated list"
            self.add(update(event_details,{'notes':mssg}))
            raise Exception(mssg,False,400)
        
        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("SELECT id FROM entity_types WHERE name = %s AND creator = %s", (entity_type_name,self._user))
            result =  cur.fetchone()
            
            mssg = "Attempt to modify events of entity {0}, which does not exist".format(entity_type_name)
            self._validate_event_parameter(result,mssg,update(event_details,{'notes':mssg}))
            entity_id = result[0]

            query_params = []
            query = "INSERT INTO entity_events(entity_type,event_type)VALUES"
            
            for event_name in to_add:
                cur.execute("SELECT id FROM event_types WHERE name = %s AND creator = %s", (event_name,self._user))
                result =  cur.fetchone()

                if result is None:
                    invalid_adds+=1
                    self.add(update(event_details,{'notes':"Invalid Add Attempt",'invalid_adds':invalid_adds}))
                else:
                    query_params.extend([entity_id,result[0]])
                    query += "(%s,%s),"

            if len(query_params) > 0:
                query = query[:-1]
                query += " ON CONFLICT ON CONSTRAINT entity_events_pkey DO NOTHING"
                cur.execute(query, tuple(query_params))

            query_params = [entity_id]
            query = "DELETE FROM entity_events WHERE entity_type = %s AND event_type IN (SELECT id FROM event_types WHERE"
            for event_name in to_remove:
                query += " (name = %s AND creator = %s) OR"
                query_params.extend(event_name,self._user)

            if len(query_params) > 1: 
                query = query[:-2]+')'
                cur.execute(query,tuple(query_params))

            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        return self.add(update(event_details,{'notes':"Entity Events Edited","success":True}))


    def view_entity_types(self, entity_type_name=None):
        entities=[]
        count=0
        
        query = """SELECT entity_types.name,array_agg(DISTINCT events.name) as entity_events FROM entity_types ,
                (SELECT entity_events.entity_type ,name FROM event_types INNER JOIN entity_events ON entity_events.event_type=event_types.id)
                 AS events WHERE entity_types.creator = %s"""
        params = [self._user]

        if entity_type_name:
            query+=" AND entity_types.name = %s"
            params.append(entity_type_name)
        query+=" GROUP BY entity_types.id"

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute(query,tuple(params))
            count = cur.rowcount
            entities = cur.fetchall()
            disconnect(conn,cur)

        except DatabaseError:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()
        
        return {'entities_returned':count,'entities':label_rows(['name','events'],entities)},True,200
        
        

class EventType(Event):
    ENTITY_TYPE_NAME = 'audit_metadata'
    ENTITY_INSTANCE_NAME = 'main_event_editor'

    def __init__(self, db_config, user):
        super().__init__(db_config, user)

    def add_event_type(self, data):
        name = data.get('name')
        event_details = {'event_type':'create_event_type','entity_type':self.ENTITY_TYPE_NAME,'success':False,'name':name,'entity_name':self.ENTITY_INSTANCE_NAME}
        mssg = 'Missing event name parameter'
        self._validate_event_parameter(name,mssg,update(event_details,{'notes':mssg}))

        conn = None
        try:    
            conn,cur = connect(self._db_config)
            cur.execute("""INSERT INTO event_types(name,creator)VALUES(%s,%s) 
            ON CONFLICT ON CONSTRAINT event_types_name_creator_key DO NOTHING RETURNING id""",(name,self._user))            
            
            mssg = "Event {0} Already Exists".format(name)
            self._validate_event_parameter(cur.fetchone(),mssg,update(event_details,{'notes':mssg}))
        
            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        return self.add(update(event_details,{'notes':"Event Added",'success':True}))


    def edit_event_type_attributes(self, event_type_name, data): 
        to_add = data.get('to_add') or []
        to_remove = data.get('to_remove') or []
        event_specs = None

        event_details = {'event_type':'edit_event_type_attributes','entity_type':self.ENTITY_TYPE_NAME,'success':False,'to_add':to_add,'to_remove':to_remove,'entity_name':self.ENTITY_INSTANCE_NAME}

        if not (isinstance(to_add,list) or isinstance(to_add,list)):
            mssg = "Attributes must be in a comma separated list"
            self.add(update(event_details,{'notes':mssg}))
            raise Exception(mssg,False,400)

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("SELECT attrs,id FROM event_types WHERE creator = %s AND name = %s", (self._user,event_type_name))
            event_specs = cur.fetchone()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        mssg = "Event {0} does not exist".format(event_type_name)
        self._validate_event_parameter(event_specs,mssg,update(event_details,{'notes':mssg}))
        
        attributes = set(event_specs[0] or set())
        event_id = event_specs[1]
        
        for attr in to_add:
            attributes.add(attr)
        for attr in to_remove:
            attributes.discard(attr)

        try:
            conn,cur = connect(self._db_config)
            cur.execute("UPDATE event_types SET attrs = %s WHERE id = %s", (list(attributes),event_id))
            conn.commit()
            disconnect(conn,cur)
         
        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        return self.add(update(event_details,{'notes':"Attributes Added",'success':True}))
        

    def view_event_types(self, event_name=None):
        event_types=[]
        count=0
        
        query = "SELECT name,attrs FROM event_types WHERE creator = %s"
        params = [self._user]
        if event_name:
            query+=" AND name = %s"
            params.append(event_name)

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute(query,tuple(params))
            count = cur.rowcount
            event_types = cur.fetchall()
            disconnect(conn,cur)

        except DatabaseError:
            raise(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()
        
        return {'events_returned':count,'events':label_rows(['name','attributes'],event_types)},True,200
