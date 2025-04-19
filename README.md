# cs467-scp-project
A Synchronous Communication Platform Project


##  How  to run this project
### Connect to Michael Shaffer's MongoDB
**userid** is **discord name** and ***password*** is ***CS467***

`mongodb://userid:password@209.46.124.94:27017/`

to change password:

`mongosh -u userid -p password --authenticationDatabase scp-db`

`db.updateUser("userid", { pwd: "newpassword" })`

Use MongoDB Compass for connecting

database name is `scp-db`


### Start local instance of Frontend

`cd client`

`npm install`

`npm run dev`

### Socket.IO setup

Install socket.io in express

`cd socket-server`

`npm install socket.io socket.io-client`

### FastAPI setup

`cd fastapi-backend`

`python3 -m venv venv`

`source venv/bin/activate`

or

`./venv/Scripts/activate`

or

`source ./venv/Scripts/activate`

`pip install -r requirements.txt`

`uvicorn app.main:app --reload --port 8000`


###  Install Postgre SQL

`npm install pg`


## Project Architecture

sycolibre/			
│			
├── client/                 ***React frontend***			
│   ├── public/			
│   ├── src/			
│   ├── package.json        ***React scripts***			
│   └── ...			
│			
├── socket-server/          ***Socket.IO Node.js server***			
│   ├── index.js			
│   ├── package.json			
│   └── ...			
│			
├── fastapi-backend/        ***Python FastAPI backend***			
│   ├── app/			
│   │   ├── main.py			
│   │   ├── routes/			
│   │   └── ...			
│   ├── requirements.txt			
│   └── ...			
│			
├── .gitignore			
├── README.md			
└── docker-compose.yml      ***Optional if you're containerizing***			