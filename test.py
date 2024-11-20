import argparse
import json
import fhir.resources
import pandas as pd
import re
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.reference import Reference
from fhir.resources.patient import Patient
from fhir.resources.humanname import HumanName
from fhir.resources.address import Address
from fhir.resources.identifier import Identifier
from fhir.resources.observation import Observation
from fhir.resources.quantity import Quantity
from fhir.resources.medicationadministration import MedicationAdministration
from datetime import datetime, date, timedelta, timezone
import json
import decimal
import math

print('fhir.resources version: ', fhir.resources.__version__)
parser = argparse.ArgumentParser(description="A script to get TSV files and convert it to FHIR resources.")

parser.add_argument('-d', '--data', type=str, required=True, help="path to data")
parser.add_argument('-o', '--output', type=str, required=True, help="output file name")
parser.add_argument('-r', '--resource', type=str, required=True, help="resource type")

args = parser.parse_args()


# Define a function to parse and format birth dates in YYYY-MM-DD format
def parse_date(date_str):
    try:
        birth_date = datetime.strptime(date_str, "%m/%d/%Y").date()
        return birth_date.isoformat()
    except ValueError:
        print(f"Invalid date format for {date_str}. Expected MM/DD/YYYY.")
        return None



if args.resource == 'patient':

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
    
    # Set the patient ID as identifier
    def set_patient_identifiers(patient, row):
        identifier = Identifier(
            type={
                "coding": [
                    {
                        "system": "https://fhir.cerner.com/codeSet/4",
                        "code": "10",
                        "display": "MRN",
                        "userSelected": True
                    },
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                        "code": "MR",
                        "display": "Medical record number"
                    }
                ],
                "text": "MRN"
            },
            system="urn:oid:2.16.840.1.113883.3.552",
            value=row['id']
        )
        patient.identifier = [identifier]

    # Set the Patient Name
    def set_patient_names(patient, row):
        name = HumanName(use="official", family=row.get('last_name', ''), given=[row.get('first_name', '')])
        patient.name = [name]
    
    # Set the Patient's gender
    def set_patient_gender(patient, gender_str):
        gender_map = {
            "male": "male",
            "m": "male",
            "female": "female",
            "f": "female"
        }
        patient.gender = gender_map.get(gender_str.lower(), "unknown")

    # Set the Patient's address
    def set_patient_address(patient, row):
        address = Address(
            line=[row.get('address', '')],
            city=row.get('city', ''),
            state=row.get('state', ''),
            postalCode=str(row.get('zip_code', '')),
            country=row.get('country', '')
        )
        patient.address = [address]

    # Set the Patient's birthdate
    def set_patient_birthdate(patient, birth_date_str):
        birth_date = parse_date(birth_date_str)
        if birth_date:
            patient.birthDate = birth_date  

    # Function to load TSV file, create Patient resources, and map data to FHIR 
    def tsv_to_fhir_patients(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t',dtype={'zip_code': str})
        df['zip_code'] = df['zip_code'].astype(str)
        patients = []

        for _, row in df.iterrows():
            patient = Patient(resourceType="Patient")
            set_patient_identifiers(patient, row)
            set_patient_names(patient, row)
            set_patient_gender(patient, row.get('gender', ''))
            set_patient_address(patient, row)
            set_patient_birthdate(patient, row.get('birth_date', ''))
            patients.append(patient.dict())
        
        return patients

    # Function to save the FHIR resources in NDJSON format
    def save_to_ndjson(data, output_file):
        with open(output_file, 'w') as f:
            for record in data:
                # Convert dates before writing
                record = convert_dates(record)
                f.write(json.dumps(record) + '\n')

    patients = tsv_to_fhir_patients(args.data)
    save_to_ndjson(patients, args.output+'.ndjson')

elif args.resource == 'encounter':

    # Adding -5 to datetime to comply with Kevin's code/Eastern time
    def convert_datetime_to_iso(date_obj):
        offset = timezone(timedelta(hours=-5))
        if date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=offset)
        return date_obj.isoformat()
    # Set the encounter ID as identifier
    def set_encounter_identifiers(encounter, row):
        identifier = Identifier(
            type={
                "coding": [{'system': 'https://fhir.cerner.com/codeSet/319',
                'code': '1077',
                'display': 'FIN NBR',
                'userSelected': True}],
                "text": "FIN NBR"
            },
            system="urn:oid:2.16.840.1.113883.3.552",
            value=row['id']
        )
        encounter.identifier = [identifier]
    # Setting the class of encounter
    def set_encounter_class(encounter):
        # Create the Coding object
        class_coding = Coding(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code="IMP"
        )
        
        class_codeable_concept = CodeableConcept(coding=[class_coding])
        
        encounter.class_fhir = [class_codeable_concept]

    # Setting the patient's ID related to the encounter
    def set_encounter_subject(encounter, row):
        subject=Reference(reference=f"{row['patient_id']}")
        encounter.subject = subject

    # Setting the period that encounter happens
    def set_encounter_period(encounter, row):
        period = Period(
        start=parse_date(row['start']),
        end=parse_date(row['end']))
        encounter.period = period

    # Setting the location of the encounter
    def set_encounter_location(encounter, row):
        encounter_location = EncounterLocation(
            location=Reference(reference=f"{row['location_id']}", display=row['location_display'])
        )
        encounter.location = [encounter_location]

    # Setting the type of encounter along with its code and name
    def set_encounter_type(encounter, row):
        type_concept = CodeableConcept(
            coding=[Coding(
                system="https://snomed.info/sct", 
                code=row['type_code'], 
                display=row['type_display']
            )],
            text=row['type_display']  
        )
        
        encounter.type = [type_concept]

    # Setting the reason code for the encounter
    def set_encounter_reason(encounter,row):
        coding = CodeableConcept(
            coding = [Coding(
            system="https://snomed.info/sct",  # SNOMED system for reason codes
            code=row['reason_code'],  # Reason code (e.g., SNOMED code)
            display=row['reason_display']  # Display name for the reason (e.g., diagnosis)
        )])
        
        
        encounter.reasonCode = [coding]  

    # Function to recursively convert datetime.date to string in YYYY-MM-DD format
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
    # Function to load TSV file, create Encounter resources, and map data to FHIR
    def tsv_to_fhir_encounters(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t',dtype={'zip_code': str})
        print(df)
        encounters = []

        for _, row in df.iterrows():
            encounter = Encounter(resourceType="Encounter", status="none", class_fhir=Coding(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code="IMP"
        ))
            set_encounter_identifiers(encounter, row)
            set_encounter_type(encounter, row)
            set_encounter_period(encounter, row)
            set_encounter_subject(encounter, row)
            set_encounter_location(encounter, row)
            set_encounter_reason(encounter, row)
            encounters.append(encounter.dict())
        
        return encounters
    # Saving the FHIR resources to NJSON file
    def save_to_ndjson(data, output_file):
        with open(output_file, 'w') as f:
            for record in data:
                # Convert dates before writing
                record = convert_dates(record)
                # Convert each OrderedDict to JSON and write it to the file
                f.write(json.dumps(record) + '\n')

    encounters = tsv_to_fhir_encounters(args.data)
    save_to_ndjson(encounters, args.output+'.ndjson')

elif args.resource == 'observation':
    
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
    
    # Parsing datetime
    def parse_date(date_str):
        try:
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
            # Set the timezone offset to -05:00 / Eastern time
            offset = timezone(timedelta(hours=-5))
            parsed_date_with_offset = parsed_date.replace(tzinfo=offset)
            # Convert to ISO format (YYYY-MM-DDTHH:MM:SS±HH:MM)
            return parsed_date_with_offset.isoformat()
        except ValueError:
            print(f"Invalid date format for '{date_str}'. Expected format: MM/DD/YYYY HH:MM:SS AM/PM.")
            return None
            
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

    def save_to_ndjson(data, output_file):
        with open(output_file, 'w') as f:
            for record in data:
                # Convert dates before writing
                record = convert_dates(record)
                record = convert_decimals_to_float(record)
                # Convert each OrderedDict to JSON and write it to the file
                f.write(json.dumps(record) + '\n')

    def set_observation_identifiers(observation, row):
        identifier = Identifier(system = 'UPMC Observation Clincial Event ID',
                value = row['id'])
        
        observation.identifier = [identifier]

    def set_observation_component(observation):
        class_coding = Coding(
            system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
            code="IMP"
        )
        class_codeable_concept = CodeableConcept(coding=[class_coding])
        observation.class_fhir = [class_codeable_concept]

    def set_observation_subject(observation, row):
        subject=Reference(reference=f"{row['patient_id']}")
        observation.subject = subject
    def set_observation_encounter(observation, row):
        subject=Reference(reference=f"{row['encounter_id']}")
        observation.encounter = subject
    def set_observation_datetime(observation, row):
        start=parse_date(row['effective'])
        observation.effectiveDateTime = start

    def set_observation_component(observation, row):
        """Sets the component for an Observation resource."""
        if row['component_value'] is None or (isinstance(row['component_value'], float) and math.isnan(row['component_value'])):
            component = {
                "code": CodeableConcept(
                    coding=[Coding(
                        system="https://loinc.org",
                        code=row['code'],
                        display=row['code_display']
                    )]
                )}
        else:
            component = {
                "code": CodeableConcept(
                    coding=[Coding(
                        system="https://loinc.org",
                        code=row['code'],
                        display=row['code_display']
                    )]
                ),
                "valueQuantity": Quantity(
                    value=row['component_value'],
                    unit=row['component_unit'],
                    system="https://unitsofmeasure.org",
                    code=row['component_unit']
                )
            }
        observation.component = [component]  


    def set_observation_category(observation,row):
        # Create the Coding object for the reason
        coding = CodeableConcept(
            coding = [Coding(
            system='http://terminology.hl7.org/CodeSystem/observation-category',  # SNOMED system for reason codes
            code=row['category'],  # Reason code (e.g., SNOMED code)
            display=row['category']  # Display name for the reason (e.g., diagnosis)
        )])
        
        
        observation.category = [coding]  
    
    def create_observation_code(row,  system="https://loinc.org"):
        """Creates a CodeableConcept for the Observation code."""
        return CodeableConcept(
            coding=[Coding(system=system, code=row['code'], display=row['code_display'])]
        )
    def tsv_to_fhir_observations(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
        observations = []

        for _, row in df.iterrows():
            observation = Observation(resourceType="Observation", status="none", code=create_observation_code(row))
            set_observation_identifiers(observation, row)
            set_observation_component(observation, row)
            set_observation_datetime(observation, row)
            set_observation_subject(observation, row)
            set_observation_encounter(observation, row)
            set_observation_category(observation, row)
            observations.append(observation.dict())
        
        return observations
    observations = tsv_to_fhir_observations(args.data)
    save_to_ndjson(observations, args.output+'.ndjson')


elif args.resource == 'medication-administration':

    def convert_decimals_to_float(obj):
        """Recursively converts Decimal values in a dictionary or list to floats."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = convert_decimals_to_float(value)
        elif isinstance(obj, list):
            for i in range(len(obj)):
                obj[i] = convert_decimals_to_float(obj[i])
        elif isinstance(obj, decimal.Decimal):  
            return float(obj)
        return obj

    def parse_date(date_str):
        try:
            parsed_date = datetime.strptime(date_str, "%m/%d/%Y %I:%M:%S %p")
            offset = timezone(timedelta(hours=-5))
            parsed_date_with_offset = parsed_date.replace(tzinfo=offset)
            return parsed_date_with_offset.isoformat()
        except ValueError:
            print(f"Invalid date format for '{date_str}'. Expected format: MM/DD/YYYY HH:MM:SS AM/PM.")
            return None
            
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

    def save_to_ndjson(data, output_file):
        with open(output_file, 'w') as f:
            for record in data:
                record = convert_dates(record)
                record = convert_decimals_to_float(record)
                f.write(json.dumps(record) + '\n')

    def set_medadmin_identifiers(medadmin, row):
        identifier = Identifier(system = 'UPMC Custom Medication Administration ID',
                value = row['id'])
    
    def create_medadmin_datetime(row):
        return parse_date(row['effective'])


    def create_medadmin_codeableconcept(row):
        """Creates a CodeableConcept for the Observation code."""
        return CodeableConcept(
            coding=[Coding(system=row['medication_system'], code=row['medication_code'], display=row['medication_display'])]
            ,text=row['medication_display'])
    def create_medadmin_status(row):
        """something!"""
        return row['status']
    def tsv_to_fhir_observations(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
        medadmins = []

        for _, row in df.iterrows():
            print(create_medadmin_status(row))
            medadmin = MedicationAdministration(resourceType="MedicationAdministration", 
            status=create_medadmin_status(row), effectiveDateTime=create_medadmin_datetime(row),
            medicationCodeableConcept=create_medadmin_codeableconcept(row), subject=Reference(reference=f"{row['patient_id']}"),
                                            context=Reference(reference=f"{row['encounter_id']}"))
            set_medadmin_identifiers(medadmin, row)
            medadmins.append(medadmin.dict())
        
        return medadmins
    
    medadmin = tsv_to_fhir_observations(args.data)
    save_to_ndjson(medadmin, args.output+'.ndjson')


with open(args.output+'.ndjson', 'r') as file:
    dataa = [json.loads(line) for line in file]
print(dataa)  

