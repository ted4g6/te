from telethon import TelegramClient, events, Button
import zipfile
import glob
import os

import os

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

grades_folders = {'grade1': 'الصف الأول', 'grade2': 'الصف الثاني', 'grade3': 'الصف الثالث'}
for folder in grades_folders.keys():
    os.makedirs(f'./{folder}', exist_ok=True)

user_states = {}

@client.on(events.NewMessage(pattern='/admin'))
async def admin_panel(event):
    if event.sender_id == ADMIN_ID:
        await event.reply("اختر الصف لإضافة أو إدارة النتائج:", buttons=[
            [Button.inline("إضافة نتائج الصف الأول", b'grade1')],
            [Button.inline("عرض طلاب الصف الأول", b'show_grade1')],
            [Button.inline("إضافة نتائج الصف الثاني", b'grade2')],
            [Button.inline("عرض طلاب الصف الثاني", b'show_grade2')],
            [Button.inline("إضافة نتائج الصف الثالث", b'grade3')],
            [Button.inline("عرض طلاب الصف الثالث", b'show_grade3')]
        ])
        user_states[event.sender_id] = None

@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    await event.reply(
        "تعليمات استخدام البوت:\n"
        "/start - لبدء اليحث عن نتيجة الامتحان.\n"
        "/admin - للدخول إلى واجهة إدارة النتائج (للمشرف فقط).\n"
        "/help - للحصول على تعليمات استخدام البوت.\n"
        "للطلاب: اختر صفك ثم أدخل اسمك الثلاثي للحصول على ورقة النتيجة.\n"
        "للأدمن: اختر الصف الذي تريد إضافة النتائج إليه وتابع التعليمات."
    )

@client.on(events.NewMessage(pattern='/start'))
async def student_interface(event):
    if event.sender_id != ADMIN_ID:
        await event.reply("اختر صفك للحصول على ورقة النتيجة:", buttons=[
            [Button.inline("الصف الأول", b'student_grade1')],
            [Button.inline("الصف الثاني", b'student_grade2')],
            [Button.inline("الصف الثالث", b'student_grade3')]
        ])
        user_states[event.sender_id] = None

@client.on(events.CallbackQuery)
async def select_grade(event):
    data = event.data.decode()
    
    if data.startswith('student_grade'):
        grade = data.split('_')[1]  # استخراج الصف من الزر
        user_states[event.sender_id] = {'current_grade': grade, 'awaiting_student_name': True}
        
        await event.respond(f"أدخل اسمك الثلاثي للحصول على نتيجتك من {grades_folders[grade]}:")
        event.stop_propagation()

@client.on(events.NewMessage(incoming=True))
async def receive_student_name(event):
    user_state = user_states.get(event.sender_id, {})
    
    if user_state.get('awaiting_student_name'):
        name = event.text.strip()
        grade = user_state.get('current_grade')  
        matching_files = [file for file in glob.glob(f'./{grade}/{name}*.png')]
        
        if len(matching_files) == 1:
            await event.reply("النتيجة:", file=matching_files[0])
        elif len(matching_files) > 1:
            await event.reply("يوجد أكثر من طالب بنفس الاسم، يرجى إدخال الاسم الرباعي للتأكيد.")
        else:
            await event.reply("لم يتم العثور على ورقة النتيجة لهذا الاسم.")
        
        user_states[event.sender_id] = {'current_grade': None, 'awaiting_student_name': False}
        event.stop_propagation()

@client.on(events.CallbackQuery)
async def add_results(event):
    data = event.data.decode()
    
    if data in ['grade1', 'grade2', 'grade3']:
        grade = data
        await event.respond(f"اختر طريقة إضافة النتائج {grades_folders[grade]}:", buttons=[
            [Button.inline("إضافة نتائج عبر ملف ZIP", f'zip_{grade}')],
            [Button.inline("إضافة نتيجة عبر صورة فردية", f'individual_{grade}')],
            [Button.inline("عرض طلاب الصف", f'show_grade{grade}')]
        ])
    
    elif data.startswith('zip_'):
        grade = data.split('_')[1]
        await event.respond(f"قم بإرسال ملف ZIP لنتائج {grades_folders[grade]}.تاكد من اضافة جميع صور نتائج الطلاب كل صورة تحمل اسم الطالب الثلاثي بصيغة png")
        user_states[event.sender_id] = 'awaiting_zip_file'
        user_states['current_grade'] = grade
    
    elif data.startswith('individual_'):
        grade = data.split('_')[1]
        await event.respond(f"أرسل صورة النتيجة ومعها في نفس الرسالة اسم الطالب الثلاثي *اذا كان هناك اكثر من طالب اكتب الاسم الرباعي للطالب \n الطالب {grades_folders[grade]}.")
        user_states[event.sender_id] = 'awaiting_individual_image'
        user_states['current_grade'] = grade

@client.on(events.NewMessage(incoming=True))
async def handle_zip(event):
    if user_states.get(event.sender_id) == 'awaiting_zip_file':
        if event.file and event.file.mime_type == 'application/zip':
            await event.reply("جاري تحميل نتائج الصف...")
            path = await event.download_media()
            
            grade = user_states.get('current_grade')
            
            with zipfile.ZipFile(path, 'r') as zip_ref:
                await event.reply("جاري استخراج النتائج...")
                zip_ref.extractall(f'./{grade}')
            
            await event.reply(f"تم تحميل نتائج {grades_folders[grade]} بنجاح.")
            os.remove(path)
        user_states[event.sender_id] = None
        event.stop_propagation()

@client.on(events.CallbackQuery)
async def add_individual_image(event):
    data = event.data.decode()
    if data.startswith('individual_'):
        grade = data.split('_')[1]
        await event.respond(f"أرسل صورة النتيجة {grades_folders[grade]}، مع اسم الطالب الثلاثي")
        user_states[event.sender_id] = 'awaiting_individual_image'
        user_states['current_grade'] = grade

@client.on(events.NewMessage(incoming=True))
async def handle_individual_image(event):
    if user_states.get(event.sender_id) == 'awaiting_individual_image':
        if event.file and event.file.mime_type.startswith('image'):
            image_path = await event.download_media()
            user_states['image_path'] = image_path
            message_text = event.text.strip()

            grade = user_states.get('current_grade')
            if not grade or not message_text:
                await event.reply("حدث خطأ: تأكد من إدخال اسم الطالب مع الصورة بشكل صحيح.")
                return
            
            new_path = f"./{grade}/{message_text}.png"
            if os.path.exists(image_path):
                os.rename(image_path, new_path)
                await event.reply(f"تم إضافة ورقة نتيجة {message_text} بنجاح {grades_folders[grade]}.")
                
                user_states[event.sender_id] = None
                user_states['image_path'] = None
                user_states['current_grade'] = None
            else:
                await event.reply("حدث خطأ في معالجة الصورة")

@client.on(events.CallbackQuery)
async def show_students(event):
    data = event.data.decode()
    
    if data.startswith('show_grade'):
        grade = data.split('_')[1]
        student_files = glob.glob(f'./{grade}/*.png')
        
        if student_files:
            buttons = [[Button.inline(file.split('/')[-1], f'delete_{file.split("/")[-1]}_{grade}')] for file in student_files]
            await event.respond("قائمة الطلاب * اذا اردت حذف طالب انقر على اسمه فقط:", buttons=buttons)
        else:
            await event.respond(f"لا يوجد طلاب مسجلين {grades_folders[grade]}.")

@client.on(events.CallbackQuery)
async def delete_student(event):
    data = event.data.decode()
    
    if data.startswith('delete_'):
        filename = data.split('_')[1]
        grade = data.split('_')[2]
        file_path = f"./{grade}/{filename}"
        
        if os.path.exists(file_path):
            os.remove(file_path)
            await event.respond(f"تم حذف الطالب: {filename} {grades_folders[grade]}.")
        else:
            await event.respond(f"لم يتم العثور على الطالب: {filename} {grades_folders[grade]}.")

client.run_until_disconnected()