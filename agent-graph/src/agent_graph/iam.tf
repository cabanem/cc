# ---------------------------------------------------------
# Service Accounts
# ---------------------------------------------------------
# Runtime identity for both the pipeline job and the API service is the
# EXISTING service account (var.existing_service_account_email). Its
# project-level BigQuery access (bigquery.jobs.create + data roles) is
# provisioned outside this stack — Terraform here adds only the
# resource-level grants that this stack's own resources introduce.
#
# The one identity this stack does own: the scheduler SA, which can do
# exactly one thing — execute the pipeline job (binding in compute.tf).

resource "google_service_account" "scheduler" {
  account_id   = "sa-workato-agent-sched"
  display_name = "Workato Agent Scheduler SA"
  depends_on   = [google_project_service.apis]
}

# ---------------------------------------------------------
# Resource-Level IAM Bindings (Existing Service Account)
# ---------------------------------------------------------
# Strict access: Only allowed to read the specific token secret
resource "google_secret_manager_secret_iam_member" "secret_accessor" {
  secret_id = google_secret_manager_secret.api_token.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.existing_service_account_email}"
}

# Strict access: Only allowed object admin on the dumps bucket
resource "google_storage_bucket_iam_member" "bucket_admin" {
  bucket = google_storage_bucket.dumps.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.existing_service_account_email}"
}

# Strict access: Allowed to edit (and view) data within the target dataset.
# Kept even if project-level roles already cover it — it makes this
# stack's dependency on the dataset explicit and survives any future
# tightening of the project-level grants.
resource "google_bigquery_dataset_iam_member" "bq_editor" {
  dataset_id = google_bigquery_dataset.store.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${var.existing_service_account_email}"
}

# NOTE (not managed here): the agent also calls Vertex AI
# (google-genai with vertexai=True), which requires roles/aiplatform.user
# or equivalent on the project. If the existing SA gained Vertex access
# through its original workload you're covered; DEPLOY.md has the
# one-liner to verify before first /ask.
