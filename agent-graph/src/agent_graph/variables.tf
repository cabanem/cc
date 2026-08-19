variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The default region for deploying resources"
  type        = string
  default     = "us-central1"
}

variable "existing_service_account_email" {
  description = "Existing service account used as the runtime identity for both the Cloud Run Job and the API service. Assumed to already hold project-level BigQuery access (jobs.create + data roles) managed outside this stack; this stack adds only resource-level grants."
  type        = string
}

variable "image_tag" {
  description = "Tag of the workato-app image in Artifact Registry (pin a version tag for reproducible deploys; 'latest' for convenience)"
  type        = string
  default     = "latest"
}

variable "model" {
  description = "Vertex AI Gemini model id used by the agent"
  type        = string
  default     = "gemini-2.5-pro"
}

variable "vertex_location" {
  description = "Vertex AI location for the genai client ('global' works for Gemini 2.x)"
  type        = string
  default     = "global"
}

variable "sdc_folder_id" {
  description = "Workato folder_id scoping the recipe dump (empty = dump everything visible to the token)"
  type        = string
  default     = ""
}

variable "api_invoker_members" {
  description = "Principals allowed to invoke the agent API, e.g. [\"user:emily@example.com\"]. Empty list = nobody (deploy-then-decide)."
  type        = list(string)
  default     = []
}
