#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
#
# Created on    Fri 29 May 2020 22:53:53 CEST
#
# project       http://t.me/ScanYourPdf_bot
# author(s)     Francesco Urbani
#
# file          bot.py
# version       
#
# descritpion   launch ngrok first: ngrok http 5000
#
#
# ===============================================================

import os
import sys
import time
import datetime
import logging
import telebot
import flask
import enum
import requests



from database import Database


env = os.getenv('ENV')

if env == "PRODUCTION":
    try:
        TOKEN           = os.getenv('TOKEN')
        MYTELEGRAMID    = int(os.getenv('MY_TELEGRAM_ID_2'))
        DATABASE_URL    = os.getenv('DATABASE_URL')
        WEBHOOK_URL     = os.getenv('WEBHOOK_URL')
    except Exception as e:
        print("[!] Setup your environment variables!")

else:
    import data
    TOKEN           = data.TOKEN
    MYTELEGRAMID    = data.MYTELEGRAMID
    DATABASE_URL    = data.DATABASE_URL
    try:
        WEBHOOK_URL = sys.argv[1]  #data.WEBHOOK_URL
        if WEBHOOK_URL[-1] != "/": WEBHOOK_URL += "/"
    except Exception as e:
        print("pass webhook url as argv[1]")
        exit(-1)



bot = telebot.TeleBot(token=TOKEN)        


INIT_DATABASE_COMMAND = './sql/init.sql'

FOLDER_RECEIVED_PDFS = "download"



def send_start_message(chat_id):
    # bot.send_message(chat_id, "Hey, welcome!\nSend me a PDF and I'll send you back a scanned-looking version of it.\nWrite /options to choose between b/w scan and rgb scan.")
    bot.send_message(chat_id, "Hey, welcome!\nSend me a PDF and I'll send you back a scanned-looking version of it.\nIf you type #feedback inside your message it will be forwarded to the author.")



@bot.message_handler(content_types=['text', 'photo', 'sticker', 'voice', 'video', 'video_note', 'document', 'contact', 'location'])
def on_chat_message(message):

    content_type  = message.content_type
    chat_id       = message.chat.id
    
    print(content_type)
    

    if content_type == "text":
        if message.text == "/start":
            send_start_message(chat_id)
            with Database(DATABASE_URL) as db:
                db.execute("INSERT INTO  users (chat_id, state, options, files_scanned, data_scanned) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (chat_id) DO NOTHING", (chat_id, "INIT", "rgb", 0, 0))

        elif message.text == "/options":
            pass
        elif "#feedback" in message.text:
            bot.send_message(MYTELEGRAMID, message, disable_notification=True)
        else:
            bot.send_message(chat_id, "👍")          # why not 



        # read current state of user
        with Database(DATABASE_URL) as db:
            state = db.query("SELECT state from users where chat_id = %s", (chat_id,))[0]
            logging.info(state)



    elif content_type == "photo":
        bot.send_message(chat_id, "I only understand PDFs...")


    elif content_type == "document":
        ### read current state of user
        print(message)

        file_id = message.document.file_id
        file_name = message.document.file_name

        original_file_name = file_name.replace('.pdf','')

        file_name = file_name.replace(' ','')
        
        
        file_data = bot.get_file(file_id)
        print(file_data)


        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_data.file_path}"
        
        
        r = requests.get(url, stream=True)
        with open(f"{FOLDER_RECEIVED_PDFS}/{file_name}", 'wb') as f:
            f.write(r.content)

        # now the received file is saved locally
        file_stats = os.stat(f"{FOLDER_RECEIVED_PDFS}/{file_name}")
        file_size = file_stats.st_size
        
        if file_size < 1e6:
            bot.send_message(chat_id, f"Ok, received a {file_size*1e-3:.1f} KB document.")
        else:
            bot.send_message(chat_id, f"Ok, received a {file_size*1e-6:.1f} MB document.")



        bw = False # for now, make it adaptive later...


        t = datetime.datetime.now().strftime("%Y%m%d_%H%M") # https://strftime.org/


        if bw:
            file_name_pdf_scanned = f"{file_name.replace('.pdf','')}_scanned_bw_{t}.pdf"
        else:
            file_name_pdf_scanned = f"{file_name.replace('.pdf','')}_scanned_{t}.pdf"


        command  = f"convert -density 150 "
        if bw:
            command += f"-colorspace gray " 
        command += f"{FOLDER_RECEIVED_PDFS}/{file_name} "
        command += f"-linear-stretch 3.5%x10% "
        command += f"-blur 0x0.5 "
        command += f"-attenuate 0.3 "
        command += f"+noise Gaussian "
        command += f"-rotate 0.5 "
        command += f"{FOLDER_RECEIVED_PDFS}/{file_name_pdf_scanned}"
        print(command)

        rv_conversion = os.system(command)
        if (rv_conversion != 0):
            msg = "Sorry, your PDF couldn't be processed correctly, try with another one..."
            bot.send_message(chat_id, msg)
            os.system(f"rm -rf {FOLDER_RECEIVED_PDFS}/{file_name}")
            return
    
        file_stats = os.stat(f"{FOLDER_RECEIVED_PDFS}/{file_name_pdf_scanned}")
        file_size = file_stats.st_size

        if file_size > 40e6: # 40 MB
            bot.send_message(chat_id, f"Sorry, the file is too big ({file_size*1e-6:.1f}) MB... Single page files aren't usually a problem for me!")
            bot.send_message(chat_id, "😢")
            
            os.system(f"rm -rf {FOLDER_RECEIVED_PDFS}/{file_name}")
            os.system(f"rm -rf {FOLDER_RECEIVED_PDFS}/{file_name_pdf_scanned}")
            return

        msg = f"PDF scanned correctly, it's coming shortly! ({file_size*1e-6:.1f} MB) "
        bot.send_message(chat_id, msg)
            

        if (rv_conversion == 0):
            try:
                bot.send_document(chat_id, open(f"{FOLDER_RECEIVED_PDFS}/{file_name_pdf_scanned}", "rb"), caption=f"[{original_file_name}_scanned.pdf](https://t.me/ScanYourPdf_bot)", parse_mode='Markdown')

                # sending document worked, update counter on database
                with Database(DATABASE_URL) as db:
                    db.execute("UPDATE users SET files_scanned = files_scanned+1, data_scanned = data_scanned + %s WHERE chat_id = %s;", (file_size, chat_id,))

            except Exception as e:
                bot.send_message(chat_id, "Sorry, the scanned document is too big... ")
                bot.send_message(chat_id, "😢")
    
        os.system(f"rm -rf {FOLDER_RECEIVED_PDFS}/{file_name}")
        os.system(f"rm -rf {FOLDER_RECEIVED_PDFS}/{file_name_pdf_scanned}")

                



def setup_logging():
    logging.basicConfig(
        format='%(asctime)s,%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S',
        level=logging.DEBUG
    )



def initialize_database(database):
    """ database initialization with all the tables. """
    with Database(DATABASE_URL) as db:
        with open(INIT_DATABASE_COMMAND, 'r' ) as f:
            sql_comm = f.read()
        db.execute(sql_comm)
    print("Initialization database done.")




server = flask.Flask(__name__)


# SERVER SIDE
@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(flask.request.stream.read().decode("utf-8"))])
    return "!", 200

@server.route("/")
def webhook():
    return "OK", 200



if __name__ == "__main__":
    setup_logging()
    initialize_database(DATABASE_URL)
    
    if not os.path.exists(FOLDER_RECEIVED_PDFS):
        os.mkdir(FOLDER_RECEIVED_PDFS)


    bot.remove_webhook()
    logging.info("removed webhook")
    time.sleep(2)
    ## Set webhook
    logging.info(f"[+] setting webhook to {WEBHOOK_URL}{TOKEN}")
    bot.set_webhook(url=f"{WEBHOOK_URL}{TOKEN}")

    ### Debug/Development
    server.run(debug=False, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

    ### Production
    ### http_server = WSGIServer(('', 5000), server)
    ### http_server.serve_forever()

