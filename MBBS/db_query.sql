drop table mbbs_course;
CREATE TABLE mbbs_course (
    course_id TEXT,
    phase INT,
    course_name TEXT,
    topic_id TEXT,
    topic_name TEXT,
    content_id TEXT,
    content_name TEXT,
    learning_objectives TEXT,
    teaching_hours INT,
    items_per_topic INT,
    course_difficulty INT,
    card TEXT,
    item TEXT
);

CREATE TABLE area_of_interest (
    subject_interest TEXT,
    subject_interest_code TEXT,
    prerequisite_H TEXT,
    prerequisite_M TEXT,
    prerequisite_L TEXT
);

CREATE TABLE area_of_interest (
    subject_interest TEXT,
    subject_interest_code TEXT,
    prerequisite_H TEXT,
    prerequisite_M TEXT,
    prerequisite_L TEXT
);

CREATE TABLE marking_policy (
    course_id VARCHAR(10) PRIMARY KEY,
    item_total INT,
    card_written_total INT,
    card_viva_total INT,
    card_ospe_total INT,
    term_written_total INT,
    term_viva_total INT,
    term_ospe_total INT,
    prof_written_total INT,
    prof_viva_total INT,
    prof_ospe_total INT,
    ward_exam_total INT,
    prof_total INT,
    item_pass_pct DECIMAL(3,2),
    card_pass_pct DECIMAL(3,2),
    term_pass_pct DECIMAL(3,2),
    prof_pass_pct DECIMAL(3,2),
    weak_threshold_pct DECIMAL(3,2),
    strong_threshold_pct DECIMAL(3,2)
);

CREATE TABLE mbbs_student (
    student_id INT PRIMARY KEY,
    name VARCHAR(100),
    batch INT,
    phase INT,
    interest_1 VARCHAR(10),
    interest_2 VARCHAR(10),
    interest_3 VARCHAR(10)
);

CREATE TABLE mbbs_activity (
    student_id INT,
    course_id VARCHAR(10),
    phase INT,
    attendance_pct DECIMAL(5,2),
    logins_count INT,
    video_watched INT,
    chatbot_interactions INT,
    on_time_submission_rate DECIMAL(4,2),
    practice_quizzes INT
);

CREATE TABLE student_course_log (
    student_id INT,
    course VARCHAR(50),
    item1 DECIMAL(4,2),
    item1_topic VARCHAR(255),
    item1_hours INT,
    item2 DECIMAL(4,2),
    item2_topic VARCHAR(255),
    item2_hours INT,
    item3 DECIMAL(4,2),
    item3_topic VARCHAR(255),
    item3_hours INT,
    item4 DECIMAL(4,2),
    item4_topic VARCHAR(255),
    item4_hours INT,
    item5 DECIMAL(4,2),
    item5_topic VARCHAR(255),
    item5_hours INT,
    upc_item6_topic VARCHAR(255),
    upc_item6_hours INT,
    upc_item6_date DATE,
    upc_item7_topic VARCHAR(255),
    upc_item7_hours INT,
    upc_item7_date DATE,
    upc_item8_topic VARCHAR(255),
    upc_item8_hours INT,
    upc_item8_date DATE,
    upc_item9_topic VARCHAR(255),
    upc_item9_hours INT,
    upc_item9_date DATE,
    upc_item10_topic VARCHAR(255),
    upc_item10_hours INT,
    upc_item10_date DATE
);



