import json
import datetime


# --- Global JSON Serializer ---
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# Custom JSON wrapper using the default serializer
class CustomJSON:
    @staticmethod
    def dumps(*args, **kwargs):
        # Ensure our default serializer is used
        kwargs.setdefault('default', json_serial)
        return json.dumps(*args, **kwargs)

    @staticmethod
    def loads(*args, **kwargs):
        # Use standard loads for receiving data
        return json.loads(*args, **kwargs)
