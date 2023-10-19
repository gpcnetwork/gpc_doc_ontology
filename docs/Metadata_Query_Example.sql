DROP TABLE IF EXISTS notes_metadata;

CREATE TABLE notes_metadata AS

SELECT
    COUNT(*) as note_count,
    PROV_REF.name                AS prov_type1,          -- role, author provider type
    PROV_REF2.name               AS prov_type2,          -- role, author provider type
    SERVICE_TYPE.name            AS author_service,      -- subject matter domain, author Service
    PROV_SPECIALTY_TYPE.name     AS author_specialty,    -- subject matter domain, author Specialty
    DEPARTMENT_REF.name          AS department_specialty,-- subject matter domain, department Specialty
    APPOINTMENT_REF.name         AS appointment_type,    -- service, appointment Type
    ENCOUNTER_REF.name           AS pat_enc_type,        -- setting, encounter type
    PATIENT_CLASS.name           AS pat_class,           -- setting, encounter patient class
    NOTE_TYPE.name               AS doctype              -- doc type, note type
    

FROM notes.NOTE_INFO AS NOTE_INFO
    -------------------- Required joins for source metadata --------------------
    INNER JOIN src_table_schema.PAT_ENC AS PAT_ENC -- limit to notes with a patient
        ON PAT_ENC.encounter_id = NOTE_INFO.encounter_id
    INNER JOIN src_table_schema.NOTE_ENC AS NOTE_ENC  -- limit to notes with some required metadata
        ON NOTE_ENC.note_id = NOTE_INFO.note_id
    -------------------- author provider type from one source --------------------
    LEFT OUTER JOIN reference_table_schema.PROV_SRC1 AS PROV_SRC1
        ON PROV_SRC1.provider_id = NOTE_INFO.author_id
    LEFT OUTER JOIN reference_table_schema.PROV_REF AS PROV_REF
        ON PROV_REF.provider_type = PROV_SRC1.provider_type
    -------------------- author provider type from a second source --------------------
    LEFT OUTER JOIN reference_table_schema.PROV_REF PROV_REF2
        ON PROV_REF2.author_prov_type = NOTE_ENC.author_prov_type
    -------------------- Author Service Type --------------------
    LEFT OUTER JOIN reference_table_schema.SERVICE_TYPE AS SERVICE_TYPE
        ON SERVICE_TYPE.service_type = NOTE_ENC.author_service_type
    -------------------- Author Specialty --------------------
    LEFT OUTER JOIN reference_table_schema.PROVIDERS AS PROVIDERS
        ON PROVIDERS.provider_id = NOTE_INFO.author_id
    LEFT OUTER JOIN reference_table_schema.PROV_SPECIALTY_TYPE AS PROV_SPECIALTY_TYPE
        ON PROV_SPECIALTY_TYPE.specialty = PROVIDERS.specialty_type
    -------------------- Department Specialty --------------------
    LEFT OUTER JOIN reference_table_schema.DEPARTMENTS AS DEPARTMENTS
        ON DEPARTMENTS.department_id = PAT_ENC.department_id
    LEFT OUTER JOIN reference_table_schema.DEPARTMENT_REF AS DEPARTMENT_REF
        ON DEPARTMENT_REF.specialty = DEPARTMENTS.specialty_type
    -------------------- Appointment Type --------------------
    LEFT OUTER JOIN reference_table_schema.APPOINTMENT_REF AS APPOINTMENT_REF
        ON APPOINTMENT_REF.appt_type = PAT_ENC.appt_type
    --------------------  encounter type from one source --------------------
    LEFT OUTER JOIN reference_table_schema.ENCOUNTER_REF AS ENCOUNTER_REF
        ON ENCOUNTER_REF.enc_type = PAT_ENC.enc_type
    --------------------  encounter type from a second source --------------------
    LEFT OUTER JOIN src_table_schema.PAT_ENC_SRC2 AS PAT_ENC_SRC2
        ON PAT_ENC_SRC2.encounter_id = NOTE_INFO.encounter_id
    LEFT OUTER JOIN reference_table_schema.PATIENT_CLASS AS PATIENT_CLASS
        ON PATIENT_CLASS.pat_class = PAT_ENC_SRC2.pat_class_tpe
    --------------------  note type -------------------- 
    LEFT OUTER JOIN reference_table_schema.NOTE_TYPE AS NOTE_TYPE
        ON NOTE_TYPE.note_type = NOTE_INFO.note_type
WHERE 
  NOTE_INFO.encounter_id IS NOT NULL
GROUP BY
    prov_type1,
    prov_type2,
    author_service,
    author_specialty,
    department_specialty,
    appointment_type,
    pat_enc_type,
    pat_class,
    doctype
