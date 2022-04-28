
# Audit Logger

An audit logging service which accepts event data 
sent by other systems and provides an HTTP endpoint 
for querying recorded event data by field values.

The service is based on an entity-event model where each 
entity has a set of events it can perform.



## Deploy Locally

Clone the project

```bash
  git clone https://github.com/JonathanEarle/Canonical_AuditLogger.git
```

Go to the project directory

```bash
  cd audit-logger
```

Make deployment script executable

```bash
  chmod +x deploy.sh
```

Run the deployment script. Set a password for the database when prompted, this is a postgres database used to store the service's data.

```bash
  ./deploy.sh
```


## Usage and Examples

#### Register with the audit logger

```http
  curl \
    -X POST http://localhost:8080/registration \
    -H 'Content-Type: application/json' \
    -d '{"email":"test@test.com","password":"password"}'
```

| Parameters| Type     | Description                |
| :-------- | :------- | :------------------------- |
| `email` | `string` | **Required**. Your email |
| `password` | `string` | **Required**. Your new password |



#### Generate a new API key

Once key is generated ensure to copy it. This key will noot be displayed again.
The key for basic authentication is the base64 encoding of `email:password`.

```http
  curl \
    -X GET http://localhost:8080/new_token \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Basic dGVzdEB0ZXN0LmNvbTpwYXNzd29yZA==' \
    -d '{"name":"Test Token"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Basic` | **Required**. base64 encoding of `email:password` |
| `name`      | `string` | Name of token |


#### Create a a new entity type

```http
  curl \
    -X POST http://localhost:8080/v1/entity \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"name":"employee"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `name`      | `string` | Name of entity type |

#### View entitiy types

```http
  curl \
    -X GET http://localhost:8080/v1/entity \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"name":"employee"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `name`      | `string` | **Optional.** Name of entity type |



#### Create a a new event type

```http
  curl \
    -X POST http://localhost:8080/v1/event_type \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"name":"open_register"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `name`      | `string` | Name of event type |

#### View event types

```http
  curl \
    -X GET http://localhost:8080/v1/event_type \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"name":"open_register"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `name`      | `string` | Name of event type |



#### Add/remove attributes to/from event type

```http
  curl \
    -X POST http://localhost:8080/v1/event_type/open_register \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"to_add":["withdrawl_amount","deposit_amount"]", "to_remove":"["register_number"]}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `to_add`      | `array` | Names of attributes to add |
| `to_remove`      | `array` | Names of attributes to remove |


#### Add/remove event types from entity type

```http
  curl \
    -X POST http://localhost:8080/v1/entity/employee \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"to_add":["open_register"]}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `to_add`      | `array` | Names of events to add |
| `to_remove`      | `array` | Names of events to remove |


#### Create new event

```http
  curl \
    -X POST http://localhost:8080/v1/events \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"event_type":"open_register","entity_type":"employee","success":true,"withdrawl_amount":10,"entity_name":"john","notes":"Employee John Withdrew $10"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `event_type`      | `string` |  **Required** Event type which occured |
| `entity_type`      | `string` |  **Required** Type of entity event occured on |
| `entity_name`      | `string` |  **Required** Names of entity instance |
| `success`      | `bool` |  **Required** Success status of event |
| `notes`      | `string` |  Extra notes |
| `{variate_attrs}`      | `any` | Event specific attributes |



#### View all events

To view all events the v1/events endpoint can be targeted.
To view all events on a particular entity the name of that entity can be added to the target path.

```http
  curl \
    -X GET http://localhost:8080/v1/events/john \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}' \
    -d '{"entity_id":"employee"}' 
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |
| `events.id`      | `int` | ID of event |
| `events.type`      | `int` | ID of event type |
| `entity_id`      | `int` | ID of entity type |
| `time`      | `string` | Time event occured |
| `success`      | `bool` | Success status of event |
| `{variate_attrs}`      | `any` | Event specific attributes |

#### View all entity instances

```http
  curl \
    -X GET http://localhost:8080/v1/entities \
    -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer {api_key}'
```

| Parameter | Type     | Description                       |
| :-------- | :------- | :-------------------------------- |
| `authorization`      | `Bearer` | **Required**. `api_key` |






## Running initial tests

To run a testing script on a newly deployed instance.
See existing `test_cases.csv` for test file format.

```bash
  cd tests
  python3 test.py `path_to_test_file`
```

