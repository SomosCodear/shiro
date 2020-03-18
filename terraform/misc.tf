data "aws_ami" "default" {
  most_recent = true

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-2.0*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["amazon"]
}

resource "aws_key_pair" "main" {
  key_name   = "agustin-keys"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCppPM3mPdtojOvzeuXtdWKPsOFJUemIYO6/dzk0sBEj4gbyaTtnBJeNHr4TYXlLjeOJaCJ7Tb7ztDt5uOwBgn+QmWfevkaJri5pRGAvQKnRhlax4Iiux2L6W6t4hxejHXSOOGxU3y0kqFBa6Pk1wJ6Sm5EehBS6rJ/kg0LGZOdOob8XTNRGFp5xGFLXEclt6DWt/gmqX9qCK+mUOBZ2wYhcDuj7O/sr4HylU36oqxgWQIXwWYGSB4yQGViJehFBC3KVYNRmvuNQ1TyL1BEV257sAhECKTGXGmAhZZndrAObR/NwoWjqluIV3tF2oF1q7K6dWawBwMc2qfD1LN79717"
}
