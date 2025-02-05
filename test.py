import argparse
import json
import pandas as pd
from datetime import datetime, date, timedelta, timezone
import json
import decimal
import math
import functions as fun
from fhir.resources.encounter import Encounter, EncounterLocation
from fhir.resources.patient import Patient
from fhir.resources.medicationadministration import MedicationAdministration
from fhir.resources.observation import Observation
from fhir.resources.extension import Extension

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

if args.resource == 'patient':
    
    # Set the patient ID as identifier
    def set_patient_identifiers(patient, row):
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
        birth_date = fun.birth_date(birth_date_str)
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


    patients = tsv_to_fhir_patients(args.data)
    fun.save_to_ndjson(patients, args.output+'.ndjson')



elif args.resource == 'encounter':
    """    # Adding -5 to datetime to comply with Kevin's code/Eastern time
    def convert_datetime_to_iso(date_obj):
        offset = timezone(timedelta(hours=-5))
        if date_obj.tzinfo is None:
            date_obj = date_obj.replace(tzinfo=offset)
        return date_obj.isoformat()"""
    # Set the encounter ID as identifier
    def set_encounter_identifiers(encounter, row):
        identifier = Identifier(
            type={
                "coding": [{'system': 'https://fhir.cerner.com/1245/codeSet/319',
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
        start=fun.parse_date(row['start']),
        end=fun.parse_date(row['end']))
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
                system="http://snomed.info/sct", 
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
            system="http://snomed.info/sct",  # SNOMED system for reason codes
            code=row['reason_code'],  # Reason code (e.g., SNOMED code)
            display=row['reason_display']  # Display name for the reason (e.g., diagnosis)
        )])
        
        
        encounter.reasonCode = [coding]  

    
    # Function to load TSV file, create Encounter resources, and map data to FHIR
    def tsv_to_fhir_encounters(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t',dtype={'zip_code': str})
        encounters = []

        for _, row in df.iterrows():
            encounter = Encounter(resourceType="Encounter", status="in-progress", class_fhir=Coding(
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

    encounters = tsv_to_fhir_encounters(args.data)
    fun.save_to_ndjson(encounters, args.output+'.ndjson')

elif args.resource == 'observation':

    def set_observation_identifiers(observation, row):
        identifier = Identifier(value = row['id'])
        
        observation.identifier = [identifier]


    def set_observation_subject(observation, row):
        subject=Reference(reference=f"{row['patient_id']}")
        observation.subject = subject
    def set_observation_encounter(observation, row):
        subject=Reference(reference=f"{row['encounter_id']}")
        observation.encounter = subject
    def set_observation_datetime(observation, row):
        start=fun.parse_date(row['effective'])
        observation.effectiveDateTime = start
    
    
    def set_observation_component(observation, row):
        """Sets the component for an Observation resource."""
        if row['code'] == '85354-9':  # LOINC code for Blood Pressure Panel
            
            components = []

            # 🩸 **Systolic Blood Pressure Component**
            systolic_component = ObservationComponent(
                extension=[
                    Extension(
                        url="http://hl7.org/fhir/StructureDefinition/observation-componentCategory",
                        valueCodeableConcept=CodeableConcept(
                            coding=[Coding(
                                system="http://loinc.org",
                                code="8480-6",
                                display="Systolic blood pressure"
                            )]
                        )
                    )
                ],
                code=CodeableConcept(
                    coding=[Coding(
                        system="http://loinc.org",
                        code="8480-6",
                        display="Systolic blood pressure"
                    )]
                )
            )
            
            # If `systolic_value` is missing, add dataAbsentReason
            if pd.isna(row.get("systolic_value")):
                systolic_component.dataAbsentReason = CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        code="unknown",
                        display="Unknown"
                    )]
                )
            else:
                systolic_component.valueQuantity = Quantity(
                    value=row["systolic_value"],
                    unit=row.get("systolic_unit", "mmHg"),
                    system="http://unitsofmeasure.org",
                    code="mm[Hg]"
                )
            
            components.append(systolic_component)

            # 💙 **Diastolic Blood Pressure Component**
            diastolic_component = ObservationComponent(
                extension=[
                    Extension(
                        url="http://hl7.org/fhir/StructureDefinition/observation-componentCategory",
                        valueCodeableConcept=CodeableConcept(
                            coding=[Coding(
                                system="http://loinc.org",
                                code="8462-4",
                                display="Diastolic blood pressure"
                            )]
                        )
                    )
                ],
                code=CodeableConcept(
                    coding=[Coding(
                        system="http://loinc.org",
                        code="8462-4",
                        display="Diastolic blood pressure"
                    )]
                )
            )

            # If `diastolic_value` is missing, add dataAbsentReason
            if pd.isna(row.get("diastolic_value")):
                diastolic_component.dataAbsentReason = CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        code="unknown",
                        display="Unknown"
                    )]
                )
            else:
                diastolic_component.valueQuantity = Quantity(
                    value=row["diastolic_value"],
                    unit=row.get("diastolic_unit", "mmHg"),
                    system="http://unitsofmeasure.org",
                    code="mm[Hg]"
                )

            components.append(diastolic_component)

            # 🔄 Assign components to the observation
            observation.component = components

    def create_value_quantity(row: dict):
        if row['code'] == '85354-9': 
            return None
        else:
            return Quantity(
                value=row['component_value'],
                unit=row.get('component_unit', ''),
                system="http://unitsofmeasure.org",
                code=row.get('component_unit', '')
            )


    def set_observation_category(observation,row):
        # Create the Coding object for the reason
        coding = CodeableConcept(
            coding = [Coding(
            system='http://terminology.hl7.org/CodeSystem/observation-category',  # SNOMED system for reason codes
            code=row['category'],  # Reason code (e.g., SNOMED code)
            display=row['category'].replace("-", " ").title()  # Display name for the reason (e.g., diagnosis)
        )])
        
        
        observation.category = [coding]  
    
    def create_observation_code(row,  system="http://loinc.org"):
        """Creates a CodeableConcept for the Observation code."""
        if row['code'] == '2713-6':
            return CodeableConcept(
            coding=[Coding(system=system, code='2708-6', display="Oxygen saturation in Arterial blood")]
        )
        else:
            return CodeableConcept(
                coding=[Coding(system=system, code=row['code'], display=row['code_display'])]
            )
    def tsv_to_fhir_observations(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
        observations = []
        for i, row in df.iterrows():
            #print(i, row['component_value'])
            if row['component_value'] is None or (isinstance(row['component_value'], float) and math.isnan(row['component_value'])):
                observation = Observation(
                resourceType="Observation",
                status="registered",
                code=create_observation_code(row)
            )
            else:
                observation = Observation(
                resourceType="Observation",
                status="registered",
                code=create_observation_code(row),
                valueQuantity = create_value_quantity(row)  # Directly use valueQuantity
            )
            set_observation_identifiers(observation, row)
            set_observation_component(observation, row)
            set_observation_datetime(observation, row)
            set_observation_subject(observation, row)
            set_observation_encounter(observation, row)
            set_observation_category(observation, row)
            observations.append(observation.dict())
        
        return observations
    observations = tsv_to_fhir_observations(args.data)
    fun.save_to_ndjson(observations, args.output+'.ndjson')


elif args.resource == 'medication-administration':

    def set_medadmin_identifiers(medadmin, row):
        identifier = Identifier(value = row['id'])
        medadmin.identifier = [identifier]

    def create_medadmin_datetime(row):
        return fun.parse_date(row['effective'])


    def create_medadmin_codeableconcept(row):
        """Creates a CodeableConcept for the Observation code."""
        return CodeableConcept(
            coding=[Coding(system=row['medication_system'], code=row['medication_code'], display=row['medication_display'])]
            ,text=row['medication_display'])
    def create_medadmin_status(row):
        """something!"""
        return row['status'].lower()
    def tsv_to_fhir_observations(tsv_file):
        df = pd.read_csv(tsv_file, sep='\t')
        medadmins = []

        for _, row in df.iterrows():
            medadmin = MedicationAdministration(resourceType="MedicationAdministration", 
            status=create_medadmin_status(row), effectiveDateTime=create_medadmin_datetime(row),
            medicationCodeableConcept=create_medadmin_codeableconcept(row), subject=Reference(reference=f"{row['patient_id']}"),
                                            context=Reference(reference=f"{row['encounter_id']}"))
            set_medadmin_identifiers(medadmin, row)
            medadmins.append(medadmin.dict())
        
        return medadmins
    
    medadmin = tsv_to_fhir_observations(args.data)
    fun.save_to_ndjson(medadmin, args.output+'.ndjson')