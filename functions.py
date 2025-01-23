# Functions to help with our conversions
from datetime import datetime, date, timedelta, timezone
import json
import decimal

# Define a function to parse and format birth dates in YYYY-MM-DD format
def birth_date(date_str):
    try:
        birth_date = datetime.strptime(date_str, "%m/%d/%Y").date()
        return birth_date.isoformat()
    except ValueError:
        print(f"Invalid date format for {date_str}. Expected MM/DD/YYYY.")
        return None

def parse_date(date_str):
    try:
        # Parse date and time from the format MM/DD/YYYY HH:MM:SS AM/PM
        parsed_date = datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
        return parsed_date.isoformat()
    except ValueError:
        print(f"Invalid date format for '{date_str}'. Expected format: MM/DD/YYYY HH:MM:SS AM/PM.")
        return None
def convert_datetime_to_iso(date_obj):
    offset = timezone(timedelta(hours=-5))
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=offset)
    return date_obj.isoformat()

def convert_dates(record):
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, datetime):  # If the value is a datetime object
                record[key] = convert_datetime_to_iso(value)
            elif isinstance(value, date):  # If the value is a date object
                record[key] = value.strftime('%Y-%m-%d')  # Convert it to a string
            elif isinstance(value, list):  # If the value is a list of items
                for item in value:
                    convert_dates(item)  # Recursively handle nested dictionaries
            else:
                convert_dates(value)  # Recursively handle nested dictionaries in the value
    elif isinstance(record, list):  # Handle lists outside of dicts
        for item in record:
            convert_dates(item)  # Recursively handle items in the list
    return record
'''

def convert_datetime_to_iso(date_obj):
    offset = timezone(timedelta(hours=-5))
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=offset)
    return date_obj.isoformat()


# Function to recursively convert datetime.date to string in YYYY-MM-DD format
def convert_dates(record):
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, date):  # If the value is a date object
                record[key] = value.strftime('%Y-%m-%d')  # Convert it to a string
            elif isinstance(value, list):  # If the value is a list of items
                for item in value:
                    convert_dates(item)  # Recursively handle nested dictionaries
            else:
                convert_dates(value)  # Recursively handle nested dictionaries in the value
    return record
'''
# component value in observations needed to be converted to float from Decimal in order to be saved in NDJSON file
def convert_decimals_to_float(obj):
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = convert_decimals_to_float(value)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = convert_decimals_to_float(obj[i])
    elif isinstance(obj, decimal.Decimal):  
        return float(obj)
    return obj


# Function to save the FHIR resources in NDJSON format
def save_to_ndjson(data, output_file):
    with open(output_file, 'w') as f:
        for record in data:
            # Convert dates before writing
            record = convert_dates(record)
            record = convert_decimals_to_float(record)
            # Convert each OrderedDict to JSON and write it to the file
            f.write(json.dumps(record) + '\n')



'''
def convert_dates(record):
    if isinstance(record, dict):
        for key, value in record.items():
            if isinstance(value, datetime):  # If the value is a datetime object
                record[key] = convert_datetime_to_iso(value)
            elif isinstance(value, list):  # If the value is a list of items
                for item in value:
                    convert_dates(item)  # Recursively handle nested dictionaries
            else:
                convert_dates(value)  # Recursively handle nested dictionaries in the value
    elif isinstance(record, list):  # Handle lists outside of dicts
        for item in record:
            convert_dates(item)  # Recursively handle items in the list
    return record


def convert_datetime_to_iso(date_obj):
    offset = timezone(timedelta(hours=-5))
    if date_obj.tzinfo is None:
        date_obj = date_obj.replace(tzinfo=offset)
    return date_obj.isoformat()


    def convert_dates(record):
        if isinstance(record, dict):
            for key, value in record.items():
                if isinstance(value, datetime):  # If the value is a datetime object
                    # Convert it to the desired format with timezone offset
                    record[key] = convert_datetime_to_iso(value)
                elif isinstance(value, list):  # If the value is a list of items
                    for item in value:
                        convert_dates(item)  # Recursively handle nested dictionaries
                else:
                    convert_dates(value)  # Recursively handle nested dictionaries in the value
        elif isinstance(record, list):  # Handle lists outside of dicts
            for item in record:
                convert_dates(item)  # Recursively handle items in the list
        return record

    def convert_datetime_to_iso(date_obj):
        # Assuming the input datetime is naive, and you want to apply a timezone of -05:00
        offset = timezone(timedelta(hours=-5))
        # Convert naive datetime to timezone-aware datetime
        if date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=offset)
        # Return the ISO format with timezone offset
        return date_obj.isoformat()
'''