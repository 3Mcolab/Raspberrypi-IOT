import subprocess
name_of_product = "kogan"
key_name = "KEY_1"
subprocess.call(["/home/pi/local_rasp/ir_send_dev.sh",name_of_product,key_name])
