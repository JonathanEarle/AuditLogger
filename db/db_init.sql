CREATE DATABASE audit_logging;
\connect audit_logging

BEGIN;
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created TIMESTAMP DEFAULT NOW(),
    salt TEXT NOT NULL
);

CREATE TABLE tokens (
    id SERIAL PRIMARY KEY,
    user_id INT,
    name TEXT,
    token TEXT NOT NULL,

    CONSTRAINT fk_user_id
      FOREIGN KEY(user_id) 
	  REFERENCES users(id)
);
CREATE INDEX idx_token
ON tokens(token);

CREATE TABLE entity_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    creator INT,
    UNIQUE(name,creator),

    CONSTRAINT fk_creator
      FOREIGN KEY(creator) 
	  REFERENCES users(id)
);

CREATE TABLE event_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    creator INT,
    attrs TEXT [] DEFAULT '{}',
    UNIQUE(name,creator),

    CONSTRAINT fk_creator
      FOREIGN KEY(creator) 
	  REFERENCES users(id)
);

CREATE TABLE entity_events (
    entity_type INT NOT NULL,
    event_type INT NOT NULL,
    PRIMARY KEY(entity_type, event_type),

    CONSTRAINT fk_entity_type
      FOREIGN KEY(entity_type) 
	  REFERENCES entity_types(id),

    CONSTRAINT fk_event_type
      FOREIGN KEY(event_type) 
	  REFERENCES event_types(id)
);

-- Can be used in the future to hold the current state of an entity for reference/validation
CREATE TABLE entity_instances (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type INT,
    creator INT,
    created TIMESTAMP DEFAULT NOW(),
    modified TIMESTAMP DEFAULT NOW(),

    UNIQUE(creator,name),

    CONSTRAINT fk_creator
      FOREIGN KEY(creator) 
	  REFERENCES users(id),

    CONSTRAINT fk_type
      FOREIGN KEY(type) 
	  REFERENCES entity_types(id)
);

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    type INT,
    creator INT NOT NULL,
    entity_id INT,
    time TIMESTAMP DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    rb_id INT, --Unused field, intended to hold the id of an event to rollback to in the implementation of a rollback feature
    notes TEXT,
    data JSONB, --{attr_name:value} --CHANGE TO ATTRIBUTES

    CONSTRAINT fk_event_type
      FOREIGN KEY(type) 
	  REFERENCES event_types(id),

    CONSTRAINT fk_entity_id
      FOREIGN KEY(entity_id) 
	  REFERENCES entity_instances(id),

    CONSTRAINT fk_creator
      FOREIGN KEY(creator) 
	  REFERENCES users(id),

    CONSTRAINT fk_rollback_id
      FOREIGN KEY(rb_id) 
	  REFERENCES events(id)
);
CREATE INDEX idx_entity_id
ON events(entity_id);

CREATE INDEX idx_event_creator
ON events(creator);

-- Sets up the initial event types for modifying the entity event model
CREATE PROCEDURE initalize_account(user_id INT)
AS $$
DECLARE
	audit_metadata_id INT;
BEGIN
    --INSERT ENTITY AUDIT-METADATA
    INSERT INTO entity_types(creator,name) 
    VALUES (user_id,'audit_metadata')
	RETURNING id INTO audit_metadata_id;

    --INSERT AUDIT-METADATA EVENT TYPES
	WITH event_type_ids AS(
		INSERT INTO event_types(creator,name,attrs)  
		VALUES 
			(user_id,'create_entity', ARRAY ['name']),
			(user_id,'create_event_type', ARRAY ['name']),
			(user_id,'edit_entity_events', ARRAY ['to_add', 'to_remove', 'invalid_adds', 'invalid_events', 'removed']),
			(user_id,'edit_event_type_attributes', ARRAY ['to_add', 'to_remove'])
		RETURNING id
	)
	
    --APPLY EVENTS TO AUDIT-METADATA ENTITY
    INSERT INTO entity_events(entity_type,event_type) 
    SELECT audit_metadata_id,event_type_ids.id FROM event_type_ids;

    --ENTITY INSTANCE FOR ENTITY AND EVENT EDITING
    INSERT INTO entity_instances(type,name,creator)  
    VALUES
	(audit_metadata_id,'main_entity_editor',user_id), 
    (audit_metadata_id,'main_event_editor',user_id);

END; $$
LANGUAGE PLPGSQL;


-- Checks to ensure the received entity type can perform the received event type
-- If not results returned it cannot
CREATE FUNCTION validate_event(entity_type_name TEXT, event_type_name TEXT, event_creator INT) 
    RETURNS TABLE(entity_id INT, event_id INT) AS
$$
BEGIN
    RETURN QUERY

        SELECT entity_events.entity_type, entity_events.event_type
        FROM entity_events
        INNER JOIN entity_types ON entity_events.entity_type = entity_types.id
        INNER JOIN event_types ON entity_events.event_type = event_types.id
        WHERE entity_types.name = entity_type_name AND event_types.name = event_type_name
        AND event_types.creator = event_creator AND entity_types.creator = event_creator; --May be an unecessarry checks

END; $$
LANGUAGE plpgsql;

-- TODO: Store information on the current state of the event for future referencing
-- Adds a new event to event store and creates a new entity if it was not created already
CREATE PROCEDURE new_event(
    event_id INT,
    entity_id INT,
    entity_name TEXT,

    event_creator INT,

	success BOOLEAN,
    event_rb_id INT,
	event_notes TEXT,	
    event_data JSONB
)
AS $$
DECLARE
    new_event_entity_id INT;

BEGIN
	INSERT INTO entity_instances(type,name,creator)
	VALUES(entity_id, entity_name, event_creator)
	ON CONFLICT ON CONSTRAINT entity_instances_creator_name_key
	DO UPDATE SET modified = NOW()
	RETURNING id INTO new_event_entity_id;

	INSERT INTO events(type,entity_id,success,rb_id,data,creator,notes)
	VALUES(event_id,new_event_entity_id,success,event_rb_id,event_data,event_creator,event_notes);
END; $$
LANGUAGE PLPGSQL;

COMMIT;
