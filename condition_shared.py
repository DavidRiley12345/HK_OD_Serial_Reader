import threading

condition = threading.Condition()

readout_finished = False
FPGA_reset = False