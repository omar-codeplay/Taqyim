import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import time

# في ملف monitor.py

# ... (الإعدادات العامة)
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/" 
HISTORY_FILE = "moe_files_history.txt" 
# *** 🚨 الكلمة المفتاحية الجديدة 🚨 ***
LINK_KEYWORD = "الصف الثاني الثانوي" 
# ... (بقية الكود)


# --- إعدادات Telegram (يتم قراءة التوكن من GitHub Secrets) ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_RECEIVER_USERNAME = "@omar_codeplay" 
# تأكد من أن هذا هو اسم المستخدم الخاص بك (مع @)

def send_notification(content, is_status=False):
    """
    إرسال التنبيهات أو رسالة الحالة إلى Telegram.
    content يمكن أن يكون قائمة روابط أو نص رسالة الحالة.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_RECEIVER_USERNAME:
        print("\n❌ فشل الإرسال: لم يتم إعداد Telegram Secrets أو اسم المستخدم بشكل صحيح.")
        return

    if is_status:
        # إذا كانت رسالة حالة، استخدم النص مباشرة
        notification_message = content
    else:
        # إذا كانت قائمة روابط جديدة
        notification_message = "🎉 *تم العثور على ملفات جديدة في موقع الوزارة!* 🎉\n"
        for link in content:
            # محاولة استخلاص اسم الملف
            link_parts = link.split('/')
            file_name = link_parts[-1] if link_parts[-1] else link_parts[-2]
            notification_message += f"\n- *اسم الملف:* {file_name}\n- *الرابط:* {link}\n"
    
    # تشفير الرسالة
    encoded_message = urllib.parse.quote_plus(notification_message)
    
    # بناء رابط API
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_RECEIVER_USERNAME}&text={encoded_message}&parse_mode=Markdown"
    
    try:
        # إرسال الطلب
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        print("\n*** تم إرسال التنبيه إلى Telegram بنجاح! ***")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ فشل في إرسال رسالة Telegram. الخطأ: {e}")
        print("تحقق: هل اسم المستخدم صحيح؟ وهل البوت بدأ محادثة معك؟")


def get_current_links(url):
    """يزور الصفحة ويستخرج الروابط التي تطابق الكلمة المفتاحية."""
    # ... (بقية الدالة كما هي)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        current_links = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            if LINK_KEYWORD.lower() in href.lower():
                full_link = requests.compat.urljoin(url, href)
                current_links.add(full_link)
                
        return current_links

    except requests.exceptions.RequestException as e:
        print(f"❌ حدث خطأ في الاتصال أو التحليل: {e}")
        return set()

def load_history(filename):
    """تحميل الروابط القديمة المحفوظة من الملف."""
    if not os.path.exists(filename):
        return set()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except IOError as e:
        print(f"حدث خطأ أثناء قراءة ملف السجل: {e}")
        return set()

def save_history(filename, links):
    """حفظ قائمة الروابط الجديدة في الملف."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for link in sorted(list(links)):
                f.write(link + '\n')
    except IOError as e:
        print(f"حدث خطأ أثناء حفظ ملف السجل: {e}")

def monitor_website():
    """الدالة الرئيسية لمراقبة الموقع."""
    print(f"جاري مراقبة: {URL_TO_MONITOR}")
    
    old_links = load_history(HISTORY_FILE)
    current_links = get_current_links(URL_TO_MONITOR)

    if not current_links and not old_links:
        print("لم يتم العثور على أي روابط حالياً. تحقق من LINK_KEYWORD.")
        return

    new_links = current_links - old_links

    if new_links:
        print(f"⚠️ تم العثور على {len(new_links)} ملف جديد!")
        send_notification(new_links)
    else:
        # *** 💡 التعديل الجديد: إرسال رسالة حالة إذا لم يتم العثور على شيء ***
        status_message = "✅ *البوت يعمل بنجاح!* لا يوجد ملفات جديدة للصف الثاني الثانوي منذ الفحص الأخير."
        print(status_message)
        send_notification(status_message, is_status=True)

    # حفظ القائمة الحالية للمقارنة التالية
    if current_links:
        save_history(HISTORY_FILE, current_links)
        print("تم تحديث سجل الروابط بنجاح.")

if __name__ == "__main__":
    monitor_website()
