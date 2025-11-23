import os
import requests
import re
import ast # 🚨 المكتبة المستخدمة حاليًا
# =================================================================
# الإعدادات العامة
# =================================================================
JS_FILE_URL = "https://ellibrary.moe.gov.eg/cha/scripts.js" 
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/" 

HISTORY_FILE = "moe_files_history.txt"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
TELEGRAM_CHAT_ID = "@omar_codeplay" 

TARGET_GRADE = "الصف الثاني الثانوي"
# =================================================================


def send_notification(content, is_status=False):
    """يرسل تنبيه أو رسالة حالة إلى قناة/دردشة تيليجرام."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ فشل الإرسال: TELEGRAM_BOT_TOKEN غير متوفر.")
        return

    message_text = ""
    if is_status:
        message_text = content
    else:
        message_text = f"🚨 *تنبيه: تم العثور على {len(content)} ملف جديد للصف الثاني الثانوي!* 🚨\n\n"
        for item in content:
            name = f"({item['type']}) {item['subject']} - {item['term']}"
            link = item['link']
            message_text += f"▪️ [{name}]({link})\n"

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }

    try:
        response = requests.post(telegram_url, data=payload)
        if response.status_code != 200:
             print(f"❌ فشل في إرسال رسالة Telegram. رمز الحالة: {response.status_code}")
             return False

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

def get_current_links_from_js(js_url, target_grade):
    """
    يقوم بتنزيل ملف JS، يستخرج مصفوفة الكتب، ويقوم بالتصفية باستخدام ast.literal_eval.
    """
    print(f"📥 جاري تنزيل ملف البيانات من: {js_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    }

    try:
        response = requests.get(js_url, headers=headers, timeout=15) 
        response.raise_for_status()
        js_content = response.text
        
        # 1. البحث عن مصفوفة الكتب في محتوى الملف
        match = re.search(r'const\s+books\s*=\s*(\[[^;]*?\]);', js_content, re.DOTALL)
        
        if not match:
            print("❌ لم يتم العثور على متغير 'const books' في الملف.")
            return []

        js_data_text = match.group(1).strip()
        
        # 2. 🚨🚨 التعديل الحاسم لتنظيف البيانات لـ ast.literal_eval 🚨🚨
        
        # أ. إزالة جميع علامات الاقتباس المزدوجة والمفردة لتنظيف الروابط وقيمها أولاً
        js_data_text = js_data_text.replace('"', '').replace("'", "")
        
        # ب. إزالة أي مسافات زائدة وفواصل أسطر جديدة
        js_data_text = js_data_text.replace('\n', '').replace('\t', '')
        
        # ج. التأكد من اقتباس المفاتيح وقيمها باستخدام علامات اقتباس مفردة (لمتطلبات ast.literal_eval)
        # هذا Regex يبحث عن أي كلمة (key) يتبعها نقطتان، ويحيطها بعلامات اقتباس مفردة.
        js_data_text = re.sub(r'([a-zA-Z0-9_]+)\s*:\s*([^,\[\]\{\}]+)', r"'\1': '\2'", js_data_text)
        
        # د. إزالة الفواصل الزائدة في نهاية المصفوفة
        js_data_text = re.sub(r',\s*\]', ']', js_data_text)

        # ----------------------------------------------------
        
        # 3. التحليل باستخدام ast.literal_eval (يحل مشكلة التنسيق غير القياسي)
        # نقوم بتحويل النص إلى مصفوفة بايثون (list of dicts)
        books_data = ast.literal_eval(js_data_text) 
        
        # 4. التصفية للحصول على الصف المطلوب
        filtered_data = [
            book for book in books_data 
            if book.get('grade') == target_grade
        ]
        
        print(f"✅ تم استخراج {len(filtered_data)} ملفاً للصف {target_grade}.")
        return filtered_data

    except requests.exceptions.RequestException as e:
        print(f"❌ فشل في تنزيل ملف JS. الخطأ: {e}")
        return []
        
    except SyntaxError as e:
        print(f"❌ فشل في تحليل بيانات JS/JSON: SyntaxError عند استخدام ast.literal_eval. الخطأ: {e}")
        return []
    except Exception as e:
        print(f"❌ حدث خطأ غير متوقع: {e}")
        return []

def monitor_website():
    """المنطق الرئيسي لمقارنة الروابط وإرسال التنبيه."""
    print(f"جاري مراقبة: {URL_TO_MONITOR}")

    structured_data = get_current_links_from_js(JS_FILE_URL, TARGET_GRADE)

    if not structured_data:
        print("❌ فشل في الحصول على بيانات الملفات. يرجى مراجعة سجل GitHub.")
        send_notification("❌ فشل البوت في الحصول على بيانات الصف الثاني الثانوي من ملف البيانات.", is_status=True)
        return

    current_links = {item['link'] for item in structured_data}
    old_links = load_history(HISTORY_FILE)

    new_links_urls = current_links - old_links
    
    new_data = [item for item in structured_data if item['link'] in new_links_urls]

    if new_data:
        print(f"⚠️ تم العثور على {len(new_data)} ملف جديد للصف الثاني الثانوي!")
        send_notification(new_data)
        save_history(HISTORY_FILE, current_links)
    else:
        status_message = f"✅ *البوت يعمل بنجاح!* لا يوجد ملفات جديدة للصف الثاني الثانوي منذ الفحص الأخير."
        print(status_message)
        send_notification(status_message, is_status=True)


if __name__ == "__main__":
    monitor_website()
