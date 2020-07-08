import pymysql
import json
import boto3
import os
from botocore.errorfactory import ClientError
from log import get_logger, init_logger
from state import abbrev2state

logger = get_logger()

DB_ENDPOINT = "iit-db-prod-1.*********.us-west-1.rds.amazonaws.com"
DB_USER = "********"
DB_PASSWORD = "************"
DB_NAME = "iit_db_prod"
URL_BASE = "https://14blfgfr47.execute-api.us-west-1.amazonaws.com/prod/get"
INTERSECTIONS_BUCKET = 'iit-intersections'
S3_FILE_URL = "https://iit-intersections.s3-us-west-1.amazonaws.com/"

if not os.environ.get("AWS_EXECUTION_ENV"):
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] \
        = '****************'


def lambda_handler(event, context):
    conn = pymysql.connect(DB_ENDPOINT, user=DB_USER, passwd=DB_PASSWORD, db=DB_NAME,
                           connect_timeout=5)
    if conn is None:
        logger.error("Could not connect to MySQL instance: %r")
        html_error = "<!DOCTYPE html><html><body><h1>DB Error</h1><p> %s </p></body></html>"
        return {'statusCode': 200, "body": html_error, 'headers': {'Content-Type': 'text/html'}}

    lst = get_list_of_items_from_db(table_name="x", column_name="count(*)",
                                    conditions="status=\"ready\"", distinct="", order="", conn=conn)
    if lst:
        num_of_x = lst[0]
    else:
        num_of_x = 1000
    lst, url_list, list_title, sub_title, image, prev_next = get_list(event, conn=conn)
    output_list = get_html_list(lst, url_list, list_title, sub_title, prev_next, image=image)

    html_code1 = "<!DOCTYPE html><html><body><h2>UC Berkeley</h2><h1>Intelligent Intersections</h1>"
    html_code = html_code1 + "<p>Total processed: %s intersections</p>%s</body></html>" % (
        num_of_x, output_list)

    conn.close()

    return {'statusCode': 200, "body": html_code, 'headers': {'Content-Type': 'text/html'}}
    # return {'statusCode': 200, 'body': ', '.join(result), 'headers': {'Content-Type': 'application/json'}} # {"result": ", ".join(result)}


def get_state(s):
    state = s.replace("_", " ")
    if state in abbrev2state:
        return abbrev2state[state]
    else:
        return state


def get_country(c):
    country = c.replace("_", " ")
    if country == "usa":
        return "USA"
    else:
        return country


def get_city(c):
    return c.replace("_", " ")


def get_x(x):
    return x.replace("_", " ")


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
        action = "UPDATE %s SET %s=\"%s\" where %s;" % (table_name, column, value, conditions)
        cur.execute(action)
        conn.commit()
        cur.close()

    if input_conn is None:
        conn.close()

    return True


def get_list_of_items_from_db(table_name="cities", column_name="city",
                              conditions="country=\"USA\"", distinct="", order="", conn=None):
    result = []
    with conn.cursor() as cur:
        action = "select %s %s from %s where %s %s;" % (
            distinct, column_name, table_name, conditions, order)

        cur.execute(action)
        for row in cur:
            result.append(row[0])
        cur.close()
    return result


def get_list_of_multiple_columns_from_db(table_name="cities", column_list=["id"],
                                         conditions="country=\"USA\"", distinct="", order="",
                                         conn=None):
    result = []
    with conn.cursor() as cur:
        action = "select %s %s from %s where %s %s;" % (
            distinct, ", ".join(column_list), table_name, conditions, order)
        cur.execute(action)
        for row in cur:
            result.append(list(row))
        cur.close()

    return result


def get_prev_next(x_id, conn=None):

    next_lst = get_list_of_items_from_db(table_name="x", column_name="id", conditions="id>%s"%x_id, order="order by id LIMIT 1", conn=conn)
    prev_lst = get_list_of_items_from_db(table_name="x", column_name="id", conditions="id<%s" % x_id, order="order by id desc LIMIT 1", conn=conn)

    if next_lst:
        nxt = str(next_lst[0])
    else:
        nxt = None
    if prev_lst:
        prv = str(prev_lst[0])
    else:
        prv = None

    return prv, nxt


def get_prev_next_html(prv, nxt):
    if prv:
        p = "<a href=\"%s\">Prev</a></li>" % (URL_BASE + "?x_id=" + prv)
    else:
        p = "Prev"
    if nxt:
        n = "<a href=\"%s\">Next</a></li>" % (URL_BASE + "?x_id=" + nxt)
    else:
        n = "Next"

    return "<p>" + p + "&nbsp;&nbsp;&nbsp;" + n + "</p>"


def s3_2_json(file_name, bucket_name=INTERSECTIONS_BUCKET):
    s3 = boto3.resource('s3')
    try:
        s3object = s3.Object(bucket_name, file_name)
        file_content = s3object.get()['Body'].read().decode('utf-8')
    except ClientError:
        logger.error("Not found: file=%s, bucket=%s" % (file_name, bucket_name))
        return {"error": "Not found", "file": file_name, "bucket": bucket_name}

    try:
        json_content = json.loads(file_content)
    except:
        logger.error('Wrong file format: %r' % json_content[:100])
        return {"error": "wrong format", "content": file_content[:100]}

    return json_content


def get_list(event, conn=None):
    url = URL_BASE + "?country="
    sub_title = None
    image = None
    prev_next = ""
    if "queryStringParameters" in event and "x_id" in event["queryStringParameters"]:
        # Get intersection data
        prv, nxt = get_prev_next(event["queryStringParameters"]["x_id"], conn=conn)
        prev_next = get_prev_next_html(prv, nxt)
        list_type = "Error"
        table_name = "x left outer join cities c on c.id=city_id"
        column_list = ["x.file_name", "x.status", "streets", "city", "state", "country", "x.image"]
        conditions = "x.id=%s" % event["queryStringParameters"]["x_id"]
        l_l = get_list_of_multiple_columns_from_db(table_name=table_name,
                                                   column_list=column_list,
                                                   conditions=conditions,
                                                   distinct="",
                                                   order="", conn=conn)
        if len(l_l):
            x_data = s3_2_json(l_l[0][0])
            file_link = S3_FILE_URL + l_l[0][0]
            x_data["meta_data"]["status"] = l_l[0][1]
            x_data["meta_data"]["download"] = "<a href=\"%s\">%s</a>" % (file_link, file_link)
            x_data["meta_data"]["id"] = event["queryStringParameters"]["x_id"]
            lst = ["%s = %s" % (k, str(x_data["meta_data"][k])) for k in
                   sorted(list(x_data["meta_data"].keys()))]
            url_list = [None] * len(lst)
            streets = l_l[0][2]
            city = l_l[0][3].replace(" ", "_")
            state = l_l[0][4].replace(" ", "_")
            country = l_l[0][5].replace(" ", "_")
            image = l_l[0][6]
            country_url = URL_BASE + "?country=%s" % country
            state_url = URL_BASE + "?country=%s&state=%s" % (country, state)
            city_url = URL_BASE + "?country=%s&state=%s&city=%s" % (country, state, city)
            list_type = "%s, <a href =\"%s\">%s</a>, <a href =\"%s\">%s</a>, <a href =\"%s\">%s</a>" % (
                streets, city_url, city.replace("_", " "), state_url, state.replace("_", " "),
                country_url, country.replace("_", " "))
        else:
            lst = []
            url_list = []

    elif "queryStringParameters" not in event or "country" not in event["queryStringParameters"]:
        # Get list of countries
        list_type = "Countries"
        lst = get_list_of_items_from_db(table_name="cities", column_name="country",
                                        conditions="country is not null", distinct="distinct",
                                        order="order by country", conn=conn)
        url_list = [URL_BASE + "?country=%s" % c.replace(" ", "_") for c in lst]
    elif "state" not in event["queryStringParameters"]:
        # Get list of states
        country = get_country(event["queryStringParameters"]["country"])
        all_url = URL_BASE + "?c=a"
        list_type = country
        conditions = "country=\"%s\"" % country
        lst = get_list_of_items_from_db(table_name="cities", column_name="state",
                                        conditions=conditions, distinct="distinct",
                                        order="order by state", conn=conn)
        url_list = [URL_BASE + "?country=%s&state=%s" % (country, s.replace(" ", "_")) for s in lst]
    elif "city" not in event["queryStringParameters"]:
        # Get list of cities
        state = get_state(event["queryStringParameters"]["state"])
        country = get_country(event["queryStringParameters"]["country"])
        country_url = URL_BASE + "?country=%s" % country
        list_type = "%s, <a href =\"%s\">%s</a>" % (
            state.replace("_", " "), country_url, country.replace("_", " "))

        conditions = "country=\"%s\" and state=\"%s\"" % (country, state)
        lst = get_list_of_items_from_db(table_name="cities", column_name="city",
                                        conditions=conditions,
                                        distinct="distinct",
                                        order="order by city", conn=conn)
        url_list = [
            URL_BASE + "?country=%s&state=%s&city=%s" % (country, state, c.replace(" ", "_")) for c
            in lst]
    elif "x" not in event["queryStringParameters"]:
        # Get list of intersections
        country = get_country(event["queryStringParameters"]["country"])
        state = get_state(event["queryStringParameters"]["state"])
        city = get_city(event["queryStringParameters"]["city"])
        country_url = URL_BASE + "?country=%s" % country
        state_url = URL_BASE + "?country=%s&state=%s" % (country, state)
        list_type = "%s, <a href =\"%s\">%s</a>, <a href =\"%s\">%s</a>" % (
            city.replace("_", " "), state_url, state.replace("_", " "), country_url,
            country.replace("_", " "))

        conditions = "country=\"%s\" and state=\"%s\" and  city=\"%s\"" % (country, state, city)
        city_list = get_list_of_items_from_db(table_name="cities", column_name="id",
                                              conditions=conditions,
                                              distinct="",
                                              order="", conn=conn)
        lst = []
        url_list = []
        if len(city_list):
            sub_title = None
            city_id = city_list[0]
            l_l = get_list_of_multiple_columns_from_db(table_name="x",
                                                       column_list=["streets", "id", "status"],
                                                       conditions="city_id=%d" % city_id,
                                                       distinct="",
                                                       order="order by streets", conn=conn)

            for i in range(len(l_l)):
                intersecting_streets = l_l[i][0]
                if l_l[i][2] == "ready":
                    url_list.append(URL_BASE + "?x_id=%s" % l_l[i][1])
                elif l_l[i][2] == "error":
                    intersecting_streets += "  ...data not available"
                    url_list.append(None)
                else:
                    url_list.append(None)
                lst.append(intersecting_streets)
        else:
            sub_title = "Data not available"
        set_value_in_db("x", "status", "requested", "city_id=%s and status=\"init\"" % city_id,
                        input_conn=conn)
        set_value_in_db("cities", "status", "requested", "id=%s and status=\"init\"" % city_id,
                        input_conn=conn)

    else:
        lst = ["Error"]
        url_list = [None]

    return lst, url_list, list_type, sub_title, image, prev_next


def get_html_list(lst, url_list, list_title, sub_title = None, prev_next="", image=None):

    title = prev_next + "<h3>%s</h3>" % list_title
    if len(lst) == 0:
        if sub_title is None:
            html_list = "<p> <br><br>Data not available</p>"
        else:
            html_list = "<p> <br>Data processing is in progress </p>"
    else:
        list_body = []
        for i in range(len(lst)):
            if url_list[i] is not None:
                list_body.append("<li><a href=\"%s\">%s</a></li>" % (url_list[i], lst[i]))
            elif "-x-" in list_title:
                list_body.append("<li style=\"color:black\">%s</li>" % lst[i])
            else:
                list_body.append("<li style=\"color:grey\">%s</li>" % lst[i])
        html_list = "<ul>" + "".join(list_body) + "</ul>"

    if image is not None:
        insert_image = "<p><img src=\"%s\"></p>" % (S3_FILE_URL + image)
    else:
        insert_image = ""
    return title + html_list + prev_next + insert_image


if __name__ == "__main__":
    print(lambda_handler({"queryStringParameters": {"x_id": "15003", "country": "usa", "state": "CA",
                                                    "city": "Arnold"}}, {}))
