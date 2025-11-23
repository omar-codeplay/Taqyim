import os
import requests
import re
import ast 
# =================================================================
# الإعدادات العامة
# =================================================================
JS_FILE_URL = "https://ellibrary.moe.gov.eg/cha/scripts.js" 
URL_TO_MONITOR = "https://ellibrary.moe.gov.eg/cha/" 

HISTORY_FILE = "moe_files_history.txt"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") 
TELEGRAM_CHAT_ID = "@taqyim_alerts" 

# تصفية الملفات إلى 'تقييم' فقط
TARGET_GRADE = "الصف الثاني الثانوي"
TARGET_TYPE = "تقييم" 

# الحد الأقصى للروابط في الرسالة الواحدة (لحل مشكلة "text is too long")
CHUNK_SIZE = 25 
# =================================================================

def send_notification_chunk(chunk_data, total_new_count, chunk_index, total_chunks, is_status=False):
    """ترسل دفعة من الملفات الجديدة أو رسالة حالة واحدة."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ فشل الإرسال: TELEGRAM_BOT_TOKEN غير متوفر.")
        return False

    message_text = ""
    if is_status:
        # رسائل الفشل الحرجة فقط (فشل التحليل أو غير ذلك)
        message_text = chunk_data
    else:
        # بناء رسائل التنبيه العادية
        message_text = f"🚨 <b>تنبيه: تم العثور على {total_new_count} تقييماً جديداً للصف {TARGET_GRADE}!</b> 🚨\n"
        if total_chunks > 1:
            message_text += f"<i>(جزء {chunk_index} من {total_chunks})</i>\n\n"
        
        for item in chunk_data:
            # صياغة اسم التقييم بدون الفصل الدراسي والرابط
            name = f"({item['type']}) {item['subject']}" 
            message_text += f"▪️ {name}\n"

    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'HTML', 
        'disable_web_page_preview': True
    }

    try:
        response = requests.post(telegram_url, data=payload)
        if response.status_code != 200:
             print(f"❌ فشل في إرسال رسالة Telegram. رمز الحالة: {response.status_code}")
             print(f"استجابة تيليجرام: {response.text}")
             return False
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

def get_current_links_from_js(js_url, target_grade, target_type):
    """
    يقوم بتنزيل ملف JS، يستخرج مصفوفة الكتب، ويقوم بالتصفية.
    """
    print(f"📥 جاري تنزيل ملف البيانات من: {js_url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'
    }

    try:
        response = requests.get(js_url, headers=headers, timeout=15) 
        response.raise_for_status()
        js_content = response.text
        
        match = re.search(r'const\s+books\s*=\s*(\[[^;]*?\]);', js_content, re.DOTALL)
        if not match: return []

        js_data_text = match.group(1).strip()
        
        # تنظيف البيانات لـ ast.literal_eval
        js_data_text = js_data_text.replace('\n', '').replace('\t', '')
        js_data_text = js_data_text.replace('"', '').replace("'", "")
        js_data_text = re.sub(r'([a-zA-Z0-9_]+)\s*:\s*([^,\[\]\{\}]+)', r"'\1': '\2'", js_data_text)
        js_data_text = re.sub(r',\s*\]', ']', js_data_text)
        
        books_data = ast.literal_eval(js_data_text) 
        
        # التصفية للوصول إلى الصف والنوع المطلوبين
        filtered_data = [
            book for book in books_data 
            if book.get('grade') == target_grade and book.get('type') == target_type
        ]
        
        print(f"✅ تم استخراج {len(filtered_data)} تقييماً للصف {target_grade}.")
        return filtered_data

    except requests.exceptions.RequestException as e:
        print(f"❌ فشل في تنزيل ملف JS. الخطأ: {e}")
        return []
        
    except (SyntaxError, ValueError) as e:
        # هنا سنرسل رسالة الفشل هذه لأنها مشكلة حرجة
        send_notification_chunk(f"❌ فشل البوت في تحليل البيانات: {e}", 0, 0, 0, is_status=True)
        print(f"❌ فشل في تحليل بيانات JS/JSON: {e}")
        return []
    except Exception as e:
        # هنا سنرسل رسالة الفشل هذه لأنها مشكلة حرجة
        send_notification_chunk(f"❌ حدث خطأ غير متوقع: {e}", 0, 0, 0, is_status=True)
        print(f"❌ حدث خطأ غير متوقع: {e}")
        return []

def monitor_website():
    """المنطق الرئيسي لمقارنة الروابط وإرسال التنبيه."""
    print(f"جاري مراقبة: {URL_TO_MONITOR}")

    # لاحظ أننا لم نعد نرسل رسالة الفشل إلا من داخل get_current_links_from_js في حالة حدوث خطأ حرج (SyntaxError/Exception)
    structured_data = get_current_links_from_js(JS_FILE_URL, TARGET_GRADE, TARGET_TYPE)

    if not structured_data:
        # هنا لا نرسل أي رسالة، لأنها قد تكون حالة "لا يوجد بيانات تقييمات أصلاً"
        print("❌ فشل في الحصول على بيانات التقييمات. يرجى مراجعة سجل GitHub.")
        # نرسل رسالة حرجة فقط في حالة عدم وجود بيانات على الإطلاق
        if not load_history(HISTORY_FILE):
             send_notification_chunk("❌ فشل البوت في الحصول على بيانات التقييمات للصف الثاني الثانوي.", 0, 0, 0, is_status=True)
        return

    current_links = {item['link'] for item in structured_data}
    old_links = load_history(HISTORY_FILE)

    new_links_urls = current_links - old_links
    
    new_data = [item for item in structured_data if item['link'] in new_links_urls]
    
    if new_data:
        total_new = len(new_data)
        print(f"⚠️ تم العثور على {total_new} تقييماً جديداً للصف {TARGET_GRADE}!")
        
        # تقسيم الروابط إلى دفعات وإرسالها
        chunks = [new_data[i:i + CHUNK_SIZE] for i in range(0, total_new, CHUNK_SIZE)]
        total_chunks = len(chunks)
        
        print(f"جاري إرسال التنبيه في {total_chunks} رسالة.")
        
        for i, chunk in enumerate(chunks):
            success = send_notification_chunk(chunk, total_new, i + 1, total_chunks)
            if not success:
                print(f"🛑 توقف الإرسال بعد فشل الدفعة {i+1}. لن يتم حفظ السجل.")
                return 
        
        # حفظ السجل فقط بعد إرسال جميع الرسائل بنجاح
        save_history(HISTORY_FILE, current_links)
        print("*** تم تحديث سجل الروابط بنجاح. ***")
        
    else:
        # 🚨 في هذه الحالة، لا يتم إرسال أي رسالة إلى تيليجرام 🚨
        status_message = f"✅ <b>البوت يعمل بنجاح!</b> لا يوجد تقييمات جديدة للصف {TARGET_GRADE} منذ الفحص الأخير."
        print(status_message)


if __name__ == "__main__":
    monitor_website()
