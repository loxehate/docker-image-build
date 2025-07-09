
import re
from datetime import datetime,timedelta

static_stringArray = {
    "Y年M月d日": 1,
    "Y/M/d": 2,
    "yyyy-MM-dd": 3,
    "yyyy.MM.dd": 4,
    "中文_零": 5,
    "中文_〇": 6,
    "周几": 7,
    "星期": 8,
    "中文hour12": 9,
    "HH:mm": 10,
    "中文": 11,
    "格式1": 1,
    "格式2": 2,
    "格式3": 3,
    "格式4": 4,
    "格式5": 5,
    "格式6": 6,
    "格式7": 7
}


def get_date():
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute
    second = now.second
    return [year, month, day, hour, minute, second]


def get_input_date(intput_date_time):
    now = intput_date_time
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour
    minute = now.minute
    second = now.second
    return [year, month, day, hour, minute, second]


def get_week_for_style(intput_date_time, type):
    if type == 7 or type == 8:
        now = intput_date_time
        week = now.strftime('%w')
        if type == 7:
            week_str = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        elif type == 8:
            week_str = ["星期天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
        week_int = int(week)
        return week_str[week_int]
    else:
        return ""


def get_date_for_style(intput_date_time, type):
    if type == 1:
        date_time = get_input_date(intput_date_time)
        return str(date_time[0]) + "年" + str(date_time[1]) + "月" + str(date_time[2]) + "日"
    elif type == 2:
        date_time = get_input_date(intput_date_time)
        return str(date_time[0]) + "/" + str(date_time[1]) + "/" + str(date_time[2]) + "/"
    elif type == 3:
        now = intput_date_time
        return now.strftime('%Y-%m-%d')
    elif type == 4:
        now = intput_date_time
        return now.strftime('%Y.%m.%d')
    elif type == 5 or type == 6 or type == 9 or type == 10 or type == 11:
        date_time = get_input_date(intput_date_time)
        num_chinese = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
        year_chinese = num_chinese[int(date_time[0] / 1000)] + num_chinese[int(date_time[0] / 100) % 10] + num_chinese[
            int(date_time[0] / 10) % 10] + num_chinese[date_time[0] % 10]
        if date_time[1] == 10:
            month_chinese = "十"
        elif date_time[1] > 10 and date_time[1] <= 12:
            month_chinese = "十" + num_chinese[date_time[1] % 10]
        elif date_time[1] > 0 and date_time[1] < 10:
            month_chinese = num_chinese[date_time[1] % 10]
        else:
            month_chinese = ""
        ################################################################
        if date_time[2] == 10:
            day_chinese = "十"
        elif date_time[2] == 20:
            day_chinese = "二十"
        elif date_time[2] == 30:
            day_chinese = "三十"
        elif date_time[2] > 10 and date_time[2] <= 19:
            day_chinese = "十" + num_chinese[date_time[2] % 10]
        elif date_time[2] > 19 and date_time[2] <= 31:
            day_chinese = num_chinese[int(date_time[2] / 10)] + "十" + num_chinese[date_time[2] % 10]
        elif date_time[2] > 0 and date_time[2] < 10:
            day_chinese = num_chinese[date_time[2] % 10]
        else:
            day_chinese = ""
        if type == 5:
            return year_chinese + "年" + month_chinese + "月" + day_chinese + "日"
        elif type == 6:
            return (year_chinese + "年" + month_chinese + "月" + day_chinese + "日").replace("零", "〇")
        elif type == 9 or type == 10 or type == 11:
            now = intput_date_time
            hour_24 = int(now.strftime('%H'))
            hour_12 = int(now.strftime('%I'))
            minute = int(now.strftime('%M'))
            if type == 9:
                if hour_24 < 12:
                    return "上午" + str(hour_24) + ":" + now.strftime('%M')
                else:
                    return "下午" + str(hour_24) + ":" + now.strftime('%M')
            elif type == 10:
                return str(hour_24) + ":" + now.strftime('%M')
            elif type == 11:
                str_temp = ""
                if hour_24 < 12:
                    str_temp = "上午"
                else:
                    str_temp = "下午"
                digital_array = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
                if hour_12 >= 10:
                    str_temp = str_temp + "十"
                    if hour_12 > 10:
                        str_temp = str_temp + str(digital_array[hour_12 % 10])
                elif hour_12 < 10 and hour_12 >= 0:
                    str_temp = str_temp + str(digital_array[hour_12])
                str_temp = str_temp + "点"
                if minute >= 0 and minute <= 9:
                    str_temp = str_temp + digital_array[int(minute)]
                elif minute == 10:
                    str_temp = str_temp + "十"
                elif minute > 10 and minute <= 19:
                    str_temp = str_temp + "十" + digital_array[int(minute % 10)]
                elif minute > 10 and minute <= 59:
                    if int(minute % 10) == 0:
                        str_temp = str_temp + digital_array[int(minute / 10)] + "十"
                    else:
                        str_temp = str_temp + digital_array[int(minute / 10)] + "十" + digital_array[int(minute % 10)]
                str_temp = str_temp + "分"

                return str_temp
    else:
        return ""


def get_local_date(type):
    if type >= 1 and type <= 6:
        return get_date_for_style(datetime.now(), type)
    elif type >= 7 and type <= 8:
        return get_week_for_style(datetime.now(), type)
    else:
        return ""


def dateFormat(_str_type, _date):  # 日期格式filter
    global static_stringArray

    if re.search("^[0-9]{1,4}-[0-9]{1,2}-([0-9]{1,2})$", _date) == None:
        return ''
    if static_stringArray.get(_str_type, -1) != -1:
        type = static_stringArray[_str_type]
    else:
        return ''
    temp_date = _date + " 00:00"
    return get_all_kinds_date_time(temp_date, type)


def timeFormat(_str_type, _time):  # 时间格式
    global static_stringArray

    if re.search("^[0-9]{1,2}:([0-9]{1,2})$", _time) == None:
        return ''
    if static_stringArray.get(_str_type, -1) != -1:
        type = static_stringArray[_str_type]
    else:
        return ''
    temp_time = "2019-01-01 " + _time
    return get_all_kinds_date_time(temp_time, type)


def dateFormatRe(_date, _str_type):  # 日期格式filter
    return dateFormat(_str_type,_date)


def timeFormatRe(_time, _str_type):  # 时间格式
    return timeFormat(_str_type,_time)


def numbersToThousandmark(_numbers):  # 数字千分符格式
    global static_stringArray
    if isinstance(_numbers, int) == False and isinstance(_numbers, float) == False:
        return ''
    return "{:,}".format(_numbers)


def getBillNumberFormat(_type, _str_bill_num):
    global static_stringArray
    if static_stringArray.get(_type, -1) == -1:
        return ''
    else:
        type = static_stringArray[_type]
    return get_bill_all_kinds_serial_number(_str_bill_num, type)


def getAgendaNumberFormat(_type, _str_agenda_num):
    global static_stringArray
    if static_stringArray.get(_type, -1) == -1:
        return ''
    else:
        type = static_stringArray[_type]
    return get_agenda_all_kinds_serial_number(_str_agenda_num, type)


def numbersToChinese(type, _numbers):  # 数字转中文格式
    global static_stringArray
    if isinstance(_numbers, int) == False:
        return ''
    if static_stringArray.get(type, -1) == -1:
        return ''
    result = []
    num_chinese = {}
    if type == '中文_零':
        num_chinese = {'0': "零", '1': "一", '2': "二", '3': "三", '4': "四", '5': "五", '6': "六", '7': "七", '8': "八",
                       '9': "九"}
    elif type == '中文_〇':
        num_chinese = {'0': "〇", '1': "一", '2': "二", '3': "三", '4': "四", '5': "五", '6': "六", '7': "七", '8': "八",
                       '9': "九"}
    else:
        return ''
    num = int(_numbers)
    numbers = str(num)
    result = map(lambda x: num_chinese[x], numbers)
    return ''.join(result)


def numberValueToChinese(digital):
    if isinstance(digital, int) == False:
        return ''
    str_digital = str(int(digital))
    chinese = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五', '6': '六', '7': '七', '8': '八', '9': '九', '0': '零'}
    chinese2 = ['十', '百', '千', '万']
    jiao = ''
    bs = str_digital.split('.')
    yuan = bs[0]
    if len(bs) > 1:
        jiao = bs[1]
    r_yuan = [i for i in reversed(yuan)]
    count = 0
    for i in range(len(yuan)):
        if i == 0:
            r_yuan[i] += ''
            continue
        r_yuan[i] += chinese2[count]
        count += 1
        if count == 4:
            count = 0
            chinese2[3] = '亿'

    s_jiao = [i for i in jiao][:3]  #

    j_count = -1
    for i in range(len(s_jiao)):
        s_jiao[i] += chinese2[j_count]
        j_count -= 1
    last = [i for i in reversed(r_yuan)] + s_jiao

    last_str = ''.join(last)
    for i in range(len(last_str)):
        digital = last_str[i]
        if digital in chinese:
            last_str = last_str.replace(digital, chinese[digital])
    last_str = last_str.replace('零千零百零十', '零')
    last_str = last_str.replace('零千零百', '零')
    last_str = last_str.replace('零千', '零')
    last_str = last_str.replace('零百', '零')
    last_str = last_str.replace('零十', '零')
    last_str = last_str.replace('零零', '零')

    try:
        if last_str.index("一十") == 0:
            last_str = last_str.replace("一十", '十')
    except:
        pass
    if last_str == '十零':
        last_str = '十'
    return last_str


def itemIncludedByList(_list: list, _item):
    try:
        _list.index(_item)
    except:
        return False
    return True


def datePlusAndSubtract(_strDateTime, _strValue, _tag):
    # 12年1月6日4时8分9秒
    year = 0
    month = 0
    day = 0
    hour = 0
    minute = 0
    second = 0
    week = 0
    date_type = 0
    if re.search("^[0-9]{1,4}-[0-9]{1,2}-([0-9]{1,2})$", _strDateTime):
        pass
        date_type = 1
    elif re.search("^[0-9]{1,2}:([0-9]{1,2})$", _strDateTime):
        date_type = 2
        pass
    else:
        return ''
    years = re.findall("[0-9]{1,4}(?=年)", _strValue, 0)
    months = re.findall("[0-9]{1,2}(?=月)", _strValue, 0)
    days = re.findall("[0-9]{1,2}(?=天)", _strValue, 0)
    hours = re.findall("[0-9]{1,2}(?=时)", _strValue, 0)
    minutes = re.findall("[0-9]{1,2}(?=分)", _strValue, 0)
    seconds = re.findall("[0-9]{1,2}(?=秒)", _strValue, 0)
    weeks = re.findall("[0-9]{1,10}(?=周)", _strValue, 0)
    if len(years) > 0: year = int(years[0])
    if len(months) > 0: month = int(months[0])
    if len(days) > 0: day = int(days[0])
    if len(hours) > 0: hour = int(hours[0])
    if len(minutes) > 0: minute = int(minutes[0])
    if len(seconds) > 0: second = int(seconds[0])
    if len(weeks) > 0: week = int(weeks[0])

    str_type = ''
    if date_type == 1:
        str_type = "%Y-%m-%d"
    else:
        str_type = "%H:%M"
    d_t = datetime.strptime(_strDateTime, str_type)

    if _tag == '前':
        pass
        dt = d_t - datetime.timedelta(weeks=week, days=day, hours=hour, minutes=minute, seconds=second)
        str_dt = dt.strftime(str_type)
        return str_dt
    elif _tag == '后':
        dt = d_t + datetime.timedelta(weeks=week, days=day, hours=hour, minutes=minute, seconds=second)
        str_dt = dt.strftime(str_type)
        return str_dt
    else:
        return ''


def get_local_week(type):
    now = datetime.now()
    return get_week_for_style(now, type)


def get_stylenum_from_str(new_num_string, grade, type):
    array_last_num = [["", "", "", "", "", "", "", ""] for i in range(4)]
    num_chinese = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    s_a = new_num_string.split(".")
    s_a.append("0");
    s_a.append("0");
    s_a.append("0");
    s_a.append("0");
    s_a.append("0")
    if int(s_a[0]) >= 100 or int(s_a[1]) >= 100 or int(s_a[2]) >= 100:
        return ""
    ####################################################################################
    if int(s_a[0]) < 20 and int(s_a[0]) >= 10:
        if int(s_a[0]) % 10 == 0:
            last_get_bill_num_c = "十"
        else:
            last_get_bill_num_c = "十" + num_chinese[int(int(s_a[0]) % 10)]
    elif int(s_a[0]) >= 20:
        if int(s_a[0]) % 10 == 0:
            last_get_bill_num_c = num_chinese[int(int(s_a[0]) / 10)] + "十"
        else:
            last_get_bill_num_c = num_chinese[int(int(s_a[0]) / 10)] + "十" + num_chinese[int(int(s_a[0]) % 10)]
    else:
        last_get_bill_num_c = num_chinese[int(s_a[0])]
    #####################################################################################三级议案分类设置
    array_last_num[1][1] = new_num_string
    array_last_num[1][2] = "（" + last_get_bill_num_c + "）"
    array_last_num[1][3] = last_get_bill_num_c
    array_last_num[1][4] = last_get_bill_num_c
    array_last_num[1][5] = s_a[0]
    array_last_num[1][6] = "议案" + last_get_bill_num_c
    array_last_num[1][7] = "议案" + s_a[0]
    #####################################################################################
    array_last_num[2][1] = new_num_string
    array_last_num[2][2] = str(int(s_a[1]))
    array_last_num[2][3] = str(int(s_a[1]))  # str(int(s_a[0]))+"."+str(int(s_a[1]))
    array_last_num[2][4] = str(int(s_a[0])) + "." + str(int(s_a[1]))
    array_last_num[2][5] = str(int(s_a[0])) + "." + str(int(s_a[1]))
    array_last_num[2][6] = str(int(s_a[1]))
    array_last_num[2][7] = str(int(s_a[1]))
    #####################################################################################
    array_last_num[3][1] = new_num_string
    array_last_num[3][2] = "（" + str(int(s_a[2])) + "）"
    array_last_num[3][3] = "（" + str(int(s_a[2])) + "）"
    array_last_num[3][4] = str(int(s_a[0])) + "." + str(int(s_a[1])) + "." + str(int(s_a[2]))
    array_last_num[3][5] = str(int(s_a[0])) + "." + str(int(s_a[1])) + "." + str(int(s_a[2]))
    array_last_num[3][6] = "（" + str(int(s_a[2])) + "）"
    array_last_num[3][7] = "（" + str(int(s_a[2])) + "）"
    #####################################################################################
    return array_last_num[grade][type]


#####jinja2中自定义的filters#################
#############################################
#####小数点后保留格式####################
def get_decimal_point_reservation(num, num_fater):
    if num_fater < 0:
        num_fater = 0
    num_float = float(num)
    c = "%(number)." + str(num_fater) + "f"
    return c % {'number': num_float}


#####特别决议议案编号格式####################
def get_style_special_resolution_num(num_string, type):
    if type >= 5 or type <= 0:
        return ""
    num = int(num_string)
    if num >= 100:
        return ""
    num_chinese = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    ####################################################################################
    if num < 20 and num >= 10:
        if num % 10 == 0:
            result_c = "十"
        else:
            result_c = "十" + num_chinese[num % 10]
    elif num >= 20:
        if num % 10 == 0:
            result_c = num_chinese[int(num / 10)] + "十"
        else:
            result_c = num_chinese[int(num / 10)] + "十" + num_chinese[num % 10]
    else:
        result_c = num_chinese[num]
    if type == 1:
        return result_c
    elif type == 2:
        return num_string
    elif type == 3:
        return "议案" + result_c
    elif type == 4:
        return "议案" + num_string


#####各种附件序号格式########################
def get_style_appendix_num(num_string, type):
    if type >= 6 or type <= 0:
        return ""
    num = int(num_string)
    if num >= 100:
        return ""
    num_chinese = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    ####################################################################################
    if num < 20 and num >= 10:
        if num % 10 == 0:
            result_c = "十"
        else:
            result_c = "十" + num_chinese[num % 10]
    elif num >= 20:
        if num % 10 == 0:
            result_c = num_chinese[int(num / 10)] + "十"
        else:
            result_c = num_chinese[int(num / 10)] + "十" + num_chinese[num % 10]
    else:
        result_c = num_chinese[num]
    if type == 1:
        return "附件" + num_string
    elif type == 2:
        return result_c
    elif type == 3:
        return "（" + result_c + "）"
    elif type == 4:
        return num_string
    elif type == 5:
        return "（" + num_string + "）"


def get_agenda_all_kinds_serial_number(num, type):
    if len(num) == 0:
        return ""
    if type <= 0 or type >= 4:
        return ""
    grade = 1
    temp_num = num
    new_array_str = []
    new_num_string = ""  # 形如:1或1.12
    if num.find(".") == -1:
        temp_num = str(num)
        new_num_string = temp_num
        grade = 1
    else:
        array_str = temp_num.split(".")
        grade = len(array_str)
        for iterating_var in array_str:
            if int(iterating_var) <= 9:
                c = "%(number)d" % {'number': int(iterating_var)}
                new_array_str.append(c)
            else:
                new_array_str.append(iterating_var)
        new_array_str[0] = str(int(new_array_str[0]))
        new_num_string = new_array_str[len(new_array_str) - 1]
    return get_agenda_stylenum_from_str(new_num_string, grade, type)


def get_agenda_stylenum_from_str(new_num_string, grade, type):
    array_last_num = [["", "", "", ""] for i in range(3)]
    num_chinese = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    s_a = new_num_string
    if int(s_a) >= 100:
        return ""
    ####################################################################################
    if int(s_a) < 20 and int(s_a) >= 10:
        if int(s_a) % 10 == 0:
            last_get_bill_num_c = "十"
        else:
            last_get_bill_num_c = "十" + num_chinese[int(int(s_a) % 10)]
    elif int(s_a) >= 20:
        if int(s_a) % 10 == 0:
            last_get_bill_num_c = num_chinese[int(int(s_a) / 10)] + "十"
        else:
            last_get_bill_num_c = num_chinese[int(int(s_a) / 10)] + "十" + num_chinese[int(int(s_a) % 10)]
    else:
        last_get_bill_num_c = num_chinese[int(s_a)]
    #####################################################################################三级议案分类设置
    array_last_num[1][1] = last_get_bill_num_c  #
    array_last_num[1][2] = new_num_string
    array_last_num[1][3] = "议程" + last_get_bill_num_c
    #####################################################################################
    array_last_num[2][1] = new_num_string
    array_last_num[2][2] = '（' + new_num_string + '）'
    array_last_num[2][3] = new_num_string

    #####################################################################################

    return array_last_num[grade][type]


#####各种议案编号格式########################
def get_bill_all_kinds_serial_number(num, type):
    if len(num) == 0:
        return ""
    if type <= 0 or type >= 12:
        return ""
    grade = 1
    temp_num = num
    new_array_str = []
    new_num_string = ""  # 形如:4.01.02
    if num.find(".") == -1:
        temp_num = str(num) + "." + "00"
        new_num_string = temp_num
        grade = 1
    else:
        array_str = temp_num.split(".")
        grade = len(array_str)
        for iterating_var in array_str:
            if int(iterating_var) <= 9:
                c = "%(number)02d" % {'number': int(iterating_var)}
                new_array_str.append(c)
            else:
                new_array_str.append(iterating_var)
        new_array_str[0] = str(int(new_array_str[0]))
        if new_array_str[grade - 1] == "00":
            grade = grade - 1
        for var_str in new_array_str:
            new_num_string = new_num_string + var_str + "."
        new_num_string = new_num_string[0:len(new_num_string) - 1]

    return get_stylenum_from_str(new_num_string, grade, type)


#####各种日期时间格式########################
def get_all_kinds_date_time(t, type):
    d_t = datetime.strptime(t, "%Y-%m-%d %H:%M")
    if (type >= 1 and type <= 6) or (type >= 9 and type <= 11):
        return get_date_for_style(d_t, type)
    elif type >= 7 and type <= 8:
        return get_week_for_style(d_t, type)
    else:
        return ""


#####召开时间################################
def get_meeting_opened_date(type):
    global context
    meeting_opened_date_time = context["meeting_opened_date_time"]
    return get_all_kinds_date_time(meeting_opened_date_time, type)


#####通知时间################################
def get_meeting_noticed_date(type):
    global context
    meeting_noticed_date_time = context["meeting_noticed_date_time"]
    return get_all_kinds_date_time(meeting_noticed_date_time, type)


#####A股股权登记日###########################
def get_a_bill_registed_date(type):
    global context
    a_bill_registed_date = context["a_bill_registed_date"]
    return get_all_kinds_date_time(a_bill_registed_date, type)


#####B股最后交易日###########################
def get_b_bill_lasttrace_date(type):
    global context
    b_bill_lasttrace_date = context["b_bill_lasttrace_date"]
    return get_all_kinds_date_time(b_bill_lasttrace_date, type)


#####登记时间################################
def get_members_assign_date(type):
    global context
    members_assign_date = context["members_assign_date"]
    return get_all_kinds_date_time(members_assign_date, type)


def add_var_to_context(context):
    context["本机时间1"] = 1
    context["本机时间2"] = 2
    context["本机时间3"] = 3
    context["本机时间4"] = 4
    context["本机时间5"] = 5
    context["本机时间6"] = 6
    context["本机时间对应周几"] = 7
    context["本机时间对应星期几"] = 8
    context["meeting_opened_date_time"] = "2019-11-03 15:20"

    context["召开时间1"] = 9
    context["召开时间2"] = 10
    context["召开时间中文"] = 11
    ###############需求变更后###############################
    context["Y年M月d日"] = 1
    context["Y/M/d"] = 2
    context["yyyy-MM-dd"] = 3
    context["yyyy.MM.dd"] = 4
    context["中文_零"] = 5
    context["中文_〇"] = 6
    context["周几"] = 7
    context["星期"] = 8
    context["中文hour12"] = 9
    context["HH:mm"] = 10
    context["中文"] = 11
    ########################################################

    # context["测试时间"] = "2319-12-13 15:35"
    # context["测试编号"] = "1.00"
    # context["议案编号列表"] = ["2","21.00","11.00","2.03","5.10.23"]


def list_append(_list: list, item):
    _list.append(item)
    return _list


def bigNumberEasyRead(_number):
    if _number == "" or _number == None:
        return ""
    number = int(_number)
    bool_100_million = False
    bool_10_thoudand = False
    _10_thoudand = int(number / 10000)
    _100_million = 0
    _1000_num = number % 10000
    if _10_thoudand > 0:
        _100_million = int(_10_thoudand / 10000)
        _10_thoudand = _10_thoudand % 10000
        if _100_million > 0:
            bool_100_million = True
        if _10_thoudand > 0:
            bool_10_thoudand = True
    result = ''
    if bool_100_million == True:
        result = str(_100_million) + '亿'
    if bool_10_thoudand == True:
        if _10_thoudand < 1000 and _100_million > 0:
            result = result + '零'
        result = result + str(_10_thoudand) + '万'

    if _1000_num < 1000:
        if number >= 10000:
            result = result + '零' + str(_1000_num)
        else:
            result = result + str(_1000_num)
    else:
        result = result + str(_1000_num)
    return result


def myfilter(a):
    return 'nice to meet you'


def getAttendDS(p_list):
    count = 0
    for people in p_list:
        if people['出席人员出席状况'] != '未反馈' and people['出席人员出席状况'] != '缺席':
            count = count + 1
    return str(count)


def getObjectListFromCondition(_obj_list, _condition):
    temp_list = []
    commond = """
for item in _obj_list:
    if item""" + _condition + '  :'"""
        temp_list.append(item)
"""
    exec(commond)
    return temp_list


def getListFromCondition(_list, _value):
    temp_list = []
    commond = """
for item in _obj_list:
    if item""" + _value + ':' + """
        temp_list.append(item)
"""
    exec(commond)
    return temp_list


def getAllYiAnsInSpreadout(_yi_an_list):
    temp_list = []
    _getAllYiAnsInSpreadout(temp_list, _yi_an_list)
    return temp_list


def _getAllYiAnsInSpreadout(temp_list, _yi_an_list):
    for y_a in _yi_an_list:
        temp_list.append(y_a)
        if len(y_a["子议案信息"]) > 0:
            _getAllYiAnsInSpreadout(temp_list, y_a["子议案信息"])


outFilters = [
    {"name": '从源对象列表生成对象列表', "filterfunction": getObjectListFromCondition},
    {"name": '从源列表生成列表', "filterfunction": getListFromCondition},
    {"name": 'hello', "filterfunction": myfilter},
    {"name": '获取出席董事人数', "filterfunction": getAttendDS},
    {"name": '平铺所有议案', "filterfunction": getAllYiAnsInSpreadout},
    {"name": '小数点后保留', "filterfunction": get_decimal_point_reservation},
    {"name": '日期时间格式化', "filterfunction": get_all_kinds_date_time},
    {"name": '议案编号格式化', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '未通过议案编号', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '反对议案编号', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '弃权议案编号', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '非累积投票制议案编号', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '累积投票制议案编号', "filterfunction": get_bill_all_kinds_serial_number},
    {"name": '议案附件序号', "filterfunction": get_style_appendix_num},
    {"name": '特别决议议案编号', "filterfunction": get_style_special_resolution_num},
    {"name": '本机时间', "filterfunction": get_local_date},
    {"name": '召开日期', "filterfunction": get_meeting_opened_date},
    {"name": '召开时间', "filterfunction": get_meeting_opened_date},
    {"name": '通知时间', "filterfunction": get_meeting_noticed_date},
    {"name": 'A股股权登记日', "filterfunction": get_a_bill_registed_date},
    {"name": 'B股最后交易日', "filterfunction": get_b_bill_lasttrace_date},
    {"name": '登记时间', "filterfunction": get_members_assign_date},
    {"name": '日期格式转换', "filterfunction": dateFormat},
    {"name": '日期格式转换re', "filterfunction": dateFormatRe},
    {"name": '时间格式转换', "filterfunction": timeFormat},
    {"name": '时间格式转换re', "filterfunction": timeFormatRe},
    {"name": '数字转中文格式', "filterfunction": numbersToChinese},
    {"name": '数值转中文格式', "filterfunction": numberValueToChinese},
    {"name": '数值转中文格式', "filterfunction": numberValueToChinese},
    {"name": '数值转中文格式', "filterfunction": numberValueToChinese},
    {"name": '数值转中文格式', "filterfunction": numberValueToChinese},
    {"name": '列表是否包含', "filterfunction": itemIncludedByList},
    {"name": '日期加减', "filterfunction": datePlusAndSubtract},
    {"name": '时间加减', "filterfunction": datePlusAndSubtract},
    {"name": '数字千分符格式', "filterfunction": numbersToThousandmark},
    {"name": '议案号转换', "filterfunction": getBillNumberFormat},
    {"name": '议程号转换', "filterfunction": getAgendaNumberFormat},
    {"name": '列表添加元素', "filterfunction": list_append},
    {"name": '大整数易读格式转换', "filterfunction": bigNumberEasyRead},
]
