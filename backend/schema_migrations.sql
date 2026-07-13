BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_employee_management

CREATE TABLE organizations (
    org_id SERIAL NOT NULL, 
    org_code VARCHAR(20) NOT NULL, 
    org_name VARCHAR(200) NOT NULL, 
    contact_phone VARCHAR(20), 
    contact_email VARCHAR(150), 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_organizations PRIMARY KEY (org_id), 
    CONSTRAINT uq_organizations_org_code UNIQUE (org_code)
);

CREATE TABLE branches (
    branch_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    branch_name VARCHAR(200) NOT NULL, 
    logo_url TEXT, 
    gstin VARCHAR(20), 
    mobile_number VARCHAR(20), 
    address TEXT, 
    landmark VARCHAR(200), 
    pin_code VARCHAR(10), 
    city VARCHAR(100), 
    state VARCHAR(100), 
    country VARCHAR(100), 
    industry_type VARCHAR(100), 
    latitude NUMERIC(10, 7), 
    longitude NUMERIC(10, 7), 
    allowed_radius_meters SMALLINT, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_branches PRIMARY KEY (branch_id), 
    CONSTRAINT fk_branches_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id)
);

CREATE TABLE departments (
    dept_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    dept_name VARCHAR(150) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_departments PRIMARY KEY (dept_id), 
    CONSTRAINT fk_departments_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id)
);

CREATE UNIQUE INDEX uq_departments_org_id_dept_name ON departments (org_id, dept_name) WHERE is_deleted = false;

CREATE TABLE designations (
    designation_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    designation_name VARCHAR(150) NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_designations PRIMARY KEY (designation_id), 
    CONSTRAINT fk_designations_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id)
);

CREATE UNIQUE INDEX uq_designations_org_id_designation_name ON designations (org_id, designation_name) WHERE is_deleted = false;

CREATE TABLE employees (
    employee_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_code VARCHAR(30) NOT NULL, 
    employee_uid VARCHAR(50), 
    employee_name VARCHAR(200) NOT NULL, 
    display_name VARCHAR(200), 
    mobile_country_code VARCHAR(5) DEFAULT '+91' NOT NULL, 
    mobile_number VARCHAR(20) NOT NULL, 
    email VARCHAR(200), 
    gender VARCHAR(10) NOT NULL, 
    master_branch_id INTEGER NOT NULL, 
    dept_id INTEGER NOT NULL, 
    designation_id INTEGER NOT NULL, 
    employee_type VARCHAR(30), 
    door_lock_permission BOOLEAN DEFAULT false NOT NULL, 
    pf_account_number VARCHAR(50), 
    uan_number VARCHAR(12), 
    esic_ip_number VARCHAR(10), 
    address TEXT, 
    date_of_joining DATE, 
    salary_type VARCHAR(20), 
    monthly_salary NUMERIC(12, 2) DEFAULT 0, 
    payroll_group_id INTEGER, 
    date_of_birth DATE, 
    date_of_leaving DATE, 
    employment_status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    profile_photo_url TEXT, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employees PRIMARY KEY (employee_id), 
    CONSTRAINT fk_employees_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_employees_master_branch_id_branches FOREIGN KEY(master_branch_id) REFERENCES branches (branch_id), 
    CONSTRAINT fk_employees_dept_id_departments FOREIGN KEY(dept_id) REFERENCES departments (dept_id), 
    CONSTRAINT fk_employees_designation_id_designations FOREIGN KEY(designation_id) REFERENCES designations (designation_id), 
    CONSTRAINT ck_employees_ck_employees_employment_status CHECK (employment_status IN ('active', 'inactive', 'terminated')), 
    CONSTRAINT ck_employees_ck_employees_gender CHECK (gender IN ('Male', 'Female', 'Other')), 
    CONSTRAINT ck_employees_ck_employees_salary_type CHECK (salary_type IN ('Monthly', 'Hourly', 'Compliance'))
);

CREATE UNIQUE INDEX uq_employees_org_id_employee_code ON employees (org_id, employee_code) WHERE is_deleted = false;

CREATE TABLE employee_bank_details (
    bank_detail_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    bank_name VARCHAR(150), 
    bank_branch_name VARCHAR(150), 
    account_number VARCHAR(30), 
    ifsc_code VARCHAR(15), 
    is_primary BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_bank_details PRIMARY KEY (bank_detail_id), 
    CONSTRAINT fk_employee_bank_details_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id)
);

CREATE TABLE employee_documents (
    document_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    document_type VARCHAR(50) NOT NULL, 
    file_url TEXT NOT NULL, 
    original_filename VARCHAR(255), 
    file_size_bytes INTEGER, 
    uploaded_by INTEGER, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_documents PRIMARY KEY (document_id), 
    CONSTRAINT fk_employee_documents_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT ck_employee_documents_ck_employee_documents_document_type CHECK (document_type IN ('aadhar_card', 'driving_licence', 'pan_card', 'passport_photo', 'other'))
);

CREATE TABLE employee_emergency_contacts (
    emergency_contact_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    contact_country_code VARCHAR(5) DEFAULT '+91' NOT NULL, 
    contact_number VARCHAR(20) NOT NULL, 
    contact_person_name VARCHAR(200) NOT NULL, 
    relation VARCHAR(100), 
    address TEXT, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_emergency_contacts PRIMARY KEY (emergency_contact_id), 
    CONSTRAINT fk_employee_emergency_contacts_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id)
);

CREATE TABLE employee_references (
    reference_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    reference_name VARCHAR(200) NOT NULL, 
    reference_country_code VARCHAR(5) DEFAULT '+91' NOT NULL, 
    reference_contact_number VARCHAR(20) NOT NULL, 
    sort_order SMALLINT DEFAULT 1 NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_references PRIMARY KEY (reference_id), 
    CONSTRAINT fk_employee_references_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id)
);

CREATE TABLE employee_biometrics (
    biometric_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    device_id INTEGER NOT NULL, 
    biometric_type VARCHAR(30) DEFAULT 'fingerprint' NOT NULL, 
    biometric_template TEXT, 
    registered_at TIMESTAMP WITH TIME ZONE, 
    registered_by INTEGER, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_biometrics PRIMARY KEY (biometric_id), 
    CONSTRAINT fk_employee_biometrics_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id)
);

CREATE UNIQUE INDEX uq_employee_biometrics_employee_id_device_id_biometric_type ON employee_biometrics (employee_id, device_id, biometric_type) WHERE is_deleted = false;

CREATE TABLE employee_punch_branches (
    punch_branch_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    branch_id INTEGER NOT NULL, 
    assigned_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_punch_branches PRIMARY KEY (punch_branch_id), 
    CONSTRAINT fk_employee_punch_branches_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_employee_punch_branches_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id), 
    CONSTRAINT uq_employee_punch_branches_employee_id_branch_id UNIQUE (employee_id, branch_id)
);

CREATE TABLE employee_attendance_permissions (
    att_perm_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    attendance_method VARCHAR(20) DEFAULT 'hardware_device' NOT NULL, 
    mobile_attendance_enabled BOOLEAN DEFAULT false NOT NULL, 
    geofencing_enabled BOOLEAN DEFAULT false NOT NULL, 
    auto_punch_out_enabled BOOLEAN DEFAULT false NOT NULL, 
    updated_by INTEGER, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_attendance_permissions PRIMARY KEY (att_perm_id), 
    CONSTRAINT fk_employee_attendance_permissions_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT uq_employee_attendance_permissions_employee_id UNIQUE (employee_id), 
    CONSTRAINT ck_employee_attendance_permissions_ck_employee_attendan_2637 CHECK (attendance_method IN ('hardware_device', 'mobile_app', 'both'))
);

CREATE TABLE org_attendance_settings (
    setting_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    branch_id INTEGER, 
    device_id INTEGER, 
    mobile_attendance_enabled BOOLEAN DEFAULT false NOT NULL, 
    geofencing_enabled BOOLEAN DEFAULT false NOT NULL, 
    auto_punch_out_enabled BOOLEAN DEFAULT false NOT NULL, 
    biometric_attempt_count SMALLINT DEFAULT 7 NOT NULL, 
    updated_by INTEGER, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_org_attendance_settings PRIMARY KEY (setting_id), 
    CONSTRAINT fk_org_attendance_settings_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_org_attendance_settings_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id), 
    CONSTRAINT uq_org_attendance_settings_org_id_branch_id_device_id UNIQUE (org_id, branch_id, device_id)
);

CREATE TABLE employee_import_logs (
    import_log_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    import_type VARCHAR(30) DEFAULT 'create' NOT NULL, 
    file_url TEXT, 
    original_filename VARCHAR(255), 
    total_rows INTEGER, 
    success_rows INTEGER, 
    failed_rows INTEGER, 
    error_details JSONB, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    initiated_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_employee_import_logs PRIMARY KEY (import_log_id), 
    CONSTRAINT fk_employee_import_logs_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT ck_employee_import_logs_ck_employee_import_logs_status CHECK (status IN ('pending', 'processing', 'completed', 'failed')), 
    CONSTRAINT ck_employee_import_logs_ck_employee_import_logs_import_type CHECK (import_type IN ('create', 'update'))
);

CREATE TABLE employee_tags (
    tag_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    tag_label VARCHAR(100) NOT NULL, 
    tag_color VARCHAR(10), 
    is_status_tag BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_tags PRIMARY KEY (tag_id), 
    CONSTRAINT fk_employee_tags_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id)
);

CREATE TABLE employee_status_history (
    status_history_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    previous_status VARCHAR(20), 
    new_status VARCHAR(20) NOT NULL, 
    changed_by INTEGER, 
    reason TEXT, 
    effective_date DATE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_status_history PRIMARY KEY (status_history_id), 
    CONSTRAINT fk_employee_status_history_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT ck_employee_status_history_ck_employee_status_history_n_7631 CHECK (new_status IN ('active', 'inactive', 'terminated'))
);

INSERT INTO alembic_version (version_num) VALUES ('0001_employee_management') RETURNING alembic_version.version_num;

-- Running upgrade 0001_employee_management -> 0002_shift_management

CREATE TABLE shifts (
    shift_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    shift_name VARCHAR(150) NOT NULL, 
    shift_type VARCHAR(20) DEFAULT 'fixed' NOT NULL, 
    is_open_shift BOOLEAN DEFAULT false NOT NULL, 
    is_default BOOLEAN DEFAULT false NOT NULL, 
    is_uniform_time BOOLEAN DEFAULT true NOT NULL, 
    has_break_time BOOLEAN DEFAULT false NOT NULL, 
    shift_color VARCHAR(30), 
    remark TEXT, 
    is_advanced_mode BOOLEAN DEFAULT false NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_shifts PRIMARY KEY (shift_id), 
    CONSTRAINT fk_shifts_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT ck_shifts_ck_shifts_shift_type CHECK (shift_type IN ('fixed', 'open'))
);

CREATE UNIQUE INDEX uq_shifts_org_id_shift_name ON shifts (org_id, shift_name) WHERE is_deleted = false;

CREATE TABLE shift_day_timings (
    timing_id SERIAL NOT NULL, 
    shift_id INTEGER NOT NULL, 
    day_of_week SMALLINT, 
    start_time TIME WITHOUT TIME ZONE, 
    end_time TIME WITHOUT TIME ZONE, 
    break_start_time TIME WITHOUT TIME ZONE, 
    break_end_time TIME WITHOUT TIME ZONE, 
    duration_minutes INTEGER, 
    is_working_day BOOLEAN DEFAULT true NOT NULL, 
    CONSTRAINT pk_shift_day_timings PRIMARY KEY (timing_id), 
    CONSTRAINT fk_shift_day_timings_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id), 
    CONSTRAINT uq_shift_day_timings_shift_id_day_of_week UNIQUE (shift_id, day_of_week)
);

CREATE TABLE shift_assignments (
    assignment_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_id INTEGER NOT NULL, 
    shift_id INTEGER NOT NULL, 
    effective_from DATE NOT NULL, 
    effective_to DATE, 
    assigned_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_shift_assignments PRIMARY KEY (assignment_id), 
    CONSTRAINT fk_shift_assignments_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_shift_assignments_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_shift_assignments_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id)
);

CREATE INDEX ix_shift_assignments_employee_id_effective_from_effective_to ON shift_assignments (employee_id, effective_from, effective_to);

CREATE TABLE employee_weekoffs (
    weekoff_id SERIAL NOT NULL, 
    employee_id INTEGER NOT NULL, 
    day_of_week SMALLINT NOT NULL, 
    weekoff_type VARCHAR(20) DEFAULT 'working' NOT NULL, 
    occurrence_1st BOOLEAN DEFAULT true NOT NULL, 
    occurrence_2nd BOOLEAN DEFAULT true NOT NULL, 
    occurrence_3rd BOOLEAN DEFAULT true NOT NULL, 
    occurrence_4th BOOLEAN DEFAULT true NOT NULL, 
    occurrence_5th BOOLEAN DEFAULT true NOT NULL, 
    effective_from DATE, 
    effective_to DATE, 
    updated_by INTEGER, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_weekoffs PRIMARY KEY (weekoff_id), 
    CONSTRAINT fk_employee_weekoffs_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT ck_employee_weekoffs_ck_employee_weekoffs_day_of_week CHECK (day_of_week BETWEEN 0 AND 6), 
    CONSTRAINT ck_employee_weekoffs_ck_employee_weekoffs_weekoff_type CHECK (weekoff_type IN ('working', 'week_off', 'occasional_week_off'))
);

CREATE UNIQUE INDEX uq_employee_weekoffs_employee_id_day_of_week ON employee_weekoffs (employee_id, day_of_week) WHERE effective_to IS NULL;

CREATE TABLE roster (
    roster_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_id INTEGER NOT NULL, 
    roster_date DATE NOT NULL, 
    shift_id INTEGER, 
    is_week_off BOOLEAN DEFAULT false NOT NULL, 
    created_by INTEGER, 
    updated_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_roster PRIMARY KEY (roster_id), 
    CONSTRAINT fk_roster_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_roster_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_roster_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id), 
    CONSTRAINT uq_roster_employee_id_roster_date UNIQUE (employee_id, roster_date)
);

CREATE INDEX ix_roster_org_id_roster_date ON roster (org_id, roster_date);

CREATE TABLE working_hours_config (
    config_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    working_hours_mode VARCHAR(20) DEFAULT 'fixed' NOT NULL, 
    full_day_hours TIME WITHOUT TIME ZONE DEFAULT '08:00', 
    half_day_hours TIME WITHOUT TIME ZONE DEFAULT '04:00', 
    full_day_buffer_period TIME WITHOUT TIME ZONE DEFAULT '00:00', 
    half_day_buffer_period TIME WITHOUT TIME ZONE DEFAULT '00:00', 
    attendance_mode VARCHAR(40) DEFAULT 'consider_all_punch' NOT NULL, 
    effective_from DATE NOT NULL, 
    created_by INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_working_hours_config PRIMARY KEY (config_id), 
    CONSTRAINT fk_working_hours_config_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT ck_working_hours_config_ck_working_hours_config_working_a01c CHECK (working_hours_mode IN ('fixed', 'shift_wise')), 
    CONSTRAINT ck_working_hours_config_ck_working_hours_config_attendance_mode CHECK (attendance_mode IN ('consider_all_punch', 'first_and_last_punch_only', 'full_day_on_single_punch', 'default_full_day'))
);

CREATE TABLE working_hours_config_history (
    history_id SERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    config_id INTEGER NOT NULL, 
    working_hours_mode VARCHAR(20) NOT NULL, 
    full_day_hours TIME WITHOUT TIME ZONE, 
    half_day_hours TIME WITHOUT TIME ZONE, 
    full_day_buffer_period TIME WITHOUT TIME ZONE, 
    half_day_buffer_period TIME WITHOUT TIME ZONE, 
    attendance_mode VARCHAR(40) NOT NULL, 
    effective_from DATE NOT NULL, 
    effective_to DATE NOT NULL, 
    changed_by INTEGER, 
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_working_hours_config_history PRIMARY KEY (history_id), 
    CONSTRAINT fk_working_hours_config_history_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_working_hours_config_history_config_id_working_hours_config FOREIGN KEY(config_id) REFERENCES working_hours_config (config_id), 
    CONSTRAINT ck_working_hours_config_history_ck_working_hours_config_4eb4 CHECK (working_hours_mode IN ('fixed', 'shift_wise')), 
    CONSTRAINT ck_working_hours_config_history_ck_working_hours_config_75c8 CHECK (attendance_mode IN ('consider_all_punch', 'first_and_last_punch_only', 'full_day_on_single_punch', 'default_full_day'))
);

UPDATE alembic_version SET version_num='0002_shift_management' WHERE alembic_version.version_num = '0001_employee_management';

-- Running upgrade 0002_shift_management -> 0003_leave_holiday_management

CREATE TABLE leave_settings (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    leave_cycle VARCHAR(20) DEFAULT 'calendar_year' NOT NULL, 
    cycle_start_month SMALLINT DEFAULT 1 NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    CONSTRAINT pk_leave_settings PRIMARY KEY (id), 
    CONSTRAINT uq_leave_settings_org_id UNIQUE (org_id)
);

CREATE TABLE leave_types (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    alias VARCHAR(50) NOT NULL, 
    description TEXT, 
    auto_allocation_count NUMERIC(6, 2) NOT NULL, 
    allocation_frequency VARCHAR(20) DEFAULT 'monthly' NOT NULL, 
    carry_forward_count NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    carry_forward_frequency VARCHAR(20) DEFAULT 'monthly' NOT NULL, 
    encashment_enabled BOOLEAN DEFAULT false NOT NULL, 
    encashment_limit NUMERIC(6, 2), 
    encashment_frequency VARCHAR(20), 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    CONSTRAINT pk_leave_types PRIMARY KEY (id), 
    CONSTRAINT uq_leave_types_org_id_alias UNIQUE (org_id, alias), 
    CONSTRAINT ck_leave_types_ck_leave_types_allocation_frequency CHECK (allocation_frequency IN ('monthly', 'yearly')), 
    CONSTRAINT ck_leave_types_ck_leave_types_carry_forward_frequency CHECK (carry_forward_frequency IN ('monthly', 'yearly')), 
    CONSTRAINT ck_leave_types_ck_leave_types_encashment_frequency CHECK (encashment_frequency IN ('monthly', 'yearly')), 
    CONSTRAINT ck_leave_types_ck_leave_types_encashment_limit_required CHECK (NOT encashment_enabled OR encashment_limit IS NOT NULL)
);

CREATE TABLE employee_leave_allocations (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    leave_type_id BIGINT NOT NULL, 
    cycle_year SMALLINT NOT NULL, 
    cycle_period VARCHAR(20), 
    allocated_days NUMERIC(6, 2) NOT NULL, 
    allocation_date DATE NOT NULL, 
    allocation_source VARCHAR(20) DEFAULT 'auto' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    CONSTRAINT pk_employee_leave_allocations PRIMARY KEY (id), 
    CONSTRAINT fk_employee_leave_allocations_leave_type_id_leave_types FOREIGN KEY(leave_type_id) REFERENCES leave_types (id), 
    CONSTRAINT uq_emp_leave_alloc_employee_type_cycle_year_period UNIQUE (employee_id, leave_type_id, cycle_year, cycle_period)
);

CREATE TABLE employee_leave_balances (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    leave_type_id BIGINT NOT NULL, 
    cycle_year SMALLINT NOT NULL, 
    opening_balance NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    allocated NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    used NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    carried_forward NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    encashed NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    adjusted NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    closing_balance NUMERIC(6, 2) DEFAULT 0 NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_by BIGINT, 
    CONSTRAINT pk_employee_leave_balances PRIMARY KEY (id), 
    CONSTRAINT fk_employee_leave_balances_leave_type_id_leave_types FOREIGN KEY(leave_type_id) REFERENCES leave_types (id), 
    CONSTRAINT uq_employee_leave_balances_employee_id_leave_type_id_cycle_year UNIQUE (employee_id, leave_type_id, cycle_year)
);

CREATE TABLE leave_balance_adjustments (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    leave_type_id BIGINT NOT NULL, 
    adjustment_type VARCHAR(20) NOT NULL, 
    delta NUMERIC(6, 2) NOT NULL, 
    new_balance NUMERIC(6, 2) NOT NULL, 
    remarks TEXT, 
    cycle_year SMALLINT NOT NULL, 
    adjusted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    adjusted_by BIGINT NOT NULL, 
    CONSTRAINT pk_leave_balance_adjustments PRIMARY KEY (id), 
    CONSTRAINT fk_leave_balance_adjustments_leave_type_id_leave_types FOREIGN KEY(leave_type_id) REFERENCES leave_types (id)
);

CREATE INDEX ix_leave_balance_adjustments_employee_id_cycle_year ON leave_balance_adjustments (employee_id, cycle_year);

CREATE TABLE holiday_templates (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    holiday_count SMALLINT DEFAULT 0 NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    CONSTRAINT pk_holiday_templates PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_holiday_templates_org_id_name ON holiday_templates (org_id, name) WHERE is_deleted = false;

CREATE TABLE holiday_template_items (
    id BIGSERIAL NOT NULL, 
    template_id BIGINT NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    day_of_week VARCHAR(15), 
    duration_days SMALLINT DEFAULT 1 NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    CONSTRAINT pk_holiday_template_items PRIMARY KEY (id), 
    CONSTRAINT fk_holiday_template_items_template_id_holiday_templates FOREIGN KEY(template_id) REFERENCES holiday_templates (id), 
    CONSTRAINT ck_holiday_template_items_ck_holiday_template_items_end_d934 CHECK (end_date >= start_date)
);

CREATE INDEX ix_holiday_template_items_template_id_start_date ON holiday_template_items (template_id, start_date);

CREATE TABLE employee_holiday_assignments (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    template_id BIGINT, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    assigned_by BIGINT NOT NULL, 
    previous_template_id BIGINT, 
    CONSTRAINT pk_employee_holiday_assignments PRIMARY KEY (id), 
    CONSTRAINT fk_employee_holiday_assignments_template_id_holiday_templates FOREIGN KEY(template_id) REFERENCES holiday_templates (id), 
    CONSTRAINT fk_emp_holiday_assign_prev_template_id_holiday_templates FOREIGN KEY(previous_template_id) REFERENCES holiday_templates (id), 
    CONSTRAINT uq_employee_holiday_assignments_employee_id UNIQUE (employee_id)
);

CREATE TABLE leave_requests (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    leave_type_id BIGINT NOT NULL, 
    start_date DATE NOT NULL, 
    end_date DATE NOT NULL, 
    duration_days NUMERIC(4, 1) NOT NULL, 
    reason TEXT, 
    status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    applied_on TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    reviewed_at TIMESTAMP WITH TIME ZONE, 
    reviewed_by BIGINT, 
    rejection_reason TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_leave_requests PRIMARY KEY (id), 
    CONSTRAINT fk_leave_requests_leave_type_id_leave_types FOREIGN KEY(leave_type_id) REFERENCES leave_types (id), 
    CONSTRAINT ck_leave_requests_ck_leave_requests_status CHECK (status IN ('pending', 'approved', 'rejected')), 
    CONSTRAINT ck_leave_requests_ck_leave_requests_end_date_after_start_date CHECK (end_date >= start_date)
);

CREATE INDEX ix_leave_requests_employee_id_status ON leave_requests (employee_id, status);

CREATE INDEX ix_leave_requests_leave_type_id_status ON leave_requests (leave_type_id, status);

UPDATE alembic_version SET version_num='0003_leave_holiday_management' WHERE alembic_version.version_num = '0002_shift_management';

-- Running upgrade 0003_leave_holiday_management -> 0004_approval_requests

CREATE TABLE approval_requests (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    request_type VARCHAR(20) NOT NULL, 
    request_subtype VARCHAR(50), 
    reference_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    status VARCHAR(10) DEFAULT 'pending' NOT NULL, 
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    reviewed_at TIMESTAMP WITH TIME ZONE, 
    reviewed_by BIGINT, 
    reject_remarks TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_approval_requests PRIMARY KEY (id), 
    CONSTRAINT ck_approval_requests_ck_approval_requests_request_type CHECK (request_type IN ('attendance', 'leave', 'login_reset')), 
    CONSTRAINT ck_approval_requests_ck_approval_requests_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX ix_approval_requests_org_id_status ON approval_requests (org_id, status);

CREATE INDEX ix_approval_requests_org_id_status_request_type ON approval_requests (org_id, status, request_type);

CREATE INDEX ix_approval_requests_employee_id_status ON approval_requests (employee_id, status);

CREATE TABLE attendance_regularization_requests (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_date DATE NOT NULL, 
    old_punch_time VARCHAR(20), 
    new_punch_time VARCHAR(20) NOT NULL, 
    employee_reason TEXT, 
    applied_on TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    status VARCHAR(10) DEFAULT 'pending' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_attendance_regularization_requests PRIMARY KEY (id), 
    CONSTRAINT ck_attendance_regularization_requests_ck_attendance_reg_8248 CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX ix_att_regularization_reqs_employee_id_attendance_date ON attendance_regularization_requests (employee_id, attendance_date);

CREATE INDEX ix_attendance_regularization_requests_status ON attendance_regularization_requests (status);

CREATE TABLE login_reset_requests (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    request_subtype VARCHAR(50), 
    request_description VARCHAR(255) DEFAULT 'Login Reset Request' NOT NULL, 
    status VARCHAR(10) DEFAULT 'pending' NOT NULL, 
    applied_on TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    reviewed_at TIMESTAMP WITH TIME ZONE, 
    reviewed_by BIGINT, 
    reject_remarks TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_login_reset_requests PRIMARY KEY (id), 
    CONSTRAINT ck_login_reset_requests_ck_login_reset_requests_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

CREATE INDEX ix_login_reset_requests_employee_id_status ON login_reset_requests (employee_id, status);

UPDATE alembic_version SET version_num='0004_approval_requests' WHERE alembic_version.version_num = '0003_leave_holiday_management';

-- Running upgrade 0004_approval_requests -> 0005_payroll

CREATE TABLE payroll_settings (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    working_hour_type VARCHAR(20) DEFAULT 'fixed' NOT NULL, 
    full_day_working_hours TIME WITHOUT TIME ZONE DEFAULT '08:00' NOT NULL, 
    half_day_working_hours TIME WITHOUT TIME ZONE DEFAULT '04:00' NOT NULL, 
    attendance_mode VARCHAR(30) DEFAULT 'consider_all_punch' NOT NULL, 
    off_day_compensation VARCHAR(30) DEFAULT 'monetary_compensation' NOT NULL, 
    off_day_wage_multiplier NUMERIC(4, 2) DEFAULT 1.00 NOT NULL, 
    daily_wage_formula VARCHAR(50) DEFAULT 'monthly_calendar_days' NOT NULL, 
    overtime_type VARCHAR(30) DEFAULT 'fixed_per_hour_pay' NOT NULL, 
    overtime_hourly_multiplier NUMERIC(4, 2) DEFAULT 0.00 NOT NULL, 
    overtime_buffer_period TIME WITHOUT TIME ZONE DEFAULT '00:00' NOT NULL, 
    overtime_period_interval VARCHAR(10) DEFAULT '15 Min', 
    full_day_penalty_enabled BOOLEAN DEFAULT false NOT NULL, 
    half_day_penalty_enabled BOOLEAN DEFAULT false NOT NULL, 
    late_coming_penalty_enabled BOOLEAN DEFAULT false NOT NULL, 
    grace_time TIME WITHOUT TIME ZONE DEFAULT '00:00' NOT NULL, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_payroll_settings PRIMARY KEY (id), 
    CONSTRAINT uq_payroll_settings_org_id UNIQUE (org_id)
);

CREATE TABLE payroll_groups (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    payroll_type VARCHAR(30) NOT NULL, 
    is_default BOOLEAN DEFAULT false NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    CONSTRAINT pk_payroll_groups PRIMARY KEY (id), 
    CONSTRAINT ck_payroll_groups_ck_payroll_groups_payroll_type CHECK (payroll_type IN ('monthly_without_compliance', 'monthly_with_compliance', 'hourly_payroll'))
);

CREATE UNIQUE INDEX uq_payroll_groups_org_id_name ON payroll_groups (org_id, name) WHERE is_deleted = false;

CREATE TABLE employee_payroll_group_assignments (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    payroll_group_id BIGINT NOT NULL, 
    salary_type VARCHAR(20) DEFAULT 'monthly' NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    assigned_by BIGINT NOT NULL, 
    previous_group_id BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_payroll_group_assignments PRIMARY KEY (id), 
    CONSTRAINT fk_emp_payroll_grp_assign_payroll_group_id_payroll_groups FOREIGN KEY(payroll_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT fk_emp_payroll_grp_assign_previous_group_id_payroll_groups FOREIGN KEY(previous_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT uq_employee_payroll_group_assignments_employee_id UNIQUE (employee_id), 
    CONSTRAINT ck_employee_payroll_group_assignments_ck_employee_payro_59db CHECK (salary_type IN ('monthly', 'hourly'))
);

CREATE TABLE payroll_salary_cycles (
    id BIGSERIAL NOT NULL, 
    payroll_group_id BIGINT NOT NULL, 
    cycle_date DATE NOT NULL, 
    is_finalized BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    CONSTRAINT pk_payroll_salary_cycles PRIMARY KEY (id), 
    CONSTRAINT fk_payroll_salary_cycles_payroll_group_id_payroll_groups FOREIGN KEY(payroll_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT uq_payroll_salary_cycles_payroll_group_id_cycle_date UNIQUE (payroll_group_id, cycle_date)
);

CREATE TABLE attendance_adjustments (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_date DATE NOT NULL, 
    original_status VARCHAR(5), 
    adjusted_status VARCHAR(5) NOT NULL, 
    is_forced_overwrite BOOLEAN DEFAULT false NOT NULL, 
    has_punch_error BOOLEAN DEFAULT false NOT NULL, 
    adjustment_source VARCHAR(20) DEFAULT 'spreadsheet' NOT NULL, 
    adjusted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    adjusted_by BIGINT NOT NULL, 
    CONSTRAINT pk_attendance_adjustments PRIMARY KEY (id), 
    CONSTRAINT uq_attendance_adjustments_employee_id_attendance_date UNIQUE (employee_id, attendance_date), 
    CONSTRAINT ck_attendance_adjustments_ck_attendance_adjustments_adj_c72a CHECK (adjusted_status IN ('FD', 'HD', 'A', 'WO', 'LWP'))
);

CREATE INDEX ix_attendance_adjustments_org_id_attendance_date ON attendance_adjustments (org_id, attendance_date);

CREATE INDEX ix_attendance_adjustments_employee_id_attendance_date ON attendance_adjustments (employee_id, attendance_date);

CREATE TABLE attendance_adjustment_penalties (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_date DATE NOT NULL, 
    penalty_amount NUMERIC(10, 2) NOT NULL, 
    remark TEXT, 
    is_removed BOOLEAN DEFAULT false NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_attendance_adjustment_penalties PRIMARY KEY (id)
);

CREATE INDEX ix_attendance_adjustment_penalties_employee_id_attendance_date ON attendance_adjustment_penalties (employee_id, attendance_date);

CREATE TABLE attendance_adjustment_extra_hours (
    id BIGSERIAL NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_date DATE NOT NULL, 
    extra_hours NUMERIC(5, 2) NOT NULL, 
    remark TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT NOT NULL, 
    CONSTRAINT pk_attendance_adjustment_extra_hours PRIMARY KEY (id), 
    CONSTRAINT uq_att_adjust_extra_hours_employee_id_attendance_date UNIQUE (employee_id, attendance_date)
);

CREATE TABLE payroll_column_settings (
    id BIGSERIAL NOT NULL, 
    payroll_group_id BIGINT NOT NULL, 
    column_key VARCHAR(50) NOT NULL, 
    column_label VARCHAR(100) NOT NULL, 
    is_visible BOOLEAN DEFAULT true NOT NULL, 
    display_order SMALLINT NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_by BIGINT, 
    CONSTRAINT pk_payroll_column_settings PRIMARY KEY (id), 
    CONSTRAINT fk_payroll_column_settings_payroll_group_id_payroll_groups FOREIGN KEY(payroll_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT uq_payroll_column_settings_payroll_group_id_column_key UNIQUE (payroll_group_id, column_key)
);

CREATE TABLE finalized_payroll_runs (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    payroll_group_id BIGINT NOT NULL, 
    cycle_from DATE NOT NULL, 
    cycle_to DATE NOT NULL, 
    payroll_module VARCHAR(30) NOT NULL, 
    finalized_amount NUMERIC(14, 2) NOT NULL, 
    finalized_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    finalized_by BIGINT NOT NULL, 
    paid_amount NUMERIC(14, 2), 
    paid_at TIMESTAMP WITH TIME ZONE, 
    payment_status VARCHAR(20) DEFAULT 'pending' NOT NULL, 
    is_definalized BOOLEAN DEFAULT false NOT NULL, 
    definalized_at TIMESTAMP WITH TIME ZONE, 
    definalized_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_finalized_payroll_runs PRIMARY KEY (id), 
    CONSTRAINT fk_finalized_payroll_runs_payroll_group_id_payroll_groups FOREIGN KEY(payroll_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT ck_finalized_payroll_runs_ck_finalized_payroll_runs_pay_e899 CHECK (payment_status IN ('pending', 'paid', 'partial'))
);

CREATE INDEX ix_finalized_payroll_runs_org_id_payroll_group_id_cycle_from ON finalized_payroll_runs (org_id, payroll_group_id, cycle_from);

CREATE TABLE payroll_computed_rows (
    id BIGSERIAL NOT NULL, 
    payroll_group_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    cycle_from DATE NOT NULL, 
    cycle_to DATE NOT NULL, 
    total_days SMALLINT NOT NULL, 
    full_day_count SMALLINT DEFAULT 0 NOT NULL, 
    half_day_count SMALLINT DEFAULT 0 NOT NULL, 
    off_day_count SMALLINT DEFAULT 0 NOT NULL, 
    paid_leave_count NUMERIC(5, 1) DEFAULT 0 NOT NULL, 
    paid_day_count NUMERIC(5, 1) DEFAULT 0 NOT NULL, 
    unpaid_day_count NUMERIC(5, 1) DEFAULT 0 NOT NULL, 
    daily_wage NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    gross_wages NUMERIC(12, 2) DEFAULT 0 NOT NULL, 
    overtime_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    penalties_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    extras_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    gross_earnings NUMERIC(12, 2) DEFAULT 0 NOT NULL, 
    loan_advance_deduction NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    arrears_amount NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    to_pay NUMERIC(12, 2) DEFAULT 0 NOT NULL, 
    balance_arrears NUMERIC(10, 2) DEFAULT 0 NOT NULL, 
    payment_method VARCHAR(30), 
    is_finalized BOOLEAN DEFAULT false NOT NULL, 
    finalized_run_id BIGINT, 
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    computed_by BIGINT, 
    CONSTRAINT pk_payroll_computed_rows PRIMARY KEY (id), 
    CONSTRAINT fk_payroll_computed_rows_payroll_group_id_payroll_groups FOREIGN KEY(payroll_group_id) REFERENCES payroll_groups (id), 
    CONSTRAINT fk_payroll_computed_rows_finalized_run_id_final_runs FOREIGN KEY(finalized_run_id) REFERENCES finalized_payroll_runs (id), 
    CONSTRAINT uq_payroll_computed_rows_group_employee_cycle UNIQUE (payroll_group_id, employee_id, cycle_from, cycle_to)
);

CREATE INDEX ix_payroll_computed_rows_payroll_group_id_cycle_from_cycle_to ON payroll_computed_rows (payroll_group_id, cycle_from, cycle_to);

CREATE INDEX ix_payroll_computed_rows_employee_id_is_finalized ON payroll_computed_rows (employee_id, is_finalized);

UPDATE alembic_version SET version_num='0005_payroll' WHERE alembic_version.version_num = '0004_approval_requests';

-- Running upgrade 0005_payroll -> 0006_settlements

CREATE TABLE employee_loans_advances (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_id BIGINT NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    type VARCHAR(20) DEFAULT 'loan' NOT NULL, 
    principal_amount NUMERIC(12, 2) NOT NULL, 
    monthly_installment NUMERIC(12, 2) NOT NULL, 
    total_debit NUMERIC(12, 2) DEFAULT 0.00 NOT NULL, 
    outstanding_amount NUMERIC(12, 2) NOT NULL, 
    transaction_date DATE NOT NULL, 
    status VARCHAR(20) DEFAULT 'active' NOT NULL, 
    comment TEXT, 
    created_by BIGINT NOT NULL, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_loans_advances PRIMARY KEY (id), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_type CHECK (type IN ('loan', 'advance')), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_status CHECK (status IN ('active', 'closed')), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_p_0898 CHECK (principal_amount > 0), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_m_0d04 CHECK (monthly_installment > 0), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_t_9595 CHECK (total_debit >= 0), 
    CONSTRAINT ck_employee_loans_advances_ck_employee_loans_advances_o_41ec CHECK (outstanding_amount >= 0)
);

CREATE TABLE loan_advance_transactions (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    loan_advance_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    transaction_date DATE NOT NULL, 
    transaction_type VARCHAR(10) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    installment_amount NUMERIC(12, 2), 
    type_label VARCHAR(20) NOT NULL, 
    comment TEXT, 
    source VARCHAR(10) DEFAULT 'manual' NOT NULL, 
    payroll_run_id BIGINT, 
    created_by BIGINT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_loan_advance_transactions PRIMARY KEY (id), 
    CONSTRAINT fk_loan_adv_txns_loan_advance_id_employee_loans_advances FOREIGN KEY(loan_advance_id) REFERENCES employee_loans_advances (id) ON DELETE RESTRICT, 
    CONSTRAINT ck_loan_advance_transactions_ck_loan_advance_transactio_e6c9 CHECK (transaction_type IN ('credit', 'debit')), 
    CONSTRAINT ck_loan_advance_transactions_ck_loan_advance_transactio_5f13 CHECK (type_label IN ('loan', 'advance')), 
    CONSTRAINT ck_loan_advance_transactions_ck_loan_advance_transactio_7aeb CHECK (source IN ('manual', 'payroll'))
);

CREATE INDEX ix_loan_advance_transactions_employee_id_transaction_date ON loan_advance_transactions (employee_id, transaction_date);

CREATE INDEX ix_loan_advance_transactions_org_id_transaction_date_type_label ON loan_advance_transactions (org_id, transaction_date, type_label);

CREATE TABLE employee_arrears (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_id BIGINT NOT NULL, 
    arrears_created NUMERIC(12, 2) DEFAULT 0.00 NOT NULL, 
    arrears_paid NUMERIC(12, 2) DEFAULT 0.00 NOT NULL, 
    outstanding_arrears NUMERIC(12, 2) DEFAULT 0.00 NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_employee_arrears PRIMARY KEY (id), 
    CONSTRAINT uq_employee_arrears_org_id_employee_id UNIQUE (org_id, employee_id), 
    CONSTRAINT ck_employee_arrears_ck_employee_arrears_arrears_created CHECK (arrears_created >= 0), 
    CONSTRAINT ck_employee_arrears_ck_employee_arrears_arrears_paid CHECK (arrears_paid >= 0), 
    CONSTRAINT ck_employee_arrears_ck_employee_arrears_outstanding_arrears CHECK (outstanding_arrears >= 0)
);

CREATE TABLE arrears_transactions (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    employee_arrears_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    transaction_date DATE NOT NULL, 
    transaction_type VARCHAR(10) NOT NULL, 
    amount NUMERIC(12, 2) NOT NULL, 
    outstanding_before NUMERIC(12, 2) NOT NULL, 
    outstanding_after NUMERIC(12, 2) NOT NULL, 
    comment TEXT, 
    source VARCHAR(10) DEFAULT 'manual' NOT NULL, 
    payroll_run_id BIGINT, 
    created_by BIGINT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_arrears_transactions PRIMARY KEY (id), 
    CONSTRAINT fk_arrears_transactions_employee_arrears_id_employee_arrears FOREIGN KEY(employee_arrears_id) REFERENCES employee_arrears (id) ON DELETE RESTRICT, 
    CONSTRAINT ck_arrears_transactions_ck_arrears_transactions_transac_b7ce CHECK (transaction_type IN ('credit', 'debit')), 
    CONSTRAINT ck_arrears_transactions_ck_arrears_transactions_source CHECK (source IN ('manual', 'payroll'))
);

CREATE INDEX ix_arrears_transactions_employee_id_transaction_date ON arrears_transactions (employee_id, transaction_date);

CREATE INDEX ix_arrears_transactions_org_id_transaction_date ON arrears_transactions (org_id, transaction_date);

UPDATE alembic_version SET version_num='0006_settlements' WHERE alembic_version.version_num = '0005_payroll';

-- Running upgrade 0006_settlements -> 0007_user_management_rbac

CREATE TABLE users (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    mobile_country_code VARCHAR(10) DEFAULT '+91' NOT NULL, 
    mobile_number VARCHAR(20) NOT NULL, 
    password_hash VARCHAR(255), 
    is_super_admin BOOLEAN DEFAULT false NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    employee_id BIGINT, 
    last_login_at TIMESTAMP WITH TIME ZONE, 
    created_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_users PRIMARY KEY (id), 
    CONSTRAINT fk_users_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT uq_users_org_id_email UNIQUE (org_id, email), 
    CONSTRAINT uq_users_org_id_mobile_country_code_mobile_number UNIQUE (org_id, mobile_country_code, mobile_number)
);

CREATE INDEX ix_users_org_id_is_active_deleted_at ON users (org_id, is_active, deleted_at);

CREATE TABLE rights_templates (
    id BIGSERIAL NOT NULL, 
    org_id INTEGER NOT NULL, 
    name VARCHAR(150) NOT NULL, 
    created_by BIGINT NOT NULL, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_rights_templates PRIMARY KEY (id), 
    CONSTRAINT fk_rights_templates_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT fk_rights_templates_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id), 
    CONSTRAINT uq_rights_templates_org_id_name UNIQUE (org_id, name)
);

CREATE INDEX ix_rights_templates_org_id_deleted_at ON rights_templates (org_id, deleted_at);

CREATE TABLE rights_template_permissions (
    id BIGSERIAL NOT NULL, 
    template_id BIGINT NOT NULL, 
    feature_key VARCHAR(100) NOT NULL, 
    feature_label VARCHAR(150) NOT NULL, 
    parent_feature_key VARCHAR(100), 
    can_create BOOLEAN DEFAULT false NOT NULL, 
    can_read BOOLEAN DEFAULT false NOT NULL, 
    can_edit BOOLEAN DEFAULT false NOT NULL, 
    can_delete BOOLEAN DEFAULT false NOT NULL, 
    CONSTRAINT pk_rights_template_permissions PRIMARY KEY (id), 
    CONSTRAINT fk_rights_template_permissions_template_id_rights_templates FOREIGN KEY(template_id) REFERENCES rights_templates (id) ON DELETE CASCADE, 
    CONSTRAINT uq_rights_template_permissions_template_id_feature_key UNIQUE (template_id, feature_key)
);

CREATE TABLE user_template_assignments (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    template_id BIGINT NOT NULL, 
    assigned_by BIGINT NOT NULL, 
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_user_template_assignments PRIMARY KEY (id), 
    CONSTRAINT fk_user_template_assignments_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_template_assignments_template_id_rights_templates FOREIGN KEY(template_id) REFERENCES rights_templates (id) ON DELETE RESTRICT, 
    CONSTRAINT fk_user_template_assignments_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id), 
    CONSTRAINT uq_user_template_assignments_user_id UNIQUE (user_id)
);

CREATE TABLE user_custom_permissions (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    feature_key VARCHAR(100) NOT NULL, 
    parent_feature_key VARCHAR(100), 
    can_create BOOLEAN DEFAULT false NOT NULL, 
    can_read BOOLEAN DEFAULT false NOT NULL, 
    can_edit BOOLEAN DEFAULT false NOT NULL, 
    can_delete BOOLEAN DEFAULT false NOT NULL, 
    set_by BIGINT NOT NULL, 
    set_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_user_custom_permissions PRIMARY KEY (id), 
    CONSTRAINT fk_user_custom_permissions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_custom_permissions_set_by_users FOREIGN KEY(set_by) REFERENCES users (id), 
    CONSTRAINT uq_user_custom_permissions_user_id_feature_key UNIQUE (user_id, feature_key)
);

CREATE TABLE user_branch_access (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    branch_id BIGINT NOT NULL, 
    granted_by BIGINT NOT NULL, 
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_user_branch_access PRIMARY KEY (id), 
    CONSTRAINT fk_user_branch_access_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_branch_access_granted_by_users FOREIGN KEY(granted_by) REFERENCES users (id), 
    CONSTRAINT uq_user_branch_access_user_id_branch_id UNIQUE (user_id, branch_id)
);

CREATE TABLE user_department_access (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    department_id BIGINT NOT NULL, 
    granted_by BIGINT NOT NULL, 
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_user_department_access PRIMARY KEY (id), 
    CONSTRAINT fk_user_department_access_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_department_access_granted_by_users FOREIGN KEY(granted_by) REFERENCES users (id), 
    CONSTRAINT uq_user_department_access_user_id_department_id UNIQUE (user_id, department_id)
);

CREATE TABLE user_sessions (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    session_token VARCHAR(500) NOT NULL, 
    device_info VARCHAR(500), 
    ip_address INET, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    CONSTRAINT pk_user_sessions PRIMARY KEY (id), 
    CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_user_sessions_session_token UNIQUE (session_token)
);

CREATE INDEX ix_user_sessions_user_id_is_active ON user_sessions (user_id, is_active);

UPDATE alembic_version SET version_num='0007_user_management_rbac' WHERE alembic_version.version_num = '0006_settlements';

-- Running upgrade 0007_user_management_rbac -> 0008_resolve_deferred_user_fks

ALTER TABLE leave_settings ADD CONSTRAINT fk_leave_settings_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE leave_settings ADD CONSTRAINT fk_leave_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE leave_types ADD CONSTRAINT fk_leave_types_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE leave_types ADD CONSTRAINT fk_leave_types_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE employee_leave_allocations ADD CONSTRAINT fk_employee_leave_allocations_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE employee_leave_balances ADD CONSTRAINT fk_employee_leave_balances_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE leave_balance_adjustments ADD CONSTRAINT fk_leave_balance_adjustments_adjusted_by_users FOREIGN KEY(adjusted_by) REFERENCES users (id);

ALTER TABLE holiday_templates ADD CONSTRAINT fk_holiday_templates_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE holiday_templates ADD CONSTRAINT fk_holiday_templates_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE holiday_template_items ADD CONSTRAINT fk_holiday_template_items_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE employee_holiday_assignments ADD CONSTRAINT fk_employee_holiday_assignments_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id);

ALTER TABLE leave_requests ADD CONSTRAINT fk_leave_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id);

ALTER TABLE approval_requests ADD CONSTRAINT fk_approval_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id);

ALTER TABLE login_reset_requests ADD CONSTRAINT fk_login_reset_requests_reviewed_by_users FOREIGN KEY(reviewed_by) REFERENCES users (id);

ALTER TABLE payroll_settings ADD CONSTRAINT fk_payroll_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE payroll_groups ADD CONSTRAINT fk_payroll_groups_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE payroll_groups ADD CONSTRAINT fk_payroll_groups_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE employee_payroll_group_assignments ADD CONSTRAINT fk_employee_payroll_group_assignments_assigned_by_users FOREIGN KEY(assigned_by) REFERENCES users (id);

ALTER TABLE payroll_salary_cycles ADD CONSTRAINT fk_payroll_salary_cycles_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE attendance_adjustments ADD CONSTRAINT fk_attendance_adjustments_adjusted_by_users FOREIGN KEY(adjusted_by) REFERENCES users (id);

ALTER TABLE attendance_adjustment_penalties ADD CONSTRAINT fk_attendance_adjustment_penalties_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE attendance_adjustment_extra_hours ADD CONSTRAINT fk_attendance_adjustment_extra_hours_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE payroll_column_settings ADD CONSTRAINT fk_payroll_column_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE finalized_payroll_runs ADD CONSTRAINT fk_finalized_payroll_runs_finalized_by_users FOREIGN KEY(finalized_by) REFERENCES users (id);

ALTER TABLE finalized_payroll_runs ADD CONSTRAINT fk_finalized_payroll_runs_definalized_by_users FOREIGN KEY(definalized_by) REFERENCES users (id);

ALTER TABLE payroll_computed_rows ADD CONSTRAINT fk_payroll_computed_rows_computed_by_users FOREIGN KEY(computed_by) REFERENCES users (id);

ALTER TABLE employee_loans_advances ADD CONSTRAINT fk_employee_loans_advances_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE employee_loans_advances ADD CONSTRAINT fk_employee_loans_advances_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id);

ALTER TABLE loan_advance_transactions ADD CONSTRAINT fk_loan_advance_transactions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

ALTER TABLE arrears_transactions ADD CONSTRAINT fk_arrears_transactions_created_by_users FOREIGN KEY(created_by) REFERENCES users (id);

UPDATE alembic_version SET version_num='0008_resolve_deferred_user_fks' WHERE alembic_version.version_num = '0007_user_management_rbac';

-- Running upgrade 0008_resolve_deferred_user_fks -> 0009_standardize_bigint_pks

ALTER TABLE branches DROP CONSTRAINT fk_branches_org_id_organizations;

ALTER TABLE departments DROP CONSTRAINT fk_departments_org_id_organizations;

ALTER TABLE designations DROP CONSTRAINT fk_designations_org_id_organizations;

ALTER TABLE employees DROP CONSTRAINT fk_employees_org_id_organizations;

ALTER TABLE employees DROP CONSTRAINT fk_employees_master_branch_id_branches;

ALTER TABLE employees DROP CONSTRAINT fk_employees_dept_id_departments;

ALTER TABLE employees DROP CONSTRAINT fk_employees_designation_id_designations;

ALTER TABLE employee_bank_details DROP CONSTRAINT fk_employee_bank_details_employee_id_employees;

ALTER TABLE employee_documents DROP CONSTRAINT fk_employee_documents_employee_id_employees;

ALTER TABLE employee_emergency_contacts DROP CONSTRAINT fk_employee_emergency_contacts_employee_id_employees;

ALTER TABLE employee_references DROP CONSTRAINT fk_employee_references_employee_id_employees;

ALTER TABLE employee_biometrics DROP CONSTRAINT fk_employee_biometrics_employee_id_employees;

ALTER TABLE employee_punch_branches DROP CONSTRAINT fk_employee_punch_branches_employee_id_employees;

ALTER TABLE employee_punch_branches DROP CONSTRAINT fk_employee_punch_branches_branch_id_branches;

ALTER TABLE employee_attendance_permissions DROP CONSTRAINT fk_employee_attendance_permissions_employee_id_employees;

ALTER TABLE org_attendance_settings DROP CONSTRAINT fk_org_attendance_settings_org_id_organizations;

ALTER TABLE org_attendance_settings DROP CONSTRAINT fk_org_attendance_settings_branch_id_branches;

ALTER TABLE employee_import_logs DROP CONSTRAINT fk_employee_import_logs_org_id_organizations;

ALTER TABLE employee_tags DROP CONSTRAINT fk_employee_tags_employee_id_employees;

ALTER TABLE employee_status_history DROP CONSTRAINT fk_employee_status_history_employee_id_employees;

ALTER TABLE shifts DROP CONSTRAINT fk_shifts_org_id_organizations;

ALTER TABLE shift_day_timings DROP CONSTRAINT fk_shift_day_timings_shift_id_shifts;

ALTER TABLE shift_assignments DROP CONSTRAINT fk_shift_assignments_org_id_organizations;

ALTER TABLE shift_assignments DROP CONSTRAINT fk_shift_assignments_employee_id_employees;

ALTER TABLE shift_assignments DROP CONSTRAINT fk_shift_assignments_shift_id_shifts;

ALTER TABLE employee_weekoffs DROP CONSTRAINT fk_employee_weekoffs_employee_id_employees;

ALTER TABLE roster DROP CONSTRAINT fk_roster_org_id_organizations;

ALTER TABLE roster DROP CONSTRAINT fk_roster_employee_id_employees;

ALTER TABLE roster DROP CONSTRAINT fk_roster_shift_id_shifts;

ALTER TABLE working_hours_config DROP CONSTRAINT fk_working_hours_config_org_id_organizations;

ALTER TABLE working_hours_config_history DROP CONSTRAINT fk_working_hours_config_history_org_id_organizations;

ALTER TABLE working_hours_config_history DROP CONSTRAINT fk_working_hours_config_history_config_id_working_hours_config;

ALTER TABLE organizations ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE branches ALTER COLUMN branch_id TYPE BIGINT;

ALTER TABLE branches ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE departments ALTER COLUMN dept_id TYPE BIGINT;

ALTER TABLE departments ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE departments ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE designations ALTER COLUMN designation_id TYPE BIGINT;

ALTER TABLE designations ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE designations ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN master_branch_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN dept_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN designation_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN payroll_group_id TYPE BIGINT;

ALTER TABLE employees ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE employee_bank_details ALTER COLUMN bank_detail_id TYPE BIGINT;

ALTER TABLE employee_bank_details ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_documents ALTER COLUMN document_id TYPE BIGINT;

ALTER TABLE employee_documents ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_documents ALTER COLUMN uploaded_by TYPE BIGINT;

ALTER TABLE employee_emergency_contacts ALTER COLUMN emergency_contact_id TYPE BIGINT;

ALTER TABLE employee_emergency_contacts ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_references ALTER COLUMN reference_id TYPE BIGINT;

ALTER TABLE employee_references ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_biometrics ALTER COLUMN biometric_id TYPE BIGINT;

ALTER TABLE employee_biometrics ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_biometrics ALTER COLUMN device_id TYPE BIGINT;

ALTER TABLE employee_biometrics ALTER COLUMN registered_by TYPE BIGINT;

ALTER TABLE employee_punch_branches ALTER COLUMN punch_branch_id TYPE BIGINT;

ALTER TABLE employee_punch_branches ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_punch_branches ALTER COLUMN branch_id TYPE BIGINT;

ALTER TABLE employee_punch_branches ALTER COLUMN assigned_by TYPE BIGINT;

ALTER TABLE employee_attendance_permissions ALTER COLUMN att_perm_id TYPE BIGINT;

ALTER TABLE employee_attendance_permissions ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_attendance_permissions ALTER COLUMN updated_by TYPE BIGINT;

ALTER TABLE org_attendance_settings ALTER COLUMN setting_id TYPE BIGINT;

ALTER TABLE org_attendance_settings ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE org_attendance_settings ALTER COLUMN branch_id TYPE BIGINT;

ALTER TABLE org_attendance_settings ALTER COLUMN device_id TYPE BIGINT;

ALTER TABLE org_attendance_settings ALTER COLUMN updated_by TYPE BIGINT;

ALTER TABLE employee_import_logs ALTER COLUMN import_log_id TYPE BIGINT;

ALTER TABLE employee_import_logs ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE employee_import_logs ALTER COLUMN initiated_by TYPE BIGINT;

ALTER TABLE employee_tags ALTER COLUMN tag_id TYPE BIGINT;

ALTER TABLE employee_tags ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_tags ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE employee_status_history ALTER COLUMN status_history_id TYPE BIGINT;

ALTER TABLE employee_status_history ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_status_history ALTER COLUMN changed_by TYPE BIGINT;

ALTER TABLE shifts ALTER COLUMN shift_id TYPE BIGINT;

ALTER TABLE shifts ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE shifts ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE shift_day_timings ALTER COLUMN timing_id TYPE BIGINT;

ALTER TABLE shift_day_timings ALTER COLUMN shift_id TYPE BIGINT;

ALTER TABLE shift_assignments ALTER COLUMN assignment_id TYPE BIGINT;

ALTER TABLE shift_assignments ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE shift_assignments ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE shift_assignments ALTER COLUMN shift_id TYPE BIGINT;

ALTER TABLE shift_assignments ALTER COLUMN assigned_by TYPE BIGINT;

ALTER TABLE employee_weekoffs ALTER COLUMN weekoff_id TYPE BIGINT;

ALTER TABLE employee_weekoffs ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE employee_weekoffs ALTER COLUMN updated_by TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN roster_id TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN employee_id TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN shift_id TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE roster ALTER COLUMN updated_by TYPE BIGINT;

ALTER TABLE working_hours_config ALTER COLUMN config_id TYPE BIGINT;

ALTER TABLE working_hours_config ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE working_hours_config ALTER COLUMN created_by TYPE BIGINT;

ALTER TABLE working_hours_config_history ALTER COLUMN history_id TYPE BIGINT;

ALTER TABLE working_hours_config_history ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE working_hours_config_history ALTER COLUMN config_id TYPE BIGINT;

ALTER TABLE working_hours_config_history ALTER COLUMN changed_by TYPE BIGINT;

ALTER TABLE employee_loans_advances ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE loan_advance_transactions ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE employee_arrears ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE arrears_transactions ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE users ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE rights_templates ALTER COLUMN org_id TYPE BIGINT;

ALTER TABLE branches ADD CONSTRAINT fk_branches_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE departments ADD CONSTRAINT fk_departments_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE designations ADD CONSTRAINT fk_designations_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE employees ADD CONSTRAINT fk_employees_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE employees ADD CONSTRAINT fk_employees_master_branch_id_branches FOREIGN KEY(master_branch_id) REFERENCES branches (branch_id);

ALTER TABLE employees ADD CONSTRAINT fk_employees_dept_id_departments FOREIGN KEY(dept_id) REFERENCES departments (dept_id);

ALTER TABLE employees ADD CONSTRAINT fk_employees_designation_id_designations FOREIGN KEY(designation_id) REFERENCES designations (designation_id);

ALTER TABLE employee_bank_details ADD CONSTRAINT fk_employee_bank_details_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_documents ADD CONSTRAINT fk_employee_documents_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_emergency_contacts ADD CONSTRAINT fk_employee_emergency_contacts_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_references ADD CONSTRAINT fk_employee_references_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_biometrics ADD CONSTRAINT fk_employee_biometrics_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_punch_branches ADD CONSTRAINT fk_employee_punch_branches_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_punch_branches ADD CONSTRAINT fk_employee_punch_branches_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id);

ALTER TABLE employee_attendance_permissions ADD CONSTRAINT fk_employee_attendance_permissions_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE org_attendance_settings ADD CONSTRAINT fk_org_attendance_settings_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE org_attendance_settings ADD CONSTRAINT fk_org_attendance_settings_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id);

ALTER TABLE employee_import_logs ADD CONSTRAINT fk_employee_import_logs_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE employee_tags ADD CONSTRAINT fk_employee_tags_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE employee_status_history ADD CONSTRAINT fk_employee_status_history_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE shifts ADD CONSTRAINT fk_shifts_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE shift_day_timings ADD CONSTRAINT fk_shift_day_timings_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id);

ALTER TABLE shift_assignments ADD CONSTRAINT fk_shift_assignments_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE shift_assignments ADD CONSTRAINT fk_shift_assignments_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE shift_assignments ADD CONSTRAINT fk_shift_assignments_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id);

ALTER TABLE employee_weekoffs ADD CONSTRAINT fk_employee_weekoffs_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE roster ADD CONSTRAINT fk_roster_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE roster ADD CONSTRAINT fk_roster_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id);

ALTER TABLE roster ADD CONSTRAINT fk_roster_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id);

ALTER TABLE working_hours_config ADD CONSTRAINT fk_working_hours_config_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE working_hours_config_history ADD CONSTRAINT fk_working_hours_config_history_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE working_hours_config_history ADD CONSTRAINT fk_working_hours_config_history_config_id_working_hours_config FOREIGN KEY(config_id) REFERENCES working_hours_config (config_id);

UPDATE alembic_version SET version_num='0009_standardize_bigint_pks' WHERE alembic_version.version_num = '0008_resolve_deferred_user_fks';

-- Running upgrade 0009_standardize_bigint_pks -> 0010_activity_log

CREATE TABLE activity_logs (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    module VARCHAR(100) NOT NULL, 
    sub_module VARCHAR(150), 
    employee_id BIGINT, 
    employee_name VARCHAR(200), 
    title VARCHAR(200) NOT NULL, 
    description TEXT NOT NULL, 
    payroll_date DATE, 
    action_type VARCHAR(50) NOT NULL, 
    performed_by_user_id BIGINT, 
    performed_by_name VARCHAR(200) NOT NULL, 
    log_date DATE NOT NULL, 
    log_time TIME WITHOUT TIME ZONE NOT NULL, 
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    action_from VARCHAR(20) DEFAULT 'Web App' NOT NULL, 
    CONSTRAINT pk_activity_logs PRIMARY KEY (id), 
    CONSTRAINT fk_activity_logs_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_activity_logs_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id) ON DELETE SET NULL, 
    CONSTRAINT fk_activity_logs_performed_by_user_id_users FOREIGN KEY(performed_by_user_id) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT ck_activity_logs_ck_activity_logs_action_type CHECK (action_type IN ('Insert', 'Update', 'Delete', 'Assign', 'Bulk Assign')), 
    CONSTRAINT ck_activity_logs_ck_activity_logs_action_from CHECK (action_from IN ('Web App', 'Mobile App'))
);

CREATE INDEX ix_activity_logs_org_id_logged_at ON activity_logs (org_id, logged_at DESC);

CREATE INDEX ix_activity_logs_org_id_log_date ON activity_logs (org_id, log_date);

CREATE INDEX ix_activity_logs_org_id_employee_id ON activity_logs (org_id, employee_id);

CREATE INDEX ix_activity_logs_org_id_module ON activity_logs (org_id, module);

CREATE INDEX ix_activity_logs_performed_by_user_id ON activity_logs (performed_by_user_id);

UPDATE alembic_version SET version_num='0010_activity_log' WHERE alembic_version.version_num = '0009_standardize_bigint_pks';

-- Running upgrade 0010_activity_log -> 0011_settings

CREATE TABLE org_settings (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    advance_shift_enabled BOOLEAN DEFAULT false NOT NULL, 
    enable_regularization BOOLEAN DEFAULT false NOT NULL, 
    enable_photo_punch BOOLEAN DEFAULT false NOT NULL, 
    device_sync_time TIME WITHOUT TIME ZONE DEFAULT '16:51:00' NOT NULL, 
    sync_code VARCHAR(50) NOT NULL, 
    pass_code VARCHAR(20) NOT NULL, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_org_settings PRIMARY KEY (id), 
    CONSTRAINT uq_org_settings_org_id UNIQUE (org_id), 
    CONSTRAINT fk_org_settings_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_org_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE org_salary_slip_settings (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    company_logo_url TEXT, 
    company_name VARCHAR(200) NOT NULL, 
    company_address TEXT NOT NULL, 
    company_contact VARCHAR(100) NOT NULL, 
    company_website_email VARCHAR(200), 
    auto_release_payslip BOOLEAN DEFAULT true NOT NULL, 
    branch_wise_payslip BOOLEAN DEFAULT false NOT NULL, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_org_salary_slip_settings PRIMARY KEY (id), 
    CONSTRAINT uq_org_salary_slip_settings_org_id UNIQUE (org_id), 
    CONSTRAINT fk_org_salary_slip_settings_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_org_salary_slip_settings_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL
);

UPDATE alembic_version SET version_num='0011_settings' WHERE alembic_version.version_num = '0010_activity_log';

-- Running upgrade 0011_settings -> 0012_hardware_biometric_devices

CREATE TABLE biometric_devices (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    branch_id BIGINT, 
    device_name VARCHAR(150) NOT NULL, 
    device_code VARCHAR(50) NOT NULL, 
    serial_number VARCHAR(100) NOT NULL, 
    model VARCHAR(100), 
    manufacturer VARCHAR(100), 
    ip_address INET, 
    port INTEGER, 
    protocol VARCHAR(20) DEFAULT 'tcp_ip' NOT NULL, 
    domain VARCHAR(255), 
    mac_address VARCHAR(17), 
    adms_enabled BOOLEAN DEFAULT false NOT NULL, 
    adms_server VARCHAR(255), 
    adms_port INTEGER, 
    cloud_id VARCHAR(100), 
    communication_key VARCHAR(255), 
    sync_key VARCHAR(255), 
    timezone VARCHAR(50), 
    status VARCHAR(20) DEFAULT 'offline' NOT NULL, 
    last_seen_at TIMESTAMP WITH TIME ZONE, 
    last_sync_at TIMESTAMP WITH TIME ZONE, 
    firmware_version VARCHAR(50), 
    software_version VARCHAR(50), 
    total_users INTEGER DEFAULT 0 NOT NULL, 
    total_fingerprints INTEGER DEFAULT 0 NOT NULL, 
    total_faces INTEGER DEFAULT 0 NOT NULL, 
    total_cards INTEGER DEFAULT 0 NOT NULL, 
    total_logs BIGINT DEFAULT 0 NOT NULL, 
    installation_location VARCHAR(255), 
    remarks TEXT, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_biometric_devices PRIMARY KEY (id), 
    CONSTRAINT fk_biometric_devices_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_biometric_devices_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id) ON DELETE SET NULL, 
    CONSTRAINT fk_biometric_devices_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT fk_biometric_devices_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT uq_biometric_devices_serial_number UNIQUE (serial_number), 
    CONSTRAINT uq_biometric_devices_org_id_device_code UNIQUE (org_id, device_code), 
    CONSTRAINT ck_biometric_devices_ck_biometric_devices_status CHECK (status IN ('online', 'offline', 'disabled', 'maintenance')), 
    CONSTRAINT ck_biometric_devices_ck_biometric_devices_protocol CHECK (protocol IN ('tcp_ip', 'adms', 'usb')), 
    CONSTRAINT ck_biometric_devices_ck_biometric_devices_port CHECK (port IS NULL OR (port BETWEEN 1 AND 65535)), 
    CONSTRAINT ck_biometric_devices_ck_biometric_devices_adms_port CHECK (adms_port IS NULL OR (adms_port BETWEEN 1 AND 65535)), 
    CONSTRAINT ck_biometric_devices_ck_biometric_devices_stats_non_negative CHECK (total_users >= 0 AND total_fingerprints >= 0 AND total_faces >= 0 AND total_cards >= 0 AND total_logs >= 0)
);

CREATE INDEX ix_biometric_devices_org_id ON biometric_devices (org_id);

CREATE INDEX ix_biometric_devices_branch_id ON biometric_devices (branch_id);

CREATE INDEX ix_biometric_devices_org_id_status ON biometric_devices (org_id, status);

UPDATE alembic_version SET version_num='0012_hardware_biometric_devices' WHERE alembic_version.version_num = '0011_settings';

-- Running upgrade 0012_hardware_biometric_devices -> 0013_resolve_deferred_device_fks

ALTER TABLE employee_biometrics ADD CONSTRAINT fk_employee_biometrics_device_id_biometric_devices FOREIGN KEY(device_id) REFERENCES biometric_devices (id) ON DELETE RESTRICT;

ALTER TABLE org_attendance_settings ADD CONSTRAINT fk_org_attendance_settings_device_id_biometric_devices FOREIGN KEY(device_id) REFERENCES biometric_devices (id) ON DELETE SET NULL;

UPDATE alembic_version SET version_num='0013_resolve_deferred_device_fks' WHERE alembic_version.version_num = '0012_hardware_biometric_devices';

-- Running upgrade 0013_resolve_deferred_device_fks -> 0014_notifications

CREATE TABLE notifications (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    title VARCHAR(200) NOT NULL, 
    message TEXT NOT NULL, 
    notification_type VARCHAR(50) NOT NULL, 
    priority VARCHAR(20) NOT NULL, 
    source_module VARCHAR(100), 
    source_entity_type VARCHAR(100), 
    source_entity_id BIGINT, 
    created_by BIGINT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_notifications PRIMARY KEY (id), 
    CONSTRAINT fk_notifications_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_notifications_created_by_users FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_notifications_org_id_created_at ON notifications (org_id, created_at);

CREATE INDEX ix_notifications_org_source_module_entity_type_entity_id ON notifications (org_id, source_module, source_entity_type, source_entity_id);

CREATE TABLE notification_recipients (
    id BIGSERIAL NOT NULL, 
    notification_id BIGINT NOT NULL, 
    org_id BIGINT NOT NULL, 
    user_id BIGINT NOT NULL, 
    delivered_at TIMESTAMP WITH TIME ZONE, 
    read_at TIMESTAMP WITH TIME ZONE, 
    archived_at TIMESTAMP WITH TIME ZONE, 
    deleted_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    CONSTRAINT pk_notification_recipients PRIMARY KEY (id), 
    CONSTRAINT fk_notification_recipients_notification_id_notifications FOREIGN KEY(notification_id) REFERENCES notifications (id) ON DELETE CASCADE, 
    CONSTRAINT fk_notification_recipients_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE RESTRICT, 
    CONSTRAINT fk_notification_recipients_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_notification_recipients_notification_id_user_id UNIQUE (notification_id, user_id)
);

CREATE INDEX ix_notification_recipients_org_id_user_id_deleted_at ON notification_recipients (org_id, user_id, deleted_at);

CREATE INDEX ix_notification_recipients_org_id_user_id_read_at ON notification_recipients (org_id, user_id, read_at);

CREATE INDEX ix_notification_recipients_user_id_created_at ON notification_recipients (user_id, created_at);

UPDATE alembic_version SET version_num='0014_notifications' WHERE alembic_version.version_num = '0013_resolve_deferred_device_fks';

-- Running upgrade 0014_notifications -> 0015_attendance_core

CREATE TABLE attendance_days (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_date DATE NOT NULL, 
    shift_id BIGINT, 
    expected_start_time TIME WITHOUT TIME ZONE, 
    expected_end_time TIME WITHOUT TIME ZONE, 
    status VARCHAR(20) DEFAULT 'not_marked' NOT NULL, 
    first_punch_in TIMESTAMP WITH TIME ZONE, 
    last_punch_out TIMESTAMP WITH TIME ZONE, 
    total_working_minutes INTEGER DEFAULT 0 NOT NULL, 
    total_break_minutes INTEGER DEFAULT 0 NOT NULL, 
    overtime_minutes INTEGER DEFAULT 0 NOT NULL, 
    late_minutes INTEGER DEFAULT 0 NOT NULL, 
    early_leaving_minutes INTEGER DEFAULT 0 NOT NULL, 
    leave_id BIGINT, 
    is_regularized BOOLEAN DEFAULT false NOT NULL, 
    source VARCHAR(20) DEFAULT 'system' NOT NULL, 
    marked_by BIGINT, 
    remarks VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    updated_by BIGINT, 
    CONSTRAINT pk_attendance_days PRIMARY KEY (id), 
    CONSTRAINT fk_attendance_days_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_attendance_days_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_attendance_days_shift_id_shifts FOREIGN KEY(shift_id) REFERENCES shifts (shift_id), 
    CONSTRAINT fk_attendance_days_leave_id_leave_requests FOREIGN KEY(leave_id) REFERENCES leave_requests (id), 
    CONSTRAINT fk_attendance_days_marked_by_users FOREIGN KEY(marked_by) REFERENCES users (id), 
    CONSTRAINT fk_attendance_days_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT fk_attendance_days_updated_by_users FOREIGN KEY(updated_by) REFERENCES users (id), 
    CONSTRAINT uq_attendance_days_employee_id_attendance_date UNIQUE (employee_id, attendance_date), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_status CHECK (status IN ('present', 'absent', 'half_day', 'week_off', 'holiday', 'on_leave', 'not_marked')), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_source CHECK (source IN ('biometric', 'mobile', 'web', 'manual', 'system')), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_total_working_min_70d6 CHECK (total_working_minutes >= 0), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_total_break_minut_28c0 CHECK (total_break_minutes >= 0), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_overtime_minutes__889c CHECK (overtime_minutes >= 0), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_late_minutes_non_negative CHECK (late_minutes >= 0), 
    CONSTRAINT ck_attendance_days_ck_attendance_days_early_leaving_min_0bd9 CHECK (early_leaving_minutes >= 0)
);

CREATE INDEX ix_attendance_days_org_id_attendance_date ON attendance_days (org_id, attendance_date);

CREATE TABLE attendance_punches (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_day_id BIGINT NOT NULL, 
    punch_type VARCHAR(20) NOT NULL, 
    punch_time TIMESTAMP WITH TIME ZONE NOT NULL, 
    sequence_no SMALLINT NOT NULL, 
    punch_source VARCHAR(20) NOT NULL, 
    device_id BIGINT, 
    latitude NUMERIC(9, 6), 
    longitude NUMERIC(9, 6), 
    is_valid BOOLEAN DEFAULT true NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    created_by BIGINT, 
    CONSTRAINT pk_attendance_punches PRIMARY KEY (id), 
    CONSTRAINT fk_attendance_punches_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_attendance_punches_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_attendance_punches_attendance_day_id_attendance_days FOREIGN KEY(attendance_day_id) REFERENCES attendance_days (id), 
    CONSTRAINT fk_attendance_punches_device_id_biometric_devices FOREIGN KEY(device_id) REFERENCES biometric_devices (id), 
    CONSTRAINT fk_attendance_punches_created_by_users FOREIGN KEY(created_by) REFERENCES users (id), 
    CONSTRAINT ck_attendance_punches_ck_attendance_punches_punch_type CHECK (punch_type IN ('in', 'out', 'break_in', 'break_out')), 
    CONSTRAINT ck_attendance_punches_ck_attendance_punches_punch_source CHECK (punch_source IN ('biometric_device', 'mobile_app', 'web_portal', 'manual_entry')), 
    CONSTRAINT ck_attendance_punches_ck_attendance_punches_sequence_no_b072 CHECK (sequence_no > 0)
);

CREATE INDEX ix_attendance_punches_attendance_day_id_sequence_no ON attendance_punches (attendance_day_id, sequence_no);

CREATE INDEX ix_attendance_punches_employee_id_punch_time ON attendance_punches (employee_id, punch_time);

CREATE INDEX ix_attendance_punches_device_id_punch_time ON attendance_punches (device_id, punch_time);

CREATE TABLE attendance_penalties (
    id BIGSERIAL NOT NULL, 
    org_id BIGINT NOT NULL, 
    employee_id BIGINT NOT NULL, 
    attendance_day_id BIGINT NOT NULL, 
    penalty_type VARCHAR(30) NOT NULL, 
    penalty_unit VARCHAR(10) NOT NULL, 
    penalty_value NUMERIC(10, 2) NOT NULL, 
    status VARCHAR(10) DEFAULT 'active' NOT NULL, 
    applied_by BIGINT NOT NULL, 
    payroll_reference_id BIGINT, 
    remarks VARCHAR(500), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    is_deleted BOOLEAN DEFAULT false NOT NULL, 
    CONSTRAINT pk_attendance_penalties PRIMARY KEY (id), 
    CONSTRAINT fk_attendance_penalties_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id), 
    CONSTRAINT fk_attendance_penalties_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id), 
    CONSTRAINT fk_attendance_penalties_attendance_day_id_attendance_days FOREIGN KEY(attendance_day_id) REFERENCES attendance_days (id), 
    CONSTRAINT fk_attendance_penalties_applied_by_users FOREIGN KEY(applied_by) REFERENCES users (id), 
    CONSTRAINT ck_attendance_penalties_ck_attendance_penalties_penalty_type CHECK (penalty_type IN ('late_coming', 'early_going', 'absent_without_notice', 'other')), 
    CONSTRAINT ck_attendance_penalties_ck_attendance_penalties_penalty_unit CHECK (penalty_unit IN ('amount', 'days', 'hours')), 
    CONSTRAINT ck_attendance_penalties_ck_attendance_penalties_status CHECK (status IN ('active', 'waived')), 
    CONSTRAINT ck_attendance_penalties_ck_attendance_penalties_penalty_a772 CHECK (penalty_value >= 0)
);

CREATE INDEX ix_attendance_penalties_employee_id_status ON attendance_penalties (employee_id, status);

CREATE INDEX ix_attendance_penalties_attendance_day_id ON attendance_penalties (attendance_day_id);

CREATE INDEX ix_attendance_penalties_payroll_reference_id ON attendance_penalties (payroll_reference_id);

UPDATE alembic_version SET version_num='0015_attendance_core' WHERE alembic_version.version_num = '0014_notifications';

-- Running upgrade 0015_attendance_core -> 0016_resolve_remaining_fks

ALTER TABLE users ADD CONSTRAINT fk_users_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id);

ALTER TABLE users ADD CONSTRAINT fk_users_employee_id_employees FOREIGN KEY(employee_id) REFERENCES employees (employee_id) ON DELETE SET NULL;

ALTER TABLE user_branch_access ADD CONSTRAINT fk_user_branch_access_branch_id_branches FOREIGN KEY(branch_id) REFERENCES branches (branch_id) ON DELETE RESTRICT;

ALTER TABLE user_department_access ADD CONSTRAINT fk_user_department_access_department_id_departments FOREIGN KEY(department_id) REFERENCES departments (dept_id) ON DELETE RESTRICT;

UPDATE alembic_version SET version_num='0016_resolve_remaining_fks' WHERE alembic_version.version_num = '0015_attendance_core';

-- Running upgrade 0016_resolve_remaining_fks -> 0017_employee_settlement_state

ALTER TABLE employees ADD COLUMN settlement_finalized_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE employees ADD COLUMN settlement_finalized_by BIGINT;

ALTER TABLE employees ADD CONSTRAINT fk_employees_settlement_finalized_by_users FOREIGN KEY(settlement_finalized_by) REFERENCES users (id) ON DELETE SET NULL;

CREATE INDEX ix_employees_settlement_finalized_at ON employees (settlement_finalized_at);

UPDATE alembic_version SET version_num='0017_employee_settlement_state' WHERE alembic_version.version_num = '0016_resolve_remaining_fks';

-- Running upgrade 0017_employee_settlement_state -> 0018_fk_supporting_indexes

CREATE INDEX ix_employee_bank_details_employee_id ON employee_bank_details (employee_id);

CREATE INDEX ix_employee_documents_employee_id ON employee_documents (employee_id);

CREATE INDEX ix_employee_emergency_contacts_employee_id ON employee_emergency_contacts (employee_id);

CREATE INDEX ix_employee_references_employee_id ON employee_references (employee_id);

CREATE INDEX ix_employee_tags_employee_id ON employee_tags (employee_id);

CREATE INDEX ix_employee_status_history_employee_id ON employee_status_history (employee_id);

CREATE INDEX ix_branches_org_id ON branches (org_id);

CREATE INDEX ix_attendance_punches_org_id_punch_time ON attendance_punches (org_id, punch_time);

CREATE INDEX ix_attendance_penalties_org_id_status ON attendance_penalties (org_id, status);

CREATE INDEX ix_shift_assignments_org_id_employee_id ON shift_assignments (org_id, employee_id);

CREATE INDEX ix_attendance_days_shift_id ON attendance_days (shift_id);

CREATE INDEX ix_shift_assignments_shift_id ON shift_assignments (shift_id);

CREATE INDEX ix_roster_shift_id ON roster (shift_id);

CREATE INDEX ix_employees_dept_id ON employees (dept_id);

CREATE INDEX ix_employees_designation_id ON employees (designation_id);

CREATE INDEX ix_employees_master_branch_id ON employees (master_branch_id);

CREATE INDEX ix_users_employee_id ON users (employee_id);

CREATE INDEX ix_employee_leave_balances_leave_type_id ON employee_leave_balances (leave_type_id);

CREATE INDEX ix_employee_holiday_assignments_template_id ON employee_holiday_assignments (template_id);

CREATE INDEX ix_employee_biometrics_device_id ON employee_biometrics (device_id);

CREATE INDEX ix_user_branch_access_branch_id ON user_branch_access (branch_id);

CREATE INDEX ix_user_department_access_department_id ON user_department_access (department_id);

CREATE INDEX ix_user_template_assignments_template_id ON user_template_assignments (template_id);

CREATE INDEX ix_arrears_transactions_employee_arrears_id ON arrears_transactions (employee_arrears_id);

CREATE INDEX ix_loan_advance_transactions_loan_advance_id ON loan_advance_transactions (loan_advance_id);

UPDATE alembic_version SET version_num='0018_fk_supporting_indexes' WHERE alembic_version.version_num = '0017_employee_settlement_state';

-- Running upgrade 0018_fk_supporting_indexes -> 0019_user_org_memberships

CREATE TABLE user_organization_memberships (
    id BIGSERIAL NOT NULL, 
    user_id BIGINT NOT NULL, 
    org_id BIGINT NOT NULL, 
    is_primary BOOLEAN DEFAULT false NOT NULL, 
    is_active BOOLEAN DEFAULT true NOT NULL, 
    invited_by BIGINT, 
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    accepted_at TIMESTAMP WITH TIME ZONE, 
    CONSTRAINT pk_user_org_memberships PRIMARY KEY (id), 
    CONSTRAINT fk_user_org_memberships_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_org_memberships_org_id_organizations FOREIGN KEY(org_id) REFERENCES organizations (org_id) ON DELETE CASCADE, 
    CONSTRAINT fk_user_org_memberships_invited_by_users FOREIGN KEY(invited_by) REFERENCES users (id) ON DELETE SET NULL, 
    CONSTRAINT uq_user_org_memberships_user_id_org_id UNIQUE (user_id, org_id)
);

CREATE INDEX ix_user_org_memberships_org_id_is_active ON user_organization_memberships (org_id, is_active);

CREATE INDEX ix_user_org_memberships_user_id_is_active ON user_organization_memberships (user_id, is_active);

INSERT INTO user_organization_memberships
                (user_id, org_id, is_primary, is_active, invited_by,
                 invited_at, accepted_at)
            SELECT
                id,
                org_id,
                true,
                true,
                NULL,
                created_at,
                created_at
            FROM users
            ON CONFLICT (user_id, org_id) DO NOTHING;

UPDATE alembic_version SET version_num='0019_user_org_memberships' WHERE alembic_version.version_num = '0018_fk_supporting_indexes';

COMMIT;

