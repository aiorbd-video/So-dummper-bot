import os
import telebot
import lief

# Railway এর Environment Variables থেকে টোকেন নেবে
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "স্বাগতম! আমাকে যেকোনো .so (ELF) ফাইল সেন্ড করুন, আমি এর অফসেট এবং ফাংশন ডাম্প করে দেব।")

@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_name = message.document.file_name
        
        # ফাইলটি .so কি না তা চেক করা
        if not file_name.endswith('.so'):
            bot.reply_to(message, "দয়া করে একটি সঠিক .so ফাইল সেন্ড করুন।")
            return

        bot.reply_to(message, "ফাইলটি স্ক্যান করা হচ্ছে... দয়া করে অপেক্ষা করুন।")

        # ফাইল ডাউনলোড করা
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        # LIEF দিয়ে ফাইল অ্যানালাইজ করা
        binary = lief.parse(file_name)
        if not binary:
            bot.reply_to(message, "ফাইলটি রিড করা যায়নি। এটি কি সঠিক ELF বাইনারি?")
            os.remove(file_name)
            return

        output = f"File: {file_name}\n"
        output += f"Architecture: {binary.header.machine_type}\n"
        output += "-" * 30 + "\n"
        
        count = 0
        # এক্সপোর্ট করা ফাংশন ও অফসেট বের করা
        for symbol in binary.exported_symbols:
            if symbol.name:
                output += f"0x{symbol.value:08X} : {symbol.name}\n"
                count += 1

        output += "-" * 30 + "\n"
        output += f"Total Functions Found: {count}"

        # টেলিগ্রামের মেসেজ লিমিট 4096 ক্যারেক্টার। আউটপুট বড় হলে টেক্সট ফাইল হিসেবে পাঠাবে।
        if len(output) > 4000:
            out_filename = f"{file_name}_dump.txt"
            with open(out_filename, "w", encoding="utf-8") as f:
                f.write(output)
            with open(out_filename, "rb") as f:
                bot.send_document(message.chat.id, f)
            os.remove(out_filename)
        else:
            bot.reply_to(message, output)

        # কাজ শেষে সার্ভার থেকে .so ফাইল মুছে ফেলা
        os.remove(file_name)

    except Exception as e:
        bot.reply_to(message, f"একটি এরর হয়েছে: {e}")

# বটটিকে সবসময় চালু রাখার কমান্ড
print("Bot is running...")
bot.infinity_polling()
