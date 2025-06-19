#!/usr/bin/python3
import configparser
import time
from datetime import datetime
import msal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import requests

#PATH TO FILE WITH SETTINGS
file_path = "settings.ini"

def read_options():
    config = configparser.ConfigParser()
    config.read(file_path)
    options = {}
    for section in config.sections():
        options[section] = {key: value for key, value in config.items(section)}
    return options

#get_option_value("Settings", "kswurl")
def get_option_value(section, key):
    options = read_options()
    return options.get(section, {}).get(key, None)

def get_ksw_events():
    URL = get_option_value("Settings", "kswurl")

    #USE LOCAL WEBDRIVER-CHROME
    # options = Options()
    # options.add_argument("--headless")
    # options.add_argument("--user-data-dir=/tmp/user-data")
    # options.add_argument("--no-sandbox")
    # driver = webdriver.Chrome(options=options)
    # driver = webdriver.Chrome()

    #USER REMOTE WEBDRIVER-CHROME
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Remote(command_executor=get_option_value("Settings", "selenium_remote_address"), options=options)

    driver.get(URL)
    time.sleep(2)

    article = driver.find_elements(By.TAG_NAME,"article")

    ksw_events = []
    for event in article:
        eventTemp = event.text.splitlines()

        event_date = datetime.strptime(eventTemp[0],'%Y-%m-%d %H:%M:%S').strftime("%d-%m-%Y")
        event_time = datetime.strptime(eventTemp[0],'%Y-%m-%d %H:%M:%S').strftime("%H:%M:%S")
        # print(event_date)
        # print(event_time)

        event_location = eventTemp[1]
        # print(event_location)

        event_name = eventTemp[2]
        # print(event_name)

        recordTemp= ','.join([event_name, event_date, event_time, event_location])
        ksw_events.append(recordTemp)

    # print(ksw_events)
    driver.quit()
    return ksw_events

def save_records(object):
    print(object)
    current_dateTime = "Last File Update: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"\n"
    with open(get_option_value("Settings","resultfile"), "w") as file:
        file.write(current_dateTime)
        file.write("\n".join(object))

def compare_records(object):
    try:
        with open(get_option_value("Settings","resultfile"), 'r') as file:
            next(file)
            file_content = file.read().splitlines()
        if(file_content == object):
            return True
        else:
            return False
    except FileNotFoundError:
        return False

def sendingNotification_smtp(ksw_events):
    SMTP_SERVER = get_option_value("Settings", "smtpserver")
    SMTP_USERNAME = get_option_value("Settings", "smtpusername")
    SMTP_PASSWORD = get_option_value("Settings", "smtppassword")
######

    msg = MIMEMultipart()
    msg['From'] = get_option_value("Settings", "smtpfrom")
    msg['To'] = get_option_value("Settings", "smtpto")
    msg['Subject'] = f"KSW ALERT 🚨 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    TEXT = f"NOWY EVENT SIE POKAZAL NA STRONIE \n strona: {get_option_value('Settings', 'kswurl')} \n Nowe dostepne bilety: \n " + "\n".join(ksw_events)


    msg.attach(MIMEText(TEXT, 'plain'))
    server = smtplib.SMTP(SMTP_SERVER)
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.quit()

def sendingNotification_graph(ksw_events):
    GRAPH_TENANT_ID = get_option_value("Settings", "graph_tenant_id")
    GRAPH_CLIENT_ID = get_option_value("Settings", "graph_client_id")
    GRAPH_SECRET_APP = get_option_value("Settings", "graph_secret")
    GRAPH_SHARED_MAILBOX = get_option_value("Settings", "graph_shared_mailbox")
    NOTIFY_USER = get_option_value("Settings", "notify_email")

    email_content = f"NOWY EVENT SIE POKAZAL NA STRONIE \n strona: {get_option_value('Settings', 'kswurl')} \n Nowe dostepne bilety: \n " + "\n".join(
        ksw_events)

    def acquire_token():
        authority_url = f'https://login.microsoftonline.com/{GRAPH_TENANT_ID}'
        app = msal.ConfidentialClientApplication(
            authority=authority_url,
            client_id=GRAPH_CLIENT_ID,
            client_credential=GRAPH_SECRET_APP
        )
        token = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        return token

    result = acquire_token()

    if "access_token" in result:
        print("✅ Access token acquired")
        access_token = result["access_token"]


        endpoint = f'https://graph.microsoft.com/v1.0/users/{GRAPH_SHARED_MAILBOX}/sendMail'

        email_msg = {
            'message': {
                'subject': f"KSW ALERT 🚨 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                'body': {
                    'contentType': 'Text',
                    'content': email_content
                },
                'toRecipients': [
                    {'emailAddress': {'address': NOTIFY_USER}}
                ]
            },
            'saveToSentItems': 'true'
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(endpoint, headers=headers, json=email_msg)
        if response.ok:
            print('✅ Sent email successfully')
        else:
            print('❌ Błąd:', response.status_code, response.json())

    else:
        print("❌ Błąd autoryzacji:", result.get("error_description"))

def save_date_time_of_run():
    current_dateTime = "Last File Update: "+datetime.now().strftime('%Y-%m-%d %H:%M:%S')+"\n"
    with open(get_option_value("Settings","lastrunfile"), 'w') as file:
        file.write(current_dateTime)

def main():
    save_date_time_of_run()
    ksw_events = get_ksw_events()
    if(compare_records(ksw_events)):
        print("Values are the same. Skipping...")
    else:
        print("Something changed. Saving new file and sending info.")
        save_records(ksw_events)
        if(get_option_value("Settings", "use_smtp_to_send_email") == "yes"):
            sendingNotification_smtp(ksw_events)
        if (get_option_value("Settings", "use_graph_to_send_email") == "yes"):
            sendingNotification_graph(ksw_events)




if __name__ == "__main__":
    main()
