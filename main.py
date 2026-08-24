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
        "২. **প্যাচ করতে:** `.so` ফাইল সেন্ড করার সময় ক্যাপশনে লিখুন:\n"
        "`/patch <offset> <hex_code>`\n"
        "উদাহরণ: `/patch 14C04 C0035FD6`"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_name = message.document.file_name
        
        # ফাইলটি .so কি না তা চেক করা
        if not file_name.endswith('.so'):
            bot.reply_to(message, "❌ দয়া করে একটি সঠিক .so ফাইল সেন্ড করুন।")
            return

        bot.reply_to(message, "⏳ ফাইল প্রসেস করা হচ্ছে...")

        # ফাইল ডাউনলোড করা
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        caption = message.caption if message.caption else ""

        # ==========================================
        # ফ্লো ১: প্যাচিং (যদি ক্যাপশনে /patch থাকে)
        # ==========================================
        if caption.startswith('/patch'):
            parts = caption.split()
            if len(parts) != 3:
                bot.reply_to(message, "⚠️ সঠিক নিয়ম: `/patch <offset> <hex_code>`\nযেমন: `/patch 14C04 C0035FD6`", parse_mode="Markdown")
                os.remove(file_name)
                return
            
            offset_hex = parts[1]
            hex_payload = parts[2]
            
            try:
                # হেক্স থেকে ইন্টিজার এবং বাইটে কনভার্ট করা
                offset = int(offset_hex, 16)
                payload_bytes = bytes.fromhex(hex_payload)
                
                # ফাইলে প্যাচ করা
                with open(file_name, 'r+b') as f:
                    f.seek(offset)
                    f.write(payload_bytes)
                
                # রিনেম করে ইউজারকে পাঠানো
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

        # ==========================================
        # ফ্লো ২: ডাম্পিং (যদি ক্যাপশনে কিছু না থাকে)
        # ==========================================
        else:
            try:
                binary = lief.parse(file_name)
                if not binary:
                    bot.reply_to(message, "❌ ফাইলটি রিড করা যায়নি। এটি কি সঠিক ELF বাইনারি?")
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
                output += "💡 **প্যাচ করতে চাইলে:**\nফাইলটি আবার সেন্ড করুন এবং ক্যাপশনে লিখুন:\n`/patch <offset> <hex_code>`"

                # আউটপুট বড় হলে টেক্সট ফাইল হিসেবে পাঠাবে
                if len(output) > 4000:
                    out_filename = f"{file_name}_dump.txt"
                    with open(out_filename, "w", encoding="utf-8") as f:
                        f.write(output)
                    with open(out_filename, "rb") as f:
                        bot.send_document(message.chat.id, f, caption="✅ ডাম্প ফাইল রেডি!")
                    os.remove(out_filename)
                else:
                    bot.reply_to(message, output, parse_mode="Markdown")
            
            except Exception as e:
                bot.reply_to(message, f"❌ ডাম্প করতে সমস্যা হয়েছে: {e}")
            
            finally:
                if os.path.exists(file_name):
                    os.remove(file_name)

    except Exception as e:
        bot.reply_to(message, f"❌ একটি অজানা এরর হয়েছে: {e}")

# বটটিকে সবসময় চালু রাখার কমান্ড
print("Bot is running...")
bot.infinity_polling()
