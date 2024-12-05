# FHIR mapper

Python code to convert TSV files resources of Patients, Observations, Encounters and Medication administration to FHIR resources.


### Parameters

| Parameter | Description                                                             | Value                                                                           
|-----------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| data      | Input data file.                                                        | A tab-separated values (tsv) file containing health data.                       
| resource  | The type of data of the input file.                                     | Either patient, encounter, observation, or medication-administration. 
| output    | The directory to write out data.  The current directory is the default. | N/A                                                                             

The output filename is the same as the input filename.

### Examples

The following examples use the data in this repo in *sample_health_data_v2*.

#### Converting Patient Health Data

To convert the patient health data to FHIR patient resources as NDJSON format, execute the following:

```
 python test.py -d sample_health_data_v2/patients.tsv -o ptest -r patient 
