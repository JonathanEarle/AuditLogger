"""
Single class file which accepts authorization details and routes requests to the appropriate method 
using defined router functions
"""

from metaevents import EntityType,EventType
from events import Event
from authorization import Authorizer
from utils import INTERNAL_ERROR


class Route():
    def __init__(self, auth_manager:Authorizer, data, db_config, params):
        self._auth_manager = auth_manager
        self._user = auth_manager.user
        self._type = auth_manager.type

        self._params = params
        self._num_params = len(params)

        self._data = data
        self._db_config = db_config

    """Router function for registration"""
    @staticmethod
    def register(data,db_config):
        try:
            return Authorizer.register(data,db_config)
        except Exception as error:
            print(error)
            return "Error occurred while registering",False,500


    """Called to raise an error when the auth type is not basic"""
    def ensure_basic(self):
        if self._type != 'Basic':
            raise Exception('Username and Password Authentication Needed',False,403)


    """Called to raise an error when the auth type is not bearer"""
    def ensure_bearer(self):
        if self._type != 'Bearer':
            raise Exception('Token Not Provided',False,403)

    """
    The below functions are called by the router and performs:
    1- Checks that the right auth type is being used
    2- Instantiation of the appropriate object
    3- Execution and returning of the appropriate funtion
    """

    def post_entity_type(self):
        self.ensure_bearer()
        entity_type_manager=EntityType(self._db_config, self._user)
        return entity_type_manager.add_entity_type(self._data)

    def post_entity_type_events(self):
        self.ensure_bearer()
        entity_type_manager=EntityType(self._db_config, self._user)
        return entity_type_manager.edit_entity_events(self._params[0], self._data)

    def post_event_type(self):
        self.ensure_bearer()
        event_type_manager=EventType(self._db_config, self._user)
        return event_type_manager.add_event_type(self._data)
    
    def post_event_type_attributes(self):
        self.ensure_bearer()
        event_type_manager=EventType(self._db_config, self._user)
        return event_type_manager.edit_event_type_attributes(self._params[0],self._data)

    def post_event(self):
        self.ensure_bearer()
        event_manager=Event(self._db_config, self._user)
        return event_manager.add(self._data)

    
    def get_token(self):
        self.ensure_basic()
        return self._auth_manager.generate_token(self._data)

    def get_entity_types(self):
        self.ensure_bearer()
        entity_type_manager=EntityType(self._db_config, self._user)
        return entity_type_manager.view_entity_types(self._params[0] if self._num_params>0 else None)

    def get_event_types(self):
        self.ensure_bearer()
        event_type_manager=EventType(self._db_config, self._user)
        return event_type_manager.view_event_types(self._params[0] if self._num_params>0 else None)

    def get_entities(self):
        self.ensure_bearer()
        event_manager=Event(self._db_config, self._user)
        return event_manager.view_entity_instances()

    def get_events(self):
        self.ensure_bearer()
        event_manager=Event(self._db_config, self._user)
        return event_manager.view(self._data, self._params[0] if self._num_params>0 else None)

    """
    Checks authoorization of requested and executes the appropriate router fn
    and catching any errors which may occur during their execution
    """
    def resolve(self, name: str):
        if not self._auth_manager.authorized:
            return "Unauthorized",False,401

        action = f"{name}"
        if hasattr(self, action) and callable(route := getattr(self, action)):
            try:
                return route()
            except Exception as error:
                #TODO: Employ sturdier undefined error catching (possibly throuh an exception handler)

                if len(error.args) == 3: #Errors defined by the system have three components (message,success,code)
                    return error.args

                #It is assumed that any error which does not have three components is an error not accounted for 
                #and a generic error message is returned to prevent unwanted information leakage
                print(error)
                return INTERNAL_ERROR,False,500
