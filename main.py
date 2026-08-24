import os
import telebot
import lief

# Railway এর Environment Variables থেকে টোকেন নেবে
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "🤖 **So Dumper & Patcher Bot**\n\n"
        "১. **ডাম্প করতে:** যেকোনো `.so` ফাইল সেন্ড করুন।\n"
        "২. **প্যাচ করতে:** ডাম্প করা ফাইলের মেসেজটিতে **Reply** করে লিখুন:\n"
        "`/patch <offset> <hex_code>`\n"
        "উদাহরণ: `/patch 14C04 C0035FD6`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

# শুধু ফাইল দিলে ডাম্প করবে
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_name = message.document.file_name
        if not file_name.endswith('.so'):
            bot.reply_to(message, "❌ দয়া করে একটি সঠিক .so ফাইল সেন্ড করুন।")
            return

        bot.reply_to(message, "⏳ ফাইল স্ক্যান করা হচ্ছে...")

        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        binary = lief.parse(file_name)
        if not binary:
            bot.reply_to(message, "❌ ফাইলটি রিড করা যায়নি।")
            os.remove(file_name)
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
        output += "💡 **প্যাচ করতে চাইলে:**\nএই মেসেজটিতে **Reply** করে লিখুন:\n`/patch <offset> <hex_code>`"

        if len(output) > 4000:
            out_filename = f"{file_name}_dump.txt"
            with open(out_filename, "w", encoding="utf-8") as f:
                f.write(output)
            with open(out_filename, "rb") as f:
                bot.send_document(message.chat.id, f)
            os.remove(out_filename)
        else:
            bot.reply_to(message, output, parse_mode="Markdown")
            
        os.remove(file_name)

    except Exception as e:
        bot.reply_to(message, f"❌ ডাম্প করতে সমস্যা হয়েছে: {e}")

# রিপ্লাই করে কমান্ড দিলে প্যাচ করবে
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/patch'))
def handle_patch(message):
    if not message.reply_to_message or not message.reply_to_message.document:
        bot.reply_to(message, "⚠️ দয়া করে যেই `.so` ফাইলটি প্যাচ করতে চান, সেটিতে **Reply** করে কমান্ড দিন।", parse_mode="Markdown")
        return

    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "⚠️ সঠিক নিয়ম: `/patch <offset> <hex_code>`\nযেমন: `/patch 14C04 C0035FD6`", parse_mode="Markdown")
        return

    offset_hex = parts[1]
    hex_payload = parts[2]
    doc = message.reply_to_message.document
    file_name = doc.file_name

    if not file_name.endswith('.so'):
        bot.reply_to(message, "❌ রিপ্লাই করা ফাইলটি .so ফাইল নয়।")
        return

    try:
        bot.reply_to(message, "⏳ প্যাচ করা হচ্ছে...")
        
        # ফাইল ডাউনলোড
        file_info = bot.get_file(doc.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        # প্যাচিং লজিক
        offset = int(offset_hex, 16)
        payload_bytes = bytes.fromhex(hex_payload)
        
        with open(file_name, 'r+b') as f:
            f.seek(offset)
            f.write(payload_bytes)
        
        # রিনেম করে পাঠানো
        patched_name = f"patched_{file_name}"
        os.rename(file_name, patched_name)
        
        with open(patched_name, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"✅ **প্যাচ সফল হয়েছে!**\nOffset: `{offset_hex}`\nHex: `{hex_payload}`", parse_mode="Markdown")
        
        os.remove(patched_name)

    except ValueError:
        bot.reply_to(message, "❌ Offset অথবা Hex কোড সঠিক নয়। আবার চেক করুন।")
        if os.path.exists(file_name): os.remove(file_name)
    except Exception as e:
        bot.reply_to(message, f"❌ প্যাচ করতে সমস্যা হয়েছে: {e}")
        if os.path.exists(file_name): os.remove(file_name)

print("Bot is running...")
bot.infinity_polling()
