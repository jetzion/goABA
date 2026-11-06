"""Option lists from the spec."""

from enum import StrEnum


class Bay(StrEnum):
    """Plan bay."""

    BAY_2_5 = "2.5"
    BAY_2_6 = "2.6"
    BAY_2_7 = "2.7"
    BAY_3 = "3"
    BAY_6 = "6"
    BAY_7 = "7"


PAGES = [
    "information",
    "medical",
    "referral",
    "medication",
    "therapy",
    "education",
    "family",
    "child",
    "assessment",
    "crisis",
    "goals",
    "discharge",
    "treatment",
]


US_STATES = tuple(
    "AK AL AR AS AZ CA CO CT DC DE FL GA GU HI IA ID IL IN KS KY LA MA MD ME MI MN MO MP MS MT NC "
    "ND NE NH NJ NM NV NY OH OK OR PA PR RI SC SD TN TX UT VA VI VT WA WI WV WY".split()
)

# Medical

HEARING = (
    'Peripheral (Medical) Hearing Loss',
    'Auditory Processing Difficulties (APD-like features)',
    'Hyperacusis (Sound Sensitivity)',
    'Hypersensitivity to Specific Frequencies',
    'Auditory Filtering Difficulties',
    'Delayed Auditory Processing',
    'Fluctuating Hearing Issues',
    'Other hearing issues',
    'No hearing issues',
)

VISION = (
    'Refractive Errors (Common in All Children)',
    'Strabismus (Eye Alignment Problems)',
    'Amblyopia (“Lazy Eye”)',
    'Visual Processing Differences (Very Common in ASD)',
    'Visual Sensory Sensitivities',
    'Visual Attention & Scanning Differences',
    'Depth Perception & Binocular Vision Issues',
    'Ocular Motor Dysfunction',
    'Other vision issues',
    'No vision issues',
)

DIAGNOSES = (
    'Adjustment Disorder (F43.2)',
    'Anxiety (F41.9)',
    'Asperger’s syndrome (F84.5)',
    'Attention-deficit hyperactivity disorder (F90.0, F90.1, F90.2, F90.8, F90.9)',
    'Cerebral Palsy (G80.9)',
    'Cerebral Visual Impairment: (H47.61)',
    'Coffin-Siris Syndrome (Q87.1)',
    'Congenital Heart Failure: (Q24.9)',
    'Depression (F33.0, F33.2)',
    'Developmental disorder of speech and language, unspecified (F80.9)',
    'Disruptive mood dysregulation disorder (F34.81)',
    'Downs Syndrome (Q90.9)',
    'Emotional Disturbance Disorder (F98.9)',
    'Epilepsy: (G40.0)',
    'Generalized Anxiety Disorder (F41.1)',
    'Global Speech Delay (F80)',
    'Mild Intellectual Developmental Disorder (F70)',
    'Mixed Receptive-Expressive Language Disorder (F80.2)',
    'Obsessive Compulsive Disorder (F42)',
    'Oppositional Defiance Disorder (F91.3)',
    'Oral Aversion (F50.82)',
    'Other childhood disintegrative disorder (F84.3)',
    'Other pervasive developmental disorders (F84.8)',
    'Pediatric Feeding Disorder (R63.32)',
    'Pervasive developmental disorder, unspecified (F84.9)',
    'Post-Traumatic Stress Disorder (F43.12)',
    'Prader-Willi Syndrome (Q87.11)',
    'Rett’s syndrome (F84.2)',
    'Sensory Processing Disorder (F88)',
)

ASD_SEVERITY = ("Level-1", "Level-2", "Level-3", "Unknown")
DELIVERY_TYPES = ("Spontaneous", "C-Section", "Induced Vaginal", "Unknown")
MEDICAL_SELECTIONS = {
    "EARLY_INTERVENTION": (
        "Applied Behavior Analysis", "Feeding Therapy", "Speech Therapy", "Play Therapy",
        "Occupational Therapy", "Special Education Preschool", "Physical Therapy", "Other", "None",
    ),
    "PREGNANCY_ISSUE": (
        "Vaginal bleeding", "Rh incompatibility", "Emotional problems", "Infections", "Bed-rest",
        "Premature Labor", "Difficulty in conception", "Threatened miscarriage", "Excessive swelling",
        "Other virus", "Excessive nausea/vomiting", "Drug or Alcohol abuse", "Other", "None",
    ),
    "REGRESSION": ("Speech language", "Gross motor", "Fine motor", "None"),
}

DIAGNOSIS_TOOLS = (
    'ADOS-2 (Autism Diagnostic Observation Schedule)',
    'Autism Spectrum Rating Scales™ (ASRS®)',
    'AQ (Autism Spectrum Quotient)',
    'CARS-2 (Childhood Autism Rating Scale)',
    'GARS-2 (Gilliam Autism Rating Scale)',
    'M-CHAT-R/F (Modified Checklist for Autism in Toddlers)',
    'Parents’ Evaluation of Developmental Status (PEDS)',
    'SRS-2 (Social Responsiveness Scale)',
    'STAT (Screening Tool for Autism in Toddlers)',
    'Tele-ASD-Peds',
    'Other',
)

# Therapy

THERAPY_SERVICE_TYPES = (
    "Applied Behavior Analysis (ABA)",
    "Speech Therapy",
    "Occupational Therapy",
    "Physical Therapy",
    "Counseling Services",
    "Feeding Therapy",
    "Equestrian Therapy",
    "Other",
)
THERAPY_FREQUENCIES = ("Daily", "Weekly", "Semi-weekly", "Monthly", "Semi-monthly")
THERAPY_PROGRESS = ("Positive improvement", "No progress", "Unfavorable outcome")
RECORD_SHARED = ("Shared", "Will share")

# Education

EDUCATION_SETTINGS = ("In-person public/private", "Homeschool", "Remote")
EVALUATION_STATUSES = ("EVALUATED", "NOT_EVALUATED", "SCHEDULED_EVALUATION")
IEP_OR_504 = ("N/A", "IEP", "504")
CLASSROOM_SETTINGS = (
    'Speech-Language',
    'Occupational Therapy',
    'Physical Therapy',
    'Social Skill Groups',
    'Applied Behavior Analysis',
    '1:1 aide',
    'Additional time',
    'General education classroom',
    'Special education classroom',
    'Integrated general education services',
    'Other',
)
SCHOOL_ATTITUDES = (
    'Very Positive (Enthusiastic, Excited to Attend)',
    'Positive (Generally Enjoys School)',
    'Somewhat Positive',
    'Neutral (No Strong Feelings)',
    'Mixed (Varies Day-to-Day)',
    'Reluctant (Needs Encouragement)',
    'Somewhat Negative',
    'Negative (Avoidant/Dislikes School)',
    'Highly Negative (Refusal, Distress, Tantrums)',
    'Anxious (Separation Anxiety, Worry)',
)

# Family

MEMBER_ROLES = ("Parent and a caregiver", "Parent not a caregiver", "Caregiver")
CAREGIVER_TYPES = ("Primary caregiver", "Secondary caregiver")
CUSTODY_TYPES = ("Joint custody", "Full custody", "No custody")
MARITAL_STATUSES = ("Divorced", "Married", "Single", "Separated", "Widowed", "Domestic Partner / Civil Union")
SIBLING_RELATIONSHIPS = ("Brother", "Sister", "Twins", "Half-brother", "Half-sister", "Step-siblings", "Adoptive-siblings")
RELATIONSHIPS = (
    'Parent (Mother / Father)',
    'Stepparent',
    'Grandparent',
    'Aunt / Uncle',
    'Older sibling',
    'Cousin',
    'Legal guardian (court-appointed)',
    'Adoptive parent',
    'Foster parent',
    'Kinship caregiver (relative/friend)',
)
FAMILY_MEDICAL_HISTORY = (
    'ASD',
    'Other developmental disorders (e.g., intellectual disabilities, language disorders)',
    'Mood disorders (e.g., depression, bipolar disorder, anxiety disorders)',
    'ADHD',
    'Schizophrenia',
    'Alcohol or drug abuse',
    'Learning disabilities',
    'Anxiety, panic concerns',
    'Genetic syndromes associated with ASD (e.g., Fragile X syndrome, Rett syndrome)',
    'Other',
    'None',
)
COMMUNITY_SUPPORT = (
    'Church (or other religion organization)',
    'Community',
    'Extended family',
    'Friends',
    'Other',
    'None',
)
FAMILY_INFO_TYPES = {
    "MATERNAL_MEDICAL_HISTORY": FAMILY_MEDICAL_HISTORY,
    "PATERNAL_MEDICAL_HISTORY": FAMILY_MEDICAL_HISTORY,
    "COMMUNITY_SUPPORT": COMMUNITY_SUPPORT,
}

# Child

COMMUNICATION_STYLES = (
    'Verbal communication (single words, sentences, etc.)',
    'Speech device (AAC, tablet, etc.)',
    'Sign language',
    'Gestures (pointing, pulling, etc.)',
    'Picture-based communication (PECS, picture boards, etc.)',
    'No communication',
)
THERAPY_GOALS = (
    'Improve communication skills',
    'Reduce tantrums or meltdowns',
    'Help with following directions',
    'Support potty training',
    'Improve social skills (making friends, sharing, taking turns)',
    'Decrease concerning behaviors',
    'Improve attention and focus',
    'Help with transitions between activities',
    'Increase independence with daily living skills (dressing, brushing teeth, feeding)',
    'Support school readiness skills',
    'Improve play skills',
    'Reduce repetitive behaviors',
    'Improve safety skills (staying nearby, crossing streets safely)',
    'Support emotional regulation',
    'Help with sleep routines',
    'Support feeding or picky eating concerns',
    'General developmental support',
)
BEHAVIOR_ISSUES = (
    'Aggression (e.g., hitting, kicking, biting)',
    'Verbal aggression (e.g., threats, name-calling)',
    'Elopement (e.g., running from caregiver)',
    'Property destruction (e.g., breaking toys, household items)',
    'Task refusal (e.g., refusing instructions or tasks)',
    'Self-injury (e.g., hitting or pinching itself)',
    'Pica (Eating non-food items such as plastic, chalk, fabric, etc.)',
    'Disrobing (Removal of clothing in inappropriate settings, etc.)',
    'None',
)
CHILD_OPTION_TYPES = {
    "COMMUNICATION_STYLE": COMMUNICATION_STYLES,
    "GOALS_FOR_THERAPY": THERAPY_GOALS,
    "BEHAVIOR_ISSUE": BEHAVIOR_ISSUES,
}
CHILD_FREE_TEXT_TYPES = ("STRENGTH", "WEAKNESS", "INTEREST", "DISLIKES")
DAYS_OF_WEEK = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
SCHEDULE_ACTIVITIES = {
    "FORTA_THERAPY": "Available for Forta therapy",
    "SCHOOL": "School",
    "OTHER_THERAPY": "Other therapies",
    "OTHER_ACTIVITY": "Other activities",
}

# Assessment

ADDITIONAL_FILES = (
    'Previous assessment reports',
    'Previous intervention plans and treatment plans',
    'Reports by other providers',
    'School reports',
    'Medical reports',
    'Other',
)
DSM5_SYMPTOMS = (
    'Deficits in social-emotional reciprocity, ranging, for example, from abnormal social approach and failure of normal back-and-forth conversation; to reduced sharing of interests, emotions, or affect; to failure to initiate or respond to social interactions.',
    'Deficits in nonverbal communicative behaviors used for social interaction, ranging, for example, from poorly integrated verbal and nonverbal communication; to abnormalities in eye contact and body language or deficits in understanding and use of gestures; to a total lack of facial expressions and nonverbal communication.',
    'Deficits in developing, maintaining, and understanding relationships, ranging, for example, from difficulties adjusting behavior to suit various social contexts; to difficulties in sharing imaginative play or in making friends; to absences of interest in peers.',
    'Stereotyped or repetitive motor movements, use of objects, or speech (e.g., simple motor stereotypies, lining up toys or flipping objects, echolalia, idiosyncratic phrases).',
    'Insistence on sameness, inflexible adherence to routines, or ritualized patterns of verbal or nonverbal behavior (e.g., extreme distress at small changes, difficulties with transitions, rigid thinking patterns, greeting rituals, need to take same route or eat same food everyday).',
    'Highly restricted, fixated interests that are abnormal in intensity or focus (e.g., strong attachment to or preoccupation with unusual objects, excessively circumscribed or perseverative interest).',
    'Hyper- or hyporeactivity to sensory input or unusual interest in sensory aspects of the environment (e.g., apparent indifference to pain/temperature, adverse response to specific sounds or textures, excessive smelling or touching of objects, visual fascination with lights or movement).',
)
ASSESSMENT_TOOLS = (
    'VB-MAPP',
    'ABLLS-R',
    'AFLS',
    'FAST',
    'PDDBI',
    'PEAK',
    'QABF',
    'Socially Savvy',
    'Vineland-3',
    'ASAP',
    'OMNIA',
    'SSIS',
    'PSI',
)
BARRIERS = (
    'Family stress or caregiver burnout',
    'Transportation challenges',
    'Financial hardship',
    'Insurance coverage limitations',
    'Scheduling conflicts with school, work, or activities',
    'Limited understanding of ABA services',
    'Language or communication barriers',
    'Cultural beliefs impacting treatment acceptance',
    'Difficulty maintaining consistent routines at home',
    'Frequent cancellations or missed appointments',
    'Limited support system within the family',
    'Technology or internet access issues for telehealth',
    'Client illness or medical complications',
    'Medication changes affecting participation',
    'Sleep difficulties impacting engagement',
    'Sensory sensitivities interfering with sessions',
    'Challenging behaviors limiting participation in services',
    'Difficulty transitioning between settings or providers',
    'Caregiver mental health or personal stressors',
    'Lack of childcare for other children in the home',
    'Concerns about privacy or services in the home',
    'Limited motivation or readiness for change',
    'Communication deficits affecting expression of needs',
)
READINESS_LEVELS = ("Not ready", "Somewhat", "Ready")
READINESS_ITEMS = {
    'CHILD': {
        'attends_to_screen': 'Attends to screen ≥ 30 seconds',
        'follows_instructions': 'Follows telehealth instructions',
        'caregiver_mediation': 'Tolerates caregiver mediation',
        'no_severe_behavior': 'No severe SIB or aggression',
        'communicates_needs': 'Communicates basic needs',
        'reinforcers_available': 'Reinforcers available via caregiver/screen',
    },
    'CAREGIVER': {
        'available_during_sessions': 'Available during sessions',
        'implements_directions': 'Implements BCBA directions',
        'operates_tech': 'Operates tech independently',
        'manages_safety': 'Manages safety appropriately',
        'distraction_free_area': 'Prepares distraction-free area',
        'reinforcers_ready': 'Has reinforcers ready',
        'attends_reliably': 'Attends sessions reliably',
    },
    'ENVIRONMENT': {
        'stable_internet': 'Stable internet connection',
        'camera_audio': 'Functional camera & audio',
        'quiet_environment': 'Quiet environment',
        'lighting': 'Good lighting / visibility',
        'materials': 'Materials available',
        'confidential_space': 'Confidential space',
    },
}

# Crisis

FUNCTIONAL_BEHAVIORS = (
    "Escape-Maintained",
    "Attention-Maintained",
    "Tangible-Maintained",
    "Physical-Maintained",
    "Non-social or Sensory-Maintained",
)

# Discharge

DISCHARGE_REASONS = (
    'The client has mastered all treatment goals, and no new goals are identified',
    'All maladaptive behavior goals have been mastered and generalized',
    'No new behaviors have emerged',
    'Client’s Vineland-3 scores have reached a level in accordance with similar-aged peers',
    'Client’s AFLS scores have reached a level in accordance with similar-aged peers',
    'Client’s parents/caregivers report confidence in continuing ABA intervention techniques',
    'Client no longer able to participate due to medical reasons',
    'Parents prefer a new provider',
    'Client no longer able to participate due to personal changes',
    'No progress has been made for 3 months',
    'Goals are not maintaining or generalizing',
    'Other',
)

# Treatment

SERVICE_PER = ("Weekly", "bi-weekly", "Monthly", "6-months authorization period")
SERVICES = {
    "assessment_97151": "97151 Assessment",
    "assessment_97152": "97152 Assisting Assessment",
    "direct_therapy_97153": "97153 Direct ABA Technician 1:1",
    "protocol_modification_97155": "97155 Protocol Modification by BCBA",
    "parent_training_97156": "97156 Parent Training/Caregiver Support",
    "group_parent_training_97157": "97157 Group Parent Training (2–8 parents in a group setting)",
    "care_coordination_99366": "99366 Care Coordination",
}

# Goals

DATA_COLLECTION_METHODS = ("Duration", "Instances", "Percentage", "Rate")
MASTERY_DIRECTIONS = ("increase", "decrease")
DURATION_AGGREGATIONS = ("average", "total")
MEASUREMENT_UNITS = ("Seconds", "Minutes", "Hours")
TARGET_TIMEFRAMES = ("Short-Term", "Intermediate-Term", "Long-Term")
GOAL_FREQUENCIES = ("Twice a week", "Once a week", "Bi monthly", "Monthly")
HYPOTHESIZED_FUNCTIONS = ("Sensory", "Escape/avoidance", "Attention", "Tangible")
PARENT_TRAINING = "Parent training"
BEHAVIOR_CHANGE = "Behavior change"
