"""Events class which manages the adding and removal of events"""
import json
from psycopg2 import DatabaseError
from utils import connect,disconnect,label_rows,DATABASE_ERROR


class Event():
    def __init__(self, db_config, user):
        self._db_config = db_config
        self._user = user

    #TODO: Add type validation as well

    """Called to determine if a required event parameter is not defined"""
    def _validate_event_parameter(self, param, mssg:str, event:dict=None):
        if param is None:
            if event is not None: self.add(event)
            raise Exception(mssg,False,400)


    """Validates incoming events and adds it to the event store"""
    def add(self, attrs: dict):

        #Determines all the mandatory event attributes are set
        INVARIATE_ATTRS = ['event_type','entity_type','success','entity_name']
        if not all(key in attrs for key in INVARIATE_ATTRS):
            mssg = 'Missing Mandatory Event Parameter(s)'
            raise Exception(mssg,False,400)

        #Adds the optional attributes into a dictionary of invariate attributes
        INVARIATE_ATTRS.extend(['rollback_id', 'notes'])
        invariate_attrs = {attr:attrs.get(attr) for attr in INVARIATE_ATTRS}

        conn = None
        try:
            #Ensures the event can occur on the entity 
            conn,cur = connect(self._db_config)
            cur.callproc('validate_event', (attrs['entity_type'], attrs['event_type'], self._user))
            results = cur.fetchone()

            self._validate_event_parameter(results,"Invalid Name(s) Received")
            entity_id,event_id = results[0],results[1]
            self._validate_event_parameter(entity_id or event_id,"Invalid Event ({0}) on Entity ({1})".format(attrs['event_type'],attrs['entity_type'])) #TODO: Ensure that this is a necessary check
        
            #Collect the event type's variate attriibutes
            cur.execute("SELECT attrs FROM event_types WHERE id = %s",(event_id,))
            event_type_attrs = list(cur.fetchone()[0] or [])
            variate_attrs = {attr:attrs.get(attr) for attr in event_type_attrs}

            #Execute the event
            cur.execute(
            'CALL new_event(%s,%s,%s,%s,%s,%s,%s,%s)',
            (
                event_id,
                entity_id,
                invariate_attrs['entity_name'],
                self._user,
                invariate_attrs['success'],
                invariate_attrs['rollback_id'],
                invariate_attrs['notes'],
                json.dumps(variate_attrs)
            ))
            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()
        
        #TODO: A more descriptive message should be returned, including details of the attributes

        return ('{0} event occured on {1} instance {2}').format(attrs['event_type'],attrs['entity_type'],attrs['entity_name']),True,201
        
    #TODO: For longterm viability and managing of the results, all views should be paginated and have the option to be ordered by an attribute

    """View all the event's details, can be filtered by a specific entity or by a list of attributes"""
    def view(self, filters, entity_name : str=None):
        events = []
        count = 0

        #TODO: Event attributes based on exact database table reference, change to application defined labels

        EVENT_ATTRIBUTES = ['events.id','events.type','entity_id','time','success','rb_id'] #Possible filters for events
        event_attr_values = [self._user]
        query = "SELECT events.id,events.type,entity_id,to_char(time,'DD Mon YYYY HH24:MI:SS'),success,rb_id,data FROM events"
        
        #Utilize entity instances table to filter results by a specific entity
        if entity_name is not None:
            query += " INNER JOIN entity_instances ON entity_instances.id = events.entity_id"
        query += " WHERE events.creator = %s"
        
        
        #TODO: Create more versatile date filtering rather than exact match eg. date range
        #TODO: Currently filtering mainly by IDs, should utilize names instead

        #Build WHERE clause for filtering of selected event attributes
        if filters is not None:
            for attr in EVENT_ATTRIBUTES:
                if attr in filters:
                    filter = filters.get(attr)
                    query += " AND "+attr+" = %s "
                    event_attr_values += [filter]
                    del filters[attr]
        
            #Fiiltering by invariate event type specific attributes
            for attr in filters:
                query += " AND data @> %s"
                event_attr_values += [json.dumps({attr:filters[attr]})]

        #Utilize entity instances table to select a specific entity
        if entity_name is not None:
            query += " AND entity_instances.name = %s"
            event_attr_values.append(entity_name)

        query += "ORDER BY time DESC"

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute(query,tuple(event_attr_values))
            count=cur.rowcount
            events = cur.fetchall() 
            disconnect(conn,cur)

        except DatabaseError:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        labels = ['event.id','event.type','entity_id','time','success','rb_id','attributes']
        return {'events_returned':count,'events':label_rows(labels,events)},True,200
        

    """View each entity instance's details"""
    def view_entity_instances(self):
        instances = []
        count = 0

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("""SELECT id, name, type, to_char(created, 'DD Mon YYYY HH24:MI:SS'),to_char(modified, 'DD Mon YYYY HH24:MI:SS') 
            FROM entity_instances 
            WHERE creator = %s""",(self._user,))

            count=cur.rowcount
            instances = cur.fetchall()
            disconnect(conn,cur)

        except DatabaseError:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        labels = ['id','name','type','created','modified']
        return {'entities_returned':count,'entities':label_rows(labels,instances)},True,200
        