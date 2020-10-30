# -*- coding: utf-8 -*-
#Library Packages
import requests
import datetime
import time
import json
import Adafruit_DHT

#Initialization
username_init = 'Rasbp1'
#country_init='AU' # obtained from web URL
#location_init = 'Sydney' #obtained from web URL
#Activity of Users
#SD: Study, SP: Sleep, WK:Week
#user_activity_init='SD' #obtained from web URL
#user_mode_init='C' #Obtained from web URL Heating:'H'or Cooling: 'C'
#setpoint_temp_init=22 #Obtained from web URL
sensor_HT=Adafruit_DHT.DHT22
GPIO_sensor_HT=4


#URL of Device to Cloud and URL from Cloud to Device for Communication
url_device_cloud='http://52.62.179.199/compute/{0}'.format(username_init)
url_cloud_device='http://52.62.179.199/{0}/data_summary'.format(username_init)

#Data Reading from Sensors
def return_sensordata():
    RH_int, temp_int = Adafruit_DHT.read_retry(sensor_HT, GPIO_sensor_HT)
    if RH_int is None and temp_int is None:
    	 time.sleep(3)
    	 return return_sensordata()
    temp_int=round(temp_int,3)
    RH_int=round(RH_int,3)
    return temp_int, RH_int

while(1):
    int_temp,int_RH=return_sensordata()
    print(int_temp)
    print(int_RH)
    #current_datetime = str(datetime.datetime.now())
    current_datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #current_date = current_datetime[:10]
    #current_time = current_datetime[11:][:8]
    data_post = requests.post(url_device_cloud,data=json.dumps({'Tem_Int':int_temp,'RH_Int':int_RH}))
    #print(data_post.text)
    data_from_cloud=requests.get(url_cloud_device).json()
    #date_compute=data_from_cloud['Date']
    #time_compute=data_from_cloud['Time']
    weath_con=data_from_cloud['Weather_cond']
    temp_amb=data_from_cloud['Temperature']
    press_amb=data_from_cloud['Pressure']
    Wamb=data_from_cloud['Wamb']
    temp_int=data_from_cloud['Temp_Int']
    rh_int=data_from_cloud['RH_Int']
    topt_calc=data_from_cloud['Topt']
    topt_control=data_from_cloud['Topt_new']
    #print(data_post.text)
    print(topt_control)
    print(data_from_cloud)

    #print(data_post.text)
    time.sleep(60)
