import json
import logging
import os
import requests
import time

logging.basicConfig(level=logging.INFO,
                    filename='!run.log',
                    filemode='w',
                    format='%(levelname)s - %(message)s')


def api_await(func):
    """
    A decorator that takes an api request and tries to execute
    it a max of 3 times in case the response is not successful.
    """
    def wrapper(*args, **kwargs):
        tries = 3
        while tries:
            response = func(*args, **kwargs)
            if response.status_code not in [200, 201]:
                tries -= 1
                time.sleep(1)
            else:
                tries = 0
        return response
    return wrapper


class Admin:
    oll_auth = "CCMToke ARh4EZMp8JSqkLGnXhjsmFcBc2V5dfa7:{email}:{password}"
    oll_us_session = 'https://api.studentlifemobile.com/cc/v1/master_session/'
    oll_can_session = 'https://canapi.studentlifemobile.com/cc/v1/master_session/'
    oll_staging = "https://usstagingapi.studentlifemobile.com/cc/v1/master_session/"

    def __init__(self, env, email, password):
        self.email = email
        self.password = password

        self.query = {
            "us": self.oll_us_session,
            "can": self.oll_can_session,
            "us-staging": self.oll_staging
        }.get(env.lower())

        if not self.query:
            raise ValueError(f"Invalid env, ({env}). Use - us|can|us-staging")

        self.ollwat_api_key = self.get_portal_api_key()
        self.credentials = 'CCMSess {}'.format(self.ollwat_api_key)
        self.headers = {'Content-Type': 'application/json',
                        'Authorization': self.credentials}

    def get_portal_api_key(self):
        """
        Requests the Internal Portal api key.
        """
        response = requests.post(
            self.query,
            headers={
                'Content-Type': 'text/plain',
                'Accept': 'application/json, text/plain, */*',
                'Authorization': self.oll_auth.format(email=self.email,
                                                      password=self.password)}
        )
        return response.json().get('id')

    @api_await
    def put(self, url, data):
        response = requests.put(
            url=url,
            headers=self.headers,
            data=json.dumps(data)
        )
        return response


def enable_crt(api_query, school_id, admin):

    # Set the community_rrt_enabled to True and the
    # school_id field required for the request
    payload = {
        "school_id": school_id,
        "community_rrt_enabled": True
    }

    # Send the request
    response = admin.put(api_query, data=payload)
    logging.info(f"School ID: {school_id} - HTTP {response.status_code}")
    print("School ID:", school_id, "- Request sent")


def main(school_data, api_queries, admins):
    for row in school_data:
        try:
            env, school_id = row['env'], row['school_id']
            api_query = api_queries[env.lower()]
            admin = admins[env.lower()]
        except Exception as e:
            logging.error(f"{row} - {e}")
        else:
            enable_crt(api_query, school_id, admin)


if __name__ == '__main__':
    # Before running the script add the Internal Portal credentials
    # in the env variables such as following:
    # > oll_login_email
    # > oll_login_password

    # This script is built around the Internal API, which makes
    # it difficult to use a single school_ids list as an input
    # because of the api keys and endpoints for the different
    # envs (us, can, staging).

    # There are 2 files attached to the script, prod and staging
    # they have to contain a list of objects like the following:

    # {
    #   "env": str",
    #   "school_id": int
    # }

    # I already built the prod list based on the below sheet
    # https://docs.google.com/spreadsheets/d/1QGlRKbiigXjnk5vfV7zVVnz2dopmcRsTYLDmwc32Oas/edit#gid=959611651

    # The staging file contains the first 100 schools returned
    # by the internal portal staging API.

    # By changing the file_path below we set the script to
    # run either on the prod env or the staging env.

    # Change the file_path
    # > staging_schools_data.json
    # > prod_schools_data.json
    file_path = "staging_schools_data.json"
    school_data = json.load(open(file_path, encoding='utf8'))

    # Get the ollwat credentials from the env variables
    email = os.environ.get("oll_login_email")
    password = os.environ.get("oll_login_password")

    if not (email and password):
        usage = "Add the following env variables: \noll_login_email \noll_login_password"
        raise SystemExit(usage)

    # Checking for valid ollwat credentials
    try:
        admins = {
            "us": Admin('us', email, password),
            "can": Admin('can', email, password),
            "us-staging": Admin('us-staging', email, password),
        }
    except json.JSONDecodeError:
        raise SystemExit("Invalid Internal Portal credentials")

    api_queries = {
        "us": "https://api.studentlifemobile.com/cc/v1/master_school_config/",
        "can": "https://canapi.studentlifemobile.com/cc/v1/master_school_config/",
        "us-staging": "https://usstagingapi.studentlifemobile.com/cc/v1/master_school_config/"
    }

    main(school_data, api_queries, admins)
