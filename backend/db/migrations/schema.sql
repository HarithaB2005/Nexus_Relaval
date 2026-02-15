
CREATE SCHEMA "public";
CREATE TABLE "api_keys" (
	"key_id" varchar(36) PRIMARY KEY,
	"client_id" varchar(255) NOT NULL,
	"api_key_hash" varchar(128) NOT NULL,
	"revoked" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE "billing_plans" (
	"id" serial PRIMARY KEY,
	"client_id" text NOT NULL,
	"plan_name" varchar(100) NOT NULL,
	"price_monthly" numeric(10, 2) DEFAULT '0.00',
	"billing_cycle_date" timestamp with time zone,
	"status" varchar(50) DEFAULT 'active',
	"is_vip" boolean DEFAULT false,
	"created_at" timestamp with time zone DEFAULT now()
);
CREATE TABLE "client_credentials" (
	"client_id" varchar(255) PRIMARY KEY,
	"api_key_hash" char(64) CONSTRAINT "client_credentials_api_key_hash_key" UNIQUE,
	"status" varchar(50) DEFAULT 'active' NOT NULL,
	"usage_limits" jsonb,
	"created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
	"last_access" timestamp,
	"password_salt" varchar(64),
	"password_hash" varchar(128),
	"client_email" varchar(255),
	"client_name" varchar(255),
	"email_verified" boolean DEFAULT false,
	"email_verification_token" varchar(128),
	"email_verification_expiry" timestamp with time zone,
	"email_verified_at" timestamp with time zone,
	"usage_count" integer DEFAULT 0,
	"plan_limit" integer DEFAULT 50,
	"is_admin" boolean DEFAULT false,
	"plan_type" varchar(50) DEFAULT 'normal',
	"updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
	"data_retention_mode" varchar(50) DEFAULT 'standard',
	"privacy_settings" jsonb DEFAULT '{"log_usage": true, "log_inputs": false, "log_outputs": false, "encryption_at_rest": true}',
	"local_inference_enabled" boolean DEFAULT false,
	"local_inference_api_url" varchar(500),
	"zero_data_retention_enabled" boolean DEFAULT false,
	"clarifier_count_last_5" integer DEFAULT 0,
	"last_5_request_types" jsonb DEFAULT '[]'
);
CREATE TABLE "data_retention_policies" (
	"policy_id" uuid PRIMARY KEY,
	"client_id" text NOT NULL,
	"policy_name" varchar(100) NOT NULL,
	"retention_days" integer DEFAULT 30,
	"applies_to" varchar(100) NOT NULL,
	"deletion_schedule" varchar(50) DEFAULT 'immediate',
	"is_active" boolean DEFAULT true,
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
CREATE TABLE "governance_audit_events" (
	"event_id" uuid PRIMARY KEY,
	"client_id" text NOT NULL,
	"event_type" varchar(50) NOT NULL,
	"severity" varchar(20) NOT NULL,
	"reason" text NOT NULL,
	"input_preview" text,
	"output_preview" text,
	"metric_value" numeric(10, 4),
	"metric_name" varchar(100),
	"created_at" timestamp with time zone DEFAULT now(),
	"created_date" date DEFAULT CURRENT_DATE
);
CREATE TABLE "governance_saved_errors" (
	"error_id" uuid PRIMARY KEY,
	"client_id" text NOT NULL,
	"error_category" varchar(100) NOT NULL,
	"error_description" text NOT NULL,
	"impact_level" varchar(20),
	"times_blocked" integer DEFAULT 1,
	"first_detected" timestamp with time zone DEFAULT now(),
	"last_detected" timestamp with time zone DEFAULT now()
);
CREATE TABLE "governance_summary" (
	"summary_id" serial PRIMARY KEY,
	"client_id" text NOT NULL UNIQUE,
	"summary_date" date DEFAULT CURRENT_DATE NOT NULL UNIQUE,
	"total_requests" integer DEFAULT 0,
	"total_rejections" integer DEFAULT 0,
	"hallucinations_blocked" integer DEFAULT 0,
	"quality_issues_found" integer DEFAULT 0,
	"safety_violations_detected" integer DEFAULT 0,
	"avg_quality_score" numeric(5, 3),
	"risk_score" numeric(5, 3),
	CONSTRAINT "governance_summary_client_id_summary_date_key" UNIQUE("client_id","summary_date")
);
CREATE TABLE "invoices" (
	"invoice_id" varchar(100) PRIMARY KEY,
	"client_id" text NOT NULL,
	"invoice_date" date NOT NULL,
	"amount_usd" numeric(10, 2) NOT NULL,
	"status" varchar(50) DEFAULT 'pending',
	"pdf_url" text,
	"created_at" timestamp with time zone DEFAULT now()
);
CREATE TABLE "local_inference_deployments" (
	"deployment_id" uuid PRIMARY KEY,
	"client_id" text NOT NULL,
	"deployment_name" varchar(255) NOT NULL,
	"deployment_url" varchar(500) NOT NULL,
	"api_key_hash" varchar(64),
	"status" varchar(50) DEFAULT 'active',
	"last_healthcheck" timestamp with time zone,
	"healthcheck_status" varchar(20) DEFAULT 'unknown',
	"created_at" timestamp with time zone DEFAULT now(),
	"updated_at" timestamp with time zone DEFAULT now()
);
CREATE TABLE "magic_links" (
	"token" varchar(128) PRIMARY KEY,
	"client_id" varchar(255) NOT NULL,
	"expires_at" timestamp NOT NULL,
	"used" boolean DEFAULT false,
	"created_at" timestamp DEFAULT now()
);
CREATE TABLE "request_processing_log" (
	"log_id" uuid PRIMARY KEY,
	"client_id" text NOT NULL,
	"request_id" uuid,
	"processing_mode" varchar(50) NOT NULL,
	"processed_at" timestamp with time zone DEFAULT now(),
	"data_retained" boolean,
	"retention_days" integer
);
CREATE TABLE "usage_events" (
	"id" bigserial PRIMARY KEY,
	"client_id" text NOT NULL,
	"event_type" varchar(50) NOT NULL,
	"requests" integer DEFAULT 1,
	"tokens" bigint DEFAULT 0,
	"cost" numeric(12, 4) DEFAULT '0',
	"created_at" timestamp DEFAULT now()
);
CREATE TABLE "usage_tracking" (
	"id" serial PRIMARY KEY,
	"client_id" text NOT NULL,
	"requests_count" integer DEFAULT 0,
	"tokens_count" integer DEFAULT 0,
	"cost_usd" numeric(10, 4) DEFAULT '0.0000',
	"created_at" timestamp with time zone DEFAULT now(),
	"silent_misalignment" boolean DEFAULT false,
	"decision_trace" jsonb DEFAULT '[]',
	"risk_tier" varchar(20),
	"provider_used" varchar(100),
	"rejection_score" numeric(5, 3) DEFAULT '0.0',
	"clarifier_score" numeric(5, 3) DEFAULT '0.0',
	"accumulated_tokens" bigint DEFAULT 0,
	"accumulated_cost_estimate" numeric(10, 6) DEFAULT '0.0',
	"per_iteration_token_estimate" jsonb DEFAULT '[]',
	"error_type" varchar(100),
	"error_stage" varchar(100),
	"request_id" varchar(64)
);
CREATE UNIQUE INDEX "api_keys_pkey" ON "api_keys" ("key_id");
CREATE INDEX "idx_api_key_hash" ON "api_keys" ("api_key_hash");
CREATE UNIQUE INDEX "billing_plans_pkey" ON "billing_plans" ("id");
CREATE INDEX "idx_billing_plans_client" ON "billing_plans" ("client_id","status");
CREATE UNIQUE INDEX "client_credentials_api_key_hash_key" ON "client_credentials" ("api_key_hash");
CREATE UNIQUE INDEX "client_credentials_pkey" ON "client_credentials" ("client_id");
CREATE INDEX "idx_client_email" ON "client_credentials" ("client_email");
CREATE INDEX "idx_usage_limits" ON "client_credentials" USING gin ("usage_limits");
CREATE UNIQUE INDEX "data_retention_policies_pkey" ON "data_retention_policies" ("policy_id");
CREATE INDEX "idx_data_retention_active" ON "data_retention_policies" ("client_id","is_active");
CREATE UNIQUE INDEX "governance_audit_events_pkey" ON "governance_audit_events" ("event_id");
CREATE INDEX "idx_governance_audit_client_date" ON "governance_audit_events" ("client_id","created_at");
CREATE UNIQUE INDEX "governance_saved_errors_pkey" ON "governance_saved_errors" ("error_id");
CREATE INDEX "idx_saved_errors_client" ON "governance_saved_errors" ("client_id");
CREATE UNIQUE INDEX "governance_summary_client_id_summary_date_key" ON "governance_summary" ("client_id","summary_date");
CREATE UNIQUE INDEX "governance_summary_pkey" ON "governance_summary" ("summary_id");
CREATE INDEX "idx_invoices_client_date" ON "invoices" ("client_id","invoice_date");
CREATE UNIQUE INDEX "invoices_pkey" ON "invoices" ("invoice_id");
CREATE INDEX "idx_local_inference_status" ON "local_inference_deployments" ("client_id","status");
CREATE UNIQUE INDEX "local_inference_deployments_pkey" ON "local_inference_deployments" ("deployment_id");
CREATE UNIQUE INDEX "magic_links_pkey" ON "magic_links" ("token");
CREATE INDEX "idx_processing_log_client_date" ON "request_processing_log" ("client_id","processed_at");
CREATE UNIQUE INDEX "request_processing_log_pkey" ON "request_processing_log" ("log_id");
CREATE INDEX "idx_usage_client_created" ON "usage_events" ("client_id","created_at");
CREATE UNIQUE INDEX "usage_events_pkey" ON "usage_events" ("id");
CREATE INDEX "idx_usage_tracking_client_date" ON "usage_tracking" ("client_id","created_at");
CREATE UNIQUE INDEX "usage_tracking_pkey" ON "usage_tracking" ("id");