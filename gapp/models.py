from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
import datetime as gdt

# Create your models here.

class Employee(models.Model):
    name = models.CharField(max_length=250,blank=False,null=False, verbose_name=u'نام')
    lastname = models.CharField(max_length=250,blank=False,null=False, verbose_name=u'نام خانوادگی')
    pcode = models.CharField(max_length=10,blank=False,null=False, verbose_name=u'کد پرسنلی')
    # avatar = models.ImageField(upload_to='', blank=False,null=False, verbose_name=u'تصویر')
    employment_choice = (
        (0,'رسمی'),
        (1,'قراردادی'),
    )
    employment = models.IntegerField(choices=employment_choice, blank=False, null=False, verbose_name=u'نوع استخدام')

    work_start = models.TimeField(blank=False, null=False, default=gdt.time(8,0), verbose_name=u'ساعت شروع به کار')
    work_finish = models.TimeField(blank=False, null=False, default=gdt.time(16,50), verbose_name=u'ساعت خاتمه کار')
    last_traffic_time = models.DateTimeField(default=timezone.now, blank=False, null=False, verbose_name=u'زمان  آخرین تردد')
    last_traffic_a_or_d = models.BooleanField(blank=False, null=False, default=True, verbose_name=u'ورود یا خروج بودن آخرین تردد')
    last_traffic_w_or_n = models.BooleanField(blank=False, null=False, default=True, verbose_name=u'کاری یا غیر بودن آخرین تردد')

    def __str__(self):
        return self.name + ' ' + self.lastname

    class Meta:
        verbose_name = u"نیرو"
        verbose_name_plural = u"نیروها"

    # @property
    # def avatar_url(self):
    #     if self.avatar:
    #         return settings.MEDIA_URL+str(self.avatar)
    #     else:
    #         return ""

    @property
    def work_sfree(self):
        return (gdt.datetime.combine(gdt.date.today(), self.work_start) + gdt.timedelta(minutes=16) ).time()

    @property
    def work_ffree(self):
        return (gdt.datetime.combine(gdt.date.today(), self.work_finish) - gdt.timedelta(minutes=10)).time() if self.employment_choice == 0 else (gdt.datetime.combine(gdt.date.today(), self.work_finish) - gdt.timedelta(minutes=15)).time()

    @property
    def presence(self):
        # presence status
        # 0 : no traffic today
        # 1 : gone
        # 3 : present and working
        # 4 : present but not working
        try:
            g_date= gdt.datetime.now().date()
            if self.last_traffic_time.date() == g_date:
                if self.last_traffic_a_or_d == 1 :
                    return 1
                else:
                    if self.last_traffic_w_or_n :
                        try:
                            last_work_traffic = Traffic.objects.filter(employee = self, work_or_not = 0).order_by('-datetime')[0]
                            if last_work_traffic.arr_dep == 0:
                                return 3
                            else:
                                return 4
                        except:
                            return 4
                    else:
                        return 3
            else:
                if self.last_traffic_a_or_d == 1 :
                    return 0
                else:
                    if self.last_traffic_w_or_n:
                        try:
                            last_work_traffic = Traffic.objects.filter(employee = self, work_or_not = 0).order_by('-datetime')[0]
                            if last_work_traffic.arr_dep == 0:
                                return 3
                            else:
                                return 4
                        except:
                            return 4
                    else:
                        return 3
        except:
            return 0




    def date_information(self,date):
        _traffics = Traffic.objects.filter(employee = self, datetime__date = date, work_or_not = 0).order_by('datetime')
        _traffic_pairs = []
        _delays = gdt.timedelta()
        _hurries = gdt.timedelta()
        _leaves = gdt.timedelta()
        _overtimes = gdt.timedelta()
        _presense = gdt.timedelta()
        _leave_day = 0
        _is_first = 0
        _traffics = list(_traffics)
        # add extra traffic for handling current present employees statistics calculation
        if len(_traffics) and _traffics[-1].datetime.date() == gdt.datetime.now().date() and _traffics[-1].arr_dep == 0 :
            _traffic = Traffic()
            _traffic.employee = self
            _traffic.datetime = gdt.datetime.now()
            _traffic.creator = User.objects.first()
            _traffic.arr_dep = 1
            _traffic.work_or_not = 0
            _traffics.append(_traffic)

        _hday_or_thu = Holiday.objects.filter(date = date).exists() or ( date.weekday() == 3 )
        _fri = ( date.weekday() == 4 )

        _tcount = len(_traffics)
        
        for i in range(_tcount-1):
            if _traffics[i].arr_dep == 0 and _traffics[i+1].arr_dep == 1:
                end = _traffics[i+1].datetime
                start = _traffics[i].datetime
                _traffic_pairs.append([start,end])
                if _is_first == 0 :
                    _is_first = 1
                else :
                    _is_first = 2
                
                next_start = None
                j = i+2
                while j < _tcount :
                    if _traffics[j].arr_dep == 0 :
                        next_start = _traffics[i+2].datetime
                        break
                    else:
                        j += 1
                    
                _presense += end - start
                if _fri :
                    if self.employment == 1:
                        _overtimes += (1.4 * (end - start))
                    else :
                        _overtimes += end - start
                elif _hday_or_thu :
                    _overtimes += end - start
                else:
                    if start < gdt.datetime.combine(date, self.work_start) :
                        if end < gdt.datetime.combine(date, self.work_start) :
                            _overtimes += end - start
                            if next_start:
                                if next_start >= gdt.datetime.combine(date, self.work_sfree) and next_start < gdt.datetime.combine(date, self.work_finish) :
                                    _leaves += next_start - gdt.datetime.combine(date, self.work_start)
                                    _delays += next_start - gdt.datetime.combine(date, self.work_start)
                                if next_start >= gdt.datetime.combine(date, self.work_finish):
                                    _leave_day = 1
                        else:
                            _overtimes +=  gdt.datetime.combine(date, self.work_start) - start
                            if end >= gdt.datetime.combine(date, self.work_ffree):
                                if end > gdt.datetime.combine(date, self.work_finish):
                                    _overtimes += end - gdt.datetime.combine(date, self.work_finish)
                                    
                            else:
                                if next_start:
                                    if next_start < gdt.datetime.combine(date, self.work_finish):
                                        _leaves += next_start - end
                                    else:
                                        _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                else:
                                    _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                    _hurries = gdt.datetime.combine(date, self.work_finish) - end
                    else:
                        if start < gdt.datetime.combine(date, self.work_sfree):
                            if end >= gdt.datetime.combine(date, self.work_ffree):
                                if end > gdt.datetime.combine(date, self.work_finish):
                                    _overtimes += end - gdt.datetime.combine(date, self.work_finish)
                            else:
                                if next_start:
                                    if next_start < gdt.datetime.combine(date, self.work_finish):
                                        _leaves += next_start - end
                                    else:
                                        _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                else:
                                    _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                    _hurries = gdt.datetime.combine(date, self.work_finish) - end
                        else:
                            if start >= gdt.datetime.combine(date, self.work_finish):
                                _leave_day = 1
                                _overtimes += end - start
                            else:
                                if _is_first == 1 :
                                    _leaves += start - gdt.datetime.combine(date, self.work_start)
                                    _delays += start - gdt.datetime.combine(date, self.work_start)
                                if end >= gdt.datetime.combine(date, self.work_ffree):
                                    if end > gdt.datetime.combine(date, self.work_finish):
                                        _overtimes += end - gdt.datetime.combine(date, self.work_finish)
                                else:
                                    if next_start:
                                        if next_start < gdt.datetime.combine(date, self.work_finish):
                                            _leaves += next_start - end
                                        else:
                                            _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                    else:
                                        _leaves += gdt.datetime.combine(date, self.work_finish) - end
                                        _hurries = gdt.datetime.combine(date, self.work_finish) - end

        if _leaves > gdt.timedelta(hours=4):
            _leave_day = 1
            # _overtimes += ( gdt.datetime.combine(date, self.work_finish) - gdt.datetime.combine(date, self.work_start)) - _leaves
        
        return {'traffics':_traffics, 'traffic_pairs':_traffic_pairs, 'hurries':_hurries, 'delays':_delays, 'leaves':_leaves, 'overtimes':_overtimes, 'presense':_presense, 'leave_day':_leave_day, 'holiday':Holiday.objects.filter(date = date).exists()}                


class Traffic(models.Model):
    employee = models.ForeignKey(Employee, blank=False, null=False, related_name="traffics",on_delete=models.CASCADE, verbose_name=u'نیرو')
    creator = models.ForeignKey(User, blank=False, null=False, related_name="traffics",on_delete=models.PROTECT, verbose_name=u'کاربر ثبت کننده')
    datetime = models.DateTimeField(default=timezone.now, blank=False, null=False, verbose_name=u'زمان تردد')
    arr_or_dep_choice = (
        (0,'ورود'),
        (1,'خروج'),
    )
    arr_dep = models.IntegerField(choices=arr_or_dep_choice, blank=False, null=False, verbose_name=u'ورود یا خروج')

    work_or_not_choice = (
        (0,'کاری'),
        (1,'غیرکاری'),
    )
    work_or_not = models.IntegerField(choices=work_or_not_choice, blank=True, null=True, default=0, verbose_name=u'تردد کاری یا غیر کاری')

    def __str__(self):
        return str(self.employee)

    class Meta:
        verbose_name = u"تردد"
        verbose_name_plural = u"ترددها"
        indexes = [
            models.Index(fields=['-datetime',]),
        ]


class Report(models.Model):
    from_user = models.ForeignKey(User, blank=False, null=False, related_name="from_reports",on_delete=models.PROTECT, verbose_name=u'تحویل دهنده شیفت')

    title = models.CharField(max_length=100,blank=False,null=False, verbose_name=u'عنوان رده')
    shift_type = models.CharField(max_length=100,blank=False,null=False, verbose_name=u'نوع شیفت روزانه')
    
    referred_count = models.SmallIntegerField(blank=False,null=False, verbose_name=u'تعداد کل افراد مراجعه کننده به رده')

    night_referred = models.TextField(verbose_name=u'تعداد و اسامی پرسنلی که بعد از ساعت 21 تردد داشتند')
    night_resident = models.TextField(verbose_name=u'تعداد و لیست پرسنلی که در شب اقامت داشتند')

    tech_referred = models.TextField(verbose_name=u'تعداد و اسامی افرادی که برای امور خدماتی و مهندسی تردد داشتند')

    all_guard = models.TextField(blank=False,null=False,verbose_name=u'تعداد و اسامی نگهبانان حاضر')

    baton_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل باتوم')
    cap_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل کلاه')
    wireless_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل بیسیم')
    bracelet_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل دستبند')
    safe_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل گاوصندوق')
    torch_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل چراغ قوه')
    spray_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل افشانه')
    monitoring_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل مانیتورینگ')
    kolt_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل سلاح کمری')
    shoker_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل شوکر')
    simulator_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل شبیه ساز')
    tempm_delivery = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'تحویل تب سنج')

    phone_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید تلفن ها')
    power_house_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید موتورخانه')
    parking_door_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید درب پارکینگ')
    units_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید واحدها')
    stores_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید انبارها')
    ent_door_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید درب ورودی')
    camera_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید دوربین ها')
    roof_door_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید درب پشت بام')
    juice_house_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید آبدارخانه و سماور برقی')
    lights_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید لامپ ها و روشنایی ها')
    windows_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید پنجره اتاق ها')
    yard_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید حیاط')
    fire_box_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید کپسول آتش نشانی')
    elev_p_h_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید موتورخانه آسانسور')
    ent_doors_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید درب های ورودی')
    power_counter_visit = models.BooleanField(default=False, blank=False, null=False, verbose_name=u'بازدید درب کنتور برق')

    power_report = models.TextField(verbose_name=u'گزارش تعداد و مدت قطعی های برق')
    shift_report = models.TextField(verbose_name=u'گزارش شیفت')

    date_time = models.DateTimeField(blank=False,null=False,verbose_name=u'زمان تحویل')

    created = models.DateTimeField(auto_now_add=True,null=True)

    class Meta:
        verbose_name = u"گزارش روزانه"
        verbose_name_plural = u"گزارش های روزانه"


    def __str__(self):
        return str(self.date_time)

class Holiday(models.Model):
    date = models.DateField( blank=False, null=False, verbose_name=u'روزهای تعطیل')

    class Meta:
        verbose_name = u"تعطیل رسمی غیر جمعه"
        verbose_name_plural = u"تعطیلات رسمی غیر جمعه"
