import emailIntegrationTest


def main():
    sender_email = 'springfields.e704@gmail.com'
    sender_name = 'Deepak Kumar'
    to_email = 'kdeepu@gmail.com'
    # to_name = 'Deepak Kumar'
    # replyTo_name = 'Deepak Kumar'
    # replyTo_email = 'springfields.e704@gmail.com'
    mail_subject = 'Stock Alert'
    mail_body = 'Consider Selling now'

    mail_response = emailIntegrationTest.Send(mail_subject, sender_email, sender_name, to_email, mail_body, mail_body, True)
    print(mail_response)
    return


if __name__ == '__main__':
 main()
