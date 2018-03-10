# -*- coding: utf-8 -*-
#     Github.com/Rasooll
from bottle import route,template, static_file, request, redirect, get,run
import pymysql.cursors
from zeep import Client
from config import *

def MakeMySqlConncetion():
    global connection
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)
    return connection

client = Client('https://www.zarinpal.com/pg/services/WebGate/wsdl')
error_list = {
    '100': 'عملیات با موفقیت انجام گردیده است.',
    '101': 'عملیات پرداخت موفق بوده و قبلا صحت تراکنش بررسی شده است',
    '-1': 'اطلاعات ارسال شده ناقص است',
    '-2': 'مرچنت کد و یا آی‌پی آدرس پذیرنده صحیح نیست',
    '-3': 'باتوجه به محدودیت های شاپرک امکان پرداخت با رقم درخواست شده میسر نمی‌باشد.',
    '-4': 'سطح تایید پذیرنده پایین تر از سطح نقره‌ای است',
    '-11': 'درخواست مورد نظر یافت نشد',
    '-12': 'امکان ویرایش درخواست میسر نمی‌باشد',
    '-21': 'هیچ نوع عملیات مالی برای این تراکنش یافت نشد',
    '-22': 'تراکنش ناموفق می‌باشد',
    '-33': 'رقم تراکنش با رقم پرداخت شده مطابقت ندارد',
    '-34': 'سقف تقسیم تراکنش از لحاظ تعداد یا رقم عبور نموده است',
    '-40': 'اجازه دسترسی به متد مربوطه وجود ندارد',
    '-41': 'اطلاعات ارسال شده مربوط به AdditionalData غیرمعتبر می‌باشد',
    '-42': 'مدت زمان معتبر طول عمر شناسه پرداخت باید بین 30 دقیقه تا 45 روز ‌باشد',
    '-54': 'درخواست مورد نظر آرشیو شده است'}

@route('/<:re:[\/static$]+>/<filename>')
def server_static(filename):
    return static_file(filename, root='./static')

@route('/')
@route('/<:re:[\/$]+>')
def index():
    pm = {'index': INDEX_URL}
    return template('./tpl/main.tpl', pm)

@route('/<:re:[\/install$]+>')
def install_func():
    try:
        MakeMySqlConncetion()
        with connection.cursor() as cursor:
            sql = '''CREATE TABLE IF NOT EXISTS info (
                name TEXT,
                email TEXT,
                price TEXT,
                description TEXT,
                authority TEXT,
                refID TEXT,
                status TEXT
                )CHARSET=utf8 COLLATE=utf8_bin;'''
            cursor.execute(sql)
        connection.commit()
    finally:
        connection.close()
        pm = {'index': INDEX_URL,'title': 'پایان فرایند تنظیمات', 'content': 'فرآیند ایجاد جداول بانک اطلاعاتی به پایان رسید.'}
        return template('./tpl/success.tpl', pm)

@get('/<:re:[\/request$]+>')
def makerequest():
    name = request.query.name
    email = request.GET.get("email")
    price = request.GET.get("price")
    description = request.query.description
    if email and price :
        result = client.service.PaymentRequest(MERCHANT, price, description, email,'', CallbackURL)
        if result.Status == 100:
            authority = str(result.Authority)
            try:
                MakeMySqlConncetion()
                with connection.cursor() as cursor:
                    # Create a new record
                    sql = "INSERT INTO info (name, email, price, description, authority) VALUES (%s, %s, %s, %s, %s)"
                    cursor.execute(sql, (name, email, price, description, authority))
                connection.commit()
            finally:
                connection.close()
                redirect('https://www.zarinpal.com/pg/StartPay/' + str(result.Authority))
        else:
            errtext ={'index': INDEX_URL,'errorText': error_list[str(result.Status)]}
            return template('./tpl/error.tpl', errtext)
    else:
        errtext ={'index': INDEX_URL, 'errorText': 'هیچ اطلاعاتی ارسال نشده است'}
        return template('./tpl/error.tpl', errtext)

@get('/<:re:[\/verify$]+>')
def verify_func():
    if request.GET.get('Status') == 'OK':
        authority = str(request.GET['Authority'])
        MakeMySqlConncetion()
        with connection.cursor() as cursor:
            sql = "SELECT price,authority FROM info WHERE authority=%s"
            cursor.execute(sql, (authority,))
            sqldata = cursor.fetchone()
            price = int(sqldata['price'])
        result = client.service.PaymentVerification(MERCHANT, authority, price)
        if result.Status == 100:
            with connection.cursor() as cursor:
                sql2 = "UPDATE info SET status='OK',refID=%s WHERE authority=%s"
                cursor.execute(sql2, (str(result.RefID),authority,))
            connection.commit()
            connection.close()
            pm = {'index': INDEX_URL, 'refID': str(result.RefID)}
            return template('./tpl/payment-ok.tpl', pm)
        elif result.Status == 101:
            pm = {'index': INDEX_URL, 'title': 'نتیجه بررسی وضعیت پرداخت', 'content': 'پرداخت شما قبلا تایید شده است'}
            return template('./tpl/info.tpl', pm)
        else:
            pm = {'index': INDEX_URL, 'errorText': error_list[result.Status]}
            return template('./tpl/error.tpl', pm)
    elif request.GET.get('Status') == 'NOK':
        pm = {'index': INDEX_URL, 'errorText': 'تراکنش ناموفق بوده و یا توسط کاربر لغو گردیده است'}
        return template('./tpl/error.tpl', pm)
    else:
        pm = {'index': INDEX_URL, 'errorText': 'هیچ تراکنشی انجام نشده است'}
        return template('./tpl/error.tpl', pm)

@route('/<:re:[\/admin$]+>')
def admin_func():
    pm = {'index': INDEX_URL, 'title': 'در دست طراحی', 'content': 'بخش مدیریت در نسخه‌های آینده‌ی این اسکریپت اضافه خواهد شد.'} 
    return template('./tpl/info.tpl', pm)

run(host='localhost', port=8080)