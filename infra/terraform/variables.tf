variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "env" {
  description = "Environment name (staging | production)"
  type        = string
  default     = "staging"
}

variable "s3_bucket" {
  description = "S3 bucket name for document storage"
  type        = string
  default     = "your-company-documents"
}

variable "ecr_image_uri" {
  description = "ECR image URI for the backend container"
  type        = string
}

variable "jwt_secret" {
  description = "JWT signing secret — stored in Secrets Manager"
  type        = string
  sensitive   = true
}
