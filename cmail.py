mail_password='nwwu uojk ttim ojyt'
import smtplib
from email.message import EmailMessage
def send_mail(to,subject,body):
    server=smtplib.SMTP_SSL('smtp.gmail.com',465)
    server.login('vennelapasumarthi7@gmail.com',mail_password)
    msg=EmailMessage()
    msg['FROM']='vennelapasumarthi7gmail.com'
    msg['TO']=to
    msg['SUBJECT']=subject
    msg.set_content(body)
    server.send_message(msg)
    print('msg sent')
    server.close()
