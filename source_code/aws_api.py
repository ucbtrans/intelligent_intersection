#!/usr/bin/env python
# -*- coding: utf-8 -*-
#######################################################################
#
#   This module provides AWS API routines
#
#######################################################################

import os
import platform
import boto3
import time
from datetime import datetime, timedelta
from botocore.errorfactory import ClientError
import json
import api
import rds_config
import pymysql
import csv
from log import get_logger
from state import state2abbrev, abbrev2state
from tile_routines import tiles2image, x2tiles, x2bbox
from intersection import graph_from_jsons, plot_lanes, insert_all_distances
from guideway import plot_guideways
from street import insert_tags_to_streets
from footway import remove_crossing_over_highway, reset_simulated_crosswalks, \
    insert_distances_to_the_center
from meta import get_intersection_diameter

import osmnx as ox
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import requests

logger = get_logger()

if "Windows" in platform.system():
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] \
        = '******************************************'

INTERSECTIONS_BUCKET = 'iit-intersections'
DB_ENDPOINT = rds_config.db_endpoint
DB_USER = rds_config.db_username
DB_PASSWORD = rds_config.db_password
DB_NAME = rds_config.db_name
COMMIT_FREQUENCY = 500
TIME_DELTA = 600
NUMBER_OF_X_TO_PROCESS = 100
SLEEP_TIME = 10
MAX_TRIES = 3

s3 = boto3.resource('s3')


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def dict_2_s3(d, file_name, bucket_name=INTERSECTIONS_BUCKET):
    try:
        s3object = s3.Object(bucket_name, file_name)
        s3object.put(Body=(bytes(json.dumps(d, cls=SetEncoder).encode('UTF-8'))))
    except Exception as e:
        logger.error("Error storing %s in bucket %s" % (file_name, bucket_name))
        logger.error("Exception %r", e)
        print("Exception %r", e)
        return False

    return True


def s3_2_json(file_name, bucket_name=INTERSECTIONS_BUCKET):
    try:
        s3object = s3.Object(bucket_name, file_name)
        file_content = s3object.get()['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error("Exception: file=%s, bucket=%s" % (file_name, bucket_name))
        logger.exception(e)
        print(("Exception: file=%s, bucket=%s" % (file_name, bucket_name)))
        print(e)
        return {"error": "Not found", "file": file_name, "bucket": bucket_name}

    try:
        json_content = json.loads(file_content)
    except:
        logger.error('Wrong file format: %r' % file_name)
        print('Wrong json in s3_2_json: %r' % file_name)
        return {"error": "wrong format", "content": file_name}

    return json_content


def str_2_int_keys(d):
    key_list = list(d.keys())
    for k in key_list:
        try:
            num = int(k)
        except ValueError:
            continue
        val = d[k]
        d[num] = val
        del d[k]


def s3_2_city(file_name, bucket_name=INTERSECTIONS_BUCKET):
    for i in range(MAX_TRIES):
        city_data = s3_2_json(file_name, bucket_name)
        if "error" in city_data:
            continue
        else:
            break
        time.sleep(3)

    if "error" in city_data:
        return city_data
    str_2_int_keys(city_data["nodes"])
    for k in city_data["nodes"]:
        if "street_name" in city_data["nodes"][k]:
            city_data["nodes"][k]["street_name"] = set(sorted(city_data["nodes"][k]["street_name"]))

    return city_data


def city_name_2_file_name(city_name):
    name_list = [x.strip() for x in city_name.split(",")[::-1]]
    if name_list[1] in state2abbrev:
        name_list[1] = state2abbrev[name_list[1]]

    return ("/".join(name_list) + ".json").replace(" ", "_")


def city_name_2_tuple(city_name):
    name_list = [x.strip() for x in city_name.split(",")[::-1]]
    country = name_list[0]

    if len(name_list) > 1:
        state = name_list[1]
    else:
        state = "Californina"

    if len(name_list) > 2:
        city = name_list[2]
    else:
        city = "Berkeley"

    return country, state, city


def does_exist(table_name, condition, input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn
    with conn.cursor() as cur:
        action = "select * from %s where %s;" % (table_name, condition)
        cur.execute(action)
        if cur.rowcount > 0:
            result = True
        else:
            result = False
        cur.close()

    if input_conn is None:
        conn.close()

    return result


def city_2_s3(city_data, input_conn=None, bucket_name=INTERSECTIONS_BUCKET, city_name=None):
    status = "init"
    if city_data is None:
        logger.error("City data is None: %s" % city_name)
        print("City data is None: %s" % city_name)
        status = "error"
    elif "name" not in city_data:
        logger.error("Name not in city data %s" % city_name)
        print("Name not in city data", city_name)
        status = "error"

    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    if status != "error":
        file_name = city_name_2_file_name(city_name)
        dict_2_s3(city_data, file_name, bucket_name=bucket_name)
    else:
        file_name = None

    with conn.cursor() as cur:
        country, state, city = city_name_2_tuple(city_name)
        conditions = "country=\"%s\" and state=\"%s\" and city=\"%s\"" % (country, state, city)
        if file_name is not None and does_exist("cities", conditions, input_conn=conn):
            action = "UPDATE cities SET file_name=\"%s\" where %s;" % (file_name, conditions)
        else:
            country, state, city = city_name_2_tuple(city_name)
            if file_name is not None:
                action = "INSERT INTO cities (country, state, city, file_name, status) " \
                         + "VALUES (\"%s\", \"%s\", \"%s\", \"%s\", \"%s\");" \
                         % (country, state, city, file_name, status)
            else:
                action = "INSERT INTO cities (country, state, city, status) " \
                         + "VALUES (\"%s\", \"%s\", \"%s\", \"%s\");" \
                         % (country, state, city, status)
        print(1, action)
        res = cur.execute(action)
        conn.commit()

        if res:
            logger.info("Updated database: %s, %s, %s" % (country, state, city))
        else:
            logger.info(
                "No change to the database: %s, %s, %s" % (country, state, city))
        cur.close()

    if input_conn is None:
        conn.close()


def get_value_from_db(table_name, column, conditions, input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    with conn.cursor() as cur:
        res = cur.execute("select %s from %s where %s;" % (column, table_name, conditions))
        if res:
            for row in cur:
                result = row[0]
        else:
            result = None
        cur.close()

    if input_conn is None:
        conn.close()

    return result


def set_value_in_db(table_name, column, value, conditions, input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    with conn.cursor() as cur:
        if not does_exist(table_name, conditions, input_conn=conn):
            logger.error("Row not found, table %s, conditions: %s" % (table_name, conditions))
            print("Row not found, table %s, conditions: %s" % (table_name, conditions))
            conn.close()
            return False
        action = "UPDATE %s SET %s=\"%s\" where %s;" % (table_name, column, value, conditions)
        cur.execute(action)
        conn.commit()
        cur.close()

    if input_conn is None:
        conn.close()

    return True


def get_list_from_db(table_name, column_list, conditions, input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    with conn.cursor() as cur:
        action = "select %s from %s where %s;" % (",".join(column_list), table_name, conditions)
        res = cur.execute(action)
        if res:
            for row in cur:
                result = list(row)
        else:
            result = None
        cur.close()
    if input_conn is None:
        conn.close()

    return result


def get_list_of_rows_from_db(table_name, column_list, conditions=None, distinct="",
                             input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    result = []
    with conn.cursor() as cur:
        if conditions is None or len(conditions) == 0:
            action = "select %s %s from %s;" % (distinct, ",".join(column_list), table_name)
        else:
            action = "select %s %s from %s where %s;" % (
                distinct,
                ",".join(column_list),
                table_name, conditions
            )

        cur.execute(action)
        for row in cur:
            result.append(list(row))
        cur.close()
    if input_conn is None:
        conn.close()

    return result


def get_city_from_s3(city_name, bucket_name=INTERSECTIONS_BUCKET):
    country, state, city = city_name_2_tuple(city_name)
    conditions = "country=\"%s\" and state=\"%s\" and city=\"%s\"" % (country, state, city)

    file_status = get_list_from_db("cities", ["file_name", "status", "id"], conditions)
    if file_status is None:
        return {"name": city_name, "status": "error", "error": "city not found"}
    elif file_status[0] is not None and file_status[1] == "ready":
        city_data = s3_2_city(file_status[0], bucket_name=bucket_name)
        city_data['id'] = int(file_status[2])
        if "error" in city_data:
            city_data['name'] = city_name
            city_data['status'] = "error"
            return city_data
        if "status" not in city_data:
            city_data["status"] = "ready"
            return city_data
    elif file_status[1] == "in progress":
        return {'id': int(file_status[2]), "name": city_name, "status": "in progress"}
    elif file_status[1] == "init":
        set_value_in_db("cities", "status", "in progress", conditions)
        return {'id': int(file_status[2]), "name": city_name, "status": "in progress"}
    elif file_status[1] == "error":
        return {'id': int(file_status[2]), "name": city_name, "status": "error"}
    else:
        return None


def get_city_from_s3_by_id(city_id, input_conn=None, bucket_name=INTERSECTIONS_BUCKET):
    file_name = get_value_from_db("cities", "file_name", "id=%d" % city_id, input_conn=input_conn, )
    if file_name is None:
        return None
    else:
        return s3_2_city(file_name, bucket_name=bucket_name)


def process_city(city_name, input_conn=None, sequence=1, bucket_name=INTERSECTIONS_BUCKET):
    country, state, city = city_name_2_tuple(city_name)
    conditions = "country=\"%s\" and state=\"%s\" and city=\"%s\"" % (country, state, city)
    city_data = api.get_data(city_name)
    city_2_s3(city_data, input_conn=input_conn, bucket_name=bucket_name, city_name=city_name)
    if city_data is None:
        set_value_in_db("cities", "status", "error", conditions, input_conn=input_conn)
    elif "name" in city_data:
        insert_intersections(city_data, input_conn=input_conn)
        set_value_in_db("cities", "status", "ready", conditions, input_conn=input_conn)
        logger.info("City %s has been processed" % city_data["name"])
        print(sequence, "City %s has been processed" % city_data["name"])
    return city_data


def process_cities(limit=1, bucket_name=INTERSECTIONS_BUCKET):
    conditions = "status=\"in progress\" ORDER BY ts DESC LIMIT %d" % limit
    cities_to_process = get_list_of_rows_from_db("cities", ["city", "state", "country"], conditions)
    if len(cities_to_process) < limit:
        conditions2 = "status=\"init\" ORDER BY ts DESC LIMIT %d" % limit
        cities_to_process.extend(get_list_of_rows_from_db("cities",
                                                          ["city", "state", "country"],
                                                          conditions2
                                                          )
                                 )
    for lst in cities_to_process:
        process_city(", ".join(lst), bucket_name=bucket_name)


def intersection_2_file_name(city_name, x_street):
    return (city_name_2_file_name(city_name).replace(".json", '') + "/" +
            "-x-".join(x_street).replace(" ", "_")
            ) + ".json"


def insert_intersections(city_data, input_conn=None):
    x_streets = api.get_intersecting_streets(city_data)
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    country, state, city = city_name_2_tuple(city_data["name"])
    conditions = "country=\"%s\" and state=\"%s\" and city=\"%s\"" % (country, state, city)
    city_id = get_value_from_db("cities", "id", conditions, input_conn=conn)

    lst = get_list_of_rows_from_db("x", ["streets"], "city_id=%s" % city_id, input_conn=conn)
    street_set = set([l[0] for l in lst])
    street_list = [" -x- ".join(s) for s in x_streets if " -x- ".join(s) not in street_set]
    insert_list = ["(%s, \"%s\")" % (city_id, s) for s in street_list]

    if insert_list:
        with conn.cursor() as cur:
            action = "INSERT INTO x (city_id, streets) VALUES %s;" % ",".join(insert_list)
            num_of_inserted = cur.execute(action)
            logger.info("Inserted %d intersections. %s" % (num_of_inserted, city_data["name"]))
            print("Inserted %d intersections. %s" % (num_of_inserted, city_data["name"]))
            conn.commit()
            cur.close()
    if input_conn is None:
        conn.close()

    return x_streets


def process_intersection(street_tuple, x_id, city_data, input_conn=None, sequence=1,
                         bucket_name=INTERSECTIONS_BUCKET):
    if city_data is None or street_tuple is None:
        logger.error("No city data")
        print("No city data")
        return None
    elif "error" in city_data:
        set_value_in_db("x", "status", "error", "id=%d" % x_id, input_conn=input_conn)
        print("X id=%s" % x_id, city_data)
        return None

    x = api.get_intersection(street_tuple, city_data)
    if x is None:
        size = 50.0
        x = api.get_intersection(street_tuple, city_data, size=size)
        logger.error("Size=%r, %r, %s" % (size, city_data['name'], street_tuple))
        print("Size=%r, %r, %s" % (size, city_data['name'], street_tuple))

    if x is None:
        logger.error("Error getting intersection %s, %r" % (city_data['name'], street_tuple))
        set_value_in_db("x", "status", "error", "id=%d" % x_id, input_conn=input_conn)
        print("Error getting intersection %d %s, %r" % (x_id, city_data['name'], street_tuple))
        return None

    try:
        guideways = api.get_guideways(x)
        cz = api.get_all_conflict_zones(x, all_guideways=guideways)
        for c in cz:
            del c['polygon']
    except Exception as e:
        guideways = None
        cz = None
        logger.error("Error getting guideways")

    x['guideway'] = guideways
    x['blind_zones'] = cz
    x['id'] = x_id

    file_name = intersection_2_file_name(city_data["name"], street_tuple)

    dict_2_s3(x, file_name)
    set_value_in_db("x", "file_name", file_name, "id=%d" % x_id, input_conn=input_conn)
    set_value_in_db("x", "status", "ready", "id=%d" % x_id, input_conn=input_conn)
    logger.info("Intersection %d %s added to db" % (x_id, file_name))
    print(sequence, "Intersection %d %s added to db" % (x_id, file_name))
    return x


def process_intersections(city_id=None, limit=1, bucket_name=INTERSECTIONS_BUCKET):
    if city_id is None:
        cond = "status=\"in progress\" ORDER BY ts DESC LIMIT %d" % limit
        cond2 = "status=\"init\" ORDER BY ts DESC LIMIT %d" % limit
        c_d = None
    else:
        cond = "city_id=%d, status=\"in progress\" ORDER BY ts DESC LIMIT %d" % (city_id, limit)
        cond2 = "ci%d, status=\"init\" ORDER BY ts DESC LIMIT %d" % (city_id, limit)
        c_d = get_city_from_s3_by_id(id, bucket_name=bucket_name)

    x_to_process = get_list_of_rows_from_db("x", ["id", "streets", "city_id"], cond)
    if len(x_to_process) < limit:
        x_to_process.extend(get_list_of_rows_from_db("x", ["id", "streets", "city_id"], cond2))

    for lst in x_to_process:
        street_tuple = tuple(lst[1].replace("_", " ").split(" -x- "))
        if c_d is None:
            city_data = get_city_from_s3_by_id(int(lst[2]), bucket_name=bucket_name)
        else:
            city_data = c_d
        if city_data is None:
            logger.error("City data not available id=%r" % city_id)
            print("City data not available id=%r" % city_id)
            continue

        process_intersection(street_tuple, int(lst[0]), city_data, bucket_name=bucket_name)


def get_requested_id(table_name="cities", input_conn=None, delta=TIME_DELTA):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn

    with conn.cursor() as cur:
        # cur.execute("LOCK TABLES cities WRITE, x WRITE;")

        select = "select id from %s " % table_name
        where = "where status=\"requested\" or (status=\"in progress\" and ts < \"%s\") " % (
                datetime.utcnow() - timedelta(seconds=delta))
        action = select + where + "order by ts DESC limit 1;"

        res = cur.execute(action)
        cur.close()

    if res:
        for row in cur:
            candidate_id = row[0]
            break
    else:
        with conn.cursor() as cur:
            select = "select id from %s where status != \"in progress\" and status != \"error\"" \
                     % table_name
            action = select + " order by status asc, ts asc limit 1;"

            cur.execute(action)
            for row in cur:
                candidate_id = row[0]
                break
            cur.close()

    with conn.cursor() as cur:
        action = "update %s set status=\"in progress\" , ts = CURRENT_TIMESTAMP() where id=%s;" % (
            table_name, candidate_id)

        cur.execute(action)
        conn.commit()
        # cur.execute("UNLOCK TABLES;")
        cur.close()

    if input_conn is None:
        conn.close()

    return candidate_id


def get_city_for_processing(row_id, input_conn=None):
    lst = get_list_from_db("cities", ["city", "state", "country"], "id=%s" % row_id,
                           input_conn=input_conn)
    return (", ".join(lst)).replace("_", " ")


def get_x_for_processing(row_id, input_conn=None):
    lst = get_list_from_db("x", ["city_id", "streets"], "id=%s" % row_id, input_conn=input_conn)
    street_tuple = tuple(lst[1].replace("_", " ").split(" -x- "))
    return street_tuple, lst[0]


def get_x_by_id(x_id, input_conn=None):
    file_name = get_value_from_db("x", "file_name", "id=%s" % x_id, input_conn=input_conn)
    if file_name is None:
        return None
    else:
        x = s3_2_json(file_name)
        x["file_name"] = file_name
        x["x_id"] = x_id
        return x


def process_all(process_id=None):
    city_seq = 0
    x_seq = 0
    conn = None
    ca_cities, all_cities = read_list_of_cities()
    while True:
        try:
            try:
                conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                       connect_timeout=5)
            except pymysql.MySQLError as e:
                logger.error("Could not connect to MySQL instance: %r", e)
                return
            if True:
                NUMBER_OF_X_TO_PROCESS = 10
                for i in range(NUMBER_OF_X_TO_PROCESS):
                    if process_id is None:
                        # x_id = get_requested_id("x", input_conn=conn)
                        x_id = get_value_from_db("x", "id",
                                                 "file_name is null order by id limit 1 ",
                                                 input_conn=conn)
                    else:
                        x_id = process_id
                    street_tuple, city_id = get_x_for_processing(x_id, input_conn=conn)

                    # Reload the city data for each intersection
                    city_data = get_city_from_s3_by_id(city_id, input_conn=conn)
                    x_seq += 1
                    process_intersection(street_tuple, x_id, city_data, sequence=x_seq,
                                         input_conn=conn)
                    if process_id is not None:
                        break

            if False:
                city_id = get_requested_id("cities", input_conn=conn)
                city_name = get_city_for_processing(city_id, input_conn=conn)
                city_seq += 1
                process_city(city_name, sequence=city_seq, input_conn=conn)

            if False:
                city_seq += 1
                ca_cities, all_cities = get_remaining_cities(ca_cities, all_cities)
                add_a_city(ca_cities, all_cities, sequence=city_seq, input_conn=conn)
                print("remained cities:", len(ca_cities), len(all_cities))

            conn.close()
            if process_id is not None:
                break
        except Exception as e:
            if conn is not None and conn.open:
                conn.close()
            logger.error("Exception: %r" % e)
            print("Exception: %r" % e)
            time.sleep(SLEEP_TIME)


def read_list_of_cities(file_name="uscities.csv"):
    # Read input csv
    ca_cities = set()
    all_cities = set()

    for c in csv.DictReader(open(file_name)):
        city_name = "%s, %s, %s" % (c["city_ascii"], c["state_name"], "USA")
        if c["state_name"] == "California":
            ca_cities.add(city_name)
        else:
            all_cities.add(city_name)
    return ca_cities, all_cities


def get_city_list_from_db():
    rows = get_list_of_rows_from_db("cities", ["city", "state", "country"])
    return set([", ".join(row) for row in rows])


def get_remaining_cities(ca_cities, all_cities, db_c=None):
    if db_c is None:
        db_cities = get_city_list_from_db()
    else:
        db_cities = db_c
    for c in db_cities:
        ca_cities.discard(c)
        all_cities.discard(c)
    return ca_cities, all_cities


def add_a_city(ca_cities, all_cities, sequence=0, input_conn=None):
    if len(ca_cities):
        process_city(ca_cities.pop(), sequence=sequence, input_conn=input_conn)
    elif len(all_cities):
        process_city(all_cities.pop(), sequence=sequence, input_conn=input_conn)


def cleanup_list_of_intersections():
    condition1 = "(select count(*) from x where city_id=c.id) < 1" \
                 + " order by id asc"
    # city_id_list = get_list_of_rows_from_db("cities c", ["distinct id"], conditions=condition1)

    condition2 = "city_id>68 and status=\"init\" order by city_id asc"
    city_id_list = get_list_of_rows_from_db("x", ["distinct city_id"], conditions=condition2)
    sq = 0
    for city_id in city_id_list:

        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
        c_i = city_id[0]
        lst = get_list_from_db("cities", ["city", "state", "country"], "id=%s" % c_i,
                               input_conn=None)
        city_name = ", ".join(lst)
        print(c_i, city_name)
        sq += 1
        city_data = process_city(city_name, sequence=sq, input_conn=conn)
        x_streets = api.get_intersecting_streets(city_data)
        x_s = get_list_of_rows_from_db("x", ["id", "streets", "status"],
                                       conditions="city_id=\"%s\"" % c_i,
                                       input_conn=conn)
        s3_set = set([" -x- ".join(list(x)) for x in x_streets])
        db_set = set([x[1] for x in x_s])
        s3_len = len(s3_set)
        db_len = len(db_set)
        missing = [x for x in s3_set if x not in db_set]
        print(s3_len, db_len, len(x_streets), len(x_s), len(missing))
        if missing:
            print("Need to process")
            print("Missing in db", missing)
            process_city(city_data["name"], input_conn=conn)

        num_del = 0
        for x in x_s:
            if x[1] not in s3_set:
                action = "delete from x where id=%s;" % x[0]
                with conn.cursor() as cur:
                    res = cur.execute(action)
                    if res:
                        print(res, "Deleted", x)
                        num_del += 1
                    else:
                        print(res, "Error", x)
                    conn.commit()

        if num_del:
            if city_data is None:
                print(c_i, "City is None", "Deleted:", num_del)
            else:
                print(c_i, city_data["name"], "Deleted:", num_del)

        conn.close()


def get_web_image(x, file_name, zoom=19, delta_lon=0.00002, delta_lat=-0.00002, alpha=0.7,
                  input_conn=None):
    if x is None:
        return None

    x_id = x["x_id"]
    G = graph_from_jsons(x["cropped_intersection"], retain_all=True, simplify=False)
    edges = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    w, s, e, n = edges.total_bounds

    x_min, x_max, y_min, y_max = x2tiles(e, w, n, s, zoom=zoom)
    east, west, north, south = x2bbox(x_min, x_max, y_min, y_max, zoom=zoom)
    tiles2image(x_min, x_max, y_min, y_max, zoom=zoom, source="bing", ttype="mapbox.satellite",
                image_name=file_name)

    logger.debug(
        "Terrain created: %r %r" % ((x_min, x_max, y_min, y_max), (east, west, north, south)))

    img = plt.imread(file_name)
    fig_height = 15
    fig_width = None
    equal_aspect = False
    bbox_aspect_ratio = (north - south) / (east - west)
    if fig_width is None:
        fig_width = fig_height / bbox_aspect_ratio

    # create the figure and axis
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    # set the extent of the figure

    ax.set_ylim((south, north))
    ax.set_xlim((west, east))

    # configure axis appearance
    xaxis = ax.get_xaxis()
    yaxis = ax.get_yaxis()

    xaxis.get_major_formatter().set_useOffset(False)
    yaxis.get_major_formatter().set_useOffset(False)
    node_Ys = [float(y) for _, y in G.nodes(data='y')]

    label = ", ".join(x["streets"]) + ", " + x["city"]
    if bbox_aspect_ratio > 1.5:
        font_size = 10
    else:
        font_size = 14
    plt.xlabel(label, fontsize=font_size)

    if equal_aspect:
        # make everything square
        ax.set_aspect('equal')
        fig.canvas.draw()
    else:
        # if the graph is not projected, conform the aspect ratio to not stretch the plot
        if G.graph['crs'] == ox.settings.default_crs:
            coslat = np.cos((min(node_Ys) + max(node_Ys)) / 2. / 180. * np.pi)
            ax.set_aspect(1. / coslat)
            fig.canvas.draw()

    if south > 35.0:
        boundaries = [west + delta_lon, east + delta_lon, south + delta_lat, north + delta_lat]
    else:
        boundaries = [west, east, south, north]

    ax.imshow(img, zorder=0, extent=boundaries, aspect=1. / coslat)
    if bbox_aspect_ratio > 1.5:
        start, end = ax.get_xlim()
        ax.xaxis.set_ticks(np.arange(start, end, 0.001))
        fig.canvas.draw()

    f1, ax1 = plot_lanes(x['merged_tracks'],
                         fig=fig, ax=ax,
                         cropped_intersection=None,
                         fig_height=fig_height,
                         fig_width=None,
                         axis_off=False,
                         edge_linewidth=1,
                         margin=0,
                         fcolor='#C0C0C0',
                         edge_color='#000000',
                         alpha=1.0,
                         linestyle='solid'
                         )
    gb = api.get_guideways(x, guideway_type='all bicycle')
    gv = api.get_guideways(x, guideway_type='all vehicle')
    cc = api.get_crosswalks(x)

    guideway_fig, guideway_ax = plot_guideways(gv, fig=f1, ax=ax1, alpha=alpha,
                                               fc='#FFFF66', ec='b', fig_height=fig_height,
                                               fig_width=None)
    guideway_fig, guideway_ax = plot_guideways(gb, fig=guideway_fig, ax=guideway_ax, alpha=alpha,
                                               fc='#FFFF66', ec='b', fig_height=fig_height,
                                               fig_width=None)
    guideway_fig, guideway_ax = plot_guideways(cc, fig=guideway_fig, ax=guideway_ax, alpha=1.0,
                                               fc='w', ec='b', fig_height=fig_height,
                                               fig_width=None)
    f_n = file_name.replace("png", "jpg")

    guideway_fig.savefig(f_n, format="jpg", quality=95, dpi=72, progressive=True)
    logger.debug("Local image saved %s" % f_n)
    image_2_s3(f_n, x_id, input_conn=input_conn)
    plt.close(f1)
    return guideway_fig


def get_web_image_by_x_id(x_id, input_conn=None, my_public_ip="windows"):
    logger.info("Start creating an image for x_id: %s by %s" % (x_id, my_public_ip))
    print(datetime.now(), "Start creating an image for x_id: %s by %s" % (x_id, my_public_ip))
    set_value_in_db("x", "worker", my_public_ip, "id=%s" % x_id, input_conn=input_conn)
    set_value_in_db("x", "status", "img in progress", "id=%s" % x_id, input_conn=input_conn)
    x = get_x_by_id(x_id, input_conn=input_conn)
    if x is None:
        logger.error("Intersection no found: %s", x_id)
        return None
    insert_all_distances(x)
    insert_tags_to_streets(x)
    x["crosswalks"] = remove_crossing_over_highway(x)
    reset_simulated_crosswalks(x)
    x["guideway"] = api.get_guideways(x)
    insert_distances_to_the_center(x)
    x["meta_data"]["diameter"] = get_intersection_diameter(x)
    dict_2_s3(x, x["file_name"])
    logger.debug("Intersection loaded %r, %s" % (x["streets"], x["city"]))
    print(datetime.now(), "Intersection loaded %r, %s" % (x["streets"], x["city"]))
    file_name = "temp.png"  # str(x_id) + ".png"
    return get_web_image(x, file_name, input_conn=input_conn)


def image_2_s3(image_file, x_id, input_conn=None, my_public_ip="windows"):
    s3_file = get_value_from_db("x", "file_name", "id=%s" % x_id, input_conn=input_conn)
    s3_image_file = s3_file.replace(".json", "_" + x_id + ".jpg")
    s3.Bucket(INTERSECTIONS_BUCKET).upload_file(image_file, s3_image_file,
                                                ExtraArgs={"ACL": 'public-read',
                                                           'ContentType': 'image/jpeg'})
    set_value_in_db("x", "image", s3_image_file, "id=%s" % x_id, input_conn=input_conn)
    set_value_in_db("x", "status", "ready", "id=%s" % x_id, input_conn=input_conn)

    logger.info("Saved image %s in s3 %s" % (x_id, s3_image_file))
    print(datetime.now(), "Saved image %s in s3 %s" % (x_id, s3_image_file))


def register_worker(my_public_ip, input_conn=None):
    if input_conn is None:
        try:
            conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                                   connect_timeout=5)
        except pymysql.MySQLError as e:
            logger.error("Could not connect to MySQL instance: %r", e)
            return
    else:
        conn = input_conn
    w = get_value_from_db("workers", "worker", "worker=\"%s\"" % my_public_ip, input_conn=conn)
    if w is not None:
        set_value_in_db("workers", "status", "active", "worker=\"%s\"" % my_public_ip,
                        input_conn=conn)
        logger.info("Updated worker %s" % my_public_ip)
        print("Updated worker %s" % my_public_ip)
    else:
        with conn.cursor() as cur:
            action = "INSERT INTO workers (worker, status, type) VALUES (\"%s\", \"active\", \"linux\");" \
                     % my_public_ip
            cur.execute(action)
            conn.commit()
            cur.close()
        logger.info("Registered worker %s" % my_public_ip)
        print("Registered %s" % my_public_ip)

    total = get_value_from_db("x", "count(*)",
                              "worker=\"%s\" and image is not null " % my_public_ip,
                              input_conn=conn)
    with conn.cursor() as cur:
        action = "UPDATE workers SET processed=%d where worker=\"%s\";" % (total, my_public_ip)
        cur.execute(action)
        conn.commit()
        cur.close()
    if input_conn is None:
        conn.close()

    return total


def process_images(x_id=None):
    my_public_ip = requests.get('https://api.ipify.org').text
    sleep_time = ((int(my_public_ip.split(".")[-1])) % 100) / 1000.0
    logger.debug("Sleep time %r" % sleep_time)
    print("Sleep time %r" % sleep_time)

    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    total = register_worker(my_public_ip, input_conn=conn)
    limit = 20
    while True:
        if x_id is None:
            with conn.cursor() as cur:
                action = ("update x set worker=\"%s\" " % my_public_ip) \
                         + "where worker is null and image is null and status !=\"error\"" + \
                         ("order by id limit %d;" % limit)
                cur.execute(action)
                conn.commit()
                cur.close()
            lst = get_list_of_rows_from_db("x", ["id"],
                                           "worker=\"%s\" and image is null and status!=\"error\""
                                           % my_public_ip,
                                           input_conn=conn)
            id_list = [i[0] for i in lst]
            if len(id_list) > limit:
                set_value_in_db("workers", "status", "error", "worker=\"%s\"" % my_public_ip,
                                input_conn=conn)
            else:
                set_value_in_db("workers", "status", "active", "worker=\"%s\"" % my_public_ip,
                                input_conn=conn)
        else:
            id_list = [x_id]

        if len(id_list) == 0:
            break

        try:
            for id_to_process in id_list:
                fig = get_web_image_by_x_id(str(id_to_process), input_conn=conn,
                                            my_public_ip=my_public_ip)
                plt.close(fig)
                total += 1
                time.sleep(sleep_time)
                with conn.cursor() as cur:
                    action = "UPDATE workers SET processed=%d where worker=\"%s\";" % (
                        total, my_public_ip)
                    cur.execute(action)
                    conn.commit()
                    cur.close()

            if x_id is not None:
                set_value_in_db("workers", "status", "stopped", "worker=\"%s\"" % my_public_ip,
                                input_conn=conn)
                if conn is not None and conn.open:
                    conn.close()
                return

        except Exception as e:
            if conn is not None and conn.open:
                conn.close()
            logger.error("Exception: %r" % e)
            print("Exception: %r" % e)
            set_value_in_db("x", "status", "error", "id=%s" % id_to_process)
            logger.error("Intersection error %s" % id_to_process)
            print("Intersection error %s" % id_to_process)
            if x_id is not None:
                break
            else:
                time.sleep(SLEEP_TIME)
                try:
                    conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD,
                                           db=DB_NAME,
                                           connect_timeout=5)
                except pymysql.MySQLError as e:
                    logger.error("Could not connect to MySQL instance: %r", e)
                    return

    set_value_in_db("workers", "status", "stopped",
                    "worker=\"%s\"" % my_public_ip)  # , input_conn=conn)
    if conn is not None and conn.open:
        conn.close()


def reset_south_california(border_lat=35.0):
    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    lst = get_list_of_rows_from_db("cities", ["id"], conditions="id > 0 order by id",
                                   input_conn=conn)
    id_list = []
    for l in lst:
        city_id = l[0]
        city_data = get_city_from_s3_by_id(city_id, input_conn=conn)

        if city_data is not None and "name" in city_data:
            print(city_id, city_data["name"])
        else:
            print(city_id, "No name")
            continue

        if "nodes" not in city_data:
            print(city_id, "No nodes")
            continue

        for n in city_data["nodes"]:
            lat = city_data["nodes"][n]["y"]
            break
        if lat > border_lat:
            continue
        # Reset images
        with conn.cursor() as cur:
            action = "UPDATE x set image=null where city_id=%s and id>0" % city_id
            cur.execute(action)
            conn.commit()
            cur.close()
        print("South - erased", city_id, city_data["name"])
        id_list.append(city_id)
    conn.close()
    print(id_list)


def get_list_of_files(bucket_name=INTERSECTIONS_BUCKET):
    file_list = []
    for f in s3.Bucket(bucket_name).objects.all():
        file_list.append(f.key)
        print(f.key)
    return file_list


def create_db():
    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    city_d = {}
    city_id = {}
    with open("file_list.txt") as f:

        # Cities
        i = 0
        for line in f:
            if "-x-" in line:
                continue
            if "jpg" in line:
                continue
            l = line.replace("\n", '')
            no_json = l.replace(".json", '')
            lst = no_json.split("/")
            if len(lst) != 3:
                continue
            if len(lst[-1]) == 0:
                continue
            action = "INSERT into cities (country, state, city, file_name, status) " \
                     + "values(\"%s\", \"%s\", \"%s\", \"%s\", \"ready\");" \
                     % (lst[0], lst[1], lst[2], l)
            with conn.cursor() as cur:
                # cur.execute(action)
                # conn.commit()
                # cur.close()
                i += 1
            c_id = get_value_from_db("cities", "id", "file_name=\"%s\" " % l, input_conn=conn)
            city_id[no_json] = c_id
            city_d[no_json] = []
            print(i, c_id, action)

    with open("file_list.txt") as f:

        # -x-
        i = 0
        for line in f:
            if "-x-" not in line:
                continue
            if "jpg" in line:
                continue
            l = line.replace("\n", '')
            lst = l.split("/")
            if len(lst) != 4:
                continue
            l = line.replace("\n", '')
            no_json = l.replace(".json", '')
            lst = no_json.split("/")
            c = "/".join(lst[:-1])
            city_d[c].append(lst[-1])

    x_d = {}
    with open("file_list.txt") as f:

        # -x-
        i = 0
        for line in f:
            if "-x-" not in line:
                continue
            if "jpg" not in line:
                continue
            l = line.replace("\n", '')
            lst = l.split("/")
            if len(lst) != 4:
                continue
            l = line.replace("\n", '')
            no_json = "_".join(l.split("_")[:-1])
            x_d[no_json] = l

    i = 0
    for c in city_d:
        insert_list = [
            "(%s, \"%s\", \"%s\", \"ready\")" % (city_id[c], s, c + "/" + s + ".json") for s in
            city_d[c]]
        i += 1
        # print(i, c, insert_list)
        if insert_list:
            for j in range(0, len(insert_list), 100):
                with conn.cursor() as cur:
                    action = "INSERT INTO x (city_id, streets, file_name, status) VALUES %s;" % ",".join(
                        insert_list[j:j + 100])
                    # print(i, action)
                    num_of_inserted = cur.execute(action)
                    print(i, "Inserted %d intersections. %s" % (num_of_inserted, c))
                    conn.commit()
                    cur.close()

    print(len(city_d))
    print(len(city_id))
    print(len(x_d))
    i = 0
    for x in x_d:
        i += 1
        streets = x.split("/")[-1]
        c = "/".join(x.split("/")[:-1])
        conditions = "city_id=%s and streets=\"%s\"" % (city_id[c], streets)
        set_value_in_db("x", "image", x_d[x], conditions, input_conn=conn)
        print(x, x_d[x], conditions)

    if conn is None:
        conn.close()


def get_all_x_per_city(country, state, city, input_conn=None):
    city_id = get_value_from_db("cities", "id",
                                "country=\"%s\" and state=\"%s\" and city=\"%s\"" % (
                                country, state, city),
                                input_conn=input_conn)
    lst = get_list_of_rows_from_db("x", ["file_name"],
                                   "city_id=%s order by file_name" % city_id,
                                   input_conn=input_conn)
    return [c[0] for c in lst]


def get_all_cities_per_state(country, state, input_conn=None):
    lst = get_list_of_rows_from_db("cities", ["city"],
                                   "country=\"%s\" and state=\"%s\" order by city" % (
                                   country, state),
                                   input_conn=input_conn)
    return [c[0] for c in lst]


def get_all_states_per_coutntry(country, input_conn=None):
    lst = get_list_of_rows_from_db("cities", ["state"], "country=\"%s\" order by state" % country,
                                   distinct="distinct",
                                   input_conn=input_conn)
    return [c[0] for c in lst]


def create_lists_of_x(country="USA"):
    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    for state in get_all_states_per_coutntry(country, input_conn=conn):
        for city in get_all_cities_per_state(country, state, input_conn=conn):
            with open("list.txt", "w") as fw:
                for x in get_all_x_per_city(country, state, city, input_conn=conn):
                    fw.write("%s\n" % x)
            s3_file = country + "/" + state2abbrev[state] + "/" + city + "/" + "intersection_list.txt"
            s3.Bucket(INTERSECTIONS_BUCKET).upload_file("list.txt", s3_file,
                                                        ExtraArgs={"ACL": 'public-read',
                                                                   'ContentType': '	text/plain'})
            logger.debug("%s created" % s3_file)
            print("%s created" % s3_file)
    conn.close()


def create_lists_of_cities(country="USA"):
    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    for state in get_all_states_per_coutntry(country, input_conn=conn):
        with open("list.txt", "w") as fw:
            for city in get_all_cities_per_state(country, state, input_conn=conn):
                fw.write("%s\n" % city)
        s3_file = country + "/" + state2abbrev[state] + "/" + "city_list.txt"
        s3.Bucket(INTERSECTIONS_BUCKET).upload_file("list.txt", s3_file,
                                                    ExtraArgs={"ACL": 'public-read',
                                                               'ContentType': '	text/plain'})
        logger.debug("%s created" % s3_file)
        print("%s created" % s3_file)
    conn.close()


def create_lists_of_states(country="USA"):
    try:
        conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                               connect_timeout=5)
    except pymysql.MySQLError as e:
        logger.error("Could not connect to MySQL instance: %r", e)
        return

    with open("list.txt", "w") as fw:
        for state in get_all_states_per_coutntry(country, input_conn=conn):
            fw.write("%s\n" % state2abbrev[state])
    s3_file = country + "/" + "state_list.txt"
    s3.Bucket(INTERSECTIONS_BUCKET).upload_file("list.txt", s3_file,
                                                ExtraArgs={"ACL": 'public-read',
                                                           'ContentType': '	text/plain'})
    logger.debug("%s created" % s3_file)
    print("%s created" % s3_file)
    conn.close()


def create_all_list():
    create_lists_of_states()
    create_lists_of_cities()
    create_lists_of_x()


if __name__ == "__main__":
    # cleanup_list_of_intersections()
    # print(ca_cities)
    # for i in range(1744, 1748):
    # for i in [42, 15003,7]:
    # process_images()
    create_lists_of_states()
    # reset_south_california()
    # for i in range(1, 100):
    # process_images(str(i))
    # process_city("Los Angeles, California, USA")
    # lst = get_list_of_rows_from_db("x", ["id"], conditions="status=\"error\"")
    # process_city("San Diego, California, USA")
    # for l in lst:
    # process_all()

    # get_list_of_files()
    # create_db()
