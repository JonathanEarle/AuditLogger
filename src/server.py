"""Routes requests sent to the audit server and serves responses to the client"""
import re
import sys
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from authorization import Authorizer
from routes import Route
from utils import config


"""Request handler for the audit server"""
class AuditServerHandler(BaseHTTPRequestHandler):
    
    #TODO: Let dictionaries hold information on the type of authorization needed

    #Dictonaries mapping endpoint regex to a function to be executed at that endpoint
    #[^\/]+ substring maps to a particular target in the URI which is variable
    _post_endpoints = {
    r'registration': 'register',
    r'v1\/entity': 'post_entity_type',
    r'v1\/event_type': 'post_event_type',
    r'v1\/event_type\/[^\/]+': 'post_event_type_attributes', #v1/event_type/{name of event type}
    r'v1\/entity\/[^\/]+': 'post_entity_type_events',   #v1/entity/{name of entity type}
    r'v1\/events': 'post_event'
    }

    _get_endpoints =  {
    r'new_token': 'get_token',
    r'v1\/entity': 'get_entity_types',
    r'v1\/entity\/[^\/]+': 'get_entity_types', #v1/entity/{name of entity type}
    r'v1\/event_type': 'get_event_types',
    r'v1\/event_type\/[^\/]+': 'get_event_types', #v1/event_type/{name of event types}
    r'v1\/entities': 'get_entities',
    r'v1\/events\/[^\/]+': 'get_events', #v1/events/{name of entity instance}
    r'v1\/events': 'get_events'
    }

    _data = {} #Data received from a request
    _response = {} #Response to the data received 

    """Sends common headers"""
    def do_HEAD(self):
        self.send_response(self._response['code'])
        origin = self.headers.get('origin')
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Content-Type", "application/json;charset=utf-8")


    """
    do_GET and do_POST serve requests by:
    1- Reading the data received
    2- Navigating to the appropriate function to perform for the given endpoint
    3- Sending the request headers set
    4- Writing the final response to send back from the server
    """
    def do_GET(self) :
        self.__read_data()
        self.__navigate_endpoint_auth(self._get_endpoints)

        self.do_HEAD()
        self.send_header("Access-Control-Allow-Methods", "GET")        
        self.end_headers()

        self.wfile.write(bytes(json.dumps(self._response), 'utf-8'))


    def do_POST(self):
        self.__read_data()
        self.__navigate_endpoint_auth(self._post_endpoints)
        
        self.do_HEAD()
        self.send_header("Access-Control-Allow-Methods", "POST")
        self.end_headers()
        
        self.wfile.write(bytes(json.dumps(self._response), 'utf-8'))


    """Reads any data sent in by a request"""
    def __read_data(self):
        content_length = self.headers.get('Content-Length')
        length = int(content_length) if content_length else 0
        data_string=self.rfile.read(length)

        try:
            self._data = json.loads(data_string)
        except ValueError as error:
            return


    """Determines if the client is authorized to navigate the endpoint they are at"""
    def __navigate_endpoint_auth(self,endpoints):
        self.path=self.path.strip('/')

        #Registration needs no authorization so all requests are routed
        if self.path == 'registration':
            result,success,code=Route.register(self._data,self.server._db_config)
            self._set_response(result,success,code)
            return

        #Send the appropriate header for unauthorized pages
        if self.headers.get('Authorization') is None:
            self.send_response(401)
            if self.path == 'new_token':
                self.send_header('WWW-Authenticate', 'Basic realm = "Add token realm"')
            else:
                self.send_header('WWW-Authenticate', 'Bearer')
            self._set_response('No auth header received',False,401)
            return

        #Retrieve the authorization type and key sent by the client
        try:
            auth_type,auth_key=self.headers.get('Authorization').split()
        except ValueError as error:
            self._set_response('Malformed auth header received',False,401)
            return

        #Authorizer authorizes on instantiation and sets a message on the status of authorization
        auth_manager=Authorizer(auth_type,auth_key,self.server._db_config) 

        if(not auth_manager.authorized):
            self._set_response(auth_manager.message,False,401)
            return

        self.__execute_endpoint(auth_manager,endpoints)
                

    """Determines which function to run based on the endpoint received by matching to a regex in an endpoint dictionary"""
    def __execute_endpoint(self,auth_manager: Authorizer,endpoints):
        matched_endpoint=[pattern for pattern in endpoints if re.compile(pattern).fullmatch(self.path)]

        if len(matched_endpoint)!=1:
            self._set_response('Page does not exist',False,404)
            return
    
        """
        TODO: 
        URL Parameter extraction assumes they only occur in an alternating pattern.
        Write code to extract all points where the resource is variable.
        """

        targets = self.path.split('/')
        url_params = [targets[i] for i in range(2,len(targets),2)] if len(targets)>2 else []

        #Router class runs the function selected based on the endpoint
        route_manager = Route(auth_manager,self._data,self.server._db_config,url_params)
        result,success,code = route_manager.resolve(endpoints[matched_endpoint[0]])

        self._set_response(result,success,code)


    def _set_response(self,result,success,code):
        self._response={'result':result,'success':success,'code':code}


"""Sets the audit server's handler and reading the database configuration on server instantiation"""
class AuditHTTPServer(HTTPServer):
    _db_config =None

    def __init__(self, address, handlerClass=AuditServerHandler):
        super().__init__(address, handlerClass)
        self._db_config = config()


"""Audit server initalization based on command ine arguments host and port which default to 0.0.0.0 and 8080"""
if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

    audit_server = AuditHTTPServer((host, port))
    print("Audit Server initiated at http://{0}:{1}".format(host, port))

    try:
        audit_server.serve_forever()
    except KeyboardInterrupt:
        pass

    audit_server.server_close()
    print("Audit Server terminated")