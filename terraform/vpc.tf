resource "aws_vpc" "main" {
  assign_generated_ipv6_cidr_block  = false
  cidr_block                        = "10.10.0.0/16"
  enable_dns_support                = true

  tags = {
    Name = var.project_name
  }
}

resource "aws_subnet" "private_1" {
  vpc_id                          = aws_vpc.main.id
  assign_ipv6_address_on_creation = false
  availability_zone               = "sa-east-1c"
  cidr_block                      = "10.10.1.0/24"

  tags = {
    Name = "${var.project_name}-private-1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id                          = aws_vpc.main.id
  assign_ipv6_address_on_creation = false
  availability_zone               = "sa-east-1a"
  cidr_block                      = "10.10.2.0/24"

  tags = {
    Name = "${var.project_name}-private-2"
  }
}

resource "aws_subnet" "public" {
  vpc_id                          = aws_vpc.main.id
  assign_ipv6_address_on_creation = false
  availability_zone               = "sa-east-1c"
  cidr_block                      = "10.10.3.0/24"

  tags = {
    Name = "${var.project_name}-public"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = var.project_name
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-public"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block  = "0.0.0.0/0"
    instance_id = aws_instance.nat.id
  }

  tags = {
    Name = "${var.project_name}-private"
  }
}
