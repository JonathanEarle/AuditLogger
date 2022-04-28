
"""Single class file which manages the authorization based functions of registration, token generation and client authorization"""

import os
import re
import base64
import hashlib
import secrets

from psycopg2 import DatabaseError
from utils import connect,disconnect,DATABASE_ERROR


class Authorizer:
    #Regex to ensure valid email format
    EMAIL_VALIDATION = re.compile(r'([A-Za-z0-9]+[.-_])*[A-Za-z0-9]+@[A-Za-z0-9-]+(\.[A-Z|a-z]{2,})+')
    

    def __init__(self, type: str, key: str, db_config):
        self._type=type
        self._key=key
        self._db_config = db_config

        #Initial unauthorized state
        self._user = None
        self._authorized = False
        self._message = "Unauthorized"
        self._code = 500

        self._authorize() #Authorization done on instantiation

    @property
    def authorized(self):
        return self._authorized

    @property
    def message(self):
        return self._message

    @property
    def user(self):
        return self._user

    @property
    def type(self):
        return self._type


    @staticmethod
    def _hash_new_password(password: str) -> tuple[str, str]:
        salt = os.urandom(32).hex()
        pw_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()
        return salt, pw_hash

    #TODO: Have more refined permissions and user roles to define possible actions eg. Admin user can edit entities

    """Validates registration data and registers a new user"""
    @staticmethod
    def register(data, db_config):
        email = data.get('email')
        password = data.get('password')

        if email is None or email == '' or password is None or password == '':
            return "Both Email and Password required",False,400

        if not re.fullmatch(Authorizer.EMAIL_VALIDATION, email):                
            return "Invalid Email",False,400

        salt,pw_hash=Authorizer._hash_new_password(password)

        conn = None
        try:
            conn,cur = connect(db_config)
            
            cur.execute("""INSERT INTO users(email,password,salt)VALUES(%s,%s,%s)
            ON CONFLICT ON CONSTRAINT users_email_key DO NOTHING RETURNING id""",(email,pw_hash,salt))
            new_user_id = cur.fetchone()
            
            if new_user_id is None:
                return "Email Already Registered",False,400
            cur.execute('CALL initalize_account (%s)',(new_user_id,)) #Setup the intial state of the account

            conn.commit()
            disconnect(conn,cur)

        except DatabaseError:
            return  DATABASE_ERROR,False,500 
        finally:
            if conn is not None: conn.close()

        return "{0} Registered".format(email),True,201

    
    def _is_correct_password(self, salt: str, pw_hash: str, password: str) -> str:
        return pw_hash == hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 310000).hex()


    """Routes to the right authorization check based on type instatiated with"""
    def _authorize(self):
        if self.type=='Bearer':
            self._bearer_auth()
        
        if self.type=='Basic': 
            self._basic_auth() 

    #TODO: Add more token management eg. Revoking, lifespan, renewal

    """Generates a new token for the currently authorized user"""
    def generate_token(self, data):
        name = data.get('name') or ''
        token = secrets.token_urlsafe()

        #Random salt, used to hash the token, stored in an environment variable set on deployment
        salt = os.getenv('TOKEN_SALT')
        token_hash = hashlib.pbkdf2_hmac('sha256', token.encode(), salt.encode(), 310000).hex()

        conn = None
        try:
            conn,cur = connect(self._db_config)
            cur.execute("INSERT INTO tokens(user_id,token,name) VALUES(%s,%s,%s)",(self._user,token_hash,name))            
            conn.commit()
            disconnect(conn,cur)

        except DatabaseError as error:
            raise Exception(DATABASE_ERROR,False,500)
        finally:
            if conn is not None: conn.close()

        response = {'mssg':"Token {0} created, will not be displayed again".format(name),'token':token}
        return response,True,201


    """Checks if the token is valid and sets the user it belong to"""
    def _bearer_auth(self):
        salt = os.getenv('TOKEN_SALT')
        token_hash = hashlib.pbkdf2_hmac('sha256', self._key.encode(), salt.encode(), 310000).hex()

        conn = None
        try:
            conn,cur=connect(self._db_config)
            cur.execute("SELECT user_id FROM tokens WHERE token = %s",(token_hash,))
            user = cur.fetchone()
            disconnect(conn,cur)

        except DatabaseError:
            return
        finally:
            if conn is not None: conn.close()

        if user is None:
            self._code = 400
            return

        self._message = "Authorized"
        self._code = 200
        self._user = user[0]
        self._authorized = True


    """Checks if the email password combination is valid and sets the user it belongs to"""
    def _basic_auth(self):
        email=sent_pw=None

        try:            
            email,sent_pw = base64.b64decode(self._key.encode()).decode().split(':',1)
        except ValueError:
            self._message = "Credentials must be sent as base64 encoded email:password"
            self._code = 400
            return

        conn = None
        try:
            conn,cur=connect(self._db_config)
            cur.execute("SELECT id,password,salt FROM users WHERE email = %s ",(email,))
            user_details = cur.fetchone()
            disconnect(conn,cur)

        except DatabaseError:
            return
        finally:
            if conn is not None: conn.close()

        if user_details is None:
            self._message = "Unregistered Email"
            self._code = 400
            return
        
        user,user_pw,salt=user_details[0],user_details[1],user_details[2]
        if self._is_correct_password(salt, user_pw, sent_pw):
            self._message = "Authorized"
            self._code = 200
            self._user = user
            self._authorized =  True

