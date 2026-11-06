# Treatment Plan v3 field reference

This file lists every field on each Treatment Plan v3 page, the rules that accept or reject a value, the database tables, and the `/api/v2` routes.

Pages appear in navigation order: Information, Medical, Referral, Medication, Therapy, Education, Family, Child, Assessment, Crisis, Goals, Discharge, Treatment.

Two kinds of rules apply:

- **Save rules** run when a field is written. On most pages a blank value is stored as empty, extra field names are rejected, and surrounding spaces are removed. A page can be saved one field at a time, so a single save does not have to complete the page.
- **Completion rules** decide whether the page is empty, complete, or in error. A page with no saved row is empty. A saved page is complete only when every required value passes the checks below.

The Goals tab is in the navigation list, but the app does not render a Goals form yet. Goal fields and rules below come from the API.

A signed or historical plan is read-only in the app. The form does not accept edits in that state.

---

## Shared value rules

| Kind | Rule |
| --- | --- |
| Phone | Exactly 10 digits |
| Email | A valid email address, at most 255 characters where a max is set |
| US state | A two-letter US state or territory code, stored in uppercase. The Family page also accepts `CZ` |
| Month and year | Sent as the first day of the month. A later day is rejected. Medication and Therapy dates cannot be in the future |
| Goal month | `mm-yyyy`, stored as `yyyy-mm` |
| Rich text | HTML is sanitized. Completion counts visible characters after tags, spaces, and invisible characters are removed |
| Number ranges | Inclusive unless a field says otherwise |

---

## 1. Information

Read-only. Values come from the client, assignments, and insurance. The page has no save form and no completion checklist of its own.

### Client

| Label | Field | Type | Control | Required | Notes |
| --- | --- | --- | --- | --- | --- |
| Client | `first_name`, `last_name` | text | read-only | shown when present | Display name |
| DOB | `date_of_birth` | date | read-only | optional | May be empty |
| Gender | `sex` | text | read-only | shown when present | |
| Client ID | `id` | integer | read-only | always | |

### Insurance

Repeated for Primary, Secondary, and Tertiary. A block can be empty.

| Label | Field | Type | Control | Required |
| --- | --- | --- | --- | --- |
| Name | `payor_name` | text | read-only | when a policy exists |
| Policy member ID | `member_id` | text | read-only | optional |
| Start date | `date_start` | date | read-only | optional |
| End date | `date_end` | date | read-only | optional |

### Assignment

Each card lists people. A person shows Name (`display_name`) and Role. The cards are Parent/guardian, BT(s), and BCBA(s). BCBA roles on the API are home BCBA, bobbing BCBA, and substitute BCBAs. An empty card shows its empty message. If parents and guardians fail to load, the card shows an error instead of an empty list.

---

## 2. Medical

Every scalar field is required for a complete page. Zero additional diagnoses is valid. Each diagnosis row that exists must be complete. Each selection group needs at least one value.

### Medical history

| Label | Field | Type | Control | Save limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Allergies | `allergies` | text | text | 4–255 characters | required |
| Special diets | `special_diets` | text | text | 4–255 characters | required |
| Hearing difficulties | `hearing_difficulty` | enum | dropdown | one option below | required |
| Hearing screening date | `hearing_screening_date` | date | date | valid date | required |
| Vision difficulties | `vision_difficulty` | enum | dropdown | one option below | required |
| Vision screening date | `vision_screening_date` | date | date | valid date | required |
| Trauma history | `trauma_history` | rich text | rich text | 4–50,000 characters | required |
| Surgical or hospitalization history | `hospitalization_history` | rich text | rich text | 4–50,000 characters | required |

Hearing options:

- Peripheral (Medical) Hearing Loss
- Auditory Processing Difficulties (APD-like features)
- Hyperacusis (Sound Sensitivity)
- Hypersensitivity to Specific Frequencies
- Auditory Filtering Difficulties
- Delayed Auditory Processing
- Fluctuating Hearing Issues
- Other hearing issues
- No hearing issues

Vision options:

- Refractive Errors (Common in All Children)
- Strabismus (Eye Alignment Problems)
- Amblyopia (“Lazy Eye”)
- Visual Processing Differences (Very Common in ASD)
- Visual Sensory Sensitivities
- Visual Attention & Scanning Differences
- Depth Perception & Binocular Vision Issues
- Ocular Motor Dysfunction
- Other vision issues
- No vision issues

### ASD diagnosis

| Label | Field | Type | Control | Save limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Severity level | `asd_severity_level` | enum | dropdown | Level-1, Level-2, Level-3, Unknown | required |
| Provider name | `asd_diagnosis_provider_name` | text | text | 8–255 characters | required |
| City | `asd_diagnosis_city` | text | text | 2–255 characters | required |
| State | `asd_diagnosis_state` | state code | dropdown | valid US state code | required |
| Year | `asd_diagnosis_year` | integer | year | 1900–2100 | required |

### Additional diagnosis rows

Optional list. Each saved row requires every column.

| Label | Field | Type | Control | Save limits |
| --- | --- | --- | --- | --- |
| Additional diagnosis | `diagnosis_name` | enum | dropdown | one diagnosis below |
| Provider name | `provider_name` | text | text | 8–255 characters |
| City | `city` | text | text | 2–255 characters |
| State | `state` | state code | dropdown | valid US state code |
| Year | `year` | integer | year | 1900–2100 |

Diagnosis options:

- Adjustment Disorder (F43.2)
- Anxiety (F41.9)
- Asperger’s syndrome (F84.5)
- Attention-deficit hyperactivity disorder (F90.0, F90.1, F90.2, F90.8, F90.9)
- Cerebral Palsy (G80.9)
- Cerebral Visual Impairment: (H47.61)
- Coffin-Siris Syndrome (Q87.1)
- Congenital Heart Failure: (Q24.9)
- Depression (F33.0, F33.2)
- Developmental disorder of speech and language, unspecified (F80.9)
- Disruptive mood dysregulation disorder (F34.81)
- Downs Syndrome (Q90.9)
- Emotional Disturbance Disorder (F98.9)
- Epilepsy: (G40.0)
- Generalized Anxiety Disorder (F41.1)
- Global Speech Delay (F80)
- Mild Intellectual Developmental Disorder (F70)
- Mixed Receptive-Expressive Language Disorder (F80.2)
- Obsessive Compulsive Disorder (F42)
- Oppositional Defiance Disorder (F91.3)
- Oral Aversion (F50.82)
- Other childhood disintegrative disorder (F84.3)
- Other pervasive developmental disorders (F84.8)
- Pediatric Feeding Disorder (R63.32)
- Pervasive developmental disorder, unspecified (F84.9)
- Post-Traumatic Stress Disorder (F43.12)
- Prader-Willi Syndrome (Q87.11)
- Rett’s syndrome (F84.2)
- Sensory Processing Disorder (F88)

### Multi-select groups

`selection_type` plus `value`. At least one value is required in each group. `None` cannot be combined with another value in the same group.

| Label | `selection_type` | Options |
| --- | --- | --- |
| Early Childhood Intervention (ECI) | `EARLY_INTERVENTION` | Applied Behavior Analysis, Feeding Therapy, Speech Therapy, Play Therapy, Occupational Therapy, Special Education Preschool, Physical Therapy, Other, None |
| Issues during pregnancy or birth | `PREGNANCY_ISSUE` | Vaginal bleeding, Rh incompatibility, Emotional problems, Infections, Bed-rest, Premature Labor, Difficulty in conception, Threatened miscarriage, Excessive swelling, Other virus, Excessive nausea/vomiting, Drug or Alcohol abuse, Other, None |
| Any regression in the areas of | `REGRESSION` | Speech language, Gross motor, Fine motor, None |

A value must belong to the enum for its `selection_type`.

### Birth and development

| Label | Field | Type | Control | Range | Completion |
| --- | --- | --- | --- | --- | --- |
| Child delivery type | `child_delivery_type` | enum | dropdown | Spontaneous, C-Section, Induced Vaginal, Unknown | required |
| Weeks | `child_gestational_age_weeks` | integer | number | 0–99 | required |
| Pounds | `child_weight_at_birth_pounds` | integer | number | 0–99 | required |
| Ounces | `child_weight_at_birth_ounces` | integer | number | 0–15 | required |
| Sitting up, months | `child_sitting_up_age_months` | integer | number | 0–99 | required |
| Crawling, months | `child_crawling_age_months` | integer | number | 0–99 | required |
| Walking, years | `child_walking_age_years` | integer | number | 0–99 | required |
| Walking, months | `child_walking_age_months` | integer | number | 0–99 | required |
| Standing, years | `child_standing_age_years` | integer | number | 0–9 | required |
| Standing, months | `child_standing_age_months` | integer | number | 0–99 | required |
| Babbling, months | `child_babbling_age_months` | integer | number | 0–99 | required |
| First word | `child_first_word` | text | text | one word, 2–16 characters, no spaces | required |
| Second word | `child_second_word` | text | text | one word, 2–16 characters, no spaces | required |
| First words, months | `child_first_words_age_months` | integer | number | 0–99 | required |

The app checks the same ranges before save.

---

## 3. Referral

Repeatable rows. The form requires every column before a row is saved, and it shows “At least one referral is required” when the list is empty. The API treats zero rows as an empty page, not an error. Each saved row must have all five fields to complete the page.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Date | `referral_date` | date | date | valid date | required |
| Provider name | `provider_name` | text | text | at least 8 characters | required |
| Diagnosis tool | `diagnosis_tool` | enum | dropdown | one option below | required |
| City | `city` | text | text | at least 2 characters | required |
| State | `state` | state code | dropdown | two-letter US state code | required |

Diagnosis tool options:

- ADOS-2 (Autism Diagnostic Observation Schedule)
- Autism Spectrum Rating Scales™ (ASRS®)
- AQ (Autism Spectrum Quotient)
- CARS-2 (Childhood Autism Rating Scale)
- GARS-2 (Gilliam Autism Rating Scale)
- M-CHAT-R/F (Modified Checklist for Autism in Toddlers)
- Parents’ Evaluation of Developmental Status (PEDS)
- SRS-2 (Social Responsiveness Scale)
- STAT (Screening Tool for Autism in Toddlers)
- Tele-ASD-Peds
- Other

---

## 4. Medication

Checkbox: **No medication taken by the client** (`no_medication`). On the API this is the inverse of `TreatmentPlan.has_medication`.

| Checkbox | Rows | Page result |
| --- | --- | --- |
| Not answered | none | empty |
| Not answered | some | error: select whether the client takes medication |
| Checked | none | complete |
| Checked | some | error: delete the rows or clear the checkbox |
| Unchecked | none | error: add a medication or check no medication |
| Unchecked | some | complete when every row is valid |

The form asks for confirmation before checking the box when rows already exist, then deletes those rows.

### Medication row

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Medication | `medication_name` | text | text | 4–255 characters | required |
| Dosage | `dosage` | text | text | 2–255 characters | required |
| Start month | `start_date` | date | month/year | first day of a month, not in the future, after the client date of birth | required |
| Prescribing physician | `physician_name` | text | text | 8–255 characters | required |
| Reason for taking | `reason` | text | text | 8–255 characters | required |

Creating a row requires at least one field. The date-of-birth check runs on completion, not on the save schema. The form requires all five fields before save and sends the start date as the first day of the selected month.

---

## 5. Therapy

Checkbox: **No historical therapy** (`no_historical_therapy`).

| Checkbox | Rows | Page result |
| --- | --- | --- |
| Not answered | none | empty |
| Checked | none | complete |
| Checked | some | error: delete the rows or clear the checkbox |
| Unchecked | none | error: add a therapy or check no historical therapy |
| Unchecked | some | complete when every row is valid |

The form asks for confirmation before checking the box when rows exist.

### Therapy row

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Provider name | `provider_name` | text | text | API: 8–255 characters. The form currently requires at least 4 | required |
| Service type | `service_type` | enum | dropdown | options below | required |
| Phone number | `phone_number` | text | phone | 10 digits | required |
| Email | `email` | email | email | valid email | required |
| Start month | `start_date` | date | month/year | first of month, not in the future, after date of birth | required |
| End month | `end_date` | date | month/year | optional. If set: first of month, not in the future, on or after start, after date of birth | optional |
| Hours | `hours` | number | number | API: 0–999.9 in steps of 0.1. The form currently allows a whole number only | required |
| Service frequency | `frequency` | enum | dropdown | Daily, Weekly, Semi-weekly, Monthly, Semi-monthly | required |
| Progress | `progress` | enum | dropdown | Positive improvement, No progress, Unfavorable outcome | required |
| Do not share info with provider | `do_not_share_info_with_provider` | boolean | checkbox | defaults to false. Cannot be cleared to null on update | required as a boolean |
| Record shared | `is_record_shared` | enum | dropdown | Shared, Will share | required unless the do-not-share box is checked. If that box is checked, this field must be empty |

Service type options:

- Applied Behavior Analysis (ABA)
- Speech Therapy
- Occupational Therapy
- Physical Therapy
- Counseling Services
- Feeding Therapy
- Equestrian Therapy
- Other

Creating a row requires at least one field. `do_not_share_info_with_provider` does not count as clinical content. Date-of-birth checks run on completion.

---

## 6. Education

Checkbox: **Child is not attending school** (`not_attending_school`).

If the box is checked, every other education field must be empty. The form hides those fields and asks for confirmation before checking the box when education data exists.

If the box is not checked, every field below is required except evaluation status and evaluation date.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Education setting | `education_setting` | enum | dropdown | In-person public/private, Homeschool, Remote | required when attending |
| Number of hours per week | `number_of_hours_per_week` | number | number | greater than 0 and at most 40, one decimal place | required when attending |
| School name | `school_name` | text | text | 4–255 characters | required when attending. The form does not require it for Homeschool |
| School phone number | `school_phone_number` | text | phone | 10 digits | required when attending. The form does not require it for Homeschool |
| Education description | `education_description` | rich text | rich text | at most 800 stored characters, at least 8 visible characters | required when attending |
| Focus area description | `focus_area_description` | rich text | rich text | at most 800 stored characters, at least 8 visible characters | required when attending |
| Client's education evaluation status | `evaluation_status` | enum | dropdown | EVALUATED, NOT_EVALUATED, SCHEDULED_EVALUATION | optional |
| Evaluation date | `evaluation_date` | date | date | valid date | optional |
| IEP or 504 in place | `iep_or_504_in_place` | enum | dropdown | N/A, IEP, 504 | required when attending |
| Educational support | `education_support` | text | text | 8–255 characters | required when attending |
| Child's current classroom setting | `classroom_setting` | enum | dropdown | options below | required when attending |
| Child's attitude towards school | `attitude_towards_school` | enum | dropdown | options below | required when attending |

Classroom setting options:

- Speech-Language
- Occupational Therapy
- Physical Therapy
- Social Skill Groups
- Applied Behavior Analysis
- 1:1 aide
- Additional time
- General education classroom
- Special education classroom
- Integrated general education services
- Other

Attitude options:

- Very Positive (Enthusiastic, Excited to Attend)
- Positive (Generally Enjoys School)
- Somewhat Positive
- Neutral (No Strong Feelings)
- Mixed (Varies Day-to-Day)
- Reluctant (Needs Encouragement)
- Somewhat Negative
- Negative (Avoidant/Dislikes School)
- Highly Negative (Refusal, Distress, Tantrums)
- Anxious (Separation Anxiety, Worry)

---

## 7. Family

A complete page needs at least one family member, a cultural consideration, and at least one value in each of the three selection lists. Siblings are optional. Each sibling row that exists must be complete.

### Family member

| Label | Field | Type | Control | API limits | Form limits | Completion |
| --- | --- | --- | --- | --- | --- | --- |
| First & last name | `full_name` | text | text | 6–255 characters | at least 4 | required |
| Role | `member_role` | enum | dropdown | Parent and a caregiver, Parent not a caregiver, Caregiver | same | required |
| Primary/secondary caregiver | `caregiver_type` | enum | dropdown | Primary caregiver, Secondary caregiver | same | required only for a caregiver role. Must be empty for “Parent not a caregiver” |
| Relationship to child | `relationship_to_client` | enum | dropdown | options below | same | required |
| Child custody | `custody_type` | enum | dropdown | Joint custody, Full custody, No custody | same | required |
| Marital status | `marital_status` | enum | dropdown | Divorced, Married, Single, Separated, Widowed, Domestic Partner / Civil Union | same | required |
| Job | `job_title` | text | text | 4–255 characters | at least 4 | required |
| Email | `email` | email | email | valid email, max 255 | valid email | required |
| Phone | `phone` | text | phone | 10 digits | 10 digits | required |
| Street address line one | `street_address_line_one` | text | text | 8–255 characters | at least 4 | required |
| Address line two (Apartment/unit) | `street_address_line_two` | text | text | max 255 | optional | optional |
| City | `street_address_city` | text | text | 2–255 characters | at least 4 | required |
| State | `street_address_state` | state code | dropdown | US state code or `CZ` | required | required |
| Zip code | `street_address_zip` | text | text | 5 digits | 5 digits | required |

Relationship options:

- Parent (Mother / Father)
- Stepparent
- Grandparent
- Aunt / Uncle
- Older sibling
- Cousin
- Legal guardian (court-appointed)
- Adoptive parent
- Foster parent
- Kinship caregiver (relative/friend)

Only one member may be Primary caregiver.

### Client sibling

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Sibling relation | `sibling_relationship` | enum | dropdown | Brother, Sister, Twins, Half-brother, Half-sister, Step-siblings, Adoptive-siblings. The API also accepts the alias “Adoptive Siblings” | required on a saved row |
| Age | `sibling_age` | integer | number | 0–99 | required on a saved row |
| Diagnosis | `sibling_diagnosis` | text | text | 4–255 characters | required on a saved row |

### Selection lists

Each list stores `info_type` and `value`. A complete page needs at least one value in each list. Duplicate values in the same list are rejected. The form marks an empty list as an error once something on the page has been saved.

| Label | `info_type` | Options |
| --- | --- | --- |
| Maternal medical history | `MATERNAL_MEDICAL_HISTORY` | medical history list below |
| Paternal medical history | `PATERNAL_MEDICAL_HISTORY` | medical history list below |
| Community support | `COMMUNITY_SUPPORT` | community list below |

Medical history options, used by both sides:

- ASD
- Other developmental disorders (e.g., intellectual disabilities, language disorders)
- Mood disorders (e.g., depression, bipolar disorder, anxiety disorders)
- ADHD
- Schizophrenia
- Alcohol or drug abuse
- Learning disabilities
- Anxiety, panic concerns
- Genetic syndromes associated with ASD (e.g., Fragile X syndrome, Rett syndrome)
- Other
- None

Community support options:

- Church (or other religion organization). The API also accepts the alias “Church (or other religious organization)”
- Community
- Extended family
- Friends
- Other
- None

A value must match the list for its `info_type`. Length is 1–500 characters.

### Cultural considerations

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Cultural considerations | `cultural_consideration` | rich text | rich text | stored HTML max 800. The form also caps visible text at 800 | required, at least 4 visible characters |

---

## 8. Child

### Background lists

Each item is `background_type` plus `background_description`. A description cannot be repeated inside the same type. Dropdown types must use a listed label. Free-text types are Strength, Weakness, Interest, and Dislikes. The API also rewrites the typo “Verbal a ggression …” to “Verbal aggression …”.

| Label | `background_type` | Control | Completion | Options or limits |
| --- | --- | --- | --- | --- |
| Child communication style | `COMMUNICATION_STYLE` | multi-select | at least 1 | Verbal communication (single words, sentences, etc.); Speech device (AAC, tablet, etc.); Sign language; Gestures (pointing, pulling, etc.); Picture-based communication (PECS, picture boards, etc.); No communication |
| Goals for therapy | `GOALS_FOR_THERAPY` | multi-select | at least 1 | Improve communication skills; Reduce tantrums or meltdowns; Help with following directions; Support potty training; Improve social skills (making friends, sharing, taking turns); Decrease concerning behaviors; Improve attention and focus; Help with transitions between activities; Increase independence with daily living skills (dressing, brushing teeth, feeding); Support school readiness skills; Improve play skills; Reduce repetitive behaviors; Improve safety skills (staying nearby, crossing streets safely); Support emotional regulation; Help with sleep routines; Support feeding or picky eating concerns; General developmental support |
| Child's strengths (at least 2) | `STRENGTH` | free text | at least 2 | 1–2000 characters |
| Child's weaknesses (at least 2) | `WEAKNESS` | free text | at least 2 | 1–2000 characters |
| Child's interests (at least 2) | `INTEREST` | free text | at least 2 | 1–2000 characters |
| Child's dislikes (at least 2) | `DISLIKES` | free text | at least 2 | 1–2000 characters |
| Child's behavior issues | `BEHAVIOR_ISSUE` | multi-select | at least 1 | Aggression (e.g., hitting, kicking, biting); Verbal aggression (e.g., threats, name-calling); Elopement (e.g., running from caregiver); Property destruction (e.g., breaking toys, household items); Task refusal (e.g., refusing instructions or tasks); Self-injury (e.g., hitting or pinching itself); Pica (Eating non-food items such as plastic, chalk, fabric, etc.); Disrobing (Removal of clothing in inappropriate settings, etc.); None |

### Other behavior issues

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Any other child behavior issues | `child_behavior_issues` | rich text | rich text | max 800 stored characters. The form also caps visible text at 800 | not required for page completion |

### ABA therapy schedule availability

| Label | Field | Type | Control | Options or limits |
| --- | --- | --- | --- | --- |
| Day of week | `day_of_week` | enum | dropdown | MONDAY through SUNDAY |
| Activity | `schedule_activity_type` | enum | dropdown | FORTA_THERAPY = Available for Forta therapy; SCHOOL = School; OTHER_THERAPY = Other therapies; OTHER_ACTIVITY = Other activities |
| Start time | `schedule_start_date` | datetime | time | timezone-aware |
| End time | `schedule_end_date` | datetime | time | timezone-aware, after start |
| UTC offset | `utc_offset` | integer | hidden | seconds, within the allowed offset range |

Schedule guardrails:

- The interval must be valid for the offset.
- Two rows on the same day cannot overlap.
- A complete page needs at least one non-overlapping Forta therapy slot.
- If Education says the child attends school, a complete page also needs a School slot.
- If Therapy says there is historical therapy (`no_historical_therapy` is false), a complete page also needs an Other therapies slot.

---

## 9. Assessment

### Assessment info

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Initial assessment date | `initial_assessment_date` | date | date | valid date | required |
| Was diagnostic report reviewed | `diagnostic_report_reviewed` | boolean | yes/no | true or false | required |
| Re-assessment date | `reassessment_date` | date | date | valid date | required |
| Parent interview summary | `parent_interview_summary` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form only requires some visible text |

### Additional files viewed

`additional_files_viewed` is a unique list, at most 6 values. Duplicates and unknown values fail completion. The form does not require a selection.

Options:

- Previous assessment reports
- Previous intervention plans and treatment plans
- Reports by other providers
- School reports
- Medical reports
- Other

### Maladaptive behaviors

Checkbox: **No Maladaptive behavior** (`no_maladaptive_behavior`).

- Checked and no behavior rows: allowed.
- Checked and behavior rows exist: error.
- Unchecked and no behavior rows: error, at least one behavior is required.
- Unchecked and rows exist: each row must be complete.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Maladaptive behavior | `behavior` | rich text | rich text | at least 16 characters, max 50,000 | required, at least 16 visible characters |
| Respective DSM5 symptoms | `dsm5_symptom` | enum | dropdown | one symptom below | required |
| Maladaptive concerns as reported by parents | `parent_concerns` | rich text | rich text | at least 16 characters, max 50,000 | required, at least 16 visible characters |

DSM-5 symptom options:

- Deficits in social-emotional reciprocity, ranging, for example, from abnormal social approach and failure of normal back-and-forth conversation; to reduced sharing of interests, emotions, or affect; to failure to initiate or respond to social interactions.
- Deficits in nonverbal communicative behaviors used for social interaction, ranging, for example, from poorly integrated verbal and nonverbal communication; to abnormalities in eye contact and body language or deficits in understanding and use of gestures; to a total lack of facial expressions and nonverbal communication.
- Deficits in developing, maintaining, and understanding relationships, ranging, for example, from difficulties adjusting behavior to suit various social contexts; to difficulties in sharing imaginative play or in making friends; to absences of interest in peers.
- Stereotyped or repetitive motor movements, use of objects, or speech (e.g., simple motor stereotypies, lining up toys or flipping objects, echolalia, idiosyncratic phrases).
- Insistence on sameness, inflexible adherence to routines, or ritualized patterns of verbal or nonverbal behavior (e.g., extreme distress at small changes, difficulties with transitions, rigid thinking patterns, greeting rituals, need to take same route or eat same food everyday).
- Highly restricted, fixated interests that are abnormal in intensity or focus (e.g., strong attachment to or preoccupation with unusual objects, excessively circumscribed or perseverative interest).
- Hyper- or hyporeactivity to sensory input or unusual interest in sensory aspects of the environment (e.g., apparent indifference to pain/temperature, adverse response to specific sounds or textures, excessive smelling or touching of objects, visual fascination with lights or movement).

### Assessment summary

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Assessment results in terms of domains of deficit vs strengths | `assessment_results` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form only requires some visible text |
| Patient symptoms noted from DSM5 in assessment | derived `dsm5_symptoms` | list | read-only | symptoms already chosen on behavior rows | not a separate input |
| Priorities/ goals based on assessment results | `priorities` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form only requires some visible text |

### Assessment methods

At least one method is required.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Tool used | `tool` | enum | dropdown | VB-MAPP, ABLLS-R, AFLS, FAST, PDDBI, PEAK, QABF, Socially Savvy, Vineland-3, ASAP, OMNIA, SSIS, PSI | required |
| Assessment date | `assessment_date` | date | date | valid date | required |
| Rationale for assessment | `rationale` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form requires at least 16 |
| Rationale for assessment selection | `selection_rationale` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form requires at least 16 |
| Tool description and modules used | `tool_description` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form requires at least 16 |
| Describe the client score | `client_score` | rich text | rich text | max 50,000 | required, at least 60 visible characters. The form requires at least 16 |

Each method can have visuals:

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Visual file | file | file | upload | stored as a URL | a visual row has a URL |
| Visual title | `title` | text | text | 8–255 characters | required when a visual exists |
| Visual analysis | `analysis` | rich text | rich text | at least 16 characters, max 50,000 | required, at least 16 visible characters |

### Barriers

`barriers` is a unique list, at most 23 values. Duplicates and unknown values fail completion. The form does not require a selection.

Options:

- Family stress or caregiver burnout
- Transportation challenges
- Financial hardship
- Insurance coverage limitations
- Scheduling conflicts with school, work, or activities
- Limited understanding of ABA services
- Language or communication barriers
- Cultural beliefs impacting treatment acceptance
- Difficulty maintaining consistent routines at home
- Frequent cancellations or missed appointments
- Limited support system within the family
- Technology or internet access issues for telehealth
- Client illness or medical complications
- Medication changes affecting participation
- Sleep difficulties impacting engagement
- Sensory sensitivities interfering with sessions
- Challenging behaviors limiting participation in services
- Difficulty transitioning between settings or providers
- Caregiver mental health or personal stressors
- Lack of childcare for other children in the home
- Concerns about privacy or services in the home
- Limited motivation or readiness for change
- Communication deficits affecting expression of needs

### Observations

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Observations noted during assessment | `observations` | rich text | rich text | at least 4 characters, max 50,000 | required, at least 4 visible characters. The form requires the field but does not enforce the 4-character minimum |

### Telehealth readiness

Checkbox: **Telehealth readiness assessment needed** (`telehealth_readiness_assessment_needed`).

If checked, assessment date is required and every readiness item below must have a rating and notes. If unchecked, the date and readiness rows must be cleared.

| Label | Field | Type | Control | Limits |
| --- | --- | --- | --- | --- |
| Assessment date | `telehealth_assessment_date` | date | date | required when the checkbox is on |
| Readiness | `readiness` | enum | choice | Not ready, Somewhat, Ready |
| Notes | `notes` | text | text | at least 8 characters, max 50,000 |
| Section Score | `readiness_scores` | integer | read-only | derived for child, caregiver, environment, and overall |
| Overall Score | overall score | integer | read-only | derived |

Readiness items, by section:

Child:

- `attends_to_screen` — Attends to screen ≥ 30 seconds
- `follows_instructions` — Follows telehealth instructions
- `caregiver_mediation` — Tolerates caregiver mediation
- `no_severe_behavior` — No severe SIB or aggression
- `communicates_needs` — Communicates basic needs
- `reinforcers_available` — Reinforcers available via caregiver/screen

Caregiver:

- `available_during_sessions` — Available during sessions
- `implements_directions` — Implements BCBA directions
- `operates_tech` — Operates tech independently
- `manages_safety` — Manages safety appropriately
- `distraction_free_area` — Prepares distraction-free area
- `reinforcers_ready` — Has reinforcers ready
- `attends_reliably` — Attends sessions reliably

Environment:

- `stable_internet` — Stable internet connection
- `camera_audio` — Functional camera & audio
- `quiet_environment` — Quiet environment
- `lighting` — Good lighting / visibility
- `materials` — Materials available
- `confidential_space` — Confidential space

---

## 10. Crisis

Checkbox: **Crisis plan for this client not needed** (`no_crisis_plan_needed`). When it is checked, the page is complete. When it is not checked and there are no plans, the page is empty. Each saved plan must be complete.

Creating a plan requires `assessment_behavior_id`. A later save cannot clear that field.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Related behavior | `assessment_behavior_id` | integer | dropdown of assessment behaviors | greater than 0, must be a behavior on this plan | required |
| Crisis creation date | `crisis_creation_date` | date | month/year | first day of a month. Future dates are allowed | required |
| Operational definition | `operational_definition` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Antecedent interventions/modifications | `antecedent_interventions` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Precursors with action steps to prevent behavior | `precursors_action_steps` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Behavior intervention plan when escalation occurs | `escalation_intervention_plan` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Follow-up steps | `follow_up_steps` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Functional behavior | `functional_behavior` | enum list | multi-select | unique, at most 5 | at least one valid value |
| Consequence strategies for behavior prior to escalation | `consequence_strategies` | rich text | rich text | max 50,000 | required, at least 60 visible characters |

Functional behavior options:

- Escape-Maintained
- Attention-Maintained
- Tangible-Maintained
- Physical-Maintained
- Non-social or Sensory-Maintained

The form uses the same 60-character minimum and a 50,000-character maximum on the rich text fields, and it requires the date, functional behavior, and related behavior.

---

## 11. Goals

The Goals page is the combination of three API sections: Parent caregiver goals (PCG), Skill acquisition goals (SAG), and Behavior reduction goals (BRG). The page is empty only when all three sections are empty. Any error in any section marks Goals in error. There is no Goals form in the current app.

Shared dropdowns:

| Name | Options |
| --- | --- |
| Data collection method | Duration, Instances, Percentage, Rate |
| Mastery direction | increase, decrease |
| Duration aggregation | average, total |
| Measurement unit | Seconds, Minutes, Hours |
| Target timeframe | Short-Term, Intermediate-Term, Long-Term |
| Goal frequency | Twice a week, Once a week, Bi monthly, Monthly |

Shared measurement rules:

- `baseline_level` and `current_level` are 0–100.
- `opportunities` is 1–99.
- `rate_interval` is 1–60. For Hours the interval must be 1–4. For Seconds or Minutes it must be 1–60.
- `mastery_to` and the matching SAG “to” fields are 0 or greater.
- Response counts are at least 1. They cannot be greater than the opportunity count on a Percentage goal.
- For Duration, Instances, and Rate, the mastery target must be above baseline when direction is increase, and below baseline when direction is decrease.
- A field that does not belong to the selected method is rejected.
- `goal_name_id` and `data_collection_method` cannot be set back to null.
- Creating a goal requires `goal_name_id` greater than 0.
- Rich text is sanitized. Stored rich text max is 50,000 characters.
- Target stage history must start at New, dates cannot move backward, and only listed transitions are allowed. On Hold can return to the prior active stage or move to Discontinued. Discontinued can return only to the prior active stage. A same-day change is allowed only for the first step out of New. System-only transitions cannot be requested by a user.

Fields required by method, for each criteria block:

| Method | Method fields | Criteria fields |
| --- | --- | --- |
| Duration | `duration_unit` | direction, aggregation, to, sessions |
| Instances | none | direction, to, sessions |
| Percentage | `opportunities` | responses, sessions |
| Rate | `rate_interval`, `rate_unit` | direction, to, sessions |

PCG uses one block named `mastery`. SAG uses `acquisition`, `generalization`, and `maintenance`. BRG uses one block named `mastery`.

Default session counts when a method is chosen: PCG mastery 3, BRG mastery 3, SAG acquisition 3, SAG generalization 3, SAG maintenance 10. Direction defaults to increase. Duration aggregation defaults to average. Rate interval defaults to 1.

### PCG goal

Focus area is fixed: Parent training. The goal name must be an active goal in that focus area.

| Field | Type | Limits | Completion |
| --- | --- | --- | --- |
| `goal_name_id` | integer | greater than 0 | required, active Parent training goal |
| `data_collection_method` | enum | shared list | required |
| method fields | mixed | shared table | required for the method |
| `baseline_date` | date | date | required |
| `baseline_level` | number | 0–100 | required |
| `current_level` | number | 0–100 | required |
| `expected_mastery_date` | month-year | `mm-yyyy` | required |
| `goal_description` | rich text | max 50,000 | required, some visible text |
| mastery criteria | mixed | shared table. Percentage responses must be at least 1 | required for the method |

### PCG target

| Field | Type | Limits | Completion |
| --- | --- | --- | --- |
| `target_name` | text | max 500 | required, at least 8 characters |
| `timeframe` | enum | shared list | required |
| `baseline_date` | date | date | required |
| `baseline_level` | number | 0–100 | required |
| method baseline fields | mixed | must match the goal method | required for the method, forbidden otherwise |
| `description` | rich text | max 50,000 | required, at least 60 visible characters |
| `instructions` | text | max 50,000 | required, at least 60 characters |
| stage history | list | New, Acquisition, Mastered, On-hold, Discontinued | required and must follow the transition rules |

PCG stage moves: New to Acquisition, On-hold, or Discontinued. Acquisition to Mastered, On-hold, or Discontinued. Mastered back to Acquisition. New to Acquisition may happen on the same day. `stage` and `stage_date` are required when adding a stage. `reason` is optional, max 500 characters. A later edit can change only the stage date.

### SAG goal

The goal name must be an active goal in a skill acquisition focus area.

| Field | Type | Limits | Completion |
| --- | --- | --- | --- |
| `goal_name_id` | integer | greater than 0 | required, active skill-acquisition goal |
| `data_collection_method` | enum | shared list | required |
| method fields | mixed | shared table | required for the method |
| `baseline_date` | date | date | required |
| `baseline_level` | number | 0–100 | required |
| `current_level` | number | 0–100 | required |
| `frequency` | enum | shared list | required |
| `expected_mastery_date` | month-year | `mm-yyyy` | required |
| `goal_description` | rich text | max 50,000 | required |
| acquisition, generalization, and maintenance criteria | mixed | response and session counts are also capped by the API maximum | required for the method |

Extra Percentage rules for SAG:

- Baseline must be lower than the opportunity count.
- Each block’s success rate must be at least 80 percent.
- Acquisition and generalization need at least 3 consecutive sessions.
- Maintenance needs at least 8 consecutive sessions.

Linked BRG goals are returned on the goal. They are not edited as a SAG field.

### SAG target

Same shape as a PCG target, except the name minimum used by SAG and BRG is 16 characters.

Stages: New, Probe, Acquisition, Generalization, Maintenance, Mastered, On-hold, Discontinued.

Moves:

- New to Probe, On-hold, or Discontinued. New to Probe may be the same day.
- Probe to Acquisition, On-hold, or Discontinued. Probe to Acquisition is automatic after three 97153 sessions and cannot be requested by a user.
- Acquisition to Generalization, On-hold, or Discontinued.
- Generalization to Acquisition, Maintenance, On-hold, or Discontinued.
- Maintenance to Generalization, Mastered, On-hold, or Discontinued.
- Mastered to Maintenance or Generalization.

### BRG goal

Focus area is Behavior change. The goal name must be an active goal in that focus area. The DSM-5 symptom must be one already recorded on this plan’s Assessment page.

| Field | Type | Limits | Completion |
| --- | --- | --- | --- |
| `goal_name_id` | integer | greater than 0 | required, active behavior-change goal |
| `dsm5_symptom` | enum | same DSM-5 list as Assessment | required, and it must exist on this plan’s Assessment page |
| `linked_sag_goal_ids` | integer list | max 100 ids | links to SAG goals on this plan |
| `data_collection_method` | enum | shared list | required |
| method fields | mixed | shared table. BRG has no `opportunities` field on the goal payload | required for the method |
| `baseline_date` | date | date | required |
| `baseline_level` | number | 0–100 | required |
| `current_level` | number | 0–100 | required |
| `frequency` | enum | shared list | required |
| `expected_mastery_date` | month-year | `mm-yyyy` | required |
| `operational_definition` | rich text | max 50,000 | required |
| `objective` | rich text | max 50,000 | required |
| `antecedent_modifications` | rich text | max 50,000 | required |
| `consequence_modifications` | rich text | max 50,000 | required |
| `goal_description` | rich text | max 50,000 | required |
| mastery criteria | mixed | `mastery_sessions` is 1–100 | required for the method |

Hypothesized functions are saved as their own list. At least one and at most four unique values: Sensory, Escape/avoidance, Attention, Tangible.

### BRG target

Same shape as a SAG target. Name minimum is 16 characters.

Stages: New, In progress, Mastered, On-hold, Discontinued.

Moves:

- New to In progress, On-hold, or Discontinued. New to In progress may be the same day.
- In progress to Mastered, On-hold, or Discontinued.
- Mastered back to In progress.

---

## 12. Discharge

A saved discharge row is required before the page can be complete. All four narrative fields and at least one reason are required.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Client's and family's ability to master the program | `mastery_of_program_goals` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Titration plan | `titration_plan` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Client's readiness to step down | `readiness_to_step_down` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Care coordination | `care_coordination` | rich text | rich text | max 50,000 | required, at least 60 visible characters |
| Reasons to decrease hours or discharge may include | `reason` | enum | dropdown | options below | at least one reason |
| Explain other | `explanation` | text | text | at least 4 characters when reason is Other | required only for Other |

Reason options:

- The client has mastered all treatment goals, and no new goals are identified
- All maladaptive behavior goals have been mastered and generalized
- No new behaviors have emerged
- Client’s Vineland-3 scores have reached a level in accordance with similar-aged peers
- Client’s AFLS scores have reached a level in accordance with similar-aged peers
- Client’s parents/caregivers report confidence in continuing ABA intervention techniques
- Client no longer able to participate due to medical reasons
- Parents prefer a new provider
- Client no longer able to participate due to personal changes
- No progress has been made for 3 months
- Goals are not maintaining or generalizing
- Other

The form uses the same 60-character minimum, 50,000-character maximum, and Other explanation rule.

---

## 13. Treatment

Header fields are required. Units are calculated as hours times 4 and are not stored. A frequency is required only when that service has hours greater than 0. At least one service must have hours greater than 0. Hours of 97151 and 97152 together must be 8 or fewer. Each of those two codes is also capped at 8. The other codes are capped at 99.

| Label | Field | Type | Control | Limits | Completion |
| --- | --- | --- | --- | --- | --- |
| Recommendations explanation | `recommendations_explanation` | rich text | rich text | max 50,000 | required, some visible text |
| Proposed start date | `proposed_start_date` | date | date | valid date | required |
| Duration (months) | `duration_in_months` | integer | number | 1–99 | required |
| Therapy provisioning description | `therapy_provisioning_description` | text | read-only | derived from the plan bay | required for bays 2.6, 3, 6, and 7 when the derived text exists. Bay 3 text is missing until an active behavior technician is assigned |

Service rows. Each row has Hours (`<prefix>_hours`, integer), Units (derived, read-only), and Per (`<prefix>_per`).

| Label | Prefix | Hours | Per options |
| --- | --- | --- | --- |
| 97151 Assessment | `assessment_97151` | 0–8, combined with 97152 at most 8 | Weekly, bi-weekly, Monthly, 6-months authorization period |
| 97152 Assisting Assessment | `assessment_97152` | 0–8, combined with 97151 at most 8 | same |
| 97153 Direct ABA Technician 1:1 | `direct_therapy_97153` | 0–99 | same |
| 97155 Protocol Modification by BCBA | `protocol_modification_97155` | 0–99 | same |
| 97156 Parent Training/Caregiver Support | `parent_training_97156` | 0–99 | same |
| 97157 Group Parent Training (2–8 parents in a group setting) | `group_parent_training_97157` | 0–99 | same |
| 99366 Care Coordination | `care_coordination_99366` | 0–99 | same |

The form requires a frequency on every service row, including rows with no hours. Completion requires a frequency only when hours are greater than 0.

Provisioning text by bay:

- Bay 2.6 and Bay 7: a fixed statement that a trained behavioral technician administers the protocol under BCBA supervision.
- Bay 3: a statement that names the assigned behavior technicians and says the therapist is the parent of the recipient and is supervised by a BCBA. It is blank when no technician is assigned.
- Bay 6: a fixed statement that a BCBA administers the protocol.
- Bay 2.5, Bay 2.7, and any other bay: no provisioning text, and completion does not require it.

---

## Data schema

All v3 page tables hang off `treatment_plan`. Deleting a plan cascades to its v3 rows. Child rows cascade when their parent page row is deleted. Crisis plans do not cascade from the assessment behavior: `assessment_behavior_id` uses `ON DELETE RESTRICT`, so a behavior that has a crisis plan cannot be deleted until that plan is removed.

Every v3 table has `id` as an integer primary key unless a table below says otherwise. Almost every table also has:

| Column | SQL type | Null | Notes |
| --- | --- | --- | --- |
| `date_row_created` | timestamp | no | server default `CURRENT_TIMESTAMP` |
| `date_row_updated` | timestamp | yes on most tables, no on goal tables | server default `CURRENT_TIMESTAMP`, updated on change |

Goal, target, stage, and hypothesized-function timestamps are timezone-aware. Stage rows and hypothesized-function rows have `date_row_created` only. Entries created before the plan was signed are locked.

`Numeric` measurement columns have no fixed scale in the model. Education hours and therapy hours are `numeric(4,1)`.

### `treatment_plan`

Existing plan table. Columns the v3 API uses:

| Column | SQL type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer | no | primary key |
| `client_id` | integer | no | foreign key to `client.id` |
| `provider_id` | integer | no | foreign key to `provider.id`, plan owner |
| `status_id` | integer | no | foreign key to `treatment_plan_status.id` |
| `bay` | string | yes | plan bay |
| `version` | integer | no | `3` for a v3 plan. No database default |
| `has_medication` | boolean | yes | Medication page checkbox. `null` untouched, `true` client takes medication, `false` no medication |
| `parent_treatment_plan_id` | integer | yes | foreign key to `treatment_plan.id`, `ON DELETE SET NULL` |
| `date_treatment_plan_started` | timestamptz | no | |
| `date_treatment_plan_ended` | timestamptz | yes | |
| `signature` | string | yes | |
| `utc_offset_date_end` | integer | yes | |
| `prior_authorization_number_2` | string | yes | |

### `treatment_plan_v3_medical_info`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK `treatment_plan.id` cascade |
| `allergies` | string | yes |
| `special_diets` | string | yes |
| `hearing_difficulty` | string | yes |
| `hearing_screening_date` | date | yes |
| `vision_difficulty` | string | yes |
| `vision_screening_date` | date | yes |
| `trauma_history` | text | yes |
| `hospitalization_history` | text | yes |
| `asd_severity_level` | string | yes |
| `asd_diagnosis_provider_name` | string | yes |
| `asd_diagnosis_city` | string | yes |
| `asd_diagnosis_state` | string(2) | yes |
| `asd_diagnosis_year` | integer | yes |
| `child_delivery_type` | string | yes |
| `child_gestational_age_weeks` | integer | yes |
| `child_weight_at_birth_pounds` | integer | yes |
| `child_weight_at_birth_ounces` | integer | yes |
| `child_sitting_up_age_months` | integer | yes |
| `child_crawling_age_months` | integer | yes |
| `child_walking_age_years` | integer | yes |
| `child_walking_age_months` | integer | yes |
| `child_standing_age_years` | integer | yes |
| `child_standing_age_months` | integer | yes |
| `child_babbling_age_months` | integer | yes |
| `child_first_word` | string | yes |
| `child_second_word` | string | yes |
| `child_first_words_age_months` | integer | yes |

### `treatment_plan_v3_medical_info_diagnosis`

Many rows per medical info. Indexed on `medical_info_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `medical_info_id` | integer | no, FK cascade |
| `diagnosis_name` | string | yes |
| `provider_name` | string | yes |
| `city` | string | yes |
| `state` | string(2) | yes |
| `year` | integer | yes |

### `treatment_plan_v3_medical_info_selection`

Unique on `(medical_info_id, selection_type, value)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `medical_info_id` | integer | no, FK cascade |
| `selection_type` | string | yes |
| `value` | string | yes |

### `treatment_plan_v3_referral`

Many rows per plan. Indexed on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `referral_date` | date | yes |
| `provider_name` | string | yes |
| `diagnosis_tool` | string | yes |
| `city` | string | yes |
| `state` | string(2) | yes |

### `treatment_plan_v3_medication`

Many rows per plan. Indexed on `treatment_plan_id`. The no-medication flag is `treatment_plan.has_medication`, not a column on this table.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `medication_name` | string | yes |
| `dosage` | string | yes |
| `start_date` | date | yes |
| `physician_name` | string | yes |
| `reason` | string | yes |

### `treatment_plan_v3_therapy`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `no_historical_therapy` | boolean | yes |

### `treatment_plan_v3_therapy_row`

Many rows per therapy page. Indexed on `therapy_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `therapy_id` | integer | no, FK `treatment_plan_v3_therapy.id` cascade |
| `provider_name` | string | yes |
| `service_type` | string | yes |
| `phone_number` | string(10) | yes |
| `email` | string | yes |
| `start_date` | date | yes |
| `end_date` | date | yes |
| `hours` | numeric(4,1) | yes |
| `frequency` | string | yes |
| `progress` | string | yes |
| `do_not_share_info_with_provider` | boolean | no, default false |
| `is_record_shared` | string | yes |

### `treatment_plan_v3_education`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `not_attending_school` | boolean | no, default false |
| `education_setting` | string | yes |
| `number_of_hours_per_week` | numeric(4,1) | yes |
| `school_name` | string | yes |
| `school_phone_number` | string(10) | yes |
| `education_description` | text | yes |
| `focus_area_description` | text | yes |
| `evaluation_status` | string | yes |
| `evaluation_date` | date | yes |
| `iep_or_504_in_place` | string | yes |
| `education_support` | text | yes |
| `classroom_setting` | string | yes |
| `attitude_towards_school` | string | yes |

### `treatment_plan_v3_family`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `cultural_consideration` | text | yes |

### `treatment_plan_v3_family_member`

Indexed on `family_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `family_id` | integer | no, FK cascade |
| `full_name` | string | yes |
| `member_role` | string | yes |
| `caregiver_type` | string | yes |
| `relationship_to_client` | string | yes |
| `custody_type` | string | yes |
| `marital_status` | string | yes |
| `job_title` | string | yes |
| `email` | string | yes |
| `phone` | string(10) | yes |
| `street_address_line_one` | string | yes |
| `street_address_line_two` | string | yes |
| `street_address_city` | string | yes |
| `street_address_state` | string(2) | yes |
| `street_address_zip` | string(5) | yes |

### `treatment_plan_v3_family_sibling`

Indexed on `family_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `family_id` | integer | no, FK cascade |
| `sibling_relationship` | string | yes |
| `sibling_age` | integer | yes |
| `sibling_diagnosis` | string | yes |

### `treatment_plan_v3_family_additional_info`

Indexed on `family_id`. The API name `value` is stored in `description`.

| Column | SQL type | Null |
| --- | --- | --- |
| `family_id` | integer | no, FK cascade |
| `info_type` | string | yes |
| `description` | string | yes |

### `treatment_plan_v3_child`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `child_behavior_issues` | text | yes |

### `treatment_plan_v3_child_background`

Indexed on `child_id`. Ordered by created time, then id.

| Column | SQL type | Null |
| --- | --- | --- |
| `child_id` | integer | no, FK cascade |
| `background_type` | string | yes |
| `background_description` | string | yes |

### `treatment_plan_v3_child_schedule`

Indexed on `child_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `child_id` | integer | no, FK cascade |
| `day_of_week` | string | yes |
| `schedule_activity_type` | string | yes |
| `schedule_start_date` | timestamptz | yes |
| `schedule_end_date` | timestamptz | yes |
| `utc_offset` | integer | yes |

### `treatment_plan_v3_assessment`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `initial_assessment_date` | date | yes |
| `reassessment_date` | date | yes |
| `diagnostic_report_reviewed` | boolean | yes |
| `parent_interview_summary` | text | yes |
| `assessment_results` | text | yes |
| `priorities` | text | yes |
| `additional_files_viewed` | string array | no, default empty |
| `no_maladaptive_behavior` | boolean | no, default false |
| `telehealth_readiness_assessment_needed` | boolean | no, default false |
| `telehealth_assessment_date` | date | yes |
| `barriers` | string array | no, default empty |
| `observations` | text | yes |

### `treatment_plan_v3_assessment_behavior`

Indexed on `assessment_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `assessment_id` | integer | no, FK cascade |
| `behavior` | text | yes |
| `dsm5_symptom` | text | yes |
| `parent_concerns` | text | yes |

### `treatment_plan_v3_assessment_method`

Indexed on `assessment_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `assessment_id` | integer | no, FK cascade |
| `tool` | string | yes |
| `assessment_date` | date | yes |
| `rationale` | text | yes |
| `selection_rationale` | text | yes |
| `tool_description` | text | yes |
| `client_score` | text | yes |

### `treatment_plan_v3_assessment_visual`

Indexed on `method_id`. The API returns a URL. The table stores the storage key.

| Column | SQL type | Null |
| --- | --- | --- |
| `method_id` | integer | no, FK cascade |
| `file_storage_key` | string | no |
| `title` | string(255) | yes |
| `analysis` | text | yes |

### `treatment_plan_v3_assessment_readiness`

Unique on `(assessment_id, item)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `assessment_id` | integer | no, FK cascade |
| `item` | string | no |
| `readiness` | string | yes |
| `notes` | text | yes |

### `treatment_plan_v3_crisis`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `no_crisis_plan_needed` | boolean | no, default false |

### `treatment_plan_v3_crisis_plan`

Unique on `assessment_behavior_id`. One crisis plan per maladaptive behavior.

| Column | SQL type | Null |
| --- | --- | --- |
| `crisis_id` | integer | no, FK `treatment_plan_v3_crisis.id` cascade |
| `assessment_behavior_id` | integer | no, FK `treatment_plan_v3_assessment_behavior.id` restrict |
| `crisis_creation_date` | date | yes |
| `operational_definition` | text | yes |
| `antecedent_interventions` | text | yes |
| `precursors_action_steps` | text | yes |
| `escalation_intervention_plan` | text | yes |
| `follow_up_steps` | text | yes |
| `functional_behavior` | string array | no, default empty |
| `consequence_strategies` | text | yes |

### `treatment_plan_v3_pcg_goal`

Unique on `(treatment_plan_id, goal_name_id)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `goal_name_id` | integer | no, FK `goal_name.id` |
| `data_collection_method` | string | yes |
| `duration_unit` | string | yes |
| `baseline_date` | date | yes |
| `baseline_level` | numeric | yes |
| `opportunities` | integer | yes |
| `rate_interval` | integer | yes |
| `rate_unit` | string | yes |
| `current_level` | numeric | yes |
| `mastery_direction` | string | yes |
| `mastery_aggregation` | string | yes |
| `mastery_to` | numeric | yes |
| `mastery_responses` | integer | yes |
| `mastery_sessions` | integer | yes |
| `expected_mastery_date` | string(7) | yes, stored `yyyy-mm` |
| `goal_description` | text | yes |

### `treatment_plan_v3_pcg_target`

Indexed on `goal_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `goal_id` | integer | no, FK cascade |
| `target_name` | string(500) | yes |
| `timeframe` | string | yes |
| `baseline_date` | date | yes |
| `baseline_level` | numeric | yes |
| `duration_unit` | string | yes |
| `opportunities` | integer | yes |
| `rate_interval` | integer | yes |
| `rate_unit` | string | yes |
| `description` | text | yes |
| `instructions` | text | yes |

### `treatment_plan_v3_pcg_target_stage`

Unique on `(target_id, order)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `target_id` | integer | no, FK cascade |
| `stage` | string | no |
| `reason` | string(500) | no |
| `stage_date` | date | no |
| `order` | integer | no |

### `treatment_plan_v3_sag_goal`

Unique on `(treatment_plan_id, goal_name_id)`. Same measurement columns as PCG, plus three criteria blocks and frequency. No `mastery_*` columns.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `goal_name_id` | integer | no, FK `goal_name.id` |
| `data_collection_method` | string | yes |
| `duration_unit` | string | yes |
| `baseline_date` | date | yes |
| `baseline_level` | numeric | yes |
| `opportunities` | integer | yes |
| `rate_interval` | integer | yes |
| `rate_unit` | string | yes |
| `current_level` | numeric | yes |
| `acquisition_direction` | string | yes |
| `acquisition_aggregation` | string | yes |
| `acquisition_to` | numeric | yes |
| `acquisition_responses` | integer | yes |
| `acquisition_sessions` | integer | yes |
| `generalization_direction` | string | yes |
| `generalization_aggregation` | string | yes |
| `generalization_to` | numeric | yes |
| `generalization_responses` | integer | yes |
| `generalization_sessions` | integer | yes |
| `maintenance_direction` | string | yes |
| `maintenance_aggregation` | string | yes |
| `maintenance_to` | numeric | yes |
| `maintenance_responses` | integer | yes |
| `maintenance_sessions` | integer | yes |
| `frequency` | string | yes |
| `expected_mastery_date` | string(7) | yes, stored `yyyy-mm` |
| `goal_description` | text | yes |

### `treatment_plan_v3_sag_target`

Indexed on `goal_id`. Same columns as `treatment_plan_v3_pcg_target`, with `goal_id` pointing at `treatment_plan_v3_sag_goal.id`.

### `treatment_plan_v3_sag_target_stage`

Unique on `(target_id, order)`. Same columns as the PCG stage table, with `target_id` pointing at `treatment_plan_v3_sag_target.id`.

### `treatment_plan_v3_brg_goal`

Unique on `(treatment_plan_id, goal_name_id)`. No `opportunities` or `mastery_responses` columns.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `goal_name_id` | integer | no, FK `goal_name.id` |
| `related_to_maladaptive_behavior` | boolean | no, default false |
| `dsm5_symptom` | text | yes |
| `data_collection_method` | string | yes |
| `duration_unit` | string | yes |
| `baseline_date` | date | yes |
| `baseline_level` | numeric | yes |
| `rate_interval` | integer | yes |
| `rate_unit` | string | yes |
| `current_level` | numeric | yes |
| `mastery_direction` | string | yes |
| `mastery_aggregation` | string | yes |
| `mastery_to` | numeric | yes |
| `mastery_sessions` | integer | yes |
| `frequency` | string | yes |
| `expected_mastery_date` | string(7) | yes, stored `yyyy-mm` |
| `operational_definition` | text | yes |
| `objective` | text | yes |
| `antecedent_modifications` | text | yes |
| `consequence_modifications` | text | yes |
| `goal_description` | text | yes |

### `treatment_plan_v3_brg_goal_sag_link`

Composite primary key. Both sides cascade.

| Column | SQL type | Null |
| --- | --- | --- |
| `brg_goal_id` | integer | no, PK, FK cascade |
| `sag_goal_id` | integer | no, PK, FK cascade, indexed |

### `treatment_plan_v3_brg_hypothesized_function`

Unique on `(goal_id, function_date)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `goal_id` | integer | no, FK cascade |
| `function_date` | date | no |
| `functions` | string array | no |

### `treatment_plan_v3_brg_target`

Indexed on `goal_id`. Same shape as a PCG target, without `opportunities`. `goal_id` points at `treatment_plan_v3_brg_goal.id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `goal_id` | integer | no, FK cascade |
| `target_name` | string(500) | yes |
| `timeframe` | string | yes |
| `baseline_date` | date | yes |
| `baseline_level` | numeric | yes |
| `duration_unit` | string | yes |
| `rate_interval` | integer | yes |
| `rate_unit` | string | yes |
| `description` | text | yes |
| `instructions` | text | yes |

### `treatment_plan_v3_brg_target_stage`

Unique on `(target_id, order)`. Same columns as the PCG stage table, with `target_id` pointing at `treatment_plan_v3_brg_target.id`.

### `treatment_plan_v3_discharge`

One row per plan. Unique on `treatment_plan_id`.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `mastery_of_program_goals` | text | yes |
| `titration_plan` | text | yes |
| `readiness_to_step_down` | text | yes |
| `care_coordination` | text | yes |

### `treatment_plan_v3_discharge_reason`

Unique on `(discharge_id, reason)`.

| Column | SQL type | Null |
| --- | --- | --- |
| `discharge_id` | integer | no, FK cascade |
| `reason` | string | no |
| `explanation` | string | yes |

### `treatment_plan_v3_treatment`

One row per plan. Unique on `treatment_plan_id`. Units are not stored.

| Column | SQL type | Null |
| --- | --- | --- |
| `treatment_plan_id` | integer | no, FK cascade |
| `recommendations_explanation` | text | yes |
| `proposed_start_date` | date | yes |
| `duration_in_months` | integer | yes |
| `assessment_97151_hours` | integer | yes |
| `assessment_97151_per` | string | yes |
| `assessment_97152_hours` | integer | yes |
| `assessment_97152_per` | string | yes |
| `direct_therapy_97153_hours` | integer | yes |
| `direct_therapy_97153_per` | string | yes |
| `protocol_modification_97155_hours` | integer | yes |
| `protocol_modification_97155_per` | string | yes |
| `parent_training_97156_hours` | integer | yes |
| `parent_training_97156_per` | string | yes |
| `group_parent_training_97157_hours` | integer | yes |
| `group_parent_training_97157_per` | string | yes |
| `care_coordination_99366_hours` | integer | yes |
| `care_coordination_99366_per` | string | yes |

Information has no table. It is assembled from the client, assignments, and insurance.

---

## API

Base path: `/api/v2/treatment_plans`.

Every route is behind the `TREATMENT_PLAN_V3_ENABLED` feature flag. When the flag is off, the route returns 404 with “Treatment plan v3 is not enabled”. Request and response bodies are fully redacted in logs.

### Access

Read roles: admin, assistant assessor, BCBA, biller, client success manager, clinical documentation QA specialist, guardian, invoice coordinator, limited access guardian, onboarding coordinator, PRBT, VBT.

Write roles: assistant assessor, BCBA.

A read loads the plan, checks that the caller can access that client, and rejects a plan whose `version` is not 3 with 409.

A write locks the plan row first, requires version 3, and uses the same edit check as v1: the plan is not completed or read-only, and the caller owns the plan or is clinically assigned to the client. A missing plan is 404.

Unknown JSON fields are rejected. Blank strings become null. Surrounding spaces are stripped. On a PATCH, an omitted field stays as stored and `null` clears it, except where a field is documented as not nullable.

Creates return 201. Deletes return 204 with an empty body. Reads and updates return 200.

### Plan

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| POST | `/` | `TreatmentPlanV3Create` | `TreatmentPlanResponse`, 201 |
| GET | `/{treatment_plan_id}/` | none | `TreatmentPlanResponse` |
| GET | `/{treatment_plan_id}/pages/` | none | list of `PageStatusResponse` |

`TreatmentPlanV3Create`:

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `client_id` | integer | yes | |
| `bay` | bay enum | yes | |
| `intake_questionnaire_id` | integer | no | copy source |
| `clone_source_tp_id` | integer | no | clone source |

Send at most one of `intake_questionnaire_id` and `clone_source_tp_id`. Omit both to create a blank plan.

`PageStatusResponse`:

| Field | Type |
| --- | --- |
| `page` | one of information, medical, referral, medication, therapy, education, family, child, assessment, crisis, goals, discharge, treatment |
| `status` | `empty`, `completed`, or `error` |
| `errors` | list of `{ field, row_id or null, message }` |

### Information

| Method | Path | Response |
| --- | --- | --- |
| GET | `/{treatment_plan_id}/pages/information/` | `TreatmentPlanV3InformationResponse` |

Response:

| Field | Type |
| --- | --- |
| `client` | `{ id, first_name, last_name, date_of_birth or null, sex }` |
| `home_bcba` | `{ provider_id, display_name }` or null |
| `bobbing_bcba` | `{ provider_id, display_name }` or null |
| `substitute_bcbas` | list of providers |
| `assigned_bts` | list of providers |
| `insurance.primary` | `{ payor_name, member_id, date_start, date_end }` or null |
| `insurance.secondary` | same or null |
| `insurance.tertiary` | same or null |

### Medical

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/medical/` | none | `MedicalPageResponse` |
| PATCH | `/{id}/pages/medical/` | `MedicalInfoPatch` | `MedicalInfoResponse` or null |
| POST | `/{id}/pages/medical/diagnoses/` | `MedicalDiagnosisBody` | `MedicalDiagnosisResponse`, 201 |
| PATCH | `/{id}/pages/medical/diagnoses/{diagnosis_id}/` | `MedicalDiagnosisBody` | `MedicalDiagnosisResponse` |
| DELETE | `/{id}/pages/medical/diagnoses/{diagnosis_id}/` | none | 204 |
| POST | `/{id}/pages/medical/selections/` | `MedicalSelectionCreate` | `MedicalSelectionResponse`, 201 |
| DELETE | `/{id}/pages/medical/selections/{selection_type}/{selection_id}/` | none | 204 |

`MedicalPageResponse` is `{ medical_info, diagnoses, selections }`. `MedicalSelectionCreate` requires `selection_type` and `value`. The value must belong to that type.

### Referral

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/referrals/` | none | list of `TreatmentPlanV3ReferralResponse` |
| POST | `/{id}/pages/referrals/` | `TreatmentPlanV3ReferralCreate` | one referral, 201 |
| PATCH | `/{id}/pages/referrals/{referral_id}/` | `TreatmentPlanV3ReferralPatch` | one referral |
| DELETE | `/{id}/pages/referrals/{referral_id}/` | none | 204 |

Response fields: `id`, `referral_date`, `provider_name`, `diagnosis_tool`, `city`, `state`.

### Medication

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/medications/` | none | `MedicationPageResponse` |
| PATCH | `/{id}/pages/medications/` | `{ no_medication: boolean }` | `MedicationPageResponse` |
| POST | `/{id}/pages/medications/` | `MedicationCreateRequest` | `MedicationResponse`, 201 |
| PATCH | `/{id}/pages/medications/{medication_id}/` | `MedicationPatchRequest` | `MedicationResponse` |
| DELETE | `/{id}/pages/medications/{medication_id}/` | none | 204 |
| DELETE | `/{id}/pages/medications/all/` | none | 204 |

`MedicationPageResponse` is `{ no_medication, medications }`. `no_medication` is true only when `has_medication` is false. A create needs at least one of the five data fields.

### Therapy

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/therapy/` | none | `TherapyPageResponse` |
| PATCH | `/{id}/pages/therapy/` | `{ no_historical_therapy: boolean }` | `TherapyPageResponse` |
| POST | `/{id}/pages/therapy/` | `TherapyCreateRequest` | `TherapyResponse`, 201 |
| PATCH | `/{id}/pages/therapy/{therapy_id}/` | `TherapyPatchRequest` | `TherapyResponse` |
| DELETE | `/{id}/pages/therapy/{therapy_id}/` | none | 204 |

`TherapyPageResponse` is `{ no_historical_therapy, therapies }`. Create requires at least one clinical field. `do_not_share_info_with_provider` defaults to false and cannot be null.

### Education

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/education/` | none | `EducationPageResponse` |
| PATCH | `/{id}/pages/education/` | `EducationPatchRequest` | `EducationPageResponse` |

`not_attending_school` defaults to false on the request. The response includes every education column. There is no separate id in the response.

### Family

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/family/` | none | `FamilyPageResponse` |
| PATCH | `/{id}/pages/family/` | `{ cultural_consideration }` | `FamilyPageResponse` |
| POST | `/{id}/pages/family/members/` | `FamilyMemberCreateRequest` | `FamilyMemberResponse`, 201 |
| PATCH | `/{id}/pages/family/members/{member_id}/` | `FamilyMemberPatchRequest` | `FamilyMemberResponse` |
| DELETE | `/{id}/pages/family/members/{member_id}/` | none | 204 |
| POST | `/{id}/pages/family/siblings/` | `FamilySiblingCreateRequest` | `FamilySiblingResponse`, 201 |
| PATCH | `/{id}/pages/family/siblings/{sibling_id}/` | `FamilySiblingPatchRequest` | `FamilySiblingResponse` |
| DELETE | `/{id}/pages/family/siblings/{sibling_id}/` | none | 204 |
| POST | `/{id}/pages/family/additional_info/` | `{ info_type, value }` | `FamilyTaggedItemResponse`, 201 |
| DELETE | `/{id}/pages/family/additional_info/{item_id}/` | none | 204 |

`FamilyPageResponse` splits additional info into `maternal_medical_history`, `paternal_medical_history`, `community_support`, and `additional_info` for any other `info_type`. Tagged items expose `description` as `value`.

### Child

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/child/` | none | `ChildPageResponse` |
| PATCH | `/{id}/pages/child/` | `{ child_behavior_issues }` | `ChildPageResponse` |
| POST | `/{id}/pages/child/backgrounds/` | `ChildBackgroundCreateRequest` | `ChildBackgroundResponse`, 201 |
| DELETE | `/{id}/pages/child/backgrounds/{background_id}/` | none | 204 |
| POST | `/{id}/pages/child/schedule/` | `ChildScheduleCreateRequest` | `ChildScheduleResponse`, 201 |
| DELETE | `/{id}/pages/child/schedule/{schedule_id}/` | none | 204 |

Background and schedule rows are created and deleted. They are not patched. Schedule times must be timezone-aware. The response schedule is sorted.

### Assessment

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/assessment/` | none | `AssessmentPageResponse` |
| PATCH | `/{id}/pages/assessment/` | `AssessmentPatchRequest` | `AssessmentPageResponse` |
| GET | `/{id}/pages/assessment/templates/` | none | `AssessmentTemplateCatalogResponse` |
| POST | `/{id}/pages/assessment/behaviors/` | `BehaviorCreateRequest` | `BehaviorResponse`, 201 |
| PATCH | `/{id}/pages/assessment/behaviors/{behavior_id}/` | `BehaviorPatchRequest` | `BehaviorResponse` |
| DELETE | `/{id}/pages/assessment/behaviors/{behavior_id}/` | none | 204 |
| POST | `/{id}/pages/assessment/methods/` | `MethodCreateRequest` | `MethodResponse`, 201 |
| PATCH | `/{id}/pages/assessment/methods/{method_id}/` | `MethodPatchRequest` | `MethodResponse` |
| DELETE | `/{id}/pages/assessment/methods/{method_id}/` | none | 204 |
| PATCH | `/{id}/pages/assessment/readiness/{item}/` | `ReadinessPatchRequest` | `ReadinessResponse` |
| POST | `/{id}/pages/assessment/methods/{method_id}/visuals/` | multipart file list | list of `VisualResponse`, 201 |
| PATCH | `/{id}/pages/assessment/methods/{method_id}/visuals/{visual_id}/` | `VisualPatchRequest` | `VisualResponse` |
| PATCH | `/{id}/pages/assessment/methods/{method_id}/visuals/{visual_id}/file/` | multipart one file | `VisualResponse` |
| DELETE | `/{id}/pages/assessment/methods/{method_id}/visuals/{visual_id}/` | none | 204 |

`{item}` is a readiness item id such as `attends_to_screen`. Method and visual ids must be greater than 0.

`AssessmentPageResponse` adds derived fields that are not stored as their own columns: `behaviors`, `methods`, `readiness_items`, `dsm5_symptoms`, and `readiness_scores` (`child`, `caregiver`, `environment`, `overall`).

`AssessmentTemplateCatalogResponse` is `{ page: { parent_interview_summary, assessment_results, priorities }, methods: { tool: { rationale, selection_rationale, tool_description, client_score } } }`.

`VisualResponse` is `{ id, title, analysis, url }`.

### Crisis

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/crisis/` | none | `CrisisPageResponse` |
| PATCH | `/{id}/pages/crisis/` | `{ no_crisis_plan_needed: boolean }` | `CrisisPageResponse` |
| GET | `/{id}/pages/crisis/templates/` | none | `CrisisTemplateCatalogResponse` |
| POST | `/{id}/pages/crisis/` | `CrisisPlanCreateRequest` | `CrisisPlanResponse`, 201 |
| PATCH | `/{id}/pages/crisis/{crisis_plan_id}/` | `CrisisPlanPatchRequest` | `CrisisPlanResponse` |
| DELETE | `/{id}/pages/crisis/{crisis_plan_id}/` | none | 204 |

Create requires `assessment_behavior_id`. Patch cannot set it to null. The template response is the six rich-text template strings: `operational_definition`, `antecedent_interventions`, `precursors_action_steps`, `escalation_intervention_plan`, `follow_up_steps`, `consequence_strategies`.

### PCG

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/pcg/` | none | `PcgPageResponse` |
| POST | `/{id}/pages/pcg/goals/` | `PcgGoalCreateRequest` | `PcgGoalResponse`, 201 |
| PATCH | `/{id}/pages/pcg/goals/{goal_id}/` | `PcgGoalPatchRequest` | `PcgGoalResponse` |
| DELETE | `/{id}/pages/pcg/goals/{goal_id}/` | none | 204 |
| POST | `/{id}/pages/pcg/goals/{goal_id}/targets/` | `PcgTargetCreateRequest` | `PcgTargetResponse`, 201 |
| PATCH | `/{id}/pages/pcg/goals/{goal_id}/targets/{target_id}/` | `PcgTargetPatchRequest` | `PcgTargetResponse` |
| DELETE | `/{id}/pages/pcg/goals/{goal_id}/targets/{target_id}/` | none | 204 |
| POST | `/{id}/pages/pcg/goals/{goal_id}/targets/{target_id}/stage-history/` | `PcgTargetStageCreateRequest` | `PcgTargetResponse`, 201 |
| PATCH | `/{id}/pages/pcg/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/` | `{ stage_date }` | `PcgTargetResponse` |
| DELETE | `/{id}/pages/pcg/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/` | none | 204 |

`PcgPageResponse` is `{ focus_area, available_goals: [{ id, label, prefix }], goals }`. A goal response adds `goal_name`, `prefix`, and `targets`. Measurement numbers are JSON numbers, not strings. `expected_mastery_date` is returned as stored. Stage create body is `{ stage, stage_date, reason or null }`.

### SAG

Same route shape as PCG under `/{id}/pages/sag/`, plus:

| Method | Path | Response |
| --- | --- | --- |
| GET | `/{id}/pages/sag/templates/` | `SagTemplatesResponse` |

`SagPageResponse` is `{ focus_areas, goals }`. Each goal includes `linked_brg_goals: [{ id, goal_name }]`. Those links are edited from BRG, not from SAG.

### BRG

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/brg/` | none | `BrgPageResponse` |
| GET | `/{id}/pages/brg/templates/` | none | `BrgTemplatesResponse` |
| POST | `/{id}/pages/brg/goals/` | `BrgGoalCreateRequest` | `BrgGoalResponse`, 201 |
| PATCH | `/{id}/pages/brg/goals/{goal_id}/` | `BrgGoalPatchRequest` | `BrgGoalResponse` |
| DELETE | `/{id}/pages/brg/goals/{goal_id}/` | none | 204 |
| POST | `/{id}/pages/brg/goals/{goal_id}/hypothesized-functions/` | `{ function_date, functions }` | `BrgGoalResponse`, 201 |
| DELETE | `/{id}/pages/brg/goals/{goal_id}/hypothesized-functions/{entry_id}/` | none | 204 |
| POST | `/{id}/pages/brg/goals/{goal_id}/targets/` | `BrgTargetCreateRequest` | `BrgTargetResponse`, 201 |
| PATCH | `/{id}/pages/brg/goals/{goal_id}/targets/{target_id}/` | `BrgTargetPatchRequest` | `BrgTargetResponse` |
| DELETE | `/{id}/pages/brg/goals/{goal_id}/targets/{target_id}/` | none | 204 |
| POST | `/{id}/pages/brg/goals/{goal_id}/targets/{target_id}/stage-history/` | stage create | `BrgTargetResponse`, 201 |
| PATCH | `/{id}/pages/brg/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/` | `{ stage_date }` | `BrgTargetResponse` |
| DELETE | `/{id}/pages/brg/goals/{goal_id}/targets/{target_id}/stage-history/{stage_id}/` | none | 204 |

`functions` is 1 to 4 unique hypothesized-function values. One SAG goal id can appear only once in `linked_sag_goal_ids`. `BrgPageResponse` includes `focus_areas`, `dsm5_symptoms`, `sag_goals`, and `goals`.

### Discharge

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/discharge/` | none | `DischargePageResponse` |
| PATCH | `/{id}/pages/discharge/` | `DischargeInfoPatch` | `DischargePageResponse` |
| POST | `/{id}/pages/discharge/reasons/` | `{ reason, explanation or null }` | `DischargeReasonResponse`, 201 |
| DELETE | `/{id}/pages/discharge/reasons/{reason_id}/` | none | 204 |

`reason` is required on create. The same reason cannot be stored twice on one discharge row.

### Treatment

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| GET | `/{id}/pages/treatment/` | none | `TreatmentPageResponse` |
| PATCH | `/{id}/pages/treatment/` | `TreatmentPatchRequest` | `TreatmentPageResponse` |

The response does not echo the hour columns one by one. It returns `services`, a map of service prefix to `{ hours, units, per }`. `units` is hours times 4. `therapy_provisioning_description` is derived and is not accepted on the PATCH. An empty page returns null editable fields and an empty service map. The provisioning sentence can still be present because it comes from the bay.
