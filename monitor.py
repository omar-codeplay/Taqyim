import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# =================================================================
# الإعدادات العامة
# =================================================================
# ملاحظة: تم حذف LINK_KEYWORD لأننا سنعتمد على التصفية الآلية
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/"
HISTORY_FILE = "moe_files_history.txt"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "@omar_codeplay"  # تأكد من أن هذا هو اسم المستخدم الصحيح لحسابك

# الكلمات التي سيتم البحث عنها واختيارها (مهمة لعمل Selenium)
STAGE_NAME = "المرحلة الثانوية"
GRADE_NAME = "الصف الثاني الثانوي"
# =================================================================


def send_notification(content, is_status=False):
    """
    يرسل تنبيه أو رسالة حالة إلى قناة/دردشة تيليجرام.
    """
    if not TELEGRAM_BOT_TOKEN:
        print("❌ فشل الإرسال: TELEGRAM_BOT_TOKEN غير متوفر.")
        return

    message_text = ""
    if is_status:
        message_text = content
    else:
        # بناء رسالة التنبيه بالملفات الجديدة
        message_text = f"🚨 *تنبيه: تم العثور على {len(content)} ملف جديد للصف الثاني الثانوي!* 🚨\n\n"
        for link in content:
            # نستبدل .pdf وندع اسم الملف يظهر بشكل أنظف
            name = link.split('/')[-1].replace('.pdf', '') 
            message_text += f"▪️ [{name}]({link})\n"

    # تهيئة البيانات للإرسال
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }

    try:
        response = requests.post(telegram_url, data=payload)
        response.raise_for_status()
        
        # نستخدم الكود الآن للتأكد من وصول رسالة النجاح
        print("*** تم إرسال التنبيه إلى Telegram بنجاح! ***")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ فشل في إرسال رسالة Telegram. الخطأ: {e}")
        return False


def load_history(filename):
    """تحميل الروابط القديمة من ملف السجل."""
    if not os.path.exists(filename):
        return set()
    with open(filename, 'r', encoding='utf-8') as f:
        return set(f.read().splitlines())

def save_history(filename, links):
    """حفظ الروابط الحالية في ملف السجل."""
    with open(filename, 'w', encoding='utf-8') as f:
        for link in sorted(list(links)):
            f.write(f"{link}\n")

def get_current_links(url):
    """
    يستخدم Selenium لمحاكاة اختيار المرحلة والسنة واستخراج الروابط.
    """
    print("🚀 بدء تشغيل المتصفح الخفي (Selenium)...")
    
    # إعداد خيارات Chrome للعمل بدون واجهة رسومية على GitHub Actions
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # تثبيت وتشغيل ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        print(f"✅ تم فتح الصفحة بنجاح: {url}")
        
        # ----------------------------------------------------
        # 1. اختيار المرحلة (المرحلة الثانوية)
        # ----------------------------------------------------
        # البحث عن عنصر المرحلة الثانوية والضغط عليه
        # نعتمد على أن الموقع يستخدم وسوم <a> أو <button> مع نص محدد
        
        print(f"🔍 البحث عن زر اختيار المرحلة: {STAGE_NAME}")
        
        # نستخدم XPATH للبحث عن أي عنصر يحتوي على هذا النص
        stage_xpath = f"//button[contains(text(), '{STAGE_NAME}')] | //a[contains(text(), '{STAGE_NAME}')]"
        
        # الانتظار حتى يصبح العنصر قابلاً للضغط
        stage_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, stage_xpath))
        )
        stage_element.click()
        print(f"✅ تم النقر على: {STAGE_NAME}")
        
        # الانتظار القصير لتحميل خيارات الصفوف
        time.sleep(2) 
        
        # ----------------------------------------------------
        # 2. اختيار الصف (الصف الثاني الثانوي)
        # ----------------------------------------------------
        print(f"🔍 البحث عن زر اختيار الصف: {GRADE_NAME}")
        
        # نستخدم XPATH للبحث عن العنصر الذي يحتوي على نص الصف
        grade_xpath = f"//button[contains(text(), '{GRADE_NAME}')] | //a[contains(text(), '{GRADE_NAME}')]"
        
        # الانتظار حتى يصبح العنصر قابلاً للضغط
        grade_element = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, grade_xpath))
        )
        grade_element.click()
        print(f"✅ تم النقر على: {GRADE_NAME}")
        
        # ----------------------------------------------------
        # 3. استخراج الروابط بعد التصفية
        # ----------------------------------------------------
        
        # الانتظار لثوانٍ حتى يتم تحميل الملفات عبر الجافاسكريبت
        time.sleep(5) 
        
        # الآن نقوم بتحليل كود المصدر الذي تم تحميله
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # نبحث عن جميع الروابط التي تنتهي بـ .pdf أو تبدأ باسم الملف
        # هذا هو الكشط الفعلي بعد تحميل الصفحة بالكامل
        links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # نبحث عن روابط PDF كاملة المسار
            if href.endswith('.pdf') and href.startswith('http'):
                links.add(href)
        
        print(f"✅ تم العثور على {len(links)} رابط (PDF) بعد التصفية.")
        return links

    except Exception as e:
        print(f"❌ حدث خطأ أثناء محاكاة المتصفح أو التصفية: {e}")
        return set()
        
    finally:
        driver.quit()
        print("🛑 تم إغلاق المتصفح الخفي.")


def monitor_website():
    """المنطق الرئيسي لمقارنة الروابط وإرسال التنبيه."""
    print(f"جاري مراقبة: {URL_TO_MONITOR}")
    
    old_links = load_history(HISTORY_FILE)
    current_links = get_current_links(URL_TO_MONITOR)

    if not current_links:
        print("❌ فشل في تحميل الروابط الديناميكية. يرجى مراجعة الخطوات في السجل.")
        send_notification("❌ فشل البوت في تحميل الروابط الديناميكية بعد التصفية (الصف الثاني الثانوي). يرجى مراجعة سجل GitHub.", is_status=True)
        return

    # حساب الروابط الجديدة
    new_links = current_links - old_links
    
    if new_links:
        print(f"⚠️ تم العثور على {len(new_links)} ملف جديد للصف الثاني الثانوي!")
        send_notification(new_links)
        # تحديث ملف السجل بعد إرسال التنبيه
        save_history(HISTORY_FILE, current_links)
    else:
        status_message = f"✅ *البوت يعمل بنجاح!* لا يوجد ملفات جديدة للصف الثاني الثانوي منذ الفحص الأخير."
        print(status_message)
        send_notification(status_message, is_status=True)


if __name__ == "__main__":
    monitor_website()
