# Bitmex orders


#### Description

This project provides its own API interface (REST + Websocket) for 
[Bitmex](https://www.bitmex.com/) account order management.


#### How to run locally

Install python, create virtual environment and install all the requirements:

    make setup

Install PostgreSQL:

    make install-psql

Create `bitmex_orders/.env` configuration file with custom settings. 

Here is an example of the `bitmex_orders/.env` file:

    DEBUG=True
    SECRET_KEY=Some secret key here
    DATABASE_URL=pgsql://user_name:user_password@localhost:5432/bitmex_orders

Run the project:

    make run

It will open your browser on http://127.0.0.1:8000/
