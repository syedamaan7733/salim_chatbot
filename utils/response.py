from flask import jsonify
from flask import make_response as flask_make_response

def make_response(success=True, message="", data=[], status_code = 200, **kwargs):
    return flask_make_response(jsonify(success=success, message=message, data=data, **kwargs), status_code)