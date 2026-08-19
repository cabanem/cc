output "agent_api_url" {
  description = "The URL of the deployed Agent API Cloud Run service"
  value       = google_cloud_run_v2_service.api.uri
}

output "dumps_bucket_name" {
  description = "The name of the GCS bucket for data ingestion"
  value       = google_storage_bucket.dumps.name
}

output "bigquery_dataset_id" {
  description = "The ID of the BigQuery dataset"
  value       = google_bigquery_dataset.store.dataset_id
}

output "pipeline_job_name" {
  description = "The name of the Cloud Run Job"
  value       = google_cloud_run_v2_job.pipeline.name
}

output "agent_image" {
  description = "Fully qualified image reference both compute resources deploy"
  value       = local.agent_image
}

output "runtime_service_account" {
  description = "Identity both the pipeline job and the API service run as"
  value       = var.existing_service_account_email
}
