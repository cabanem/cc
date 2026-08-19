project_id                     = "rsr-rpa-ai-prd-f1cb"
region                         = "us-central1"
existing_service_account_email = "invoice-idp@rsr-rpa-ai-prd-f1cb.iam.gserviceaccount.com"

# Pin this to a real version tag once you push one (you set up AR with versioning)
image_tag = "latest"

model           = "gemini-2.5-pro"
vertex_location = "global"

# Uncomment and fill in to scope the dump to the SDC folder:
# sdc_folder_id = "YOUR_WORKATO_FOLDER_ID"

# Who may call the API service (needed even with INGRESS_TRAFFIC_ALL —
# Cloud Run still authenticates callers):
# api_invoker_members = ["user:you@randstadsourceright.com"]
