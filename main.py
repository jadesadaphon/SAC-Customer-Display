import cv2
import win32gui
import win32ui
import win32con
import os
import logging
import numpy as np
import customtkinter
import pytesseract
import crcmod
import datetime
import qrcode
from screeninfo import get_monitors
from time import sleep
from threading import Thread, Event
from pynput import keyboard 
from PIL import Image

log_filename = 'log_SmileGenerateQrCodePayment.txt'
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(name)s] [%(threadName)s] %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_filename),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])

customtkinter.set_appearance_mode("light")
customtkinter.set_default_color_theme("dark-blue")

pytesseract.pytesseract.tesseract_cmd = ""

class HookSmile(Thread):
    def __init__(self) -> None:
        super().__init__(name="HookThread")
        logging.info(f'HookSmile class is __init__')
        self.__running_hook_smile = Event()
        self.hook_smile_image_path = r"_internal/static/image/background_blank.png"
        self.hook_smile_product_list_image_path = r"_internal/static/image/product_list.png"
        self.str_price = '0.00'
        self.image = None
        self.payment = False
        
    def stop_hook_smile(self):
        logging.info(f"Hook smile event is stopping...")
        self.__running_hook_smile.clear()      
        
    def show_cv2(self):
        while True :
            if self.image is not None:
                print("CV2 Show")
                try:
                    cv2.imshow('Display Window', self.image)
                except:
                    pass
            cv2.waitKey(1)
            sleep(0.1)
  
    def run(self):
        # bot_process_job = Thread(target=self.show_cv2, name="App")
        # bot_process_job.start()
        self.__running_hook_smile.set()
        logging.info('HookSmile class is running.')
        
        while self.__running_hook_smile.is_set():
            try:
                total_payment_area = {"start": (200,310), "end": (391,333)}
                windows_name = "บันทึกรับเงิน"
                hwnd = win32gui.FindWindow(None, windows_name)
                img = self.__capture_window(hwnd)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                img = self.__crop_target_area(img, total_payment_area)
                
                str_price = pytesseract.image_to_string(img, lang='eng').replace("\n", "")
                
                try:
                    if len(str_price) >= 3 and str_price[-3] == '.':
                        if str_price != self.str_price:
                            if str_price != '0.00':
                                self.str_price = str_price
                                self.__generate_payment_qr()
                            else:
                                self.str_price = '0.00'
                                self.hook_smile_image_path = r'_internal/static/image/background_blank.png'
                                logging.info(f'Set image path to {self.hook_smile_image_path}')
                except Exception as e:
                    logging.error(f"Error occurred: {e}")
                    pass
                self.payment =True
                sleep(0.5)
            except Exception as e:
                sleep(0.5)
                if 'Invalid window handle.' not in str(e):
                    logging.error(f"Error occurred: {e}")
                else:
                    self.str_price = '0.00'
                    self.hook_smile_image_path = r'_internal/static/image/background_blank.png'
                    try:
                        total_payment_area = {"start": (50,234), "end": (1924,1022)}
                        # windows_name = "CharmingAcc(Training ห้องฝึกหัด) - [บันทึกขายสินค้าและบริการ]"
                        windows_name = "CharmingAcc(บริษัท ไอดีโฮม 2015 จำกัด) - [บันทึกขายสินค้าและบริการ]"
                        hwnd = win32gui.FindWindow(None, windows_name)
                        img = self.__capture_window(hwnd)
                        img = self.__crop_target_area(img, total_payment_area)
                        self.image = img
                        self.payment = False
                    except Exception as e:
                        self.image = None
                        if 'Invalid window handle.' not in str(e):
                            logging.error(f"Error occurred: {e}")
                        

        logging.info(f"Hook smile has stopped running.")
                    
    def __generate_payment_qr(self):
        num_price = self.str_price.strip().replace(",", "")
        if(len(num_price) == 4):
            unit_code = "53113"
            unit = "04"
        if(len(num_price) == 5):
            unit_code = "53127"
            unit = "05"
        if(len(num_price) == 6):
            unit_code = "30030"
            unit = "06"
        if(len(num_price) == 7):
            unit_code = "53140"
            unit = "07"
        if(len(num_price) == 8):
            unit_code = "53148"
            unit = "08"
        if(len(num_price) == 9):
            unit_code = "53200"
            unit = "09"
        if(len(num_price) == 10):
            unit_code = "53210"
            unit = "10"
        
        payment_code = f"0002010102111531267607642676076400000220302684430810016A00000067701011201150107536000374030215000002203026844031943002685117091{unit_code}52040000530376454{unit}{num_price}5802TH5912ID HOME 20156005SURIN61053214062120708430026856304"
        crc_code = self.__calculate_crc_ccitt(payment_code)
        payment_data = f"{payment_code}{crc_code}"
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.hook_smile_image_path = os.path.join('_internal/static', f'{timestamp}.png')

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        img.save(self.hook_smile_image_path)
        logging.info(f'New payment QR code for {num_price} baht saved as {self.hook_smile_image_path}')
          
    def __calculate_crc_ccitt(self,data):
        crc_func = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, xorOut=0x0000, rev=False)
        crc_value = crc_func(data.encode('ascii'))
        return format(crc_value, '04X')
    
    def __capture_window(self,hwnd):
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bot - top
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        signedIntsArray = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img
    
    def __crop_target_area(self, img, target_area):
        img = img[target_area.get("start")[1]:target_area.get("end")[1], target_area.get("start")[0]:target_area.get("end")[0]]
        return img
    
class App(customtkinter.CTk, HookSmile):  
    def __init__(self) -> None:
        customtkinter.CTk.__init__(self)  
        HookSmile.__init__(self) 
        self.__running = Event()

        keyboard_thread = Thread(target=self.hook_keyboard, daemon=True, name="HookKeyboard")
        keyboard_thread.start()
        
        self.__kanit_40 = customtkinter.CTkFont(family='Kanit', size=40, weight='bold')
        self.__kanit_bold_28 = customtkinter.CTkFont(family='Kanit', size=28, weight='bold')
        self.__kanit_bold_20 = customtkinter.CTkFont(family='Kanit', size=20, weight='bold')
        self.__kanit_30 = customtkinter.CTkFont(family='Kanit', size=30)
        
        self.qrcode_image_path = "_internal/static/image/background_blank.png"
        
    def start(self):
        self.__running.set()
        hook_running_thread = Thread(target=self.hook_running, daemon=True, name="HookRunning")
        hook_running_thread.start()
        
        HookSmile.start(self)
        
        monitor_width, monitor_height = self.monitor_info()
        self.setup_qrcode_frame(monitor_width, monitor_height)
        self.qrcode_frame.pack_forget()
        
        self.setup_product_list_frame(monitor_width, monitor_height)
        self.product_list_frame.pack_forget()
        
        hook_price_thread = Thread(target=self.hook_price, daemon=True, name="HookPrice")
        hook_price_thread.start()
        
        self.mainloop()
        
   
    def hook_price(self):
        while self.__running.is_set():
            if self.payment:
                self.product_list_frame.pack_forget()
                self.qrcode_frame.pack(fill="x")
                if self.hook_smile_image_path != self.qrcode_image_path:
                    width, height = self.get_image_size(self.hook_smile_image_path)
                    width, height = self.calculate_new_height(width, height, 300)
                    qrcode_image = customtkinter.CTkImage(light_image=Image.open(self.hook_smile_image_path),dark_image=Image.open(self.hook_smile_image_path), size=(width, height))
                    self.qrcode_image_label.configure(image=qrcode_image, text="")
                    self.qrcode_image_label.pack(pady=25, padx=25)
                    if self.str_price != '0.00':
                        self.money_label.configure(text=f'จำนวนเงิน {self.str_price} บาท')
                        self.money_label.pack()
                    else:
                        self.money_label.configure(text=f'')
                        self.money_label.pack()
                    
                    if self.qrcode_image_path != "_internal/static/image/background_blank.png":
                        if os.path.exists(self.qrcode_image_path):
                            os.remove(self.qrcode_image_path)
                    self.qrcode_image_path = self.hook_smile_image_path
                sleep(0.5)
            else:   
                self.qrcode_frame.pack_forget()
                self.product_list_frame.pack(fill="x")
                if self.image is not None:
                    
                    try:
                        img_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                        height, width, channels = img_rgb.shape
                        width, height = self.calculate_new_height(width, height, 1923)
                        pil_image = Image.fromarray(img_rgb)
                        product_list_image = customtkinter.CTkImage(light_image=pil_image, dark_image=pil_image, size=(width, height))
                        self.product_list_image_label.configure(image=product_list_image)
                        self.product_list_image_label.image = product_list_image  # เก็บ reference เพื่อไม่ให้ภาพถูกลบ
                        self.product_list_image_label.update_idletasks()
                    
                    except Exception as e:
                        pass
             
                sleep(0.1)
               

    def monitor_info(self):
        monitor = self.get_monitor()
        monitor_width = monitor.width
        monitor_height = monitor.height
        monitor_x = monitor.x
        monitor_y = monitor.y
        self.title("Smile generate QRCode payment version 1.0.0.1") 
        self.overrideredirect(True)
        self.geometry(f"{monitor_width}x{monitor_height}+{monitor_x}+{monitor_y}")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        head_frame_height = monitor_height * 100 / 100
        return monitor_width, head_frame_height
    
    def setup_product_list_frame(self, monitor_width, monitor_height):
        self.product_list_frame = customtkinter.CTkFrame(self, width=monitor_width, height=monitor_height, corner_radius=0, fg_color='#E6E6E6')
        self.product_list_frame.pack_propagate(False)
        self.product_list_frame.pack(fill="x")
        
        logo_image_path = "_internal/static/image/logo_idhome.jpg"
        width, height = self.get_image_size(logo_image_path)
        width, height = self.calculate_new_height(width, height, 350)
        logo_image = customtkinter.CTkImage(light_image=Image.open(logo_image_path),dark_image=Image.open(logo_image_path), size=(width, height))
        self.logo_image_label = customtkinter.CTkLabel(self.product_list_frame)
        self.logo_image_label.configure(image=logo_image, text="")
        self.logo_image_label.pack(pady=(25,0))
        
        self.product_list_image_label = customtkinter.CTkLabel(self.product_list_frame, text="")
        self.product_list_image_label.pack(side="bottom", anchor="s", pady=0, padx=0)
    
    def setup_qrcode_frame(self,monitor_width, monitor_height):
        self.qrcode_frame = customtkinter.CTkFrame(self, width=monitor_width, height=monitor_height, corner_radius=0, fg_color='#E6E6E6')
        self.qrcode_frame.pack_propagate(False)
        self.qrcode_frame.pack(fill="x")
        
        logo_image_path = "_internal/static/image/logo_idhome.jpg"
        width, height = self.get_image_size(logo_image_path)
        width, height = self.calculate_new_height(width, height, 350)
        logo_image = customtkinter.CTkImage(light_image=Image.open(logo_image_path),dark_image=Image.open(logo_image_path), size=(width, height))
        self.logo_image_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.logo_image_label.configure(image=logo_image, text="")
        self.logo_image_label.pack(pady=(100,0))
        
        self.idhome_payment_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.idhome_payment_label.configure(text="ID-HOME PAYMENT", text_color='#00205A', font=self.__kanit_40, )
        self.idhome_payment_label.pack(pady=(40,0))
        
        self.img_qrcode_frame = customtkinter.CTkFrame(self.qrcode_frame)
        self.img_qrcode_frame.configure(width=350, height=350, fg_color='#D9D9D9')
        self.img_qrcode_frame.pack()
        
        width, height = self.get_image_size(self.qrcode_image_path)
        width, height = self.calculate_new_height(width, height, 300)
        qrcode_image = customtkinter.CTkImage(light_image=Image.open(self.qrcode_image_path),dark_image=Image.open(self.qrcode_image_path), size=(width, height))
        self.qrcode_image_label = customtkinter.CTkLabel(self.img_qrcode_frame)
        self.qrcode_image_label.configure(image=qrcode_image, text="")
        self.qrcode_image_label.pack(pady=25, padx=25)
        
        self.money_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.money_label.configure(text="", text_color='#00205A', font=self.__kanit_bold_28, )
        self.money_label.pack()
        
        self.account_number_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.account_number_label.configure(text="4620882680 บทจ.ไอดีโฮม2015", text_color='#00205A', font=self.__kanit_bold_20, )
        self.account_number_label.pack()
        
        message = 'Please scan QR Code with your mobile by\nusing Mobile Banking Application'
        self.description_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.description_label.configure(text=message, text_color='#00205A', font=self.__kanit_30, )
        self.description_label.pack(pady=(30,0))
        
        bank_image_path = "_internal/static/image/logo_bank.png"
        width, height = self.get_image_size(bank_image_path)
        width, height = self.calculate_new_height(width, height, 500)
        bank_image = customtkinter.CTkImage(light_image=Image.open(bank_image_path),dark_image=Image.open(bank_image_path), size=(width, height))
        self.bank_image_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.bank_image_label.configure(image=bank_image, text="")
        self.bank_image_label.pack()
        
    def calculate_new_height(self,original_width, original_height, new_width):
        new_height = int((original_height * new_width) / original_width)
        return new_width, new_height
    
    def get_image_size(self,image_path):
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height
        
    def get_monitor(self):
        obj= []
        monitor = get_monitors()
        if len(get_monitors()) == 1:
            obj = monitor[0]
        if len(get_monitors()) >= 2:
            obj = monitor[1]
        return obj
                
    def hook_keyboard(self):
        with keyboard.Listener(on_release=self.on_release) as listener:
            listener.join()

    def on_release(self, key):
        if key == keyboard.Key.end:
            self.__running.clear()
            return False

    def hook_running(self):
        while self.__running.is_set():
            sleep(1)
        self.stop()
        
    def on_closing(self): pass

    def stop(self):
        self.stop_hook_smile()
        self.quit()
        self.destroy()


if __name__ == "__main__": 
    
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = r"" r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        username = os.environ.get('USERNAME')
        pytesseract.pytesseract.tesseract_cmd = rf"C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    
    app = App()
    app.start()
    
    
    
    
     
    
import cv2
import win32gui
import win32ui
import win32con
import os
import logging
import numpy as np
import customtkinter
import pytesseract
import crcmod
import datetime
import qrcode
from screeninfo import get_monitors
from time import sleep
from threading import Thread, Event
from pynput import keyboard 
from PIL import Image

log_filename = 'log_SmileGenerateQrCodePayment.txt'
logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s] [%(name)s] [%(threadName)s] %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler(log_filename),  # Log to file
                        logging.StreamHandler()  # Log to console
                    ])

customtkinter.set_appearance_mode("light")
customtkinter.set_default_color_theme("dark-blue")

pytesseract.pytesseract.tesseract_cmd = ""

class HookSmile(Thread):
    def __init__(self) -> None:
        super().__init__(name="HookThread")
        logging.info(f'HookSmile class is __init__')
        self.__running_hook_smile = Event()
        self.hook_smile_image_path = r"_internal/static/image/background_blank.png"
        self.hook_smile_product_list_image_path = r"_internal/static/image/product_list.png"
        self.str_price = '0.00'
        self.image = None
        self.payment = False
        
    def stop_hook_smile(self):
        logging.info(f"Hook smile event is stopping...")
        self.__running_hook_smile.clear()      
        
    def show_cv2(self):
        while True :
            if self.image is not None:
                print("CV2 Show")
                try:
                    cv2.imshow('Display Window', self.image)
                except:
                    pass
            cv2.waitKey(1)
            sleep(0.1)
  
    def run(self):
        # bot_process_job = Thread(target=self.show_cv2, name="App")
        # bot_process_job.start()
        self.__running_hook_smile.set()
        logging.info('HookSmile class is running.')
        
        while self.__running_hook_smile.is_set():
            try:
                total_payment_area = {"start": (200,310), "end": (391,333)}
                windows_name = "บันทึกรับเงิน"
                hwnd = win32gui.FindWindow(None, windows_name)
                img = self.__capture_window(hwnd)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                img = self.__crop_target_area(img, total_payment_area)
                
                str_price = pytesseract.image_to_string(img, lang='eng').replace("\n", "")
                
                try:
                    if len(str_price) >= 3 and str_price[-3] == '.':
                        if str_price != self.str_price:
                            if str_price != '0.00':
                                self.str_price = str_price
                                self.__generate_payment_qr()
                            else:
                                self.str_price = '0.00'
                                self.hook_smile_image_path = r'_internal/static/image/background_blank.png'
                                logging.info(f'Set image path to {self.hook_smile_image_path}')
                except Exception as e:
                    logging.error(f"Error occurred: {e}")
                    pass
                self.payment =True
                sleep(0.5)
            except Exception as e:
                sleep(0.5)
                if 'Invalid window handle.' not in str(e):
                    logging.error(f"Error occurred: {e}")
                else:
                    self.str_price = '0.00'
                    self.hook_smile_image_path = r'_internal/static/image/background_blank.png'
                    try:
                        total_payment_area = {"start": (50,234), "end": (1924,1022)}
                        windows_name = "CharmingAcc(Training ห้องฝึกหัด) - [บันทึกขายสินค้าและบริการ]"
                        # windows_name = "CharmingAcc(บริษัท ไอดีโฮม 2015 จำกัด) - [บันทึกขายสินค้าและบริการ]"
                        hwnd = win32gui.FindWindow(None, windows_name)
                        img = self.__capture_window(hwnd)
                        img = self.__crop_target_area(img, total_payment_area)
                        self.image = img
                        self.payment = False
                    except Exception as e:
                        self.image = None
                        if 'Invalid window handle.' not in str(e):
                            logging.error(f"Error occurred: {e}")
                        

        logging.info(f"Hook smile has stopped running.")
                    
    def __generate_payment_qr(self):
        num_price = self.str_price.strip().replace(",", "")
        if(len(num_price) == 4):
            unit_code = "53113"
            unit = "04"
        if(len(num_price) == 5):
            unit_code = "53127"
            unit = "05"
        if(len(num_price) == 6):
            unit_code = "30030"
            unit = "06"
        if(len(num_price) == 7):
            unit_code = "53140"
            unit = "07"
        if(len(num_price) == 8):
            unit_code = "53148"
            unit = "08"
        if(len(num_price) == 9):
            unit_code = "53200"
            unit = "09"
        if(len(num_price) == 10):
            unit_code = "53210"
            unit = "10"
        
        payment_code = f"0002010102111531267607642676076400000220302684430810016A00000067701011201150107536000374030215000002203026844031943002685117091{unit_code}52040000530376454{unit}{num_price}5802TH5912ID HOME 20156005SURIN61053214062120708430026856304"
        crc_code = self.__calculate_crc_ccitt(payment_code)
        payment_data = f"{payment_code}{crc_code}"
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.hook_smile_image_path = os.path.join('_internal/static', f'{timestamp}.png')

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(payment_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        img.save(self.hook_smile_image_path)
        logging.info(f'New payment QR code for {num_price} baht saved as {self.hook_smile_image_path}')
          
    def __calculate_crc_ccitt(self,data):
        crc_func = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, xorOut=0x0000, rev=False)
        crc_value = crc_func(data.encode('ascii'))
        return format(crc_value, '04X')
    
    def __capture_window(self,hwnd):
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bot - top
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
        signedIntsArray = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (height, width, 4)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img
    
    def __crop_target_area(self, img, target_area):
        img = img[target_area.get("start")[1]:target_area.get("end")[1], target_area.get("start")[0]:target_area.get("end")[0]]
        return img
    
class App(customtkinter.CTk, HookSmile):  
    def __init__(self) -> None:
        customtkinter.CTk.__init__(self)  
        HookSmile.__init__(self) 
        self.__running = Event()

        keyboard_thread = Thread(target=self.hook_keyboard, daemon=True, name="HookKeyboard")
        keyboard_thread.start()
        
        self.__kanit_40 = customtkinter.CTkFont(family='Kanit', size=40, weight='bold')
        self.__kanit_bold_28 = customtkinter.CTkFont(family='Kanit', size=28, weight='bold')
        self.__kanit_bold_20 = customtkinter.CTkFont(family='Kanit', size=20, weight='bold')
        self.__kanit_30 = customtkinter.CTkFont(family='Kanit', size=30)
        
        self.qrcode_image_path = "_internal/static/image/background_blank.png"
        
    def start(self):
        self.__running.set()
        hook_running_thread = Thread(target=self.hook_running, daemon=True, name="HookRunning")
        hook_running_thread.start()
        
        HookSmile.start(self)
        
        monitor_width, monitor_height = self.monitor_info()
        self.setup_qrcode_frame(monitor_width, monitor_height)
        self.qrcode_frame.pack_forget()
        
        self.setup_product_list_frame(monitor_width, monitor_height)
        self.product_list_frame.pack_forget()
        
        hook_price_thread = Thread(target=self.hook_price, daemon=True, name="HookPrice")
        hook_price_thread.start()
        
        self.mainloop()
        
   
    def hook_price(self):
        while self.__running.is_set():
            if self.payment:
                self.product_list_frame.pack_forget()
                self.qrcode_frame.pack(fill="x")
                if self.hook_smile_image_path != self.qrcode_image_path:
                    width, height = self.get_image_size(self.hook_smile_image_path)
                    width, height = self.calculate_new_height(width, height, 300)
                    qrcode_image = customtkinter.CTkImage(light_image=Image.open(self.hook_smile_image_path),dark_image=Image.open(self.hook_smile_image_path), size=(width, height))
                    self.qrcode_image_label.configure(image=qrcode_image, text="")
                    self.qrcode_image_label.pack(pady=25, padx=25)
                    if self.str_price != '0.00':
                        self.money_label.configure(text=f'จำนวนเงิน {self.str_price} บาท')
                        self.money_label.pack()
                    else:
                        self.money_label.configure(text=f'')
                        self.money_label.pack()
                    
                    if self.qrcode_image_path != "_internal/static/image/background_blank.png":
                        if os.path.exists(self.qrcode_image_path):
                            os.remove(self.qrcode_image_path)
                    self.qrcode_image_path = self.hook_smile_image_path
                sleep(0.5)
            else:   
                self.qrcode_frame.pack_forget()
                self.product_list_frame.pack(fill="x")
                if self.image is not None:
                    
                    try:
                        img_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
                        height, width, channels = img_rgb.shape
                        width, height = self.calculate_new_height(width, height, 1923)
                        pil_image = Image.fromarray(img_rgb)
                        product_list_image = customtkinter.CTkImage(light_image=pil_image, dark_image=pil_image, size=(width, height))
                        self.product_list_image_label.configure(image=product_list_image)
                        self.product_list_image_label.image = product_list_image  # เก็บ reference เพื่อไม่ให้ภาพถูกลบ
                        self.product_list_image_label.update_idletasks()
                    
                    except Exception as e:
                        pass
             
                sleep(0.1)
               

    def monitor_info(self):
        monitor = self.get_monitor()
        monitor_width = monitor.width
        monitor_height = monitor.height
        monitor_x = monitor.x
        monitor_y = monitor.y
        self.title("Smile generate QRCode payment version 1.0.0.1") 
        self.overrideredirect(True)
        self.geometry(f"{monitor_width}x{monitor_height}+{monitor_x}+{monitor_y}")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        head_frame_height = monitor_height * 100 / 100
        return monitor_width, head_frame_height
    
    def setup_product_list_frame(self, monitor_width, monitor_height):
        self.product_list_frame = customtkinter.CTkFrame(self, width=monitor_width, height=monitor_height, corner_radius=0, fg_color='#E6E6E6')
        self.product_list_frame.pack_propagate(False)
        self.product_list_frame.pack(fill="x")
        
        logo_image_path = "_internal/static/image/logo_idhome.jpg"
        width, height = self.get_image_size(logo_image_path)
        width, height = self.calculate_new_height(width, height, 350)
        logo_image = customtkinter.CTkImage(light_image=Image.open(logo_image_path),dark_image=Image.open(logo_image_path), size=(width, height))
        self.logo_image_label = customtkinter.CTkLabel(self.product_list_frame)
        self.logo_image_label.configure(image=logo_image, text="")
        self.logo_image_label.pack(pady=(25,0))
        
        self.product_list_image_label = customtkinter.CTkLabel(self.product_list_frame, text="")
        self.product_list_image_label.pack(side="bottom", anchor="s", pady=0, padx=0)
    
    def setup_qrcode_frame(self,monitor_width, monitor_height):
        self.qrcode_frame = customtkinter.CTkFrame(self, width=monitor_width, height=monitor_height, corner_radius=0, fg_color='#E6E6E6')
        self.qrcode_frame.pack_propagate(False)
        self.qrcode_frame.pack(fill="x")
        
        logo_image_path = "_internal/static/image/logo_idhome.jpg"
        width, height = self.get_image_size(logo_image_path)
        width, height = self.calculate_new_height(width, height, 350)
        logo_image = customtkinter.CTkImage(light_image=Image.open(logo_image_path),dark_image=Image.open(logo_image_path), size=(width, height))
        self.logo_image_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.logo_image_label.configure(image=logo_image, text="")
        self.logo_image_label.pack(pady=(100,0))
        
        self.idhome_payment_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.idhome_payment_label.configure(text="ID-HOME PAYMENT", text_color='#00205A', font=self.__kanit_40, )
        self.idhome_payment_label.pack(pady=(40,0))
        
        self.img_qrcode_frame = customtkinter.CTkFrame(self.qrcode_frame)
        self.img_qrcode_frame.configure(width=350, height=350, fg_color='#D9D9D9')
        self.img_qrcode_frame.pack()
        
        width, height = self.get_image_size(self.qrcode_image_path)
        width, height = self.calculate_new_height(width, height, 300)
        qrcode_image = customtkinter.CTkImage(light_image=Image.open(self.qrcode_image_path),dark_image=Image.open(self.qrcode_image_path), size=(width, height))
        self.qrcode_image_label = customtkinter.CTkLabel(self.img_qrcode_frame)
        self.qrcode_image_label.configure(image=qrcode_image, text="")
        self.qrcode_image_label.pack(pady=25, padx=25)
        
        self.money_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.money_label.configure(text="", text_color='#00205A', font=self.__kanit_bold_28, )
        self.money_label.pack()
        
        self.account_number_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.account_number_label.configure(text="4620882680 บทจ.ไอดีโฮม2015", text_color='#00205A', font=self.__kanit_bold_20, )
        self.account_number_label.pack()
        
        message = 'Please scan QR Code with your mobile by\nusing Mobile Banking Application'
        self.description_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.description_label.configure(text=message, text_color='#00205A', font=self.__kanit_30, )
        self.description_label.pack(pady=(30,0))
        
        bank_image_path = "_internal/static/image/logo_bank.png"
        width, height = self.get_image_size(bank_image_path)
        width, height = self.calculate_new_height(width, height, 500)
        bank_image = customtkinter.CTkImage(light_image=Image.open(bank_image_path),dark_image=Image.open(bank_image_path), size=(width, height))
        self.bank_image_label = customtkinter.CTkLabel(self.qrcode_frame)
        self.bank_image_label.configure(image=bank_image, text="")
        self.bank_image_label.pack()
        
    def calculate_new_height(self,original_width, original_height, new_width):
        new_height = int((original_height * new_width) / original_width)
        return new_width, new_height
    
    def get_image_size(self,image_path):
        with Image.open(image_path) as img:
            width, height = img.size
        return width, height
        
    def get_monitor(self):
        obj= []
        monitor = get_monitors()
        if len(get_monitors()) == 1:
            obj = monitor[0]
        if len(get_monitors()) >= 2:
            obj = monitor[1]
        return obj
                
    def hook_keyboard(self):
        with keyboard.Listener(on_release=self.on_release) as listener:
            listener.join()

    def on_release(self, key):
        if key == keyboard.Key.end:
            self.__running.clear()
            return False

    def hook_running(self):
        while self.__running.is_set():
            sleep(1)
        self.stop()
        
    def on_closing(self): pass

    def stop(self):
        self.stop_hook_smile()
        self.quit()
        self.destroy()


if __name__ == "__main__": 
    
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = r"" r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    else:
        username = os.environ.get('USERNAME')
        pytesseract.pytesseract.tesseract_cmd = rf"C:\Users\{username}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
    
    app = App()
    app.start()
    
    
    
    
     
    
