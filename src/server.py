import re
import sys
import json

from http.server import BaseHTTPRequestHandler, HTTPServer
from authorization import Authorizer
from routes import Route
from utils import config



class AuditServerHandler(BaseHTTPRequestHandler):
    _post_endpoints = {
    r'\/registration': 'register',
    r'\/v1\/entity': 'post_entity_type',
    r'\/v1\/event_type': 'post_event_type',
    r'\/v1\/event_type\/[^\/]+': 'post_event_type_attributes',
    r'\/v1\/entity\/[^\/]+': 'post_entity_type_events',
    r'\/v1\/events': 'post_event'
    }

    _get_endpoints =  {
    r'\/new_token': 'get_token',
    r'\/v1\/entity': 'get_entity_types',
    r'\/v1\/entity\/[^\/]+': 'get_entity_types',
    r'\/v1\/event_type': 'get_event_types',
    r'\/v1\/event_type\/[^\/]+': 'get_event_types',
    r'\/v1\/entities': 'get_entities',
    r'\/v1\/events\/[^\/]+': 'get_events',
    r'\/v1\/events': 'get_events'
    }

    _data = None
    _response = {}

    def do_HEAD(self):
        self.send_response(self._response['code'])
        origin = self.headers.get('origin')
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Content-Type", "application/json;charset=utf-8")


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


    def __read_data(self):
        content_length = self.headers.get('Content-Length')
        length = int(content_length) if content_length else 0
        data_string=self.rfile.read(length)
        self._data = json.loads(data_string) if data_string else None


    def __navigate_endpoint_auth(self,endpoints):
        if self.path == '/registration':
            result,success,code=Route.register(self._data,self.server._db_config)
            self._set_response(result,success,code)
            return

        if self.headers.get('Authorization') is None:
            self.send_response(401)
            if self.path == '/new_token':
                self.send_header('WWW-Authenticate', 'Basic realm = "Add token realm"')
            else:
                self.send_header('WWW-Authenticate', 'Bearer')
            self._set_response('No auth header received',False,401)
            return

        auth_type,auth_key=self.headers.get('Authorization').split()
        auth_manager=Authorizer(auth_type,auth_key,self.server._db_config)

        if(not auth_manager.authorized):
            self._set_response(auth_manager.message,False,401)
            return

        self.__execute_endpoint(auth_manager,endpoints)
                

    def __execute_endpoint(self,auth_manager: Authorizer,endpoints):
        matched_endpoint=[pattern for pattern in endpoints if re.compile(pattern).fullmatch(self.path)]

        if len(matched_endpoint)!=1:
            self._set_response('Page does not exist',False,404)
            return
    
        targets = self.path.split('/')
        url_params = [targets[i] for i in range(3,len(targets),2)] if len(targets)>3 else []

        route_manager = Route(auth_manager,self._data,self.server._db_config,url_params)
        result,success,code = route_manager.resolve(endpoints[matched_endpoint[0]])

        self._set_response(result,success,code)

    def _set_response(self,result,success,code):
        self._response={'result':result,'success':success,'code':code}



class AuditHTTPServer(HTTPServer):
    _db_config =None

    def __init__(self, address, handlerClass=AuditServerHandler):
        super().__init__(address, handlerClass)
        self._db_config = config()



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