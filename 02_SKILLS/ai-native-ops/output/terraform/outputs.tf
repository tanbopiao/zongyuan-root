output "instance_id" {
  description = "实例ID"
  value       = tencentcloud_instance.web_server.id
}

output "public_ip" {
  description = "公网IP"
  value       = tencentcloud_instance.web_server.public_ip
}

output "private_ip" {
  description = "内网IP"
  value       = tencentcloud_instance.web_server.private_ip
}
