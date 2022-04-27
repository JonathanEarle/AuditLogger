import json
from psycopg2 import DatabaseError
from utils import connect,disconnect,label_rows,DATABASE_ERROR


class Event():
    def __init__(self, db_config, user):
        self._db_config = db_config
        self._user = user

    def _validate_event_parameter(self, param, mssg:str, event:dict=None):
        if param is None:
            if event is not None: self.add(event)
            raise Exception(mssg,False,400)

    def add(self, attrs):
        INVARIATE_ATTRS = ['event_type','entity_type','success','entity_name']
        if not all(key in attrs for key in INVARIATE_ATTRS):
            mssg = 'Missing Mandatory Event Parameter(s)'
            raise Exception(mssg,False,400)

        INVARIATE_ATTRS.extend(['rollback_id', 'notes'])
        invariate_attrs = {attr:attrs.get(attr) for attr in INVARIATE_ATTRS}

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.callproc('validate_event', (attrs['entity_type'], attrs['event_type'], self._user))
            results = cur.fetchone()

            self._validate_event_parameter(results,"Invalid Name(s) Received")
            entity_id,event_id = results[0],results[1]
            self._validate_event_parameter(entity_id or event_id,"Invalid Event ({0}) on Entity ({1})".format(attrs['event_type'],attrs['entity_type']))
        
            cur.execute("SELECT attrs FROM event_types WHERE id = %s",(event_id,))
            event_type_attrs = list(cur.fetchone()[0] or [])
            variate_attrs = {attr:attrs.get(attr) for attr in event_type_attrs}

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
        
        return ('{0} event occured on {1} instance {2}').format(attrs['event_type'],attrs['entity_type'],attrs['entity_name']),True,201
        

    def view(self, filters, entity_name=None):
        events = []
        count = 0

        EVENT_ATTRIBUTES = ['events.id','events.type','entity_id','time','success','rb_id']
        event_attr_values = [self._user]
        query = "SELECT events.id,events.type,entity_id,to_char(time,'DD Mon YYYY HH24:MI:SS'),success,rb_id,data FROM events"
        
        if entity_name is not None:
            query += " INNER JOIN entity_instances ON entity_instances.id = events.entity_id"
        query += " WHERE events.creator = %s"
        
        if filters is not None:
            for attr in EVENT_ATTRIBUTES:
                if attr in filters:
                    filter = filters.get(attr)
                    query += " AND "+attr+" = %s "
                    event_attr_values += [filter]
                    del filters[attr]
        
            for attr in filters:
                query += " AND data @> %s"
                event_attr_values += [json.dumps({attr:filters[attr]})]

        if entity_name is not None:
            query += " AND entity_instances.name = %s"
            event_attr_values.append(entity_name)

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

        labels = ['event_id','event_type_id','entity_id','created','success','rollback_id','attributes']
        return {'events_returned':count,'events':label_rows(labels,events)},True,200
        

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
        