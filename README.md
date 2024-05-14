# VPN Server Management
This project is made for automating process of replacing vpn servers using 99stack APIs
https://api.99stack.com/docs/v1.3/

## Installing Requirements
For installing requirements of project run the following command:
```
pip install -r requirements.txt
```

## Running the Project
Make a .env file based on .env.template file enter your credentials in it and run the ```run()``` function that exists in ```core.py``` file:
```
def run():
    
    schedule.every(CHECK_WAIT).minutes.do(check_routine)

    # Main loop
    while True:
        schedule.run_pending()
        sleep(RUN_PENDING_WAIT)
```
- Connecting to VPN servers has been done using SSH keys. Your private key should exist in the PK_PATH directory. (PK_PATH is the variable specified in the .env file.)
