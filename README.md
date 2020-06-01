# Bitmex orders


### Description

This project provides its own API interface (REST + Websocket) for 
[Bitmex](https://www.bitmex.com/) account orders management.


### How to run locally

1. Install python, create virtual environment and install all the requirements:

        $ make setup

1. Install PostgreSQL:

        $ make install-psql

1. Create `bitmex_orders/.env` configuration file with custom settings. 

    Here is an example of the `bitmex_orders/.env` file:
    
        DEBUG=True
        SECRET_KEY=Some secret key here
        DATABASE_URL=pgsql://user_name:user_password@localhost:5432/bitmex_orders

1. Create new account in the DB.

2. Run the project:

        $ make run

    It will open your browser on http://localhost:8000/orders/


### How to run tests

Run the tests:

    $ make test

Check the coverage:

    $ make test-cov


### Usage Examples

* REST API usage

    Get all orders for an account:

        $ curl -X GET -i 'http://localhost:8000/orders/?account=<account name>'
        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept, Cookie
        Allow: GET, POST, HEAD, OPTIONS
        X-Frame-Options: DENY
        Content-Length: 150
        X-Content-Type-Options: nosniff
        
        [{"id":1,"order_id":"123-123-123","symbol":"XBTUSD","volume":1,"timestamp":"2020-05-30T09:01:34.389289Z","side":"Buy","price":123.0,"account":"test"}]

    Create new order for an account:

        $ curl -X POST -i 'http://localhost:8000/orders/?account=<account name>' -H 'Content-Type: application/json' -d '{"symbol": "XBTUSD", "volume": 1, "side": "Buy"}'
        HTTP/1.1 400 Bad Request
        Content-Type: application/json
        Vary: Accept, Cookie
        Allow: GET, POST, HEAD, OPTIONS
        X-Frame-Options: DENY
        Content-Length: 142
        X-Content-Type-Options: nosniff
        
        {"error":"400 Bad Request: {'error': {'message': 'Account has insufficient Available Balance, 120 XBt required', 'name': 'ValidationError'}}"}

    Show order info for an account:

        $ curl -X GET -i 'http://localhost:8000/orders/<order id>/?account=<account name>'
        HTTP/1.1 200 OK
        Content-Type: application/json
        Vary: Accept, Cookie
        Allow: GET, DELETE, HEAD, OPTIONS
        X-Frame-Options: DENY
        Content-Length: 720
        X-Content-Type-Options: nosniff
        
        [{"orderID":"dfb933b9-722f-5c31-ad32-356718319540","clOrdID":"","clOrdLinkID":"","account":209905,"symbol":"XBTUSD","side":"Buy","simpleOrderQty":null,"orderQty":1,"price":8391.0,"displayQty":null,"stopPx":null,"pegOffsetValue":null,"pegPriceType":"","currency":"USD","settlCurrency":"XBt","ordType":"Market","timeInForce":"ImmediateOrCancel","execInst":"","contingencyType":"","exDestination":"XBME","ordStatus":"Filled","triggered":"","workingIndicator":false,"ordRejReason":"","simpleLeavesQty":null,"leavesQty":0,"simpleCumQty":null,"cumQty":1,"avgPx":8390.5,"multiLegReportingType":"SingleSecurity","text":"Submitted via API.","transactTime":"2019-05-31T11:12:27.972000Z","timestamp":"2019-05-31T11:12:27.972000Z"}]

    Remove/Cancel order for an account: 

        $ curl -X DELETE -i 'http://localhost:8000/orders/<order id>/?account=<account name>'
        TTP/1.1 404 Not Found
        Content-Type: application/json
        Vary: Accept, Cookie
        Allow: GET, DELETE, HEAD, OPTIONS
        X-Frame-Options: DENY
        Content-Length: 83
        X-Content-Type-Options: nosniff
        
        {"error":"404 Not Found: {'error': {'message': 'Not Found', 'name': 'HTTPError'}}"}

* Websocket usage

    Open websocket client

        $ make run-ws-client

    Subscribe to a Bitmex instrument topic:

        > {"action": "subscribe", "account": "<account name>"}

        < {"success": true, "subscribe": "instrument", "account": "<account name>"}
        < {"timestamp": "2020-06-01T16:30:00.000Z", "account": "<account name>", "symbol": ".EVOL7D", "price": 5.48}
        < ...

    Unsubscribe from a Bitmex instrument topic:

        > {"action": "unsubscribe", "account": "<account name>"}
        
        < {"success": true, "unsubscribe": "instrument", "account": "<account name>"}
