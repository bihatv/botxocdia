import telebot
from telebot import types
import os
import json
import datetime
import random
import base64
from captcha.image import ImageCaptcha  # Thư viện tạo captcha
from io import BytesIO  # Thư viện hỗ trợ làm việc với dữ liệu nhị phân

# Bot information and required channels
# Bot information and required channels
API_TOKEN ='7584993027:AAGm1y0ms1odeE-nlsOYGQdWWFv8iOyCMLc'  # Updated token
bot = telebot.TeleBot(API_TOKEN)
settings = {
    "groups": ['@hupcodenhacai1'],
    "min_withdraw": 20000,
    "referral_bonus": 4000
}

user_data, invited_users, captcha_codes = {}, {}, {}
admins = [7014048216]  # Admin IDs
from PIL import Image, ImageDraw, ImageFont
import random
import string
from io import BytesIO

# Dictionary to store CAPTCHA solutions
captcha_solutions = {}

# Generate a simple CAPTCHA image
def generate_captcha():
    # Random 5-character string
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    # Create a white image with PIL
    img = Image.new('RGB', (150, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    # Use a basic font for the CAPTCHA (adjust the path to a .ttf font file if needed)
    font = ImageFont.load_default()

    # Draw the CAPTCHA text on the image
    d.text((10, 10), captcha_text, font=font, fill=(0, 0, 0))

    # Save image to a BytesIO object
    captcha_image = BytesIO()
    img.save(captcha_image, format='PNG')
    captcha_image.seek(0)

    return captcha_image, captcha_text

# When the user starts interacting with the bot
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    referrer_id = None

    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]

    if referrer_id:
        if str(user_id) not in user_data:
            invited_users[str(user_id)] = referrer_id
            save_data(invited_users_file, invited_users)
            
            initialize_user(user_id)
            save_data(user_data_file, user_data)

    markup = types.InlineKeyboardMarkup()
    for channel in settings["groups"]:

        markup.add(types.InlineKeyboardButton(f'👉 Tham Gia Nhóm 👈', url=f'https://t.me/{channel[1:]}'))
    
    # Generate a CAPTCHA image and solution
    captcha_image, captcha_text = generate_captcha()
    captcha_solutions[user_id] = captcha_text  # Store CAPTCHA solution for the user

    markup.add(types.InlineKeyboardButton('✔️ Xác minh CAPTCHA ✔️', callback_data='check_captcha'))

    caption = """
    <b>NHẬP CHỮ CÁI TRÊN ẢNH !</b>
    ❗ Trước tiên phải tham gia nhóm trước rồi giải CAPTCHA để tiếp tục.
    """  
    bot.send_photo(message.chat.id, 
                   captcha_image, 
                   caption=caption, 
                   reply_markup=markup, 
                   parse_mode='HTML')

# CAPTCHA verification process
@bot.callback_query_handler(func=lambda call: call.data == 'check_captcha')
def ask_for_captcha(call):
    user_id = call.from_user.id
    if user_id in captcha_solutions:
        bot.send_message(call.message.chat.id, "Vui lòng nhập mã CAPTCHA mà bạn thấy:")
    else:
        bot.send_message(call.message.chat.id, "Bạn đã vượt qua bước xác minh CAPTCHA!")

# Handle user's CAPTCHA input
@bot.message_handler(func=lambda message: message.from_user.id in captcha_solutions)
def handle_captcha_response(message):
    user_id = message.from_user.id
    user_input = message.text.strip()

    # Compare user input with stored CAPTCHA solution
    if user_input.upper() == captcha_solutions[user_id]:
        bot.send_message(message.chat.id, "✔️ Xác minh CAPTCHA thành công!")
        del captcha_solutions[user_id]  # Remove solved CAPTCHA

        # Now check if the user is subscribed to all required channels
        if check_subscription(user_id):
            referrer_id = invited_users.get(str(user_id))

            if str(user_id) not in user_data:
                initialize_user(user_id)
                save_data(user_data_file, user_data)

            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add(types.KeyboardButton('👤 Tài Khoản'), types.KeyboardButton('👥 Mời Bạn Bè'))
            markup.add(types.KeyboardButton('💵 Rút tiền'), types.KeyboardButton('📊 Thống Kê'))
            markup.add(types.KeyboardButton('🆘 Hỗ Trợ'))

            balance = get_balance(user_id)
            bot.send_message(message.chat.id, f"🫡 Chào Mừng Bạn Quay Trở Lại! Số Dư Của Bạn Là {balance} đồng. Tiếp Tục Mời Bạn Bè Kiếm Code Ngay Nào", reply_markup=markup)

            if referrer_id and referrer_id in user_data:
                update_user_balance(referrer_id, settings["referral_bonus"])
                bot.send_message(referrer_id, f"Bạn đã nhận được {settings['referral_bonus']} đồng khi mời {message.from_user.username} tham gia.")

                invited_users.pop(str(user_id))
                save_data(invited_users_file, invited_users)
        else:
            bot.send_message(message.chat.id, "Vui lòng tham gia tất cả các kênh yêu cầu trước khi kiểm tra lại.")
    else:
        bot.send_message(message.chat.id, "❌ Sai CAPTCHA. Vui lòng thử lại.")

user_data_file = 'userdata.json'
invited_users_file = 'invitedusers.json'

# Check channel subscription
def check_subscription(user_id):
    for channel in settings["groups"]:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

# Hàm tải dữ liệu
def load_data(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Hàm lưu dữ liệu
def save_data(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

user_data = load_data(user_data_file)
invited_users = load_data(invited_users_file)

# Hàm lấy số dư của người dùng
def get_balance(user_id):
    return user_data.get(str(user_id), {}).get('balance', 0)

# Hàm khởi tạo người dùng
def initialize_user(user_id):
    if str(user_id) not in user_data:
        user_data[str(user_id)] = {'balance': 1000, 'registration_date': datetime.datetime.now().timestamp()}

# Hàm cập nhật số dư của người dùng
def update_user_balance(user_id, amount):
    if str(user_id) in user_data:
        user_data[str(user_id)]['balance'] += amount
    else:
        user_data[str(user_id)] = {'balance': amount}
    save_data(user_data_file, user_data)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    referrer_id = None

    # Kiểm tra nếu có mã giới thiệu trong tin nhắn
    if len(message.text.split()) > 1:
        referrer_id = message.text.split()[1]

    # Lưu thông tin người mời và xử lý thưởng
    if referrer_id:
        if str(user_id) not in user_data:  # Chỉ xử lý nếu người dùng chưa có tài khoản
            invited_users[str(user_id)] = referrer_id
            save_data(invited_users_file, invited_users)
            
            # Khởi tạo tài khoản cho người mới nếu chưa tồn tại
            initialize_user(user_id)
            save_data(user_data_file, user_data)

            # Thưởng cho người mời
            if referrer_id in user_data:
                update_user_balance(referrer_id, settings["referral_bonus"])
                bot.send_message(referrer_id, f"🎉 Bạn đã nhận được {settings['referral_bonus']} đồng khi mời {message.from_user.username} tham gia.")


        # Xóa thông tin người mời sau khi thưởng
        if str(user_id) in invited_users:
            invited_users.pop(str(user_id))
            save_data(invited_users_file, invited_users)

    markup = types.InlineKeyboardMarkup()
    for channel in settings["groups"]:
        markup.add(types.InlineKeyboardButton(f'👉 Tham Gia Nhóm 👈', url=f'https://t.me/{channel[1:]}'))
    markup.add(types.InlineKeyboardButton('✔️Kiểm Tra✔️', callback_data='check'))
    photo_url = "https://i.imgur.com/wmsTcUg.jpeg"
    caption = """


"""  
    bot.send_photo(message.chat.id, 
                   photo_url,
                   caption=caption,
                   reply_markup=markup,
                   parse_mode='HTML')

# Hàm xử lý khi người dùng kiểm tra kênh
@bot.callback_query_handler(func=lambda call: call.data == 'check')
def check_channels(call):
    user_id = call.from_user.id

    if check_subscription(user_id):
        referrer_id = invited_users.get(str(user_id))

        # Khởi tạo tài khoản cho người dùng nếu chưa tồn tại
        if str(user_id) not in user_data:
            initialize_user(user_id)
            save_data(user_data_file, user_data)

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(types.KeyboardButton('👤 Tài Khoản'), types.KeyboardButton('👥 Mời Bạn Bè'))
        markup.add(types.KeyboardButton('💵 Rút tiền'), types.KeyboardButton('Link Game'))
        markup.add(types.KeyboardButton('📊 Thống Kê'))  # Thêm nút "Thống Kê"

        balance = get_balance(user_id)
        bot.send_message(call.message.chat.id, f"🫡 Chào Mừng Bạn Quay Trở Lại! Số Dư Của Bạn Là {balance} đồng. Tiếp Tục Mời Bạn Bè Kiếm Code Ngay Nào", reply_markup=markup)

        if referrer_id and referrer_id in user_data:
            update_user_balance(referrer_id, settings["referral_bonus"])
            bot.send_message(referrer_id, f"Bạn đã nhận được {settings['referral_bonus']} đồng khi mời {call.from_user.username} tham gia.")
            invited_users.pop(str(user_id))
            save_data(invited_users_file, invited_users)
    else:
        bot.send_message(call.message.chat.id, "Vui lòng tham gia tất cả các kênh yêu cầu trước khi kiểm tra lại.")

@bot.message_handler(func=lambda message: message.text == "👥 Mời Bạn Bè")
def handle_invite_friends(message):
    user_id = message.from_user.id
    invite_link = f"https://t.me/{bot.get_me().username}?start={user_id}"

    photo_url = "https://images.app.goo.gl/Ejj1CcpVhqbRBsz28"
    caption = """
<b>❗️ NHẬN GIFCODE RẤT ĐƠN GIẢN CHỈ CẦN VÀI THAO TÁC
✅ MỜI BẠN BÈ THAM GIA BOT NHẬN NGAY 1000đ 
✅ https://momo.vn// LÀ TÊN MIỀN CHÍNH HÃNG DUY NHẤT!</b>

👤 Link Mời Bạn Bè ( Bấm vào coppy ) :<code> {invite_link}</code>
    """.format(invite_link=invite_link)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Sao chép link", callback_data=f"copy_invite_link_{user_id}"))

    bot.send_photo(message.chat.id, 
                   photo_url,
                   caption=caption,
                   reply_markup=markup,
                   parse_mode='HTML')

@bot.message_handler(commands=['thongbao'])
def thongbao_text(message):
    if message.from_user.id in admins:
        try:
            parts = message.text.split(maxsplit=1)
            if len(parts) < 2:
                raise ValueError("Sai cú pháp. Sử dụng: /thongbao [Nội dung thông báo]")

            announcement = parts[1]

            for user_id in user_data.keys():
                try:
                    bot.send_message(user_id, f"<b>{announcement}</b>", parse_mode='HTML')
                except Exception as e:
                    print(f"Gửi thông báo cho user_id {user_id} không thành công: {str(e)}")

            bot.reply_to(message, "Đã gửi thông báo đến tất cả người dùng thành công!")

        except ValueError as e:
            bot.reply_to(message, str(e))

    else:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này.")

@bot.message_handler(commands=['addcoin'])
def handle_addcoin_command(message):
    user_id = message.from_user.id
    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền thực hiện lệnh này.")
        return

    try:
        details = message.text.split()
        target_user_id = int(details[1])
        amount = int(details[2])

        update_user_balance(target_user_id, amount)
        bot.reply_to(message, f'Đã cộng {amount} coins cho user {target_user_id}. Số dư hiện tại: {get_balance(target_user_id)} coins')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp /addcoin [user_id] [số tiền]')

@bot.message_handler(commands=['truemoney'])
def handle_truemoney_command(message):
    user_id = message.from_user.id
    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền thực hiện lệnh này.")
        return

    try:
        details = message.text.split()
        target_user_id = int(details[1])
        amount = int(details[2])

        balance = get_balance(target_user_id)
        if balance >= amount:
            update_user_balance(target_user_id, -amount)
            bot.reply_to(message, f'Đã trừ {amount} coins từ user {target_user_id}. Số dư hiện tại: {get_balance(target_user_id)} coins')
        else:
            bot.reply_to(message, 'Số dư không đủ để thực hiện giao dịch.')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp /truemoney [user_id] [số tiền]')

@bot.message_handler(func=lambda message: message.text == '👤 Tài Khoản')
def handle_account_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = f"{message.from_user.first_name} {message.from_user.last_name}"
    balance = get_balance(user_id)
    balance_formatted = "{:,} Đ".format(balance) 
    
    registration_date = datetime.datetime.fromtimestamp(user_data.get(str(user_id), {}).get('registration_date', datetime.datetime.now().timestamp())).strftime('%d-%m-%Y')  # Ngày đăng ký tài khoản
    last_active = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')  
    
    text = f"""
Họ và tên: {full_name}
Số Dư: {balance_formatted}
ID Của Bạn: {user_id}

"""
    
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '💵 Rút tiền')
def handle_withdraw(message):
    user_id = message.from_user.id
    if str(user_id) in user_data and user_data[str(user_id)]['balance'] >= settings["min_withdraw"]:
        withdraw_instructions = f"""
🏦 Hướng dẫn rút tiền:
✅ Số tiền rút tối thiểu: {settings["min_withdraw"]} VND
💬 Cú pháp:
/ruttien [nganhang/momo] [stk/sđt] [sotien]

📌 Ví dụ:
/ruttien vietcombank 0123456789 20000
/ruttien momo 0912345678 50000

Ngân hàng hỗ trợ: Vietcombank, ACB, VPBank, MBBank, TPBank, BIDV, Techcombank, Agribank, MoMo
"""
        bot.send_message(message.chat.id, withdraw_instructions)
    else:
        bot.send_message(message.chat.id, "⚠️ Bạn cần có số dư ít nhất 20.000 đồng để thực hiện lệnh rút tiền.")

# Tải danh sách mã đổi thưởng từ file
def load_redeemable_codes(filename):
    try:
        with open(filename, 'r') as file:
            codes = [line.strip() for line in file.readlines() if line.strip()]
        return codes
    except FileNotFoundError:
        return []

# Lưu danh sách mã đổi thưởng đã cập nhật lại vào file
def save_redeemable_codes(filename, codes):
    with open(filename, 'w') as file:
        file.write('\n'.join(codes))

# Đường dẫn đến file chứa mã đổi thưởng
redeemable_codes_file = 'redeemable_codes.txt'

# Hàm xử lý lệnh /doicode với chức năng duyệt tự động
@bot.message_handler(commands=['ruttien'])
def handle_withdraw_request(message):
    user_id = message.from_user.id

    if str(user_id) not in user_data:
        bot.send_message(message.chat.id, "🔒 Bạn chưa có tài khoản hoặc chưa đủ điều kiện rút tiền.")
        return

    current_balance = user_data[str(user_id)]['balance']
    parts = message.text.split()

    if len(parts) != 4:
        bot.send_message(message.chat.id, "⚠️ Sai cú pháp!\nDùng đúng mẫu:\n/ruttien [nganhang] [sotaikhoan] [sotien]\nVí dụ: /ruttien vietcombank 0123456789 20000")
        return

    bank_name = parts[1].lower()
    account_number = parts[2]
    try:
        amount = int(parts[3])
    except ValueError:
        bot.send_message(message.chat.id, "🚫 Số tiền phải là số nguyên hợp lệ.")
        return

    valid_banks = ['vietcombank', 'acb', 'vpbank', 'mbbank', 'tpbank', 'bidv', 'techcombank', 'agribank', 'momo']

    if bank_name not in valid_banks:
        bot.send_message(message.chat.id, f"🏦 Ngân hàng không hợp lệ.\nChỉ hỗ trợ: {', '.join(valid_banks)}")
        return

    if amount < settings["min_withdraw"]:
        bot.send_message(message.chat.id, f"⚠️ Số tiền rút tối thiểu là {settings['min_withdraw']} VND.")
        return

    if current_balance < amount:
        bot.send_message(message.chat.id, "❌ Số dư của bạn không đủ để thực hiện rút tiền.")
        return

    # Trừ tiền
       # Trừ tiền
    user_data[str(user_id)]['balance'] -= amount
    save_data(user_data_file, user_data)

    # Gửi xác nhận cho người dùng
    bot.send_message(message.chat.id, f"🎉 Yêu cầu rút {amount} VND đã được ghi nhận.\nVui lòng đợi admin duyệt giao dịch.")

    # Gửi thông báo cho admin kèm nút duyệt/hủy
    for admin_id in admins:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{user_id}_{amount}"),
            types.InlineKeyboardButton("❌ Hủy", callback_data=f"decline_{user_id}_{amount}")
        )

        loai_tai_khoan = "📱 Ví MoMo" if bank_name == "momo" else f"💳 Ngân hàng: {bank_name.upper()}"
        bot.send_message(
            admin_id,
            f"📤 YÊU CẦU RÚT TIỀN MỚI\n👤 User: @{message.from_user.username or user_id}\n{loai_tai_khoan}\n🔢 SĐT/STK: {account_number}\n💰 Số tiền: {amount} VND",
            reply_markup=markup
        )



@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'decline_')))
def handle_approval(call):
    try:
        action, user_id, amount = call.data.split('_')
        if action == "approve":
            bot.send_message(user_id, f"🎉 Yêu cầu rút {amount} VND đã được admin duyệt.\n💰 Tiền sẽ được chuyển trong thời gian sớm nhất.")

            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ Đã duyệt yêu cầu rút tiền.")
        elif action == "decline":
            bot.send_message(user_id, "❌ Yêu cầu rút tiền của bạn đã bị hủy. Vui lòng liên hệ admin để biết thêm chi tiết.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Đã hủy yêu cầu rút tiền.")

        # Xóa nút inline sau khi duyệt hoặc hủy
        bot.edit_message_text("Yêu cầu đã được xử lý", call.message.chat.id, call.message.message_id)
    except ValueError:
        bot.send_message(call.message.chat.id, "⚠️ Đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau.")

@bot.message_handler(func=lambda message: message.text == '📊 Thống Kê')
def handle_statistics(message):
    user_id = message.from_user.id

    if user_id not in admins:
        bot.reply_to(message, "Bạn không có quyền xem thống kê.")
        return

    total_users = len(user_data)
    total_balance = sum(user['balance'] for user in user_data.values())

    response_text = f"""
    📊 **Thống Kê Hiện Tại**
    - Tổng số người dùng: {total_users}
    - Tổng số dư: {total_balance} đồng
    """
    bot.send_message(message.chat.id, response_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '🆘 Hỗ Trợ')
def handle_support(message):
    bot.send_message(message.chat.id, "🆘 Bạn cần hỗ trợ? Vui lòng liên hệ với chúng tôi qua Telegram: @congthinh29 Và Đợi Phản Hồi.")

@bot.message_handler(commands=['chatmem'])
def handle_chatmem_command(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "Bạn không có quyền sử dụng lệnh này.")
        return

    try:
        details = message.text.split(maxsplit=2)
        if len(details) < 3:
            raise ValueError("Sai cú pháp. Sử dụng: /chatmem [user_id] [Nội dung tin nhắn]")

        target_user_id = int(details[1])
        message_text = details[2]

        bot.send_message(target_user_id, message_text)
        bot.reply_to(message, f"Đã gửi tin nhắn đến người dùng ID {target_user_id}.")
    except (IndexError, ValueError):
        bot.reply_to(message, 'Vui lòng nhập theo cú pháp: /chatmem [user_id] [Nội dung tin nhắn]')

# resetuid
@bot.message_handler(commands=['resetuser'])
def reset_user_command(message):
    if message.from_user.id not in admins:
        bot.reply_to(message, "❌ Bạn không có quyền dùng lệnh này.")
        return

    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError("❗ Dùng đúng cú pháp: /resetuser [user_id]")

        target_id = str(int(parts[1]))

        # Xoá dữ liệu người dùng
        user_removed = False
        invited_removed = False

        if target_id in user_data:
            del user_data[target_id]
            save_data(user_data_file, user_data)
            user_removed = True

        if target_id in invited_users:
            del invited_users[target_id]
            save_data(invited_users_file, invited_users)
            invited_removed = True

        if user_removed or invited_removed:
            bot.reply_to(message, f"✅ Đã reset dữ liệu của user {target_id}.")
        else:
            bot.reply_to(message, f"ℹ️ Không tìm thấy dữ liệu user {target_id}.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Lỗi: {str(e)}")
#chỉnh min rút và nhóm
@bot.message_handler(commands=['setgroup'])
def set_group_command(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "📌 Dùng đúng cú pháp: /setgroup @tennhom")

    new_group = parts[1]
    settings["groups"] = [new_group]
    bot.reply_to(message, f"✅ Đã cập nhật nhóm yêu cầu tham gia thành: {new_group}")

@bot.message_handler(commands=['setminwithdraw'])
def set_min_withdraw(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.reply_to(message, "📌 Dùng đúng cú pháp: /setminwithdraw [số tiền]")

    settings["min_withdraw"] = int(parts[1])
    bot.reply_to(message, f"✅ Số tiền rút tối thiểu mới: {parts[1]} đồng")

@bot.message_handler(commands=['setreferral'])
def set_referral_bonus(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        return bot.reply_to(message, "📌 Dùng đúng cú pháp: /setreferral [số tiền]")

    settings["referral_bonus"] = int(parts[1])
    bot.reply_to(message, f"✅ Tiền thưởng mỗi lời mời mới: {parts[1]} đồng")


#thêm group
@bot.message_handler(commands=['addgroup'])
def add_group_command(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "📌 Dùng đúng cú pháp: /addgroup @tennhom")

    new_group = parts[1]
    if new_group not in settings["groups"]:
        settings["groups"].append(new_group)
        bot.reply_to(message, f"✅ Đã thêm nhóm mới: {new_group}")
    else:
        bot.reply_to(message, "ℹ️ Nhóm đã tồn tại trong danh sách.")
#xoá group
@bot.message_handler(commands=['removegroup'])
def remove_group_command(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "📌 Dùng đúng cú pháp: /removegroup @tennhom")

    group_to_remove = parts[1]
    if group_to_remove in settings["groups"]:
        settings["groups"].remove(group_to_remove)
        bot.reply_to(message, f"✅ Đã xoá nhóm: {group_to_remove}")
    else:
        bot.reply_to(message, "⚠️ Không tìm thấy nhóm trong danh sách.")
#check quản trị viên của bot
@bot.message_handler(commands=['checkbotingroup'])
def check_bot_in_group(message):
    if message.from_user.id not in admins:
        return bot.reply_to(message, "❌ Bạn không có quyền thực hiện.")

    results = []
    for group in settings["groups"]:
        try:
            bot_member = bot.get_chat_member(group, bot.get_me().id)
            status = bot_member.status  # 'administrator', 'member', 'left', etc.

            if status == 'administrator':
                results.append(f"✅ {group}: Bot là quản trị viên.")
            elif status == 'member':
                results.append(f"⚠️ {group}: Bot chỉ là thành viên, không có quyền quản trị.")
            else:
                results.append(f"❌ {group}: Bot chưa được thêm vào nhóm.")
        except Exception as e:
            results.append(f"❌ {group}: Lỗi - {str(e)}")

    reply = "\n".join(results)
    bot.reply_to(message, reply)

#cuối
from flask import Flask, request, abort

WEBHOOK_HOST = 'https://botxocdia.onrender.com'  # Đổi thành domain của bạn trên Render
WEBHOOK_PATH = f"/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running!'

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        abort(403)

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
