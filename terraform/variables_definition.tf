variable "project_name" {
  description = "Project name used for various configuration names"
  type        = string
}

variable "database_name" {
  description = "Name used for the main database"
  type        = string
  default     = "shiro"
}

variable "database_user" {
  description = "Name used for the main database user"
  type        = string
  default     = "shiro"
}
