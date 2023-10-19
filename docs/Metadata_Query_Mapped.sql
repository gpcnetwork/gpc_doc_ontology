DROP TABLE IF EXISTS notes_metadata_mapped;

CREATE TABLE notes_metadata_mapped AS

SELECT
  SUM(m.note_count) AS note_count,
  COALESCE(m.prov_type1, m.prov_type2) as author_role, -- give one provider type priority
  COALESCE(m.department_specialty, m.author_specialty, m.author_service) as subject,
  m.appointment_type as service,  
  NULLIF(TRIM(CONCAT(m.pat_enc_type, ' ', m.pat_class)), '') AS setting, -- concat example
  m.doctype as doctype
FROM notes_metadata AS m
GROUP BY
  author_role,
  subject,
  service,
  setting,
  doctype
ORDER BY
  note_count DESC;