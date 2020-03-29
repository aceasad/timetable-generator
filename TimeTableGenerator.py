import pandas as pd
import requests
import random
import json
from datetime import datetime
from itertools import combinations, groupby
from jinja2 import Environment, FileSystemLoader
from flask import Flask, request, make_response
from flash_weasyprint import HTML, render_pdf

app = Flask(__name__)


def load(url):
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36', 'Accept':'text/html'}, timeout=10)
    return json.loads(res.text)

def get_API_data(student_id):
    timetable_url="http://academicadmin.site/public/api/timetableData/"
    courses_url="http://academicadmin.site/public/api/coursesData?id="+student_id
    courses_json=load(courses_url)
    timetable_json=load(timetable_url)
    timetable=pd.DataFrame(dict(timetable_json)['timetable_data'])
    timetable=timetable.drop(['id','created_at','updated_at'], 1)
    courses=pd.DataFrame(dict(courses_json)['courses_data'])
    courses=courses.drop(['created_at','updated_at'],1)
    student=pd.DataFrame(dict(courses_json)['current_course_data'])
    student = student[student.type != 'Future']
    student=student.drop(['name','type','supervisor_id','student_id','username','college_id','student_name','email','password','created_at','updated_at','id'],1)
    return timetable,courses,student

# It returns the related courses for the student from the global time table day wise
def get_timetable_days(student,timetable):
    all_index=student.index
    frames=[]
    for i in all_index:
        x=timetable.loc[(timetable['course_id'] == student['course_id'][i])]
        frames.append(x)
    student_timetable=pd.concat(frames)
    #print(student_timetable.sort_values(by=['day_of_week']))
    mon = student_timetable[student_timetable.day_of_week == '1']
    tue = student_timetable[student_timetable.day_of_week == '2']
    wed = student_timetable[student_timetable.day_of_week == '3']
    thu = student_timetable[student_timetable.day_of_week == '4']
    sun = student_timetable[student_timetable.day_of_week == '7']
    mon=mon.drop(['day_of_week'],1)
    tue=tue.drop(['day_of_week'],1)
    wed=wed.drop(['day_of_week'],1)
    thu=thu.drop(['day_of_week'],1)
    sun=sun.drop(['day_of_week'],1)
    output=[mon,tue,wed,thu,sun]
    return output

 
def get_grouped_classes(data):
    temp=[]
    for i in data.course_id.index:
        temp.append(data.loc[i])
    output={}
    for data in temp:
        if(data.course_id in output):
            output[data.course_id].extend([[data.course_id,data.section,data.start_time,data.end_time,data.level]])
        else:
            output.setdefault(data.course_id,[[data.course_id,data.section,data.start_time,data.end_time,data.level]])
    return output

def Random_time_generator(day):
    temp=get_grouped_classes(day)
    selection=[]
    for c in temp:
        l=len(temp[c])
        x=random.randint(1,l)-1
        #print("Random Selection Class",x)
        selection.append(temp[c][x])
    return selection

def rSubset(arr, r): 
    return list(combinations(arr, r)) 

#(1,2,3) #(2,3,1) #(3,2,1)
def compare(random_selection,overlap_pairs):
    index=[]
    for i in range(0,len(random_selection)):
        index.append(i)
    checks=rSubset(index,2)
    # i=11 [ Islamiat: 10:30 / 11:30 / OS : 10:30 / 11:30 / Coding 9:30 / 10:30]
    for ind in checks:
        c1_s=random_selection[ind[0]][2] #Starting Time
        c1_e=random_selection[ind[0]][3] #Ending Time
        c2_s=random_selection[ind[1]][2] #Starting Time
        c2_e=random_selection[ind[1]][3] #Ending Time
        StartA = datetime.strptime(c1_s, '%H:%M:%S')
        EndA = datetime.strptime(c1_e, '%H:%M:%S')
        StartB = datetime.strptime(c2_s, '%H:%M:%S')
        EndB = datetime.strptime(c2_e, '%H:%M:%S')
        if(EndA <= StartB or StartA >= EndB):
            pass
        else:
            overlap_pairs.append([random_selection[ind[0]],random_selection[ind[1]]])
            return False
    return True

def removeDuplicates(k):
    k.sort()
    return list(k for k,_ in groupby(k))
'''

        # i=0 [ Islamiat: 10:30 / 11:30 / OS : 10:30 / 11:30 / Coding 9:30 / 10:30]
        # i=11 [ Islamiat: 10:30 / 11:30 / OS : 10:30 / 11:30 / Coding 9:30 / 10:30]
        # i=66 [ Islamiat: 9:30 / 10:30 / OS : 10:30 / 11:30 / Coding 9:30 / 10:30]
        # i=1 [ Islamiat: 9:30 / 10:30 / OS : 10:30 / 11:30 / Coding 9:30 / 10:30]
        # i=2 [ Islamiat: 9:30 / 10:30 / OS : 10:30 / 11:30 / Coding 11:30 / 12:30]

'''
def get_recommendation(day,samples):
    random_schedules=[]
    for i in range(0,samples):
        random_selection=Random_time_generator(day)
        random_schedules.append(random_selection)
    removed_duplicated_random_schedules=removeDuplicates(random_schedules)

    recommendations=[]
    overlap_pairs=[]
    for random_timetables in removed_duplicated_random_schedules:
        result=compare(random_timetables,overlap_pairs)
        if(result==True):
            print("Time Table Suggestion Found!")
            recommendations.append(random_timetables)
            break
    return recommendations, overlap_pairs

def get_clashes(day,time_table_response):
    if len(time_table_response[day]['clashes']) != 0:
        frames=[]
        for i in range(0,len(time_table_response[day]['clashes'])):
            frames.append(pd.DataFrame(time_table_response[day]['clashes'][i],columns=['Course ID','Section','Start Time','End Time','Level']))
        return pd.concat(frames)
    else:
        return pd.DataFrame(['No Clash Exists'])

@app.route('/',methods=['GET'])
def index():
    return ("<div><h1>Academic Time Table Recommender API</h1> <br/><h2>/timetable?query=Student_id</h2> <br/><h3>This returns the recommended courses and clashes for this particular student</h3> </div>")

@app.route('/timetable', methods=['GET'])
def get_timeschedule():
    student_id = request.args.get("query")
    try:
        timetable,courses,student=get_API_data(student_id)
        days=get_timetable_days(student,timetable)
        time_table_response={
            'monday':{
                'recommendation':[],
                'clashes':[]
            },
            'tuesday':{
                'recommendation':[],
                'clashes':[]
            },
            'wednesday':{
                'recommendation':[],
                'clashes':[]
            },
            'thursday':{
                'recommendation':[],
                'clashes':[]
            },
            'sunday':{
                'recommendation':[],
                'clashes':[]
            }
        }
        for i in range(0,len(days)):
            recommendations,overlap_pairs=get_recommendation(days[i],100)
            if(i==0):
                for items in recommendations:
                    time_table_response['monday']['recommendation'].extend(items)
                for pairs in overlap_pairs:
                    time_table_response['monday']['clashes'].append(pairs)
            if(i==1):
                for items in recommendations:
                    time_table_response['tuesday']['recommendation'].extend(items)
                for pairs in overlap_pairs:
                    time_table_response['tuesday']['clashes'].append(pairs)
            if(i==2):
                for items in recommendations:
                    time_table_response['wednesday']['recommendation'].extend(items)
                for pairs in overlap_pairs:
                    time_table_response['wednesday']['clashes'].append(pairs)
            if(i==3):
                for items in recommendations:
                    time_table_response['thursday']['recommendation'].extend(items)
                for pairs in overlap_pairs:
                    time_table_response['thursday']['clashes'].append(pairs)
            if(i==4):
                for items in recommendations:
                    time_table_response['sunday']['recommendation'].extend(items)
                for pairs in overlap_pairs:
                    time_table_response['sunday']['clashes'].append(pairs)

        mon = pd.DataFrame(time_table_response['monday']['recommendation'], columns = ['Course ID', 'Section','Start Time',"End time","Level"]).sort_values(by='Start Time')
        tue = pd.DataFrame(time_table_response['tuesday']['recommendation'], columns = ['Course ID', 'Section','Start Time',"End time","Level"]).sort_values(by='Start Time')
        wed = pd.DataFrame(time_table_response['wednesday']['recommendation'], columns = ['Course ID', 'Section','Start Time',"End time","Level"]).sort_values(by='Start Time')
        thu = pd.DataFrame(time_table_response['thursday']['recommendation'], columns = ['Course ID', 'Section','Start Time',"End time","Level"]).sort_values(by='Start Time')
        sun = pd.DataFrame(time_table_response['sunday']['recommendation'], columns = ['Course ID', 'Section','Start Time',"End time","Level"]).sort_values(by='Start Time')

        mon_clash=get_clashes('monday',time_table_response)
        tue_clash=get_clashes('tuesday',time_table_response)
        wed_clash=get_clashes('wednesday',time_table_response)
        thu_clash=get_clashes('thursday',time_table_response)
        sun_clash=get_clashes('sunday',time_table_response)


        env = Environment(loader=FileSystemLoader('.'))
        template = env.get_template("template.html")
        template_vars = {"Info" : "Timetable for Student ID "+student_id,
                        "title":"Student Timetable",
                        "time_table_mon": mon.to_html(),
                        "time_table_tue": tue.to_html(),
                        "time_table_wed": wed.to_html(),
                        "time_table_thu": thu.to_html(),
                        "time_table_sun": sun.to_html(),
                        "clash_mon": mon_clash.to_html(),
                        "clash_tue": tue_clash.to_html(),
                        "clash_wed": wed_clash.to_html(),
                        "clash_thu": thu_clash.to_html(),
                        "clash_sun": sun_clash.to_html()

                        }
        html_timetable = template.render(template_vars)
        with open('timetable.html', 'w') as file:
            file.write(html_timetable)
        return render_pdf(HTML(string=html_timetable))
    except:
        return "<div> <h1>Time Table Generator</h1><br/><h2>The Student ID doesn't exist for which time-table is requested!</h2></div>"

if __name__=='__main__':
    app.run()
