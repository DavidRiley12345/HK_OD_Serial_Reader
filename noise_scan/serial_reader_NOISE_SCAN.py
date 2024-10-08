import os
import sys
import serial
import time
import threading
import queue
import struct
#import tektronix_func_gen as tfg
import pickle as pkl
import numpy as np
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_reader_base import listen_serial, send_value, handle_messages, func_gen_set_mV, \
    set_DAC_levels, DAC_level_send, take_data, take_data_func, close_fpga_SDK

pcb_number = 3
program_reset_timer = 8
trigger_number_thousand = 7 # in thousands
folder_name = 'NOISE_SCAN'

readout_finished = False
FPGA_reset = False
condition = threading.Condition()

def main():
    # reponse values from FPGA
    # 00: message to user
    # 01: Main menu
    # 99: failure
    # 99: failure
    
    #visaRsrcAddr = "USB0::0x0699::0x0357::C020190::INSTR"

    #fgen = tfg.FuncGen(visaRsrcAddr,override_compatibility='AFG3022')
    
    #amp = 6
    #func_gen_freq = 12500000
    #func_gen_set_mV(amp,fgen)
    #fgen.ch1.set_frequency(func_gen_freq)
    #fgen.ch1.set_limit("amplitude lims","50ohm","min",0.001)
  
    global readout_finished
    global FPGA_reset
    
    #rm = visa.ResourceManager()
    #func_gen = rm.open_resource(visaRsrcAddr)
    #print(func_gen.query('*IDN?'))
    
    #ser = serial.Serial("COM4",460800,timeout=1)
    ser = None
    q = queue.LifoQueue()
    data_q = queue.LifoQueue()

    print("listening on COM11")
    listener_thread = threading.Thread(target=listen_serial,args=(ser,q,data_q))
    listener_thread.daemon = True
    listener_thread.start()

    print("listener set up")
   
    
    DAC_settings = np.arange(3800,3931,1)
        
    print("DAC Thresholds :", DAC_settings)
    
     ### Dac Scan ###

    results = {}
    
    DAC_CHANNELS = [1,2,3,4,5,6]
     
    ### NOISE SCAN ###
    for dac_channel in DAC_CHANNELS:
        FPGA_reset = False
        
        # initially set all DACs to 0
              
        with condition:
            condition.wait_for(lambda: FPGA_reset)

        print("PYTH:FPGA reset, proceeding")
        print(f"PYTH:taking data")
        
        set_DAC_levels(7,0,ser)
        
        counts = {}
        
        for i in DAC_settings:
            FPGA_reset = False
            readout_finished = False
            print("PYTH: Waiting for FPGA reset----------------------")
            with condition:
                condition.wait_for(lambda: FPGA_reset)
            print("PYTH:FPGA reset, proceeding")
            print("PYTH: Setting DAC----------------------")
            DAC = i # 0-4095
            CH = dac_channel # 1-6 for individual, 7 for all
            set_DAC_levels(CH,DAC,ser)
            print("PYTH: Data Taking----------------------")
            #time.sleep(1)
            
            num_trigs = trigger_number_thousand # in thousands
        
            read_count_output, time_taken_output = take_data_func(num_trigs,q,data_q,ser,CH,DAC,folder_name)
            
            counts[int(i)] = read_count_output
            
            print(counts)
            
            time.sleep(2)
            with data_q.mutex:
                data_q.queue.clear()
            time.sleep(2)
            
        results[int(dac_channel)] = counts
        print(results)
        with open("D:/xil_SDK_python_bridge/output/{0}/autosave_NOISE_SCAN_270924.txt".format(folder_name),"w") as temp_file:
            results_str = json.dumps(results)
            temp_file.write(results_str)
    
    print(results)
    
    with open("D:/xil_SDK_python_bridge/output/{0}/NOISE_SCAN_270924.txt".format(folder_name),"w+") as file:
        #output file 
        results_str = json.dumps(results)
        file.write(results_str)
    
    
    #readout_finished = 0
    #print("First Data Take")
    #take_data_func(num_trigs,q,data_q,ser,func_gen_freq,amp,DAC)
                
    #time.sleep(3)
    #print("Second Data Take")
    #take_data_func(num_trigs,q,data_q,ser,func_gen_freq,amp,DAC) 
    #close_fpga_SDK(ser)
    #max volatge dac=2.5V
    #per dac scan = 30us
    
 
main()