terraform {
  required_providers {
    tencentcloud = {
      source  = "tencentcloudstack/tencentcloud"
      version = ">= 1.81.0"
    }
  }
}

provider "tencentcloud" {
  secret_id  = var.tencent_secret_id
  secret_key = var.tencent_secret_key
  region     = var.region
}
