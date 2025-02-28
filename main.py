import configparser
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

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
    driver = webdriver.Chrome()
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

def sendingNotification(ksw_events):
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


def main():
    ksw_events = get_ksw_events()
    if(compare_records(ksw_events)):
        print("Values are the same. Skipping...")
    else:
        print("Something changed. Saving new file and sending info.")
        save_records(ksw_events)
        sendingNotification(ksw_events)



if __name__ == "__main__":
    main()
