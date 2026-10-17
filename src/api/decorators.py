from functools import wraps
from flask import jsonify
from flask_login import current_user, login_required


def admin_required(view_function):
    @wraps(view_function)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({
                "error": "Admin access required"
            }), 403

        return view_function(*args, **kwargs)

    return wrapped_view