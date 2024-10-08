# HK_OD_Serial_Reader

This repo contains the serial communication scripts used for testing of the Hyper OD elctronics splitter/digitizer boards v???.

General organisation is scantype.py to run communicate with a board and take data and then analysistype.ipynb to analyse and plot.

Dependencies are: [tektronix python communication library](https://github.com/asvela/tektronix-func-gen/blob/main/tektronix_func_gen.py) (some modification needed based on the desired amplitude range on your func gen if not one of the supported models)

---

TODOs:
- break serial communication setup into a separate library to aid ease of use (any apply any updates to this to all data taking scripts)

