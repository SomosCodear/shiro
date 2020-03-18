resource "aws_db_subnet_group" "default" {
  name        = "${var.project_name}-database-subnet-group"
  description = "Webconf 2020 Database Subnet Group"
  subnet_ids  = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

resource "aws_db_instance" "main" {
  identifier                    = "${var.project_name}-${terraform.workspace}"
  db_subnet_group_name          = aws_db_subnet_group.default.name
  instance_class                = "db.t2.micro"
  engine                        = "postgres"
  engine_version                = "11"
  name                          = var.database_name
  username                      = var.database_user
  allocated_storage             = 20
  max_allocated_storage         = 100
  backup_retention_period       = 7
  copy_tags_to_snapshot         = true
  performance_insights_enabled  = true
  skip_final_snapshot           = true
}
