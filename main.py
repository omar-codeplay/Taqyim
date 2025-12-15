import os
import requests
import re
import ast
import json
import execjs # تم إضافة المكتبة هنا

# =================================================================
# التكوين والإعدادات
# =================================================================
# 1. إعدادات الموقع الوزاري
JS_FILE_URL = "https://ellibrary.moe.gov.eg/cha/scripts.js"
TARGET_TYPE_FILTER = "تقييم"

# 2. إعدادات Firebase (يتم جلبها من GitHub Secrets)
FIREBASE_URL = os.getenv("FIREBASE_URL")
FIREBASE_PATH_G1 = "books"   # للصف الأول الثانوي
FIREBASE_PATH_G2 = "taq_it"  # للصف الثاني الثانوي

# 3. إعدادات Telegram (يتم جلب TELEGRAM_BOT_TOKEN من GitHub Secrets)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "@taqyim_alerts"

# 4. ملف السجل
HISTORY_FILE = "history_log.txt"

# =================================================================
# خرائط المواد (Mapping)
# =================================================================

# خريطة الصف الأول الثانوي
SUBJECT_MAP_G1 = {
    "اللغة العربية": "1",
    "اللغة الانجليزية لغة اولى": "2",
    "العلوم المتكاملة باللغة العربية": "3",
    "العلوم المتكاملة باللغة الإنجليزية": "4",
    "الرياضيات باللغة العربية": "5",
    "الرياضيات باللغة الانجليزية": "6",
    "التاريخ": "7",
    "اللغة الفرنسية لغة أولى": "8",
    "اللغة الايطالية لغة ثانية": "9",
    "اللغة الإسبانية لغة ثانية": "10",
    "اللغة الصينية لغة ثانية": "11",
    "اللغة الفرنسية لغة ثانية": "12",
    "اللغة الالمانية لغة ثانية": "13",
    "البرمجة والذكاء الاصطناعي باللغة العربية": "14",
    "التربية الدينية الإسلامية": "15",
    "التربية الدينية المسيحية": "16",
    "الفلسفة والمنطق": "17"
}

# خريطة الصف الثاني الثانوي
SUBJECT_MAP_G2 = {
    "اللغة العربية": "1",
    "اللغة الانجليزية لغة اولى": "2",
    "الفيزياء باللغة العربية": "3",
    "الفيزياء باللغة الانجليزية": "4",
    "الكيمياء باللغة العربية": "5",
    "الرياضيات البحتة باللغة العربية": "6",
    "الرياضيات البحتة باللغة الانجليزية": "7",
    "تطبيقات الرياضيات باللغة العربية": "8",
    "تطبيقات الرياضيات باللغة الانجليزية": "9",
    "الرياضيات العامة باللغة العربية": "10",
    "الرياضيات العامة باللغة الإنجليزية": "11",
    "علم النفس والاجتماع": "12",
    "التاريخ": "13",
    "جغرافيا التنمية": "14",
    "اللغة الإسبانية لغة ثانية": "15",
    "اللغة الصينية لغة ثانية": "16",
    "اللغة الالمانية لغة ثانية": "17",
    "اللغة الايطالية لغة ثانية": "18",
    "اللغة الفرنسية لغة أولى": "19",
    "اللغة الفرنسية لغة ثانية": "20",
    "التربية الدينية الإسلامية": "21",
    "التربية الدينية المسيحية": "22",
    "الكيمياء باللغة الانجليزية": "23",
}

# =================================================================
# الدوال المساعدة
# =================================================================

def load_history():
    """تحميل الروابط التي تمت معالجتها سابقاً."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"❌ فشل تحميل ملف السجل: {e}")
        return set()

def save_history(new_links):
    """إضافة الروابط الجديدة إلى ملف السجل."""
    try:
        with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
            for link in new_links:
                f.write(f"{link}\n")
    except Exception as e:
        print(f"❌ فشل حفظ ملف السجل: {e}")

def fetch_moe_data():
    """
    جلب ملف JS وتنفيذ جزء JavaScript الذي يُعرّف مصفوفة 'books' لاستخراج البيانات بشكل موثوق.
    """
    print(f"📥 جاري جلب البيانات من المصدر: {JS_FILE_URL}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(JS_FILE_URL, headers=headers, timeout=20)
        response.raise_for_status()
        
        js_code = response.text
        
        # 1. استخراج الكود المسؤول عن المصفوفة
        match = re.search(r'const\s+books\s*=\s*(\[[^;]*?\]);', js_code, re.DOTALL)
        if not match:
            print("❌ لم يتم العثور على مصفوفة books في ملف JS.")
            return []

        # 2. إنشاء سياق JavaScript وتنفيذ الكود
        print("🔧 جاري تنفيذ كود JavaScript لاستخراج المصفوفة...")
        
        # نضيف جزء تعريف المصفوفة ثم نطبعها كـ JSON
        # نستخدم JSON.stringify لتحويل الكائنات بشكل سليم إلى تنسيق JSON صالح
        js_execution_code = match.group(0) + '\n' + 'return JSON.stringify(books);'
        
        ctx = execjs.compile(js_execution_code)
        json_string = ctx.eval('JSON.stringify(books)')
        
        # 3. تحليل سلسلة JSON بواسطة Python
        data = json.loads(json_string)
        print("✅ نجاح تحليل البيانات عبر تنفيذ JS.")
        return data

    except requests.exceptions.RequestException as e:
        print(f"❌ خطأ في الاتصال أو التحميل: {e}")
        return []
    except execjs.ProgramError as e:
        print(f"❌ خطأ في تنفيذ كود JavaScript: {e}")
        print(">>> تأكد من تثبيت بيئة تشغيل JS مثل Node.js (عبر الأمر: npm install -g nodejs).")
        return []
    except Exception as e:
        print(f"❌ فشل التحليل النهائي بعد التنفيذ: {e}")
        return []

def parse_week(type_str):
    """استخراج رقم الأسبوع من النص مثل '(13) تقييمات الاسبوع...'."""
    match = re.search(r'\((\d+)\)', str(type_str))
    return match.group(1) if match else "0"

def process_items(all_data, history_set):
    """معالجة البيانات وتجهيز القوائم الجديدة حسب الصف ونوع التقييم."""
    new_items_g1 = []
    new_items_g2 = []
    
    for item in all_data:
        link = item.get('link')
        grade = item.get('grade')
        subject = item.get('subject', '').strip()
        raw_type = item.get('type') 
        
        # 1. تصفية: هل هو "تقييم"؟
        if TARGET_TYPE_FILTER not in str(raw_type):
            continue
            
        # 2. تصفية: هل الرابط موجود في السجل؟
        if link in history_set:
            continue
            
        # 3. معالجة البيانات
        week = parse_week(raw_type)
        
        processed_item = {
            "name": subject,
            "url": link,
            "week": week,
            "raw_grade": grade
        }

        # 4. التصنيف حسب الصف وتعيين الـ ID
        if grade == "الصف الاول الثانوي":
            type_id = SUBJECT_MAP_G1.get(subject, "0")
            processed_item["type"] = type_id
            new_items_g1.append(processed_item)
            
        elif grade == "الصف الثاني الثانوي":
            type_id = SUBJECT_MAP_G2.get(subject, "0")
            processed_item["type"] = type_id
            new_items_g2.append(processed_item)
            
    return new_items_g1, new_items_g2

def upload_batch_firebase(items, node_path):
    """رفع قائمة عناصر إلى Firebase Realtime Database."""
    if not items or not FIREBASE_URL:
        return
    
    print(f"🚀 جاري رفع {len(items)} عنصر إلى المسار: {node_path}...")
    
    for item in items:
        key = f"{item['type']}_{item['week']}"
        url = f"{FIREBASE_URL}/{node_path}/{key}.json"
        
        payload = {
            'name': item['name'],
            'week': item['week'],
            'url': item['url'],
            'type': item['type']
        }
        
        try:
            resp = requests.put(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"✅ تم الرفع: {item['name']} (W{item['week']})")
            else:
                print(f"❌ فشل الرفع ({resp.status_code}): {item['name']}")
        except Exception as e:
            print(f"❌ خطأ اتصال بـ Firebase لـ {item['name']}: {e}")

def send_telegram_alert(items_g1, items_g2):
    """إرسال إشعار مجمع لتيليجرام بالملفات الجديدة."""
    if not TELEGRAM_BOT_TOKEN:
        print("⚠️ لم يتم تعيين توكن تيليجرام.")
        return

    all_new = items_g1 + items_g2
    if not all_new:
        return

    chunk_size = 20
    chunks = [all_new[i:i + chunk_size] for i in range(0, len(all_new), chunk_size)]

    total_new = len(all_new)
    
    for idx, chunk in enumerate(chunks):
        msg = f"🚨 <b>تنبيه: تم إضافة {total_new} تقييم جديد!</b> 🚨\n"
        if len(chunks) > 1:
            msg += f"<i>(الجزء {idx+1} من {len(chunks)})</i>\n"
        msg += "\n"
        
        for item in chunk:
            grade_short = "1ث" if item['raw_grade'] == "الصف الاول الثانوي" else "2ث"
            msg += f"▪️ <b>{grade_short}</b> | {item['name']} (أسبوع {item['week']})\n"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, data={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': msg,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }, timeout=10)
        except Exception as e:
            print(f"❌ فشل إرسال تيليجرام (الدفعة {idx+1}): {e}")

# =================================================================
# التشغيل الرئيسي
# =================================================================
def main():
    print("--- بدء مهمة فحص التقييمات ---")
    
    # 1. تحميل السجل القديم
    history = load_history()
    print(f"📂 تم تحميل {len(history)} رابط من السجل.")

    # 2. جلب البيانات
    raw_data = fetch_moe_data()
    if not raw_data:
        print("🛑 فشل جلب البيانات الخام أو تحليلها.")
        return

    # 3. المعالجة والفرز (الجديد فقط)
    new_g1, new_g2 = process_items(raw_data, history)
    
    total_new = len(new_g1) + len(new_g2)
    if total_new == 0:
        print("✅ لا توجد تحديثات جديدة.")
        return

    print(f"⚡ تم العثور على {len(new_g1)} لـ 1ث، و {len(new_g2)} لـ 2ث.")

    # 4. الرفع لقاعدة البيانات
    if new_g1:
        upload_batch_firebase(new_g1, FIREBASE_PATH_G1)
    if new_g2:
        upload_batch_firebase(new_g2, FIREBASE_PATH_G2)

    # 5. إرسال الإشعارات
    send_telegram_alert(new_g1, new_g2)

    # 6. تحديث السجل
    links_to_save = [i['url'] for i in new_g1] + [i['url'] for i in new_g2]
    save_history(links_to_save)
    print("💾 تم تحديث ملف السجل.")

if __name__ == "__main__":
    main()
