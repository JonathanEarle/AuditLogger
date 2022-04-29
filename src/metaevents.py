"""
Classes which manage the enforcement of the entity type event type structure
Self auditing clsses which audit their own actions within the system
"""

"""
TODO: EventsTypes and EntityTypes have no deletion function to maintain the integrity of all existsing types.
An inactive or decomissioned column can be applied instead
"""

from events import Event
from psycopg2 import DatabaseError
from utils import connect,disconnect,label_rows,update,DATABASE_ERROR


"""Manages the creation, modification and viewing of entity types"""
class EntityType(Event):
    #Default entity and entity instance created on account instantiation
    ENTITY_TYPE_NAME = 'audit_metadata'
    ENTITY_INSTANCE_NAME = 'main_entity_editor'

    def __init__(self, db_config, user):
        super().__init__(db_config, user)

    """Validates the incoming data for creating a new entitiy type and creates it"""
    def add_entity_type(self, data):
        name = data.get('name')

        #Initial event definition
        event_details = {'event_type':'create_entity','entity_type':self.ENTITY_TYPE_NAME,'success':False,'attrs':data,'entity_name':self.ENTITY_INSTANCE_NAME}
        
        #Name validation
        mssg = 'Missing entity name parameter'
        self._validate_event_parameter(name,mssg,update(event_details,{'notes':mssg}))

        #Insertion of entity type
        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("""INSERT INTO entity_types(name,creator) VALUES(%s,%s)
            ON CONFLICT ON CONSTRAINT entity_types_name_creator_key DO NOTHING RETURNING id""",(name,self._user))

            #Ensure entity does not already exist
            mssg = "Entity {0} Already Exists".format(name)
            self._validate_event_parameter(cur.fetchone(),mssg,update(event_details,{'notes':mssg}))

            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        #Record that the creation of a new entity type happened
        return self.add(update(event_details,{'name':name,'notes':"Entity Added",'success':True}))
           

    """Add and remove event types the entity can perform"""
    def edit_entity_events(self, entity_type_name, data):
        to_add = data.get('to_add') or []
        to_remove = data.get('to_remove') or []
        invalid_events = []
        invalid_adds = removed = 0

        #Initial event definition
        event_details = {'event_type':'edit_entity_events','entity_type':self.ENTITY_TYPE_NAME,'success':False,'invalid_adds':0,'to_add':to_add,'to_remove':to_remove,'invalid_events':[],'entity_name':self.ENTITY_INSTANCE_NAME}

        #Ensure the incoming to add and to remove are ina list format
        if not (isinstance(to_add,list) and isinstance(to_remove,list)):
            mssg = "Events must be in a comma separated list"
            self.add(update(event_details,{'notes':mssg}))
            raise Exception(mssg,False,400)
        
        #Insertion and removal of events
        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("SELECT id FROM entity_types WHERE name = %s AND creator = %s", (entity_type_name,self._user))
            result =  cur.fetchone()
            
            #Ensure entity exists
            mssg = "Attempt to modify events of entity {0}, which does not exist".format(entity_type_name)
            self._validate_event_parameter(result,mssg,update(event_details,{'notes':mssg}))
            entity_id = result[0]

            query_params = []
            query = "INSERT INTO entity_events(entity_type,event_type)VALUES"
            
            #Loop through each event to add
            for event_name in to_add:
                cur.execute("SELECT id FROM event_types WHERE name = %s AND creator = %s", (event_name,self._user))
                result =  cur.fetchone()

                #TODO: Directly notify the user which events were invalid

                #Ensure each event exists if not make a note of it
                if result is None:
                    invalid_adds+=1
                    invalid_events.append(event_name)
                    self.add(update(event_details,{'invalid_adds':invalid_adds}))
                else:
                    query_params.extend([entity_id,result[0]])
                    query += "(%s,%s),"

            #Only attempt to run the query once we have entities to add
            if len(query_params) > 0:
                query = query[:-1]
                query += " ON CONFLICT ON CONSTRAINT entity_events_pkey DO NOTHING"
                cur.execute(query, tuple(query_params))

            #TODO: Diirectly notify the user which events were not deleted

            #Generate query string for deletion
            query_params = [entity_id]
            query = "DELETE FROM entity_events WHERE entity_type = %s AND event_type IN (SELECT id FROM event_types WHERE"
            for event_name in to_remove:
                query += " (name = %s AND creator = %s) OR"
                query_params.extend([event_name,self._user])

            #Only remove events if there are events to remove and return the remove events to use as a count
            if len(query_params) > 1:
                query = query[:-2]+') RETURNING *'
                cur.execute(query,tuple(query_params))
                removed = cur.rowcount

            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        #Record that the modification of an entity type happened
        return self.add(update(event_details,{'notes':"Entity Events Edited","success":True,'invalid_events':invalid_events,'removed':removed}))


    """View all entity type's details takes optional parameter of the name of the entity type"""
    def view_entity_types(self, entity_type_name=None):
        entities=[]
        count=0
        
        #Query string for viewing all entity types
        query = """SELECT all_entities.name, array_agg(DISTINCT (event_types.name)) AS events FROM
                (SELECT * FROM entity_types
                LEFT JOIN entity_events ON entity_types.id = entity_events.entity_type) AS all_entities
                LEFT JOIN event_types ON all_entities.event_type = event_types.id
                WHERE all_entities.creator = %s"""
        params = [self._user]

        #Filter by entity type name
        if entity_type_name:
            query+=" AND all_entities.name = %s"
            params.append(entity_type_name)
        query+=" GROUP BY all_entities.name"

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute(query,tuple(params))
            print(cur.query)
            count = cur.rowcount
            entities = cur.fetchall()
            disconnect(conn,cur)

        except DatabaseError:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()
        
        return {'entities_returned':count,'entities':label_rows(['name','events'],entities)},True,200
        
        

"""Manages the creation, modification and viewing of event types"""
class EventType(Event):
    #Default entity and entity instance created on account instantiation
    ENTITY_TYPE_NAME = 'audit_metadata'
    ENTITY_INSTANCE_NAME = 'main_event_editor'

    def __init__(self, db_config, user):
        super().__init__(db_config, user)

    """Validates the incoming data for creating a new event type and creates it"""
    def add_event_type(self, data):
        name = data.get('name')
        
        #Initial event definition
        event_details = {'event_type':'create_event_type','entity_type':self.ENTITY_TYPE_NAME,'success':False,'name':name,'entity_name':self.ENTITY_INSTANCE_NAME}
        
        #Name validation
        mssg = 'Missing event name parameter'
        self._validate_event_parameter(name,mssg,update(event_details,{'notes':mssg}))

        #Insertion of event type
        conn = None
        try:    
            conn,cur = connect(self._db_config)
            cur.execute("""INSERT INTO event_types(name,creator)VALUES(%s,%s) 
            ON CONFLICT ON CONSTRAINT event_types_name_creator_key DO NOTHING RETURNING id""",(name,self._user))            
            
            #Ensure event does not already exist
            mssg = "Event {0} Already Exists".format(name)
            self._validate_event_parameter(cur.fetchone(),mssg,update(event_details,{'notes':mssg}))
        
            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            self.add(update(event_details,{'notes':DATABASE_ERROR}))
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        #Record that the creation of a new event type happened
        return self.add(update(event_details,{'notes':"Event Added",'success':True}))

    #TODO: More details on the event specific attributes could be stored such as required tags and default value

    """Add and remove attributes from event types"""
    def edit_event_type_attributes(self, event_type_name, data): 
        to_add = data.get('to_add') or []
        to_remove = data.get('to_remove') or []
        event_specs = None

        #Initial event definition
        event_details = {'event_type':'edit_event_type_attributes','entity_type':self.ENTITY_TYPE_NAME,'success':False,'to_add':to_add,'to_remove':to_remove,'entity_name':self.ENTITY_INSTANCE_NAME}

        #Ensure the incoming to add and to remove are ina list format
        if not (isinstance(to_add,list) and isinstance(to_remove,list)):
            mssg = "Attributes must be in a comma separated list"
            self.add(update(event_details,{'notes':mssg}))
            raise Exception(mssg,False,400)

        #Select the event from the database
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

        #Ensure the event exists
        mssg = "Event {0} does not exist".format(event_type_name)
        self._validate_event_parameter(event_specs,mssg,update(event_details,{'notes':mssg}))
        
        #Cast the event's attributes to a set to ensure uniqueness of attributes
        attributes = set(event_specs[0] or set())
        event_id = event_specs[1]
        
        #TODO: Notify the user which attributes were not removed or how many were not

        #Add and remoove new attributes respectively
        for attr in to_add:
            attributes.add(attr)
        for attr in to_remove:
            attributes.discard(attr)

        #Write new attributes list to the event
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

        #Record that the modification of an event type happened
        return self.add(update(event_details,{'to_add':to_add,'to_remove':to_remove,'notes':"Attributes Added",'success':True}))
        

    """View all event type's details takes optional parameter of the name of the event type"""
    def view_event_types(self, event_name=None):
        event_types=[]
        count=0
        
        #Query string for viewing all event types
        query = "SELECT name,attrs FROM event_types WHERE creator = %s"
        params = [self._user]
        
        #Filter by event type name
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
