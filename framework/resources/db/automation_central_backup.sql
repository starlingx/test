toc.dat                                                                                             0000600 0004000 0002000 00000071746 14633101454 0014457 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        PGDMP   (    3                |        
   basic_dump    16.2    16.2 ^    O           0    0    ENCODING    ENCODING        SET client_encoding = 'UTF8';
                      false         P           0    0 
   STDSTRINGS 
   STDSTRINGS     (   SET standard_conforming_strings = 'on';
                      false         Q           0    0 
   SEARCHPATH 
   SEARCHPATH     8   SELECT pg_catalog.set_config('search_path', '', false);
                      false         R           1262    18125 
   basic_dump    DATABASE     �   CREATE DATABASE basic_dump WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'English_United States.1252';
    DROP DATABASE basic_dump;
                automation_user    false         �            1259    18126    analysis    TABLE     �   CREATE TABLE public.analysis (
    analysis_id integer NOT NULL,
    run_content_id integer,
    test_info_id integer,
    defect_id character varying,
    comment character varying,
    failure_type_id integer
);
    DROP TABLE public.analysis;
       public         heap    automation_user    false         �            1259    18131    analysis_analysis_id_seq    SEQUENCE     �   ALTER TABLE public.analysis ALTER COLUMN analysis_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analysis_analysis_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    215         �            1259    18132    capability_lab    TABLE     �   CREATE TABLE public.capability_lab (
    capability_lab_id integer NOT NULL,
    lab_info_id integer,
    capability_id integer
);
 "   DROP TABLE public.capability_lab;
       public         heap    automation_user    false         �            1259    18135 &   capabilities_lab_capability_lab_id_seq    SEQUENCE     �   ALTER TABLE public.capability_lab ALTER COLUMN capability_lab_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capabilities_lab_capability_lab_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    217         �            1259    18136 
   capability    TABLE     �   CREATE TABLE public.capability (
    capability_id integer NOT NULL,
    capability_name character varying,
    capability_marker character varying
);
    DROP TABLE public.capability;
       public         heap    automation_user    false         �            1259    18141    capability_capability_id_seq    SEQUENCE     �   ALTER TABLE public.capability ALTER COLUMN capability_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_capability_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    219         �            1259    18142    capability_session    TABLE     �   CREATE TABLE public.capability_session (
    capability_session_id integer NOT NULL,
    session_info_id integer,
    capability_id integer
);
 &   DROP TABLE public.capability_session;
       public         heap    automation_user    false         �            1259    18145 ,   capability_session_capability_session_id_seq    SEQUENCE       ALTER TABLE public.capability_session ALTER COLUMN capability_session_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_session_capability_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    221         �            1259    18146    capability_test    TABLE     �   CREATE TABLE public.capability_test (
    capability_test_id integer NOT NULL,
    test_info_id integer,
    capability_id integer
);
 #   DROP TABLE public.capability_test;
       public         heap    automation_user    false         �            1259    18149 &   capability_test_capability_test_id_seq    SEQUENCE     �   ALTER TABLE public.capability_test ALTER COLUMN capability_test_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_test_capability_test_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    223         �            1259    18150    failure_type    TABLE     t   CREATE TABLE public.failure_type (
    failure_type_id integer NOT NULL,
    failure_type_name character varying
);
     DROP TABLE public.failure_type;
       public         heap    automation_user    false         �            1259    18155     failure_type_failure_type_id_seq    SEQUENCE     �   ALTER TABLE public.failure_type ALTER COLUMN failure_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.failure_type_failure_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    225         �            1259    18156    lab_info    TABLE     c   CREATE TABLE public.lab_info (
    lab_info_id integer NOT NULL,
    lab_name character varying
);
    DROP TABLE public.lab_info;
       public         heap    automation_user    false         �            1259    18161    lab_info_lab_info_id_seq    SEQUENCE     �   ALTER TABLE public.lab_info ALTER COLUMN lab_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lab_info_lab_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    227         �            1259    18162    release    TABLE     e   CREATE TABLE public.release (
    release_id integer NOT NULL,
    release_name character varying
);
    DROP TABLE public.release;
       public         heap    automation_user    false         �            1259    18167    release_release_id_seq    SEQUENCE     �   ALTER TABLE public.release ALTER COLUMN release_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.release_release_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    229         �            1259    18168    run    TABLE     �   CREATE TABLE public.run (
    run_id integer NOT NULL,
    run_name character varying,
    run_type_id integer,
    release character varying,
    run_created_at timestamp without time zone
);
    DROP TABLE public.run;
       public         heap    automation_user    false         �            1259    18173    run_content    TABLE     
  CREATE TABLE public.run_content (
    run_content_id integer NOT NULL,
    run_id integer,
    session_info_id integer,
    test_info_id integer,
    run_content_execution_status character varying,
    execution_fail_count integer,
    test_case_group_id integer
);
    DROP TABLE public.run_content;
       public         heap    automation_user    false         �            1259    18178    run_content_run_content_id_seq    SEQUENCE     �   ALTER TABLE public.run_content ALTER COLUMN run_content_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_content_run_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    232         �            1259    18179    run_run_id_seq    SEQUENCE     �   ALTER TABLE public.run ALTER COLUMN run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    231         �            1259    18180    run_type    TABLE     h   CREATE TABLE public.run_type (
    run_type_id integer NOT NULL,
    run_type_name character varying
);
    DROP TABLE public.run_type;
       public         heap    automation_user    false         �            1259    18185    run_type_run_type_id_seq    SEQUENCE     �   ALTER TABLE public.run_type ALTER COLUMN run_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_type_run_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    235         �            1259    18186    session_info    TABLE     �   CREATE TABLE public.session_info (
    session_info_id integer NOT NULL,
    session_name character varying,
    test_plan_id integer DEFAULT '-1'::integer,
    enabled boolean DEFAULT false
);
     DROP TABLE public.session_info;
       public         heap    automation_user    false         �            1259    18949    session_info_content    TABLE     �   CREATE TABLE public.session_info_content (
    session_info_content_id integer NOT NULL,
    session_info_id integer,
    test_info_id integer,
    enabled boolean
);
 (   DROP TABLE public.session_info_content;
       public         heap    automation_user    false         �            1259    18952 0   session_info_content_session_info_content_id_seq    SEQUENCE       ALTER TABLE public.session_info_content ALTER COLUMN session_info_content_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.session_info_content_session_info_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    249         �            1259    18193     session_info_session_info_id_seq    SEQUENCE     �   ALTER TABLE public.session_info ALTER COLUMN session_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.session_info_session_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    237         �            1259    18194    test_case_group    TABLE     }   CREATE TABLE public.test_case_group (
    test_case_group_id integer NOT NULL,
    test_case_group_name character varying
);
 #   DROP TABLE public.test_case_group;
       public         heap    automation_user    false         �            1259    18199 &   test_case_group_test_case_group_id_seq    SEQUENCE     �   ALTER TABLE public.test_case_group ALTER COLUMN test_case_group_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_case_group_test_case_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    239         �            1259    18200    test_case_result    TABLE     �  CREATE TABLE public.test_case_result (
    test_case_result_id integer NOT NULL,
    test_info_id integer NOT NULL,
    execution_result character varying NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    duration integer GENERATED ALWAYS AS (EXTRACT(epoch FROM (end_time - start_time))) STORED,
    test_run_execution_id integer DEFAULT '-1'::integer
);
 $   DROP TABLE public.test_case_result;
       public         heap    automation_user    false         �            1259    18206 (   test_case_result_test_case_result_id_seq    SEQUENCE     �   ALTER TABLE public.test_case_result ALTER COLUMN test_case_result_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_case_result_test_case_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    241         �            1259    18207 	   test_info    TABLE     I  CREATE TABLE public.test_info (
    test_info_id integer NOT NULL,
    test_name character varying,
    test_suite character varying,
    priority character varying,
    test_path character varying,
    pytest_node_id character varying,
    test_case_group_id integer DEFAULT '-1'::integer,
    is_active boolean DEFAULT true
);
    DROP TABLE public.test_info;
       public         heap    automation_user    false         �            1259    18214    test_info_test_info_id_seq    SEQUENCE     �   ALTER TABLE public.test_info ALTER COLUMN test_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_info_test_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    243         �            1259    18215 	   test_plan    TABLE     �   CREATE TABLE public.test_plan (
    test_plan_id integer NOT NULL,
    test_plan_name character varying,
    description character varying,
    run_type_id integer,
    locked boolean DEFAULT false
);
    DROP TABLE public.test_plan;
       public         heap    automation_user    false         �            1259    18221    test_plan_test_plan_id_seq    SEQUENCE     �   ALTER TABLE public.test_plan ALTER COLUMN test_plan_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_plan_test_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    245         �            1259    18222    test_run_execution    TABLE     �   CREATE TABLE public.test_run_execution (
    test_run_execution_id integer NOT NULL,
    lab_info_id integer,
    run_id integer,
    dispatching_status character varying,
    run_content_id integer,
    test_case_group_id integer
);
 &   DROP TABLE public.test_run_execution;
       public         heap    automation_user    false         �            1259    18227 ,   test_run_execution_test_run_execution_id_seq    SEQUENCE       ALTER TABLE public.test_run_execution ALTER COLUMN test_run_execution_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_run_execution_test_run_execution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);
            public          automation_user    false    247         )          0    18126    analysis 
   TABLE DATA           r   COPY public.analysis (analysis_id, run_content_id, test_info_id, defect_id, comment, failure_type_id) FROM stdin;
    public          automation_user    false    215       4905.dat -          0    18136 
   capability 
   TABLE DATA           W   COPY public.capability (capability_id, capability_name, capability_marker) FROM stdin;
    public          automation_user    false    219       4909.dat +          0    18132    capability_lab 
   TABLE DATA           W   COPY public.capability_lab (capability_lab_id, lab_info_id, capability_id) FROM stdin;
    public          automation_user    false    217       4907.dat /          0    18142    capability_session 
   TABLE DATA           c   COPY public.capability_session (capability_session_id, session_info_id, capability_id) FROM stdin;
    public          automation_user    false    221       4911.dat 1          0    18146    capability_test 
   TABLE DATA           Z   COPY public.capability_test (capability_test_id, test_info_id, capability_id) FROM stdin;
    public          automation_user    false    223       4913.dat 3          0    18150    failure_type 
   TABLE DATA           J   COPY public.failure_type (failure_type_id, failure_type_name) FROM stdin;
    public          automation_user    false    225       4915.dat 5          0    18156    lab_info 
   TABLE DATA           9   COPY public.lab_info (lab_info_id, lab_name) FROM stdin;
    public          automation_user    false    227       4917.dat 7          0    18162    release 
   TABLE DATA           ;   COPY public.release (release_id, release_name) FROM stdin;
    public          automation_user    false    229       4919.dat 9          0    18168    run 
   TABLE DATA           U   COPY public.run (run_id, run_name, run_type_id, release, run_created_at) FROM stdin;
    public          automation_user    false    231       4921.dat :          0    18173    run_content 
   TABLE DATA           �   COPY public.run_content (run_content_id, run_id, session_info_id, test_info_id, run_content_execution_status, execution_fail_count, test_case_group_id) FROM stdin;
    public          automation_user    false    232       4922.dat =          0    18180    run_type 
   TABLE DATA           >   COPY public.run_type (run_type_id, run_type_name) FROM stdin;
    public          automation_user    false    235       4925.dat ?          0    18186    session_info 
   TABLE DATA           \   COPY public.session_info (session_info_id, session_name, test_plan_id, enabled) FROM stdin;
    public          automation_user    false    237       4927.dat K          0    18949    session_info_content 
   TABLE DATA           o   COPY public.session_info_content (session_info_content_id, session_info_id, test_info_id, enabled) FROM stdin;
    public          automation_user    false    249       4939.dat A          0    18194    test_case_group 
   TABLE DATA           S   COPY public.test_case_group (test_case_group_id, test_case_group_name) FROM stdin;
    public          automation_user    false    239       4929.dat C          0    18200    test_case_result 
   TABLE DATA           �   COPY public.test_case_result (test_case_result_id, test_info_id, execution_result, start_time, end_time, test_run_execution_id) FROM stdin;
    public          automation_user    false    241       4931.dat E          0    18207 	   test_info 
   TABLE DATA           �   COPY public.test_info (test_info_id, test_name, test_suite, priority, test_path, pytest_node_id, test_case_group_id, is_active) FROM stdin;
    public          automation_user    false    243       4933.dat G          0    18215 	   test_plan 
   TABLE DATA           c   COPY public.test_plan (test_plan_id, test_plan_name, description, run_type_id, locked) FROM stdin;
    public          automation_user    false    245       4935.dat I          0    18222    test_run_execution 
   TABLE DATA           �   COPY public.test_run_execution (test_run_execution_id, lab_info_id, run_id, dispatching_status, run_content_id, test_case_group_id) FROM stdin;
    public          automation_user    false    247       4937.dat S           0    0    analysis_analysis_id_seq    SEQUENCE SET     G   SELECT pg_catalog.setval('public.analysis_analysis_id_seq', 1, false);
          public          automation_user    false    216         T           0    0 &   capabilities_lab_capability_lab_id_seq    SEQUENCE SET     U   SELECT pg_catalog.setval('public.capabilities_lab_capability_lab_id_seq', 1, false);
          public          automation_user    false    218         U           0    0    capability_capability_id_seq    SEQUENCE SET     J   SELECT pg_catalog.setval('public.capability_capability_id_seq', 5, true);
          public          automation_user    false    220         V           0    0 ,   capability_session_capability_session_id_seq    SEQUENCE SET     [   SELECT pg_catalog.setval('public.capability_session_capability_session_id_seq', 1, false);
          public          automation_user    false    222         W           0    0 &   capability_test_capability_test_id_seq    SEQUENCE SET     U   SELECT pg_catalog.setval('public.capability_test_capability_test_id_seq', 1, false);
          public          automation_user    false    224         X           0    0     failure_type_failure_type_id_seq    SEQUENCE SET     O   SELECT pg_catalog.setval('public.failure_type_failure_type_id_seq', 1, false);
          public          automation_user    false    226         Y           0    0    lab_info_lab_info_id_seq    SEQUENCE SET     G   SELECT pg_catalog.setval('public.lab_info_lab_info_id_seq', 1, false);
          public          automation_user    false    228         Z           0    0    release_release_id_seq    SEQUENCE SET     E   SELECT pg_catalog.setval('public.release_release_id_seq', 1, false);
          public          automation_user    false    230         [           0    0    run_content_run_content_id_seq    SEQUENCE SET     M   SELECT pg_catalog.setval('public.run_content_run_content_id_seq', 1, false);
          public          automation_user    false    233         \           0    0    run_run_id_seq    SEQUENCE SET     =   SELECT pg_catalog.setval('public.run_run_id_seq', 1, false);
          public          automation_user    false    234         ]           0    0    run_type_run_type_id_seq    SEQUENCE SET     F   SELECT pg_catalog.setval('public.run_type_run_type_id_seq', 3, true);
          public          automation_user    false    236         ^           0    0 0   session_info_content_session_info_content_id_seq    SEQUENCE SET     _   SELECT pg_catalog.setval('public.session_info_content_session_info_content_id_seq', 1, false);
          public          automation_user    false    250         _           0    0     session_info_session_info_id_seq    SEQUENCE SET     O   SELECT pg_catalog.setval('public.session_info_session_info_id_seq', 1, false);
          public          automation_user    false    238         `           0    0 &   test_case_group_test_case_group_id_seq    SEQUENCE SET     U   SELECT pg_catalog.setval('public.test_case_group_test_case_group_id_seq', 1, false);
          public          automation_user    false    240         a           0    0 (   test_case_result_test_case_result_id_seq    SEQUENCE SET     W   SELECT pg_catalog.setval('public.test_case_result_test_case_result_id_seq', 1, false);
          public          automation_user    false    242         b           0    0    test_info_test_info_id_seq    SEQUENCE SET     I   SELECT pg_catalog.setval('public.test_info_test_info_id_seq', 1, false);
          public          automation_user    false    244         c           0    0    test_plan_test_plan_id_seq    SEQUENCE SET     I   SELECT pg_catalog.setval('public.test_plan_test_plan_id_seq', 1, false);
          public          automation_user    false    246         d           0    0 ,   test_run_execution_test_run_execution_id_seq    SEQUENCE SET     [   SELECT pg_catalog.setval('public.test_run_execution_test_run_execution_id_seq', 1, false);
          public          automation_user    false    248         w           2606    18230    analysis analysis_pkey 
   CONSTRAINT     ]   ALTER TABLE ONLY public.analysis
    ADD CONSTRAINT analysis_pkey PRIMARY KEY (analysis_id);
 @   ALTER TABLE ONLY public.analysis DROP CONSTRAINT analysis_pkey;
       public            automation_user    false    215         y           2606    18234 "   capability_lab capability_lab_pkey 
   CONSTRAINT     o   ALTER TABLE ONLY public.capability_lab
    ADD CONSTRAINT capability_lab_pkey PRIMARY KEY (capability_lab_id);
 L   ALTER TABLE ONLY public.capability_lab DROP CONSTRAINT capability_lab_pkey;
       public            automation_user    false    217         {           2606    18232    capability capability_pkey 
   CONSTRAINT     c   ALTER TABLE ONLY public.capability
    ADD CONSTRAINT capability_pkey PRIMARY KEY (capability_id);
 D   ALTER TABLE ONLY public.capability DROP CONSTRAINT capability_pkey;
       public            automation_user    false    219         }           2606    18236 *   capability_session capability_session_pkey 
   CONSTRAINT     {   ALTER TABLE ONLY public.capability_session
    ADD CONSTRAINT capability_session_pkey PRIMARY KEY (capability_session_id);
 T   ALTER TABLE ONLY public.capability_session DROP CONSTRAINT capability_session_pkey;
       public            automation_user    false    221                    2606    18238 $   capability_test capability_test_pkey 
   CONSTRAINT     r   ALTER TABLE ONLY public.capability_test
    ADD CONSTRAINT capability_test_pkey PRIMARY KEY (capability_test_id);
 N   ALTER TABLE ONLY public.capability_test DROP CONSTRAINT capability_test_pkey;
       public            automation_user    false    223         �           2606    18240    failure_type failure_type_pkey 
   CONSTRAINT     i   ALTER TABLE ONLY public.failure_type
    ADD CONSTRAINT failure_type_pkey PRIMARY KEY (failure_type_id);
 H   ALTER TABLE ONLY public.failure_type DROP CONSTRAINT failure_type_pkey;
       public            automation_user    false    225         �           2606    18242    lab_info lab_info_pkey 
   CONSTRAINT     ]   ALTER TABLE ONLY public.lab_info
    ADD CONSTRAINT lab_info_pkey PRIMARY KEY (lab_info_id);
 @   ALTER TABLE ONLY public.lab_info DROP CONSTRAINT lab_info_pkey;
       public            automation_user    false    227         �           2606    18244    release release_pkey 
   CONSTRAINT     Z   ALTER TABLE ONLY public.release
    ADD CONSTRAINT release_pkey PRIMARY KEY (release_id);
 >   ALTER TABLE ONLY public.release DROP CONSTRAINT release_pkey;
       public            automation_user    false    229         �           2606    18248    run_content run_content_pkey 
   CONSTRAINT     f   ALTER TABLE ONLY public.run_content
    ADD CONSTRAINT run_content_pkey PRIMARY KEY (run_content_id);
 F   ALTER TABLE ONLY public.run_content DROP CONSTRAINT run_content_pkey;
       public            automation_user    false    232         �           2606    18246    run run_pkey 
   CONSTRAINT     N   ALTER TABLE ONLY public.run
    ADD CONSTRAINT run_pkey PRIMARY KEY (run_id);
 6   ALTER TABLE ONLY public.run DROP CONSTRAINT run_pkey;
       public            automation_user    false    231         �           2606    18250    run_type run_type_pkey 
   CONSTRAINT     ]   ALTER TABLE ONLY public.run_type
    ADD CONSTRAINT run_type_pkey PRIMARY KEY (run_type_id);
 @   ALTER TABLE ONLY public.run_type DROP CONSTRAINT run_type_pkey;
       public            automation_user    false    235         �           2606    18957 .   session_info_content session_info_content_pkey 
   CONSTRAINT     �   ALTER TABLE ONLY public.session_info_content
    ADD CONSTRAINT session_info_content_pkey PRIMARY KEY (session_info_content_id);
 X   ALTER TABLE ONLY public.session_info_content DROP CONSTRAINT session_info_content_pkey;
       public            automation_user    false    249         �           2606    18252    session_info session_info_pkey 
   CONSTRAINT     i   ALTER TABLE ONLY public.session_info
    ADD CONSTRAINT session_info_pkey PRIMARY KEY (session_info_id);
 H   ALTER TABLE ONLY public.session_info DROP CONSTRAINT session_info_pkey;
       public            automation_user    false    237         �           2606    18254 $   test_case_group test_case_group_pkey 
   CONSTRAINT     r   ALTER TABLE ONLY public.test_case_group
    ADD CONSTRAINT test_case_group_pkey PRIMARY KEY (test_case_group_id);
 N   ALTER TABLE ONLY public.test_case_group DROP CONSTRAINT test_case_group_pkey;
       public            automation_user    false    239         �           2606    18256 &   test_case_result test_case_result_pkey 
   CONSTRAINT     u   ALTER TABLE ONLY public.test_case_result
    ADD CONSTRAINT test_case_result_pkey PRIMARY KEY (test_case_result_id);
 P   ALTER TABLE ONLY public.test_case_result DROP CONSTRAINT test_case_result_pkey;
       public            automation_user    false    241         �           2606    18258    test_info test_info_pkey 
   CONSTRAINT     `   ALTER TABLE ONLY public.test_info
    ADD CONSTRAINT test_info_pkey PRIMARY KEY (test_info_id);
 B   ALTER TABLE ONLY public.test_info DROP CONSTRAINT test_info_pkey;
       public            automation_user    false    243         �           2606    18260    test_plan test_plan_pkey 
   CONSTRAINT     `   ALTER TABLE ONLY public.test_plan
    ADD CONSTRAINT test_plan_pkey PRIMARY KEY (test_plan_id);
 B   ALTER TABLE ONLY public.test_plan DROP CONSTRAINT test_plan_pkey;
       public            automation_user    false    245         �           2606    18262 *   test_run_execution test_run_execution_pkey 
   CONSTRAINT     {   ALTER TABLE ONLY public.test_run_execution
    ADD CONSTRAINT test_run_execution_pkey PRIMARY KEY (test_run_execution_id);
 T   ALTER TABLE ONLY public.test_run_execution DROP CONSTRAINT test_run_execution_pkey;
       public            automation_user    false    247                                  4905.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014247 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4909.dat                                                                                            0000600 0004000 0002000 00000000260 14633101454 0014256 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        1	standby_controller	lab_has_standby_controller
2	non_low_latency	lab_has_non_low_latency
3	sriov	lab_has_sriov
4	low_latency	lab_has_low_latency
5	simplex	lab_is_simplex
\.


                                                                                                                                                                                                                                                                                                                                                4907.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014251 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4911.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014244 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4913.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014246 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4915.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014250 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4917.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014252 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4919.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014254 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4921.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014245 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4922.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014246 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4925.dat                                                                                            0000600 0004000 0002000 00000000044 14633101454 0014254 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        1	Regression
2	Sanity
3	Custom
\.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            4927.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014253 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4939.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014256 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4929.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014255 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4931.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014246 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4933.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014250 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4935.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014252 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           4937.dat                                                                                            0000600 0004000 0002000 00000000005 14633101454 0014254 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        \.


                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           restore.sql                                                                                         0000600 0004000 0002000 00000063222 14633101454 0015372 0                                                                                                    ustar 00postgres                        postgres                        0000000 0000000                                                                                                                                                                        --
-- NOTE:
--
-- File paths need to be edited. Search for $$PATH$$ and
-- replace it with the path to the directory containing
-- the extracted data files.
--
--
-- PostgreSQL database dump
--

-- Dumped from database version 16.2
-- Dumped by pg_dump version 16.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

DROP DATABASE basic_dump;
--
-- Name: basic_dump; Type: DATABASE; Schema: -; Owner: automation_user
--

CREATE DATABASE basic_dump WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'English_United States.1252';


ALTER DATABASE basic_dump OWNER TO automation_user;

\connect basic_dump

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.analysis (
    analysis_id integer NOT NULL,
    run_content_id integer,
    test_info_id integer,
    defect_id character varying,
    comment character varying,
    failure_type_id integer
);


ALTER TABLE public.analysis OWNER TO automation_user;

--
-- Name: analysis_analysis_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.analysis ALTER COLUMN analysis_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.analysis_analysis_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capability_lab; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.capability_lab (
    capability_lab_id integer NOT NULL,
    lab_info_id integer,
    capability_id integer
);


ALTER TABLE public.capability_lab OWNER TO automation_user;

--
-- Name: capabilities_lab_capability_lab_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.capability_lab ALTER COLUMN capability_lab_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capabilities_lab_capability_lab_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capability; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.capability (
    capability_id integer NOT NULL,
    capability_name character varying,
    capability_marker character varying
);


ALTER TABLE public.capability OWNER TO automation_user;

--
-- Name: capability_capability_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.capability ALTER COLUMN capability_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_capability_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capability_session; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.capability_session (
    capability_session_id integer NOT NULL,
    session_info_id integer,
    capability_id integer
);


ALTER TABLE public.capability_session OWNER TO automation_user;

--
-- Name: capability_session_capability_session_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.capability_session ALTER COLUMN capability_session_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_session_capability_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: capability_test; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.capability_test (
    capability_test_id integer NOT NULL,
    test_info_id integer,
    capability_id integer
);


ALTER TABLE public.capability_test OWNER TO automation_user;

--
-- Name: capability_test_capability_test_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.capability_test ALTER COLUMN capability_test_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.capability_test_capability_test_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: failure_type; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.failure_type (
    failure_type_id integer NOT NULL,
    failure_type_name character varying
);


ALTER TABLE public.failure_type OWNER TO automation_user;

--
-- Name: failure_type_failure_type_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.failure_type ALTER COLUMN failure_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.failure_type_failure_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: lab_info; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.lab_info (
    lab_info_id integer NOT NULL,
    lab_name character varying
);


ALTER TABLE public.lab_info OWNER TO automation_user;

--
-- Name: lab_info_lab_info_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.lab_info ALTER COLUMN lab_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.lab_info_lab_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: release; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.release (
    release_id integer NOT NULL,
    release_name character varying
);


ALTER TABLE public.release OWNER TO automation_user;

--
-- Name: release_release_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.release ALTER COLUMN release_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.release_release_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: run; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.run (
    run_id integer NOT NULL,
    run_name character varying,
    run_type_id integer,
    release character varying,
    run_created_at timestamp without time zone
);


ALTER TABLE public.run OWNER TO automation_user;

--
-- Name: run_content; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.run_content (
    run_content_id integer NOT NULL,
    run_id integer,
    session_info_id integer,
    test_info_id integer,
    run_content_execution_status character varying,
    execution_fail_count integer,
    test_case_group_id integer
);


ALTER TABLE public.run_content OWNER TO automation_user;

--
-- Name: run_content_run_content_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.run_content ALTER COLUMN run_content_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_content_run_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: run_run_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.run ALTER COLUMN run_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: run_type; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.run_type (
    run_type_id integer NOT NULL,
    run_type_name character varying
);


ALTER TABLE public.run_type OWNER TO automation_user;

--
-- Name: run_type_run_type_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.run_type ALTER COLUMN run_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.run_type_run_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: session_info; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.session_info (
    session_info_id integer NOT NULL,
    session_name character varying,
    test_plan_id integer DEFAULT '-1'::integer,
    enabled boolean DEFAULT false
);


ALTER TABLE public.session_info OWNER TO automation_user;

--
-- Name: session_info_content; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.session_info_content (
    session_info_content_id integer NOT NULL,
    session_info_id integer,
    test_info_id integer,
    enabled boolean
);


ALTER TABLE public.session_info_content OWNER TO automation_user;

--
-- Name: session_info_content_session_info_content_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.session_info_content ALTER COLUMN session_info_content_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.session_info_content_session_info_content_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: session_info_session_info_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.session_info ALTER COLUMN session_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.session_info_session_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: test_case_group; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.test_case_group (
    test_case_group_id integer NOT NULL,
    test_case_group_name character varying
);


ALTER TABLE public.test_case_group OWNER TO automation_user;

--
-- Name: test_case_group_test_case_group_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.test_case_group ALTER COLUMN test_case_group_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_case_group_test_case_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: test_case_result; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.test_case_result (
    test_case_result_id integer NOT NULL,
    test_info_id integer NOT NULL,
    execution_result character varying NOT NULL,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    duration integer GENERATED ALWAYS AS (EXTRACT(epoch FROM (end_time - start_time))) STORED,
    test_run_execution_id integer DEFAULT '-1'::integer
);


ALTER TABLE public.test_case_result OWNER TO automation_user;

--
-- Name: test_case_result_test_case_result_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.test_case_result ALTER COLUMN test_case_result_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_case_result_test_case_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: test_info; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.test_info (
    test_info_id integer NOT NULL,
    test_name character varying,
    test_suite character varying,
    priority character varying,
    test_path character varying,
    pytest_node_id character varying,
    test_case_group_id integer DEFAULT '-1'::integer,
    is_active boolean DEFAULT true
);


ALTER TABLE public.test_info OWNER TO automation_user;

--
-- Name: test_info_test_info_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.test_info ALTER COLUMN test_info_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_info_test_info_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: test_plan; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.test_plan (
    test_plan_id integer NOT NULL,
    test_plan_name character varying,
    description character varying,
    run_type_id integer,
    locked boolean DEFAULT false
);


ALTER TABLE public.test_plan OWNER TO automation_user;

--
-- Name: test_plan_test_plan_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.test_plan ALTER COLUMN test_plan_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_plan_test_plan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: test_run_execution; Type: TABLE; Schema: public; Owner: automation_user
--

CREATE TABLE public.test_run_execution (
    test_run_execution_id integer NOT NULL,
    lab_info_id integer,
    run_id integer,
    dispatching_status character varying,
    run_content_id integer,
    test_case_group_id integer
);


ALTER TABLE public.test_run_execution OWNER TO automation_user;

--
-- Name: test_run_execution_test_run_execution_id_seq; Type: SEQUENCE; Schema: public; Owner: automation_user
--

ALTER TABLE public.test_run_execution ALTER COLUMN test_run_execution_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.test_run_execution_test_run_execution_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: analysis; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.analysis (analysis_id, run_content_id, test_info_id, defect_id, comment, failure_type_id) FROM stdin;
\.
COPY public.analysis (analysis_id, run_content_id, test_info_id, defect_id, comment, failure_type_id) FROM '$$PATH$$/4905.dat';

--
-- Data for Name: capability; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.capability (capability_id, capability_name, capability_marker) FROM stdin;
\.
COPY public.capability (capability_id, capability_name, capability_marker) FROM '$$PATH$$/4909.dat';

--
-- Data for Name: capability_lab; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.capability_lab (capability_lab_id, lab_info_id, capability_id) FROM stdin;
\.
COPY public.capability_lab (capability_lab_id, lab_info_id, capability_id) FROM '$$PATH$$/4907.dat';

--
-- Data for Name: capability_session; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.capability_session (capability_session_id, session_info_id, capability_id) FROM stdin;
\.
COPY public.capability_session (capability_session_id, session_info_id, capability_id) FROM '$$PATH$$/4911.dat';

--
-- Data for Name: capability_test; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.capability_test (capability_test_id, test_info_id, capability_id) FROM stdin;
\.
COPY public.capability_test (capability_test_id, test_info_id, capability_id) FROM '$$PATH$$/4913.dat';

--
-- Data for Name: failure_type; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.failure_type (failure_type_id, failure_type_name) FROM stdin;
\.
COPY public.failure_type (failure_type_id, failure_type_name) FROM '$$PATH$$/4915.dat';

--
-- Data for Name: lab_info; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.lab_info (lab_info_id, lab_name) FROM stdin;
\.
COPY public.lab_info (lab_info_id, lab_name) FROM '$$PATH$$/4917.dat';

--
-- Data for Name: release; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.release (release_id, release_name) FROM stdin;
\.
COPY public.release (release_id, release_name) FROM '$$PATH$$/4919.dat';

--
-- Data for Name: run; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.run (run_id, run_name, run_type_id, release, run_created_at) FROM stdin;
\.
COPY public.run (run_id, run_name, run_type_id, release, run_created_at) FROM '$$PATH$$/4921.dat';

--
-- Data for Name: run_content; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.run_content (run_content_id, run_id, session_info_id, test_info_id, run_content_execution_status, execution_fail_count, test_case_group_id) FROM stdin;
\.
COPY public.run_content (run_content_id, run_id, session_info_id, test_info_id, run_content_execution_status, execution_fail_count, test_case_group_id) FROM '$$PATH$$/4922.dat';

--
-- Data for Name: run_type; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.run_type (run_type_id, run_type_name) FROM stdin;
\.
COPY public.run_type (run_type_id, run_type_name) FROM '$$PATH$$/4925.dat';

--
-- Data for Name: session_info; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.session_info (session_info_id, session_name, test_plan_id, enabled) FROM stdin;
\.
COPY public.session_info (session_info_id, session_name, test_plan_id, enabled) FROM '$$PATH$$/4927.dat';

--
-- Data for Name: session_info_content; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.session_info_content (session_info_content_id, session_info_id, test_info_id, enabled) FROM stdin;
\.
COPY public.session_info_content (session_info_content_id, session_info_id, test_info_id, enabled) FROM '$$PATH$$/4939.dat';

--
-- Data for Name: test_case_group; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.test_case_group (test_case_group_id, test_case_group_name) FROM stdin;
\.
COPY public.test_case_group (test_case_group_id, test_case_group_name) FROM '$$PATH$$/4929.dat';

--
-- Data for Name: test_case_result; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.test_case_result (test_case_result_id, test_info_id, execution_result, start_time, end_time, test_run_execution_id) FROM stdin;
\.
COPY public.test_case_result (test_case_result_id, test_info_id, execution_result, start_time, end_time, test_run_execution_id) FROM '$$PATH$$/4931.dat';

--
-- Data for Name: test_info; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.test_info (test_info_id, test_name, test_suite, priority, test_path, pytest_node_id, test_case_group_id, is_active) FROM stdin;
\.
COPY public.test_info (test_info_id, test_name, test_suite, priority, test_path, pytest_node_id, test_case_group_id, is_active) FROM '$$PATH$$/4933.dat';

--
-- Data for Name: test_plan; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.test_plan (test_plan_id, test_plan_name, description, run_type_id, locked) FROM stdin;
\.
COPY public.test_plan (test_plan_id, test_plan_name, description, run_type_id, locked) FROM '$$PATH$$/4935.dat';

--
-- Data for Name: test_run_execution; Type: TABLE DATA; Schema: public; Owner: automation_user
--

COPY public.test_run_execution (test_run_execution_id, lab_info_id, run_id, dispatching_status, run_content_id, test_case_group_id) FROM stdin;
\.
COPY public.test_run_execution (test_run_execution_id, lab_info_id, run_id, dispatching_status, run_content_id, test_case_group_id) FROM '$$PATH$$/4937.dat';

--
-- Name: analysis_analysis_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.analysis_analysis_id_seq', 1, false);


--
-- Name: capabilities_lab_capability_lab_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.capabilities_lab_capability_lab_id_seq', 1, false);


--
-- Name: capability_capability_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.capability_capability_id_seq', 5, true);


--
-- Name: capability_session_capability_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.capability_session_capability_session_id_seq', 1, false);


--
-- Name: capability_test_capability_test_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.capability_test_capability_test_id_seq', 1, false);


--
-- Name: failure_type_failure_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.failure_type_failure_type_id_seq', 1, false);


--
-- Name: lab_info_lab_info_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.lab_info_lab_info_id_seq', 1, false);


--
-- Name: release_release_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.release_release_id_seq', 1, false);


--
-- Name: run_content_run_content_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.run_content_run_content_id_seq', 1, false);


--
-- Name: run_run_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.run_run_id_seq', 1, false);


--
-- Name: run_type_run_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.run_type_run_type_id_seq', 3, true);


--
-- Name: session_info_content_session_info_content_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.session_info_content_session_info_content_id_seq', 1, false);


--
-- Name: session_info_session_info_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.session_info_session_info_id_seq', 1, false);


--
-- Name: test_case_group_test_case_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.test_case_group_test_case_group_id_seq', 1, false);


--
-- Name: test_case_result_test_case_result_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.test_case_result_test_case_result_id_seq', 1, false);


--
-- Name: test_info_test_info_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.test_info_test_info_id_seq', 1, false);


--
-- Name: test_plan_test_plan_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.test_plan_test_plan_id_seq', 1, false);


--
-- Name: test_run_execution_test_run_execution_id_seq; Type: SEQUENCE SET; Schema: public; Owner: automation_user
--

SELECT pg_catalog.setval('public.test_run_execution_test_run_execution_id_seq', 1, false);


--
-- Name: analysis analysis_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.analysis
    ADD CONSTRAINT analysis_pkey PRIMARY KEY (analysis_id);


--
-- Name: capability_lab capability_lab_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.capability_lab
    ADD CONSTRAINT capability_lab_pkey PRIMARY KEY (capability_lab_id);


--
-- Name: capability capability_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.capability
    ADD CONSTRAINT capability_pkey PRIMARY KEY (capability_id);


--
-- Name: capability_session capability_session_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.capability_session
    ADD CONSTRAINT capability_session_pkey PRIMARY KEY (capability_session_id);


--
-- Name: capability_test capability_test_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.capability_test
    ADD CONSTRAINT capability_test_pkey PRIMARY KEY (capability_test_id);


--
-- Name: failure_type failure_type_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.failure_type
    ADD CONSTRAINT failure_type_pkey PRIMARY KEY (failure_type_id);


--
-- Name: lab_info lab_info_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.lab_info
    ADD CONSTRAINT lab_info_pkey PRIMARY KEY (lab_info_id);


--
-- Name: release release_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.release
    ADD CONSTRAINT release_pkey PRIMARY KEY (release_id);


--
-- Name: run_content run_content_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.run_content
    ADD CONSTRAINT run_content_pkey PRIMARY KEY (run_content_id);


--
-- Name: run run_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.run
    ADD CONSTRAINT run_pkey PRIMARY KEY (run_id);


--
-- Name: run_type run_type_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.run_type
    ADD CONSTRAINT run_type_pkey PRIMARY KEY (run_type_id);


--
-- Name: session_info_content session_info_content_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.session_info_content
    ADD CONSTRAINT session_info_content_pkey PRIMARY KEY (session_info_content_id);


--
-- Name: session_info session_info_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.session_info
    ADD CONSTRAINT session_info_pkey PRIMARY KEY (session_info_id);


--
-- Name: test_case_group test_case_group_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.test_case_group
    ADD CONSTRAINT test_case_group_pkey PRIMARY KEY (test_case_group_id);


--
-- Name: test_case_result test_case_result_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.test_case_result
    ADD CONSTRAINT test_case_result_pkey PRIMARY KEY (test_case_result_id);


--
-- Name: test_info test_info_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.test_info
    ADD CONSTRAINT test_info_pkey PRIMARY KEY (test_info_id);


--
-- Name: test_plan test_plan_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.test_plan
    ADD CONSTRAINT test_plan_pkey PRIMARY KEY (test_plan_id);


--
-- Name: test_run_execution test_run_execution_pkey; Type: CONSTRAINT; Schema: public; Owner: automation_user
--

ALTER TABLE ONLY public.test_run_execution
    ADD CONSTRAINT test_run_execution_pkey PRIMARY KEY (test_run_execution_id);


--
-- PostgreSQL database dump complete
--

                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              