CREATE TABLE IF NOT EXISTS public.whatsapp_admin
(
    id serial,
    response_id bigint,
    map_user_message character varying(255) COLLATE pg_catalog."default",
    valid_response character varying(255) COLLATE pg_catalog."default",
    invalid_response character varying(255) COLLATE pg_catalog."default",
    functions_to_call json,
    queries_to_execute_pre json,
    queries_to_execute_post json,
    created_on timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT whatsapp_admin_pkey PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS public.whatsapp_conversation_history
(
    id serial,
    mobile bigint,
    message text COLLATE pg_catalog."default",
    response_id bigint,
    created_on timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT whatsapp_conversation_history_pkey PRIMARY KEY (id)
);



CREATE TABLE IF NOT EXISTS public.whatsapp_request_collection
(
    id serial,
    payload json default null,
    created_on timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT whatsapp_request_collection_pkey PRIMARY KEY (id)
);

insert into whatsapp_request_collection (payload) values (null);

insert into whatsapp_admin(response_id, valid_response, invalid_response, functions_to_call) values ('1','1','1','["generate_pay_now_messages"]');