import requests, sys, pytz, os
from datetime import datetime

from absl import logging as log
import json


class FitbitApi:
    def __init__(self, client_id: str, client_secret: str, redirect_url: str) -> None:
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.__redirect_url = redirect_url

        self.__local_timezone = pytz.timezone("America/Los_Angeles")
        self.__access_token = ""

    def fetch_body_weight(self):
        return self.fetch_data("body", "weight")

    def fetch_data(self, category, type):
        # FIXME: This needs to also happen when the access token expires and we need to use the refresh token.
        if self.__access_token == "":
            self.__get_access_token()

        points = []
        try:
            response = requests.get(
                # TODO: Figure out, what timeframe to use (based on last sync).
                f"https://api.fitbit.com/1/user/-/{category}/{type}/date/today/1d.json",
                headers={
                    "Authorization": f"Bearer {self.__access_token}",
                    "Accept-Language": "en_US",
                },
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            log.error("HTTP request failed: %s", err)
            sys.exit(1)

        data = response.json()
        log.info(f"Got {type} from Fitbit")

        for day in data[category.replace("/", "-") + "-" + type]:
            points.append(
                {
                    "measurement": type,
                    "time": self.__local_timezone.localize(
                        datetime.fromisoformat(day["dateTime"])
                    )
                    .astimezone(pytz.utc)
                    .isoformat(),
                    "fields": {"value": float(day["value"])},
                }
            )
        return points

    def set_initial_code(self, code):
        self.__write_path(".fitbit-code", code)

    def __get_access_token(self):
        if not self.__access_token:
            refresh_token = self.__read_path(".fitbit-refreshtoken")
            if refresh_token is not "":
                response = requests.post(
                    "https://api.fitbit.com/oauth2/token",
                    data={
                        "client_id": self.__client_id,
                        "grant_type": "refresh_token",
                        "redirect_uri": self.__redirect_url,
                        "refresh_token": refresh_token,
                    },
                    auth=(self.__client_id, self.__client_secret),
                )
            else:
                code = self.__read_path(".fitbit-code")
                if code == "":
                    log.error("Code not set, cannot initialize auth")
                    return ""
                response = requests.post(
                    "https://api.fitbit.com/oauth2/token",
                    data={
                        "client_id": self.__client_id,
                        "grant_type": "authorization_code",
                        "redirect_uri": self.__redirect_url,
                        "code": code,
                    },
                    auth=(self.__client_id, self.__client_secret),
                )
            json = response.json()
            if "success" in json and not json["success"]:
                for err in json["errors"]:
                    log.error(
                        "Error while contacting Fitbit auth: {(%s) -> '%s'}",
                        err["errorType"],
                        err["message"],
                    )
                return
            log.info(f"Response from Fitbit Auth: '{response.text}")
            response.raise_for_status()

            self.__access_token = json["access_token"]
            refresh_token = json["refresh_token"]
            # FIXME: We need to refresh the access token using the refresh_token when this time is up (about 8 hours)
            expires_in = json["expires_in"]
            self.__write_path(".fitbit-refreshtoken", refresh_token)

    def __read_path(self, filename: str) -> str:
        path = self.__get_path(filename)
        if not os.path.isfile(path):
            return ""

        f = open(path, "r")
        token = f.read().strip()
        f.close()
        return token

    def __write_path(self, filename: str, content: str):
        path = self.__get_path(filename)
        f = open(path, "w+")
        f.write(content)
        f.close()

    def __get_path(self, filename: str) -> str:
        script_dir = os.path.dirname(__file__)
        return os.path.join(script_dir, filename)
