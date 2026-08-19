# ---------------------------------------------------------
# Cloud Run Job (Pipeline)
# ---------------------------------------------------------
resource "google_cloud_run_v2_job" "pipeline" {
  name     = "workato-agent-pipeline-job"
  location = var.region

  template {
    template {
      service_account = var.existing_service_account_email
      timeout         = "1200s" # ~58 recipes at 0.5s pacing + BQ loads: minutes, not the 10m default edge

      containers {
        image = local.agent_image

        # The Dockerfile CMD is uvicorn (a server that never exits) — a Job
        # inheriting it would hang until timeout. Override with the pipeline.
        command = ["bash", "scripts/run_pipeline.sh"]

        # Name matches what dumps.py actually reads: WORKATO_API_TOKEN
        # (the secret RESOURCE keeps its WORKATO_AGENT_API_TOKEN name).
        env {
          name = "WORKATO_API_TOKEN"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.api_token.secret_id
              version = "latest"
            }
          }
        }
        env {
          name  = "GCS_BUCKET"
          value = google_storage_bucket.dumps.name
        }
        env {
          name  = "SDC_DUMP_DIR"
          value = "dumps"
        }
        env {
          name  = "BIGQUERY_DATASET"
          value = google_bigquery_dataset.store.dataset_id
        }
        env {
          name  = "SDC_FOLDER_ID"
          value = var.sdc_folder_id # empty string is treated as unset by dumps.py
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# ---------------------------------------------------------
# Scheduler SA IAM Binding & Cloud Scheduler Job
# ---------------------------------------------------------
resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  project  = google_cloud_run_v2_job.pipeline.project
  location = google_cloud_run_v2_job.pipeline.location
  name     = google_cloud_run_v2_job.pipeline.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "daily_dump" {
  name        = "daily-workato-agent-dump"
  description = "Triggers the Workato Agent Pipeline Job daily"
  schedule    = "0 2 * * *"
  time_zone   = "UTC"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.pipeline.name}:run"

    # OAuth token: required for the Cloud Run management API
    # (OIDC is for direct service-to-service invocation).
    oauth_token {
      service_account_email = google_service_account.scheduler.email
      scope                 = "https://www.googleapis.com/auth/cloud-platform"
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_job_iam_member.scheduler_invoker
  ]
}

# ---------------------------------------------------------
# Cloud Run Service (Agent API)
# ---------------------------------------------------------
resource "google_cloud_run_v2_service" "api" {
  name                = "workato-agent-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    # Same identity as the pipeline. Consequence worth knowing: this SA
    # holds dataEditor, so the IAM layer does not enforce read-only for
    # model-authored SQL — corpus.py's SELECT-only + single-statement
    # guard is the fence. Revisit with a read-only SA if/when org
    # process allows a project-level jobUser grant on a new identity.
    service_account = var.existing_service_account_email

    containers {
      image = local.agent_image

      # agent.py hard-requires MODEL and GOOGLE_CLOUD_PROJECT. Cloud Run
      # does NOT inject GOOGLE_CLOUD_PROJECT automatically (Functions does).
      env {
        name  = "MODEL"
        value = var.model
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "LOCATION"
        value = var.vertex_location
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = google_bigquery_dataset.store.dataset_id
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# INGRESS_TRAFFIC_ALL exposes the URL but Cloud Run still authenticates —
# without an invoker binding every caller gets 403. Grant yourself here,
# then call with: curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" ...
resource "google_cloud_run_v2_service_iam_member" "api_invokers" {
  for_each = toset(var.api_invoker_members)
  project  = google_cloud_run_v2_service.api.project
  location = google_cloud_run_v2_service.api.location
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = each.value
}
