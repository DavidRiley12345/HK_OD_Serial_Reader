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

def listen_serial(ser, q, data_q):
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
            if line[:2] != '22':
                print(f"FPGA:{line}")  # Run-time error while printing out the line 
            if line[:2] != '00':
                q.put(line)
                if line[:2] == '22':
                    data_q.put(line)
                if line[:2] == '32':
                    readout_finished = 1
                    print("PYTH: readout finished")
                if line[:2] == '06':
                    FPGA_reset = 1


def send_value(value,ser):
    while True:
        try: 
            ser.write(struct.pack('B',value))
            print(f"PYTH:Send: {value}")
            return True
        except Exception as e:
            print(f"Error {e}")
            return False
   
def handle_messages(q):
        while True:
            message = q.get()
            if message is None:
                break
            print(f"FPGA: {message}")
            
def func_gen_set_mV(voltage,func_gen):
    voltage = voltage/1000
    func_gen.ch1.set_amplitude(voltage)
    func_gen.ch1.set_offset(-(voltage/2))

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
    #time.sleep(1)
    DAC_level_send(DAC,ser)

def DAC_level_send(DAC_lvl,ser):
    if 0 <= DAC_lvl <= 4095:
        print(f"Sending: {DAC_lvl}")
        firstbyte = (DAC_lvl>>8) & 0x0F
        lastbyte = DAC_lvl & 0xFF
        send_value(firstbyte,ser)
        send_value(lastbyte,ser)
    else:
        print("Error out of range 0-4095")

def take_data(number_of_samples,q,ser):
    print("PYTH:trying data take")
    
    if (int(q.get()[:2]) == 1):
        print("PYTH:On right menu, sending 2")
        send_value(2+48,ser)
        print("PYTH:2 sent")
       # time.sleep(1)
        print("PYTH:sending sample number")
        send_value(number_of_samples,ser)
        time.sleep(1)
        
        
    else:
        print("PYTH: ERR! Not at main menu: {0}", q.get()[:2])
        
        
def take_data_func(num_trigs,q,data_q,ser,DAC_CH,DAC,folder_name):   
    print("PYTH:sending take data message")
    take_data(num_trigs,q,ser)
    print("PYTH:sent")
    
    time_waited = 0
    time_to_wait = program_reset_timer + 1#changed fixed time wait~(program refersh time 8 second +2 second)
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
    new_folder = 'D:/xil_SDK_python_bridge/output/' + folder_name + "/" + subfolder_name
    if not os.path.exists(new_folder):
        os.makedirs(new_folder)
    
    with open("D:/xil_SDK_python_bridge/output/{0}/{1}/log_CH{2}_{3}DAC.txt".format(folder_name,subfolder_name,DAC_CH,DAC),"w+") as file:
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
