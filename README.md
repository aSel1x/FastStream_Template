# FastStream Template

**Create a .env file based on .env.dist and make all the necessary customizations.**

### To run the application in a docker container, run the command:
`make docker` or `docker-compose up -d`

### To run the tests of application in a docker container, run the command:
`make docker-tests` or `docker-compose -f docker-compose-tests.yaml up --exit-code-from tests`

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
