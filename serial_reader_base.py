import os
import serial
import time
import threading
import queue
import struct
#import tektronix_func_gen as tfg
import pickle as pkl
import numpy as np
import json

# This is a listener set up to run on a thread, allowing for the serial output of the FPGA to be read at any time
# it needs to be provided with a serial port to listen on, a queue to put data into if you want to act on any of the messages it sends
# and a queue to put data into if you want to save the data read from the FPGA
def listen_serial(ser, q, data_q):

    # Set up global variables to be used in the main program
    # These are used to signal when the FPGA has finished reading out data or when the FPGA reset signal gets sent
    global readout_finished
    global FPGA_reset

    while True:
        if ser.in_waiting > 0:
            try:
                # Attempt to read and decode the line
                line = ser.readline().decode('utf-8').strip() 
            except UnicodeDecodeError:

                # Skip the line if there's a decoding error
                print("Skipping line due to decoding error.")
                continue

            # Process the line if decoding was successful
            # 22 signifies a data message from the FPGA so readout everything else but these
            if line[:2] != '22':
                print(f"FPGA:{line}")
            # 00 likewise is for debugging from the FPGA we dont need to store those on the queue
            if line[:2] != '00':
                q.put(line)

                # Check if we have a data message, if so store it in the data queue
                if line[:2] == '22':
                    data_q.put(line)

                # Check for the data finished code and set the global variable to 1
                if line[:2] == '32':
                    readout_finished = 1
                    print("PYTH: readout finished")

                # Check for the FPGA reset code and set the global variable to 1
                if line[:2] == '06':
                    FPGA_reset = 1

# This function allows a number to be sent to the FPGA over serial
def send_value(value,ser):
    while True:
        try: 

            # Send the value to the FPGA as a byte (0-255)
            ser.write(struct.pack('B',value))
            print(f"PYTH:Send: {value}")
            return True
        except Exception as e:
            print(f"Error {e}")
            return False

# redudant function for message handling
# POTENTIALLY DELETE
def handle_messages(q):
        while True:
            message = q.get()
            if message is None:
                break
            print(f"FPGA: {message}")

# This sets the Arb Func Gen amplitude and offset to the desired voltage
# we want to set the range of the voltage between 0 and -xmV where x is the desired voltage
# The function generator expects however a total amplitude and an offset, so we need to set the total amplitude first and then offset it down the 0mV like we want
def func_gen_set_mV(voltage,func_gen):
    voltage = voltage/1000
    func_gen.ch1.set_amplitude(voltage)
    func_gen.ch1.set_offset(-(voltage/2))

# This function sets the DAC levels for a given channel
# It first sends the channel number to the FPGA, then the DAC level
# the numbers are offset by 48 to convert them to ASCII (a hold over from the FPGA code which took keyboard inputs)
def set_DAC_levels(ch,DAC,ser):

    # from main menu enter 1 to go to DAC mode
    #time.sleep(1)
    send_value(1+48,ser)
    
    # enter 1 to go to update ch mode
    #time.sleep(1)
    send_value(1+48,ser)
    
    # enter the desired channel number
    # time.sleep(1)
    send_value(ch+48,ser)
    
    # send the DAC level itself
    #time.sleep(1)
    DAC_level_send(DAC,ser)

# This function sets the DAC levels for a given channel
# The DAC value need to be sent across as a 12 bit number, so we split it into two 8 bit numbers since the serial port only takes 8 bit numbers
def DAC_level_send(DAC_lvl,ser):
    if 0 <= DAC_lvl <= 4095:
        print(f"Sending: {DAC_lvl}")
        firstbyte = (DAC_lvl>>8) & 0x0F
        lastbyte = DAC_lvl & 0xFF
        send_value(firstbyte,ser)
        send_value(lastbyte,ser)
    else:
        print("Error out of range 0-4095")

# This function tells to FPGA to enter data take mode
def take_data(number_of_samples,q,ser):
    print("PYTH:trying data take")
    
    # check that the FPGA is at the main menu by seeing if the first two characters of the message are 01
    if (int(q.get()[:2]) == 1):
        print("PYTH:On right menu, sending 2")

        # send 2 to enter data take mode
        send_value(2+48,ser)
        print("PYTH:2 sent")
        # time.sleep(1)

        # send the number of samples to take in thousands
        print("PYTH:sending sample number")
        send_value(number_of_samples,ser)

    else:
        print("PYTH: ERR! Not at main menu: {0}", q.get()[:2])
        
        
def take_data_func(num_trigs,q,data_q,ser,DAC_CH,DAC,folder_name):   
    print("PYTH:sending take data message")
    take_data(num_trigs,q,ser)
    print("PYTH:sent")
    
    time_waited = 0
    time_to_wait = program_reset_timer + 1 #changed fixed time wait~(program refersh time 8 second +2 second)
    #time_to_wait = (num_trigs * 1000 / 100) + 20 # estimated time for a given num of triggers plus a 5 second buffer
    
    print(f"PYTH:Waiting for {num_trigs},000 trigs or {time_to_wait}s")
    
    while ((readout_finished != 1) and (time_waited <= time_to_wait)):
        time.sleep(1)
        time_waited += 1
    
    print(f"PYTH: Waited {time_waited} of {time_to_wait}")
    
    readout = []
    
    while (data_q.empty() == False):
        readout.append(data_q.get())
       
    readout_reordered = readout[::-1]
    
    read_count = 0
    trigger_number = trigger_number_thousand * 1000
    #create new folder location
    subfolder_name = ( "pcb" + str(pcb_number)+ "_ch" + str(DAC_CH) + "_" + str(trigger_number) )
    new_folder = 'output/' + folder_name + "/" + subfolder_name
    if not os.path.exists(new_folder):
        os.makedirs(new_folder)
    
    with open("output/{0}/{1}/log_CH{2}_{3}DAC.txt".format(folder_name,subfolder_name,DAC_CH,DAC),"w+") as file:
        #output file 
        file.write('START READOUT\n')
        for i in readout_reordered:
            if int(i[:2]) == 22:
                file.write(i[3:])
                file.write("\n")
                read_count += 1
        file.write('STOP READOUT\n')
    
                
    print(f"PYTH: Saved {read_count} lines ({read_count/4} events)")
    return read_count
        
def close_fpga_SDK(ser):
        
    send_value(3+48,ser)
    
    time.sleep(5)
