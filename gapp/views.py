from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.db import transaction
from django.http import HttpResponseRedirect,HttpResponse, HttpResponseNotFound
from jdatetime import datetime as jdt
import time
from django.core.exceptions import PermissionDenied, ValidationError
from datetime import datetime as gdt
from datetime import timedelta
import json
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder

# Create your views here.

form_defaults={}

@csrf_exempt
@login_required(login_url='login')
def index(request):
    global form_defaults
    if request.method == "POST":
        try:
            arr_dep = request.POST["arr-dep"]
            emp_id = request.POST["employee-id"]
            working = request.POST["work"]
            try:
                if request.POST["year"] and request.POST["month"] and request.POST["day"] and request.POST["time-h"] and request.POST["time-m"]:
                    is_manual = True
            except:
                is_manual=False
            if  is_manual:
                dt_str = request.POST["year"] + "/" + request.POST["month"] + "/" + request.POST["day"] + " " + ("00" + request.POST["time-h"])[-2:]+":"+ ("00" + request.POST["time-m"])[-2:] + ":00"
                form_defaults={"year":request.POST["year"], "month":request.POST["month"], "day":request.POST["day"], "emp":emp_id}
                utc_datetime = jdt.strptime(dt_str,'%Y/%m/%d %H:%M:%S').togregorian()
                with transaction.atomic():
                    _traffic = Traffic()
                    try:
                        if (arr_dep == "arr" or arr_dep == "dep") and emp_id :
                            _traffic.employee = Employee.objects.get(pk=emp_id)
                            _traffic.arr_dep = 0 if arr_dep == "arr" else 1
                            _traffic.work_or_not = 0 if working == "yes" else 1
                            _traffic.creator = request.user
                            _traffic.datetime = utc_datetime
                            _traffic.save()
                            _traffic.employee.last_traffic_time = _traffic.datetime
                            _traffic.employee.last_traffic_a_or_d = _traffic.arr_dep
                            _traffic.employee.last_traffic_w_or_n = _traffic.work_or_not
                            _traffic.employee.save()
                    except:
                        pass
            else:
                with transaction.atomic():
                    _traffic = Traffic()
                    try:
                        if (arr_dep == "arr" or arr_dep == "dep") and emp_id :
                            _traffic.employee = Employee.objects.get(pk=emp_id)
                            _traffic.arr_dep = 0 if arr_dep == "arr" else 1
                            _traffic.work_or_not = 0 if working == "yes" else 1
                            _traffic.creator = request.user
                            _traffic.save()
                            _traffic.employee.last_traffic_time = _traffic.datetime
                            _traffic.employee.last_traffic_a_or_d = _traffic.arr_dep
                            _traffic.employee.last_traffic_w_or_n = _traffic.work_or_not
                            _traffic.employee.save()
                    except:
                        pass
        except:
            pass
        try:
            tra_id = request.POST["traffic-id"]
            with transaction.atomic():
                try:
                    if  tra_id :
                        _traffic = Traffic.objects.get(pk=tra_id)
                        _employee = _traffic.employee
                        if _traffic.creator == request.user:
                            _traffic.delete()
                        try:
                            _last_traffic = Traffic.objects.filter(employee=_employee).order_by("-datetime").first()
                            _employee.last_traffic_time = _last_traffic.datetime
                            _employee.last_traffic_a_or_d = _last_traffic.arr_dep
                            _employee.last_traffic_w_or_n = _last_traffic.work_or_not
                            _employee.save()
                        except:
                            pass
                except:
                    pass
        except:
            pass

        return redirect("index")



    now_m = lambda: int(round(time.time() * 1000))
    employees = Employee.objects.all().order_by('lastname')
    traffics = Traffic.objects.all().order_by('-datetime')[:100]
    for traffic in traffics:
        traffic.datetime = jdt.fromgregorian(date=traffic.datetime)
    
    cyear = jdt.now().year
    cmonth = jdt.now().month
    cday = jdt.now().day
    cemp = employees[0].id
    try:    
        if form_defaults["year"] and form_defaults["month"] and form_defaults["day"] and form_defaults["emp"]:
            cyear = form_defaults["year"] 
            cmonth = form_defaults["month"]
            cday = form_defaults["day"]
            cemp = int(form_defaults["emp"])
    except:
        pass
    
    return render(request, 'index.html',{'employees':employees,'traffics':traffics,'now_m':now_m, 'cyear':cyear, 'cmonth':cmonth, 'cday':cday, 'cemp':cemp, 'now':jdt.now()})


@login_required(login_url='login')
def report(request,employee_id,from_date,to_date):
    if request.user.is_superuser :
        traffics=[]
        if from_date == '0' and to_date == '0' :
            gto_date=gdt.now().date()
            gfrom_date=(gdt.now() - timedelta(35)).date()
        else :
            
            try:
                gto_date = jdt.strptime(to_date,'%Y-%m-%d').togregorian().date()
                gfrom_date = jdt.strptime(from_date,'%Y-%m-%d').togregorian().date()
                if gto_date < gfrom_date :
                    raise ValidationError
            except:
                raise ValidationError
        
            
        traffics = Traffic.objects.filter(employee__id=int(employee_id)).filter(datetime__date__gte=gfrom_date).filter(datetime__date__lte=gto_date).order_by('datetime')
        employees = Employee.objects.all().order_by('lastname')
        employee = Employee.objects.get(pk=int(employee_id))
        now_m = lambda: int(round(time.time() * 1000))
        for traffic in traffics:
            traffic.datetime = jdt.fromgregorian(date=traffic.datetime)
        
        gdates_list = [gfrom_date + timedelta(days=x) for x in range(0,(gto_date-gfrom_date).days+1)]
        
        dates_list = [ (jdt.fromgregorian(date=d)).date() for d in gdates_list]
        weekdays_list = [ jdt.j_weekdays_fa[jdt.weekday(d)] for d in dates_list]
        
        dates_dic={}
        
        for date_rec in dates_list:
            dates_dic[str(date_rec)] = [t for t in traffics if t.datetime.date() == date_rec]
            
        html_content = "<table id = 'report-result-content'><tbody>"
        
        for i in range(0,len(dates_list)):
            date_info = employee.date_information(gdates_list[i])
            overtimes = date_info['overtimes']
            leaves = date_info['leaves']
            
            l_hours = str(leaves.seconds//3600)
            l_minutes = str((leaves.seconds//60)%60)
            if len(l_minutes) == 1 :
                l_minutes = '0' + l_minutes

            o_hours = str(overtimes.seconds//3600)
            o_minutes = str((overtimes.seconds//60)%60)
            if len(o_minutes) == 1 :
                o_minutes = '0' + o_minutes

            if weekdays_list[i] == 'پنجشنبه' or weekdays_list[i] == 'جمعه' or date_info['holiday']:
                html_content += "<tr> <td class='off-day'>" + str(dates_list[i]) + " ■ </td> <td class='off-day'>" + weekdays_list[i] + "</td>" 
            else:
                html_content += "<tr> <td class='on-day'>" + str(dates_list[i]) + " ■ </td> <td>" + weekdays_list[i] + "</td>" 
            if leaves.seconds == 0 :
                html_content += "<td class='no-leaves-cell'> بدون کسر کار </td> "
            else:
                html_content += "<td class='leaves-cell'>کسر کار: " + str(l_hours) + ":" + str(l_minutes) + "</td>"

            if overtimes.seconds == 0 :
                html_content += "<td class='no-overtimes-cell'> بدون اضافه کار </td> "
            else:
                html_content += "<td class='overtimes-cell'>اضافه کار: " + str(o_hours) + ":" + str(o_minutes) + "</td>"

            for rec in dates_dic[str(dates_list[i])]:
                if rec.arr_dep :
                    if rec.work_or_not:
                        html_content += "<td class='dep_cell no-work' style='background-color:#FFCDD2;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"
                    else:
                        html_content += "<td class='dep_cell' style='background-color:#FFCDD2;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"

                else:
                    if rec.work_or_not:
                        html_content += "<td class='arr_cell no-work' style='background-color:#C8E6C9;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"
                    else:
                        html_content += "<td class='arr_cell' style='background-color:#C8E6C9;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"

            
            html_content += "</tr>"
            
        html_content += "</tbody></table>"
            
        return render(request, 'report.html',{'employees':employees,'traffics':traffics,'now_m':now_m, 'fyear':gfrom_date.year , 'fmonth': (gfrom_date.month-1), 'fday':gfrom_date.day, 'tyear':gto_date.year , 'tmonth': (gto_date.month-1), 'tday':gto_date.day, 'cemp':employee_id ,\
                                              'html_content':html_content, 'dates_list':dates_list })

    else:
        raise PermissionDenied
    
    
@login_required(login_url='login')
def daily(request,delta):
    
    

    traffics=[]
    g_date=(gdt.now() - timedelta(delta)).date()
    
    date = request.GET.get('date', None)
    if date:
        utc_datetime = jdt.strptime(date,'%Y/%m/%d').togregorian()
        g_date = utc_datetime.date()
        date = jdt.strptime(date,'%Y/%m/%d')
    else:
        date = jdt.today()
    
        
    traffics = Traffic.objects.filter(datetime__date=g_date).order_by('employee','datetime')
    employees = Employee.objects.all().order_by('lastname')
    now_m = lambda: int(round(time.time() * 1000))
    for traffic in traffics:
        traffic.datetime = jdt.fromgregorian(date=traffic.datetime)
    
    
    traffic_list={}
    
    html_content = "<table id = 'daily-report-result-content'><tbody>"
    
    for employee in employees:
        traffic_list = [t for t in traffics if t.employee == employee]

        date_info = employee.date_information(g_date)
        overtimes = date_info['overtimes']
        leaves = date_info['leaves']
        
        l_hours = str(leaves.seconds//3600)
        l_minutes = str((leaves.seconds//60)%60)
        if len(l_minutes) == 1 :
            l_minutes = '0' + l_minutes

        o_hours = str(overtimes.seconds//3600)
        o_minutes = str((overtimes.seconds//60)%60)
        if len(o_minutes) == 1 :
            o_minutes = '0' + o_minutes

        html_content += "<tr> <td class='name-cell'> &#9632 " + str(employee) + "</td> " 

        if request.user.is_superuser :
            if leaves.seconds == 0 :
                html_content += "<td class='no-leaves-cell'> بدون کسر کار </td> "
            else:
                html_content += "<td class='leaves-cell'>کسر کار: " + str(l_hours) + ":" + str(l_minutes) + "</td>"

            if overtimes.seconds == 0 :
                html_content += "<td class='no-overtimes-cell'> بدون اضافه کار </td> "
            else:
                html_content += "<td class='overtimes-cell'>اضافه کار: " + str(o_hours) + ":" + str(o_minutes) + "</td>"

            fa_weekday = jdt.j_weekdays_fa[jdt.weekday(date)]
            if  fa_weekday == 'جمعه' :
                jovertimes =overtimes * 0.2857
                jo_hours = str(jovertimes.seconds//3600)
                jo_minutes = str((jovertimes.seconds//60)%60)
                if len(o_minutes) == 1 :
                    jo_minutes = '0' + jo_minutes
                html_content += "<td class='off-day'> اضافه کار مازاد جمعه: " + str(jo_hours) + ":" + str(jo_minutes) + "</td>" 


        for rec in traffic_list:
            if rec.arr_dep :
                if rec.work_or_not:
                    html_content += "<td class='no-work-cell' style='background-color:#ffc5ab;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"
                else:
                    html_content += "<td class='dep-cell' style='background-color:#ffc8cc;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"

            else:
                if rec.work_or_not:
                    html_content += "<td class='no-work-cell' style='background-color:#ffc5ab;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>"          
                else:
                    html_content += "<td class='arr-cell' style='background-color:#a1ffd0;'> " + str(rec.datetime.strftime("%H:%M:%S")) + "</td>" 

        html_content += "</tr>"
        
    html_content += "</tbody></table>"
    
    rdate = jdt.fromgregorian(date=g_date)
    nrdate = jdt.fromgregorian(date=(g_date + timedelta(1)))
    prdate = jdt.fromgregorian(date=(g_date - timedelta(1)))
        
    return render(request, 'daily.html',{'now_m':now_m, 'rdate':rdate, 'ndelta':(delta-1 if delta > 0 else 0), 'pdelta':delta+1 , 'html_content':html_content, 'nrdate':nrdate, 'prdate':prdate })

@login_required(login_url='login')
def final_report(request):
    if request.method == "POST":
        try:
            title = request.POST['title']
        except:
            return 0

        try:
            shift_time = request.POST['shift-time']
        except:
            return 0

        try:
            shift_type = request.POST['shift-type']
        except:
            return 0

        try:
            referred_count = request.POST['referred-count']
        except:
            return 0
        
        if ( title != '') and (shift_time != '') and (shift_type != '') and (referred_count != ''):
            try:
                utc_datetime = jdt.strptime(shift_time,'%Y/%m/%d   %H:%M:%S').togregorian()

                night_referred = request.POST['night-referred']
                night_resident = request.POST['night-resident']
                tech_referred = request.POST['tech-referred']
                all_guard = request.POST['all-guard']

                baton_delivery = True if (request.POST.get('baton-delivery', None))  else False
                cap_delivery = True if (request.POST.get('cap-delivery', None))  else False
                wireless_delivery = True if (request.POST.get('wireless-delivery', None))  else False
                bracelet_delivery = True if (request.POST.get('bracelet-delivery', None))  else False
                safe_delivery = True if (request.POST.get('safe-delivery', None))  else False
                torch_delivery = True if (request.POST.get('torch-delivery', None))  else False
                spray_delivery = True if (request.POST.get('spray-delivery', None))  else False
                monitoring_delivery = True if (request.POST.get('monitoring-delivery', None))  else False
                kolt_delivery = True if (request.POST.get('kolt-delivery', None))  else False
                shoker_delivery = True if (request.POST.get('shoker-delivery', None))  else False
                simulator_delivery = True if (request.POST.get('simulator-delivery', None))  else False
                tempm_delivery = True if (request.POST.get('tempm-delivery', None))  else False

                phone_visit = True if (request.POST.get('phone-visit', None))  else False
                power_house_visit = True if (request.POST.get('power-house-visit', None))  else False
                parking_door_visit = True if (request.POST.get('parking-door-visit', None))  else False
                units_visit = True if (request.POST.get('units-visit', None))  else False
                stores_visit = True if (request.POST.get('stores-visit', None))  else False
                ent_door_visit = True if (request.POST.get('ent-door-visit', None))  else False
                camera_visit = True if (request.POST.get('camera-visit', None))  else False
                roof_door_visit = True if (request.POST.get('roof-door-visit', None))  else False
                juice_house_visit = True if (request.POST.get('juice-house-visit', None))  else False
                lights_visit = True if (request.POST.get('lights-visit', None))  else False
                windows_visit = True if (request.POST.get('windows-visit', None))  else False
                yard_visit = True if (request.POST.get('yard-visit', None))  else False
                fire_box_visit = True if (request.POST.get('fire-box-visit', None))  else False
                elev_p_h_visit = True if (request.POST.get('elev-p-h-visit', None))  else False
                ent_doors_visit = True if (request.POST.get('ent-doors-visit', None))  else False
                power_counter_visit = True if (request.POST.get('power-counter-visit', None))  else False
                
                power_report = request.POST['power-report']
                shift_report = request.POST['shift-report']

                _report = Report()
                _report.from_user = request.user
                _report.title = title
                _report.shift_type = shift_type
                _report.referred_count = referred_count
                _report.night_referred = night_referred
                _report.night_resident = night_resident
                _report.tech_referred = tech_referred
                _report.all_guard = all_guard
                _report.baton_delivery = baton_delivery
                _report.cap_delivery = cap_delivery
                _report.wireless_delivery = wireless_delivery
                _report.bracelet_delivery = bracelet_delivery
                _report.safe_delivery =safe_delivery
                _report.torch_delivery = torch_delivery
                _report.spray_delivery = spray_delivery
                _report.monitoring_delivery = monitoring_delivery
                _report.kolt_delivery = kolt_delivery
                _report.shoker_delivery = shoker_delivery
                _report.simulator_delivery = simulator_delivery
                _report.tempm_delivery = tempm_delivery
                _report.phone_visit = phone_visit
                _report.power_house_visit = power_house_visit
                _report.parking_door_visit = parking_door_visit
                _report.units_visit = units_visit
                _report.stores_visit = stores_visit
                _report.ent_door_visit = ent_door_visit
                _report.camera_visit = camera_visit
                _report.roof_door_visit = roof_door_visit
                _report.juice_house_visit = juice_house_visit
                _report.lights_visit = lights_visit
                _report.windows_visit = windows_visit
                _report.yard_visit = yard_visit
                _report.fire_box_visit = fire_box_visit
                _report.elev_p_h_visit = elev_p_h_visit
                _report.ent_doors_visit = ent_doors_visit
                _report.power_counter_visit = power_counter_visit

                _report.power_report = power_report
                _report.shift_report = shift_report

                _report.date_time = utc_datetime

                _report.save()
                

            except:
                pass


        return redirect("index")
    else:
        delta = int(request.GET.get('delta', 0))
        g_date = (gdt.now() - timedelta(delta)).date()

        
        date = request.GET.get('date', None)
        if date:
            utc_datetime = jdt.strptime(date,'%Y/%m/%d').togregorian()
            g_date = utc_datetime.date()

        
        _last_report = Report.objects.filter(date_time__date=g_date)
        
        now_m = lambda: int(round(time.time() * 1000))

        # if (len(_last_report) > 0) and (not request.user.is_superuser):
            
        #     action = request.GET.get('action', None)
        #     if action == 'verify':
        #         _report = Report.objects.get(date_time__date=g_date)
        #         if not  _report.to_user:
        #             _report.to_user = request.user
        #             _report.save()
        #         return redirect("index")

        #     rjdate = jdt.fromgregorian(date=_last_report[0].date_time.date())
        #     can_verify = (not request.user.is_superuser) and (not _last_report[0].to_user) and (not _last_report[0].from_user == request.user)
        #     return render(request, 'final-view.html', {'now_m':now_m,'report':_last_report[0],'rjdate':rjdate.date(),'can_verify':can_verify})
        # else:
        if request.user.is_superuser :
            try:
                if (len(_last_report) > 0):
                    _last_report = _last_report.first()
                else:
                    if(request.GET.get('direction') == 'next'):
                        _last_report = Report.objects.filter(date_time__date__gte=g_date).order_by("date_time").first()
                    elif(request.GET.get('direction') == 'prev'):
                        _last_report = Report.objects.filter(date_time__date__lte=g_date).order_by("-date_time").first()
                    else:
                        _last_report = Report.objects.all().order_by("-date_time").first()
                    delta = (gdt.now() - _last_report.date_time).days
                if _last_report :
                    rjdate = jdt.fromgregorian(date=_last_report.date_time.date())
                    prev_delta = delta + 1
                    next_delta = 0 if delta == 0 else delta -1
                    return render(request, 'final-view.html', {'now_m':now_m,'report':_last_report,'rjdate':rjdate.date(),'can_verify':False,'next_delta':next_delta,'prev_delta':prev_delta})
                else:
                    return redirect("index")
            except:
                return redirect("index")
    
        return render(request, 'final.html', {'now_m':now_m,})

@csrf_exempt
def daily_information(request):
    if request.method == "POST":
        try:
            
            p_id = request.POST['p_id']
            i_date = request.POST['i_date']
            token = request.POST['token']
            result ={}
            d_result = {}

            if token == 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ':
                from_date = i_date[:-2]+'01'
                from_date = jdt.strptime(from_date,'%Y/%m/%d')
                if from_date.month == 12 :
                    to_date = jdt(year=from_date.year+1,month=1,day=1).togregorian() + timedelta(-1)
                else:
                    to_date = jdt(year=from_date.year,month=from_date.month+1,day=1).togregorian() + timedelta(-1)
                
                from_date = from_date.togregorian()

                days_list = [from_date]

                while(days_list[-1] < to_date):
                    days_list.append(days_list[-1] + timedelta(1))

                employee = Employee.objects.get(pcode=p_id)

                last_enter = None

                if employee.presence == 3:
                    try:
                        last_enter = Traffic.objects.filter(employee = employee, work_or_not = 0,arr_dep = 0).order_by('-datetime')[0].datetime
                    except:
                        pass

                for _date in days_list:
                    data = employee.date_information(_date)
                    data.pop('traffics')
                    data['overtimes']=data['overtimes'].seconds
                    data['delays']=data['delays'].seconds
                    data['leaves']=data['leaves'].seconds
                    data['hurries']=data['hurries'].seconds
                    data['presense']=data['presense'].seconds
                    d_result[jdt.fromgregorian(date = _date).strftime(format='%Y/%m/%d')]=data

                result['days_data']=d_result
                result['employee']={ 'work_start': employee.work_start , 'work_end': employee.work_finish, 'last_enter': last_enter}

                return HttpResponse(json.dumps(result, sort_keys=True, indent=1, cls=DjangoJSONEncoder))
        except:
            return HttpResponseNotFound()

@csrf_exempt
def month_information(request):
    if request.method == "POST":
        try:
            
            p_id = request.POST['p_id']
            i_date = request.POST['i_date']
            token = request.POST['token']
            result ={}
            d_result = {}

            if token == 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ':
                from_date = i_date[:-2]+'01'
                from_date = jdt.strptime(from_date,'%Y/%m/%d')
                if from_date.month == 12 :
                    to_date = jdt(year=from_date.year+1,month=1,day=1).togregorian() + timedelta(-1)
                else:
                    to_date = jdt(year=from_date.year,month=from_date.month+1,day=1).togregorian() + timedelta(-1)
                
                from_date = from_date.togregorian()

                days_list = [from_date]

                while(days_list[-1] < to_date):
                    days_list.append(days_list[-1] + timedelta(1))

                employee = Employee.objects.get(pcode=p_id)

                last_enter = None

                if employee.presence == 3:
                    try:
                        last_enter = Traffic.objects.filter(employee = employee, work_or_not = 0,arr_dep = 0).order_by('-datetime')[0].datetime
                    except:
                        pass

                overtimes=0
                delays=0
                leaves=0
                hurries=0
                presense=0

                for _date in days_list:
                    data = employee.date_information(_date)
                    data.pop('traffics')
                    overtimes+=data['overtimes'].seconds
                    delays+=data['delays'].seconds
                    leaves+=data['leaves'].seconds
                    hurries+=data['hurries'].seconds
                    presense+=data['presense'].seconds

                result['month_data']={'overtimes':overtimes ,'delays':delays, 'leaves':leaves, 'hurries':hurries, 'presense':presense }
                result['employee']={ 'work_start': employee.work_start , 'work_end': employee.work_finish, 'last_enter': last_enter}

                return HttpResponse(json.dumps(result, sort_keys=True, indent=1, cls=DjangoJSONEncoder))
        except:
            return HttpResponseNotFound()

@csrf_exempt
def from_date_information(request):
    if request.method == "POST":
        try:
            
            p_id = request.POST['p_id']
            i_date = request.POST['i_date']
            token = request.POST['token']


            if token == 'NDI5M2VjMDgxNGRmYjlhMDMwNGJmODI5NmIwZTMzYzEwMzM2YzE3NTp7Il9hdXRoX3VzZXJfaWQiOiIzIiwiX2F1dGhfdXNlcl9iYWNrZW5kIjoiZ':
                from_date = gdt.strptime(i_date,'%Y/%m/%d')

                employee = Employee.objects.get(pcode=p_id)

                first_enter = None

                if employee.presence == 3:
                    try:
                        first_enter = Traffic.objects.filter(employee = employee, datetime__gte=from_date, work_or_not = 0,arr_dep = 0).order_by('datetime')[0].datetime
                    except:
                        pass

                

                return HttpResponse(first_enter)
        except:
            return HttpResponseNotFound()