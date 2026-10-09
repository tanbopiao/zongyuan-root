variable "region" {
  description = "云区域"
  type        = string
  default     = "ap-guangzhou"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "子网ID"
  type        = string
  default     = ""
}

variable "ssh_key_name" {
  description = "SSH密钥名称"
  type        = string
  default     = "ance-deploy-key"
}

variable "tencent_secret_id" {
  description = "腾讯云SecretId"
  type        = string
  sensitive   = true
}

variable "tencent_secret_key" {
  description = "腾讯云SecretKey"
  type        = string
  sensitive   = true
}
