import flask

from lib import utils


def jsonify(data: dict):
    return flask.Response(
        utils.pjson(data),
        mimetype="application/json",
    )
