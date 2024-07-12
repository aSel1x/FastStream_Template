# FastStream Template

**Create a .env file based on .env.dist and make all the necessary customizations.**

### To run the application in a docker container, run the command:
`docker-compose up -d` or `make docker`

### To run the application without a docker container, complete follow these steps:
1. Install dependencies.

    `poetry install` or `pip install -r requirements.txt`
2. Run application.

    `make run`

### To run the HTTP and AMQP separately, use follow commands:

`make http` and `make amqp`

### Make documentation:
`make help`
