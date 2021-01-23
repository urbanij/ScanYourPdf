"""
    August 2020
    Francesco Urbani
"""

import os
import datetime

def processPDF(input_document, bw=True):
    
    t = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") #https://strftime.org/

    command  = f"convert -density 150 "
    if bw:
        command += f"-colorspace gray " 
    command += f"{input_document} "
    command += f"-linear-stretch 3.5%x10% "
    command += f"-blur 0x0.2 "
    command += f"-attenuate 0.3 "
    command += f"+noise Gaussian "
    command += f"-rotate 0.6 "
    command += f"{input_document.replace('.pdf', '')}_scanned_{t}.pdf"
    
    rv = os.system(command)  
    return rv






if __name__ == '__main__':
    import sys
    try:
        input_document = sys.argv[1]
    except Exception as e:
        raise("pass file to convert")


    rv = processPDF(input_document)

    if rv:
        print("Error, your PDF couldn't be processed correctly.")
    else:
        print("PDF scanned correctly.")
    


