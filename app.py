import os
import urllib.parse

from fitbit import FitbitApi

# NOTE: You need to create these to files and add the corresponding id and secret.
FITBIT_CLIENT_ID = ""
FITBIT_CLIENT_SECRET = ""
with open(".fitbit-client-id", "r") as f:
    FITBIT_CLIENT_ID = f.read().strip()
with open(".fitbit-client-secret", "r") as f:
    FITBIT_CLIENT_SECRET = f.read().strip()


# NOTE: Must match what is set in the app settings.
FITBIT_REDIRECT_URL = "https://saschah.com"


from absl import logging as log
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    send_file,
    abort,
    flash,
)


def lbs_to_kg(lbs: float) -> float:
    return lbs * 0.45359237


log.set_verbosity(log.DEBUG)

fitbitApi = FitbitApi(
    client_id=FITBIT_CLIENT_ID,
    client_secret=FITBIT_CLIENT_SECRET,
    redirect_url=FITBIT_REDIRECT_URL,
)
app = Flask(__name__, static_folder=os.path.join(os.getcwd(), "web"))


@app.route("/auth/start", methods=["GET"])
def auth_start():
    # This needs to only be called once, after the user authorized the application.

    host = request.server[0]
    port = request.server[1]
    protocol = "http" if (host == "localhost" or host == "127.0.0.1") else "https"
    redirect_url = urllib.parse.quote_plus(
        f"{protocol}://{host}:{port}/auth/start_response"
    )
    log.info("Root path: '%s'", request.server)

    # FIXME: Must use what we set in the app for now:
    # Note, for now, copy the "code" parameter you get here and pass it on to /auth/start_response?code=
    redirect_url = FITBIT_REDIRECT_URL

    url = f"https://www.fitbit.com/oauth2/authorize?response_type=code&client_id={FITBIT_CLIENT_ID}&scope=weight&redirect_uri={redirect_url}"
    return redirect(url)


@app.route("/auth/start_response", methods=["GET"])
def auth_start_response():
    code = request.args.get("code", default="")
    if code == "":
        return "No code reseived", 403
    fitbitApi.set_initial_code(code)
    return redirect("/")


@app.route("/", methods=["GET", "POST"])
def upload_image():
    weight_points = fitbitApi.fetch_body_weight()
    print(weight_points)
    return f"We got {len(weight_points)} weight data points from Fitbit"


# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, port=5000)
