# Shiro - WebConf Checkout API

## Local development
To setup the application you will need:
- Python 3.7 (pyenv recommended)
- pipenv
- docker & docker-compose (optional)

For the initial setup, follow these steps:
- Clone the repository
  ```
    git clone git@github.com:SomosCodear/shiro.git
  ```
- Move to the directory, start a pipenv venv and install the project's dependencies
  ```
    cd shiro
    pipenv --python 3.7
    pipenv install
  ```
- Copy the `.env-example` file to `.env` and replace the info if necessary. If you're going to be
  using docker-compose then you probably don't need to change anything there; if you plan on setting
  up services on your own instead, you will have to configure these variables accordingly.
- Start the docker-compose services (only postgresql for now)
  ```
    docker-compose up
  ```
- Migrate the project's database
  ```
    pipenv run src/manage.py migrate
  ```
- Create cache table
  ```
    pipenv run src/manage.py createcachetable
  ```
- Create yourself a superuser
  ```
    pipenv run src/manage.py createsuperuser
  ```
- And run the project
  ```
    pipenv run src/manage.py runserver
  ```
- You should be able to access the application at `localhost:8000`. You should be able to access the
  admin site at `/admin`, the navigable API at `/api` and the swagger API reference at `/api/swagger`
