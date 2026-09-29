# 腾讯云CVM实例
resource "tencentcloud_instance" "web_server" {
  instance_name              = "ance-web-server"
  availability_zone          = "${var.region}-3"
  image_id                   = "img-22trbn9r"  # Ubuntu 22.04
  instance_type              = "S5.MEDIUM2"  # 2核4GB
  system_disk_type           = "CLOUD_PREMIUM"
  system_disk_size           = 50
  vpc_id                     = var.vpc_id
  subnet_id                  = var.subnet_id
  key_name                   = var.ssh_key_name
  internet_max_bandwidth_out = 100
  charge_type                = "POSTPAID_BY_HOUR"

  tags = {
    managed_by = "ANCE"
    pattern    = "ai-native-ops"
  }
}
