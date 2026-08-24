import os
import telebot
import lief

# Railway এর Environment Variables থেকে টোকেন নেবে
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

# ইউজারদের ফাইল টেম্পোরারি সেভ রাখার জন্য ডিকশনারি
user_files = {}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🤖 So Dumper & Patcher Bot\n\nকাজ শুরু করতে যেকোনো .so ফাইল সেন্ড করুন।")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_name = message.document.file_name
        if not file_name.endswith('.so'):
            bot.reply_to(message, "❌ দয়া করে একটি সঠিক .so ফাইল সেন্ড করুন।")
            return

        msg = bot.reply_to(message, "⏳ ফাইল স্ক্যান করা হচ্ছে...")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # ইউজারের চ্যাট আইডি দিয়ে ফাইল সেভ করা
        user_file_path = f"{message.chat.id}_{file_name}"
        with open(user_file_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        binary = lief.parse(user_file_path)
        if not binary:
            bot.edit_message_text("❌ ফাইলটি রিড করা যায়নি।", chat_id=message.chat.id, message_id=msg.message_id)
            os.remove(user_file_path)
            return

        output = f"File: {file_name}\n"
        output += f"Architecture: {binary.header.machine_type}\n"
        output += "-" * 30 + "\n"
        
        count = 0
        for symbol in binary.exported_symbols:
            if symbol.name:
                output += f"0x{symbol.value:08X} : {symbol.name}\n"
                count += 1

        output += "-" * 30 + "\n"
        output += f"Total Functions Found: {count}\n\n"
        output += "✅ ফাইলটি প্যাচ করতে চাইলে:\nএখন শুধু Offset এবং Hex Code স্পেস দিয়ে লিখে সেন্ড করুন。\n\nউদাহরণ: 14C04 C0035FD6"

        # ডাম্প মেসেজ পাঠানো (Markdown রিমুভ করা হয়েছে)
        bot.edit_message_text(output, chat_id=message.chat.id, message_id=msg.message_id)
        
        # ইউজারের ফাইলের স্টেট সেভ রাখা
        user_files[message.chat.id] = user_file_path
        
        # বটের পরবর্তী মেসেজের জন্য অপেক্ষা করা
        bot.register_next_step_handler(message, process_patch_step)

    except Exception as e:
        bot.reply_to(message, f"❌ ডাম্প করতে সমস্যা হয়েছে: {e}")

def process_patch_step(message):
    chat_id = message.chat.id
    
    # যদি ইউজার কোড না দিয়ে অন্য কোনো ফাইল দেয়
    if message.content_type == 'document':
        handle_docs(message)
        return
        
    if chat_id not in user_files:
        return

    file_path = user_files[chat_id]
    original_name = file_path.split('_', 1)[1]
    text = message.text.strip()
    
    parts = text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ সঠিক নিয়ম হয়নি। উদাহরণ: 14C04 C0035FD6\nদয়া করে ফাইলটি আবার সেন্ড করে চেষ্টা করুন।")
        if os.path.exists(file_path): os.remove(file_path)
        del user_files[chat_id]
        return
        
    offset_hex, hex_payload = parts[0], parts[1]
    
    try:
        bot.reply_to(message, "⏳ প্যাচ করা হচ্ছে...")
        
        # প্যাচিং
        offset = int(offset_hex, 16)
        payload_bytes = bytes.fromhex(hex_payload)
        
        with open(file_path, 'r+b') as f:
            f.seek(offset)
            f.write(payload_bytes)
        
        # রিনেম করে পাঠানো
        patched_name = f"patched_{original_name}"
        os.rename(file_path, patched_name)
        
        with open(patched_name, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"✅ প্যাচ সফল হয়েছে!\nOffset: {offset_hex}\nHex: {hex_payload}")
        
        os.remove(patched_name)
        del user_files[chat_id]

    except ValueError:
        bot.reply_to(message, "❌ Offset অথবা Hex কোড সঠিক নয়। ফাইলটি আবার সেন্ড করে চেষ্টা করুন।")
        if os.path.exists(file_path): os.remove(file_path)
        del user_files[chat_id]
    except Exception as e:
        bot.reply_to(message, f"❌ প্যাচ করতে সমস্যা হয়েছে: {e}")
        if os.path.exists(file_path): os.remove(file_path)
        del user_files[chat_id]

print("Bot is running...")
bot.infinity_polling()
