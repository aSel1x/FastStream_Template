# FastStream Template

**Create a .env file based on .env.dist and make all the necessary customizations.**
For docker and tests I recommend you create .env.docker and .env.tests files
and override here args like docker-host or tests-database.

### To run the application in a docker container, run the command:
`make docker` or `docker-compose up -d`

### To run the application without a docker container, complete follow these steps:
1. Install dependencies.

    `poetry install` or `pip install -r requirements.txt`
2. Run application.

   `make http` - to run HTTP;

   `make amqp` - to run AMQP;

   `make scheduler` - to run scheduler

### To run the application tests:
`make test`

### Make documentation:
`make help`
