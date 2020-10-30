#Installation Libraries
#Installation of Flask and Dependencies
import requests
import datetime
import time
import atexit
import json

import mysql.connector #Connect to Mysql Database in AWS
import arrow #Convert Timezone based on Location
from urllib.request import urlopen
from flask import Flask, render_template, request, jsonify, send_file, make_response, redirect, url_for
from collections import deque
from apscheduler.schedulers.background import BackgroundScheduler #Use for Periodic Scheduler
from apscheduler.triggers.interval import IntervalTrigger

app = Flask(__name__)

#Weather API http://api.wunderground.com/api/
#Get Weather Key from Above Website
API_Weather_UNG_Key="56a448f475c5044d"
location_init = ['Sydney','Brisbane','Melbourne']
country_init=['AU','AU','AU']

#Human Thermal Comfort
#Activity of Users Assuming that Users are Walking, Sleeping, Studying etc.
#SD: Study, SP: Sleep, WK: Walk
user_activity_init= {"SD":1.2,"SP":0.6,"WK":0.4}

user_mode_init=['H','C'] #User Mode: Heating:'H'or Cooling: 'C'
Th_C=18 #Threshold Cooling Temperature
Th_H=25 #Threshold Heating Temperature
sm_data=30 #Data Sampling Time

#AWS MySQL Database Initialization
host_init="dbtestv1.c12avvlyprkq.ap-southeast-2.rds.amazonaws.com"
user_init="remote-monitor" #Username of AWS RDS
password_init="RemoteTest#" #Password of AWS RDS
db_name_init="RemotedB" #AWS RDS Database Name

inx_datetime=1
inx_webdata=2 #Table Index: userID-0,Datetime-1

#Local User Behavior
#Datastructure to hold results for all users
#Assuming that Raspberry Pi/HVAC are individual users
user_results = {}
#dictionary to hold information about the user inputs
#dictionary keys will be the user id
user_input_data = {}
class UserData_init:
    #Default values, it will be re-written from webpage from the user
    country_selected     = 'AU'
    location_selected     = 'Sydney'
    useractivity_selected = 'TYP'
    usermode_selected     = 'C'
    tsp_selected          = 22
UserData= UserData_init()

#Outdoor Conditions Measurement Using Weather API
API_url="http://api.wunderground.com/api/" +API_Weather_UNG_Key+ "/conditions/q/{0}/{1}"
def return_current_weather(country_init,location_init):
    API_address=API_url.format(country_init,location_init)+".json"
    try:
        f=urlopen(API_address)
    except:
        return false
    json_content = f.read().decode('utf-8')
    parsed_json = json.loads(json_content)
    WCon_amb = parsed_json['current_observation']['weather']
    Tamb= parsed_json['current_observation']['temp_c']
    RHamb= parsed_json['current_observation']['relative_humidity']
    Pamb= parsed_json['current_observation']['pressure_mb']
    Wamb= parsed_json['current_observation']['wind_mph']
    f.close()
    return WCon_amb,Tamb, Pamb, RHamb,Wamb

#Optimal Temperature Calculation Algorithm
def compute_optimal_param(user_act,user_mode, Tsp, Tamb):
    i_init = user_act
    if user_mode== 'C':
        Tn=Tsp+1
        Topt=round(28.68+(0.009*Tamb)-(9.1*i_init)+(0.04*Tamb*i_init)) #You can alot of research on this point of calculation
        if Topt>Tn:
            if Topt<Tamb or Topt>Th_C:
                Topt_new=Topt
            else:
                Topt_new=Tsp
        else:
            Topt_new=Tn
    elif user_mode== 'H':
        Tn=Tsp-1
        Topt=round(26+(0.01*Tamb)-(2.1*i_init)-(0.04*Tamb*i_init)) #You can research which algorithm suits you best
        if Topt<Tn:
            if Topt>Tamb or Topt<Th_H:
                Topt_new=Topt
            else:
                Topt_new=Tsp
        else:
            Topt_new=Tn
    else:
        print("Invalid Character for Mode")
    return Topt_new,Topt

#Client Side Date time Range
def validate_date(d_init):
    try:
        datetime.datetime.strptime(d_init, '%Y-%m-%d %H:%M')
        return True
    except ValueError:
        return False

def add_localdata_to_queue():
    current_datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wcon_amb,tamb, pamb, rhamb,wamb = return_current_weather(UserData.country_selected,UserData.location_selected)
    topt_new, topt    = compute_optimal_param(user_activity_init[UserData.useractivity_selected],
                                          UserData.usermode_selected,UserData.tsp_selected,tamb)

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(
    func=add_localdata_to_queue,
    trigger=IntervalTrigger(seconds=sm_data), #change this to control how often data is pulled
    id='weather_job',
    name='Get and store current weather data every 15 min',
    replace_existing=True)

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

#Main Program
@app.route("/")
def index():
   return render_template('index.html',country=country_init,location=location_init,
                           user_activity=user_activity_init,
                           user_mode=user_mode_init)

@app.route("/user_inputs",methods=['POST'])
def user_inputs():
    username_selected    = request.form.get('userIDen')
    country_selected     = request.form.get('country_selected')
    location_selected    = request.form.get('location_selected')
    useractivity_selected= request.form.get('user_activity_selected')
    usermode_selected    = request.form.get('user_mode_selected')
    tsp_selected         = request.form.get('setpoint_temp')

    user_input_data[username_selected] = {'country_selected':country_selected,'location_selected':location_selected,
                    'useractivity_selected':useractivity_selected,'usermode_selected':usermode_selected,
                    'tsp_selected':tsp_selected}
    return "Thank you for sending your Preferences"

@app.route("/compute/<username>",methods=['GET','POST'])
def compute_algorithm(username):
    #Current time from Input
    compute_local_datetime=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    posted_data = request.get_json(force=True)
    Tem_Int = posted_data['Tem_Int']
    RH_Int = posted_data['RH_Int']

    username_selected = username
    if username not in user_input_data.keys():
        country_selected = UserData.country_selected
        location_selected= UserData.location_selected
        useractivity_selected=UserData.useractivity_selected
        usermode_selected = UserData.usermode_selected
        tsp_selected      = UserData.tsp_selected
    else:
        country_selected = user_input_data[username]['country_selected']
        location_selected= user_input_data[username]['location_selected']
        useractivity_selected = user_input_data[username]['useractivity_selected']
        usermode_selected = user_input_data[username]['usermode_selected']
        tsp_selected = float(user_input_data[username]['tsp_selected'])

    WCon_amb,Tamb, Pamb, RHamb,Wamb = return_current_weather(country_selected,location_selected)
    Topt_new,Topt       = compute_optimal_param((user_activity_init[useractivity_selected]),usermode_selected,tsp_selected,Tamb)
    #Store the results in the user result class
    user_results[username_selected] = {'Date_time':compute_local_datetime,
                                       'Weather_cond':WCon_amb,'Temperature':Tamb,'RH':RHamb,
                                       'Pressure':Pamb,'Wamb':Wamb,'Temp_Int':Tem_Int,
                                       'RH_Int':RH_Int,'Topt':Topt,'Topt_new':Topt_new}

    #Connection to AWS MySQL Database
    conn = mysql.connector.connect(host=host_init,user=user_init,password=password_init,db=db_name_init)
    curs=conn.cursor()
    curs.execute("""insert into  users_4 values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (username_selected,compute_local_datetime,country_selected,location_selected,
                useractivity_selected,usermode_selected,tsp_selected,
                WCon_amb,Tamb, Pamb, RHamb,Wamb,Tem_Int,RH_Int,Topt,Topt_new))
    conn.commit()
    conn.close()
    return redirect('/{0}/data_summary'.format(username_selected))

@app.route("/<username>/graph_db",methods=['GET'])
def graph_db(username):
    from_date_str 	= request.args.get('from',time.strftime("%Y-%m-%d %H:%M")) #Get the from date value from the URL
    to_date_str 	= request.args.get('to',time.strftime("%Y-%m-%d %H:%M"))   #Get the to date value from the URL
    timezone 		= request.args.get('timezone','Etc/UTC');
    range_d_form	= request.args.get('range_d','');  #This will return a string, if field range_h exists in the request
    #range_h_form        = request.args.get('range_h','');  #This will return a string, if field range_h exists in the request
    range_d_int 	= "nan"  #initialise this variable with not a number
    try:
        range_d_int= int(range_d_form)
    except:
        print("range_h_form not a number")

    # Create datetime object so that we can convert to UTC from the browser's local time
    from_date_obj       = datetime.datetime.strptime(from_date_str,'%Y-%m-%d %H:%M')
    to_date_obj         = datetime.datetime.strptime(to_date_str,'%Y-%m-%d %H:%M')
    if isinstance(range_d_int,int):
       #arrow_time_from = arrow.utcnow().replace(hours=-range_h_int)
       arrow_time_from = arrow.utcnow().replace(days=-range_d_int)
       arrow_time_to   = arrow.utcnow()
       #time_now = datetime.datetime.now()
       #time_from = time_now - datetime.timedelta(hours = range_h_int)
       from_date_utc   = arrow_time_from.strftime("%Y-%m-%d %H:%M")
       to_date_utc     = arrow_time_to.strftime("%Y-%m-%d %H:%M")
       #from_date_str=time_from.strftime("%Y-%m-%d %H:%M")
       #to_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
       from_date_str   = arrow_time_from.to(timezone).strftime("%Y-%m-%d %H:%M")
       to_date_str     = arrow_time_to.to(timezone).strftime("%Y-%m-%d %H:%M")
    else:
       #Convert datetimes to UTC
       from_date_utc   = arrow.get(from_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")
       to_date_utc     = arrow.get(to_date_obj, timezone).to('Etc/UTC').strftime("%Y-%m-%d %H:%M")

    #Data Fetching From SQL connect to AWS RDS
    conn = mysql.connector.connect(host=host_init,user=user_init,password=password_init,db=db_name_init)
    curs=conn.cursor()
    #Assume that Users or Local Server users is users_4 with its ID ='Raspb1'
    curs.execute("SELECT *FROM users_4 WHERE ID='Rasbp1' AND Date_Time BETWEEN %s AND %s",(from_date_utc.format('YYYY-MM-DD HH:mm'), to_date_utc.format('YYYY-MM-DD HH:mm')))
    #curs.execute("SELECT *FROM users_4 WHERE ID='Rasbp1' AND Date_Time BETWEEN %s AND %s",(from_date_str, to_date_str))
    #curs.execute("SELECT *FROM users_4 WHERE ID=%s",username)
    webdata_db=curs.fetchall()
   # Create new record tables so that datetimes are adjusted back to the user browser's time zone.
    adjusted_webdata_db= []
    for i_webdb in webdata_db:
       local_timedate = arrow.get(i_webdb[inx_datetime], "YYYY-MM-DD HH:mm").to(timezone)
       local_timedate_db=local_timedate.format('YYYY-MM-DD HH:mm')
       to_append_localtimedata = ()
       to_append_localtimedata= to_append_localtimedata + (local_timedate_db,)
       for j_webdb in range(inx_webdata,len(i_webdb)):
          to_append_localtimedata = to_append_localtimedata + (i_webdb[j_webdb],)
       adjusted_webdata_db.append(to_append_localtimedata)
    conn.close()
    return render_template("graph_db.html",username=username,db_webdata=adjusted_webdata_db)

@app.route("/<username>/data_summary")
def data_summary(username):
    try:
       all_data = user_results[username]
    except:
       all_data='No Data Yet'
    return_alldata=app.response_class(response=json.dumps(all_data),
                                status=200,
                                mimetype='application/json')
    return return_alldata

if __name__ == "__main__":
    app.run(host='0.0.0.0')
