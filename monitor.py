import requests
from bs4 import BeautifulSoup
import os
import time # لإضافة تأخير بسيط

# --- الإعدادات (المعدلة) ---
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/" 
HISTORY_FILE = "moe_files_history.txt" 
# عادةً ما تكون الملفات الجديدة في هذا الموقع هي عبارة عن وسوم 'a'
# داخل وسم يحتوي على فئة (class) معينة، لكن سنبحث عن الروابط العامة أولاً.
# كلمة مفتاحية شائعة للروابط في هذا الموقع هي "download" أو "pdf"
LINK_KEYWORD = "pdf" 

# أضف مكتبة urllib.parse لضمان تشفير الرسالة في الرابط
import urllib.parse 
# ... (باقي المكتبات: requests, BeautifulSoup, os, time) ...

# --- الإعدادات (ستبقى نفسها) ---
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/" 
HISTORY_FILE = "moe_files_history.txt" 
LINK_KEYWORD = "pdf" 

# --- إعدادات Telegram (مؤقتة) ---
# ستستبدل هذه القيم بـ GitHub Secrets لاحقاً!
TELEGRAM_BOT_TOKEN = "ضع_هنا_مفتاح_التوكن_الذي_أعطاك_إياه_BotFather" 
TELEGRAM_CHAT_ID = "ضع_هنا_معرف_المحادثة_الذي_حصلت_عليه"

def send_notification(new_links):
    """
    الدالة الجديدة لإرسال التنبيهات إلى Telegram.
    """
    if not new_links:
        return

    notification_message = "🎉 *تم العثور على ملفات جديدة في موقع الوزارة!* 🎉\n"
    for link in new_links:
        notification_message += f"• الرابط: {link}\n"
    
    # 1. تشفير الرسالة لتكون صالحة للاستخدام في رابط URL
    encoded_message = urllib.parse.quote_plus(notification_message)
    
    # 2. بناء رابط API لإرسال الرسالة
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={encoded_message}&parse_mode=Markdown"
    
    try:
        # 3. إرسال الطلب
        response = requests.get(api_url)
        response.raise_for_status()
        print("\n*** تم إرسال التنبيه إلى Telegram بنجاح! ***")
    except requests.exceptions.RequestException as e:
        print(f"\n❌ فشل في إرسال رسالة Telegram: {e}")
        print("تأكد من صحة التوكن و Chat ID.")

# ... (باقي الدوال: get_current_links, load_history, save_history, monitor_website) ...
# ... (لا تحتاج لتغييرها) ...


def get_current_links(url):
    """يزور الصفحة ويستخرج الروابط التي تطابق الكلمة المفتاحية."""
    # لتجنب حظر الخادم، أرسل user-agent كمتصفح حقيقي
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # التأكد من نجاح الاتصال (كود 200)

        soup = BeautifulSoup(response.content, 'html.parser')
        current_links = set()
        
        # البحث عن كل الروابط (<a>) التي تحتوي على خاصية href
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # تحقق من الكلمة المفتاحية في الرابط
            if LINK_KEYWORD.lower() in href.lower():
                # تحويل الروابط النسبية إلى كاملة
                full_link = requests.compat.urljoin(url, href)
                current_links.add(full_link)
                
        return current_links

    except requests.exceptions.RequestException as e:
        print(f"❌ حدث خطأ في الاتصال أو التحليل: {e}")
        return set()

# (دالتا load_history و save_history من الكود السابق تعملان كما هما)
# ... [Code for load_history and save_history functions] ...
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
# --------------------------------------------------------

def monitor_website():
    """الدالة الرئيسية لمراقبة الموقع."""
    print(f"جاري مراقبة: {URL_TO_MONITOR}")
    
    # 1. تحميل الروابط القديمة
    old_links = load_history(HISTORY_FILE)

    # 2. استخراج الروابط الحالية
    current_links = get_current_links(URL_TO_MONITOR)

    if not current_links and not old_links:
        print("لم يتم العثور على أي روابط حالياً. ربما تحتاج لتعديل LINK_KEYWORD.")
        return

    # 3. مقارنة القوائم
    new_links = current_links - old_links

    if new_links:
        send_notification(new_links)
    else:
        print("✅ لا يوجد ملفات جديدة تم العثور عليها منذ الفحص الأخير.")

    # 4. حفظ القائمة الحالية للمقارنة التالية
    if current_links:
        save_history(HISTORY_FILE, current_links)
        print("تم تحديث سجل الروابط بنجاح.")

if __name__ == "__main__":
    monitor_website()
