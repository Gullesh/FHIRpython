import argparse
import json
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import json
import decimal
import math

from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.patient import Patient
from fhir.resources.medicationadministration import MedicationAdministration
from fhir.resources.observation import Observation

from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.period import Period
from fhir.resources.reference import Reference
from fhir.resources.humanname import HumanName
from fhir.resources.address import Address
from fhir.resources.identifier import Identifier
from fhir.resources.quantity import Quantity
from fhir.resources.observation import ObservationComponent

import fhir.resources
print('fhir.resources version: ', fhir.resources.__version__)
parser = argparse.ArgumentParser(description="A script to get TSV files and convert it to FHIR resources.")

parser.add_argument('-d', '--data', type=str, required=True, help="path to data")
parser.add_argument('-o', '--output', type=str, required=True, help="output file name")
parser.add_argument('-r', '--resource', type=str, required=True, help="resource type")

args = parser.parse_args()

class PatientFHIRProcessor:
    def __init__(self, tsv_file, output_file):
        self.tsv_file = tsv_file
        self.output_file = output_file

    @staticmethod
    def parse_date(date_str):
        """Parse and format birth dates in YYYY-MM-DD format."""
        try:
            birth_date = datetime.strptime(date_str, "%m/%d/%Y").date()
            return birth_date.isoformat()
        except ValueError:
            print(f"Invalid date format for {date_str}. Expected MM/DD/YYYY.")
            return None

    @staticmethod
    def convert_dates(record):
        """Recursively convert datetime.date to string in YYYY-MM-DD format."""
        if isinstance(record, dict):
            for key, value in record.items():
                if isinstance(value, date):
                    record[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, list):
                    for item in value:
                        PatientFHIRProcessor.convert_dates(item)
                else:
                    PatientFHIRProcessor.convert_dates(value)
        return record

    @staticmethod
    def set_patient_identifiers(patient, row):
        """Set the patient ID as identifier."""
        identifier = Identifier(
            type={
                "coding": [
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

    @staticmethod
    def set_patient_names(patient, row):
        """Set the Patient Name."""
        name = HumanName(use="official", family=row.get('last_name', ''), given=[row.get('first_name', '')])
        patient.name = [name]

    @staticmethod
    def set_patient_gender(patient, gender_str):
        """Set the Patient's gender."""
        gender_map = {
            "male": "male",
            "m": "male",
            "female": "female",
            "f": "female"
        }
        patient.gender = gender_map.get(gender_str.lower(), "unknown")

    @staticmethod
    def set_patient_address(patient, row):
        """Set the Patient's address."""
        address = Address(
            line=[row.get('address', '')],
            city=row.get('city', ''),
            state=row.get('state', ''),
            postalCode=str(row.get('zip_code', '')),
            country=row.get('country', '')
        )
        patient.address = [address]

    @staticmethod
    def set_patient_birthdate(patient, birth_date_str):
        """Set the Patient's birthdate."""
        birth_date = PatientFHIRProcessor.parse_date(birth_date_str)
        if birth_date:
            patient.birthDate = birth_date

    def tsv_to_fhir_patients(self):
        """Load TSV file, create Patient resources, and map data to FHIR."""
        df = pd.read_csv(self.tsv_file, sep='\t', dtype={'zip_code': str})
        df['zip_code'] = df['zip_code'].astype(str)
        patients = []

        for _, row in df.iterrows():
            patient = Patient(resourceType="Patient")
            self.set_patient_identifiers(patient, row)
            self.set_patient_names(patient, row)
            self.set_patient_gender(patient, row.get('gender', ''))
            self.set_patient_address(patient, row)
            self.set_patient_birthdate(patient, row.get('birth_date', ''))
            patients.append(patient.dict())

        return patients

    def save_to_ndjson(self, data):
        """Save the FHIR resources in NDJSON format."""
        with open(self.output_file, 'w') as f:
            for record in data:
                # Convert dates before writing
                record = self.convert_dates(record)
                f.write(json.dumps(record) + '\n')

    def process(self):
        """Main processing method to handle the entire workflow."""
        patients = self.tsv_to_fhir_patients()
        self.save_to_ndjson(patients)


# Usage
if args.resource == "patient":

    processor = PatientFHIRProcessor(tsv_file=args.data, output_file=args.output + '.ndjson')
    processor.process()
