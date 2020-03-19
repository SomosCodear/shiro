resource "aws_security_group" "nat_sg" {
  name    = "${var.project_name}-nat-sg"
  vpc_id  = aws_vpc.main.id

  egress {
    cidr_blocks = ["0.0.0.0/0"]
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
  }
  ingress {
    cidr_blocks       = ["0.0.0.0/0"]
    ipv6_cidr_blocks  = ["::/0"]
    from_port         = 22
    to_port           = 22
    protocol          = "tcp"
  }
  ingress {
    cidr_blocks   = [aws_vpc.main.cidr_block]
    description   = "NAT traffic"
    from_port     = 0
    to_port       = 0
    protocol      = "-1"
  }
}

resource "aws_instance" "nat" {
  ami                           = data.aws_ami.default.id
  instance_type                 = "t3a.nano"
  key_name                      = aws_key_pair.main.key_name
  associate_public_ip_address   = true
  ebs_optimized                 = true
  source_dest_check             = false
  vpc_security_group_ids        = [aws_security_group.nat_sg.id]

  tags = {
    Name = "${var.project_name}-nat"
  }

  volume_tags = {
    Name = "${var.project_name}-nat"
  }

  provisioner "remote-exec" {
    inline = [
      "sysctl -w net.ipv4.ip_forward=1",
      "/sbin/iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE",
    ]
  }
}
