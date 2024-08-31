# FastStream Template

**Create a .env file based on .env.dist and make all the necessary customizations.**

### To run the application in a docker container, run the command:
`make docker` or `docker-compose up -d`

### To run the application without a docker container, complete follow these steps:
1. Install dependencies.

    `poetry install` or `pip install -r requirements.txt`
2. Run application.

   `make app` or `python -m app`

### Make documentation:
`make help`
